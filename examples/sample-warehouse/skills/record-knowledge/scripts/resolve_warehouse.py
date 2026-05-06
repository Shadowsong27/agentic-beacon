# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Walk up from $PWD to resolve the warehouse path from .agentic-beacon/config.toml.

Exits 0 with the warehouse absolute path on stdout if found.
Exits non-zero with an error message on stderr if not found or misconfigured.
"""

import sys
import tomllib
from pathlib import Path

ERROR_NO_WAREHOUSE = (
    "Error: no warehouse connected. Run 'abc warehouse connect <path>' first."
)


def find_project_root(start: Path) -> Path | None:
    """Walk up from start to find a directory containing .agentic-beacon/config.toml."""
    current = start.resolve()
    while True:
        if (current / ".agentic-beacon" / "config.toml").exists():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def get_warehouse_path(cwd: Path) -> str:
    """Return the resolved warehouse local_path for the project at cwd.

    Prints error to stderr and raises SystemExit(1) on any failure.
    """
    project_root = find_project_root(cwd)
    if project_root is None:
        print(ERROR_NO_WAREHOUSE, file=sys.stderr)
        sys.exit(1)

    config_path = project_root / ".agentic-beacon" / "config.toml"
    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    if "warehouse" not in data:
        print(
            f"Error: {config_path} is missing [warehouse] section.",
            file=sys.stderr,
        )
        sys.exit(1)

    if "local_path" not in data["warehouse"]:
        print(
            f"Error: {config_path} is missing warehouse.local_path field.",
            file=sys.stderr,
        )
        sys.exit(1)

    return str(Path(data["warehouse"]["local_path"]).resolve())


def main() -> None:
    """Resolve warehouse path from project config and print to stdout."""
    warehouse_path = get_warehouse_path(Path.cwd())
    print(warehouse_path)


if __name__ == "__main__":
    main()
