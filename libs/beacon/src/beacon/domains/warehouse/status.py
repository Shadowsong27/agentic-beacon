"""Warehouse status domain logic.

Runs git status / git diff inside the warehouse clone, filtered by
beacon.yaml-matched paths, and reports modified files and ahead/behind counts.
"""

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from beacon.core.dependencies.manifest import (
    AgentManifestError,
    load_agent_manifest,
    validate_agent_frontmatter_clean,
    validate_agents_directory,
    validate_declared_skills,
)
from beacon.domains.warehouse._tracked_paths import get_tracked_paths
from beacon.domains.warehouse.preconditions import ensure_sync_ready


@dataclass
class StatusEntry:
    """A single file status entry."""

    path: str
    status: str  # e.g. "M", "A", "D", "??"


@dataclass
class StatusResult:
    """Result of a warehouse status query."""

    modifications: list[StatusEntry] = field(default_factory=list)
    ahead: int | None = None
    behind: int | None = None
    has_upstream: bool = True
    diff: str | None = None


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


def status(
    project_root: Path,
    *,
    path: str | None = None,
    all_paths: bool = False,
) -> StatusResult:
    """Get warehouse status filtered by beacon.yaml.

    Args:
        project_root: Path to the project root.
        path: Optional single file path to get diff for.
        all_paths: If True, don't filter by beacon.yaml.

    Returns:
        StatusResult with modifications and ahead/behind counts.
    """
    warehouse_path = ensure_sync_ready(project_root)

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
                raise ValueError(str(exc)) from exc

    result = StatusResult()

    # Ahead / behind
    rev_list = _run_git(
        warehouse_path, ["rev-list", "--left-right", "--count", "HEAD...@{u}"]
    )
    if rev_list.returncode == 0:
        parts = rev_list.stdout.strip().split("\t")
        if len(parts) == 2:
            result.ahead = int(parts[0])
            result.behind = int(parts[1])
        result.has_upstream = True
    else:
        result.has_upstream = False
        result.ahead = None
        result.behind = None

    if path:
        # Single-file diff mode
        if not all_paths:
            beacon_yaml = project_root / ".agentic-beacon" / "beacon.yaml"
            tracked = get_tracked_paths(warehouse_path, beacon_yaml)
            if path not in tracked:
                raise ValueError(f"Path '{path}' is not tracked by beacon.yaml")

        diff_result = _run_git(warehouse_path, ["diff", "--", path])
        result.diff = diff_result.stdout
        return result

    # Full status mode
    if all_paths:
        status_result = _run_git(warehouse_path, ["status", "--porcelain"])
    else:
        beacon_yaml = project_root / ".agentic-beacon" / "beacon.yaml"
        tracked = get_tracked_paths(warehouse_path, beacon_yaml)
        if tracked:
            status_result = _run_git(
                warehouse_path, ["status", "--porcelain", "--", *tracked]
            )
        else:
            status_result = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )

    for line in status_result.stdout.splitlines():
        if len(line) >= 3:
            code = line[:2].strip()
            file_path = line[3:]
            result.modifications.append(StatusEntry(path=file_path, status=code))

    return result
