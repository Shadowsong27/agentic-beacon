"""Migration from copy-based artifact trees to symlink-based trees.

Inline migration runs inside abc sync.  When regular files are detected under
.agentic-beacon/artifacts/ at paths that should be symlinks, the user is prompted
to contribute or discard local changes.
"""

import difflib
import shutil
import sys
from pathlib import Path

import click

from beacon.domains.distribution.sync_engine import SyncEngine


def _is_tty() -> bool:
    """Return True if stdin appears to be a TTY."""
    return sys.stdin.isatty()


def _diff_preview(local_file: Path, warehouse_file: Path) -> str:
    """Return a unified diff string between local and warehouse files."""
    try:
        local_lines = local_file.read_text().splitlines()
        warehouse_lines = warehouse_file.read_text().splitlines()
    except OSError as e:
        return f"Error reading files for diff: {e}"

    diff = difflib.unified_diff(
        warehouse_lines,
        local_lines,
        fromfile="warehouse",
        tofile="local",
        lineterm="",
    )
    return "\n".join(diff)


def _prompt_resolution(rel_path: str, diff: str) -> str:
    """Prompt the user to contribute, discard, or skip a modified file.

    Returns one of: "contribute", "discard", "skip".
    """
    click.echo(f"\nModified file: {rel_path}")
    if diff:
        click.echo(diff)
    choice = click.prompt(
        "[c]ontribute / [d]iscard / [s]kip",
        type=click.Choice(["c", "d", "s"], case_sensitive=False),
        default="s",
    )
    return choice.lower()


def migrate_entries(
    engine: SyncEngine,
    classification: dict[str, str],
    *,
    contribute_local: bool = False,
    discard_local: bool = False,
) -> dict[str, str]:
    """Run migration for classified entries.

    Returns a dict of resolved entries -> resolution action.
    Entries that are skipped remain as regular files.
    """
    resolved: dict[str, str] = {}

    for rel_path, state in classification.items():
        if state == "symlink_ok":
            resolved[rel_path] = "already_symlink"
            continue

        if state == "symlink_broken":
            # Repair broken symlink
            engine.create_symlink(rel_path)
            resolved[rel_path] = "repaired"
            continue

        if state == "missing":
            engine.create_symlink(rel_path)
            resolved[rel_path] = "created"
            continue

        if state == "regular_file_identical":
            # Silently replace with symlink
            dest = engine.artifacts_path / rel_path
            dest.unlink()
            engine.create_symlink(rel_path)
            resolved[rel_path] = "converted"
            continue

        if state == "regular_file_modified":
            local_file = engine.artifacts_path / rel_path
            warehouse_file = engine.warehouse_path / rel_path

            if contribute_local:
                # Write local content to warehouse, then symlink
                warehouse_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(local_file, warehouse_file)
                local_file.unlink()
                engine.create_symlink(rel_path)
                resolved[rel_path] = "contributed"
                continue

            if discard_local:
                # Delete local file, create symlink
                local_file.unlink()
                engine.create_symlink(rel_path)
                resolved[rel_path] = "discarded"
                continue

            if not _is_tty():
                # Non-TTY without a flag — skip, will be reported later
                resolved[rel_path] = "skipped"
                continue

            diff = _diff_preview(local_file, warehouse_file)
            choice = _prompt_resolution(rel_path, diff)

            if choice == "c":
                warehouse_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(local_file, warehouse_file)
                local_file.unlink()
                engine.create_symlink(rel_path)
                resolved[rel_path] = "contributed"
            elif choice == "d":
                local_file.unlink()
                engine.create_symlink(rel_path)
                resolved[rel_path] = "discarded"
            else:
                resolved[rel_path] = "skipped"

    return resolved
