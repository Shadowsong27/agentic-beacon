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
@click.version_option(package_name="agentic-beacon")
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
  contexts: []
    # Filename within the contexts/ directory in warehouse
    # Examples:
    # - AGENTS.global.md
    # - AGENTS.python.md
    # - team-standards.md

  knowledge: []
    # Full warehouse-relative paths (supports globs)
    # Examples:
    # - knowledge/global/**/*.md
    # - knowledge/languages/python/**/*.md
    # - knowledge/domains/data-platform/*.md

  skills: []
    # Skill directory name in warehouse skills/ directory
    # Examples:
    # - code-review
    # - generate-unit-tests
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

        # Resolve contexts: filename within contexts/ (e.g. "AGENTS.global.md" → "contexts/AGENTS.global.md")
        for context_name in beacon_settings.artifacts.contexts:
            artifact_paths.append(f"contexts/{context_name}")

        # Resolve knowledge: full warehouse-relative paths (e.g. "knowledge/global/**/*.md")
        for pattern in beacon_settings.artifacts.knowledge:
            if "*" in pattern or "?" in pattern or "[" in pattern:
                matches = sync_engine.expand_glob(pattern)
                artifact_paths.extend(matches)
            else:
                artifact_paths.append(pattern)

        # Resolve skills: "record-decision" → all files in "skills/record-decision/"
        for skill_name in beacon_settings.artifacts.skills:
            skill_dir = warehouse_path / "skills" / skill_name
            if skill_dir.exists() and skill_dir.is_dir():
                skill_files = sync_engine.expand_glob(f"skills/{skill_name}/**/*")
                artifact_paths.extend(skill_files)
            else:
                artifact_paths.append(f"skills/{skill_name}")
        
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
def update(*, project: Optional[Path]) -> None:
    """Update existing synced artifacts from warehouse (re-runs sync, overwrites changes)."""
    project_root = project or find_project_root()
    beacon_dir = project_root / ".agentic-beacon"

    if not beacon_dir.exists():
        console.print(f"[red]Error:[/red] No warehouse connected at {project_root}")
        console.print("Run 'abc warehouse connect' first.")
        sys.exit(1)

    if not (beacon_dir / "beacon.yaml").exists():
        console.print(f"[red]Error:[/red] No beacon.yaml found.")
        console.print("Run 'abc setup' to create artifact configuration.")
        sys.exit(1)

    console.print(f"[blue]Updating artifacts from warehouse...[/blue]")

    try:
        from .core.settings import WarehouseSettings, BeaconSettings
        from .core.sync import SyncEngine

        warehouse_settings = WarehouseSettings()
        warehouse_path = Path(warehouse_settings.warehouse.local_path)
        beacon_settings = BeaconSettings.from_yaml(beacon_dir / "beacon.yaml")

        artifacts_dir = beacon_dir / "artifacts"
        artifacts_dir.mkdir(exist_ok=True)

        sync_engine = SyncEngine(warehouse_path=warehouse_path, artifacts_path=artifacts_dir)

        artifact_paths: list[str] = []

        for context_name in beacon_settings.artifacts.contexts:
            artifact_paths.append(f"contexts/{context_name}")

        for pattern in beacon_settings.artifacts.knowledge:
            if "*" in pattern or "?" in pattern or "[" in pattern:
                artifact_paths.extend(sync_engine.expand_glob(pattern))
            else:
                artifact_paths.append(pattern)

        for skill_name in beacon_settings.artifacts.skills:
            skill_dir = warehouse_path / "skills" / skill_name
            if skill_dir.exists() and skill_dir.is_dir():
                artifact_paths.extend(sync_engine.expand_glob(f"skills/{skill_name}/**/*"))
            else:
                artifact_paths.append(f"skills/{skill_name}")

        copied_count = 0
        overwritten_count = 0
        error_count = 0

        for artifact_path in artifact_paths:
            # Force update: remove destination first so idempotent check doesn't skip
            dest = artifacts_dir / artifact_path
            if dest.exists():
                dest.unlink()
                overwritten_count += 1
            result = sync_engine.copy_file(artifact_path)
            if result.action == "copied":
                copied_count += 1
            elif result.action == "error":
                error_count += 1
                console.print(f"  [red]✗[/red] {artifact_path}: {result.error_message}")

        console.print(f"\n[bold green]✓ Update complete![/bold green]")
        console.print(f"  [blue]Updated:[/blue] {overwritten_count} files")
        console.print(f"  [blue]New:[/blue] {copied_count - overwritten_count if copied_count > overwritten_count else 0} files")
        if error_count > 0:
            console.print(f"  [red]Errors:[/red] {error_count} files")

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
@click.confirmation_option(prompt="Are you sure you want to remove synced artifacts?")
def clean(*, project: Optional[Path]) -> None:
    """Remove synced artifacts from project (.agentic-beacon/artifacts/)."""
    import shutil

    project_root = project or find_project_root()
    artifacts_dir = project_root / ".agentic-beacon" / "artifacts"

    if artifacts_dir.exists():
        shutil.rmtree(artifacts_dir)
        console.print(f"[green]✓ Removed:[/green] {artifacts_dir}")
    else:
        console.print(f"[yellow]No artifacts found at {artifacts_dir}[/yellow]")


