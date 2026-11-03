# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Write a new context file to the connected warehouse.

This script exists so the record-knowledge skill cannot accidentally write into
the project's symlink-mirror at .agentic-beacon/artifacts/contexts/. The
warehouse is resolved from .agentic-beacon/config.toml in the project root, and
the script refuses to write anywhere outside `<warehouse>/contexts/`.

The body must open with a frontmatter block that carries a non-empty
`description` (the conductor context selector reads it), and the frontmatter's
only allowed key is `description`. The script refuses any other body and writes
nothing.

Use this only when authoring a *new* context file. Appending a knowledge pointer
to an *existing* context is a normal in-place edit and does not go through here.

Usage:
    write_context.py --name <kebab-name> \
                     [--overwrite] \
                     [--content-file <path>]

Content is read from stdin unless --content-file is given.

On success: prints the final warehouse-relative path on stdout (e.g.
"contexts/linear-ops.md") and exits 0.

On failure: prints an error to stderr and exits non-zero.
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path

import yaml

NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

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


def resolve_warehouse(cwd: Path) -> Path:
    """Return the absolute warehouse path or exit with an error."""
    project_root = find_project_root(cwd)
    if project_root is None:
        print(ERROR_NO_WAREHOUSE, file=sys.stderr)
        sys.exit(1)

    config_path = project_root / ".agentic-beacon" / "config.toml"
    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    if "warehouse" not in data or "local_path" not in data["warehouse"]:
        print(
            f"Error: {config_path} is missing warehouse.local_path.",
            file=sys.stderr,
        )
        sys.exit(1)

    return Path(data["warehouse"]["local_path"]).resolve()


def assert_under_warehouse(target: Path, warehouse: Path) -> None:
    """Refuse to proceed if *target* resolves outside <warehouse>/contexts/."""
    contexts_root = (warehouse / "contexts").resolve()
    try:
        target.resolve().relative_to(contexts_root)
    except ValueError:
        print(
            f"Error: refusing to write outside warehouse: {target} is not under "
            f"{contexts_root}",
            file=sys.stderr,
        )
        sys.exit(2)


def validate_frontmatter_description(content: str) -> str | None:
    """Return an error message if content lacks a non-empty frontmatter description."""
    lines = content.splitlines(keepends=True)
    if not content.startswith(("---\n", "---\r\n")):
        return _description_error("body does not open with a frontmatter block")
    closing = next(
        (
            i
            for i, line in enumerate(lines[1:], start=1)
            if line.rstrip("\r\n") == "---"
        ),
        None,
    )
    if closing is None:
        return _description_error("frontmatter block is not closed with '---'")
    try:
        data = yaml.safe_load("".join(lines[1:closing]))
    except yaml.YAMLError as exc:
        return _description_error(f"frontmatter is not valid YAML ({exc})")
    if not isinstance(data, dict):
        return _description_error("frontmatter is not a mapping")
    extra = set(data) - {"description"}
    if extra:
        return _description_error(
            f"frontmatter has unknown key(s): {', '.join(sorted(map(str, extra)))}; "
            "the only allowed key is `description`"
        )
    description = data.get("description")
    if not isinstance(description, str) or not description.strip():
        return _description_error("frontmatter has no non-empty string `description`")
    return None


def _description_error(reason: str) -> str:
    return (
        "Error: refusing to write a context without a non-empty frontmatter description "
        f"({reason}; start the body with a --- block containing description: '...')."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Write a new context file directly to the connected warehouse.",
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Context file stem in kebab-case (without .md extension)",
    )
    parser.add_argument(
        "--content-file",
        default=None,
        help="Read body content from this file. Default: stdin.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the file if it already exists.",
    )
    args = parser.parse_args()

    if not NAME_PATTERN.match(args.name):
        print(
            f"Error: --name must be kebab-case (got {args.name!r})",
            file=sys.stderr,
        )
        sys.exit(2)

    warehouse = resolve_warehouse(Path.cwd())

    target = warehouse / "contexts" / f"{args.name}.md"
    assert_under_warehouse(target, warehouse)

    if target.exists() and not args.overwrite:
        print(
            f"Error: {target} already exists. Pass --overwrite to replace it.",
            file=sys.stderr,
        )
        sys.exit(3)

    if args.content_file:
        content_path = Path(args.content_file)
        if not content_path.is_file():
            print(
                f"Error: --content-file not found: {content_path}",
                file=sys.stderr,
            )
            sys.exit(2)
        content = content_path.read_text(encoding="utf-8")
    else:
        content = sys.stdin.read()

    if not content.strip():
        print("Error: refusing to write an empty context file.", file=sys.stderr)
        sys.exit(2)

    error = validate_frontmatter_description(content)
    if error is not None:
        print(error, file=sys.stderr)
        sys.exit(2)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

    rel = target.resolve().relative_to(warehouse)
    print(rel.as_posix())


if __name__ == "__main__":
    main()
