"""CLI interface for Beacon - Distribute knowledge contexts for AI development."""

import sys
from pathlib import Path

import click
from loguru import logger
from rich.console import Console
from rich.table import Table

from .distributor import WarehouseDistributor

console = Console()


def find_warehouse_root() -> Path | None:
    """
    Find warehouse root by looking for warehouse markers.

    Returns:
        Path to warehouse root or None if not found
    """
    current = Path.cwd()

    # Check current directory and parents
    for path in [current, *current.parents]:
        # Check for warehouse markers
        if (
            (path / "contexts").exists()
            and (path / "knowledge").exists()
            and (path / "skills").exists()
        ):
            return path

    return None


def find_project_root() -> Path:
    """
    Find project root (current directory or first parent with .git).

    Returns:
        Path to project root
    """
    current = Path.cwd()

    # Check for .git directory
    for path in [current, *current.parents]:
        if (path / ".git").exists():
            return path

    # Fallback to current directory
    return current


@click.group()
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
def main(*, verbose: bool) -> None:
    """Beacon - Guide your agents with distributed knowledge."""
    if verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.remove()
        logger.add(sys.stderr, level="INFO")


@main.command()
@click.option(
    "--warehouse",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Path to warehouse repository (auto-detected if not provided)",
)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Path to project root (auto-detected if not provided)",
)
@click.option(
    "--context",
    "-c",
    "contexts",
    multiple=True,
    help="Context to install (e.g., 'global', 'python'). Can be specified multiple times.",
)
@click.option(
    "--knowledge",
    "-k",
    "knowledge_scopes",
    multiple=True,
    help="Knowledge scope to install (e.g., 'global', 'languages/python'). Can be specified multiple times.",
)
@click.option(
    "--skill",
    "-s",
    "skills",
    multiple=True,
    help="Skill to install (e.g., 'example-skill'). Can be specified multiple times.",
)
@click.option(
    "--all",
    "install_all",
    is_flag=True,
    help="Install all available contexts, knowledge, and skills",
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Interactive mode to select content",
)
def setup(
    *,
    warehouse: Path | None,
    project: Path | None,
    contexts: tuple[str, ...],
    knowledge_scopes: tuple[str, ...],
    skills: tuple[str, ...],
    install_all: bool,
    interactive: bool,
) -> None:
    """Setup warehouse content in project .opencode directory."""
    # Find warehouse and project roots
    warehouse_root = warehouse or find_warehouse_root()
    if not warehouse_root:
        console.print(
            "[red]Error:[/red] Could not find warehouse root. "
            "Specify --warehouse or run from warehouse directory."
        )
        sys.exit(1)

    project_root = project or find_project_root()

    console.print(f"[blue]Warehouse:[/blue] {warehouse_root}")
    console.print(f"[blue]Project:[/blue] {project_root}")
    console.print()

    # Create distributor
    distributor = WarehouseDistributor(
        warehouse_root=warehouse_root, target_root=project_root
    )

    # Get available content
    available = distributor.list_available()

    # Determine what to install
    if interactive:
        contexts_list = _interactive_select(
            "Select contexts:", available["contexts"], default_all=True
        )
        knowledge_list = _interactive_select(
            "Select knowledge scopes:", available["knowledge"], default_all=True
        )
        skills_list = _interactive_select(
            "Select skills:", available["skills"], default_all=False
        )
    elif install_all:
        contexts_list = available["contexts"]
        knowledge_list = available["knowledge"]
        skills_list = available["skills"]
    else:
        contexts_list = list(contexts)
        knowledge_list = list(knowledge_scopes)
        skills_list = list(skills)

    # Validate selections
    if not contexts_list and not knowledge_list and not skills_list:
        console.print(
            "[yellow]Warning:[/yellow] No content selected. Use --all, --interactive, "
            "or specify content with --context, --knowledge, --skill"
        )
        sys.exit(1)

    # Display what will be installed
    console.print("[bold]Installing:[/bold]")
    if contexts_list:
        console.print(f"  [green]Contexts:[/green] {', '.join(contexts_list)}")
    if knowledge_list:
        console.print(f"  [green]Knowledge:[/green] {', '.join(knowledge_list)}")
    if skills_list:
        console.print(f"  [green]Skills:[/green] {', '.join(skills_list)}")
    console.print()

    # Perform distribution
    try:
        result = distributor.setup(
            contexts=contexts_list,
            knowledge_scopes=knowledge_list,
            skills=skills_list,
        )

        # Save configuration
        distributor._save_config(
            contexts=contexts_list,
            knowledge_scopes=knowledge_list,
            skills=skills_list,
        )

        # Display results
        console.print("[bold green]✓ Setup complete![/bold green]")
        console.print(f"  [blue]Target:[/blue] {result['target_dir']}")
        console.print(f"  [blue]Contexts:[/blue] {result['contexts']} files")
        console.print(f"  [blue]Knowledge:[/blue] {result['knowledge']} files")
        console.print(f"  [blue]Skills:[/blue] {result['skills']} directories")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Setup failed")
        sys.exit(1)


