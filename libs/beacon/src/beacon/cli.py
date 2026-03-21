"""CLI interface for Beacon - Distribute knowledge contexts for AI development."""

import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import click
from loguru import logger
from rich.console import Console
from rich.table import Table

from .core.delta import DeltaComparator, DeltaStatus
from .core.gitignore import GitignoreManager
from .core.settings import ArtifactsConfig, BeaconSettings, WarehouseSettings
from .core.sync import SyncEngine
from .distributor import WarehouseDistributor
from .initializer import WarehouseInitializer
from .upgrader import WarehouseUpgrader
from .warehouse import WarehouseValidator

console = Console()


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


def _check_warehouse_git_clean(warehouse_path: Path) -> str | None:
    """Check if the warehouse git working tree is clean.

    Returns an error message string if there are uncommitted changes,
    or None if the tree is clean / not a git repo / git not installed.
    """
    if not (warehouse_path / ".git").exists():
        return None  # Not a git repo — skip silently

    try:
        result = subprocess.run(
            ["git", "-C", str(warehouse_path), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        console.print(
            "[yellow]Warning:[/yellow] git not found — skipping warehouse clean check."
        )
        return None
    except subprocess.TimeoutExpired:
        console.print(
            "[yellow]Warning:[/yellow] git status timed out — skipping warehouse clean check."
        )
        return None

    if result.stdout.strip():
        short_path = str(warehouse_path).replace(str(Path.home()), "~")
        return (
            f"Warehouse has uncommitted changes.\n"
            f"  Warehouse: {short_path}\n\n"
            f"  Commit or stash your warehouse changes before running this command:\n"
            f"    cd {short_path}\n"
            f"    git diff          # review changes\n"
            f'    git add . && git commit -m "..."\n'
            f"    # or: git stash\n\n"
            f"  Use --skip-git-check to bypass this check."
        )
    return None


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


# ========== Warehouse Management Commands ==========


@main.group()
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

    # Interactive prompts if not disabled
    if not no_interactive:
        console.print("\n[bold]Initialize New Warehouse[/bold]")

        if name is None:
            # Prompt for the full path; default to CWD so user can see and edit it
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

    # Interactive prompts for metadata (when not disabled)
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

    # Set defaults
    org = org or "Your Organization"
    languages_list = [
        lang.strip() for lang in (languages or "").split(",") if lang.strip()
    ]
    domains_list = [
        domain.strip() for domain in (domains or "").split(",") if domain.strip()
    ]

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

        # Next steps
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

    # Validate path exists
    if not warehouse_path.exists():
        console.print(f"\n[red]Error:[/red] Path not found: {warehouse_path}")
        console.print("Please check the path and try again.")
        sys.exit(1)

    if not warehouse_path.is_dir():
        console.print(f"\n[red]Error:[/red] Path is not a directory: {warehouse_path}")
        sys.exit(1)

    console.print(f"\n[blue]Validating:[/blue] {warehouse_path}")

    # Validate warehouse structure
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

    # Create .agentic-beacon directory if it doesn't exist
    beacon_dir = Path.cwd() / ".agentic-beacon"
    beacon_dir.mkdir(exist_ok=True)

    # Save connection configuration
    try:
        WarehouseSettings.from_path(warehouse_path)
        console.print("[green]✓[/green] Connection saved")

        # Update .gitignore
        gitignore_mgr = GitignoreManager(Path.cwd())
        if gitignore_mgr.ensure_entries():
            console.print("[green]✓[/green] Updated .gitignore")
        _update_agent_gitignores(Path.cwd())

        # Success message
        console.print("\n[bold green]✓ Connected to warehouse[/bold green]")
        console.print(f"  [blue]Location:[/blue] {warehouse_path}")

        # Next steps
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
    type=click.Choice(["knowledge", "skills", "contexts"], case_sensitive=False),
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
        warehouse_settings = WarehouseSettings()
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
        [artifact_type] if artifact_type else ["contexts", "knowledge", "skills"]
    )

    section_config = {
        "contexts": ("Available Contexts", "cyan", "Context"),
        "knowledge": ("Available Knowledge", "green", "Scope"),
        "skills": ("Available Skills", "yellow", "Skill"),
    }

    any_shown = False
    for section in types_to_show:
        items = available.get(section, [])
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


# ========== Client Commands (top-level) ==========


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
        console.print(
            "[red]Error:[/red] --manual and --agent-assisted are mutually exclusive"
        )
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
        _create_beacon_template(beacon_yaml)
        _install_project_setup_skill(beacon_dir)
        console.print("\n[bold green]✓ Agent-assisted setup ready[/bold green]")
        console.print(f"  [blue]beacon.yaml:[/blue] {beacon_yaml}")
        console.print(f"  [blue]Catalog:[/blue] {beacon_dir / 'warehouse-catalog.md'}")
        console.print("\n[bold]Paste this into your agent:[/bold]")
        console.print(
            "\n[on dark_green] Read `.agentic-beacon/warehouse-catalog.md` to see "
            "what artifacts are available in the connected warehouse. Analyse this "
            "project, then update `.agentic-beacon/beacon.yaml` with the artifacts "
            "that are relevant. Always preserve any default bundled skills already "
            "listed in beacon.yaml (e.g. `skills/record-knowledge/SKILL.md`). "
            "Run `abc sync` when done. [/on dark_green]\n"
        )


def _get_bundled_skill_paths() -> list[str]:
    """Return beacon.yaml-relative paths for all bundled skills shipped with abc."""
    bundled_skills_dir = Path(__file__).parent / "data" / "skills"
    paths = []
    if bundled_skills_dir.exists():
        for skill_dir in sorted(bundled_skills_dir.iterdir()):
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                paths.append(f"skills/{skill_dir.name}/SKILL.md")
    return paths


def _warn_missing_bundled_skills(beacon_settings: "BeaconSettings") -> None:
    """Print a warning for any bundled skills absent from beacon.yaml."""
    configured = set(beacon_settings.artifacts.skills)
    missing = [p for p in _get_bundled_skill_paths() if p not in configured]
    if missing:
        console.print(
            "\n[yellow]Warning:[/yellow] The following default bundled skill(s) are "
            "not in beacon.yaml:"
        )
        for p in missing:
            console.print(f"  [yellow]-[/yellow] {p}")
        console.print(
            "  Add them to [bold].agentic-beacon/beacon.yaml[/bold] under "
            "[bold]artifacts.skills[/bold] and re-run [bold]abc sync[/bold]."
        )


def _create_beacon_template(path: Path) -> None:
    """Create empty beacon.yaml template with commented examples."""
    template = """\
# beacon.yaml - Declare which warehouse artifacts this project needs.
# Run 'abc sync' after editing to download artifacts.
#
# Supports glob patterns: knowledge/languages/python/**/*.md
# Supports specific files: skills/code-review/SKILL.md

artifacts:
  knowledge: []
    # Examples:
    # - knowledge/languages/python/**/*.md
    # - knowledge/infrastructure/docker-standards.md

  skills:
    - skills/record-knowledge/SKILL.md
    # Examples:
    # - skills/code-review/SKILL.md
    # - skills/generate-unit-tests/SKILL.md

  contexts: []
    # Examples:
    # - contexts/README.md
    # - contexts/teams/backend/README.md
"""
    path.write_text(template)


def _install_project_setup_skill(beacon_dir: Path) -> None:
    """Install project-setup skill and generate warehouse catalog.

    This generates a warehouse catalog file that AI agents can read
    to understand what artifacts are available and populate beacon.yaml.
    """
    try:
        config_file = beacon_dir / "config.toml"
        if not config_file.exists():
            return

        settings = WarehouseSettings()
        warehouse_path = Path(settings.warehouse.local_path)

        if not warehouse_path.exists():
            console.print(
                "[yellow]Warning:[/yellow] Warehouse path not found, skipping catalog generation"
            )
            return

        # Generate warehouse catalog
        catalog = _generate_warehouse_catalog(warehouse_path)
        catalog_path = beacon_dir / "warehouse-catalog.md"
        catalog_path.write_text(catalog, encoding="utf-8")

    except Exception as e:
        console.print(f"[yellow]Warning:[/yellow] Could not generate catalog: {e}")


def _generate_warehouse_catalog(warehouse_path: Path) -> str:
    """Scan warehouse and generate markdown catalog for AI agents.

    Args:
        warehouse_path: Path to warehouse directory

    Returns:
        Markdown-formatted catalog string
    """
    lines = [
        "# Warehouse Artifact Catalog",
        "",
        "This catalog lists all available artifacts in the connected warehouse.",
        "Use this to decide which artifacts to add to your project's beacon.yaml.",
        "",
        f"**Warehouse:** `{warehouse_path}`",
        "",
    ]

    for section_name, section_dir in [
        ("Knowledge", "knowledge"),
        ("Skills", "skills"),
        ("Contexts", "contexts"),
    ]:
        section_path = warehouse_path / section_dir
        if not section_path.exists():
            continue

        lines.append(f"## {section_name}")
        lines.append("")
        lines.append(
            f"Paths are relative to warehouse root. Use in beacon.yaml under `artifacts.{section_dir}`."
        )
        lines.append("")

        # Scan for files
        files = sorted(section_path.rglob("*"))
        file_entries = []
        for f in files:
            if f.is_file() and not f.name.startswith("."):
                rel = f.relative_to(warehouse_path)
                # Try to extract description from first line
                desc = _extract_description(f)
                if desc:
                    file_entries.append(f"- `{rel}` - {desc}")
                else:
                    file_entries.append(f"- `{rel}`")

        if file_entries:
            lines.extend(file_entries)
        else:
            lines.append("_No artifacts found._")

        lines.append("")

    lines.extend(
        [
            "## Usage",
            "",
            "Add paths to your `.agentic-beacon/beacon.yaml` file:",
            "",
            "```yaml",
            "artifacts:",
            "  knowledge:",
            "    - knowledge/languages/python/**/*.md  # Glob pattern",
            "    - knowledge/infrastructure/docker-standards.md  # Specific file",
            "  skills:",
            "    - skills/code-review/SKILL.md",
            "  contexts:",
            "    - contexts/README.md",
            "```",
            "",
            "Then run `abc sync` to download the artifacts.",
            "",
        ]
    )

    return "\n".join(lines)


def _extract_description(file_path: Path) -> str:
    """Extract a brief description from a file's first heading or content.

    Args:
        file_path: Path to the file

    Returns:
        Description string, or empty string if none found
    """
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        for line in content.splitlines()[:5]:
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
            if line.startswith("description:"):
                return line.split(":", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


@main.command()
@click.option("--preserve", is_flag=True, help="Skip files with local modifications")
@click.option("--prune", is_flag=True, help="Remove artifacts no longer in beacon.yaml")
@click.option(
    "--verbose", "verbose_flag", is_flag=True, help="Show detailed sync output"
)
@click.option(
    "--dry-run", is_flag=True, help="Preview what would be synced without copying"
)
@click.option(
    "--skip-git-check",
    is_flag=True,
    help="Skip warehouse uncommitted-changes check",
)
def sync(
    *,
    preserve: bool,
    prune: bool,
    verbose_flag: bool,
    dry_run: bool,
    skip_git_check: bool,
) -> None:
    """
    Sync artifacts from warehouse to project.

    Reads .agentic-beacon/beacon.yaml and copies specified artifacts
    from the connected warehouse to .agentic-beacon/artifacts/ directory.

    Example:
        abc sync              # Sync all artifacts
        abc sync --preserve   # Skip locally modified files
        abc sync --prune      # Remove artifacts not in beacon.yaml
        abc sync --verbose    # Show detailed output
        abc sync --dry-run    # Preview without copying
    """
    # Check for .agentic-beacon directory
    beacon_dir = Path.cwd() / ".agentic-beacon"
    if not beacon_dir.exists():
        console.print("[red]Error:[/red] No .agentic-beacon directory found.")
        console.print("Run 'abc warehouse connect' to connect to a warehouse first.")
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
        warehouse_settings = WarehouseSettings()
        warehouse_path = Path(warehouse_settings.warehouse.local_path)

        # Validate warehouse still exists
        if not warehouse_path.exists():
            console.print(
                f"[red]Error:[/red] Warehouse path no longer exists: {warehouse_path}"
            )
            console.print("The warehouse may have been moved or deleted.")
            console.print(
                "Run 'abc warehouse connect --path <warehouse>' to reconnect."
            )
            sys.exit(1)

        # Check warehouse git cleanliness (skip if --dry-run or --skip-git-check)
        if not dry_run and not skip_git_check:
            git_error = _check_warehouse_git_clean(warehouse_path)
            if git_error:
                console.print(f"[red]Error:[/red] {git_error}")
                sys.exit(1)

        # Load beacon.yaml
        beacon_settings = BeaconSettings.from_yaml(beacon_yaml)

        # Check if there are any artifacts to sync
        total_artifacts = (
            len(beacon_settings.artifacts.knowledge)
            + len(beacon_settings.artifacts.skills)
            + len(beacon_settings.artifacts.contexts)
        )

        if total_artifacts == 0:
            console.print(
                "[yellow]No artifacts configured in beacon.yaml. Nothing to sync.[/yellow]"
            )
            sys.exit(0)

        _warn_missing_bundled_skills(beacon_settings)

        # Create artifacts directory
        artifacts_dir = beacon_dir / "artifacts"
        artifacts_dir.mkdir(exist_ok=True)

        # Initialize sync engine
        sync_engine = SyncEngine(
            warehouse_path=warehouse_path, artifacts_path=artifacts_dir
        )

        if dry_run:
            console.print("[dim]Dry run — no files will be copied or pruned.[/dim]\n")

        # Collect all artifact paths (expanding globs)
        artifact_paths = []
        console.print("\n[blue]Syncing artifacts from warehouse...[/blue]\n")

        for artifact_type in ["knowledge", "skills", "contexts"]:
            artifacts_list = getattr(beacon_settings.artifacts, artifact_type)
            for pattern in artifacts_list:
                # Check if pattern contains glob characters
                if "*" in pattern or "?" in pattern or "[" in pattern:
                    try:
                        matches = sync_engine.expand_glob(pattern)
                        if not matches:
                            console.print(
                                f"  [yellow]Warning:[/yellow] No files matched pattern: {pattern}"
                            )
                        elif verbose_flag:
                            console.print(
                                f"  Pattern '{pattern}' matched {len(matches)} files"
                            )
                        artifact_paths.extend(matches)
                    except Exception as e:
                        console.print(
                            f"  [red]Error:[/red] Invalid glob pattern '{pattern}': {e}"
                        )
                        sys.exit(1)
                else:
                    artifact_paths.append(pattern)

        # Perform sync
        def log_fn(msg: str) -> None:
            console.print(f"  {msg}")

        summary = sync_engine.sync_all(
            artifact_paths=artifact_paths,
            preserve=preserve,
            prune=prune,
            verbose=verbose_flag,
            dry_run=dry_run,
            log_fn=log_fn if (verbose_flag or dry_run) else None,
        )

        # Update .gitignore (only when actually syncing)
        if not dry_run:
            gitignore_mgr = GitignoreManager(Path.cwd())
            gitignore_mgr.ensure_entries()

        # Display summary
        action_word = "Would copy" if dry_run else "Copied"
        done_label = "Dry run complete" if dry_run else "Sync complete"
        console.print(f"\n[bold green]✓ {done_label}[/bold green]")
        console.print(f"  [blue]{action_word}:[/blue] {summary.copied} files")
        console.print(f"  [blue]Unchanged:[/blue] {summary.skipped} files")
        if summary.preserved > 0:
            console.print(
                f"  [yellow]{'Would preserve' if dry_run else 'Preserved'}:[/yellow] "
                f"{summary.preserved} locally modified files"
            )
            if not dry_run:
                console.print("  [dim]Use 'abc delta' to review local changes.[/dim]")
        if summary.pruned > 0:
            console.print(
                f"  [yellow]{'Would prune' if dry_run else 'Pruned'}:[/yellow] "
                f"{summary.pruned} artifacts no longer in beacon.yaml"
            )
        if summary.errors > 0:
            console.print(f"  [red]Errors:[/red] {summary.errors} files")
            for path, msg in summary.failed_files:
                console.print(f"    [red]✗[/red] {path}: {msg}")

        if dry_run:
            console.print(
                "\n  [dim]Run without --dry-run to apply these changes.[/dim]"
            )
            return

        # Post-sync wiring
        project_root = Path.cwd()
        wiring_notes: list[str] = []

        if beacon_settings.artifacts.contexts:
            oc_added = _wire_contexts_opencode(project_root, artifacts_dir)
            if oc_added:
                console.print(
                    f"\n[green]✓[/green] Wired {len(oc_added)} context(s) into opencode.json"
                )

            cc_added = _wire_contexts_claudecode(project_root, artifacts_dir)
            if cc_added:
                console.print(
                    f"[green]✓[/green] Wired {len(cc_added)} context(s) into CLAUDE.md"
                )

            # If no agent config exists at all, surface manual instructions
            has_opencode = (project_root / "opencode.json").exists()
            has_claude = any(
                p.exists()
                for p in [
                    project_root / ".claude" / "CLAUDE.md",
                    project_root / "CLAUDE.md",
                ]
            )
            if not has_opencode and not has_claude:
                contexts_dir = artifacts_dir / "contexts"
                if contexts_dir.exists() and any(contexts_dir.rglob("*.md")):
                    if not dry_run and _is_interactive():
                        console.print(
                            "\n[yellow]No agent config detected.[/yellow] "
                            "Set one up to wire contexts automatically."
                        )
                        if click.confirm("  Initialize opencode.json?", default=False):
                            _init_opencode_json(project_root)
                            oc_init = _wire_contexts_opencode(
                                project_root, artifacts_dir
                            )
                            if oc_init:
                                console.print(
                                    f"[green]✓[/green] Created opencode.json and "
                                    f"wired {len(oc_init)} context(s)"
                                )
                        if click.confirm("  Initialize CLAUDE.md?", default=False):
                            _init_claude_md(project_root)
                            cc_init = _wire_contexts_claudecode(
                                project_root, artifacts_dir
                            )
                            if cc_init:
                                console.print(
                                    f"[green]✓[/green] Created CLAUDE.md and "
                                    f"wired {len(cc_init)} context(s)"
                                )
                    else:
                        wiring_notes.append(
                            "  Contexts synced — wire them into your agent config:\n"
                            '  [bold]opencode.json[/bold] → add to "instructions" array:\n'
                            '    ".agentic-beacon/artifacts/contexts/<name>.md"\n'
                            "  [bold]CLAUDE.md[/bold] → add a line per context:\n"
                            "    @.agentic-beacon/artifacts/contexts/<name>.md"
                        )

        if beacon_settings.artifacts.skills:
            wired_skills, wire_errors = _wire_skills_post_sync(
                project_root, artifacts_dir
            )
            if wired_skills:
                console.print(
                    f"[green]✓[/green] Installed {len(wired_skills)} skill(s) "
                    f"({', '.join(wired_skills)})"
                )
            if wire_errors:
                for err in wire_errors:
                    console.print(f"  [yellow]⚠[/yellow] Skill wiring: {err}")
            _update_agent_gitignores(project_root)

        if wiring_notes:
            console.print("\n[bold]Manual wiring required:[/bold]")
            for note in wiring_notes:
                console.print(note)

    except Exception as e:
        console.print(f"\n[red]Error:[/red] Sync failed: {e}")
        logger.exception("Sync failed")
        sys.exit(1)


@main.command(name="install")
@click.argument("artifact", metavar="ARTIFACT")
@click.option(
    "--agent",
    type=click.Choice(["opencode", "claudecode"], case_sensitive=False),
    help="Target agent tool (auto-detected if not specified)",
)
def install_artifact(*, artifact: str, agent: str | None) -> None:
    """Pull and wire a single artifact from the warehouse.

    ARTIFACT is a path relative to the warehouse root. Type is inferred
    from the leading path component.

    Example:
        abc install skills/code-reviewer
        abc install contexts/python
        abc install knowledge/decisions/coding-standards.md
    """
    beacon_dir = Path.cwd() / ".agentic-beacon"
    if not beacon_dir.exists():
        console.print("[red]Error:[/red] No .agentic-beacon directory found.")
        console.print("Run 'abc warehouse connect' to connect to a warehouse first.")
        sys.exit(1)

    try:
        warehouse_settings = WarehouseSettings()
        warehouse_path = Path(warehouse_settings.warehouse.local_path)
    except Exception as e:
        console.print(f"[red]Error:[/red] Could not load warehouse settings: {e}")
        sys.exit(1)

    if not warehouse_path.exists():
        console.print(f"[red]Error:[/red] Warehouse not found at {warehouse_path}")
        sys.exit(1)

    artifact = artifact.rstrip("/")
    artifacts_dir = beacon_dir / "artifacts"
    engine = SyncEngine(warehouse_path=warehouse_path, artifacts_path=artifacts_dir)

    # Resolve which files to copy
    source = warehouse_path / artifact
    if source.is_file():
        files_to_copy = [artifact]
    elif source.is_dir():
        files_to_copy = engine.expand_glob(f"{artifact}/**/*")
    elif (warehouse_path / f"{artifact}.md").exists():
        files_to_copy = [f"{artifact}.md"]
        artifact = f"{artifact}.md"
    else:
        console.print(f"[red]Error:[/red] Artifact not found in warehouse: {artifact}")
        sys.exit(1)

    if not files_to_copy:
        console.print(f"[red]Error:[/red] No files found for: {artifact}")
        sys.exit(1)

    # Copy files from warehouse to artifacts
    copy_errors: list[str] = []
    copied = 0
    for path in files_to_copy:
        result = engine.copy_file(path)
        if result.success:
            if result.action == "copied":
                copied += 1
        else:
            copy_errors.append(f"{path}: {result.error_message}")

    if copy_errors:
        for err in copy_errors:
            console.print(f"[red]✗[/red] {err}")
        sys.exit(1)

    # Update beacon.yaml so future abc sync stays idempotent
    _update_beacon_yaml(beacon_dir, files_to_copy)

    # Infer type and wire
    artifact_type = Path(artifact).parts[0] if Path(artifact).parts else ""
    project_root = Path.cwd()
    agents = _detect_agents(project_root) if not agent else [agent.lower()]

    if artifact_type == "skills":
        # Skill name is the directory directly under skills/
        skill_name = (
            Path(artifact).parts[1]
            if len(Path(artifact).parts) > 1
            else Path(artifact).stem
        )
        skill_md = artifacts_dir / "skills" / skill_name / "SKILL.md"
        if skill_md.exists() and agents:
            content = skill_md.read_text(encoding="utf-8")
            description = _extract_skill_description(content)
            for target_agent in agents:
                if target_agent == "opencode":
                    _install_skill_opencode(
                        project_root, skill_name, content, description
                    )
                else:
                    _install_skill_claudecode(project_root, skill_name, content)
            console.print(f"[green]✓[/green] Installed skill: {skill_name}")
            _update_agent_gitignores(project_root)
            _print_skill_next_steps(agents)
        elif skill_md.exists():
            console.print(
                "[green]✓[/green] Skill copied (no agent detected for wiring)"
            )
        else:
            console.print(
                f"[green]✓[/green] Artifact copied ({len(files_to_copy)} file(s))"
            )

    elif artifact_type == "contexts":
        wired_opencode = _wire_contexts_opencode(project_root, artifacts_dir)
        wired_claudecode = _wire_contexts_claudecode(project_root, artifacts_dir)
        if wired_opencode or wired_claudecode:
            console.print("[green]✓[/green] Context copied and wired into agent config")
        else:
            console.print(
                "[green]✓[/green] Context copied (no agent config found to wire)"
            )

    elif artifact_type == "knowledge":
        console.print(
            f"[green]✓[/green] Knowledge artifact installed ({len(files_to_copy)} file(s))"
        )

    else:
        console.print(
            f"[green]✓[/green] Artifact installed ({len(files_to_copy)} file(s))"
        )

    if copied:
        console.print(f"  [dim]{copied} file(s) newly copied[/dim]")


def _build_skills_paths(project_root: Path) -> dict[str, Path]:
    """Return a mapping of agent name → live skills directory for detected agents.

    This is the shared detection logic used by both `abc delta` and
    `abc contribute` so both commands always compare/read from the same
    live agent locations.
    """
    skills_paths: dict[str, Path] = {}
    for agent in _detect_agents(project_root):
        if agent == "opencode":
            skills_paths["opencode"] = project_root / ".opencode" / "skills"
        elif agent == "claudecode":
            skills_paths["claudecode"] = project_root / ".claude" / "skills"
    return skills_paths


@main.command()
@click.argument("file", required=False, type=str)
@click.option("--no-color", is_flag=True, help="Disable color output in diffs")
def delta(*, file: str | None, no_color: bool) -> None:
    """
    Compare local artifacts against warehouse.

    Without arguments: shows summary of all differences.
    With file argument: shows detailed line-by-line diff.

    Example:
        abc delta                              # Summary view
        abc delta knowledge/lessons.md         # Detailed diff
        abc delta knowledge/lessons.md --no-color  # Without colors
    """
    # Check for .agentic-beacon directory
    beacon_dir = Path.cwd() / ".agentic-beacon"
    if not beacon_dir.exists():
        console.print("[red]Error:[/red] No .agentic-beacon directory found.")
        console.print("Run 'abc warehouse connect' to connect to a warehouse first.")
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

    try:
        warehouse_settings = WarehouseSettings()
        warehouse_path = Path(warehouse_settings.warehouse.local_path)

        if not warehouse_path.exists():
            console.print(
                f"[red]Error:[/red] Warehouse path no longer exists: {warehouse_path}"
            )
            console.print(
                "Run 'abc warehouse connect --path <warehouse>' to reconnect."
            )
            sys.exit(1)

        artifacts_dir = beacon_dir / "artifacts"
        beacon_settings = BeaconSettings.from_yaml(beacon_yaml)

        # Build skills_paths via shared helper — same logic used by contribute.
        project_root = Path.cwd()
        comparator = DeltaComparator(
            warehouse_path=warehouse_path,
            artifacts_path=artifacts_dir,
            skills_paths=_build_skills_paths(project_root),
        )

        if file:
            # Detailed diff for specific file
            _show_detailed_diff(comparator, beacon_settings, file, no_color)
        else:
            # Summary view
            _show_delta_summary(comparator, beacon_settings)

    except Exception as e:
        console.print(f"\n[red]Error:[/red] Delta comparison failed: {e}")
        logger.exception("Delta comparison failed")
        sys.exit(1)


def _show_delta_summary(
    comparator: DeltaComparator, beacon_settings: BeaconSettings
) -> None:
    """Show summary of all artifact differences."""
    summary = comparator.compare_from_config(beacon_settings)
    untracked = _find_untracked_local_files(
        comparator, beacon_settings, comparator.artifacts_path
    )

    if not summary.has_differences and not untracked:
        console.print(
            "[green]No differences found. Local artifacts match local warehouse.[/green]"
        )
        return

    # Show differences
    console.print("\n[bold]Artifact Differences:[/bold]\n")

    for result in summary.results:
        if result.status == DeltaStatus.MODIFIED:
            if result.is_skill and result.agent_statuses:
                # Show per-agent breakdown for skills
                agent_detail = _format_skill_agent_statuses(result.agent_statuses)
                console.print(
                    f"  [yellow][Modified][/yellow] {result.path} [dim]({agent_detail})[/dim]"
                )
            else:
                console.print(f"  [yellow][Modified][/yellow] {result.path}")
        elif result.status == DeltaStatus.ADDED:
            if result.is_skill and result.agent_statuses:
                agent_detail = _format_skill_agent_statuses(result.agent_statuses)
                console.print(
                    f"  [green][Added][/green]    {result.path} [dim]({agent_detail})[/dim]"
                )
            else:
                console.print(f"  [green][Added][/green]    {result.path}")
        elif result.status == DeltaStatus.MISSING:
            if result.is_skill and result.agent_statuses:
                agent_detail = _format_skill_agent_statuses(result.agent_statuses)
                console.print(
                    f"  [red][Missing][/red]  {result.path} [dim]({agent_detail})[/dim]"
                )
            else:
                console.print(f"  [red][Missing][/red]  {result.path}")

    for rel_path in untracked:
        console.print(
            f"  [green][Added][/green]    {rel_path} [dim](not in beacon.yaml)[/dim]"
        )

    # Summary counts
    console.print("\n[bold]Summary:[/bold]")
    if summary.modified:
        console.print(f"  [yellow]Modified:[/yellow] {len(summary.modified)} files")
    total_added = len(summary.added) + len(untracked)
    if total_added:
        console.print(f"  [green]Added:[/green] {total_added} files")
    if summary.missing:
        console.print(f"  [red]Missing:[/red] {len(summary.missing)} files")
    if summary.identical:
        console.print(f"  [dim]Identical:[/dim] {len(summary.identical)} files")

    # Tips
    if summary.missing:
        console.print(
            "\n[dim]Tip: Run 'abc sync' to download missing artifacts from warehouse.[/dim]"
        )
    if summary.modified:
        console.print(
            "[dim]Tip: Run 'abc delta <file>' to see detailed diff for a modified file.[/dim]"
        )
    if untracked:
        console.print(
            "[dim]Tip: Run 'abc contribute --all' to push untracked local artifacts to the warehouse.[/dim]"
        )


def _show_detailed_diff(
    comparator: DeltaComparator,
    beacon_settings: BeaconSettings,
    file_path: str,
    no_color: bool,
) -> None:
    """Show detailed diff for a specific file."""
    # Check if file is tracked in beacon.yaml
    all_paths = _collect_artifact_paths(comparator, beacon_settings)
    if file_path not in all_paths:
        console.print(
            f"[red]Error:[/red] File '{file_path}' is not tracked in beacon.yaml."
        )
        console.print("Only artifacts declared in beacon.yaml can be compared.")
        sys.exit(1)

    # Compare the specific file
    result = comparator.compare_file(file_path)

    if result.status == DeltaStatus.IDENTICAL:
        console.print(
            f"[green]No differences found.[/green] Local and warehouse versions of '{file_path}' are identical."
        )
        return

    if result.status == DeltaStatus.MISSING:
        console.print(
            f"[red][Missing][/red] '{file_path}' has not been synced locally."
        )
        console.print("[dim]Run 'abc sync' to download it.[/dim]")
        return

    if result.status == DeltaStatus.ADDED:
        console.print(
            f"[green][Added][/green] '{file_path}' exists locally but not in warehouse."
        )
        return

    # Show detailed diff
    console.print(f"\n[bold]Diff: {file_path}[/bold]\n")
    diff_output = comparator.detailed_diff(file_path, color=not no_color)
    if diff_output:
        console.print(diff_output)
    else:
        console.print("[dim]No differences to display.[/dim]")


def _format_skill_agent_statuses(agent_statuses: dict) -> str:
    """Format per-agent skill statuses for display.

    e.g. "opencode: modified, claudecode: identical"
    """
    from beacon.core.delta import DeltaStatus

    label = {
        DeltaStatus.MODIFIED: "modified",
        DeltaStatus.MISSING: "missing",
        DeltaStatus.ADDED: "added",
        DeltaStatus.IDENTICAL: "identical",
    }
    parts = [
        f"{agent}: {label.get(status, status.value)}"
        for agent, status in agent_statuses.items()
    ]
    return ", ".join(parts)


def _collect_artifact_paths(
    comparator: DeltaComparator, beacon_settings: BeaconSettings
) -> set:
    """Collect all artifact paths from beacon.yaml, expanding globs.

    Globs both the warehouse and local artifacts directory so that locally-added
    files (not yet in the warehouse) are included.
    """
    sync_engine = SyncEngine(
        warehouse_path=comparator.warehouse_path,
        artifacts_path=comparator.artifacts_path,
    )
    paths: set[str] = set()
    for artifact_type in ["knowledge", "skills", "contexts"]:
        patterns = getattr(beacon_settings.artifacts, artifact_type)
        for pattern in patterns:
            if "*" in pattern or "?" in pattern or "[" in pattern:
                paths.update(sync_engine.expand_glob(pattern))
                # Also glob local artifacts to catch ADDED files
                if comparator.artifacts_path.exists():
                    for match in comparator.artifacts_path.glob(pattern):
                        if match.is_file():
                            paths.add(str(match.relative_to(comparator.artifacts_path)))
            else:
                paths.add(pattern)
    return paths


def _infer_artifact_type(file_path: str) -> str | None:
    """Infer artifact type from a relative path prefix.

    Returns "knowledge", "skills", "contexts", or None if unrecognisable.
    """
    first_part = Path(file_path).parts[0] if Path(file_path).parts else ""
    if first_part in ("knowledge", "skills", "contexts"):
        return first_part
    return None


def _register_in_beacon_yaml(
    beacon_settings: BeaconSettings, beacon_yaml: Path, file_path: str
) -> bool:
    """Add an explicit path to beacon.yaml under the appropriate artifact type.

    Returns True if the file was added (i.e. it wasn't already listed explicitly).
    """
    artifact_type = _infer_artifact_type(file_path)
    if artifact_type is None:
        return False

    current_list: list[str] = getattr(beacon_settings.artifacts, artifact_type)
    if file_path not in current_list:
        current_list.append(file_path)
        beacon_settings.to_yaml(beacon_yaml)
        return True
    return False


def _find_untracked_local_files(
    comparator: DeltaComparator,
    beacon_settings: BeaconSettings,
    artifacts_dir: Path,
) -> list[str]:
    """Return local artifact files that are not covered by any beacon.yaml pattern."""
    tracked = _collect_artifact_paths(comparator, beacon_settings)
    untracked: list[str] = []
    if artifacts_dir.exists():
        for file_path in sorted(artifacts_dir.rglob("*")):
            if file_path.is_file():
                rel = str(file_path.relative_to(artifacts_dir))
                if rel not in tracked:
                    untracked.append(rel)
    return untracked


# ========== Contribute Command ==========


@main.command()
@click.argument("file", required=False, type=str)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would be contributed without copying",
)
@click.option(
    "--skip-git-check",
    is_flag=True,
    help="Skip warehouse uncommitted-changes check",
)
@click.option(
    "--manual-git",
    is_flag=True,
    help="Skip auto git commit/push/PR — print manual steps instead",
)
def contribute(
    *, file: str | None, dry_run: bool, skip_git_check: bool, manual_git: bool
) -> None:
    """Copy local artifact changes back to the warehouse for sharing.

    After editing synced artifacts and verifying they work with your agent,
    use this command to copy them back to the warehouse so the whole team
    benefits from the improvements.

    Without a FILE argument, all modified and added artifacts are contributed.

    Examples:

        abc contribute                                  # All modified/added

        abc contribute knowledge/python/type-hints.md   # Single file

        abc contribute --dry-run                        # Preview only

        abc contribute --manual-git                     # Skip auto PR creation
    """
    beacon_dir = Path.cwd() / ".agentic-beacon"
    if not beacon_dir.exists():
        console.print("[red]Error:[/red] No .agentic-beacon directory found.")
        console.print("Run 'abc warehouse connect' to connect to a warehouse first.")
        sys.exit(1)

    config_file = beacon_dir / "config.toml"
    if not config_file.exists():
        console.print("[red]Error:[/red] No warehouse connected.")
        console.print("Run 'abc warehouse connect --path <warehouse>' first.")
        sys.exit(1)

    beacon_yaml = beacon_dir / "beacon.yaml"
    if not beacon_yaml.exists():
        console.print("[red]Error:[/red] No beacon.yaml found.")
        console.print("Run 'abc setup' to create artifact configuration.")
        sys.exit(1)

    try:
        warehouse_settings = WarehouseSettings()
        warehouse_path = Path(warehouse_settings.warehouse.local_path)

        if not warehouse_path.exists():
            console.print(
                f"[red]Error:[/red] Warehouse path no longer exists: {warehouse_path}"
            )
            console.print(
                "Run 'abc warehouse connect --path <warehouse>' to reconnect."
            )
            sys.exit(1)

        # Check warehouse git cleanliness (skip if --dry-run or --skip-git-check)
        if not dry_run and not skip_git_check:
            git_error = _check_warehouse_git_clean(warehouse_path)
            if git_error:
                console.print(f"[red]Error:[/red] {git_error}")
                sys.exit(1)

        artifacts_dir = beacon_dir / "artifacts"
        beacon_settings = BeaconSettings.from_yaml(beacon_yaml)
        project_root = Path.cwd()
        comparator = DeltaComparator(
            warehouse_path=warehouse_path,
            artifacts_path=artifacts_dir,
            skills_paths=_build_skills_paths(project_root),
        )

        if dry_run:
            console.print("[dim]Dry run — no files will be copied.[/dim]\n")

        if file:
            contributed = _contribute_single(
                comparator,
                beacon_settings,
                beacon_yaml,
                warehouse_path,
                artifacts_dir,
                file,
                dry_run,
            )
        else:
            contributed = _contribute_all(
                comparator,
                beacon_settings,
                beacon_yaml,
                warehouse_path,
                artifacts_dir,
                dry_run,
            )

        if not dry_run and contributed:
            if manual_git:
                _print_contribute_next_steps(
                    warehouse_path, [p for p, _ in contributed]
                )
            else:
                _auto_git_contribute(warehouse_path, contributed)

    except Exception as e:
        console.print(f"\n[red]Error:[/red] Contribute failed: {e}")
        logger.exception("Contribute failed")
        sys.exit(1)


def _resolve_skill_contribute_source(
    comparator: DeltaComparator,
    relative_path: str,
    artifacts_dir: Path,
) -> Path | None:
    """Resolve which file to read when contributing a skill back to the warehouse.

    Skills live in agent-specific directories (.opencode/skills/, .claude/skills/).
    We need to decide which copy to contribute when multiple agents are present.

    Rules:
    - No agents configured → fall back to artifact snapshot (backward compat).
    - One agent modified → use that agent's copy.
    - Multiple agents modified with identical content → use any (they agree).
    - Multiple agents modified with different content → prompt user to choose.
    - No agent has a modified copy (IDENTICAL/MISSING/ADDED) → return None,
      letting the caller decide (IDENTICAL means nothing to contribute).

    Returns the absolute Path of the file to copy, or None if nothing to contribute.
    Exits with an error message if the user cancels the prompt.
    """
    if not comparator.skills_paths:
        # No agents detected — fall back to artifact snapshot
        return artifacts_dir / relative_path

    result = comparator.compare_file(relative_path)

    # Collect agents whose live copy differs from warehouse
    modified_agents = [
        agent
        for agent, status in result.agent_statuses.items()
        if status == DeltaStatus.MODIFIED
    ]

    if not modified_agents:
        # Nothing modified in any live dir — nothing to contribute
        return None

    # Build the candidate paths for modified agents
    candidates: dict[str, Path] = {}
    for agent in modified_agents:
        live_path = comparator._skill_live_path(agent, relative_path)
        if live_path.exists():
            candidates[agent] = live_path

    if not candidates:
        return None

    if len(candidates) == 1:
        return next(iter(candidates.values()))

    # Multiple agents have modified versions — check if they are identical
    hashes = {
        agent: comparator.compute_hash(path) for agent, path in candidates.items()
    }
    unique_hashes = set(hashes.values())

    if len(unique_hashes) == 1:
        # All modified copies are identical — pick the first one
        return next(iter(candidates.values()))

    # Genuinely different versions across agents — prompt the user
    console.print(
        f"\n[yellow]Conflict:[/yellow] '{relative_path}' has been modified differently across agents:\n"
    )
    agent_list = list(candidates.keys())
    for i, agent in enumerate(agent_list, 1):
        live_path = candidates[agent]
        console.print(f"  [{i}] {agent}")
        console.print(f"      [dim]{live_path}[/dim]")

    console.print()
    valid = [str(i) for i in range(1, len(agent_list) + 1)]
    while True:
        raw = click.prompt(
            f"Which version to contribute to the warehouse? ({'/'.join(valid)})",
            default="",
            show_default=False,
        ).strip()
        if raw in valid:
            break
        console.print(f"  [red]Invalid choice.[/red] Enter {' or '.join(valid)}.")

    chosen_agent = agent_list[int(raw) - 1]
    console.print(f"  Using [bold]{chosen_agent}[/bold] version.\n")
    return candidates[chosen_agent]


def _contribute_single(
    comparator: DeltaComparator,
    beacon_settings: BeaconSettings,
    beacon_yaml: Path,
    warehouse_path: Path,
    artifacts_dir: Path,
    file_path: str,
    dry_run: bool,
) -> list[tuple[str, str]]:
    """Contribute a single artifact back to the warehouse.

    If the file is not yet tracked in beacon.yaml, it will be auto-registered
    (inferred from path prefix: knowledge/, skills/, or contexts/).

    For skills: reads from the live agent directory rather than the artifact
    snapshot, matching the same source that abc delta inspects.

    Returns a list of (path, status_label) tuples for contributed files.
    """
    is_skill = file_path.startswith("skills/") and bool(comparator.skills_paths)

    if is_skill:
        # Resolve the live agent source (may prompt user if multiple agents conflict)
        local_path = _resolve_skill_contribute_source(
            comparator, file_path, artifacts_dir
        )
        if local_path is None:
            console.print(
                f"[yellow]Nothing to contribute.[/yellow] "
                f"'{file_path}' is identical to the warehouse version across all agents."
            )
            return []
    else:
        local_path = artifacts_dir / file_path
        if not local_path.exists():
            console.print(f"[red]Error:[/red] '{file_path}' does not exist locally.")
            console.print(
                "Create the file in .agentic-beacon/artifacts/ first, then contribute it."
            )
            sys.exit(1)

    all_paths = _collect_artifact_paths(comparator, beacon_settings)
    is_untracked = file_path not in all_paths

    if is_untracked:
        artifact_type = _infer_artifact_type(file_path)
        if artifact_type is None:
            console.print(
                f"[red]Error:[/red] '{file_path}' is not tracked in beacon.yaml "
                f"and its type cannot be inferred."
            )
            console.print(
                "Path must start with knowledge/, skills/, or contexts/ "
                "to be auto-registered."
            )
            sys.exit(1)

    if not is_skill:
        result = comparator.compare_file(file_path)
        if result.status == DeltaStatus.IDENTICAL:
            console.print(
                f"[yellow]Nothing to contribute.[/yellow] "
                f"'{file_path}' is identical to the warehouse version."
            )
            return []

    dest_existed = (warehouse_path / file_path).exists()
    _copy_to_warehouse(local_path, warehouse_path / file_path, file_path, dry_run)
    if not dry_run:
        if is_untracked and _register_in_beacon_yaml(
            beacon_settings, beacon_yaml, file_path
        ):
            console.print(f"  [dim]Registered in beacon.yaml:[/dim] {file_path}")
        status_label = "modified" if dest_existed else "added"
        return [(file_path, status_label)]
    return []


def _contribute_all(
    comparator: DeltaComparator,
    beacon_settings: BeaconSettings,
    beacon_yaml: Path,
    warehouse_path: Path,
    artifacts_dir: Path,
    dry_run: bool,
) -> list[tuple[str, str]]:
    """Contribute all modified and added artifacts back to the warehouse.

    Also discovers and contributes local files not yet tracked in beacon.yaml,
    registering them automatically.

    For skills: reads from live agent directories. If multiple agents have
    conflicting modifications the user is prompted to choose per-skill.

    Returns a list of (path, status_label) tuples for contributed files.
    """
    summary = comparator.compare_from_config(beacon_settings)
    contributable = summary.modified + summary.added

    # Also find local files not covered by any beacon.yaml pattern
    untracked = _find_untracked_local_files(comparator, beacon_settings, artifacts_dir)

    if not contributable and not untracked:
        console.print(
            "[green]Nothing to contribute.[/green] "
            "All local artifacts match the warehouse."
        )
        return []

    contributed: list[tuple[str, str]] = []

    # Contribute tracked modified/added files
    for result in contributable:
        is_skill = result.path.startswith("skills/") and bool(comparator.skills_paths)

        if is_skill:
            local_path = _resolve_skill_contribute_source(
                comparator, result.path, artifacts_dir
            )
            if local_path is None:
                console.print(
                    f"  [yellow]Skipping[/yellow] {result.path} "
                    "(no modified live copy found)"
                )
                continue
        else:
            local_path = artifacts_dir / result.path
            if not local_path.exists():
                console.print(
                    f"  [yellow]Skipping[/yellow] {result.path} (not found locally — run 'abc sync')"
                )
                continue

        _copy_to_warehouse(
            local_path, warehouse_path / result.path, result.path, dry_run
        )
        if not dry_run:
            status_label = (
                "modified" if result.status == DeltaStatus.MODIFIED else "added"
            )
            contributed.append((result.path, status_label))

    # Contribute untracked local files and register them in beacon.yaml
    for rel_path in untracked:
        artifact_type = _infer_artifact_type(rel_path)
        if artifact_type is None:
            console.print(
                f"  [yellow]Skipping[/yellow] {rel_path} "
                "(cannot infer artifact type — path must start with knowledge/, skills/, or contexts/)"
            )
            continue
        local_path = artifacts_dir / rel_path
        _copy_to_warehouse(local_path, warehouse_path / rel_path, rel_path, dry_run)
        if not dry_run:
            contributed.append((rel_path, "added"))
            if _register_in_beacon_yaml(beacon_settings, beacon_yaml, rel_path):
                console.print(f"  [dim]Registered in beacon.yaml:[/dim] {rel_path}")

    return contributed


def _copy_to_warehouse(
    local_path: Path, dest_path: Path, display_path: str, dry_run: bool
) -> None:
    """Copy a local artifact to the warehouse, creating parent dirs as needed."""
    if dry_run:
        console.print(f"  [dim]Would contribute:[/dim] {display_path}")
        return
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(local_path, dest_path)
    console.print(f"  [green]✓[/green] {display_path}")


def _print_contribute_next_steps(warehouse_path: Path, contributed: list[str]) -> None:
    """Print post-contribute git workflow (used when --manual-git is set)."""
    count = len(contributed)
    console.print(
        f"\n[bold green]✓ Contributed {count} file{'s' if count != 1 else ''} to warehouse[/bold green]"
    )
    console.print(f"  Warehouse: [dim]{warehouse_path}[/dim]\n")
    console.print("[bold]Next Steps — commit the changes in your warehouse:[/bold]")
    console.print(f"\n  cd {warehouse_path}")
    console.print("  git diff                    # Review what changed")
    console.print("  git add .")
    console.print('  git commit -m "feat: <describe your improvements>"')
    console.print("  git push\n")
    console.print("[dim]Teammates get the changes on their next:[/dim]")
    console.print("  cd ~/team-warehouse && git pull")
    console.print("  cd my-project && abc sync")


def _build_pr_body(contributed: list[tuple[str, str]]) -> str:
    """Build the PR body listing contributed artifacts with their status."""
    lines = ["## Contributed artifacts", ""]
    for path, status in contributed:
        lines.append(f"- `{path}` ({status})")
    return "\n".join(lines)


def _auto_git_contribute(
    warehouse_path: Path,
    contributed: list[tuple[str, str]],
) -> None:
    """Create a branch, commit, push, and open a PR for contributed artifacts.

    Falls back to manual-git output if .git is absent, any git step fails,
    gh is not installed, or the remote is not GitHub.
    """
    paths = [p for p, _ in contributed]
    count = len(paths)

    if not (warehouse_path / ".git").exists():
        console.print(
            "[yellow]Warning:[/yellow] Warehouse has no .git — skipping auto git workflow."
        )
        _print_contribute_next_steps(warehouse_path, paths)
        return

    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    branch = f"contrib/{timestamp}"

    def _git(args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(warehouse_path), *args],
            capture_output=True,
            text=True,
            timeout=30,
        )

    def _fallback(reason: str, detail: str = "") -> None:
        console.print(
            f"[yellow]Warning:[/yellow] {reason} — falling back to manual git."
        )
        if detail:
            console.print(f"  [dim]{detail}[/dim]")
        _print_contribute_next_steps(warehouse_path, paths)

    try:
        r = _git(["checkout", "-b", branch])
        if r.returncode != 0:
            _fallback("Could not create branch", r.stderr.strip())
            return
    except FileNotFoundError:
        _fallback("git not found")
        return
    except subprocess.TimeoutExpired:
        _fallback("git timed out")
        return

    r = _git(["add", "."])
    if r.returncode != 0:
        _fallback("git add failed", r.stderr.strip())
        return

    r = _git(["commit", "-m", "feat: contribute warehouse artifacts"])
    if r.returncode != 0:
        _fallback("git commit failed", r.stderr.strip())
        return

    r = _git(["push", "-u", "origin", branch])
    if r.returncode != 0:
        _fallback("git push failed", r.stderr.strip())
        return

    pr_body = _build_pr_body(contributed)
    try:
        r = subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--title",
                "feat: contribute warehouse artifacts",
                "--body",
                pr_body,
            ],
            cwd=str(warehouse_path),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if r.returncode != 0:
            console.print(
                "[yellow]Warning:[/yellow] Could not create PR — branch pushed, create PR manually."
            )
            if r.stderr.strip():
                console.print(f"  [dim]{r.stderr.strip()}[/dim]")
            console.print(
                f"\n[bold green]✓ Contributed {count} file{'s' if count != 1 else ''} to warehouse[/bold green]"
            )
            console.print(f"  Branch: [dim]{branch}[/dim]")
            return

        pr_url = r.stdout.strip()
        console.print(
            f"\n[bold green]✓ Contributed {count} file{'s' if count != 1 else ''} to warehouse[/bold green]"
        )
        console.print(f"  PR: [blue]{pr_url}[/blue]")

    except FileNotFoundError:
        console.print(
            "[yellow]Warning:[/yellow] gh not installed — branch pushed, create PR manually."
        )
        console.print(
            f"\n[bold green]✓ Contributed {count} file{'s' if count != 1 else ''} to warehouse[/bold green]"
        )
        console.print(f"  Branch: [dim]{branch}[/dim]")
        console.print(f"  cd {warehouse_path} && gh pr create")
    except subprocess.TimeoutExpired:
        console.print(
            "[yellow]Warning:[/yellow] gh timed out — branch pushed, create PR manually."
        )
        console.print(
            f"\n[bold green]✓ Contributed {count} file{'s' if count != 1 else ''} to warehouse[/bold green]"
        )
        console.print(f"  Branch: [dim]{branch}[/dim]")


