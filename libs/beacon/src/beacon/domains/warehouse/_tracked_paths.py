"""Internal helpers for expanding beacon.yaml tracked paths."""

import glob
from pathlib import Path

from beacon.core.manifest.beacon import BeaconManifest


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
