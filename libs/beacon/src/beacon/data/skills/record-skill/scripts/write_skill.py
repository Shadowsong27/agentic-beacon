# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Scaffold a new skill directly in the connected warehouse.

This script exists so the record-skill skill cannot accidentally write into the
project's symlink-mirror at .agentic-beacon/artifacts/skills/. The warehouse is
resolved from .agentic-beacon/config.toml in the project root, and the script
refuses to write anywhere outside `<warehouse>/skills/<name>/`.

Usage:
    write_skill.py --name <kebab-name> \
                   --description <one-line description> \
                   [--requires-context <warehouse-relative-path> ...] \
                   [--include-script] \
                   [--invocation <command, default '/<name>'>] \
                   [--overwrite]

On success: prints the warehouse-relative skill directory on stdout (e.g.
"skills/deploy-check/") and exits 0.

On failure: prints an error to stderr and exits non-zero.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import tomllib
from pathlib import Path

NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ERROR_NO_WAREHOUSE = (
    "Error: no warehouse connected. Run 'abc warehouse connect <path>' first."
)


def find_project_root(start: Path) -> Path | None:
    current = start.resolve()
    while True:
        if (current / ".agentic-beacon" / "config.toml").exists():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def resolve_warehouse(cwd: Path) -> Path:
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
    skills_root = (warehouse / "skills").resolve()
    try:
        target.resolve().relative_to(skills_root)
    except ValueError:
        print(
            f"Error: refusing to write outside warehouse: {target} is not under "
            f"{skills_root}",
            file=sys.stderr,
        )
        sys.exit(2)


def render_skill_md(
    name: str,
    description: str,
    invocation: str,
    requires_contexts: list[str],
) -> str:
    """Render the SKILL.md skeleton."""
    if requires_contexts:
        contexts_yaml_lines = ["  contexts:"]
        for ctx in requires_contexts:
            contexts_yaml_lines.append(f"    - {ctx}")
        contexts_yaml = "\n".join(contexts_yaml_lines)
    else:
        contexts_yaml = "  contexts: []"

    title = name.replace("-", " ").title()

    return f"""---
name: {name}
description: {description}
license: MIT
compatibility: opencode
requires:
{contexts_yaml}
---

# SKILL: {title}

## Purpose

{description}

## When to Use

<!-- Describe the specific situations where this skill applies -->

## Invocation

{invocation}

## Process

<!-- Step-by-step workflow -->

## Examples

<!-- Concrete usage examples -->

## Checklist

- [ ] Skill files are complete and tested
- [ ] Documentation is accurate and up-to-date
- [ ] Skill has been validated in a real project
"""


def render_script_pep723(name: str, description: str) -> str:
    return f'''# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""{description}"""

from __future__ import annotations


def main() -> None:
    """Main entry point for {name}."""
    print(f"Running {name}...")
    # TODO: Implement your skill logic here


if __name__ == "__main__":
    main()
'''


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scaffold a new skill directly in the connected warehouse."
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Skill name in kebab-case (becomes the directory under skills/)",
    )
    parser.add_argument(
        "--description",
        required=True,
        help="One-line skill description for SKILL.md frontmatter",
    )
    parser.add_argument(
        "--requires-context",
        action="append",
        default=[],
        metavar="PATH",
        help=(
            "Add a warehouse-relative context path to requires.contexts. "
            "May be passed multiple times."
        ),
    )
    parser.add_argument(
        "--include-script",
        action="store_true",
        help="Also generate a PEP 723 Python script scaffold under scripts/",
    )
    parser.add_argument(
        "--invocation",
        default=None,
        help="Invocation command shown in SKILL.md (default: '/<name>')",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing skill directory at the target path",
    )
    args = parser.parse_args()

    if not NAME_PATTERN.match(args.name):
        print(
            f"Error: --name must be kebab-case (got {args.name!r})",
            file=sys.stderr,
        )
        sys.exit(2)

    invocation = args.invocation if args.invocation else f"/{args.name}"

    warehouse = resolve_warehouse(Path.cwd())
    skill_dir = warehouse / "skills" / args.name
    assert_under_warehouse(skill_dir, warehouse)

    if skill_dir.exists():
        if not args.overwrite:
            print(
                f"Error: {skill_dir} already exists. Pass --overwrite to replace it.",
                file=sys.stderr,
            )
            sys.exit(3)
        shutil.rmtree(skill_dir)

    skill_dir.mkdir(parents=True)

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        render_skill_md(
            name=args.name,
            description=args.description,
            invocation=invocation,
            requires_contexts=args.requires_context,
        ),
        encoding="utf-8",
    )

    if args.include_script:
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        script_path = scripts_dir / f"{args.name}.py"
        script_path.write_text(
            render_script_pep723(args.name, args.description),
            encoding="utf-8",
        )

    rel = skill_dir.resolve().relative_to(warehouse)
    print(rel.as_posix() + "/")


if __name__ == "__main__":
    main()
