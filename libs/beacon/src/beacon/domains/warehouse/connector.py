"""Warehouse connection orchestration for the warehouse domain."""

from dataclasses import dataclass, field
from pathlib import Path

from beacon.core.gitignore import apply_all_gitignores
from beacon.core.manifest.workspace import WorkspaceConfig
from beacon.domains.warehouse.validator import WarehouseValidator


@dataclass
class ConnectResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    gitignore_updated: bool = False


def _ensure_beacon_dir(project_root: Path) -> Path:
    beacon_dir = project_root / ".agentic-beacon"
    beacon_dir.mkdir(exist_ok=True)
    return beacon_dir


def connect_to_warehouse(
    project_root: Path,
    warehouse_path: Path,
    *,
    main_branch: str | None = None,
) -> ConnectResult:
    """Validate warehouse and connect the project to it.

    Orchestrates validation, beacon-dir setup, config persistence, and gitignore
    update in a single domain call so the CLI handler stays to one domain call.
    """
    validator = WarehouseValidator()
    validation_result = validator.validate(str(warehouse_path))
    if not validation_result.valid:
        return ConnectResult(valid=False, errors=list(validation_result.errors))

    _ensure_beacon_dir(project_root)
    WorkspaceConfig.from_path(
        warehouse_path,
        project_root=project_root,
        main_branch=main_branch,
    )

    apply_all_gitignores(project_root)
    updated = True

    return ConnectResult(valid=True, gitignore_updated=updated)
