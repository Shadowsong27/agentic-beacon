"""Setup command for the abc CLI."""

import sys
from pathlib import Path

import click
from rich.console import Console

from beacon.domains.setup.wiring import (
    create_beacon_template,
    install_project_setup_skill,
)

console = Console()


@click.command()
@click.option(
    "--manual",
    is_flag=True,
    help="Create empty beacon.yaml template without interactive prompts",
)
@click.option(
    "--agent-assisted",
    is_flag=True,
    help="Install project-setup skill for agent-assisted configuration",
)
def setup(*, manual: bool, agent_assisted: bool) -> None:
    """
    Initialize project artifact configuration.

    Creates beacon.yaml file that declares which artifacts this project uses.
    Supports three workflows: agent-assisted, manual, or skip.

    Example:
        abc setup --manual  # Create empty template
        abc setup           # Interactive mode
    """
    if manual and agent_assisted:
        console.print(
            "[red]Error:[/red] --manual and --agent-assisted are mutually exclusive"
        )
        sys.exit(1)

    beacon_dir = Path.cwd() / ".agentic-beacon"
    if not beacon_dir.exists():
        console.print("[red]Error:[/red] No warehouse connected.")
        console.print("Run 'abc warehouse connect' first to connect to a warehouse.")
        sys.exit(1)

    config_file = beacon_dir / "config.toml"
    if not config_file.exists():
        console.print("[red]Error:[/red] No warehouse connected.")
        console.print("Run 'abc warehouse connect --path <warehouse>' first.")
        sys.exit(1)

    beacon_yaml = beacon_dir / "beacon.yaml"

    if beacon_yaml.exists():
        console.print("[yellow]Note:[/yellow] beacon.yaml already exists")
        if not click.confirm("Overwrite existing configuration?", default=False):
            console.print("Setup cancelled.")
            sys.exit(0)

    workflow = None
    if manual:
        workflow = "manual"
    elif agent_assisted:
        workflow = "agent-assisted"
    else:
        console.print("\n[bold]Setup Project Configuration[/bold]")
        console.print(
            "[dim]Choose how to configure artifacts for this project:[/dim]\n"
        )
        console.print(
            "  1. [cyan]Agent-assisted[/cyan] - Install project-setup skill for AI agent"
        )
        console.print(
            "  2. [green]Manual[/green] - Create empty template to edit yourself"
        )
        console.print("  3. [yellow]Skip[/yellow] - Configure later\n")

        choice = click.prompt(
            "Select workflow",
            type=click.Choice(["1", "2", "3"], case_sensitive=False),
            default="2",
        )

        if choice == "1":
            workflow = "agent-assisted"
        elif choice == "2":
            workflow = "manual"
        else:
            console.print("Skipped setup. Run 'abc setup' again when ready.")
            sys.exit(0)

    if workflow == "manual":
        create_beacon_template(beacon_yaml)
        console.print("\n[bold green]✓ Created beacon.yaml template[/bold green]")
        console.print(f"  [blue]Location:[/blue] {beacon_yaml}")
        console.print("\n[bold]Next Steps:[/bold]")
        console.print("  1. Edit .agentic-beacon/beacon.yaml to specify artifacts")
        console.print("  2. Run 'abc sync' to download artifacts from warehouse")
        console.print("\n[bold]Artifact Types:[/bold]")
        console.print(
            "  • [cyan]knowledge[/cyan], [cyan]contexts[/cyan], [cyan]skills[/cyan] — project-scoped, tracked in beacon.yaml"
        )
        console.print(
            "  • [magenta]agents[/magenta] — globally installed on your machine (not in beacon.yaml)"
        )
        console.print(
            "    Agent definitions are installed globally — use [bold]abc install agents/<name>[/bold] to install them"
        )

    elif workflow == "agent-assisted":
        create_beacon_template(beacon_yaml)
        install_project_setup_skill(beacon_dir)
        console.print("\n[bold green]✓ Agent-assisted setup ready[/bold green]")
        console.print(f"  [blue]beacon.yaml:[/blue] {beacon_yaml}")
        console.print(f"  [blue]Catalog:[/blue] {beacon_dir / 'warehouse-catalog.md'}")
        console.print("\n[bold]Paste this into your agent:[/bold]")
        console.print(
            "\n[on dark_green] Read `.agentic-beacon/warehouse-catalog.md` to see "
            "what artifacts are available in the connected warehouse. Analyse this "
            "project, then update `.agentic-beacon/beacon.yaml` with the artifacts "
            "that are relevant. Run `abc sync` when done. [/on dark_green]\n"
        )
