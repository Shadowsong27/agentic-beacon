"""Legacy global-agent symlink cleanup for the distribution domain.

PER-113 migration: scans `~/.claude/agents/` and `~/.config/opencode/agents/`
on every `abc sync` invocation and removes symlinks pointing into the
connected warehouse's `agents/` directory. Idempotent — subsequent runs find
nothing and return 0. A run-once marker (so the cleanup only fires the first
time after upgrade) is tracked separately in PER-133.
"""

from pathlib import Path

from loguru import logger


def cleanup_legacy_global_agent_symlinks(warehouse_path: Path) -> int:
    """Remove legacy global agent symlinks that point into the connected warehouse.

    Scans ~/.claude/agents/ and ~/.config/opencode/agents/ non-recursively.
    For each entry that is a symlink whose resolved target is under
    ``warehouse_path / "agents"``, unlinks it.

    Idempotent: subsequent calls find no matching symlinks and return 0.
    Missing tool directories are silently skipped.

    Args:
        warehouse_path: Absolute path to the connected warehouse root.

    Returns:
        The total number of symlinks removed across both directories.
    """
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

    return removed
