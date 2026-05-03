"""Agent-related commands for the abc CLI."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from beacon.core.manifest.workspace import WorkspaceConfig
from beacon.domains.artifact.agent import list_global_agents, sync_agents_from_warehouse
from beacon.domains.distribution.sync_engine import SyncEngine
from beacon.domains.warehouse.git_health import (
    check_warehouse_git_clean,
    check_warehouse_on_main_branch,
)

console = Console()


@click.group()
def agents() -> None:
    """Agent definition commands (sync)."""
    pass


@agents.command(name="sync")
@click.option(
    "--force", is_flag=True, help="Overwrite conflicting files without prompting"
)
@click.option(
    "--skip-git-check",
    is_flag=True,
    help="Skip warehouse uncommitted-changes check",
)
def agents_sync(*, force: bool, skip_git_check: bool) -> None:
    """Sync all agent definitions from warehouse into global tool directories.

    Reads the connected warehouse, finds every agent definition under agents/,
    and installs them into the global directories for all detected tools
    (~/.config/opencode/agents/ and/or ~/.claude/agents/).

    A confirmation prompt is shown when local agent files differ from the
    warehouse version. Use --force to overwrite without prompting.

    Example:
        abc agents sync            # Sync all agents, prompt on conflicts
        abc agents sync --force    # Overwrite all conflicts without prompting
    """

    beacon_dir = Path.cwd() / ".agentic-beacon"
    if not beacon_dir.exists():
        console.print("[red]Error:[/red] No .agentic-beacon directory found.")
        console.print("Run 'abc warehouse connect' to connect to a warehouse first.")
        sys.exit(1)

    try:
        warehouse_settings = WorkspaceConfig()
        warehouse_path = Path(warehouse_settings.warehouse.local_path)
    except Exception as e:
        console.print(f"[red]Error:[/red] Could not load warehouse settings: {e}")
        sys.exit(1)

    if not skip_git_check:
        git_result = check_warehouse_git_clean(warehouse_path)
        if not git_result.ok:
            console.print(f"[red]Error:[/red] {git_result.error_message}")
            if git_result.hint:
                console.print(f"\n  [dim]{git_result.hint}[/dim]")
            sys.exit(1)
        branch_result = check_warehouse_on_main_branch(warehouse_path)
        if not branch_result.ok:
            console.print(f"[red]Error:[/red] {branch_result.error_message}")
            if branch_result.hint:
                console.print(f"\n  [dim]{branch_result.hint}[/dim]")
            sys.exit(1)

    sync_agents_from_warehouse(warehouse_path, force=force)


@click.command(name="list")
@click.argument(
    "artifact_type",
    required=False,
    type=click.Choice(
        ["agents", "knowledge", "skills", "contexts"], case_sensitive=False
    ),
    default=None,
)
def list_cmd(*, artifact_type: str | None) -> None:
    """List artifacts synced to the current project.

    ARTIFACT_TYPE filters output to a single type. Omit to show all.

    Reads from .agentic-beacon/artifacts/. Run 'abc sync' first to populate.
    For agents, shows globally installed files from ~/.config/opencode/agents/
    and ~/.claude/agents/.

    Example:
        abc list
        abc list knowledge
        abc list skills
        abc list contexts
        abc list agents
    """
    if artifact_type == "agents":
        list_global_agents()
        return

    beacon_dir = Path.cwd() / ".agentic-beacon"
    artifacts_dir = beacon_dir / "artifacts"

    if not artifacts_dir.exists():
        console.print("[red]Error:[/red] No synced artifacts found.")
        console.print("Run 'abc sync' to download artifacts from the warehouse.")
        sys.exit(1)

    section_config = {
        "contexts": ("Synced Contexts", "cyan", "Context"),
        "knowledge": ("Synced Knowledge", "green", "File"),
        "skills": ("Synced Skills", "yellow", "Skill"),
    }

    engine = SyncEngine(warehouse_path=Path.cwd(), artifacts_path=artifacts_dir)
    artifacts = engine.list_artifacts(artifact_type)

    for section, files in artifacts.items():
        title, color, col_name = section_config[section]
        table = Table(title=title)
        table.add_column(col_name, style=color)
        for item in files:
            table.add_row(item)
        console.print(table)
        console.print()

    if not artifacts:
        label = artifact_type or "artifacts"
        console.print(
            f"[yellow]No {label} found in .agentic-beacon/artifacts/.[/yellow]"
        )
        console.print("Run 'abc sync' to download artifacts from the warehouse.")
