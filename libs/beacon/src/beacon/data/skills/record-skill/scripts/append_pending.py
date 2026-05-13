# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
# Self-contained script — no beacon package required at runtime.
"""Append an entry to .agentic-beacon/pending.yaml.

Usage:
    uv run append_pending.py --path <path> --type <type> --action <action> --source <source>
"""

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

VALID_TYPES = ("skill", "context", "agent")
VALID_ACTIONS = ("created", "modified")
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


def append_pending_entry(
    project_root: Path,
    path: str,
    type_: str,
    action: str,
    source: str,
) -> None:
    """Append a pending entry to .agentic-beacon/pending.yaml."""
    pending_path = project_root / ".agentic-beacon" / "pending.yaml"

    entries: list[dict] = []
    if pending_path.exists():
        try:
            with open(pending_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"Error: invalid YAML in {pending_path}: {e}", file=sys.stderr)
            sys.exit(1)

        if data is None:
            entries = []
        elif not isinstance(data, dict):
            print(
                f"Error: pending.yaml must be a YAML mapping, got {type(data).__name__}",
                file=sys.stderr,
            )
            sys.exit(1)
        else:
            raw_entries = data.get("pending", [])
            if raw_entries is None:
                entries = []
            elif not isinstance(raw_entries, list):
                print(
                    "Error: 'pending' field must be a list",
                    file=sys.stderr,
                )
                sys.exit(1)
            else:
                entries = list(raw_entries)

    created_at_str = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    new_entry = {
        "path": path,
        "type": type_,
        "action": action,
        "source": source,
        "created_at": created_at_str,
    }
    entries.append(new_entry)

    pending_path.parent.mkdir(parents=True, exist_ok=True)
    with open(pending_path, "w", encoding="utf-8") as f:
        yaml.dump(
            {"pending": entries},
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )


def main() -> None:
    """Parse args and append a pending artifact entry."""
    parser = argparse.ArgumentParser(
        description="Append a pending artifact entry to .agentic-beacon/pending.yaml."
    )
    parser.add_argument(
        "--path", required=True, help="Artifact path (warehouse-relative)"
    )
    parser.add_argument(
        "--type",
        dest="type_",
        required=True,
        choices=VALID_TYPES,
        metavar="TYPE",
        help=f"Artifact type: one of {', '.join(VALID_TYPES)}",
    )
    parser.add_argument(
        "--action",
        required=True,
        choices=VALID_ACTIONS,
        metavar="ACTION",
        help=f"Action: one of {', '.join(VALID_ACTIONS)}",
    )
    parser.add_argument(
        "--source", required=True, help="Source skill name (free-form string)"
    )
    args = parser.parse_args()

    project_root = find_project_root(Path.cwd())
    if project_root is None:
        print(ERROR_NO_WAREHOUSE, file=sys.stderr)
        sys.exit(1)

    append_pending_entry(
        project_root=project_root,
        path=args.path,
        type_=args.type_,
        action=args.action,
        source=args.source,
    )


if __name__ == "__main__":
    main()
