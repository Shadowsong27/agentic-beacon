"""Adopt command for the abc CLI."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from beacon.core.manifest.beacon import BeaconManifest
from beacon.core.manifest.workspace import WorkspaceConfig
from beacon.domains.adoption.apply import (
    apply_adoption,
    cleanup_unadopted_artifacts,
    commit_pending_session,
)
from beacon.domains.adoption.discovery import discover_candidates
from beacon.domains.adoption.tui import AdoptApp
from beacon.domains.artifact.agent import (
    detect_agents_global,
    install_agent_global,
    read_agent_definition,
)
from beacon.utils.display import is_interactive
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

    Shows all unadopted artifacts by default. Press ``t`` in the TUI to toggle
    to a full view where you can also unadopt currently adopted artifacts.
    Artifacts added within the last few commits are tagged with how recent they are.
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

    candidates = discover_candidates(project_root, warehouse_path)

    if not candidates:
        console.print("[green]✓[/green] No unadopted warehouse artifacts found.")
        return

    if dry_run:
        table = Table(title="Unadopted Artifacts")
        table.add_column("Type", style="cyan")
        table.add_column("Path", style="white")
        table.add_column("Description", style="dim")
        table.add_column("Recently Added", style="yellow")

        for c in candidates:
            recently = (
                f"{c.commits_ago} commit{'s' if c.commits_ago != 1 else ''} ago"
                if c.commits_ago is not None
                else ""
            )
            table.add_row(c.artifact_type, c.path, c.description, recently)

        console.print(table)
        console.print("\n[dim]Run without --dry-run to interactively adopt.[/dim]")
        return

    if not is_interactive():
        console.print("[bold]Unadopted artifacts:[/bold]")
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

    # Per Decision 1: artifacts.agents is a per-project dependency pointer, not
    # an install filter. The adopt TUI represents project intent — pre-tick
    # state must reflect beacon.yaml, not the global install dirs (which can
    # contain agents declared by other projects on the same machine).
    adopted_paths: list[str] = (
        beacon_settings.artifacts.contexts
        + beacon_settings.artifacts.skills
        + beacon_settings.artifacts.agents
    )

    app = AdoptApp(
        candidates,
        adopted_paths,
        project_name=project_root.name,
        warehouse_name=warehouse_path.name,
        warehouse_path=warehouse_path,
    )
    result = app.run()

    if (
        not result.to_adopt
        and not result.to_unadopt
        and not result.to_reject
        and not result.to_defer
    ):
        console.print("[dim]No changes made.[/dim]")
        return

    agent_adoptions = [p for p in result.to_adopt if p.startswith("agents/")]
    agent_unadoptions = [p for p in result.to_unadopt if p.startswith("agents/")]
    non_agent_unadoptions = [
        p for p in result.to_unadopt if not p.startswith("agents/")
    ]

    session_state = {
        **dict.fromkeys(result.to_adopt, "accept"),
        **dict.fromkeys(result.to_reject, "reject"),
        **dict.fromkeys(result.to_defer, "defer"),
    }

    if session_state:
        commit_pending_session(
            session_state,
            candidates,
            project_root,
            warehouse_path,
            artifacts_dir,
            beacon_yaml,
        )

        accepted_non_agents = [
            p for p in result.to_adopt if not p.startswith("agents/")
        ]
        if accepted_non_agents:
            console.print(
                f"[green]✓[/green] Accepted {len(accepted_non_agents)} artifact(s)"
            )
        if result.to_reject:
            console.print(
                f"[yellow]−[/yellow] Rejected {len(result.to_reject)} pending artifact(s)"
            )
        if result.to_defer:
            console.print(f"[dim]Deferred {len(result.to_defer)} artifact(s).[/dim]")

    # All selections (agents + non-agents) are recorded in beacon.yaml via
    # apply_adoption. Agents additionally get a global symlink install below.
    # Per Decision 7, removing an agent from beacon.yaml does NOT uninstall the
    # global symlink — global install state is managed independently of project
    # declaration so an agent can serve multiple projects on the same machine.
    all_unadoptions = non_agent_unadoptions + agent_unadoptions

    if all_unadoptions:
        apply_adoption(beacon_yaml, [], unadoptions=all_unadoptions)
        if non_agent_unadoptions:
            console.print(
                f"[yellow]−[/yellow] Removed {len(non_agent_unadoptions)} artifact(s) from beacon.yaml"
            )

    if agent_adoptions:
        tools = detect_agents_global()
        installed_count = 0
        for agent_path in agent_adoptions:
            agent_file = warehouse_path / agent_path
            if read_agent_definition(agent_file) is None:
                continue
            agent_name = agent_file.name
            for tool in tools:
                install_agent_global(tool, agent_name, agent_file)
            installed_count += 1
        if installed_count:
            console.print(
                f"[green]✓[/green] Recorded {installed_count} agent(s) in beacon.yaml "
                f"and installed globally"
                + (f" for: {', '.join(tools)}" if tools else "")
            )

    if agent_unadoptions:
        # Decision 7: do NOT uninstall global symlinks here. The agent has been
        # removed from beacon.yaml.artifacts.agents (via apply_adoption above);
        # global symlinks remain because other projects on this machine may
        # still depend on them. To explicitly uninstall globally, use
        # `abc agents uninstall <name>` (separate command).
        console.print(
            f"[yellow]−[/yellow] Removed {len(agent_unadoptions)} agent(s) from beacon.yaml "
            f"[dim](global install retained per Decision 7)[/dim]"
        )

    if non_agent_unadoptions:
        cleanup_unadopted_artifacts(
            non_agent_unadoptions,
            artifacts_dir,
            warehouse_path,
            project_root=project_root,
        )
