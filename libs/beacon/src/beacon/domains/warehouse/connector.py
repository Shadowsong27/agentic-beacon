"""Warehouse connection orchestration for the warehouse domain."""

from dataclasses import dataclass, field
from pathlib import Path

from beacon.core.beacon_dir import ensure_beacon_dir
from beacon.core.gitignore import GitignoreManager
from beacon.core.manifest.workspace import WorkspaceConfig
from beacon.domains.warehouse.validator import WarehouseValidator


@dataclass
class ConnectResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    gitignore_updated: bool = False


def connect_to_warehouse(project_root: Path, warehouse_path: Path) -> ConnectResult:
    """Validate warehouse and connect the project to it.

    Orchestrates validation, beacon-dir setup, config persistence, and gitignore
    update in a single domain call so the CLI handler stays to one domain call.
    """
    validator = WarehouseValidator()
    validation_result = validator.validate(str(warehouse_path))
    if not validation_result.valid:
        return ConnectResult(valid=False, errors=list(validation_result.errors))

    ensure_beacon_dir(project_root)
    WorkspaceConfig.from_path(warehouse_path, project_root=project_root)

    gitignore_mgr = GitignoreManager(project_root)
    updated = gitignore_mgr.ensure_entries()

    return ConnectResult(valid=True, gitignore_updated=updated)
