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
from beacon.core.manifest.workspace import WorkspaceConfig
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
from beacon.domains.distribution.state import read_sync_sha, write_sync_state
from beacon.domains.distribution.sync_engine import (
    OrphanInfo,
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
from beacon.utils.interaction import ConflictResolution, resolve_conflict


@dataclass
class SyncOrchestrationResult:
    """Result returned by run_sync()."""

    dry_run: bool
    summary: SyncSummary
    artifact_paths: list[str]
    conflicts: list[str]
    orphans: list[OrphanInfo]
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


def run_sync(
    project_root: Path | None = None,
    *,
    preserve: bool = False,
    force: bool = False,
    verbose: bool = False,
    dry_run: bool = False,
    skip_git_check: bool = False,
    log_fn: Callable[[str], None] | None = None,
) -> SyncOrchestrationResult:
    """Run the full sync pipeline.

    Raises BeaconSyncError or other exceptions on fatal issues;
    callers should catch and format output.
    """
    project_root = project_root or find_project_root()
    beacon_dir = project_root / ".agentic-beacon"

    if not beacon_dir.exists():
        raise BeaconSyncError(
            "No .agentic-beacon directory found.\n"
            "Run 'abc warehouse connect' to connect to a warehouse first."
        )

    config_file = beacon_dir / "config.toml"
    if not config_file.exists():
        raise BeaconSyncError(
            "No warehouse connected.\n"
            "Run 'abc warehouse connect --path <warehouse>' first."
        )

    beacon_yaml = beacon_dir / "beacon.yaml"
    if not beacon_yaml.exists():
        raise BeaconSyncError(
            "No beacon.yaml found.\nRun 'abc setup' to create artifact configuration."
        )

    warehouse_settings = WorkspaceConfig()
    warehouse_path = Path(warehouse_settings.warehouse.local_path)

    if not warehouse_path.exists():
        raise BeaconSyncError(
            f"Warehouse path no longer exists: {warehouse_path}\n"
            "The warehouse may have been moved or deleted.\n"
            "Run 'abc warehouse connect --path <warehouse>' to reconnect."
        )

    if not dry_run and not skip_git_check:
        git_result = check_warehouse_git_clean(warehouse_path)
        if not git_result.ok:
            raise BeaconSyncError(git_result.error_message, hint=git_result.hint)

    if not dry_run and not skip_git_check:
        branch_result = check_warehouse_on_main_branch(warehouse_path)
        if not branch_result.ok:
            raise BeaconSyncError(branch_result.error_message, hint=branch_result.hint)

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
        bundled_installed, bundled_skipped = install_bundled_skills_globally()
        if not dry_run:
            bundled_wired, bundled_wire_errors = wire_bundled_skills_per_project(
                project_root
            )
        else:
            bundled_wired, bundled_wire_errors = [], []
        sync_agents_from_warehouse(warehouse_path, force=force, preserve=preserve)
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

    old_sync_sha = read_sync_sha(artifacts_dir)

    if not dry_run:
        write_sync_state(artifacts_dir, warehouse_path)

    if not dry_run:
        conflicts = sync_engine.classify_conflicts(artifact_paths)
        resolution = resolve_conflict(
            force=force, preserve=preserve, has_conflicts=bool(conflicts)
        )
        if resolution == ConflictResolution.SKIP:
            preserve = True
        elif resolution == ConflictResolution.NEEDS_CONFIRMATION:
            raise BeaconSyncError(
                f"{len(conflicts)} file(s) have local changes that differ from the warehouse:\n"
                + "\n".join(f"  • {p}" for p in conflicts)
                + "\n\nNon-interactive mode — cannot prompt for overwrite.",
                hint="Use --force to overwrite or --preserve to skip conflicting files.",
            )
    else:
        conflicts = []

    orphans = sync_engine.classify_orphans(artifact_paths)
    confirmed_prune: list[str] = []
    if orphans:
        confirmed_prune = confirm_prune(orphans, dry_run=dry_run)

    summary = sync_engine.sync_all(
        artifact_paths=artifact_paths,
        preserve=preserve,
        paths_to_prune=confirmed_prune if not dry_run else None,
        verbose=verbose,
        dry_run=dry_run,
        log_fn=log_fn,
    )

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

    if beacon_settings.artifacts.contexts:
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

    if beacon_settings.artifacts.skills:
        wired_skills, wire_errors = wire_skills_post_sync(
            project_root, artifacts_dir, force=force, preserve=preserve
        )
        if not dry_run:
            update_agent_gitignores(project_root)

    bundled_installed, bundled_skipped = install_bundled_skills_globally()
    if not dry_run:
        bundled_wired, bundled_wire_errors = wire_bundled_skills_per_project(
            project_root
        )
        wired_skills = wired_skills + bundled_wired
        wire_errors = wire_errors + bundled_wire_errors

    sync_agents_from_warehouse(warehouse_path, force=force, preserve=preserve)

    adoption_notification = None
    if old_sync_sha is not None:
        try:
            unadopted_count = count_unadopted_since(
                warehouse_path, beacon_settings, old_sync_sha
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
        conflicts=conflicts,
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
    )
