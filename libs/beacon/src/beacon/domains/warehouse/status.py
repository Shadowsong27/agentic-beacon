"""Warehouse status domain logic.

Runs git status / git diff inside the warehouse clone, filtered by
beacon.yaml-matched paths, and reports modified files and ahead/behind counts.
"""

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from beacon.core.manifest.beacon import BeaconManifest
from beacon.core.preconditions import ensure_sync_ready


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


def _get_tracked_paths(warehouse_path: Path, beacon_yaml: Path) -> list[str]:
    """Return the list of beacon.yaml-matched paths relative to warehouse root."""

    if not beacon_yaml.exists():
        return []

    beacon_settings = BeaconManifest.from_yaml(beacon_yaml)
    paths: list[str] = []

    for pattern in beacon_settings.artifacts.knowledge:
        paths.extend(_expand_pattern(warehouse_path, pattern))

    for pattern in beacon_settings.artifacts.skills:
        paths.extend(_expand_pattern(warehouse_path, pattern))

    for pattern in beacon_settings.artifacts.contexts:
        paths.extend(_expand_pattern(warehouse_path, pattern))

    return paths


def _expand_pattern(warehouse_path: Path, pattern: str) -> list[str]:
    """Expand a beacon.yaml pattern to concrete relative paths."""
    import glob

    if "*" in pattern or "?" in pattern:
        matches = glob.glob(str(warehouse_path / pattern), recursive=True)
        return [
            str(Path(m).relative_to(warehouse_path))
            for m in matches
            if Path(m).is_file()
        ]

    p = warehouse_path / pattern
    if p.is_dir():
        matches = glob.glob(str(p / "**" / "*"), recursive=True)
        return [
            str(Path(m).relative_to(warehouse_path))
            for m in matches
            if Path(m).is_file()
        ]

    if p.is_file():
        return [pattern]

    return [pattern]


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
            tracked = _get_tracked_paths(warehouse_path, beacon_yaml)
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
        tracked = _get_tracked_paths(warehouse_path, beacon_yaml)
        if tracked:
            status_result = _run_git(
                warehouse_path, ["status", "--porcelain", "--", *tracked]
            )
        else:
            status_result = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )

    for line in status_result.stdout.strip().splitlines():
        if len(line) >= 3:
            code = line[:2].strip()
            file_path = line[3:]
            result.modifications.append(StatusEntry(path=file_path, status=code))

    return result
