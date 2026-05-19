"""Warehouse contribute domain logic.

Encapsulates git add + git commit inside the warehouse clone,
driven by a project's .agentic-beacon/config.toml and beacon.yaml.
"""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from beacon.domains.warehouse._tracked_paths import get_tracked_paths
from beacon.domains.warehouse.preconditions import ensure_sync_ready


@dataclass
class ContributeResult:
    """Result of a warehouse contribute operation."""

    status: str  # "committed", "no_changes", "push_failed"
    committed_sha: str | None = None
    message: str | None = None
    dirty_outside_scope_count: int = 0


def _run_git(
    warehouse_path: Path, args: list[str], timeout: int = 30
) -> subprocess.CompletedProcess:
    """Run a git command in the warehouse directory."""
    return subprocess.run(
        ["git", "-C", str(warehouse_path), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _normalize_path(path: str) -> str:
    """Normalize a user-supplied warehouse-relative path for membership checking.

    * Converts to POSIX-style forward slashes.
    * Removes leading './' segments.
    * Collapses redundant separators (e.g. 'skills//foo' -> 'skills/foo').
    * Rejects absolute paths and parent-directory traversal.
    """
    p = Path(path)
    if p.is_absolute():
        raise ValueError(f"Absolute paths are not allowed: {path!r}")
    parts = p.parts
    if ".." in parts:
        raise ValueError(f"Parent-directory traversal is not allowed: {path!r}")
    # normpath removes './' and collapses redundant separators
    normalized = os.path.normpath(path)
    # Ensure POSIX-style forward slashes for cross-platform consistency
    normalized = normalized.replace(os.sep, "/")
    return normalized


def _count_dirty_outside_scope(warehouse_path: Path, tracked: list[str]) -> int:
    """Return number of dirty files outside the tracked set."""
    full = _run_git(warehouse_path, ["status", "--porcelain"])
    if full.returncode != 0:
        return 0
    total_lines = len([ln for ln in full.stdout.splitlines() if ln.strip()])
    filtered = _run_git(warehouse_path, ["status", "--porcelain", "--", *tracked])
    filtered_lines = (
        len([ln for ln in filtered.stdout.splitlines() if ln.strip()])
        if filtered.returncode == 0
        else 0
    )
    return max(0, total_lines - filtered_lines)


def contribute(
    project_root: Path,
    *,
    message: str,
    push: bool = False,
    paths: tuple[str, ...] | None = None,
) -> ContributeResult:
    """Contribute local changes to the warehouse.

    Stages and commits files tracked by beacon.yaml that have uncommitted
    changes in the warehouse working tree.

    Args:
        project_root: Path to the project root.
        message: Commit message (must be non-empty).
        push: Whether to push after committing.
        paths: Optional tuple of warehouse-relative paths to restrict the commit
            to. When None (the default), all beacon.yaml-tracked dirty paths are
            committed (existing behaviour). When provided, every path must be a
            member of the beacon.yaml-tracked set; paths outside that set raise
            ValueError. An empty tuple is rejected — omit the argument to commit
            all tracked paths.

    Returns:
        ContributeResult indicating the outcome.
    """
    if not message or not message.strip():
        raise ValueError("Commit message cannot be empty")

    if paths is not None and len(paths) == 0:
        raise ValueError(
            "--paths must not be empty when provided; omit the flag to commit all tracked paths"
        )

    warehouse_path, _ = ensure_sync_ready(project_root)

    beacon_yaml = project_root / ".agentic-beacon" / "beacon.yaml"
    tracked_paths = get_tracked_paths(warehouse_path, beacon_yaml)

    if paths is not None:
        normalized_paths = [_normalize_path(p) for p in paths]
        tracked_set = set(tracked_paths)
        untracked = [p for p in normalized_paths if p not in tracked_set]
        if untracked:
            raise ValueError(
                f"The following paths are not tracked by beacon.yaml and cannot be committed: "
                f"{', '.join(repr(p) for p in untracked)}"
            )
        # Use the caller-supplied paths (preserving their order), scoped within tracked_paths
        commit_paths = normalized_paths
    else:
        commit_paths = tracked_paths

    if not commit_paths:
        count = (
            _count_dirty_outside_scope(warehouse_path, tracked_paths)
            if paths is None
            else 0
        )
        return ContributeResult(status="no_changes", dirty_outside_scope_count=count)

    # Check git status for the paths we intend to commit
    status_result = _run_git(
        warehouse_path, ["status", "--porcelain", "--", *commit_paths]
    )
    if not status_result.stdout.strip():
        count = (
            _count_dirty_outside_scope(warehouse_path, tracked_paths)
            if paths is None
            else 0
        )
        return ContributeResult(status="no_changes", dirty_outside_scope_count=count)

    # Stage the paths we intend to commit
    _run_git(warehouse_path, ["add", "--", *commit_paths])

    # Commit
    commit_result = _run_git(
        warehouse_path, ["commit", "-m", message, "--", *commit_paths]
    )
    if commit_result.returncode != 0:
        logger.error("Git commit failed: {}", commit_result.stderr)
        raise RuntimeError(
            f"Git commit failed in warehouse: {commit_result.stderr.strip()}"
        )

    # Get the committed SHA
    sha_result = _run_git(warehouse_path, ["rev-parse", "HEAD"])
    committed_sha = sha_result.stdout.strip() if sha_result.returncode == 0 else None

    if push:
        push_result = _run_git(warehouse_path, ["push"])
        if push_result.returncode != 0:
            return ContributeResult(
                status="push_failed",
                committed_sha=committed_sha,
                message=push_result.stderr,
            )

    return ContributeResult(
        status="committed",
        committed_sha=committed_sha,
        message=message,
    )
