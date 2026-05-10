"""Adopt command for the abc CLI."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from beacon.core.exceptions import RegularFileConflictError
from beacon.core.manifest.beacon import BeaconManifest
from beacon.core.manifest.workspace import WorkspaceConfig
from beacon.domains.adoption.apply import (
    CommitError,
    cleanup_unadopted_artifacts,
    commit_session,
)
from beacon.domains.adoption.discovery import discover_adoptable, discover_pending
from beacon.domains.adoption.tui import AdoptApp
from beacon.utils.display import format_regular_file_conflict, is_interactive
from beacon.utils.git import find_project_root

console = Console()


@click.command()
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview adoptable artifacts without modifying beacon.yaml.",
)
def adopt(*, dry_run: bool) -> None:
    """Adopt warehouse artifacts into beacon.yaml.

    Two flows:
    - Warehouse browser — diff between warehouse and beacon.yaml. Press ``t``
      in the TUI to toggle to a full view where adopted artifacts can be
      unchecked to unadopt them.
    - Pending TODO — entries in pending.yaml from authoring tools
      (record-knowledge, record-skill, manual). Press ``y`` / ``n`` per item.
    """
    project_root = find_project_root()
    beacon_dir = project_root / ".agentic-beacon"
    artifacts_dir = beacon_dir / "artifacts"
    beacon_yaml = beacon_dir / "beacon.yaml"

    if not beacon_dir.exists():
        console.print(f"[red]Error:[/red] No warehouse connected at {project_root}")
        console.print("Run 'abc warehouse connect' first.")
        sys.exit(1)

    if not beacon_yaml.exists():
        console.print("[red]Error:[/red] No beacon.yaml found.")
        console.print("Run 'abc setup' to create artifact configuration.")
        sys.exit(1)

    try:
        warehouse_settings = WorkspaceConfig()
        warehouse_path = Path(warehouse_settings.warehouse.local_path)
    except Exception:
        console.print("[red]Error:[/red] Could not read warehouse connection settings.")
        console.print("Run 'abc warehouse connect' to connect to a warehouse.")
        sys.exit(1)

    beacon_settings = BeaconManifest.from_yaml(beacon_yaml)

    pending_entries = discover_pending(project_root)
    pending_paths = {e.path for e in pending_entries}
    candidates, _ = discover_adoptable(
        warehouse_path, beacon_settings, excluded_paths=pending_paths
    )

    if not candidates and not pending_entries:
        console.print("[green]✓[/green] Nothing to adopt or resolve.")
        return

    if dry_run:
        if pending_entries:
            pending_table = Table(title="Pending TODO")
            pending_table.add_column("Type", style="cyan")
            pending_table.add_column("Path", style="white")
            pending_table.add_column("Source", style="dim")
            for e in pending_entries:
                pending_table.add_row(e.type, e.path, e.source)
            console.print(pending_table)

        if candidates:
            wh_table = Table(title="Warehouse — unadopted artifacts")
            wh_table.add_column("Type", style="cyan")
            wh_table.add_column("Path", style="white")
            wh_table.add_column("Description", style="dim")
            wh_table.add_column("Recently Added", style="yellow")
            for c in candidates:
                recently = (
                    f"{c.commits_ago} commit{'s' if c.commits_ago != 1 else ''} ago"
                    if c.commits_ago is not None
                    else ""
                )
                wh_table.add_row(c.artifact_type, c.path, c.description, recently)
            console.print(wh_table)

        console.print("\n[dim]Run without --dry-run to interactively adopt.[/dim]")
        return

    if not is_interactive():
        if pending_entries:
            console.print("[bold]Pending TODO:[/bold]")
            for e in pending_entries:
                console.print(f"  [{e.type}] {e.path} [dim](via {e.source})[/dim]")
        if candidates:
            console.print("[bold]Warehouse — unadopted artifacts:[/bold]")
            for c in candidates:
                desc = f" — {c.description}" if c.description else ""
                tag = (
                    f" [added {c.commits_ago} commits ago]"
                    if c.commits_ago is not None
                    else ""
                )
                console.print(f"  [{c.artifact_type}] {c.path}{desc}{tag}")
        console.print(
            "\n[dim]Non-interactive mode. Edit beacon.yaml manually to adopt artifacts, "
            "then run [bold]abc sync[/bold].[/dim]"
        )
        return

    adopted_paths: list[str] = (
        beacon_settings.artifacts.contexts
        + beacon_settings.artifacts.skills
        + beacon_settings.artifacts.agents
    )

    app = AdoptApp(
        candidates,
        pending_entries,
        adopted_paths,
        project_name=project_root.name,
        warehouse_name=warehouse_path.name,
        warehouse_path=warehouse_path,
    )
    result = app.run()

    if (
        not result.to_adopt
        and not result.to_unadopt
        and not result.pending_accept
        and not result.pending_reject
    ):
        console.print("[dim]No changes made.[/dim]")
        return

    try:
        wiring_notes = commit_session(
            to_adopt=result.to_adopt,
            to_unadopt=result.to_unadopt,
            pending_accept=result.pending_accept,
            pending_reject=result.pending_reject,
            candidates=candidates,
            pending_entries=pending_entries,
            project_root=project_root,
            warehouse_path=warehouse_path,
            artifacts_path=artifacts_dir,
            beacon_yaml_path=beacon_yaml,
        )
    except CommitError as e:
        if isinstance(e.__cause__, RegularFileConflictError):
            console.print(format_regular_file_conflict(e.__cause__.conflicts))
        else:
            console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    accepted_paths = result.to_adopt + result.pending_accept
    accepted_non_agents = [p for p in accepted_paths if not p.startswith("agents/")]
    accepted_agents = [p for p in accepted_paths if p.startswith("agents/")]

    if accepted_non_agents:
        console.print(
            f"[green]✓[/green] Adopted {len(accepted_non_agents)} artifact(s)"
        )
    if result.pending_reject:
        console.print(
            f"[yellow]−[/yellow] Rejected {len(result.pending_reject)} pending artifact(s)"
        )
    if result.to_unadopt:
        non_agent_unadoptions = [
            p for p in result.to_unadopt if not p.startswith("agents/")
        ]
        agent_unadoptions = [p for p in result.to_unadopt if p.startswith("agents/")]
        if non_agent_unadoptions:
            console.print(
                f"[yellow]−[/yellow] Removed {len(non_agent_unadoptions)} artifact(s) from beacon.yaml"
            )
        if agent_unadoptions:
            console.print(
                f"[yellow]−[/yellow] Removed {len(agent_unadoptions)} agent(s) from beacon.yaml"
            )

    if accepted_agents:
        if wiring_notes:
            console.print(
                f"[green]✓[/green] Adopted {len(accepted_agents)} agent(s) "
                "(see wiring note below)"
            )
        else:
            console.print(
                f"[green]✓[/green] Adopted {len(accepted_agents)} agent(s) "
                "(wired via abc sync or adopt)"
            )

    for note in wiring_notes:
        console.print(f"[yellow]ℹ[/yellow]\n{note}")

    # Agents are handled atomically inside commit_session() (round-3 reject atomicity
    # contract); skip them here to avoid double-processing.
    non_agent_unadoptions = [
        p for p in result.to_unadopt if not p.startswith("agents/")
    ]
    if non_agent_unadoptions:
        cleanup_unadopted_artifacts(
            non_agent_unadoptions,
            artifacts_dir,
            warehouse_path,
            project_root=project_root,
        )
