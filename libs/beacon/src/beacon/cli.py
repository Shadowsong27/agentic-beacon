"""CLI interface for Beacon - Distribute knowledge contexts for AI development."""

import sys
from pathlib import Path
from typing import List, Optional

import click
from loguru import logger
from rich.console import Console
from rich.table import Table

from .core.settings import WarehouseSettings, validate_beacon_directory
from .distributor import WarehouseDistributor
from .initializer import WarehouseInitializer
from .warehouse import WarehouseValidator

console = Console()


def find_warehouse_root() -> Optional[Path]:
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
    """Agentic Beacon CLI (abc) - Guide your agents with distributed knowledge."""
    if verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.remove()
        logger.add(sys.stderr, level="INFO")


@main.group()
def warehouse() -> None:
    """Warehouse management commands."""
    pass


@warehouse.command()
@click.argument("name", type=str)
@click.option(
    "--path",
    type=click.Path(path_type=Path),
    help="Path where warehouse will be created (default: current directory)",
)
@click.option(
    "--org",
    type=str,
    help="Organization name (e.g., 'Acme Corp')",
)
@click.option(
    "--languages",
    type=str,
    help="Primary languages, comma-separated (e.g., 'python,typescript')",
)
@click.option(
    "--domains",
    type=str,
    help="Primary domains, comma-separated (e.g., 'data-platform,web-services')",
)
@click.option(
    "--no-git",
    is_flag=True,
    help="Skip git initialization",
)
@click.option(
    "--no-interactive",
    is_flag=True,
    help="Skip interactive prompts (use defaults or provided options)",
)
def init(
    *,
    name: str,
    path: Optional[Path],
    org: Optional[str],
    languages: Optional[str],
    domains: Optional[str],
    no_git: bool,
    no_interactive: bool,
) -> None:
    """
    Initialize a new warehouse repository.
    
    Creates a complete warehouse structure with contexts, knowledge, and skills.
    
    Example:
        abc warehouse init my-warehouse
        abc warehouse init my-warehouse --org "Acme Corp" --languages python,typescript
    """
    # Determine warehouse path
    warehouse_path = (path or Path.cwd()) / name
    
    # Interactive prompts if not disabled
    if not no_interactive:
        console.print("\n[bold]Initialize New Warehouse[/bold]")
        console.print(f"[dim]Creating warehouse at: {warehouse_path}[/dim]\n")
        
        if not org:
            org = click.prompt(
                "Organization name",
                default="Your Organization",
                type=str,
            )
        
        if not languages:
            languages = click.prompt(
                "Primary languages (comma-separated)",
                default="python",
                type=str,
            )
        
        if not domains:
            domains = click.prompt(
                "Primary domains (comma-separated)",
                default="",
                type=str,
            )
        
        if not no_git:
            init_git = click.confirm("Initialize git repository?", default=True)
            no_git = not init_git
    
    # Set defaults
    org = org or "Your Organization"
    languages_list = [lang.strip() for lang in (languages or "").split(",") if lang.strip()]
    domains_list = [domain.strip() for domain in (domains or "").split(",") if domain.strip()]
    
    # Create initializer and init warehouse
    try:
        initializer = WarehouseInitializer(warehouse_path=warehouse_path)
        result = initializer.init(
            org_name=org,
            languages=languages_list if languages_list else None,
            domains=domains_list if domains_list else None,
            init_git=not no_git,
        )
        
        # Display results
        console.print("\n[bold green]✓ Warehouse initialized successfully![/bold green]\n")
        console.print(f"  [blue]Location:[/blue] {result['warehouse_path']}")
        console.print(f"  [blue]Organization:[/blue] {org}")
        
        if languages_list:
            console.print(f"  [blue]Languages:[/blue] {', '.join(languages_list)}")
        
        if domains_list:
            console.print(f"  [blue]Domains:[/blue] {', '.join(domains_list)}")
        
        if result['git_initialized']:
            console.print(f"  [blue]Git:[/blue] Initialized with initial commit")
        
        # Next steps
        console.print("\n[bold]Next Steps:[/bold]")
        console.print(f"  1. cd {warehouse_path}")
        console.print("  2. Customize contexts, knowledge, and skills")
        console.print("  3. git remote add origin <your-repo-url>")
        console.print("  4. git push -u origin main")
        console.print("\n[bold]Usage:[/bold]")
        console.print(f"  abc setup --warehouse {warehouse_path} --all")
        
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to initialize warehouse: {e}")
        logger.exception("Initialization failed")
        sys.exit(1)


