"""Artifact adoption apply logic for the abc adopt command.

Provides:
- apply_adoption(): update beacon.yaml with selected/removed artifacts
- commit_session(): session-atomic commit with rollback for the unified
  warehouse-browser + pending-TODO flow
- CommitError: raised on mid-commit failure after rollback
- cleanup_unadopted_artifacts(): prompt to remove local artifact symlinks for unadopted entries
- warehouse_uncommitted_paths(): return set of relative paths with uncommitted changes
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

from beacon.core.manifest.pending import PendingEntry
from beacon.domains.adoption.models import AdoptCandidate

# ─────────────────────────────────────────────────────────────
# Commit error
# ─────────────────────────────────────────────────────────────


class CommitError(Exception):
    """Raised when a session commit fails mid-transaction.

    Both tracked files (beacon.yaml, pending.yaml) are restored to their
    pre-commit state before this exception propagates.
    """

    def __init__(self, message: str, failed_entry: str | None = None) -> None:
        self.failed_entry = failed_entry
        super().__init__(message)


# ─────────────────────────────────────────────────────────────
# Public API: beacon.yaml update
# ─────────────────────────────────────────────────────────────


def apply_adoption(
    beacon_yaml_path: Path,
    selections: list[AdoptCandidate],
    unadoptions: list[str] | None = None,
) -> None:
    """Update beacon.yaml — append selected artifacts and remove unadopted ones.

    Skills are normalised to directory form with trailing slash.
    Duplicate additions are silently skipped.
    """
    if not selections and not unadoptions:
        return

    from beacon.core.manifest.beacon import BeaconManifest

    beacon_settings = BeaconManifest.from_yaml(beacon_yaml_path)

    for candidate in selections:
        if candidate.artifact_type == "agents":
            if candidate.path not in beacon_settings.artifacts.agents:
                beacon_settings.artifacts.agents.append(candidate.path)
        elif candidate.artifact_type == "contexts":
            if candidate.path not in beacon_settings.artifacts.contexts:
                beacon_settings.artifacts.contexts.append(candidate.path)
        elif candidate.artifact_type == "skills":
            skill_path = candidate.path
            if not skill_path.endswith("/"):
                skill_path = skill_path + "/"
            if skill_path not in beacon_settings.artifacts.skills:
                beacon_settings.artifacts.skills.append(skill_path)

    for path in unadoptions or []:
        norm = path.rstrip("/")
        beacon_settings.artifacts.contexts = [
            p for p in beacon_settings.artifacts.contexts if p.rstrip("/") != norm
        ]
        beacon_settings.artifacts.skills = [
            p for p in beacon_settings.artifacts.skills if p.rstrip("/") != norm
        ]
        beacon_settings.artifacts.agents = [
            p for p in beacon_settings.artifacts.agents if p.rstrip("/") != norm
        ]

    beacon_settings.to_yaml(beacon_yaml_path)


# ─────────────────────────────────────────────────────────────
# Pending-session atomic commit
# ─────────────────────────────────────────────────────────────

_BEACON_ARTIFACT_TYPES = frozenset({"contexts", "skills", "agents"})


def _default_symlink_sync(
    artifact_paths: list[str],
    *,
    warehouse_path: Path,
    artifacts_path: Path,
) -> None:
    """Sync symlinks for the given artifact paths using SyncEngine."""
    from beacon.domains.distribution.sync_engine import SyncEngine

    sync_engine = SyncEngine(
        warehouse_path=warehouse_path, artifacts_path=artifacts_path
    )

    expanded: list[str] = []
    for path in artifact_paths:
        if path.endswith("/"):
            matches = sync_engine.expand_glob(f"{path.rstrip('/')}/**/*")
            expanded.extend(matches)
        else:
            expanded.append(path)

    if expanded:
        summary = sync_engine.sync_all(artifact_paths=expanded, dry_run=False)
        if summary.errors > 0:
            failed = ", ".join(f for f, _ in summary.failed_files[:3])
            raise RuntimeError(f"Sync errors: {failed}")


_PENDING_TYPE_TO_ARTIFACT_TYPE: dict[str, str] = {
    "skill": "skills",
    "context": "contexts",
    "agent": "agents",
}


def _candidate_from_pending_entry(entry: PendingEntry) -> AdoptCandidate:
    """Build an AdoptCandidate from a PendingEntry for beacon.yaml updates."""
    return AdoptCandidate(
        artifact_type=_PENDING_TYPE_TO_ARTIFACT_TYPE.get(entry.type, entry.type),
        path=entry.path,
        description="",
    )


def commit_session(
    *,
    to_adopt: list[str],
    to_unadopt: list[str],
    pending_accept: list[str],
    pending_reject: list[str],
    candidates: list[AdoptCandidate],
    pending_entries: list[PendingEntry],
    project_root: Path,
    warehouse_path: Path,
    artifacts_path: Path,
    beacon_yaml_path: Path,
    _symlink_sync_fn: Callable[..., None] | None = None,
    _post_sync_wiring_fn: Callable[..., None] | None = None,
    _unlink_fn: Callable[[Path], None] | None = None,
) -> None:
    """Atomically commit a unified adopt session (warehouse browser + pending TODO).

    Two flows are merged into a single transaction:
    - Warehouse browser: *to_adopt* paths are added to beacon.yaml; *to_unadopt*
      are removed.
    - Pending TODO: *pending_accept* paths are added to beacon.yaml AND removed
      from pending.yaml; *pending_reject* paths are removed from pending.yaml only.
      Pending entries not in either list stay in pending.yaml (deferred).

    On any failure mid-commit both beacon.yaml and pending.yaml are restored
    to their pre-commit state and CommitError is raised.

    Args:
        to_adopt: Warehouse browser paths to adopt into beacon.yaml.
        to_unadopt: Warehouse browser paths to remove from beacon.yaml.
        pending_accept: Pending paths to adopt + remove from pending.yaml.
        pending_reject: Pending paths to remove from pending.yaml only.
        candidates: Warehouse browser candidates (for artifact_type lookup).
        pending_entries: Current pending.yaml entries (for type lookup).
        project_root: Project root (contains .agentic-beacon/).
        warehouse_path: Warehouse root for symlink targets.
        artifacts_path: Project artifact directory (.agentic-beacon/artifacts/).
        beacon_yaml_path: Path to beacon.yaml.
        _symlink_sync_fn: Injectable sync function for testing rollback scenarios.
        _post_sync_wiring_fn: Injectable post-sync wiring hook for testing.
        _unlink_fn: Injectable unlink callable for testing reject rollback scenarios;
            defaults to Path.unlink. Production code never passes this.
    """
    from beacon.core.manifest.pending import PendingManifest

    ab = project_root / ".agentic-beacon"
    pending_path = ab / "pending.yaml"

    # Pre-commit snapshot of the two tracked files
    pre_beacon = beacon_yaml_path.read_bytes() if beacon_yaml_path.exists() else b""
    pre_pending = pending_path.read_bytes() if pending_path.exists() else b""

    candidate_map = {c.path: c for c in candidates}
    pending_map = {e.path: e for e in pending_entries}

    # Build the AdoptCandidate list for beacon.yaml updates: warehouse adopts
    # + pending accepts. Skip paths that don't resolve (defensive).
    beacon_adds: list[AdoptCandidate] = []
    for path in to_adopt:
        c = candidate_map.get(path)
        if c is not None and c.artifact_type in _BEACON_ARTIFACT_TYPES:
            beacon_adds.append(c)
    for path in pending_accept:
        e = pending_map.get(path)
        if e is None:
            continue
        beacon_adds.append(_candidate_from_pending_entry(e))

    # Sync needs the union of all newly-adopted paths
    paths_to_sync = [c.path for c in beacon_adds]

    # New pending.yaml: keep entries that were neither accepted nor rejected
    pending_resolved = set(pending_accept) | set(pending_reject)
    new_pending_entries = [e for e in pending_entries if e.path not in pending_resolved]

    sync_fn = _symlink_sync_fn or _default_symlink_sync

    # Accumulators for filesystem rollback (Bug 2 fix)
    created_paths: list[Path] = []
    removed_paths_with_target: list[tuple[Path, Path]] = []
    # Per-path pre-state snapshot for tool symlinks; reconciled on rollback.
    # Each entry: (path, kind, prior_target) where kind is "missing"/"symlink"/"regular_file".
    tool_snapshots: list[tuple[Path, str, Path | None]] = []

    def _snapshot_path(p: Path) -> tuple[str, Path | None]:
        """Capture pre-state of a path for rollback restoration."""
        if p.is_symlink():
            return ("symlink", p.readlink())
        if p.exists():
            return ("regular_file", None)
        return ("missing", None)

    def _default_post_sync_wiring(beacon_adds: list[AdoptCandidate]) -> None:
        # `beacon_adds` is the union of candidates being added to beacon.yaml:
        # both the to_adopt set and the pending-accept set (filtered to beacon
        # artifact types). Not the full session result.
        has_contexts = any(c.artifact_type == "contexts" for c in beacon_adds)
        has_skills = any(c.artifact_type == "skills" for c in beacon_adds)
        agent_candidates = [c for c in beacon_adds if c.artifact_type == "agents"]

        if has_contexts:
            from beacon.domains.setup.wiring import (
                wire_contexts_claudecode,
                wire_contexts_opencode,
            )

            wire_contexts_opencode(project_root, artifacts_path)
            wire_contexts_claudecode(project_root, artifacts_path)

        if has_skills:
            from beacon.domains.artifact.skill import wire_skills_post_sync

            wire_skills_post_sync(project_root, artifacts_path)

        if agent_candidates:
            from beacon.domains.artifact.agent import (
                detect_agent_targets,
                ensure_agent_dirs_gitignored,
            )
            from beacon.domains.setup.wiring import (
                wire_agent_claudecode,
                wire_agent_opencode,
            )

            detected_tools = detect_agent_targets(project_root)
            for candidate in agent_candidates:
                artifact_file = artifacts_path / candidate.path
                leaf = artifact_file.name
                if "claudecode" in detected_tools:
                    cc_dest = project_root / ".claude" / "agents" / leaf
                    kind, prior = _snapshot_path(cc_dest)
                    tool_snapshots.append((cc_dest, kind, prior))
                    wire_agent_claudecode(project_root, artifact_file)
                if "opencode" in detected_tools:
                    oc_dest = project_root / ".opencode" / "agents" / leaf
                    kind, prior = _snapshot_path(oc_dest)
                    tool_snapshots.append((oc_dest, kind, prior))
                    wire_agent_opencode(project_root, artifact_file)

            # PER-113 (Finding 2): ensure root .gitignore has agent dir entries
            ensure_agent_dirs_gitignored(project_root)

    post_sync_wiring_fn = _post_sync_wiring_fn or _default_post_sync_wiring

    def _rollback() -> None:
        """Restore beacon.yaml, pending.yaml, and filesystem state to pre-commit."""
        if pre_beacon:
            beacon_yaml_path.write_bytes(pre_beacon)
        elif beacon_yaml_path.exists():
            beacon_yaml_path.unlink()
        if pre_pending:
            pending_path.write_bytes(pre_pending)
        elif pending_path.exists():
            pending_path.unlink()
        for path in created_paths:
            if path.is_symlink() or path.exists():
                path.unlink()
        for path, target in removed_paths_with_target:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.symlink_to(target)
        for path, kind, prior_target in tool_snapshots:
            if kind == "missing":
                if path.is_symlink() or path.exists():
                    path.unlink()
            elif kind == "symlink":
                if path.is_symlink():
                    if path.readlink() != prior_target:
                        path.unlink()
                        path.symlink_to(prior_target)
                else:
                    if path.exists():
                        path.unlink()
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.symlink_to(prior_target)

    try:
        # 1. Update beacon.yaml — add adopts + pending accepts, remove unadopts.
        if beacon_adds or to_unadopt:
            apply_adoption(
                beacon_yaml_path, beacon_adds, unadoptions=list(to_unadopt) or None
            )

        # 2. Sync symlinks per accepted path (one call per path for testability).
        for path in paths_to_sync:
            artifact_link = artifacts_path / path
            existed_before = artifact_link.is_symlink() or artifact_link.exists()
            try:
                sync_fn(
                    [path],
                    warehouse_path=warehouse_path,
                    artifacts_path=artifacts_path,
                )
            except Exception as exc:
                raise CommitError(
                    f"Symlink sync failed for '{path}': {exc}",
                    failed_entry=path,
                ) from exc
            if not existed_before and (
                artifact_link.is_symlink() or artifact_link.exists()
            ):
                created_paths.append(artifact_link)

        if beacon_adds:
            post_sync_wiring_fn(beacon_adds)

        # 2b. Unwire project-local tool symlinks for unadopted agents (Bug 1 + 2 fix).
        agent_unadoptions = [p for p in to_unadopt if p.startswith("agents/")]
        if agent_unadoptions:
            from beacon.domains.setup.wiring import unwire_agent_with_undo

            unlink_fn: Callable[[Path], None] = _unlink_fn or Path.unlink

            for agent_path in agent_unadoptions:
                agent_name = Path(agent_path).stem
                leaf = Path(agent_path).name

                # Pre-snapshot all 3 symlinks before any removal so _rollback()
                # can restore them even if unwire_agent_with_undo fails mid-operation.
                for p in (
                    project_root / ".claude" / "agents" / leaf,
                    project_root / ".opencode" / "agents" / leaf,
                    artifacts_path / agent_path,
                ):
                    kind, prior = _snapshot_path(p)
                    tool_snapshots.append((p, kind, prior))

                removed = unwire_agent_with_undo(
                    project_root, agent_name, _unlink_fn=_unlink_fn
                )
                removed_paths_with_target.extend(removed)

                # Bug 1 fix: also remove the artifact symlink atomically
                artifact_symlink = artifacts_path / agent_path
                if artifact_symlink.is_symlink():
                    target = artifact_symlink.readlink()
                    unlink_fn(artifact_symlink)
                    removed_paths_with_target.append((artifact_symlink, target))
                elif artifact_symlink.exists():
                    unlink_fn(artifact_symlink)

        # 3. Rewrite pending.yaml (drop accepted + rejected; keep deferred).
        if pending_resolved or pre_pending:
            new_manifest = PendingManifest(pending=new_pending_entries)
            new_manifest.to_yaml(pending_path)

    except CommitError:
        _rollback()
        raise
    except Exception as exc:
        _rollback()
        raise CommitError(f"Commit failed: {exc}") from exc


def warehouse_uncommitted_paths(warehouse_path: Path) -> set[str]:
    """Return relative paths of files with uncommitted changes in the warehouse."""
    result = subprocess.run(
        ["git", "-C", str(warehouse_path), "status", "--porcelain"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    paths: set[str] = set()
    for line in result.stdout.splitlines():
        if len(line) >= 3:
            paths.add(line[3:].strip())
    return paths


def cleanup_unadopted_artifacts(
    unadoptions: list[str],
    artifacts_dir: Path,
    warehouse_path: Path,
    *,
    project_root: Path | None = None,
) -> None:
    """Prompt to remove local artifact symlinks for unadopted entries.

    Always requires confirmation.

    When project_root is provided, skill unadoptions also remove live agent
    copies under .opencode/skills/<name>/ and .claude/skills/<name>/.
    """
    import click
    from rich.console import Console

    from beacon.domains.setup.wiring import unwire_agent

    console = Console()

    to_remove: list[tuple[str, Path]] = []

    for entry in unadoptions:
        entry_clean = entry.rstrip("/")

        if entry_clean.startswith("agents/"):
            # PER-113: unwire project-local agent symlinks on unadopt
            if project_root is not None:
                agent_name = Path(entry_clean).stem
                unwire_agent(project_root, agent_name)
            # Also fall through to remove the artifact symlink
            local_entry = artifacts_dir / entry_clean
            if local_entry.is_file() or local_entry.is_symlink():
                rel = str(local_entry.relative_to(artifacts_dir))
                to_remove.append((rel, local_entry))
            continue

        local_entry = artifacts_dir / entry_clean

        if local_entry.is_dir():
            for f in local_entry.rglob("*"):
                if not f.is_file():
                    continue
                rel = str(f.relative_to(artifacts_dir))
                to_remove.append((rel, f))
        elif local_entry.is_file():
            rel = str(local_entry.relative_to(artifacts_dir))
            to_remove.append((rel, local_entry))

        parts = entry_clean.split("/")
        if project_root is not None and len(parts) >= 2 and parts[0] == "skills":
            from beacon.domains.artifact.skill import build_skills_paths

            skill_name = parts[1]
            for agent, live_skills_root in build_skills_paths(project_root).items():
                live_skill_dir = live_skills_root / skill_name
                if not live_skill_dir.is_dir():
                    continue
                for f in live_skill_dir.rglob("*"):
                    if not f.is_file():
                        continue
                    rel_within_skill = f.relative_to(live_skill_dir)
                    display_label = str(
                        Path(".opencode" if agent == "opencode" else ".claude")
                        / "skills"
                        / skill_name
                        / rel_within_skill
                    )
                    to_remove.append((display_label, f))

    if not to_remove:
        return

    symlink_count = sum(1 for _, path in to_remove if path.is_symlink())
    file_count = len(to_remove) - symlink_count

    if symlink_count > 0 and file_count == 0:
        noun = "symlink"
        action = "unlink"
    elif symlink_count > 0 and file_count > 0:
        noun = "reference"
        action = "remove"
    else:
        noun = "file"
        action = "delete"

    console.print()
    console.print(f"[bold]Local artifact {noun}s to {action}:[/bold]")
    for rel, _ in sorted(to_remove):
        console.print(f"  {rel}")

    confirmed = click.confirm(
        f"\n{action.capitalize()} {len(to_remove)} local {noun}(s)?", default=False
    )
    if not confirmed:
        console.print("[dim]Skipped cleanup.[/dim]")
        return

    removed = 0
    for _, path in to_remove:
        try:
            path.unlink()
            removed += 1
        except OSError:
            pass

    live_skill_roots: list[Path] = []
    if project_root is not None:
        from beacon.domains.artifact.skill import build_skills_paths

        for live_skills_root in build_skills_paths(project_root).values():
            for entry in unadoptions:
                entry_clean = entry.rstrip("/")
                parts = entry_clean.split("/")
                if len(parts) >= 2 and parts[0] == "skills":
                    live_skill_roots.append(live_skills_root / parts[1])

    for _, path in to_remove:
        for parent in path.parents:
            if parent == artifacts_dir:
                break
            if any(parent == r for r in live_skill_roots):
                break
            try:
                parent.rmdir()
            except OSError:
                break

    for live_skill_dir in live_skill_roots:
        try:
            live_skill_dir.rmdir()
        except OSError:
            pass

    console.print(f"[green]✓[/green] {action.capitalize()}ed {removed} {noun}(s).")
