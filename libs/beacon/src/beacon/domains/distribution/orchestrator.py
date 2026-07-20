"""Sync orchestrator for the distribution domain.

Encapsulates the full sync business logic so the CLI handler remains thin:
argument parsing + one orchestrator call + output formatting.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

from beacon.core.dependencies.manifest import (
    AgentManifestError,
    load_agent_manifest,
    validate_agent_frontmatter_clean,
    validate_agents_directory,
    validate_declared_skills,
)
from beacon.core.dependencies.resolver import (
    ResolutionFailure,
    SkillGap,
    compute_effective_set,
)
from beacon.core.exceptions import BeaconSyncError, DependencyError
from beacon.core.gitignore import apply_all_gitignores
from beacon.core.manifest.beacon import BeaconManifest
from beacon.domains.adoption.discovery import count_unadopted_since
from beacon.domains.artifact.agent import detect_agent_targets
from beacon.domains.artifact.skill import (
    install_bundled_skills_globally,
    normalize_skill_entry,
    skill_name_from_entry,
    validate_skill_entries,
    wire_bundled_skills_per_project,
    wire_skills_post_sync,
)
from beacon.domains.distribution.legacy_cleanup import (
    cleanup_legacy_global_agent_symlinks,
)
from beacon.domains.distribution.migration import migrate_entries
from beacon.domains.distribution.sync_engine import (
    DestinationOutsideArtifactsError,
    OutOfWarehouseError,
    SyncEngine,
    SyncSummary,
)
from beacon.domains.setup.wiring import (
    confirm_prune,
    desired_context_refs,
    has_synced_contexts,
    reconcile_context_references,
    unwire_pruned_artifacts,
    wire_agents_atomically,
)
from beacon.domains.warehouse.git_health import (
    check_warehouse_git_clean,
    check_warehouse_on_main_branch,
)
from beacon.domains.warehouse.preconditions import ensure_sync_ready
from beacon.utils.git import find_project_root

MIGRATION_DOC_URL = "docs/archive/migrations/artifact-dependencies-frontmatter.md"


@dataclass
class Orphan:
    """A symlink under .agentic-beacon/artifacts/ not in beacon.yaml."""

    rel_path: str
    is_modified: bool = False


@dataclass
class SyncOrchestrationResult:
    """Result returned by run_sync()."""

    dry_run: bool
    summary: SyncSummary
    artifact_paths: list[str]
    conflicts: list[str]
    orphans: list[Orphan]
    confirmed_prune: list[str]
    oc_added: list[str]
    cc_added: list[str]
    wired_skills: list[str]
    wire_errors: list[str]
    bundled_installed: list[str]
    bundled_skipped: list[str]
    adoption_notification: str | None
    no_artifacts: bool
    agent_config_init_needed: bool
    project_root: Path
    artifacts_dir: Path
    warehouse_path: Path
    wiring_notes: list[str] = field(default_factory=list)
    migration_resolved: dict[str, str] = field(default_factory=dict)
    unresolved_files: list[str] = field(default_factory=list)
    legacy_agents_cleaned: int = 0


def _normalize_beacon_for_resolver(
    beacon: BeaconManifest, warehouse_path: Path
) -> BeaconManifest:
    """Normalize beacon.yaml entries to match resolver's expected format.

    Resolver expects context names without 'contexts/' prefix and '.md' suffix,
    and skill names without 'skills/' prefix and trailing slash.
    Also expands glob patterns to concrete entries.

    Skill globs like skills/code-review/**/* normalize to the unique skill
    directory name (code-review), not individual files.
    """
    sync_engine = SyncEngine(
        warehouse_path=warehouse_path, artifacts_path=Path("/dev/null")
    )

    normalized_contexts: list[str] = []
    for c in beacon.artifacts.contexts:
        if "*" in c or "?" in c or "[" in c:
            for match in sync_engine.expand_glob(c):
                normalized_contexts.append(
                    str(Path(match).with_suffix("")).replace("contexts/", "", 1)
                )
        else:
            if c.startswith("contexts/"):
                normalized_contexts.append(
                    str(Path(c).with_suffix("")).replace("contexts/", "", 1)
                )
            else:
                normalized_contexts.append(c)

    normalized_skills: list[str] = []
    seen_skills: set[str] = set()
    for s in beacon.artifacts.skills:
        if "*" in s or "?" in s or "[" in s:
            for match in sync_engine.expand_glob(s):
                # Glob matches may be files like skills/code-review/SKILL.md
                # Extract unique skill directory name
                norm = match.replace("skills/", "", 1).split("/")[0]
                if norm and norm not in seen_skills:
                    normalized_skills.append(norm)
                    seen_skills.add(norm)
        else:
            norm = s.replace("skills/", "").rstrip("/").split("/")[0]
            if norm and norm not in seen_skills:
                normalized_skills.append(norm)
                seen_skills.add(norm)

    normalized = BeaconManifest(
        artifacts={
            "contexts": normalized_contexts,
            "skills": normalized_skills,
            "agents": beacon.artifacts.agents,
        },
        ignore=beacon.ignore,
    )
    return normalized


def _expand_effective_set(
    effective_set,
    sync_engine: SyncEngine,
    warehouse_path: Path,
    verbose: bool,
) -> list[str]:
    """Expand EffectiveSet into individual file paths for sync.

    Skills and knowledge directories are expanded to their contents;
    contexts are used as-is.
    """
    artifact_paths: list[str] = []

    for ctx in sorted(effective_set.contexts):
        ctx_path = f"contexts/{ctx}.md"
        artifact_paths.append(ctx_path)

    for skill_name in sorted(effective_set.skills):
        skill_dir_entry = normalize_skill_entry(skill_name)
        matches = sync_engine.expand_glob(f"{skill_dir_entry}/**/*")
        if matches:
            artifact_paths.extend(matches)
        else:
            logger.warning(
                "No files found for skill: {}",
                skill_name_from_entry(skill_name),
            )

    for knowledge_path in sorted(effective_set.knowledge):
        if (warehouse_path / knowledge_path).is_dir():
            matches = sync_engine.expand_glob(f"{knowledge_path}/**/*.md")
            if matches:
                artifact_paths.extend(matches)
            else:
                logger.warning("No .md files found under: {}", knowledge_path)
        else:
            artifact_paths.append(knowledge_path)

    return artifact_paths


def run_sync(
    project_root: Path | None = None,
    *,
    force: bool = False,
    verbose: bool = False,
    dry_run: bool = False,
    skip_git_check: bool = False,
    contribute_local: bool = False,
    discard_local: bool = False,
    log_fn: Callable[[str], None] | None = None,
    resolve_callback: Callable[[str, str], str] | None = None,
    skill_conflict_callback: Callable[[list[str]], bool] | None = None,
    auto_accept_gaps: bool = False,
    gap_prompt_callback: Callable[[SkillGap], bool] | None = None,
) -> SyncOrchestrationResult:
    """Run the full sync pipeline.

    Raises BeaconSyncError or other exceptions on fatal issues;
    callers should catch and format output.
    """
    if contribute_local and discard_local:
        raise BeaconSyncError(
            "--contribute-local and --discard-local are mutually exclusive."
        )

    project_root = project_root or find_project_root()

    warehouse_path, workspace_config = ensure_sync_ready(project_root)

    # Validate agent manifest (only when agents/ has content)
    agents_dir = warehouse_path / "agents"
    if agents_dir.exists() and agents_dir.is_dir():
        has_agent_files = any(
            f.is_file() and f.suffix == ".md" and f.name != "README.md"
            for f in agents_dir.iterdir()
        )
        if has_agent_files:
            try:
                manifest = load_agent_manifest(warehouse_path)
                validate_agents_directory(warehouse_path, manifest)
                validate_agent_frontmatter_clean(warehouse_path)
                if manifest is not None:
                    validate_declared_skills(warehouse_path, manifest)
            except AgentManifestError as exc:
                raise BeaconSyncError(
                    f"Warehouse agent manifest validation failed:\n{exc}"
                ) from exc

    if not dry_run and not skip_git_check:
        git_result = check_warehouse_git_clean(warehouse_path)
        if not git_result.ok:
            raise BeaconSyncError(git_result.error_message, hint=git_result.hint)

    if not dry_run and not skip_git_check:
        branch_result = check_warehouse_on_main_branch(
            warehouse_path,
            main_branch=workspace_config.warehouse.main_branch,
        )
        if not branch_result.ok:
            raise BeaconSyncError(branch_result.error_message, hint=branch_result.hint)

    beacon_dir = project_root / ".agentic-beacon"
    beacon_yaml = beacon_dir / "beacon.yaml"
    beacon_settings = BeaconManifest.from_yaml(beacon_yaml)
    validate_skill_entries(beacon_settings)

    # 8.1: Dependency resolution as FIRST step — before any file I/O
    normalized_beacon = _normalize_beacon_for_resolver(beacon_settings, warehouse_path)
    effective_result = compute_effective_set(normalized_beacon, warehouse_path)

    # Handle agent-required skill gaps (project-scoped-agents feature)
    if isinstance(effective_result, ResolutionFailure) and effective_result.gaps:
        gaps = effective_result.gaps
        if auto_accept_gaps:
            gaps_to_accept = list(gaps)
        elif gap_prompt_callback is not None:
            # Collect answers for all gaps first to preserve atomicity
            answers = [gap_prompt_callback(gap) for gap in gaps]
            if all(answers):
                gaps_to_accept = list(gaps)
            else:
                # Atomic rejection: if any gap is rejected, reject all
                gap_names = ", ".join(g.missing_skill for g in gaps)
                raise DependencyError(
                    f"Missing required skills for declared agents: {gap_names}. "
                    f"See {MIGRATION_DOC_URL} for migration instructions."
                )
        else:
            # Non-interactive without --yes
            gap_names = ", ".join(g.missing_skill for g in gaps)
            raise DependencyError(
                f"Missing required skills for declared agents: {gap_names}. "
                f"See {MIGRATION_DOC_URL} for migration instructions."
            )

        if gaps_to_accept and not dry_run:
            # Append normalised skill paths to beacon.yaml
            for gap in gaps_to_accept:
                skill_entry = f"skills/{gap.missing_skill}/"
                if skill_entry not in beacon_settings.artifacts.skills:
                    beacon_settings.artifacts.skills.append(skill_entry)
            beacon_settings.to_yaml(beacon_yaml)

            # Re-run resolver with updated state
            normalized_beacon = _normalize_beacon_for_resolver(
                beacon_settings, warehouse_path
            )
            effective_result = compute_effective_set(normalized_beacon, warehouse_path)

    if isinstance(effective_result, ResolutionFailure):
        # 8.2: Exit with structured error containing migration doc URL
        error_msg = (
            f"Dependency resolution failed. See {MIGRATION_DOC_URL} "
            f"for migration instructions.\n\n"
            + "\n".join(f"  • {e}" for e in effective_result.errors)
        )
        logger.error(error_msg)
        raise BeaconSyncError(error_msg)

    effective_set = effective_result

    artifacts_dir = beacon_dir / "artifacts"
    sync_engine = SyncEngine(
        warehouse_path=warehouse_path, artifacts_path=artifacts_dir
    )

    # 8.3: Single expansion over EffectiveSet
    artifact_paths = _expand_effective_set(
        effective_set, sync_engine, warehouse_path, verbose
    )

    # Add declared agent paths to artifact_paths so the sync engine creates
    # the .agentic-beacon/artifacts/agents/<name>.md symlinks
    for agent_entry in beacon_settings.artifacts.agents:
        artifact_paths.append(agent_entry)

    # Co-distribute agent partials alongside declared agents.
    if beacon_settings.artifacts.agents:
        partial_matches = sync_engine.expand_glob("agent-partials/**/*")
        for partial_path in partial_matches:
            if (warehouse_path / partial_path).is_file():
                artifact_paths.append(partial_path)

    total_explicit = (
        len(beacon_settings.artifacts.skills)
        + len(beacon_settings.artifacts.contexts)
        + len(beacon_settings.artifacts.agents)
    )
    no_artifacts = total_explicit == 0

    if not no_artifacts:
        try:
            sync_engine.validate_paths(artifact_paths)
        except OutOfWarehouseError as e:
            raise BeaconSyncError(
                f"Sync aborted: {e}\n"
                f"Entry '{e.entry}' resolves to {e.resolved_path} which is outside the warehouse.\n"
                f"See {MIGRATION_DOC_URL} for details."
            ) from e
        except DestinationOutsideArtifactsError as e:
            raise BeaconSyncError(
                f"Sync aborted: {e}\n"
                f"Entry '{e.entry}' would write to {e.resolved_path}, outside the project artifacts directory.\n"
                f"See {MIGRATION_DOC_URL} for details."
            ) from e

        # Detect and handle migration from copy-based trees
        classification = sync_engine.classify_entries(artifact_paths)
        regular_files = {
            p: s for p, s in classification.items() if s.startswith("regular_file")
        }

        migration_resolved: dict[str, str] = {}
        unresolved_files: list[str] = []

        if regular_files and not dry_run:
            if not contribute_local and not discard_local and resolve_callback is None:
                # No resolution strategy — collect unresolved and fail
                unresolved_files = list(regular_files.keys())
            else:
                migration_resolved = migrate_entries(
                    sync_engine,
                    classification,
                    contribute_local=contribute_local,
                    discard_local=discard_local,
                    resolve_callback=resolve_callback,
                )
                # Any regular files still remaining are unresolved
                post_classification = sync_engine.classify_entries(artifact_paths)
                unresolved_files = [
                    p
                    for p, s in post_classification.items()
                    if s.startswith("regular_file")
                ]
    else:
        migration_resolved = {}
        unresolved_files = []

    # 8.6-8.8: Orphan pruning against effective set (always run, even for empty manifests)
    orphans: list[Orphan] = []
    if artifacts_dir.exists():
        synced_set = set(artifact_paths)
        for file_path in sorted(artifacts_dir.rglob("*")):
            if not file_path.is_symlink():
                continue
            rel_path = str(file_path.relative_to(artifacts_dir))
            if rel_path not in synced_set:
                orphans.append(Orphan(rel_path=rel_path, is_modified=False))

    confirmed_prune: list[str] = []
    if orphans and not dry_run:
        confirmed_prune = confirm_prune(orphans, dry_run=dry_run)

    try:
        summary = sync_engine.sync_all(
            artifact_paths=artifact_paths,
            paths_to_prune=confirmed_prune if not dry_run else None,
            verbose=verbose,
            dry_run=dry_run,
            log_fn=log_fn,
        )
    except OutOfWarehouseError as e:
        raise BeaconSyncError(
            f"Sync aborted: {e}\n"
            f"Entry '{e.entry}' resolves to {e.resolved_path} which is outside the warehouse.\n"
            f"See {MIGRATION_DOC_URL} for details."
        ) from e
    except DestinationOutsideArtifactsError as e:
        raise BeaconSyncError(
            f"Sync aborted: {e}\n"
            f"Entry '{e.entry}' would write to {e.resolved_path}, outside the project artifacts directory.\n"
            f"See {MIGRATION_DOC_URL} for details."
        ) from e

    # Post-sync wiring
    oc_added: list[str] = []
    cc_added: list[str] = []
    wired_skills: list[str] = []
    wire_errors: list[str] = []
    wiring_notes: list[str] = []
    agent_config_init_needed = False

    if summary.pruned_paths and not dry_run:
        unwire_pruned_artifacts(project_root, summary.pruned_paths, artifacts_dir)

    # Wire declared agents into project-local tool directories — atomic
    # with rollback on partial failure (PER-131).
    if not dry_run:
        detected_tools = detect_agent_targets(project_root)
        agent_artifact_files = [
            artifacts_dir / agent_entry
            for agent_entry in beacon_settings.artifacts.agents
        ]
        wire_agents_atomically(project_root, agent_artifact_files, detected_tools)
        if beacon_settings.artifacts.agents and not detected_tools:
            wiring_notes.append(
                "  Agents declared but not wired — no tool directories found at project root.\n"
                "  Agent wiring into [bold].claude/agents/[/bold] and"
                " [bold].opencode/agents/[/bold] was skipped.\n"
                "  Create a tool directory then re-run [bold]abc sync[/bold]:\n"
                "    mkdir .claude    [dim]# for Claude Code[/dim]\n"
                "    mkdir .opencode  [dim]# for OpenCode[/dim]"
            )

    # Use effective set for wiring decisions — reconcile references wholesale
    has_contexts = bool(effective_set.contexts) and not dry_run
    has_skills = bool(effective_set.skills) and not dry_run

    if effective_set.contexts:
        desired_refs = desired_context_refs(effective_set.contexts)
        reconcile_result = reconcile_context_references(
            project_root, desired_refs, dry_run=dry_run
        )
        oc_added = reconcile_result.added
        cc_added = reconcile_result.removed

        if not dry_run:
            has_opencode = (project_root / "opencode.json").exists()
            has_claude = any(
                p.exists()
                for p in [
                    project_root / ".claude" / "CLAUDE.md",
                    project_root / "CLAUDE.md",
                ]
            )
            if not has_opencode and not has_claude:
                if has_synced_contexts(artifacts_dir):
                    agent_config_init_needed = True
                else:
                    wiring_notes.append(
                        "  Contexts synced — wire them into your agent config:\n"
                        '  [bold]opencode.json[/bold] → add to "instructions" array:\n'
                        '    ".agentic-beacon/artifacts/contexts/<name>.md"\n'
                        "  [bold]CLAUDE.md[/bold] → add a line per context:\n"
                        "    @.agentic-beacon/artifacts/contexts/<name>.md"
                    )
        else:
            if reconcile_result:
                wiring_notes.append(
                    "  Contexts would be synced — wire them into your agent config if needed:\n"
                    '  [bold]opencode.json[/bold] → add to "instructions" array:\n'
                    '    ".agentic-beacon/artifacts/contexts/<name>.md"\n'
                    "  [bold]CLAUDE.md[/bold] → add a line per context:\n"
                    "    @.agentic-beacon/artifacts/contexts/<name>.md"
                )

    if has_skills:
        wired_skills, wire_errors = wire_skills_post_sync(
            project_root,
            artifacts_dir,
            force=force,
            skill_conflict_callback=skill_conflict_callback,
        )

    # Gitignore managed blocks are applied unconditionally above (Tier A always,
    # Tier B per tool-dir existence) — no per-tool or per-agent gating needed.

    if not dry_run:
        bundled_installed, bundled_skipped = install_bundled_skills_globally()
        bundled_wired, bundled_wire_errors = wire_bundled_skills_per_project(
            project_root
        )
        wired_skills = wired_skills + bundled_wired
        wire_errors = wire_errors + bundled_wire_errors
    else:
        bundled_installed, bundled_skipped = [], []
        bundled_wired, bundled_wire_errors = [], []

    # Legacy global agent symlink cleanup (PER-113 migration)
    legacy_agents_cleaned = 0
    if not dry_run:
        legacy_agents_cleaned = cleanup_legacy_global_agent_symlinks(
            warehouse_path, project_root
        )

    adoption_notification = None
    if not dry_run:
        try:
            unadopted_count = count_unadopted_since(
                warehouse_path, beacon_settings, "HEAD"
            )
            if unadopted_count > 0:
                adoption_notification = (
                    f"{unadopted_count} new artifact(s) available "
                    "-- run abc adopt to review"
                )
        except Exception:
            pass

    # Apply gitignore managed blocks after all wiring so tool dirs exist.
    if not dry_run:
        apply_all_gitignores(project_root)

    return SyncOrchestrationResult(
        dry_run=dry_run,
        summary=summary,
        artifact_paths=artifact_paths,
        conflicts=[],
        orphans=orphans,
        confirmed_prune=confirmed_prune,
        oc_added=oc_added,
        cc_added=cc_added,
        wired_skills=wired_skills,
        wire_errors=wire_errors,
        bundled_installed=list(bundled_installed),
        bundled_skipped=list(bundled_skipped),
        adoption_notification=adoption_notification,
        no_artifacts=no_artifacts,
        agent_config_init_needed=agent_config_init_needed,
        project_root=project_root,
        artifacts_dir=artifacts_dir,
        warehouse_path=warehouse_path,
        wiring_notes=wiring_notes,
        migration_resolved=migration_resolved,
        unresolved_files=unresolved_files,
        legacy_agents_cleaned=legacy_agents_cleaned,
    )
