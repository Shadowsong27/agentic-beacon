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
    warehouse_uncommitted_paths,
)
from beacon.domains.adoption.discovery import discover_adoptable, is_agent_installed
from beacon.domains.adoption.models import AdoptCandidate
from beacon.domains.adoption.tui import AdoptApp
from beacon.domains.artifact.agent import (
    detect_agents_global,
    install_agent_global,
    read_agent_definition,
)
from beacon.domains.artifact.skill import wire_skills_post_sync
from beacon.domains.distribution.distributor import WarehouseDistributor
from beacon.domains.distribution.sync_engine import SyncEngine
from beacon.domains.setup.wiring import (
    wire_contexts_claudecode,
    wire_contexts_opencode,
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

    candidates, _ = discover_adoptable(warehouse_path, beacon_settings)

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

    adopted_paths: list[str] = (
        beacon_settings.artifacts.contexts + beacon_settings.artifacts.skills
    )
    try:
        distributor = WarehouseDistributor(
            warehouse_root=warehouse_path, target_root=warehouse_path
        )
        available_agents = distributor.list_available().get("agents", [])
        adopted_paths += [p for p in available_agents if is_agent_installed(p)]
    except Exception:
        pass

    app = AdoptApp(
        candidates,
        adopted_paths,
        project_name=project_root.name,
        warehouse_name=warehouse_path.name,
    )
    result = app.run()

    if not result.to_adopt and not result.to_unadopt:
        console.print("[dim]No changes made.[/dim]")
        return

    path_to_candidate: dict[str, AdoptCandidate] = {c.path: c for c in candidates}
    agent_adoptions = [p for p in result.to_adopt if p.startswith("agents/")]
    non_agent_selections = [
        path_to_candidate[p]
        for p in result.to_adopt
        if p in path_to_candidate and not p.startswith("agents/")
    ]
    agent_unadoptions = [p for p in result.to_unadopt if p.startswith("agents/")]
    non_agent_unadoptions = [
        p for p in result.to_unadopt if not p.startswith("agents/")
    ]

    # All selections (agents + non-agents) are recorded in beacon.yaml via
    # apply_adoption. Agents additionally get a global symlink install below.
    # Per Decision 7, removing an agent from beacon.yaml does NOT uninstall the
    # global symlink — global install state is managed independently of project
    # declaration so an agent can serve multiple projects on the same machine.
    agent_selections = [
        path_to_candidate[p] for p in agent_adoptions if p in path_to_candidate
    ]
    all_selections = non_agent_selections + agent_selections
    all_unadoptions = non_agent_unadoptions + agent_unadoptions

    apply_adoption(beacon_yaml, all_selections, unadoptions=all_unadoptions)
    if non_agent_selections:
        console.print(
            f"[green]✓[/green] Added {len(non_agent_selections)} artifact(s) to beacon.yaml"
        )
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

    if non_agent_selections:
        try:
            sync_engine = SyncEngine(
                warehouse_path=warehouse_path,
                artifacts_path=artifacts_dir,
            )

            new_artifact_paths: list[str] = []
            for c in non_agent_selections:
                if c.artifact_type == "skills":
                    new_artifact_paths.append(c.path.rstrip("/") + "/")
                else:
                    new_artifact_paths.append(c.path)

            expanded: list[str] = []
            for path in new_artifact_paths:
                if path.endswith("/"):
                    matches = sync_engine.expand_glob(f"{path.rstrip('/')}/**/*")
                    expanded.extend(matches)
                else:
                    expanded.append(path)

            if expanded:
                sync_engine.sync_all(
                    artifact_paths=expanded,
                    dry_run=False,
                )
                dirty = warehouse_uncommitted_paths(warehouse_path)
                for c in non_agent_selections:
                    rel = c.path.rstrip("/")
                    note = (
                        " [yellow](has local edits in warehouse)[/yellow]"
                        if rel in dirty
                        else ""
                    )
                    console.print(f"[green]✓[/green] Symlink created: {c.path}{note}")

                for c in non_agent_selections:
                    if c.artifact_type == "contexts":
                        wire_contexts_opencode(project_root, artifacts_dir)
                        wire_contexts_claudecode(project_root, artifacts_dir)
                        break

                has_skills = any(
                    c.artifact_type == "skills" for c in non_agent_selections
                )
                if has_skills:
                    wire_skills_post_sync(project_root, artifacts_dir)

        except Exception as e:
            console.print(
                f"[yellow]⚠[/yellow] Post-adoption sync failed: {e}\n"
                "  Run [bold]abc sync[/bold] to sync and wire adopted artifacts."
            )

    if non_agent_unadoptions:
        cleanup_unadopted_artifacts(
            non_agent_unadoptions,
            artifacts_dir,
            warehouse_path,
            project_root=project_root,
        )
