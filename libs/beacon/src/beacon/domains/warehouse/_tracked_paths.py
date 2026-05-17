"""Internal helpers for expanding beacon.yaml tracked paths."""

import glob
from pathlib import Path

from beacon.core.manifest.beacon import BeaconManifest


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


def _expand_pattern(warehouse_path: Path, pattern: str) -> list[str]:
    """Expand a beacon.yaml pattern to concrete relative paths."""
    if "*" in pattern or "?" in pattern:
        matches = glob.glob(str(warehouse_path / pattern), recursive=True)
        return [
            str(Path(m).relative_to(warehouse_path))
            for m in matches
            if Path(m).is_file()
            and ".git" not in Path(m).relative_to(warehouse_path).parts
        ]

    p = warehouse_path / pattern
    if p.is_dir():
        matches = glob.glob(str(p / "**" / "*"), recursive=True)
        return [
            str(Path(m).relative_to(warehouse_path))
            for m in matches
            if Path(m).is_file()
            and ".git" not in Path(m).relative_to(warehouse_path).parts
        ]

    if p.is_file():
        return [pattern]

    return [pattern]