# ========== Skill Commands ==========


def _update_beacon_yaml(beacon_dir: Path, files: list[str]) -> None:
    """Add installed file paths to beacon.yaml, creating it if absent."""
    beacon_yaml = beacon_dir / "beacon.yaml"

    if beacon_yaml.exists():
        try:
            settings = BeaconSettings.from_yaml(beacon_yaml)
        except Exception:
            return  # Don't corrupt a file we can't parse
    else:
        settings = BeaconSettings(artifacts=ArtifactsConfig())

    for path in files:
        parts = Path(path).parts
        artifact_type = parts[0] if parts else ""
        if artifact_type == "skills":
            if path not in settings.artifacts.skills:
                settings.artifacts.skills.append(path)
        elif artifact_type == "contexts":
            if path not in settings.artifacts.contexts:
                settings.artifacts.contexts.append(path)
        elif artifact_type == "knowledge":
            if path not in settings.artifacts.knowledge:
                settings.artifacts.knowledge.append(path)

    settings.to_yaml(beacon_yaml)


def _is_interactive() -> bool:
    """Return True if running in an interactive terminal."""
    return sys.stdin.isatty()


def _wire_contexts_opencode(project_root: Path, artifacts_dir: Path) -> list[str]:
    """Append synced context paths to opencode.json instructions.

    Returns the list of paths that were newly added (empty if nothing changed
    or opencode.json does not exist).
    """
    opencode_json = project_root / "opencode.json"
    if not opencode_json.exists():
        return []

    contexts_dir = artifacts_dir / "contexts"
    if not contexts_dir.exists():
        return []

    ctx_files = sorted(contexts_dir.rglob("*.md"))
    if not ctx_files:
        return []

    try:
        data = json.loads(opencode_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    instructions: list[str] = data.get("instructions", [])
    added: list[str] = []

    for ctx_file in ctx_files:
        rel_path = str(ctx_file.relative_to(project_root))
        if rel_path not in instructions:
            instructions.append(rel_path)
            added.append(rel_path)

    if added:
        data["instructions"] = instructions
        opencode_json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    return added


def _wire_contexts_claudecode(project_root: Path, artifacts_dir: Path) -> list[str]:
    """Append synced context @-references to CLAUDE.md.

    Checks .claude/CLAUDE.md then root CLAUDE.md. Returns the list of paths
    that were newly added (empty if nothing changed or no CLAUDE.md found).
    """
    claude_md = next(
        (
            p
            for p in [
                project_root / ".claude" / "CLAUDE.md",
                project_root / "CLAUDE.md",
            ]
            if p.exists()
        ),
        None,
    )
    if claude_md is None:
        return []

    contexts_dir = artifacts_dir / "contexts"
    if not contexts_dir.exists():
        return []

    ctx_files = sorted(contexts_dir.rglob("*.md"))
    if not ctx_files:
        return []

    existing = claude_md.read_text(encoding="utf-8")
    lines_to_append: list[str] = []
    added: list[str] = []

    for ctx_file in ctx_files:
        rel_path = str(ctx_file.relative_to(project_root))
        ref = f"@{rel_path}"
        if ref not in existing:
            lines_to_append.append(ref)
            added.append(rel_path)

    if lines_to_append:
        separator = "\n" if existing.endswith("\n") else "\n\n"
        claude_md.write_text(
            existing + separator + "\n".join(lines_to_append) + "\n",
            encoding="utf-8",
        )

    return added


def _init_opencode_json(project_root: Path) -> None:
    """Create a minimal opencode.json if one does not already exist."""
    opencode_json = project_root / "opencode.json"
    if not opencode_json.exists():
        data = {"$schema": "https://opencode.ai/config.json", "instructions": []}
        opencode_json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _init_claude_md(project_root: Path) -> None:
    """Create an empty CLAUDE.md at the project root if none exists."""
    claude_md = project_root / "CLAUDE.md"
    if not claude_md.exists():
        claude_md.write_text("", encoding="utf-8")


def _update_agent_gitignores(project_root: Path) -> None:
    """Add gitignore entries to agent subdirectory .gitignore files.

    Updates .claude/.gitignore and .opencode/.gitignore if those directories
    exist, creating the gitignore files if needed.
    """
    claude_dir = project_root / ".claude"
    if claude_dir.is_dir():
        GitignoreManager(claude_dir).ensure_entries(["skills/"])

    opencode_dir = project_root / ".opencode"
    if opencode_dir.is_dir():
        GitignoreManager(opencode_dir).ensure_entries(["skills/", "command/"])


def _wire_skills_post_sync(
    project_root: Path, artifacts_dir: Path
) -> tuple[list[str], list[str]]:
    """Install all synced skills for detected agents.

    Returns (installed, errors) where each entry is '<skill> (<agent>)'.
    Silently skips if no agents are detected.
    """
    agents = _detect_agents(project_root)
    if not agents:
        return [], []

    skills_dir = artifacts_dir / "skills"
    if not skills_dir.exists():
        return [], []

    skill_dirs = sorted(d for d in skills_dir.iterdir() if d.is_dir())
    if not skill_dirs:
        return [], []

    installed: list[str] = []
    errors: list[str] = []

    for skill_dir in skill_dirs:
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        content = skill_md.read_text(encoding="utf-8")
        description = _extract_skill_description(content)
        name = skill_dir.name

        for agent in agents:
            try:
                if agent == "opencode":
                    changed = _install_skill_opencode(
                        project_root, name, content, description
                    )
                else:
                    changed = _install_skill_claudecode(project_root, name, content)
                if changed:
                    installed.append(f"{name} ({agent})")
            except Exception as e:
                errors.append(f"{name} ({agent}): {e}")

    return installed, errors


def _detect_agents(project_root: Path) -> list[str]:
    """Detect which agent tools are configured in the project."""
    agents = []
    if (project_root / "opencode.json").exists():
        agents.append("opencode")
    if (project_root / ".claude").exists():
        agents.append("claudecode")
    return agents


def _extract_skill_description(content: str) -> str:
    """Extract description value from SKILL.md YAML frontmatter."""
    if not content.startswith("---"):
        return ""
    try:
        end = content.index("---", 3)
        for line in content[3:end].splitlines():
            if line.startswith("description:"):
                return line.split(":", 1)[1].strip()
    except ValueError:
        pass
    return ""


def _install_skill_opencode(
    project_root: Path, skill_name: str, content: str, description: str
) -> bool:
    """Install a skill for OpenCode: skill file + thin command stub.

    Returns True if files were written, False if already up-to-date.
    """
    skill_dest = project_root / ".opencode" / "skills" / skill_name
    skill_dest.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dest / "SKILL.md"

    stub = (
        f"---\ndescription: {description}\n---\n\n"
        f"Use the **skill** tool to load and execute the `{skill_name}` skill "
        f"with any provided arguments.\n"
    )
    command_dir = project_root / ".opencode" / "command"
    command_dir.mkdir(parents=True, exist_ok=True)
    stub_file = command_dir / f"{skill_name}.md"

    skill_unchanged = (
        skill_file.exists() and skill_file.read_text(encoding="utf-8") == content
    )
    stub_unchanged = (
        stub_file.exists() and stub_file.read_text(encoding="utf-8") == stub
    )

    if skill_unchanged and stub_unchanged:
        return False

    if not skill_unchanged:
        skill_file.write_text(content)
    if not stub_unchanged:
        stub_file.write_text(stub)

    return True


def _install_skill_claudecode(
    project_root: Path, skill_name: str, content: str
) -> bool:
    """Install a skill for Claude Code: copy SKILL.md to .claude/skills/<name>/.

    Returns True if the file was written, False if already up-to-date.
    """
    dest = project_root / ".claude" / "skills" / skill_name
    dest.mkdir(parents=True, exist_ok=True)
    dest_file = dest / "SKILL.md"

    if dest_file.exists() and dest_file.read_text(encoding="utf-8") == content:
        return False

    dest_file.write_text(content)
    return True


def _print_skill_next_steps(agents: list[str]) -> None:
    """Print agent-specific guidance after install."""
    console.print("\n[bold]Next Steps:[/bold]")
    if "opencode" in agents:
        console.print(
            "  [bold]OpenCode[/bold] — restart your session to pick up new commands"
        )
    if "claudecode" in agents:
        console.print(
            "  [bold]Claude Code[/bold] — skills are available as /skill-name in new sessions"
        )


# ========== Legacy Commands ==========


@main.command(name="init", hidden=True)
@click.argument("name", required=False)
def deprecated_init(name: str | None = None) -> None:
    """Deprecated: Use 'abc warehouse init' instead."""
    console.print(
        "[red]Error:[/red] 'abc init' has been moved to 'abc warehouse init'."
    )
    console.print("\n[bold]New command:[/bold]")
    if name:
        console.print(f"  abc warehouse init {name}")
    else:
        console.print("  abc warehouse init <name>")
    sys.exit(1)


@main.command()
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Path to project root (auto-detected if not provided)",
)
def update(*, project: Path | None) -> None:
    """Update existing synced artifacts from warehouse (re-runs sync, overwrites changes)."""
    project_root = project or find_project_root()
    beacon_dir = project_root / ".agentic-beacon"

    if not beacon_dir.exists():
        console.print(f"[red]Error:[/red] No warehouse connected at {project_root}")
        console.print("Run 'abc warehouse connect' first.")
        sys.exit(1)

    if not (beacon_dir / "beacon.yaml").exists():
        console.print("[red]Error:[/red] No beacon.yaml found.")
        console.print("Run 'abc setup' to create artifact configuration.")
        sys.exit(1)

    console.print("[blue]Updating artifacts from warehouse...[/blue]")

    try:
        from .core.settings import BeaconSettings, WarehouseSettings
        from .core.sync import SyncEngine

        warehouse_settings = WarehouseSettings()
        warehouse_path = Path(warehouse_settings.warehouse.local_path)
        beacon_settings = BeaconSettings.from_yaml(beacon_dir / "beacon.yaml")

        artifacts_dir = beacon_dir / "artifacts"
        artifacts_dir.mkdir(exist_ok=True)

        sync_engine = SyncEngine(
            warehouse_path=warehouse_path, artifacts_path=artifacts_dir
        )

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
                artifact_paths.extend(
                    sync_engine.expand_glob(f"skills/{skill_name}/**/*")
                )
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

        console.print("\n[bold green]✓ Update complete![/bold green]")
        console.print(f"  [blue]Updated:[/blue] {overwritten_count} files")
        console.print(
            f"  [blue]New:[/blue] {copied_count - overwritten_count if copied_count > overwritten_count else 0} files"
        )
        if error_count > 0:
            console.print(f"  [red]Errors:[/red] {error_count} files")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Update failed")
        sys.exit(1)


