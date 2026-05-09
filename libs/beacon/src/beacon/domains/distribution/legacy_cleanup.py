"""Legacy global-agent symlink cleanup for the distribution domain.

PER-113 migration: scans `~/.claude/agents/` and `~/.config/opencode/agents/`
on the first `abc sync` invocation after upgrade and removes symlinks pointing
into the connected warehouse's `agents/` directory. A run-once marker at
`<project_root>/.agentic-beacon/.legacy-migrated` is written after the first
successful scan so that subsequent syncs skip the home-dir I/O entirely.
Delete that marker file to re-run the cleanup.
"""

from datetime import UTC, datetime
from pathlib import Path

from loguru import logger


def cleanup_legacy_global_agent_symlinks(
    warehouse_path: Path, project_root: Path
) -> int:
    """Remove legacy global agent symlinks that point into the connected warehouse.

    On the first call (no marker present), scans ~/.claude/agents/ and
    ~/.config/opencode/agents/ non-recursively. For each entry that is a
    symlink whose resolved target is under ``warehouse_path / "agents"``,
    unlinks it. After the scan completes (whether or not anything was removed),
    writes a marker at ``project_root / ".agentic-beacon" / ".legacy-migrated"``
    so that all future calls short-circuit with 0 home-dir I/O.

    If the marker already exists, the function returns 0 immediately without
    touching the filesystem.

    Escape hatch: delete ``.agentic-beacon/.legacy-migrated`` to re-run the
    cleanup. The marker lives under ``.agentic-beacon/``, which is
    project-internal and gitignored via the project ``.gitignore``.

    Args:
        warehouse_path: Absolute path to the connected warehouse root.
        project_root: Absolute path to the project root (where
            ``.agentic-beacon/`` lives).

    Returns:
        The total number of symlinks removed across both directories, or 0
        when the marker is present and the scan is skipped.
    """
    marker = project_root / ".agentic-beacon" / ".legacy-migrated"
    if marker.exists():
        return 0

    home = Path.home()
    global_agent_dirs = [
        home / ".claude" / "agents",
        home / ".config" / "opencode" / "agents",
    ]

    # Resolve the canonical warehouse agents path once for comparison
    try:
        warehouse_agents = (warehouse_path / "agents").resolve()
    except OSError:
        warehouse_agents = warehouse_path / "agents"

    removed = 0

    for agent_dir in global_agent_dirs:
        if not agent_dir.exists():
            continue

        for entry in agent_dir.iterdir():
            # Only handle direct children (non-recursive); skip directories
            if entry.is_dir() and not entry.is_symlink():
                continue
            if not entry.is_symlink():
                continue

            # Resolve the symlink target — dangling symlinks return themselves
            # under strict=False, which won't match the warehouse path
            try:
                resolved = entry.resolve(strict=False)
            except OSError:
                continue

            # Check if the target is under warehouse_path/agents/
            try:
                resolved.relative_to(warehouse_agents)
            except ValueError:
                # Not under warehouse — leave it alone
                continue

            # Verify the target actually resolves under the warehouse agents dir
            # (resolve() with strict=False may return a non-existent path that
            # still starts with the right prefix — that is fine; we still remove it)
            try:
                entry.unlink()
                removed += 1
                logger.debug(
                    "Removed legacy global agent symlink: {} (pointed at {})",
                    entry,
                    resolved,
                )
            except OSError as exc:
                logger.warning(
                    "Could not remove legacy agent symlink {}: {}", entry, exc
                )

    # Write marker regardless of how many were removed; the marker means
    # "scan ran", not "scan removed something".
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        f"PER-113 legacy global-agent cleanup ran: {datetime.now(UTC).isoformat()}\n",
        encoding="utf-8",
    )
    return removed
