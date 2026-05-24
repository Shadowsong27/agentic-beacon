"""Warehouse contribute domain logic.

Encapsulates git add + git commit inside the warehouse clone. By default
(PER-203), accepts any dirty path in the warehouse working tree — the
invariant is "is this a real dirty warehouse path?", not "is this in the
invoking project's beacon.yaml?". Pass ``only_tracked=True`` to restore the
legacy beacon.yaml-filtered behavior.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from beacon.domains.warehouse._tracked_paths import get_tracked_paths
from beacon.domains.warehouse.preconditions import ensure_sync_ready
from beacon.utils.paths import normalize_relative_path


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


def _has_any_dirty_path(warehouse_path: Path) -> bool:
    """Return True iff the warehouse working tree contains at least one dirty path.

    Used as a non-empty-changes gate for the default-mode commit. The actual
    staging path uses ``git add -A`` directly, so we no longer need to
    enumerate or parse porcelain entries here.
    """
    full = _run_git(warehouse_path, ["status", "--porcelain", "--untracked-files=all"])
    if full.returncode != 0:
        return False
    return any(line.strip() for line in full.stdout.splitlines())


def _expand_rename_sources(warehouse_path: Path, user_paths: list[str]) -> list[str]:
    """For each user path that is the destination of a rename or copy, also
    include the source path in the returned list.

    Porcelain reports renames as ``R  old -> new`` and copies as ``C  old ->
    new``. When the caller asks to commit only ``new``, git would commit the
    new file but leave the old-side deletion staged. Including both sides in
    the pathspec keeps the commit atomic.

    The source path appears immediately after its destination in the returned
    list to keep ordering predictable. Duplicate sources (when multiple
    destinations map to the same source — unusual but valid for copies) are
    only added once.
    """
    rc, stdout, _ = _run_git_inner(
        warehouse_path, ["status", "--porcelain", "--untracked-files=all"]
    )
    if rc != 0:
        return user_paths

    rename_sources_by_dest: dict[str, str] = {}
    for line in stdout.splitlines():
        if len(line) < 4:
            continue
        code = line[:2]
        rest = line[3:]
        # Gate the ' -> ' split on R/C status codes (PR#156 M2 lesson).
        if code[0] in ("R", "C") and " -> " in rest:
            src, dst = rest.split(" -> ", 1)
            rename_sources_by_dest[dst] = src

    expanded: list[str] = []
    seen: set[str] = set()
    for p in user_paths:
        if p not in seen:
            expanded.append(p)
            seen.add(p)
        src = rename_sources_by_dest.get(p)
        if src and src not in seen:
            expanded.append(src)
            seen.add(src)
    return expanded


def _run_git_inner(
    warehouse_path: Path, args: list[str], timeout: int = 30
) -> tuple[int, str, str]:
    """Internal git runner returning a (rc, stdout, stderr) tuple."""
    result = subprocess.run(
        ["git", "-C", str(warehouse_path), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


def _validate_dirty(warehouse_path: Path, candidate_paths: list[str]) -> None:
    """Raise ValueError if any candidate path has no porcelain status.

    A path is acceptable when ``git status --porcelain -- <path>`` returns a
    non-empty line. This covers modified (M), added (A), untracked (??),
    deleted (D), renamed (R), and copied (C) — i.e. anything dirty in the
    warehouse working tree.
    """
    not_dirty: list[str] = []
    for p in candidate_paths:
        status = _run_git(warehouse_path, ["status", "--porcelain", "--", p])
        if status.returncode != 0 or not status.stdout.strip():
            not_dirty.append(p)
    if not_dirty:
        raise ValueError(
            "The following paths are not dirty in the warehouse working tree "
            "(no uncommitted change) and cannot be committed: "
            f"{', '.join(repr(p) for p in not_dirty)}"
        )


def contribute(
    project_root: Path,
    *,
    message: str,
    push: bool = False,
    paths: tuple[str, ...] | None = None,
    only_tracked: bool = False,
) -> ContributeResult:
    """Contribute local changes to the warehouse.

    Stages and commits dirty paths in the warehouse working tree.

    Args:
        project_root: Path to the project root (used to resolve the connected
            warehouse via ``.agentic-beacon/config.toml``).
        message: Commit message (must be non-empty).
        push: Whether to push after committing.
        paths: Optional tuple of warehouse-relative paths to restrict the commit
            to. When None (the default), every dirty path in the warehouse
            working tree is committed.
        only_tracked: When True, restore the legacy project-scoped invariant —
            commits are restricted to paths declared in the invoking project's
            ``beacon.yaml`` and out-of-scope paths in ``paths`` raise
            ValueError. When False (the default, PER-203), any dirty warehouse
            path is acceptable, including brand-new artifacts and cross-project
            knowledge that no ``beacon.yaml`` lists.

    Returns:
        ContributeResult indicating the outcome.
    """
    if not message or not message.strip():
        raise ValueError("Commit message cannot be empty")

    if paths is not None and len(paths) == 0:
        raise ValueError(
            "--paths must not be empty when provided; omit the flag to commit all dirty paths"
        )

    warehouse_path, _ = ensure_sync_ready(project_root)

    if only_tracked:
        beacon_yaml = project_root / ".agentic-beacon" / "beacon.yaml"
        tracked_paths = get_tracked_paths(warehouse_path, beacon_yaml)

        if paths is not None:
            normalized_paths = [normalize_relative_path(p) for p in paths]
            tracked_set = set(tracked_paths)
            untracked = [p for p in normalized_paths if p not in tracked_set]
            if untracked:
                raise ValueError(
                    "The following paths are not tracked by beacon.yaml and cannot be committed: "
                    f"{', '.join(repr(p) for p in untracked)}"
                )
            commit_paths = normalized_paths
        else:
            commit_paths = tracked_paths

        if not commit_paths:
            count = (
                _count_dirty_outside_scope(warehouse_path, tracked_paths)
                if paths is None
                else 0
            )
            return ContributeResult(
                status="no_changes", dirty_outside_scope_count=count
            )
    else:
        # PER-203 default: warehouse-scoped — accept any dirty warehouse path.
        if paths is not None:
            normalized_paths = [normalize_relative_path(p) for p in paths]
            _validate_dirty(warehouse_path, normalized_paths)
            # If any user path is the destination of a rename, transparently
            # include the source so the commit captures both sides (PR#156
            # round-2 review). Without this, `git commit -- dest` would
            # commit the new file but leave the old-side deletion staged.
            commit_paths = _expand_rename_sources(warehouse_path, normalized_paths)
        else:
            # paths=None: commit the entire working tree. We deliberately do
            # NOT enumerate-then-restrict here — `git add -A` + an unrestricted
            # commit handles renames (R old -> new) and deletions correctly,
            # whereas an explicit pathspec list silently drops one side of a
            # rename and is fragile against unusual filenames.
            if not _has_any_dirty_path(warehouse_path):
                return ContributeResult(status="no_changes")
            _run_git(warehouse_path, ["add", "-A"])
            commit_result = _run_git(warehouse_path, ["commit", "-m", message])
            if commit_result.returncode != 0:
                logger.error("Git commit failed: {}", commit_result.stderr)
                raise RuntimeError(
                    f"Git commit failed in warehouse: {commit_result.stderr.strip()}"
                )
            sha_result = _run_git(warehouse_path, ["rev-parse", "HEAD"])
            committed_sha = (
                sha_result.stdout.strip() if sha_result.returncode == 0 else None
            )
            if push:
                push_result = _run_git(warehouse_path, ["push"])
                if push_result.returncode != 0:
                    return ContributeResult(
                        status="push_failed",
                        committed_sha=committed_sha,
                        message=push_result.stderr,
                    )
            return ContributeResult(
                status="committed", committed_sha=committed_sha, message=message
            )

    # Check git status for the paths we intend to commit
    status_result = _run_git(
        warehouse_path, ["status", "--porcelain", "--", *commit_paths]
    )
    if not status_result.stdout.strip():
        if only_tracked:
            count = (
                _count_dirty_outside_scope(warehouse_path, tracked_paths)
                if paths is None
                else 0
            )
            return ContributeResult(
                status="no_changes", dirty_outside_scope_count=count
            )
        return ContributeResult(status="no_changes")

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