@main.command(name="list")
@click.argument(
    "artifact_type",
    required=False,
    type=click.Choice(["knowledge", "skills", "contexts"], case_sensitive=False),
    default=None,
)
def list_cmd(*, artifact_type: str | None) -> None:
    """List artifacts synced to the current project.

    ARTIFACT_TYPE filters output to a single type. Omit to show all.

    Reads from .agentic-beacon/artifacts/. Run 'abc sync' first to populate.

    Example:
        abc list
        abc list knowledge
        abc list skills
        abc list contexts
    """
    beacon_dir = Path.cwd() / ".agentic-beacon"
    artifacts_dir = beacon_dir / "artifacts"

    if not artifacts_dir.exists():
        console.print("[red]Error:[/red] No synced artifacts found.")
        console.print("Run 'abc sync' to download artifacts from the warehouse.")
        sys.exit(1)

    types_to_show = (
        [artifact_type] if artifact_type else ["contexts", "knowledge", "skills"]
    )

    section_config = {
        "contexts": ("Synced Contexts", "cyan", "Context"),
        "knowledge": ("Synced Knowledge", "green", "File"),
        "skills": ("Synced Skills", "yellow", "Skill"),
    }

    any_shown = False
    for section in types_to_show:
        section_dir = artifacts_dir / section
        if not section_dir.exists():
            continue

        files = sorted(
            str(f.relative_to(artifacts_dir))
            for f in section_dir.rglob("*")
            if f.is_file() and not f.name.startswith(".")
        )

        if files:
            title, color, col_name = section_config[section]
            table = Table(title=title)
            table.add_column(col_name, style=color)
            for item in files:
                table.add_row(item)
            console.print(table)
            console.print()
            any_shown = True

    if not any_shown:
        label = artifact_type or "artifacts"
        console.print(
            f"[yellow]No {label} found in .agentic-beacon/artifacts/.[/yellow]"
        )
        console.print("Run 'abc sync' to download artifacts from the warehouse.")