@warehouse.command()
@click.option(
    "--path",
    type=click.Path(path_type=Path),
    help="Path to local warehouse directory",
)
def connect(*, path: Optional[Path]) -> None:
    """
    Connect project to a local warehouse.
    
    Creates .agentic-beacon/config.toml with warehouse connection.
    The warehouse is validated before accepting the connection.
    
    Example:
        abc warehouse connect --path ~/org-warehouse
        abc warehouse connect  # Interactive mode
    """
    # Interactive prompt if path not provided
    if not path:
        console.print("\n[bold]Connect to Warehouse[/bold]")
        console.print("[dim]Enter the path to your local warehouse directory[/dim]\n")
        
        path_str = click.prompt(
            "Warehouse path",
            type=str,
        )
        path = Path(path_str)
    
    # Expand and resolve path
    warehouse_path = path.expanduser().resolve()
    
    console.print(f"\n[blue]Validating:[/blue] {warehouse_path}")
    
    # Validate warehouse structure
    validator = WarehouseValidator()
    validation_result = validator.validate(str(warehouse_path))
    
    if not validation_result.valid:
        console.print("\n[red bold]✗ Invalid warehouse structure[/red bold]\n")
        for error in validation_result.errors:
            console.print(f"  [red]✗[/red] {error}")
        console.print("\n[dim]See examples/sample-warehouse for a valid warehouse structure[/dim]")
        sys.exit(1)
    
    console.print("[green]✓[/green] Warehouse structure validated")
    
    # Create .agentic-beacon directory if it doesn't exist
    beacon_dir = Path.cwd() / ".agentic-beacon"
    beacon_dir.mkdir(exist_ok=True)
    
    # Save connection configuration
    try:
        settings = WarehouseSettings.from_path(warehouse_path)
        console.print("[green]✓[/green] Connection saved")
        
        # Success message
        console.print(f"\n[bold green]✓ Connected to warehouse[/bold green]")
        console.print(f"  [blue]Location:[/blue] {warehouse_path}")
        
        # Next steps
        console.print("\n[bold]Next Steps:[/bold]")
        console.print("  1. Run 'abc setup' to configure artifacts")
        console.print("  2. Run 'abc sync' to download artifacts")
        
    except Exception as e:
        console.print(f"\n[red]Error:[/red] Failed to save connection: {e}")
        logger.exception("Connection failed")
        sys.exit(1)


@main.command()
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
    # Validate mutually exclusive flags
    if manual and agent_assisted:
        console.print("[red]Error:[/red] --manual and --agent-assisted are mutually exclusive")
        sys.exit(1)
    
    # Check for .agentic-beacon directory
    beacon_dir = Path.cwd() / ".agentic-beacon"
    if not beacon_dir.exists():
        console.print("[red]Error:[/red] No warehouse connected.")
        console.print("Run 'abc warehouse connect' first to connect to a warehouse.")
        sys.exit(1)
    
    # Check for config.toml (warehouse connection)
    config_file = beacon_dir / "config.toml"
    if not config_file.exists():
        console.print("[red]Error:[/red] No warehouse connected.")
        console.print("Run 'abc warehouse connect --path <warehouse>' first.")
        sys.exit(1)
    
    beacon_yaml = beacon_dir / "beacon.yaml"
    
    # Check if beacon.yaml already exists
    if beacon_yaml.exists():
        console.print("[yellow]Note:[/yellow] beacon.yaml already exists")
        if not click.confirm("Overwrite existing configuration?", default=False):
            console.print("Setup cancelled.")
            sys.exit(0)
    
    # Determine workflow
    workflow = None
    if manual:
        workflow = "manual"
    elif agent_assisted:
        workflow = "agent-assisted"
    else:
        # Interactive mode
        console.print("\n[bold]Setup Project Configuration[/bold]")
        console.print("[dim]Choose how to configure artifacts for this project:[/dim]\n")
        console.print("  1. [cyan]Agent-assisted[/cyan] - Install project-setup skill for AI agent")
        console.print("  2. [green]Manual[/green] - Create empty template to edit yourself")
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
        else:  # choice == "3"
            console.print("Skipped setup. Run 'abc setup' again when ready.")
            sys.exit(0)
    
    # Execute workflow
    if workflow == "manual":
        _create_beacon_template(beacon_yaml)
        console.print("\n[bold green]✓ Created beacon.yaml template[/bold green]")
        console.print(f"  [blue]Location:[/blue] {beacon_yaml}")
        console.print("\n[bold]Next Steps:[/bold]")
        console.print("  1. Edit .agentic-beacon/beacon.yaml to specify artifacts")
        console.print("  2. Run 'abc sync' to download artifacts from warehouse")
        
    elif workflow == "agent-assisted":
        # TODO: Implement skill installation (Phase 5)
        _create_beacon_template(beacon_yaml)
        console.print("\n[bold green]✓ Created beacon.yaml template[/bold green]")
        console.print("[yellow]Note:[/yellow] Agent-assisted workflow (skill installation) not yet implemented")
        console.print(f"  [blue]Location:[/blue] {beacon_yaml}")


def _create_beacon_template(path: Path) -> None:
    """Create empty beacon.yaml template with commented examples."""
    template = """artifacts:
  knowledge: []
    # Examples:
    # - languages/python/**/*.md
    # - infrastructure/docker-standards.md
    
  skills: []
    # Examples:
    # - code-review
    # - generate-unit-tests
    
  contexts: []
    # Examples:
    # - backend-microservice
    # - data-platform
"""
    path.write_text(template)


