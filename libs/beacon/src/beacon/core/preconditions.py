"""Precondition checks for sync and warehouse operations."""

from pathlib import Path

from beacon.core.exceptions import BeaconSyncError
from beacon.core.warehouse_path import (
    WarehousePathMissing,
    WarehousePathNotARepo,
    validate_warehouse_path,
)
from beacon.utils.platform import UnsupportedPlatformError, ensure_supported_platform


def ensure_sync_ready(project_root: Path) -> Path:
    """Check platform support and warehouse path validity.

    Returns the resolved warehouse path on success.
    Raises BeaconSyncError with an actionable message on failure.
    """
    try:
        ensure_supported_platform()
    except UnsupportedPlatformError as e:
        raise BeaconSyncError(str(e)) from e

    beacon_dir = project_root / ".agentic-beacon"
    config_file = beacon_dir / "config.toml"

    if not config_file.exists():
        raise BeaconSyncError(
            "No warehouse connected.\n"
            "Run 'abc warehouse connect --path <warehouse>' first."
        )

    from beacon.core.manifest.workspace import WorkspaceConfig

    warehouse_settings = WorkspaceConfig()
    raw_path = warehouse_settings.warehouse.local_path
    result = validate_warehouse_path(raw_path)

    if isinstance(result, WarehousePathMissing):
        raise BeaconSyncError(
            f"Warehouse path no longer exists: {result.path}\n"
            "The warehouse may have been moved or deleted.\n"
            "Run 'abc warehouse connect --path <warehouse>' to reconnect."
        )

    if isinstance(result, WarehousePathNotARepo):
        raise BeaconSyncError(
            f"Warehouse path is not a valid git repository: {result.path}\n"
            f"Reason: {result.reason}\n"
            "Run 'abc warehouse connect --path <warehouse>' to reconnect."
        )

    return result.path