@main.command()
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Path to project root (auto-detected if not provided)",
)
@click.option(
    "--warehouse",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Path to warehouse repository (auto-detected if not provided)",
)
def update(*, project: Path | None, warehouse: Path | None) -> None:
    """Update existing .opencode content from warehouse."""
    warehouse_root = warehouse or find_warehouse_root()
    if not warehouse_root:
        console.print(
            "[red]Error:[/red] Could not find warehouse root. Specify --warehouse."
        )
        sys.exit(1)

    project_root = project or find_project_root()
    opencode_dir = project_root / ".opencode"

    if not opencode_dir.exists():
        console.print(
            f"[red]Error:[/red] No .opencode directory found at {project_root}"
        )
        console.print("Run 'agentic setup' first.")
        sys.exit(1)

    console.print(f"[blue]Updating:[/blue] {opencode_dir}")

    try:
        distributor = WarehouseDistributor(
            warehouse_root=warehouse_root, target_root=project_root
        )
        result = distributor.update()

        console.print("[bold green]✓ Update complete![/bold green]")
        console.print(f"  [blue]Contexts:[/blue] {result['contexts']} files")
        console.print(f"  [blue]Knowledge:[/blue] {result['knowledge']} files")
        console.print(f"  [blue]Skills:[/blue] {result['skills']} directories")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Update failed")
        sys.exit(1)


@main.command()
@click.option(
    "--warehouse",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Path to warehouse repository (auto-detected if not provided)",
)
def list(*, warehouse: Path | None) -> None:
    """List available warehouse content."""
    warehouse_root = warehouse or find_warehouse_root()
    if not warehouse_root:
        console.print(
            "[red]Error:[/red] Could not find warehouse root. Specify --warehouse."
        )
        sys.exit(1)

    distributor = WarehouseDistributor(
        warehouse_root=warehouse_root, target_root=Path.cwd()
    )
    available = distributor.list_available()

    # Display contexts
    if available["contexts"]:
        table = Table(title="Available Contexts")
        table.add_column("Context", style="cyan")
        for context in available["contexts"]:
            table.add_row(context)
        console.print(table)
        console.print()

    # Display knowledge
    if available["knowledge"]:
        table = Table(title="Available Knowledge Scopes")
        table.add_column("Scope", style="green")
        for scope in available["knowledge"]:
            table.add_row(scope)
        console.print(table)
        console.print()

    # Display skills
    if available["skills"]:
        table = Table(title="Available Skills")
        table.add_column("Skill", style="yellow")
        for skill in available["skills"]:
            table.add_row(skill)
        console.print(table)


@main.command()
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Path to project root (auto-detected if not provided)",
)
@click.confirmation_option(prompt="Are you sure you want to remove .opencode?")
def clean(*, project: Path | None) -> None:
    """Remove .opencode directory from project."""
    project_root = project or find_project_root()
    warehouse_root = find_warehouse_root()

    if not warehouse_root:
        console.print(
            "[yellow]Warning:[/yellow] Could not find warehouse root. "
            "Proceeding with clean anyway."
        )
        warehouse_root = Path.cwd()

    distributor = WarehouseDistributor(
        warehouse_root=warehouse_root, target_root=project_root
    )

    if distributor.clean():
        console.print(f"[green]✓ Removed:[/green] {project_root / '.opencode'}")
    else:
        console.print(f"[yellow]No .opencode directory found at {project_root}[/yellow]")


@main.command()
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Path to project root (auto-detected if not provided)",
)
def status(*, project: Path | None) -> None:
    """Show current warehouse installation status."""
    project_root = project or find_project_root()
    opencode_dir = project_root / ".opencode"

    if not opencode_dir.exists():
        console.print(f"[yellow]No warehouse content installed at {project_root}[/yellow]")
        console.print("Run 'beacon setup' to install.")
        sys.exit(0)

    console.print(f"[blue]Installation:[/blue] {opencode_dir}")

    # Read configuration
    warehouse_root = find_warehouse_root() or Path.cwd()
    distributor = WarehouseDistributor(
        warehouse_root=warehouse_root, target_root=project_root
    )
    config = distributor._read_config()

    # Display installed content
    if config.get("contexts"):
        table = Table(title="Installed Contexts")
        table.add_column("Context", style="cyan")
        for context in config["contexts"]:
            table.add_row(context)
        console.print(table)
        console.print()

    if config.get("knowledge_scopes"):
        table = Table(title="Installed Knowledge Scopes")
        table.add_column("Scope", style="green")
        for scope in config["knowledge_scopes"]:
            table.add_row(scope)
        console.print(table)
        console.print()

    if config.get("skills"):
        table = Table(title="Installed Skills")
        table.add_column("Skill", style="yellow")
        for skill in config["skills"]:
            table.add_row(skill)
        console.print(table)


