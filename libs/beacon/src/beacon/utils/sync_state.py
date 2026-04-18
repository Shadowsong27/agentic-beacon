"""Sync state management utilities for Beacon CLI."""

import json
from datetime import UTC, datetime
from pathlib import Path

import click
from loguru import logger
from rich.console import Console

from .git import _get_warehouse_head_sha

console = Console()

_SYNC_STATE_FILENAME = ".sync-state"
_GLOBAL_SYNC_STATE_VERSION = 1


def _global_sync_state_file() -> Path:
    """Return path to the global agent sync-state file (lazy, respects Path.home() mocking)."""
    return Path.home() / ".config" / "agentic-beacon" / "sync-state.json"


def _read_sync_sha(artifacts_dir: Path) -> str | None:
    """Read the recorded warehouse HEAD SHA from the artifacts sync-state file.

    Returns the SHA string, or None if the file does not exist.
    """
    state_file = artifacts_dir / _SYNC_STATE_FILENAME
    if not state_file.exists():
        return None
    content = state_file.read_text().strip()
    return content or None


def _write_sync_state(artifacts_dir: Path, warehouse_path: Path) -> None:
    """Record the warehouse HEAD SHA into the artifacts sync-state file.

    Called at the end of a successful (non-dry-run) sync so contribute can
    verify the snapshot was taken against the current warehouse HEAD.
    """
    sha = _get_warehouse_head_sha(warehouse_path)
    if sha is None:
        return  # Warehouse has no git — nothing to record
    state_file = artifacts_dir / _SYNC_STATE_FILENAME
    state_file.write_text(sha + "\n")


def _check_sync_state(artifacts_dir: Path, warehouse_path: Path) -> str | None:
    """Check that the local artifact snapshot is current with the warehouse HEAD.

    Returns a warning message string if:
    - artifacts_dir does not exist or is empty (sync never run), OR
    - the recorded sync SHA does not match the current warehouse HEAD (stale snapshot)

    Returns None if everything looks current, or if the warehouse has no git.
    """
    if not (warehouse_path / ".git").exists():
        return None  # No git in warehouse — skip

    # artifacts_dir missing or empty → sync was never run
    if not artifacts_dir.exists() or not any(
        f for f in artifacts_dir.iterdir() if f.name != _SYNC_STATE_FILENAME
    ):
        return "No artifacts found — run 'abc sync' before contributing.\n\n  abc sync"

    state_file = artifacts_dir / _SYNC_STATE_FILENAME
    if not state_file.exists():
        # Sync was run before sync-state tracking was introduced — warn softly
        return (
            "Sync state is unknown. Run 'abc sync' to ensure your snapshot is\n"
            "  current before contributing to avoid overwriting newer warehouse content.\n\n"
            "  abc sync"
        )

    recorded_sha = state_file.read_text().strip()
    current_sha = _get_warehouse_head_sha(warehouse_path)

    if current_sha is None:
        return None  # Can't determine current SHA — skip silently

    if recorded_sha != current_sha:
        return (
            "Local artifact snapshot is based on an older warehouse commit.\n"
            "  The warehouse has been updated since your last sync — contributing\n"
            "  now risks overwriting newer warehouse content with stale local changes.\n\n"
            "  Run 'abc sync' to refresh your snapshot first:\n"
            "    abc sync\n\n"
            "  Use --skip-git-check to bypass this check."
        )

    return None


def _read_global_sync_state() -> dict:
    """Read global agent sync-state from ~/.config/agentic-beacon/sync-state.json.

    Returns empty dict if file does not exist, is unparseable, or has unknown version.
    """
    state_file = _global_sync_state_file()
    if not state_file.exists():
        return {}
    try:
        raw = state_file.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Could not read global sync state: {e}")
        return {}
    version = data.get("version")
    if version != _GLOBAL_SYNC_STATE_VERSION:
        logger.warning(f"Global sync state has unknown version {version!r}, skipping.")
        return {}
    return data


def _write_global_sync_state(state: dict) -> None:
    """Write global agent sync-state to ~/.config/agentic-beacon/sync-state.json.

    Always writes version field at the top level.
    """
    state_file = _global_sync_state_file()
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state["version"] = _GLOBAL_SYNC_STATE_VERSION
    state_file.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _write_agent_sync_state(
    warehouse_path: Path, relative_path: str, content_hash: str
) -> None:
    """Upsert an agent install entry into the global sync-state file.

    Entry schema:
        {"content_hash": "...", "warehouse_head": "...", "installed_at": "..."}
    """
    state = _read_global_sync_state()
    warehouses = state.get("warehouses", {})
    wh_key = str(warehouse_path)
    wh_entries = warehouses.setdefault(wh_key, {})
    wh_entries[relative_path] = {
        "content_hash": content_hash,
        "warehouse_head": _get_warehouse_head_sha(warehouse_path) or "",
        "installed_at": datetime.now(UTC).isoformat(),
    }
    state["warehouses"] = warehouses
    _write_global_sync_state(state)


def _relink_global_sync_state(current_warehouse_path: Path) -> bool:
    """Prompt user to relink sync-state when warehouse has been moved/renamed.

    Returns True if the state was relinked (key renamed), False otherwise.
    """
    state = _read_global_sync_state()
    warehouses = state.get("warehouses", {})
    current_key = str(current_warehouse_path)

    if current_key in warehouses:
        return False  # Already have state for this path

    if not warehouses:
        return False

    # Find candidate old paths whose directory name matches the current warehouse name
    current_name = current_warehouse_path.name
    candidates = [
        old_path
        for old_path in warehouses
        if Path(old_path).name == current_name and old_path != current_key
    ]

    if not candidates:
        return False

    if len(candidates) == 1:
        old_key = candidates[0]
        console.print(
            f"\n[yellow]No tracking state found for[/yellow] {current_key}\n"
            f"[yellow]Found existing state for[/yellow] {old_key}\n"
            f"Is this the same warehouse? [y/N] (Relinks tracking state) ",
            end="",
        )
        try:
            answer = click.prompt("", default="N", prompt_suffix="")
        except click.Abort:
            return False
        if answer.strip().lower() != "y":
            return False
        warehouses[current_key] = warehouses.pop(old_key)
        state["warehouses"] = warehouses
        _write_global_sync_state(state)
        return True
    else:
        # Multiple candidates — ask user to pick
        console.print(f"\n[yellow]No tracking state found for[/yellow] {current_key}")
        console.print("[yellow]Found existing state for multiple paths:[/yellow]")
        for i, cand in enumerate(candidates, 1):
            console.print(f"  {i}. {cand}")
        console.print("  0. None — skip relink\n")
        try:
            choice_str = click.prompt(
                "Which path is the same warehouse?",
                default="0",
            )
            choice = int(choice_str)
        except (click.Abort, ValueError):
            return False
        if choice == 0 or choice > len(candidates):
            return False
        old_key = candidates[choice - 1]
        warehouses[current_key] = warehouses.pop(old_key)
        state["warehouses"] = warehouses
        _write_global_sync_state(state)
        return True
