#!/usr/bin/env python3
"""One-shot migration script: move agent requires from frontmatter to agents.yaml.

Usage:
    python scripts/migrate-agent-requires.py /path/to/warehouse

What it does:
1. Reads every agents/*.md file (excluding README.md).
2. Extracts the `requires:` frontmatter block.
3. Writes agents/agents.yaml with skills only (drops contexts).
4. Strips `requires:` from each agent file's frontmatter.
5. Prints a summary of dropped contexts per agent.

Idempotent: running twice on the same warehouse is a no-op.
Errors if agents/agents.yaml already exists and differs from the computed manifest.
"""

import argparse
import sys
from pathlib import Path

import yaml


def parse_frontmatter(path: Path) -> tuple[dict | None, str]:
    """Parse YAML frontmatter from a markdown file.

    Returns (frontmatter_dict, body_text) where frontmatter_dict is None
    if no frontmatter is present.
    """
    content = path.read_text(encoding="utf-8")
    content = content.lstrip("\ufeff").lstrip()

    if not content.startswith("---"):
        return None, content

    remainder = content[3:]
    end_idx = remainder.find("---")
    if end_idx == -1:
        return None, content

    yaml_block = remainder[:end_idx].strip()
    body = remainder[end_idx + 3 :]

    try:
        data = yaml.safe_load(yaml_block)
    except yaml.YAMLError:
        return None, content

    if not isinstance(data, dict):
        return None, content

    return data, body


def strip_requires_from_frontmatter(frontmatter: dict) -> dict:
    """Return a copy of frontmatter with 'requires' removed."""
    cleaned = dict(frontmatter)
    cleaned.pop("requires", None)
    return cleaned


def write_frontmatter(path: Path, frontmatter: dict, body: str) -> None:
    """Write markdown file with YAML frontmatter and body."""
    if frontmatter:
        yaml_text = yaml.safe_dump(
            frontmatter, default_flow_style=False, sort_keys=False
        )
        content = f"---\n{yaml_text}---\n{body}"
    else:
        content = body
    path.write_text(content, encoding="utf-8")


def migrate_warehouse(warehouse_path: Path) -> None:
    agents_dir = warehouse_path / "agents"
    if not agents_dir.exists():
        print("No agents/ directory found. Nothing to migrate.")
        return

    manifest: dict[str, dict] = {}
    stripped_files: list[Path] = []
    dropped_contexts: dict[str, list[str]] = {}

    for md_file in sorted(agents_dir.iterdir()):
        if (
            not md_file.is_file()
            or md_file.suffix != ".md"
            or md_file.name == "README.md"
        ):
            continue

        frontmatter, body = parse_frontmatter(md_file)
        if frontmatter is None or "requires" not in frontmatter:
            continue

        requires = frontmatter["requires"]
        if not isinstance(requires, dict):
            continue

        agent_name = md_file.stem
        skills = requires.get("skills", [])
        contexts = requires.get("contexts", [])

        if isinstance(skills, list):
            manifest[agent_name] = {"skills": skills}
        else:
            manifest[agent_name] = {"skills": []}

        if isinstance(contexts, list) and contexts:
            dropped_contexts[agent_name] = contexts

        cleaned_fm = strip_requires_from_frontmatter(frontmatter)
        write_frontmatter(md_file, cleaned_fm, body)
        stripped_files.append(md_file)

    manifest_path = agents_dir / "agents.yaml"

    if manifest_path.exists():
        existing_text = manifest_path.read_text(encoding="utf-8")
        try:
            existing_manifest = yaml.safe_load(existing_text) or {}
        except yaml.YAMLError:
            existing_manifest = {}
        # If no new files were stripped, the computed manifest is the idempotent
        # result of an already-migrated warehouse. Accept the existing file.
        if not stripped_files:
            print(
                f"{manifest_path} already exists. No new requires: found — nothing to do."
            )
        elif existing_manifest != manifest:
            print(
                f"Error: {manifest_path} already exists and differs from computed manifest.\n"
                "Aborting to avoid overwriting. "
                "Remove or back up the existing file and re-run.",
                file=sys.stderr,
            )
            sys.exit(1)
        else:
            print(
                f"{manifest_path} already exists and matches computed manifest. Skipping write."
            )
    else:
        manifest_path.write_text(
            yaml.safe_dump(manifest, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )
        print(f"Wrote {manifest_path} with {len(manifest)} agent(s).")

    if stripped_files:
        print(f"Stripped 'requires:' from {len(stripped_files)} agent file(s):")
        for f in stripped_files:
            print(f"  - {f.name}")

    if dropped_contexts:
        print(
            "\nDropped contexts entries (contexts are project-level, not agent-level):"
        )
        for agent_name, contexts in sorted(dropped_contexts.items()):
            ctx_str = ", ".join(contexts)
            print(f"  {agent_name}: {ctx_str}")
    else:
        print("\nNo contexts entries were dropped.")

    print("\nMigration complete.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate agent requires from frontmatter to agents/agents.yaml"
    )
    parser.add_argument("warehouse_path", type=Path, help="Path to the warehouse root")
    args = parser.parse_args()

    warehouse_path = args.warehouse_path.expanduser().resolve()
    if not warehouse_path.exists():
        print(f"Error: path does not exist: {warehouse_path}", file=sys.stderr)
        sys.exit(1)
    if not warehouse_path.is_dir():
        print(f"Error: path is not a directory: {warehouse_path}", file=sys.stderr)
        sys.exit(1)

    migrate_warehouse(warehouse_path)


if __name__ == "__main__":
    main()