@main.command()
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Path to project root (auto-detected if not provided)",
)
def status(*, project: Optional[Path]) -> None:
    """Show current warehouse installation status."""
    project_root = project or find_project_root()
    beacon_dir = project_root / ".agentic-beacon"
    artifacts_dir = beacon_dir / "artifacts"
    beacon_yaml = beacon_dir / "beacon.yaml"

    if not beacon_dir.exists():
        console.print(f"[yellow]No warehouse connected at {project_root}[/yellow]")
        console.print("Run 'abc warehouse connect' to connect to a warehouse.")
        sys.exit(0)

    # Show warehouse connection
    config_file = beacon_dir / "config.toml"
    if config_file.exists():
        try:
            from .core.settings import WarehouseSettings
            warehouse_settings = WarehouseSettings()
            console.print(f"[blue]Warehouse:[/blue] {warehouse_settings.warehouse.local_path}")
        except Exception:
            console.print(f"[blue]Config:[/blue] {config_file}")

    if not artifacts_dir.exists():
        console.print(f"\n[yellow]No artifacts synced yet.[/yellow]")
        console.print("Run 'abc sync' to download artifacts from warehouse.")
        sys.exit(0)

    # Show beacon.yaml configuration
    if beacon_yaml.exists():
        from .core.settings import BeaconSettings
        beacon_settings = BeaconSettings.from_yaml(beacon_yaml)

        if beacon_settings.artifacts.contexts:
            table = Table(title="Configured Contexts")
            table.add_column("Context", style="cyan")
            for ctx in beacon_settings.artifacts.contexts:
                synced = (artifacts_dir / "contexts" / f"AGENTS.{ctx}.md").exists()
                status_str = "[green]✓[/green]" if synced else "[red]✗[/red]"
                table.add_row(f"{status_str} {ctx}")
            console.print(table)
            console.print()

        if beacon_settings.artifacts.knowledge:
            table = Table(title="Configured Knowledge Patterns")
            table.add_column("Pattern", style="green")
            for pattern in beacon_settings.artifacts.knowledge:
                table.add_row(pattern)
            console.print(table)
            console.print()

        if beacon_settings.artifacts.skills:
            table = Table(title="Configured Skills")
            table.add_column("Skill", style="yellow")
            for skill in beacon_settings.artifacts.skills:
                synced = (artifacts_dir / "skills" / skill).exists()
                status_str = "[green]✓[/green]" if synced else "[red]✗[/red]"
                table.add_row(f"{status_str} {skill}")
            console.print(table)
            console.print()

    # Count synced files
    import os
    file_count = sum(len(files) for _, _, files in os.walk(str(artifacts_dir)))
    console.print(f"[blue]Artifacts location:[/blue] {artifacts_dir}")
    console.print(f"[blue]Total synced files:[/blue] {file_count}")


