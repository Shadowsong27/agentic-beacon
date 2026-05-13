# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
# Self-contained script -- no beacon package required at runtime.
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


def _canonicalize_entry(entry: dict) -> dict:
    """Return a new dict with created_at normalized to canonical Z string form."""
    created_at = entry.get("created_at")
    if isinstance(created_at, datetime):
        if created_at.tzinfo is None:
            ts = created_at.replace(tzinfo=UTC)
        else:
            ts = created_at.astimezone(UTC)
        return {**entry, "created_at": ts.strftime("%Y-%m-%dT%H:%M:%SZ")}
    return entry


def _validate_entry(entry: dict, index: int) -> dict:
    """Validate a pending.yaml entry; exit 1 with a clear message on failure."""
    if not isinstance(entry, dict):
        print(
            f"Error: pending.yaml entry #{index}: must be a mapping,"
            f" got {type(entry).__name__}",
            file=sys.stderr,
        )
        sys.exit(1)

    required_fields = ("path", "type", "action", "source", "created_at")
    for field in required_fields:
        if field not in entry:
            print(
                f"Error: pending.yaml entry #{index}: missing required field '{field}'",
                file=sys.stderr,
            )
            sys.exit(1)

    if entry["type"] not in VALID_TYPES:
        print(
            f"Error: pending.yaml entry #{index}: invalid type {entry['type']!r},"
            f" must be one of {VALID_TYPES}",
            file=sys.stderr,
        )
        sys.exit(1)

    if entry["action"] not in VALID_ACTIONS:
        print(
            f"Error: pending.yaml entry #{index}: invalid action {entry['action']!r},"
            f" must be one of {VALID_ACTIONS}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not isinstance(entry["path"], str):
        print(
            f"Error: pending.yaml entry #{index}: 'path' must be a string",
            file=sys.stderr,
        )
        sys.exit(1)

    if not isinstance(entry["source"], str):
        print(
            f"Error: pending.yaml entry #{index}: 'source' must be a string",
            file=sys.stderr,
        )
        sys.exit(1)

    created_at = entry["created_at"]
    if isinstance(created_at, datetime):
        pass
    elif isinstance(created_at, str):
        try:
            parsed = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError as exc:
            print(
                f"Error: pending.yaml entry #{index}: 'created_at' is not a valid"
                f" UTC timestamp in '%Y-%m-%dT%H:%M:%SZ' format ({exc})",
                file=sys.stderr,
            )
            sys.exit(1)
        canonical = parsed.strftime("%Y-%m-%dT%H:%M:%SZ")
        if canonical != created_at:
            print(
                f"Error: pending.yaml entry #{index}: 'created_at' {created_at!r}"
                f" is not in canonical '%Y-%m-%dT%H:%M:%SZ' form"
                f" (expected {canonical!r}; check zero-padding)",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        print(
            f"Error: pending.yaml entry #{index}: 'created_at' must be a datetime"
            f" or a string in '%Y-%m-%dT%H:%M:%SZ' format",
            file=sys.stderr,
        )
        sys.exit(1)

    return entry


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
                validated = [_validate_entry(e, i) for i, e in enumerate(raw_entries)]
                entries = [_canonicalize_entry(e) for e in validated]

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
