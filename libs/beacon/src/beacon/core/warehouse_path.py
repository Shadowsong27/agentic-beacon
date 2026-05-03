"""Warehouse path validation."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class WarehousePathOK:
    """Warehouse path is valid and resolved."""

    path: Path


@dataclass
class WarehousePathMissing:
    """Warehouse path does not exist."""

    path: Path


@dataclass
class WarehousePathNotARepo:
    """Warehouse path exists but is not a git working tree."""

    path: Path
    reason: str


WarehousePathResult = WarehousePathOK | WarehousePathMissing | WarehousePathNotARepo


def validate_warehouse_path(path: str | Path) -> WarehousePathResult:
    """Validate that a path exists and is a git working tree.

    Returns a tagged result indicating OK, missing, or not-a-repo.
    The OK variant carries the resolved absolute path.
    """
    p = Path(path).expanduser().resolve()

    if not p.exists():
        return WarehousePathMissing(path=p)

    if p.is_file():
        return WarehousePathNotARepo(
            path=p, reason="Path is a regular file, not a directory"
        )

    # Find git root by walking up
    git_root = _find_git_root(p)
    if git_root is None:
        return WarehousePathNotARepo(
            path=p, reason="No .git directory found in path or any parent"
        )

    return WarehousePathOK(path=git_root)


def _find_git_root(start: Path) -> Path | None:
    """Walk up from *start* looking for a .git directory."""
    current = start
    for _ in range(1000):  # reasonable depth limit
        if (current / ".git").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None
