"""Warehouse management subcommands (abc warehouse ...)."""

import os
import sys
from pathlib import Path

import click
from loguru import logger
from rich.console import Console
from rich.table import Table

from beacon.core.gitignore import GitignoreManager
from beacon.core.manifest.workspace import WorkspaceConfig
from beacon.domains.artifact.agent import update_agent_gitignores
from beacon.domains.distribution.distributor import WarehouseDistributor
from beacon.domains.distribution.state import relink_global_sync_state
from beacon.domains.distribution.upgrader import WarehouseUpgrader
from beacon.domains.setup.initializer import WarehouseInitializer, ensure_beacon_dir
from beacon.domains.warehouse.validator import WarehouseValidator

console = Console()


@click.group()
def warehouse() -> None:
    """Warehouse management commands (init, connect, list)."""
    pass


@warehouse.command()
@click.argument("name", type=str, required=False, default=None)
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
    name: str | None,
    path: Path | None,
    org: str | None,
    languages: str | None,
    domains: str | None,
    no_git: bool,
    no_interactive: bool,
) -> None:
    """
    Initialize a new warehouse repository.

    Creates a complete warehouse structure with contexts, knowledge, and skills.
    When NAME is omitted, the warehouse is initialised in the current directory
    (useful when the repo already exists, e.g. freshly cloned from GitHub).
    Existing files are always preserved — only missing files are created.

    Example:
        abc warehouse init                          # initialise in current dir
        abc warehouse init my-warehouse             # create new subdirectory
        abc warehouse init my-warehouse --org "Acme Corp" --languages python,typescript
    """
    base_path = path or Path.cwd()

    if not no_interactive:
        console.print("\n[bold]Initialize New Warehouse[/bold]")

        if name is None:
            raw = click.prompt(
                "Where should the warehouse be created?",
                default=str(base_path),
                type=str,
            )
            warehouse_path = Path(os.path.expandvars(raw)).expanduser().resolve()
        else:
            warehouse_path = (base_path / name).expanduser().resolve()

        console.print(f"[dim]Will create: {warehouse_path}[/dim]\n")

    else:
        raw = str(base_path / name) if name else str(base_path)
        warehouse_path = Path(os.path.expandvars(raw)).expanduser().resolve()

    if not no_interactive:
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

    org = org or "Your Organization"
    languages_list = [
        lang.strip() for lang in (languages or "").split(",") if lang.strip()
    ]
    domains_list = [
        domain.strip() for domain in (domains or "").split(",") if domain.strip()
    ]

    try:
        initializer = WarehouseInitializer(warehouse_path=warehouse_path)
        result = initializer.init(
            org_name=org,
            languages=languages_list if languages_list else None,
            domains=domains_list if domains_list else None,
            init_git=not no_git,
        )

        if result["in_place"]:
            console.print(
                "\n[bold green]✓ Warehouse initialized in current directory![/bold green]\n"
            )
        else:
            console.print(
                "\n[bold green]✓ Warehouse initialized successfully![/bold green]\n"
            )
        console.print(f"  [blue]Location:[/blue] {result['warehouse_path']}")
        console.print(f"  [blue]Organization:[/blue] {org}")

        if languages_list:
            console.print(f"  [blue]Languages:[/blue] {', '.join(languages_list)}")

        if domains_list:
            console.print(f"  [blue]Domains:[/blue] {', '.join(domains_list)}")

        if result["git_initialized"]:
            console.print("  [blue]Git:[/blue] Initialized with initial commit")

        console.print("\n[bold]Next Steps:[/bold]")
        if not result["in_place"]:
            console.print(f"  1. cd {warehouse_path}")
            step = 2
        else:
            step = 1
        console.print(f"  {step}. Customize contexts, knowledge, and skills")
        console.print(f"  {step + 1}. git remote add origin <your-repo-url>")
        console.print(f"  {step + 2}. git push -u origin main")

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
def connect(*, path: Path | None) -> None:
    """
    Connect project to a local warehouse.

    Creates .agentic-beacon/config.toml with warehouse connection.
    The warehouse is validated before accepting the connection.

    Example:
        abc warehouse connect --path ~/org-warehouse
        abc warehouse connect  # Interactive mode
    """
    if not path:
        console.print("\n[bold]Connect to Warehouse[/bold]")
        console.print("[dim]Enter the path to your local warehouse directory[/dim]\n")

        path_str = click.prompt(
            "Warehouse path",
            type=str,
        )
        path = Path(path_str)

    warehouse_path = path.expanduser().resolve()

    if not warehouse_path.exists():
        console.print(f"\n[red]Error:[/red] Path not found: {warehouse_path}")
        console.print("Please check the path and try again.")
        sys.exit(1)

    if not warehouse_path.is_dir():
        console.print(f"\n[red]Error:[/red] Path is not a directory: {warehouse_path}")
        sys.exit(1)

    console.print(f"\n[blue]Validating:[/blue] {warehouse_path}")

    validator = WarehouseValidator()
    validation_result = validator.validate(str(warehouse_path))

    if not validation_result.valid:
        console.print("\n[red bold]✗ Invalid warehouse structure[/red bold]\n")
        for error in validation_result.errors:
            console.print(f"  [red]✗[/red] {error}")
        console.print(
            "\n[dim]See examples/sample-warehouse for a valid warehouse structure[/dim]"
        )
        sys.exit(1)

    console.print("[green]✓[/green] Warehouse structure validated")

    ensure_beacon_dir(Path.cwd())

    try:
        WorkspaceConfig.from_path(warehouse_path)
        console.print("[green]✓[/green] Connection saved")

        gitignore_mgr = GitignoreManager(Path.cwd())
        if gitignore_mgr.ensure_entries():
            console.print("[green]✓[/green] Updated .gitignore")
        update_agent_gitignores(Path.cwd())

        relink_global_sync_state(warehouse_path)

        console.print("\n[bold green]✓ Connected to warehouse[/bold green]")
        console.print(f"  [blue]Location:[/blue] {warehouse_path}")

        console.print("\n[bold]Next Steps:[/bold]")
        console.print("  1. Run 'abc setup' to configure artifacts")
        console.print("  2. Run 'abc sync' to download artifacts")

    except Exception as e:
        console.print(f"\n[red]Error:[/red] Failed to save connection: {e}")
        logger.exception("Connection failed")
        sys.exit(1)


