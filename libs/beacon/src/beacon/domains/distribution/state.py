"""Sync state management for the distribution domain."""

import json
from datetime import UTC, datetime
from pathlib import Path

import click
from loguru import logger
from rich.console import Console

from beacon.utils.git import get_warehouse_head_sha

console = Console()

GLOBAL_SYNC_STATE_VERSION = 1


def global_sync_state_file() -> Path:
    """Return path to the global agent sync-state file (lazy, respects Path.home() mocking)."""
    return Path.home() / ".config" / "agentic-beacon" / "sync-state.json"


def read_global_sync_state() -> dict:
    """Read global agent sync-state from ~/.config/agentic-beacon/sync-state.json.

    Returns empty dict if file does not exist, is unparseable, or has unknown version.
    """
    state_file = global_sync_state_file()
    if not state_file.exists():
        return {}
    try:
        raw = state_file.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Could not read global sync state: {e}")
        return {}
    version = data.get("version")
    if version != GLOBAL_SYNC_STATE_VERSION:
        logger.warning(f"Global sync state has unknown version {version!r}, skipping.")
        return {}
    return data


def write_global_sync_state(state: dict) -> None:
    """Write global agent sync-state to ~/.config/agentic-beacon/sync-state.json.

    Always writes version field at the top level.
    """
    state_file = global_sync_state_file()
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state["version"] = GLOBAL_SYNC_STATE_VERSION
    state_file.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def write_agent_sync_state(
    warehouse_path: Path, relative_path: str, content_hash: str
) -> None:
    """Upsert an agent install entry into the global sync-state file.

    Entry schema:
        {"content_hash": "...", "warehouse_head": "...", "installed_at": "..."}
    """
    state = read_global_sync_state()
    warehouses = state.get("warehouses", {})
    wh_key = str(warehouse_path)
    wh_entries = warehouses.setdefault(wh_key, {})
    wh_entries[relative_path] = {
        "content_hash": content_hash,
        "warehouse_head": get_warehouse_head_sha(warehouse_path) or "",
        "installed_at": datetime.now(UTC).isoformat(),
    }
    state["warehouses"] = warehouses
    write_global_sync_state(state)


def relink_global_sync_state(current_warehouse_path: Path) -> bool:
    """Prompt user to relink sync-state when warehouse has been moved/renamed.

    Returns True if the state was relinked (key renamed), False otherwise.
    """
    state = read_global_sync_state()
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
        write_global_sync_state(state)
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
        write_global_sync_state(state)
        return True
