"""Artifact reset operations for the distribution domain."""

import shutil
from pathlib import Path

from beacon.core.exceptions import ResetError
from beacon.core.manifest.beacon import BeaconManifest
from beacon.core.manifest.workspace import WorkspaceConfig
from beacon.domains.artifact.skill import normalize_skill_entry
from beacon.domains.distribution.sync_engine import SyncEngine


def reset_artifacts(project_root: Path) -> tuple[int, int, int]:
    """Force-overwrite all synced artifacts from warehouse.

    Returns (overwritten_count, new_count, error_count).
    Raises ResetError on configuration errors.
    """
    beacon_dir = project_root / ".agentic-beacon"

    if not beacon_dir.exists():
        raise ResetError(
            f"No warehouse connected at {project_root}\n"
            "Run 'abc warehouse connect' first."
        )

    if not (beacon_dir / "beacon.yaml").exists():
        raise ResetError(
            "No beacon.yaml found.\nRun 'abc setup' to create artifact configuration."
        )

    warehouse_settings = WorkspaceConfig()
    warehouse_path = Path(warehouse_settings.warehouse.local_path)
    beacon_settings = BeaconManifest.from_yaml(beacon_dir / "beacon.yaml")

    artifacts_dir = beacon_dir / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)

    sync_engine = SyncEngine(
        warehouse_path=warehouse_path, artifacts_path=artifacts_dir
    )

    artifact_paths: list[str] = []

    for context_name in beacon_settings.artifacts.contexts:
        artifact_paths.append(f"contexts/{context_name}")

    for skill_entry in beacon_settings.artifacts.skills:
        normalized = normalize_skill_entry(skill_entry)
        skill_dir = warehouse_path / normalized
        if skill_dir.exists() and skill_dir.is_dir():
            artifact_paths.extend(sync_engine.expand_glob(f"{normalized}/**/*"))
        else:
            artifact_paths.append(normalized)

    copied_count = 0
    overwritten_count = 0
    error_count = 0

    for artifact_path in artifact_paths:
        dest = artifacts_dir / artifact_path
        if dest.exists() or dest.is_symlink():
            dest.unlink()
            overwritten_count += 1
        result = sync_engine.create_symlink(artifact_path)
        if result.action == "created":
            copied_count += 1
        elif result.action == "error":
            error_count += 1

    new_count = (
        copied_count - overwritten_count if copied_count > overwritten_count else 0
    )
    return overwritten_count, new_count, error_count


def remove_artifacts_dir(project_root: Path) -> Path | None:
    """Remove the .agentic-beacon/artifacts directory.

    Returns the removed directory path if it existed, None otherwise.
    """
    artifacts_dir = project_root / ".agentic-beacon" / "artifacts"
    if artifacts_dir.exists():
        shutil.rmtree(artifacts_dir)
        return artifacts_dir
    return None


def count_synced_files(project_root: Path) -> int:
    """Count total symlinks in .agentic-beacon/artifacts.

    Returns 0 if the directory does not exist.
    """
    artifacts_dir = project_root / ".agentic-beacon" / "artifacts"
    if not artifacts_dir.exists():
        return 0
    return sum(1 for _ in artifacts_dir.rglob("*") if _.is_symlink())