@warehouse.command(name="list")
@click.argument(
    "artifact_type",
    required=False,
    type=click.Choice(
        ["agents", "knowledge", "skills", "contexts"], case_sensitive=False
    ),
    default=None,
)
def warehouse_list(*, artifact_type: str | None) -> None:
    """List artifacts available in the connected warehouse.

    ARTIFACT_TYPE filters output to a single type. Omit to show all.

    Example:
        abc warehouse list
        abc warehouse list knowledge
        abc warehouse list skills
        abc warehouse list contexts
    """
    beacon_dir = Path.cwd() / ".agentic-beacon"
    config_file = beacon_dir / "config.toml"

    if not config_file.exists():
        console.print("[red]Error:[/red] No warehouse connected.")
        console.print("Run 'abc warehouse connect --path <warehouse>' first.")
        sys.exit(1)

    try:
        warehouse_settings = WorkspaceConfig()
        warehouse_path = Path(warehouse_settings.warehouse.local_path)
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to read warehouse connection: {e}")
        sys.exit(1)

    if not warehouse_path.exists():
        console.print(
            f"[red]Error:[/red] Warehouse path no longer exists: {warehouse_path}"
        )
        console.print("Run 'abc warehouse connect --path <warehouse>' to reconnect.")
        sys.exit(1)

    distributor = WarehouseDistributor(
        warehouse_root=warehouse_path, target_root=Path.cwd()
    )
    available = distributor.list_available()

    types_to_show = (
        [artifact_type]
        if artifact_type
        else ["agents", "contexts", "knowledge", "skills"]
    )

    section_config = {
        "agents": ("Available Agents", "magenta", "Agent"),
        "contexts": ("Available Contexts", "cyan", "Context"),
        "knowledge": ("Available Knowledge", "green", "Scope"),
        "skills": ("Available Skills", "yellow", "Skill"),
    }

    any_shown = False
    for section in types_to_show:
        items = available.get(section, [])
        if section == "agents" and not items:
            if artifact_type == "agents":
                console.print("[yellow]No agents found in warehouse.[/yellow]")
                any_shown = True
            continue
        if items:
            title, color, col_name = section_config[section]
            table = Table(title=title)
            table.add_column(col_name, style=color)
            for item in items:
                table.add_row(item)
            console.print(table)
            console.print()
            any_shown = True

    if not any_shown:
        label = artifact_type or "artifacts"
        console.print(f"[yellow]No {label} found in warehouse.[/yellow]")


@warehouse.command(name="template-upgrade")
@click.argument(
    "warehouse_path",
    type=click.Path(path_type=Path, exists=True, file_okay=False),
    required=False,
    default=None,
)
@click.option(
    "--dry-run", is_flag=True, help="Show planned changes without writing anything."
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite all files regardless of modification status (scripting-friendly).",
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Prompt per modified file with a coloured diff before overwriting.",
)
def warehouse_template_upgrade(
    *,
    warehouse_path: Path | None,
    dry_run: bool,
    force: bool,
    interactive: bool,
) -> None:
    """Upgrade template-generated files in an existing warehouse.

    Compares each template-generated file against the stored checksum to
    determine whether it was user-modified.  Modified files are protected by
    default: the new template is written to a '<file>.new' sidecar so you can
    merge manually.

    \b
    Examples:
        abc warehouse template-upgrade /path/to/warehouse
        abc warehouse template-upgrade /path/to/warehouse --dry-run
        abc warehouse template-upgrade /path/to/warehouse --force
        abc warehouse template-upgrade /path/to/warehouse --interactive
    """
    target = warehouse_path or Path.cwd()
    upgrader = WarehouseUpgrader(warehouse_path=target)
    upgrader.run(dry_run=dry_run, force=force, interactive=interactive)
