"""Internal helpers for expanding beacon.yaml tracked paths."""

import glob
import subprocess
from pathlib import Path

from beacon.core.manifest.beacon import BeaconManifest


def _run_git(warehouse_path: Path, args: list[str]) -> tuple[int, str, str]:
    """Run a git command inside warehouse, return (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["git", "-C", str(warehouse_path)] + args,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def get_tracked_paths(warehouse_path: Path, beacon_yaml: Path) -> list[str]:
    """Return the list of beacon.yaml-matched paths relative to warehouse root."""
    if not beacon_yaml.exists():
        return []

    beacon_settings = BeaconManifest.from_yaml(beacon_yaml)
    paths: list[str] = []

    # Walk all three artifact types declared by ArtifactsConfig: skills, contexts, agents.
    # The schema (core/manifest/beacon.py) has `extra: forbid`, so these are the
    # exhaustive set — knowledge files are intentionally NOT here; they are
    # auto-derived during `abc sync` / `abc adopt` from context+skill references.
    for pattern in beacon_settings.artifacts.skills:
        paths.extend(_expand_pattern(warehouse_path, pattern))

    for pattern in beacon_settings.artifacts.contexts:
        paths.extend(_expand_pattern(warehouse_path, pattern))

    for pattern in beacon_settings.artifacts.agents:
        paths.extend(_expand_pattern(warehouse_path, pattern))

    return paths


def _git_tracked_or_staged_deleted(warehouse_path: Path, pathspec: str) -> set[str]:
    """Return tracked paths matching pathspec, INCLUDING staged-for-deletion ones."""
    found = set()
    rc, stdout, _ = _run_git(warehouse_path, ["ls-files", "--", pathspec])
    if rc == 0:
        for line in stdout.strip().splitlines():
            if line and ".git" not in Path(line).parts:
                found.add(line)
    rc, stdout, _ = _run_git(
        warehouse_path,
        ["diff", "--cached", "--name-only", "--diff-filter=D", "--", pathspec],
    )
    if rc == 0:
        for line in stdout.strip().splitlines():
            if line and ".git" not in Path(line).parts:
                found.add(line)
    return found


def _expand_pattern(warehouse_path: Path, pattern: str) -> list[str]:
    """Expand a beacon.yaml pattern to concrete relative paths."""
    if "*" in pattern or "?" in pattern:
        # Glob finds existing files (including untracked)
        matches = glob.glob(str(warehouse_path / pattern), recursive=True)
        paths = {
            str(Path(m).relative_to(warehouse_path))
            for m in matches
            if Path(m).is_file()
            and ".git" not in Path(m).relative_to(warehouse_path).parts
        }
        # Supplement with tracked files, including staged deletions
        paths |= _git_tracked_or_staged_deleted(warehouse_path, pattern)
        return sorted(paths)

    p = warehouse_path / pattern
    # Treat as directory pattern if it ends with '/' OR the path exists as a dir.
    # The '/' suffix is the beacon.yaml convention for directories; we must also
    # handle the case where git rm has removed an empty directory from disk.
    if pattern.endswith("/") or p.is_dir():
        matches = glob.glob(str(p / "**" / "*"), recursive=True) if p.exists() else []
        paths = {
            str(Path(m).relative_to(warehouse_path))
            for m in matches
            if Path(m).is_file()
            and ".git" not in Path(m).relative_to(warehouse_path).parts
        }
        # Supplement with tracked files, including staged deletions
        paths |= _git_tracked_or_staged_deleted(warehouse_path, pattern)
        return sorted(paths)

    if p.is_file():
        return [pattern]

    return [pattern]
