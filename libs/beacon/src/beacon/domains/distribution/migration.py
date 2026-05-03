"""Migration from copy-based artifact trees to symlink-based trees.

Inline migration runs inside abc sync. When regular files are detected under
.agentic-beacon/artifacts/ at paths that should be symlinks, the caller is
asked to resolve each modified file via a resolver callback.
"""

import difflib
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from beacon.domains.distribution.sync_engine import SyncEngine

# Callback signature: given (relative path, unified diff string), return the resolution.
# "contribute" — write local content into warehouse, then symlink
# "discard"    — delete local file, create symlink pointing at warehouse
# "skip"       — leave as-is (file remains a regular file, will be reported unresolved)
Resolution = Literal["contribute", "discard", "skip"]
ResolveCallback = Callable[[str, str], Resolution]


def diff_preview(local_file: Path, warehouse_file: Path) -> str:
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


def migrate_entries(
    engine: SyncEngine,
    classification: dict[str, str],
    *,
    contribute_local: bool = False,
    discard_local: bool = False,
    resolve_callback: ResolveCallback | None = None,
) -> dict[str, str]:
    """Run migration for classified entries.

    Resolution precedence for regular_file_modified entries:
      1. If contribute_local is set, always contribute.
      2. Else if discard_local is set, always discard.
      3. Else if resolve_callback is provided, call it per file.
      4. Else mark "skipped" (caller will report as unresolved).

    Returns dict of rel_path -> resolution action string.
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

            if resolve_callback is not None:
                diff = diff_preview(local_file, warehouse_file)
                choice = resolve_callback(rel_path, diff)
                if choice == "contribute":
                    warehouse_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(local_file, warehouse_file)
                    local_file.unlink()
                    engine.create_symlink(rel_path)
                    resolved[rel_path] = "contributed"
                elif choice == "discard":
                    local_file.unlink()
                    engine.create_symlink(rel_path)
                    resolved[rel_path] = "discarded"
                else:
                    resolved[rel_path] = "skipped"
                continue

            resolved[rel_path] = "skipped"

    return resolved