@main.command()
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Path to project root (auto-detected if not provided)",
)
@click.confirmation_option(prompt="Are you sure you want to remove synced artifacts?")
def clean(*, project: Path | None) -> None:
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
def status(*, project: Path | None) -> None:
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
            console.print(
                f"[blue]Warehouse:[/blue] {warehouse_settings.warehouse.local_path}"
            )
        except Exception:
            console.print(f"[blue]Config:[/blue] {config_file}")

    if not artifacts_dir.exists():
        console.print("\n[yellow]No artifacts synced yet.[/yellow]")
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
                synced = (artifacts_dir / ctx).exists()
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
                synced = (artifacts_dir / skill).exists()
                status_str = "[green]✓[/green]" if synced else "[red]✗[/red]"
                table.add_row(f"{status_str} {skill}")
            console.print(table)
            console.print()

        _warn_missing_bundled_skills(beacon_settings)

    # Count synced files
    import os

    file_count = sum(len(files) for _, _, files in os.walk(str(artifacts_dir)))
    console.print(f"[blue]Artifacts location:[/blue] {artifacts_dir}")
    console.print(f"[blue]Total synced files:[/blue] {file_count}")


def _interactive_select(
    prompt: str, options: list[str], *, default_all: bool = False
) -> list[str]:
    """Interactive selection of options."""
    if not options:
        return []

    console.print(f"\n[bold]{prompt}[/bold]")
    console.print(
        "[dim]Enter numbers separated by commas, or 'all' for all options[/dim]"
    )

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
