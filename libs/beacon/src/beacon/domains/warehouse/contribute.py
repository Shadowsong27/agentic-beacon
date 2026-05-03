"""Warehouse contribute domain logic.

Encapsulates git add + git commit inside the warehouse clone,
driven by a project's .agentic-beacon/config.toml and beacon.yaml.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from beacon.core.preconditions import ensure_sync_ready
from beacon.domains.warehouse._tracked_paths import get_tracked_paths


@dataclass
class ContributeResult:
    """Result of a warehouse contribute operation."""

    status: str  # "committed", "no_changes", "push_failed"
    committed_sha: str | None = None
    message: str | None = None


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


def contribute(
    project_root: Path,
    *,
    message: str,
    push: bool = False,
) -> ContributeResult:
    """Contribute local changes to the warehouse.

    Stages and commits files tracked by beacon.yaml that have uncommitted
    changes in the warehouse working tree.

    Args:
        project_root: Path to the project root.
        message: Commit message (must be non-empty).
        push: Whether to push after committing.

    Returns:
        ContributeResult indicating the outcome.
    """
    if not message or not message.strip():
        raise ValueError("Commit message cannot be empty")

    warehouse_path = ensure_sync_ready(project_root)

    beacon_yaml = project_root / ".agentic-beacon" / "beacon.yaml"
    tracked_paths = get_tracked_paths(warehouse_path, beacon_yaml)

    if not tracked_paths:
        return ContributeResult(status="no_changes")

    # Check git status for tracked paths
    status_result = _run_git(
        warehouse_path, ["status", "--porcelain", "--", *tracked_paths]
    )
    if not status_result.stdout.strip():
        return ContributeResult(status="no_changes")

    # Stage tracked paths
    _run_git(warehouse_path, ["add", "--", *tracked_paths])

    # Commit
    commit_result = _run_git(
        warehouse_path, ["commit", "-m", message, "--", *tracked_paths]
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
