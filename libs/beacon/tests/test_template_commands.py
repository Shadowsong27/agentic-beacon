"""Regression test: all `abc ...` commands referenced in templates must exist in the CLI."""

import re
from pathlib import Path

import click
from beacon.cli import main

_TEMPLATES_DIR = Path(__file__).parent.parent / "src/beacon/data/templates"

# Pattern: backtick-quoted `abc <something>` — captures the part after "abc "
_ABC_CMD_RE = re.compile(r"`abc ([\w][\w/ -]*)`")


def _collect_valid_commands(group: click.Group, prefix: str = "") -> set[str]:
    """Recursively build the set of all valid command strings."""
    valid: set[str] = set()
    for name, cmd in group.commands.items():
        full = f"{prefix} {name}".strip() if prefix else name
        valid.add(full)
        if isinstance(cmd, click.Group):
            valid |= _collect_valid_commands(cmd, full)
    return valid


def _extract_abc_refs(templates_dir: Path) -> list[tuple[str, str]]:
    """Return list of (filename, command_string) for every `abc ...` reference in templates."""
    refs = []
    for tmpl in sorted(templates_dir.rglob("*.md")):
        for match in _ABC_CMD_RE.finditer(tmpl.read_text(encoding="utf-8")):
            refs.append(
                (tmpl.relative_to(templates_dir).as_posix(), match.group(1).strip())
            )
    return refs


def test_template_commands_exist_in_cli():
    """Every `abc <cmd>` reference in templates must match a real CLI command."""
    valid = _collect_valid_commands(main)
    invalid = []

    for filename, ref in _extract_abc_refs(_TEMPLATES_DIR):
        # Strip flags/arguments — keep only the leading command words
        # e.g. "warehouse connect --path ~/foo" → check "warehouse connect" then "warehouse"
        words = ref.split()
        two_word = " ".join(words[:2])
        one_word = words[0]

        if two_word not in valid and one_word not in valid:
            invalid.append(f"  [{filename}] `abc {ref}`")

    assert not invalid, "Templates reference unknown abc commands:\n" + "\n".join(
        invalid
    )
