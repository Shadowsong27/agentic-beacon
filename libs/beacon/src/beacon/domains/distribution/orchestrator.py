"""Sync orchestrator for the distribution domain.

Encapsulates the full sync business logic so the CLI handler remains thin:
argument parsing + one orchestrator call + output formatting.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

from beacon.core.exceptions import BeaconSyncError
from beacon.core.gitignore import GitignoreManager
from beacon.core.manifest.beacon import BeaconManifest
from beacon.core.preconditions import ensure_sync_ready
from beacon.domains.adoption.discovery import count_unadopted_since
from beacon.domains.artifact.agent import (
    sync_agents_from_warehouse,
    update_agent_gitignores,
)
from beacon.domains.artifact.skill import (
    install_bundled_skills_globally,
    normalize_skill_entry,
    skill_name_from_entry,
    validate_skill_entries,
    wire_bundled_skills_per_project,
    wire_skills_post_sync,
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
    has_synced_contexts,
    unwire_pruned_artifacts,
    wire_contexts_claudecode,
    wire_contexts_opencode,
)
from beacon.domains.warehouse.git_health import (
    check_warehouse_git_clean,
    check_warehouse_on_main_branch,
)
from beacon.utils.git import find_project_root


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

    warehouse_path = ensure_sync_ready(project_root)

    if not dry_run and not skip_git_check:
        git_result = check_warehouse_git_clean(warehouse_path)
        if not git_result.ok:
            raise BeaconSyncError(git_result.error_message, hint=git_result.hint)

    if not dry_run and not skip_git_check:
        branch_result = check_warehouse_on_main_branch(warehouse_path)
        if not branch_result.ok:
            raise BeaconSyncError(branch_result.error_message, hint=branch_result.hint)

    beacon_dir = project_root / ".agentic-beacon"
    beacon_yaml = beacon_dir / "beacon.yaml"
    beacon_settings = BeaconManifest.from_yaml(beacon_yaml)
    validate_skill_entries(beacon_settings)

    artifacts_dir = beacon_dir / "artifacts"
    sync_engine = SyncEngine(
        warehouse_path=warehouse_path, artifacts_path=artifacts_dir
    )

    total_artifacts = (
        len(beacon_settings.artifacts.knowledge)
        + len(beacon_settings.artifacts.skills)
        + len(beacon_settings.artifacts.contexts)
    )

    if total_artifacts == 0:
        if not dry_run:
            bundled_installed, bundled_skipped = install_bundled_skills_globally()
            bundled_wired, bundled_wire_errors = wire_bundled_skills_per_project(
                project_root
            )
            sync_agents_from_warehouse(warehouse_path, force=force)
        else:
            bundled_installed, bundled_skipped = [], []
            bundled_wired, bundled_wire_errors = [], []
        return SyncOrchestrationResult(
            dry_run=dry_run,
            summary=SyncSummary(),
            artifact_paths=[],
            conflicts=[],
            orphans=[],
            confirmed_prune=[],
            oc_added=[],
            cc_added=[],
            wired_skills=list(bundled_wired),
            wire_errors=list(bundled_wire_errors),
            bundled_installed=list(bundled_installed),
            bundled_skipped=list(bundled_skipped),
            adoption_notification=None,
            no_artifacts=True,
            agent_config_init_needed=False,
            project_root=project_root,
            artifacts_dir=artifacts_dir,
            warehouse_path=warehouse_path,
        )

    artifact_paths: list[str] = []

    for artifact_type in ["knowledge", "skills", "contexts"]:
        artifacts_list = getattr(beacon_settings.artifacts, artifact_type)
        for pattern in artifacts_list:
            if "*" in pattern or "?" in pattern or "[" in pattern:
                try:
                    matches = sync_engine.expand_glob(pattern)
                    if not matches:
                        logger.warning("No files matched pattern: {}", pattern)
                    elif verbose:
                        logger.info(
                            "Pattern '{}' matched {} files", pattern, len(matches)
                        )
                    artifact_paths.extend(matches)
                except Exception as e:
                    raise BeaconSyncError(
                        f"Invalid glob pattern '{pattern}': {e}"
                    ) from e
            elif artifact_type == "skills":
                skill_dir_entry = normalize_skill_entry(pattern)
                matches = sync_engine.expand_glob(f"{skill_dir_entry}/**/*")
                if matches:
                    artifact_paths.extend(matches)
                else:
                    logger.warning(
                        "No files found for skill: {}",
                        skill_name_from_entry(pattern),
                    )
            elif artifact_type == "knowledge" and (warehouse_path / pattern).is_dir():
                matches = sync_engine.expand_glob(f"{pattern}/**/*.md")
                if matches:
                    artifact_paths.extend(matches)
                else:
                    logger.warning("No .md files found under: {}", pattern)
            else:
                artifact_paths.append(pattern)

    try:
        sync_engine.validate_paths(artifact_paths)
    except OutOfWarehouseError as e:
        raise BeaconSyncError(
            f"Sync aborted: {e}\n"
            f"Entry '{e.entry}' resolves to {e.resolved_path} which is outside the warehouse."
        ) from e
    except DestinationOutsideArtifactsError as e:
        raise BeaconSyncError(
            f"Sync aborted: {e}\n"
            f"Entry '{e.entry}' would write to {e.resolved_path}, outside the project artifacts directory."
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

    # Orphan pruning: only symlinks, not regular files
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
            f"Entry '{e.entry}' resolves to {e.resolved_path} which is outside the warehouse."
        ) from e
    except DestinationOutsideArtifactsError as e:
        raise BeaconSyncError(
            f"Sync aborted: {e}\n"
            f"Entry '{e.entry}' would write to {e.resolved_path}, outside the project artifacts directory."
        ) from e

    if not dry_run:
        gitignore_mgr = GitignoreManager(project_root)
        gitignore_mgr.ensure_entries()

    # Post-sync wiring
    oc_added: list[str] = []
    cc_added: list[str] = []
    wired_skills: list[str] = []
    wire_errors: list[str] = []
    wiring_notes: list[str] = []
    agent_config_init_needed = False

    if summary.pruned_paths and not dry_run:
        unwire_pruned_artifacts(project_root, summary.pruned_paths, artifacts_dir)

    if beacon_settings.artifacts.contexts and not dry_run:
        oc_added = wire_contexts_opencode(project_root, artifacts_dir)
        cc_added = wire_contexts_claudecode(project_root, artifacts_dir)

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
                if not dry_run:
                    agent_config_init_needed = True
                else:
                    wiring_notes.append(
                        "  Contexts synced — wire them into your agent config:\n"
                        '  [bold]opencode.json[/bold] → add to "instructions" array:\n'
                        '    ".agentic-beacon/artifacts/contexts/<name>.md"\n'
                        "  [bold]CLAUDE.md[/bold] → add a line per context:\n"
                        "    @.agentic-beacon/artifacts/contexts/<name>.md"
                    )

    if beacon_settings.artifacts.contexts and dry_run:
        wiring_notes.append(
            "  Contexts would be synced — wire them into your agent config if needed:\n"
            '  [bold]opencode.json[/bold] → add to "instructions" array:\n'
            '    ".agentic-beacon/artifacts/contexts/<name>.md"\n'
            "  [bold]CLAUDE.md[/bold] → add a line per context:\n"
            "    @.agentic-beacon/artifacts/contexts/<name>.md"
        )

    if beacon_settings.artifacts.skills and not dry_run:
        wired_skills, wire_errors = wire_skills_post_sync(
            project_root,
            artifacts_dir,
            force=force,
            skill_conflict_callback=skill_conflict_callback,
        )
        update_agent_gitignores(project_root)

    if not dry_run:
        bundled_installed, bundled_skipped = install_bundled_skills_globally()
        bundled_wired, bundled_wire_errors = wire_bundled_skills_per_project(
            project_root
        )
        wired_skills = wired_skills + bundled_wired
        wire_errors = wire_errors + bundled_wire_errors
        sync_agents_from_warehouse(warehouse_path, force=force)
    else:
        bundled_installed, bundled_skipped = [], []

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
        no_artifacts=False,
        agent_config_init_needed=agent_config_init_needed,
        project_root=project_root,
        artifacts_dir=artifacts_dir,
        warehouse_path=warehouse_path,
        wiring_notes=wiring_notes,
        migration_resolved=migration_resolved,
        unresolved_files=unresolved_files,
    )