@main.command()
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Path to project root (auto-detected if not provided)",
)
def delta(*, project: Optional[Path]) -> None:
    """
    Compare synced artifacts with warehouse to find differences.

    Shows:
    - New files added locally (potential contributions back to warehouse)
    - Modified files that differ from warehouse
    - Missing files available in warehouse but not synced
    """
    import hashlib

    project_root = project or find_project_root()
    beacon_dir = project_root / ".agentic-beacon"
    artifacts_dir = beacon_dir / "artifacts"
    beacon_yaml = beacon_dir / "beacon.yaml"

    if not artifacts_dir.exists():
        console.print(f"[red]Error:[/red] No artifacts synced at {project_root}")
        console.print("Run 'abc sync' first.")
        sys.exit(1)

    # Load warehouse settings
    try:
        from .core.settings import WarehouseSettings, BeaconSettings
        from .core.sync import SyncEngine

        warehouse_settings = WarehouseSettings()
        warehouse_path = Path(warehouse_settings.warehouse.local_path)
    except Exception as e:
        console.print(f"[red]Error:[/red] Could not load warehouse settings: {e}")
        sys.exit(1)

    console.print(f"[blue]Comparing:[/blue] {artifacts_dir}")
    console.print(f"[blue]Warehouse:[/blue] {warehouse_path}")
    console.print()

    sync_engine = SyncEngine(warehouse_path=warehouse_path, artifacts_path=artifacts_dir)

    # Build expected artifact paths from beacon.yaml
    expected_paths: list[str] = []
    if beacon_yaml.exists():
        beacon_settings = BeaconSettings.from_yaml(beacon_yaml)

        for context_name in beacon_settings.artifacts.contexts:
            expected_paths.append(f"contexts/{context_name}")

        for pattern in beacon_settings.artifacts.knowledge:
            if "*" in pattern or "?" in pattern:
                expected_paths.extend(sync_engine.expand_glob(pattern))
            else:
                expected_paths.append(pattern)

        for skill_name in beacon_settings.artifacts.skills:
            skill_dir = warehouse_path / "skills" / skill_name
            if skill_dir.exists():
                expected_paths.extend(sync_engine.expand_glob(f"skills/{skill_name}/**/*"))

    def file_hash(path: Path) -> str:
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    new_in_target: list[str] = []
    modified_in_target: list[str] = []
    missing_in_target: list[str] = []

    # Check each expected path
    expected_set = set(expected_paths)
    for rel_path in expected_paths:
        warehouse_file = warehouse_path / rel_path
        artifact_file = artifacts_dir / rel_path
        if artifact_file.exists():
            if warehouse_file.exists() and file_hash(warehouse_file) != file_hash(artifact_file):
                modified_in_target.append(rel_path)
        elif warehouse_file.exists():
            missing_in_target.append(rel_path)

    # Find files in artifacts not in expected set
    for artifact_file in artifacts_dir.rglob("*"):
        if artifact_file.is_file():
            rel = str(artifact_file.relative_to(artifacts_dir))
            if rel not in expected_set:
                new_in_target.append(rel)

    # Display results
    if new_in_target:
        table = Table(title="[green]New in Target[/green] (Potential Contributions)")
        table.add_column("File", style="green")
        for file in new_in_target:
            table.add_row(file)
        console.print(table)
        console.print("[dim]These files could be contributed back to the warehouse[/dim]\n")

    if modified_in_target:
        table = Table(title="[yellow]Modified in Target[/yellow] (Local Changes)")
        table.add_column("File", style="yellow")
        for file in modified_in_target:
            table.add_row(file)
        console.print(table)
        console.print("[dim]These files differ from warehouse - may be local customizations[/dim]\n")

    if missing_in_target:
        table = Table(title="[red]Missing in Target[/red] (Available in Warehouse)")
        table.add_column("File", style="red")
        for file in missing_in_target:
            table.add_row(file)
        console.print(table)
        console.print("[dim]Run 'abc sync' to download missing files[/dim]\n")

    if not any([new_in_target, modified_in_target, missing_in_target]):
        console.print("[green]✓ Target and warehouse are in sync![/green]")
    else:
        console.print("[bold]Summary:[/bold]")
        console.print(f"  [green]New:[/green] {len(new_in_target)} files")
        console.print(f"  [yellow]Modified:[/yellow] {len(modified_in_target)} files")
        console.print(f"  [red]Missing:[/red] {len(missing_in_target)} files")


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
