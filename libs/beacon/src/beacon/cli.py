"""CLI interface for Beacon - Distribute knowledge contexts for AI development."""

import sys
from pathlib import Path
from typing import List, Optional

import click
from loguru import logger
from rich.console import Console
from rich.table import Table

from .core.settings import WarehouseSettings, BeaconSettings, validate_beacon_directory
from .core.sync import SyncEngine
from .core.delta import DeltaComparator, DeltaStatus
from .core.gitignore import GitignoreManager
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


# ========== Warehouse Management Commands ==========


@main.group()
def warehouse() -> None:
    """Warehouse management commands (init, connect)."""
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
            console.print("  [blue]Git:[/blue] Initialized with initial commit")

        # Next steps
        console.print("\n[bold]Next Steps:[/bold]")
        console.print(f"  1. cd {warehouse_path}")
        console.print("  2. Customize contexts, knowledge, and skills")
        console.print("  3. git remote add origin <your-repo-url>")
        console.print("  4. git push -u origin main")

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

        # Update .gitignore
        gitignore_mgr = GitignoreManager(Path.cwd())
        if gitignore_mgr.ensure_entries():
            console.print("[green]✓[/green] Updated .gitignore")

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
        _create_beacon_template(beacon_yaml)
        _install_project_setup_skill(beacon_dir)
        console.print("\n[bold green]✓ Agent-assisted setup ready[/bold green]")
        console.print(f"  [blue]beacon.yaml:[/blue] {beacon_yaml}")
        console.print(f"  [blue]Catalog:[/blue] {beacon_dir / 'warehouse-catalog.md'}")
        console.print("\n[bold]Next Steps:[/bold]")
        console.print("  1. Open your AI agent (Cursor, Copilot, etc.)")
        console.print("  2. Ask it to read .agentic-beacon/warehouse-catalog.md")
        console.print("  3. Have it analyze your project and populate beacon.yaml")
        console.print("  4. Run 'abc sync' to download artifacts")


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
    # - languages/python/**/*.md
    # - infrastructure/docker-standards.md

  skills: []
    # Examples:
    # - code-review/SKILL.md
    # - generate-unit-tests/SKILL.md

  skills: []
    # Skill directory name in warehouse skills/ directory
    # Examples:
    # - code-review/SKILL.md
    # - generate-unit-tests/SKILL.md

  contexts: []
    # Examples:
    # - AGENTS.global.md
    # - teams/backend/AGENTS.md
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
            console.print("[yellow]Warning:[/yellow] Warehouse path not found, skipping catalog generation")
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
        lines.append(f"Paths are relative to warehouse root. Use in beacon.yaml under `artifacts.{section_dir}`.")
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

    lines.extend([
        "## Usage",
        "",
        "Add paths to your `.agentic-beacon/beacon.yaml` file:",
        "",
        "```yaml",
        "artifacts:",
        "  knowledge:",
        "    - languages/python/**/*.md  # Glob pattern",
        "    - infrastructure/docker-standards.md  # Specific file",
        "  skills:",
        "    - code-review/SKILL.md",
        "  contexts:",
        "    - AGENTS.global.md",
        "```",
        "",
        "Then run `abc sync` to download the artifacts.",
        "",
    ])

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
@click.option("--verbose", "verbose_flag", is_flag=True, help="Show detailed sync output")
def sync(*, preserve: bool, prune: bool, verbose_flag: bool) -> None:
    """
    Sync artifacts from warehouse to project.

    Reads .agentic-beacon/beacon.yaml and copies specified artifacts
    from the connected warehouse to .agentic-beacon/artifacts/ directory.

    Example:
        abc sync              # Sync all artifacts
        abc sync --preserve   # Skip locally modified files
        abc sync --prune      # Remove artifacts not in beacon.yaml
        abc sync --verbose    # Show detailed output
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
            console.print(f"[red]Error:[/red] Warehouse path no longer exists: {warehouse_path}")
            console.print("The warehouse may have been moved or deleted.")
            console.print("Run 'abc warehouse connect --path <warehouse>' to reconnect.")
            sys.exit(1)

        # Load beacon.yaml
        beacon_settings = BeaconSettings.from_yaml(beacon_yaml)

        # Check if there are any artifacts to sync
        total_artifacts = (
            len(beacon_settings.artifacts.knowledge) +
            len(beacon_settings.artifacts.skills) +
            len(beacon_settings.artifacts.contexts)
        )

        if total_artifacts == 0:
            console.print("[yellow]No artifacts configured in beacon.yaml. Nothing to sync.[/yellow]")
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
        console.print("\n[blue]Syncing artifacts from warehouse...[/blue]\n")

        for artifact_type in ["knowledge", "skills", "contexts"]:
            artifacts_list = getattr(beacon_settings.artifacts, artifact_type)
            for pattern in artifacts_list:
                # Check if pattern contains glob characters
                if "*" in pattern or "?" in pattern or "[" in pattern:
                    try:
                        matches = sync_engine.expand_glob(pattern)
                        if not matches:
                            console.print(f"  [yellow]Warning:[/yellow] No files matched pattern: {pattern}")
                        elif verbose_flag:
                            console.print(f"  Pattern '{pattern}' matched {len(matches)} files")
                        artifact_paths.extend(matches)
                    except Exception as e:
                        console.print(f"  [red]Error:[/red] Invalid glob pattern '{pattern}': {e}")
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
            log_fn=log_fn if verbose_flag else None,
        )

        # Update .gitignore
        gitignore_mgr = GitignoreManager(Path.cwd())
        gitignore_mgr.ensure_entries()

        # Display summary
        console.print(f"\n[bold green]✓ Sync complete[/bold green]")
        console.print(f"  [blue]Copied:[/blue] {summary.copied} files")
        console.print(f"  [blue]Unchanged:[/blue] {summary.skipped} files")
        if summary.preserved > 0:
            console.print(f"  [yellow]Preserved:[/yellow] {summary.preserved} locally modified files")
            console.print("  [dim]Use 'abc delta' to review local changes.[/dim]")
        if summary.pruned > 0:
            console.print(f"  [yellow]Pruned:[/yellow] {summary.pruned} artifacts no longer in beacon.yaml")
        if summary.errors > 0:
            console.print(f"  [red]Errors:[/red] {summary.errors} files")

    except Exception as e:
        console.print(f"\n[red]Error:[/red] Sync failed: {e}")
        logger.exception("Sync failed")
        sys.exit(1)


@main.command()
@click.argument("file", required=False, type=str)
@click.option("--no-color", is_flag=True, help="Disable color output in diffs")
def delta(*, file: Optional[str], no_color: bool) -> None:
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
            console.print(f"[red]Error:[/red] Warehouse path no longer exists: {warehouse_path}")
            console.print("Run 'abc warehouse connect --path <warehouse>' to reconnect.")
            sys.exit(1)

        artifacts_dir = beacon_dir / "artifacts"
        beacon_settings = BeaconSettings.from_yaml(beacon_yaml)

        comparator = DeltaComparator(
            warehouse_path=warehouse_path,
            artifacts_path=artifacts_dir,
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


def _show_delta_summary(comparator: DeltaComparator, beacon_settings: BeaconSettings) -> None:
    """Show summary of all artifact differences."""
    summary = comparator.compare_from_config(beacon_settings)

    if not summary.has_differences:
        console.print("[green]No differences found. Local artifacts match warehouse.[/green]")
        return

    # Show differences
    console.print("\n[bold]Artifact Differences:[/bold]\n")

    for result in summary.results:
        if result.status == DeltaStatus.MODIFIED:
            console.print(f"  [yellow][Modified][/yellow] {result.path}")
        elif result.status == DeltaStatus.ADDED:
            console.print(f"  [green][Added][/green]    {result.path}")
        elif result.status == DeltaStatus.MISSING:
            console.print(f"  [red][Missing][/red]  {result.path}")

    # Summary counts
    console.print(f"\n[bold]Summary:[/bold]")
    if summary.modified:
        console.print(f"  [yellow]Modified:[/yellow] {len(summary.modified)} files")
    if summary.added:
        console.print(f"  [green]Added:[/green] {len(summary.added)} files")
    if summary.missing:
        console.print(f"  [red]Missing:[/red] {len(summary.missing)} files")
    if summary.identical:
        console.print(f"  [dim]Identical:[/dim] {len(summary.identical)} files")

    # Tips
    if summary.missing:
        console.print("\n[dim]Tip: Run 'abc sync' to download missing artifacts from warehouse.[/dim]")
    if summary.modified:
        console.print("[dim]Tip: Run 'abc delta <file>' to see detailed diff for a modified file.[/dim]")


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
        console.print(f"[red]Error:[/red] File '{file_path}' is not tracked in beacon.yaml.")
        console.print("Only artifacts declared in beacon.yaml can be compared.")
        sys.exit(1)

    # Compare the specific file
    result = comparator.compare_file(file_path)

    if result.status == DeltaStatus.IDENTICAL:
        console.print(f"[green]No differences found.[/green] Local and warehouse versions of '{file_path}' are identical.")
        return

    if result.status == DeltaStatus.MISSING:
        console.print(f"[red][Missing][/red] '{file_path}' has not been synced locally.")
        console.print("[dim]Run 'abc sync' to download it.[/dim]")
        return

    if result.status == DeltaStatus.ADDED:
        console.print(f"[green][Added][/green] '{file_path}' exists locally but not in warehouse.")
        return

    # Show detailed diff
    console.print(f"\n[bold]Diff: {file_path}[/bold]\n")
    diff_output = comparator.detailed_diff(file_path, color=not no_color)
    if diff_output:
        console.print(diff_output)
    else:
        console.print("[dim]No differences to display.[/dim]")


def _collect_artifact_paths(comparator: DeltaComparator, beacon_settings: BeaconSettings) -> set:
    """Collect all artifact paths from beacon.yaml, expanding globs."""
    sync_engine = SyncEngine(
        warehouse_path=comparator.warehouse_path,
        artifacts_path=comparator.artifacts_path,
    )
    paths = set()
    for artifact_type in ["knowledge", "skills", "contexts"]:
        patterns = getattr(beacon_settings.artifacts, artifact_type)
        for pattern in patterns:
            if "*" in pattern or "?" in pattern or "[" in pattern:
                matches = sync_engine.expand_glob(pattern)
                paths.update(matches)
            else:
                paths.add(pattern)
    return paths


# ========== Legacy Commands ==========


@main.command(name="init", hidden=True)
@click.argument("name", required=False)
def deprecated_init(name: Optional[str] = None) -> None:
    """Deprecated: Use 'abc warehouse init' instead."""
    console.print("[red]Error:[/red] 'abc init' has been moved to 'abc warehouse init'.")
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


@main.command(name="list")
@click.option(
    "--warehouse",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Path to warehouse repository (auto-detected if not provided)",
)
def list_cmd(*, warehouse: Optional[Path]) -> None:
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
