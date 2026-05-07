"""Setup command for the abc CLI."""

import sys
from pathlib import Path

import click
from rich.console import Console

from beacon.domains.setup.wiring import create_beacon_template

console = Console()


@click.command()
def setup() -> None:
    """
    Initialize project artifact configuration.

    Creates beacon.yaml file that declares which artifacts this project uses.

    Example:
        abc setup
    """
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

    create_beacon_template(beacon_yaml)
    # Note: .gitignore entries for .claude/agents/ and .opencode/agents/ are
    # added later by `abc sync` or `abc adopt` accept when agents are first
    # declared. Doing it here unconditionally would dirty the .gitignore on
    # projects that never declare agents.
    console.print("\n[bold green]✓ Created beacon.yaml template[/bold green]")
    console.print(f"  [blue]Location:[/blue] {beacon_yaml}")
    console.print("\n[bold]Next Steps:[/bold]")
    console.print("  1. Run 'abc adopt' to select artifacts from the warehouse")
    console.print("  2. Or edit .agentic-beacon/beacon.yaml directly")
    console.print("  3. Run 'abc sync' to create artifact symlinks")
    console.print("\n[bold]Artifact Types:[/bold]")
    console.print(
        "  • [cyan]knowledge[/cyan], [cyan]contexts[/cyan], [cyan]skills[/cyan] — project-scoped, tracked in beacon.yaml"
    )
    console.print(
        "  • [magenta]agents[/magenta] — project-scoped, declared in beacon.yaml; "
        "run 'abc adopt' or 'abc sync' to wire agents"
    )