@main.command()
def sync() -> None:
    """
    Sync artifacts from warehouse to project.
    
    Reads .agentic-beacon/beacon.yaml and copies specified artifacts
    from the connected warehouse to .agentic-beacon/artifacts/ directory.
    
    Example:
        abc sync  # Sync all artifacts in beacon.yaml
    """
    # Check for .agentic-beacon directory
    beacon_dir = Path.cwd() / ".agentic-beacon"
    if not beacon_dir.exists():
        console.print("[red]Error:[/red] No .agentic-beacon directory found.")
        console.print("Run 'abc warehouse connect' to connect to a warehouse.")
        sys.exit(1)
    
    # Check for config.toml (warehouse connection)
    config_file = beacon_dir / "config.toml"
    if not config_file.exists():
        console.print("[red]Error:[/red] No warehouse connected.")
        console.print("Run 'abc warehouse connect --path <warehouse>' first.")
        sys.exit(1)
    
    # Check for beacon.yaml
    beacon_yaml = beacon_dir / "beacon.yaml"
    if not beacon_yaml.exists():
        console.print("[red]Error:[/red] No beacon.yaml found.")
        console.print("Run 'abc setup' to create artifact configuration.")
        sys.exit(1)
    
    # Load warehouse settings
    try:
        from .core.settings import WarehouseSettings, BeaconSettings
        from .core.sync import SyncEngine
        
        warehouse_settings = WarehouseSettings()
        warehouse_path = Path(warehouse_settings.warehouse.local_path)
        
        # Load beacon.yaml
        beacon_settings = BeaconSettings.from_yaml(beacon_yaml)
        
        # Check if there are any artifacts to sync
        total_artifacts = (
            len(beacon_settings.artifacts.knowledge) +
            len(beacon_settings.artifacts.skills) +
            len(beacon_settings.artifacts.contexts)
        )
        
        if total_artifacts == 0:
            console.print("[yellow]No artifacts configured in beacon.yaml.[/yellow]")
            console.print("Nothing to sync.")
            sys.exit(0)
        
        # Create artifacts directory
        artifacts_dir = beacon_dir / "artifacts"
        artifacts_dir.mkdir(exist_ok=True)
        
        # Initialize sync engine
        sync_engine = SyncEngine(
            warehouse_path=warehouse_path,
            artifacts_path=artifacts_dir
        )
        
        # Collect all artifact paths (expanding globs)
        artifact_paths = []
        console.print(f"\n[blue]Syncing artifacts from warehouse...[/blue]\n")
        
        for artifact_type in ["knowledge", "skills", "contexts"]:
            artifacts_list = getattr(beacon_settings.artifacts, artifact_type)
            for pattern in artifacts_list:
                # Check if pattern contains glob characters
                if "*" in pattern or "?" in pattern or "[" in pattern:
                    # Expand glob
                    matches = sync_engine.expand_glob(pattern)
                    artifact_paths.extend(matches)
                else:
                    # Direct path
                    artifact_paths.append(pattern)
        
        # Sync all artifacts
        copied_count = 0
        skipped_count = 0
        error_count = 0
        
        for artifact_path in artifact_paths:
            result = sync_engine.copy_file(artifact_path)
            
            if result.action == "copied":
                copied_count += 1
            elif result.action == "skipped":
                skipped_count += 1
            elif result.action == "error":
                error_count += 1
                console.print(f"  [red]✗[/red] {artifact_path}: {result.error_message}")
        
        # Display summary
        console.print(f"\n[bold green]✓ Sync complete[/bold green]")
        console.print(f"  [blue]Copied:[/blue] {copied_count} files")
        console.print(f"  [blue]Unchanged:[/blue] {skipped_count} files")
        if error_count > 0:
            console.print(f"  [red]Errors:[/red] {error_count} files")
        
    except Exception as e:
        console.print(f"\n[red]Error:[/red] Sync failed: {e}")
        logger.exception("Sync failed")
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
def update(*, project: Optional[Path], warehouse: Optional[Path]) -> None:
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
def list(*, warehouse: Optional[Path]) -> None:
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
def clean(*, project: Optional[Path]) -> None:
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
def status(*, project: Optional[Path]) -> None:
    """Show current warehouse installation status."""
    project_root = project or find_project_root()
    opencode_dir = project_root / ".opencode"

    if not opencode_dir.exists():
        console.print(f"[yellow]No warehouse content installed at {project_root}[/yellow]")
        console.print("Run 'abc setup' to install.")
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
def delta(*, project: Optional[Path], warehouse: Optional[Path]) -> None:
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
        console.print("Run 'abc setup' first.")
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
                "[dim]ℹ️  Run 'abc update' to sync with warehouse[/dim]"
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
    prompt: str, options: List[str], *, default_all: bool = False
) -> List[str]:
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
