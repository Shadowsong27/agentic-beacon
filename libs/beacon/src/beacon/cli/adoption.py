"""Adopt command for the abc CLI."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from beacon.core.manifest.beacon import BeaconManifest
from beacon.core.manifest.workspace import WorkspaceConfig
from beacon.domains.adoption.adopter import (
    AdoptApp,
    AdoptCandidate,
    apply_adoption,
    discover_adoptable,
    is_agent_installed,
)
from beacon.domains.artifact.agent import (
    detect_agents_global,
    install_agent_global,
    read_agent_definition,
    uninstall_agent_global,
)
from beacon.domains.artifact.skill import wire_skills_post_sync
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
    from beacon.domains.adoption.adopter import (
        cleanup_unadopted_artifacts,
    )

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
        beacon_settings.artifacts.contexts
        + beacon_settings.artifacts.skills
        + beacon_settings.artifacts.knowledge
    )
    try:
        from beacon.domains.distribution.distributor import WarehouseDistributor

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

    apply_adoption(beacon_yaml, non_agent_selections, unadoptions=non_agent_unadoptions)
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
            content = read_agent_definition(agent_file)
            if content is None:
                continue
            agent_name = agent_file.name
            for tool in tools:
                install_agent_global(tool, agent_name, content)
            installed_count += 1
        if installed_count:
            console.print(
                f"[green]✓[/green] Installed {installed_count} agent(s) globally"
                + (f" for: {', '.join(tools)}" if tools else "")
            )

    if agent_unadoptions:
        removed_count = 0
        for agent_path in agent_unadoptions:
            agent_name = Path(agent_path).name
            removed_count += uninstall_agent_global(agent_name)
        if removed_count:
            console.print(
                f"[yellow]−[/yellow] Uninstalled {removed_count} agent(s) from global directories"
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

            expanded = sync_engine.expand_artifact_paths(new_artifact_paths)

            if expanded:
                sync_engine.sync_all(
                    artifact_paths=expanded,
                    preserve=False,
                    dry_run=False,
                )
                console.print(
                    f"[green]✓[/green] Synced and wired: "
                    f"{', '.join(c.path for c in non_agent_selections)}"
                )

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
            non_agent_unadoptions, artifacts_dir, warehouse_path
        )