@main.command()
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Path to project root (auto-detected if not provided)",
)
@click.option(
    "--warehouse",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Path to warehouse repository (auto-detected if not provided)",
)
def delta(*, project: Path | None, warehouse: Path | None) -> None:
    """
    Compare target installation with warehouse to find differences.
    
    Shows:
    - New files in target (potential contributions back to warehouse)
    - Modified files in target (local customizations)  
    - Missing files in target (content available in warehouse)
    """
    warehouse_root = warehouse or find_warehouse_root()
    if not warehouse_root:
        console.print(
            "[red]Error:[/red] Could not find warehouse root. Specify --warehouse."
        )
        sys.exit(1)

    project_root = project or find_project_root()
    opencode_dir = project_root / ".opencode"

    if not opencode_dir.exists():
        console.print(
            f"[red]Error:[/red] No .opencode directory found at {project_root}"
        )
        console.print("Run 'beacon setup' first.")
        sys.exit(1)

    console.print(f"[blue]Comparing:[/blue] {opencode_dir}")
    console.print(f"[blue]Warehouse:[/blue] {warehouse_root}")
    console.print()

    try:
        distributor = WarehouseDistributor(
            warehouse_root=warehouse_root, target_root=project_root
        )
        result = distributor.delta()

        # Display new files in target
        if result["new_in_target"]:
            table = Table(title="[green]New in Target[/green] (Potential Contributions)")
            table.add_column("File", style="green")
            for file in result["new_in_target"]:
                table.add_row(file)
            console.print(table)
            console.print()
            console.print(
                "[dim]💡 These files could be contributed back to the warehouse[/dim]"
            )
            console.print()

        # Display modified files in target
        if result["modified_in_target"]:
            table = Table(title="[yellow]Modified in Target[/yellow] (Local Changes)")
            table.add_column("File", style="yellow")
            for file in result["modified_in_target"]:
                table.add_row(file)
            console.print(table)
            console.print()
            console.print(
                "[dim]⚠️  These files differ from warehouse - may be local customizations[/dim]"
            )
            console.print()

        # Display missing files in target
        if result["missing_in_target"]:
            table = Table(title="[red]Missing in Target[/red] (Available in Warehouse)")
            table.add_column("File", style="red")
            for file in result["missing_in_target"]:
                table.add_row(file)
            console.print(table)
            console.print()
            console.print(
                "[dim]ℹ️  Run 'beacon update' to sync with warehouse[/dim]"
            )
            console.print()

        # Summary
        if not any([result["new_in_target"], result["modified_in_target"], result["missing_in_target"]]):
            console.print("[green]✓ Target and warehouse are in sync![/green]")
        else:
            console.print("[bold]Summary:[/bold]")
            console.print(f"  [green]New:[/green] {len(result['new_in_target'])} files")
            console.print(f"  [yellow]Modified:[/yellow] {len(result['modified_in_target'])} files")
            console.print(f"  [red]Missing:[/red] {len(result['missing_in_target'])} files")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Delta comparison failed")
        sys.exit(1)


def _interactive_select(
    prompt: str, options: list[str], *, default_all: bool = False
) -> list[str]:
    """Interactive selection of options."""
    if not options:
        return []

    console.print(f"\n[bold]{prompt}[/bold]")
    console.print("[dim]Enter numbers separated by commas, or 'all' for all options[/dim]")

    for i, option in enumerate(options, 1):
        console.print(f"  {i}. {option}")

    if default_all:
        default_text = " [default: all]"
    else:
        default_text = ""

    selection = click.prompt(
        f"\nSelection{default_text}",
        default="all" if default_all else "",
        show_default=False,
    )

    if selection.lower() == "all":
        return options

    if not selection:
        return []

    # Parse comma-separated numbers
    try:
        indices = [int(x.strip()) for x in selection.split(",")]
        return [options[i - 1] for i in indices if 1 <= i <= len(options)]
    except (ValueError, IndexError):
        console.print("[red]Invalid selection. Using none.[/red]")
        return []


if __name__ == "__main__":
    main()
