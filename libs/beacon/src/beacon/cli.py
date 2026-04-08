"""CLI interface for Beacon - Distribute knowledge contexts for AI development."""

import datetime
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC
from pathlib import Path

import click
from loguru import logger
from rich.console import Console
from rich.table import Table

from .core.delta import ComparisonResult, DeltaComparator, DeltaStatus
from .core.gitignore import GitignoreManager
from .core.settings import ArtifactsConfig, BeaconSettings, WarehouseSettings
from .core.sync import OrphanInfo, SyncEngine
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
    """Check if the warehouse git working tree is clean and up to date with remote.

    Returns an error message string if there are uncommitted changes or if the
    local branch is behind its remote tracking branch, or None if everything is
    clean / not a git repo / git not installed.
    """
    if not (warehouse_path / ".git").exists():
        return None  # Not a git repo — skip silently

    short_path = str(warehouse_path).replace(str(Path.home()), "~")

    def _git(args: list[str], timeout: int = 10) -> subprocess.CompletedProcess | None:
        try:
            return subprocess.run(
                ["git", "-C", str(warehouse_path), *args],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except FileNotFoundError:
            return None
        except subprocess.TimeoutExpired:
            return None

    # Check working tree cleanliness
    result = _git(["status", "--porcelain"])
    if result is None:
        console.print(
            "[yellow]Warning:[/yellow] git not available — skipping warehouse clean check."
        )
        return None

    if result.stdout.strip():
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

    # Fetch remote silently to get up-to-date tracking info
    fetch_result = _git(["fetch", "--quiet"], timeout=15)
    if fetch_result is None:
        console.print(
            "[yellow]Warning:[/yellow] git fetch timed out or git not found — skipping remote check."
        )
        return None

    # Check if local branch is behind the remote tracking branch
    behind_result = _git(["rev-list", "--count", "HEAD..@{u}"])
    if behind_result is None or behind_result.returncode != 0:
        # No upstream configured or other error — skip silently
        return None

    behind_count_str = behind_result.stdout.strip()
    try:
        behind_count = int(behind_count_str)
    except ValueError:
        return None

    if behind_count > 0:
        return (
            f"Warehouse is behind its remote by {behind_count} commit(s).\n"
            f"  Warehouse: {short_path}\n\n"
            f"  Pull the latest changes before contributing to avoid creating a\n"
            f"  stale PR or overwriting newer warehouse content:\n"
            f"    cd {short_path}\n"
            f"    git pull\n\n"
            f"  Use --skip-git-check to bypass this check."
        )

    return None


def _check_warehouse_on_main_branch(warehouse_path: Path) -> str | None:
    """Check that the warehouse git repo is on the main (or master) branch.

    Returns an error message string if the warehouse is on a non-main branch,
    or None if everything looks good / not a git repo / git not installed.
    """
    if not (warehouse_path / ".git").exists():
        return None  # Not a git repo — skip silently

    short_path = str(warehouse_path).replace(str(Path.home()), "~")

    try:
        result = subprocess.run(
            ["git", "-C", str(warehouse_path), "symbolic-ref", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        return None  # git not available — skip silently
    except subprocess.TimeoutExpired:
        console.print(
            "[yellow]Warning:[/yellow] git timed out — skipping branch check."
        )
        return None

    if result.returncode != 0:
        # Detached HEAD or other error — treat as non-main
        return (
            f"Warehouse is in a detached HEAD state (not on any branch).\n"
            f"  Warehouse: {short_path}\n\n"
            f"  Switch to the main branch before syncing:\n"
            f"    cd {short_path}\n"
            f"    git checkout main\n\n"
            f"  Use --skip-git-check to bypass this check."
        )

    current_branch = result.stdout.strip()
    main_branches = {"main", "master"}
    if current_branch not in main_branches:
        return (
            f"Warehouse is on branch '{current_branch}', not 'main'.\n"
            f"  Warehouse: {short_path}\n\n"
            f"  This usually means you have a contribution in progress.\n"
            f"  Before switching branches, make sure your work is published:\n"
            f"    - Open a PR or push your branch so the work isn't lost\n"
            f"    - Or run 'abc contribute' to package it up first\n\n"
            f"  Then switch to main:\n"
            f"    cd {short_path}\n"
            f"    git checkout main\n\n"
            f"  Use --skip-git-check to bypass this check."
        )

    return None


_SYNC_STATE_FILENAME = ".sync-state"


def _get_warehouse_head_sha(warehouse_path: Path) -> str | None:
    """Return the current HEAD commit SHA of the warehouse git repo, or None."""
    if not (warehouse_path / ".git").exists():
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(warehouse_path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _write_sync_state(artifacts_dir: Path, warehouse_path: Path) -> None:
    """Record the warehouse HEAD SHA into the artifacts sync-state file.

    Called at the end of a successful (non-dry-run) sync so contribute can
    verify the snapshot was taken against the current warehouse HEAD.
    """
    sha = _get_warehouse_head_sha(warehouse_path)
    if sha is None:
        return  # Warehouse has no git — nothing to record
    state_file = artifacts_dir / _SYNC_STATE_FILENAME
    state_file.write_text(sha + "\n")


def _check_sync_state(artifacts_dir: Path, warehouse_path: Path) -> str | None:
    """Check that the local artifact snapshot is current with the warehouse HEAD.

    Returns a warning message string if:
    - artifacts_dir does not exist or is empty (sync never run), OR
    - the recorded sync SHA does not match the current warehouse HEAD (stale snapshot)

    Returns None if everything looks current, or if the warehouse has no git.
    """
    if not (warehouse_path / ".git").exists():
        return None  # No git in warehouse — skip

    # artifacts_dir missing or empty → sync was never run
    if not artifacts_dir.exists() or not any(
        f for f in artifacts_dir.iterdir() if f.name != _SYNC_STATE_FILENAME
    ):
        return "No artifacts found — run 'abc sync' before contributing.\n\n  abc sync"

    state_file = artifacts_dir / _SYNC_STATE_FILENAME
    if not state_file.exists():
        # Sync was run before sync-state tracking was introduced — warn softly
        return (
            "Sync state is unknown. Run 'abc sync' to ensure your snapshot is\n"
            "  current before contributing to avoid overwriting newer warehouse content.\n\n"
            "  abc sync"
        )

    recorded_sha = state_file.read_text().strip()
    current_sha = _get_warehouse_head_sha(warehouse_path)

    if current_sha is None:
        return None  # Can't determine current SHA — skip silently

    if recorded_sha != current_sha:
        return (
            "Local artifact snapshot is based on an older warehouse commit.\n"
            "  The warehouse has been updated since your last sync — contributing\n"
            "  now risks overwriting newer warehouse content with stale local changes.\n\n"
            "  Run 'abc sync' to refresh your snapshot first:\n"
            "    abc sync\n\n"
            "  Use --skip-git-check to bypass this check."
        )

    return None


_GLOBAL_SYNC_STATE_VERSION = 1


def _global_sync_state_file() -> Path:
    """Return path to the global agent sync-state file (lazy, respects Path.home() mocking)."""
    return Path.home() / ".config" / "agentic-beacon" / "sync-state.json"


def _read_global_sync_state() -> dict:
    """Read global agent sync-state from ~/.config/agentic-beacon/sync-state.json.

    Returns empty dict if file does not exist, is unparseable, or has unknown version.
    """
    import json

    state_file = _global_sync_state_file()
    if not state_file.exists():
        return {}
    try:
        raw = state_file.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Could not read global sync state: {e}")
        return {}
    version = data.get("version")
    if version != _GLOBAL_SYNC_STATE_VERSION:
        logger.warning(f"Global sync state has unknown version {version!r}, skipping.")
        return {}
    return data


def _write_global_sync_state(state: dict) -> None:
    """Write global agent sync-state to ~/.config/agentic-beacon/sync-state.json.

    Always writes version field at the top level.
    """
    import json

    state_file = _global_sync_state_file()
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state["version"] = _GLOBAL_SYNC_STATE_VERSION
    state_file.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _write_agent_sync_state(
    warehouse_path: Path, relative_path: str, content_hash: str
) -> None:
    """Upsert an agent install entry into the global sync-state file.

    Entry schema:
        {"content_hash": "...", "warehouse_head": "...", "installed_at": "..."}
    """
    from datetime import datetime

    state = _read_global_sync_state()
    warehouses = state.get("warehouses", {})
    wh_key = str(warehouse_path)
    wh_entries = warehouses.setdefault(wh_key, {})
    wh_entries[relative_path] = {
        "content_hash": content_hash,
        "warehouse_head": _get_warehouse_head_sha(warehouse_path) or "",
        "installed_at": datetime.now(UTC).isoformat(),
    }
    state["warehouses"] = warehouses
    _write_global_sync_state(state)


def _relink_global_sync_state(current_warehouse_path: Path) -> bool:
    """Prompt user to relink sync-state when warehouse has been moved/renamed.

    Returns True if the state was relinked (key renamed), False otherwise.
    """
    state = _read_global_sync_state()
    warehouses = state.get("warehouses", {})
    current_key = str(current_warehouse_path)

    if current_key in warehouses:
        return False  # Already have state for this path

    if not warehouses:
        return False

    # Find candidate old paths whose directory name matches the current warehouse name
    current_name = current_warehouse_path.name
    candidates = [
        old_path
        for old_path in warehouses
        if Path(old_path).name == current_name and old_path != current_key
    ]

    if not candidates:
        return False

    if len(candidates) == 1:
        old_key = candidates[0]
        console.print(
            f"\n[yellow]No tracking state found for[/yellow] {current_key}\n"
            f"[yellow]Found existing state for[/yellow] {old_key}\n"
            f"Is this the same warehouse? [y/N] (Relinks tracking state) ",
            end="",
        )
        try:
            answer = click.prompt("", default="N", prompt_suffix="")
        except click.Abort:
            return False
        if answer.strip().lower() != "y":
            return False
        warehouses[current_key] = warehouses.pop(old_key)
        state["warehouses"] = warehouses
        _write_global_sync_state(state)
        return True
    else:
        # Multiple candidates — ask user to pick
        console.print(f"\n[yellow]No tracking state found for[/yellow] {current_key}")
        console.print("[yellow]Found existing state for multiple paths:[/yellow]")
        for i, cand in enumerate(candidates, 1):
            console.print(f"  {i}. {cand}")
        console.print("  0. None — skip relink\n")
        try:
            choice_str = click.prompt(
                "Which path is the same warehouse?",
                default="0",
            )
            choice = int(choice_str)
        except (click.Abort, ValueError):
            return False
        if choice == 0 or choice > len(candidates):
            return False
        old_key = candidates[choice - 1]
        warehouses[current_key] = warehouses.pop(old_key)
        state["warehouses"] = warehouses
        _write_global_sync_state(state)
        return True


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
            "that are relevant. Run `abc sync` when done. [/on dark_green]\n"
        )


def _bundled_global_skill_dirs() -> dict[str, Path]:
    """Return global agent skill directories for bundled skill installation.

    These are the user-level skill dirs read by opencode and Claude Code
    regardless of which project is active.
    """
    return {
        "opencode": Path.home() / ".config" / "opencode" / "skills",
        "claudecode": Path.home() / ".claude" / "skills",
    }


def _global_agent_dirs() -> dict[str, Path]:
    """Return global agent definition directories per tool."""
    return {
        "opencode": Path.home() / ".config" / "opencode" / "agents",
        "claudecode": Path.home() / ".claude" / "agents",
    }


def _detect_agents_global() -> list[str]:
    """Detect which agent tools are available on this machine via home-dir paths.

    Checks only home-directory paths (not project-relative paths).
    Returns list of tool names: 'opencode' and/or 'claudecode'.
    """
    tools = []
    opencode_dir = Path.home() / ".config" / "opencode"
    if opencode_dir.is_dir():
        tools.append("opencode")
    claudecode_dir = Path.home() / ".claude"
    if claudecode_dir.is_dir():
        tools.append("claudecode")
    return tools


def _install_agent_global(agent: str, agent_name: str, content: str) -> bool:
    """Write an agent definition file to the global agent directory for a tool.

    Creates parent dirs if needed.
    Returns True if the file was written, False if content was identical (skipped).
    Conflict handling is the caller's responsibility (soft block pre-check).

    Args:
        agent: Tool name — "opencode" or "claudecode".
        agent_name: Filename (e.g. "code-reviewer.md").
        content: File content to write.
    """
    agent_dirs = _global_agent_dirs()
    dest = agent_dirs[agent] / agent_name
    if dest.exists() and dest.read_text(encoding="utf-8") == content:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    return True


def _list_global_agents() -> None:
    """Display globally installed agent files from all detected tool directories."""
    agent_dirs = _global_agent_dirs()

    # Union of all agent filenames across detected tools, deduplicated
    seen: dict[str, list[str]] = {}  # filename -> list of tools that have it
    for tool, agent_dir in agent_dirs.items():
        if not agent_dir.exists():
            continue
        for f in sorted(agent_dir.rglob("*.md")):
            if f.is_file() and not f.name.startswith("."):
                name = f.name
                seen.setdefault(name, []).append(tool)

    if not seen:
        console.print("[yellow]No agents found.[/yellow]")
        console.print("Install agents with: abc install agents/<name>.md")
        return

    table = Table(title="Installed Agents (Global)")
    table.add_column("Agent", style="magenta")
    table.add_column("Tools", style="dim")
    for name in sorted(seen):
        table.add_row(name, ", ".join(seen[name]))
    console.print(table)


def _install_bundled_skills_globally() -> tuple[list[str], list[str]]:
    """Install abc-bundled skills into global agent skill directories.

    Writes directly to ~/.config/opencode/skills/ and ~/.claude/skills/,
    bypassing the warehouse and any per-project agent detection.  Skills
    are available in every project as soon as they are installed.

    # Bundled skills are abc-package-managed — not user content; exempt from soft block

    Returns (installed, errors) where each entry is '<skill> (<agent>)'.
    """
    bundled_skills_dir = Path(__file__).parent / "data" / "skills"
    if not bundled_skills_dir.exists():
        return [], []

    global_dirs = _bundled_global_skill_dirs()
    installed: list[str] = []
    errors: list[str] = []

    for skill_dir in sorted(bundled_skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        content = skill_md.read_text(encoding="utf-8")
        name = skill_dir.name

        for agent, skills_root in global_dirs.items():
            try:
                dest = skills_root / name / "SKILL.md"
                if dest.exists() and dest.read_text(encoding="utf-8") == content:
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content, encoding="utf-8")
                installed.append(f"{name} ({agent})")
            except Exception as e:
                errors.append(f"{name} ({agent}): {e}")

    return installed, errors


def _print_bundled_install_result(installed: list[str], errors: list[str]) -> None:
    """Print the result of a bundled skill install to the console."""
    if installed:
        names = ", ".join(s.split(" (")[0] for s in dict.fromkeys(installed))
        console.print(
            f"[green]✓[/green] Installed bundled skill(s) ({names}) "
            "[dim]— managed by abc, no beacon.yaml entry needed[/dim]"
        )
    for err in errors:
        console.print(f"  [yellow]⚠[/yellow] Bundled skill wiring: {err}")


def _show_bundled_skills_status() -> None:
    """Print bundled skill installation status for the status command.

    Checks global agent skill dirs — bundled skills are user-level,
    not per-project.
    """
    bundled_skills_dir = Path(__file__).parent / "data" / "skills"
    if not bundled_skills_dir.exists():
        return

    skill_names = sorted(
        d.name
        for d in bundled_skills_dir.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    )
    if not skill_names:
        return

    global_dirs = _bundled_global_skill_dirs()

    table = Table(title="Bundled Skills (abc-managed, global)")
    table.add_column("Skill", style="yellow")
    for name in skill_names:
        installed_in_all = all(
            (skills_root / name / "SKILL.md").exists()
            for skills_root in global_dirs.values()
        )
        status_str = "[green]✓[/green]" if installed_in_all else "[red]✗[/red]"
        table.add_row(f"{status_str} {name}")
    console.print(table)
    console.print()


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

  skills: []
    # Examples:
    # - skills/code-review/SKILL.md
    # - skills/generate-unit-tests/SKILL.md
    # Note: abc bundled skills (e.g. record-knowledge) are installed globally
    #       into ~/.config/opencode/skills/ and ~/.claude/skills/ by 'abc sync'
    #       — they are not project-scoped and need no entry here.

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


def _handle_soft_block(
    conflicts: list[str],
    force: bool,
    preserve: bool,
) -> bool:
    """Handle soft-block pre-check for conflicting files.

    Returns True if we should proceed with overwriting, False to skip conflicts.
    May call sys.exit(1) in non-interactive mode when conflicts exist without flags.

    Args:
        conflicts: List of relative paths that have conflicting local content
        force: --force flag (overwrite without prompt)
        preserve: --preserve flag (skip without prompt)

    Returns:
        True to proceed (overwrite), False to skip (preserve)
    """
    if not conflicts:
        return True  # No conflicts — proceed normally

    if preserve:
        return False  # --preserve: skip all conflicts silently

    if force:
        return True  # --force: overwrite all conflicts silently

    # Interactive vs non-interactive
    is_interactive = sys.stdin.isatty()

    conflict_list = "\n".join(f"  • {p}" for p in conflicts)
    console.print(
        f"\n[yellow]Warning:[/yellow] {len(conflicts)} file(s) have local changes "
        f"that differ from the warehouse:\n{conflict_list}\n"
    )

    if not is_interactive:
        console.print(
            "[red]Error:[/red] Non-interactive mode — cannot prompt for overwrite.\n"
            "Use --force to overwrite or --preserve to skip conflicting files."
        )
        sys.exit(1)

    answer = click.confirm(
        "Overwrite these files with warehouse content?", default=False
    )
    return answer


@main.command()
@click.option("--preserve", is_flag=True, help="Skip files with local modifications")
@click.option(
    "--force", is_flag=True, help="Overwrite conflicting files without prompting"
)
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
    force: bool,
    verbose_flag: bool,
    dry_run: bool,
    skip_git_check: bool,
) -> None:
    """
    Sync artifacts from warehouse to project.

    Reads .agentic-beacon/beacon.yaml and copies specified artifacts
    from the connected warehouse to .agentic-beacon/artifacts/ directory.
    Artifacts that were previously synced but removed from beacon.yaml will
    be detected and you will be prompted before they are deleted.

    Example:
        abc sync              # Sync all artifacts
        abc sync --preserve   # Skip locally modified files
        abc sync --force      # Overwrite all conflicts without prompting
        abc sync --verbose    # Show detailed output
        abc sync --dry-run    # Preview without copying
    """
    if force and preserve:
        console.print(
            "[red]Error:[/red] --force and --preserve are mutually exclusive."
        )
        sys.exit(1)

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

        # Check warehouse is on main branch (skip if --dry-run or --skip-git-check)
        if not dry_run and not skip_git_check:
            branch_error = _check_warehouse_on_main_branch(warehouse_path)
            if branch_error:
                console.print(f"[red]Error:[/red] {branch_error}")
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
            # Still install bundled skills and sync agents even when no warehouse artifacts configured
            _print_bundled_install_result(*_install_bundled_skills_globally())
            _sync_agents_from_warehouse(warehouse_path, force=force, preserve=preserve)
            sys.exit(0)

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

        # Record sync state now — before the conflict check which may sys.exit(1).
        # Semantics: "I've verified the warehouse at this HEAD."  Even when sync exits
        # early (non-interactive conflict), the stale-snapshot warning in `abc contribute`
        # should clear because the user has checked the current warehouse commit.
        if not dry_run:
            _write_sync_state(artifacts_dir, warehouse_path)

        # Soft-block pre-check: detect conflicts before writing
        if not dry_run:
            conflicts = sync_engine.classify_conflicts(artifact_paths)
            overwrite = _handle_soft_block(conflicts, force=force, preserve=preserve)
            if not overwrite and conflicts:
                # User said N or --preserve: switch to preserve mode for the conflicting files
                preserve = True

        # Auto-prune: classify orphans and ask for confirmation
        orphans = sync_engine.classify_orphans(artifact_paths)
        confirmed_prune: list[str] = []
        if orphans:
            confirmed_prune = _confirm_prune(orphans, dry_run=dry_run)

        # Perform sync
        def log_fn(msg: str) -> None:
            console.print(f"  {msg}")

        summary = sync_engine.sync_all(
            artifact_paths=artifact_paths,
            preserve=preserve,
            paths_to_prune=confirmed_prune if not dry_run else None,
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
        if dry_run and orphans:
            console.print(
                f"  [yellow]Would remove:[/yellow] {len(orphans)} artifact(s) "
                f"no longer in beacon.yaml (confirmation required)"
            )
        elif summary.pruned > 0:
            console.print(
                f"  [yellow]Removed:[/yellow] "
                f"{summary.pruned} artifact(s) no longer in beacon.yaml"
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

        # Post-sync wiring: wire newly synced artifacts
        project_root = Path.cwd()
        wiring_notes: list[str] = []

        # Unwire pruned artifacts first
        if summary.pruned_paths:
            _unwire_pruned_artifacts(project_root, summary.pruned_paths, artifacts_dir)

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
                project_root, artifacts_dir, force=force, preserve=preserve
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

        # Install abc-bundled skills directly from data/skills/ (no beacon.yaml entry needed)
        _print_bundled_install_result(*_install_bundled_skills_globally())

        # Sync global agents from warehouse
        _sync_agents_from_warehouse(warehouse_path, force=force, preserve=preserve)

    except Exception as e:
        console.print(f"\n[red]Error:[/red] Sync failed: {e}")
        logger.exception("Sync failed")
        sys.exit(1)


def _sync_agents_from_warehouse(
    warehouse_path: Path,
    *,
    force: bool = False,
    preserve: bool = False,
) -> None:
    """Sync all agent definition files from the warehouse into global tool directories.

    Called as part of `abc sync`. Finds every *.md under warehouse/agents/,
    compares each against the global agent dirs for detected tools, and installs
    any that are out-of-date.  A single Y/N prompt is shown when conflicts exist
    (unless --force or --preserve are supplied).

    Args:
        warehouse_path: Absolute path to the connected warehouse root.
        force: Overwrite conflicting files without prompting.
        preserve: Skip conflicting files without prompting.
    """
    agents_dir = warehouse_path / "agents"
    if not agents_dir.is_dir():
        return

    agent_files = sorted(agents_dir.rglob("*.md"))
    if not agent_files:
        return

    tools = _detect_agents_global()
    if not tools:
        return

    agent_dirs = _global_agent_dirs()

    # Build list of (relative_path, content, agent_name) tuples
    entries: list[tuple[str, str, str]] = []
    for af in agent_files:
        rel = str(af.relative_to(warehouse_path))  # e.g. "agents/code-reviewer.md"
        content = af.read_text(encoding="utf-8")
        agent_name = af.name
        entries.append((rel, content, agent_name))

    # Detect conflicts: files that exist in global dirs but differ from warehouse
    conflicts: list[str] = []
    for _rel, content, agent_name in entries:
        for tool in tools:
            dest = agent_dirs[tool] / agent_name
            if dest.exists() and dest.read_text(encoding="utf-8") != content:
                conflicts.append(str(dest))

    # Single Y/N prompt for all conflicts together
    effective_preserve = preserve
    if conflicts and not force and not preserve:
        conflict_list = "\n".join(f"  • {p}" for p in conflicts)
        console.print(
            f"\n[yellow]Warning:[/yellow] {len(conflicts)} global agent file(s) "
            f"differ from the warehouse and will be overwritten:\n{conflict_list}\n"
        )
        is_interactive = sys.stdin.isatty()
        if is_interactive:
            if not click.confirm(
                "Overwrite local agent files with warehouse versions?", default=False
            ):
                effective_preserve = True
        else:
            console.print(
                "[dim]Non-interactive mode — skipping agent overwrite. "
                "Use --force to overwrite or --preserve to suppress this warning.[/dim]"
            )
            effective_preserve = True

    # Install
    installed: list[str] = []
    skipped: list[str] = []
    for rel, content, agent_name in entries:
        for tool in tools:
            dest = agent_dirs[tool] / agent_name
            is_conflict = str(dest) in conflicts

            if effective_preserve and is_conflict:
                skipped.append(agent_name)
                continue

            written = _install_agent_global(tool, agent_name, content)
            if written:
                installed.append(agent_name)
                _write_agent_sync_state(warehouse_path, rel, _hash_content(content))

    if installed:
        unique = sorted(set(installed))
        console.print(
            f"\n[green]✓[/green] Synced {len(unique)} global agent(s) from warehouse "
            f"({', '.join(unique)})"
        )
    if skipped:
        unique_skipped = sorted(set(skipped))
        console.print(
            f"  [yellow]Skipped {len(unique_skipped)} agent(s) with local changes "
            f"(use --force to overwrite): {', '.join(unique_skipped)}[/yellow]"
        )


def _handle_install_agent(
    artifact: str, *, force: bool = False, preserve: bool = False
) -> None:
    """Handle 'abc install agents/<name>.md' — global install for all detected tools.

    Loads warehouse settings, reads the agent file, performs soft-block conflict
    detection against global agent dirs, writes to each detected tool dir, and
    records sync-state for each successful write. Does NOT update beacon.yaml.
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

    agent_file = warehouse_path / artifact
    if not agent_file.exists():
        console.print(f"[red]Error:[/red] Agent not found in warehouse: {artifact}")
        sys.exit(1)

    content = agent_file.read_text(encoding="utf-8")
    agent_name = Path(artifact).name

    # Relink sync state if warehouse path has changed
    _relink_global_sync_state(warehouse_path)

    # Detect tools
    tools = _detect_agents_global()
    if not tools:
        console.print(
            "[yellow]Warning:[/yellow] No agent tools detected "
            "(neither ~/.config/opencode/ nor ~/.claude/ found)."
        )
        console.print("Install OpenCode or Claude Code and re-run to install agent.")
        return

    # Soft-block pre-check: check for conflicting global agent files
    agent_dirs = _global_agent_dirs()
    conflicts: list[str] = []
    for tool in tools:
        dest = agent_dirs[tool] / agent_name
        if dest.exists() and dest.read_text(encoding="utf-8") != content:
            conflicts.append(str(dest))

    overwrite = _handle_soft_block(conflicts, force=force, preserve=preserve)
    if not overwrite and conflicts:
        preserve = True  # skip conflicting files

    written_any = False
    for tool in tools:
        dest = agent_dirs[tool] / agent_name
        is_conflict = str(dest) in conflicts

        if preserve and is_conflict:
            console.print(f"[yellow]Skipped[/yellow] {dest} (preserved local version)")
            continue

        written = _install_agent_global(tool, agent_name, content)
        if written:
            console.print(f"[green]Installed[/green] {artifact} → {dest}")
            _write_agent_sync_state(warehouse_path, artifact, _hash_content(content))
            written_any = True
        else:
            console.print(f"[dim]Up to date[/dim] {dest}")

    if not written_any and not conflicts:
        console.print(
            f"[dim]{artifact} is already up to date in all tool directories.[/dim]"
        )


def _hash_content(content: str) -> str:
    """Return SHA-256 hex digest of UTF-8 encoded content string."""
    import hashlib

    return hashlib.sha256(content.encode("utf-8")).hexdigest()


@main.group()
def agents() -> None:
    """Agent definition commands (sync)."""
    pass


@agents.command(name="sync")
@click.option("--preserve", is_flag=True, help="Skip files with local modifications")
@click.option(
    "--force", is_flag=True, help="Overwrite conflicting files without prompting"
)
@click.option(
    "--skip-git-check",
    is_flag=True,
    help="Skip warehouse uncommitted-changes check",
)
def agents_sync(*, preserve: bool, force: bool, skip_git_check: bool) -> None:
    """Sync all agent definitions from warehouse into global tool directories.

    Reads the connected warehouse, finds every agent definition under agents/,
    and installs them into the global directories for all detected tools
    (~/.config/opencode/agents/ and/or ~/.claude/agents/).

    A confirmation prompt is shown when local agent files differ from the
    warehouse version. Use --force to overwrite without prompting, or
    --preserve to skip conflicts silently.

    Example:
        abc agents sync            # Sync all agents, prompt on conflicts
        abc agents sync --force    # Overwrite all conflicts without prompting
        abc agents sync --preserve # Skip conflicting agents
    """
    if force and preserve:
        console.print(
            "[red]Error:[/red] --force and --preserve are mutually exclusive."
        )
        sys.exit(1)

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

    if not skip_git_check:
        _check_warehouse_git_clean(warehouse_path)
        _check_warehouse_on_main_branch(warehouse_path)

    _sync_agents_from_warehouse(warehouse_path, force=force, preserve=preserve)


@main.command(name="install")
@click.argument("artifact", metavar="ARTIFACT")
@click.option(
    "--agent",
    type=click.Choice(["opencode", "claudecode"], case_sensitive=False),
    help="Target agent tool (auto-detected if not specified)",
)
@click.option("--preserve", is_flag=True, help="Skip files with local modifications")
@click.option(
    "--force", is_flag=True, help="Overwrite conflicting files without prompting"
)
def install_artifact(
    *, artifact: str, agent: str | None, preserve: bool, force: bool
) -> None:
    """Pull and wire a single artifact from the warehouse.

    ARTIFACT is a path relative to the warehouse root. Type is inferred
    from the leading path component.

    Example:
        abc install skills/code-reviewer
        abc install contexts/python
        abc install knowledge/decisions/coding-standards.md
        abc install agents/code-reviewer.md
    """
    if force and preserve:
        console.print(
            "[red]Error:[/red] --force and --preserve are mutually exclusive."
        )
        sys.exit(1)

    # Special case: agents are globally installed
    artifact_path = Path(artifact.rstrip("/"))
    if artifact_path.parts and artifact_path.parts[0] == "agents":
        _handle_install_agent(artifact.rstrip("/"), force=force, preserve=preserve)
        return

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

    # Soft-block pre-check: detect conflicts before writing
    conflicts = engine.classify_conflicts(files_to_copy)
    overwrite = _handle_soft_block(conflicts, force=force, preserve=preserve)
    if not overwrite and conflicts:
        preserve = True  # Switch to preserve mode for conflicting files

    # Copy files from warehouse to artifacts
    copy_errors: list[str] = []
    copied = 0
    for path in files_to_copy:
        result = engine.copy_file(path, preserve=preserve)
        if result.success:
            if result.action == "copied":
                copied += 1
        else:
            copy_errors.append(f"{path}: {result.error_message}")

    if copy_errors:
        for err in copy_errors:
            console.print(f"[red]✗[/red] {err}")
        sys.exit(1)

    # Update beacon.yaml only when at least one file was successfully written
    if copied > 0:
        _update_beacon_yaml(beacon_dir, files_to_copy)

    # Infer type and wire
    artifact_type = Path(artifact).parts[0] if Path(artifact).parts else ""
    project_root = Path.cwd()
    agents = (
        _detect_agents(project_root, fallback_to_all=True)
        if not agent
        else [agent.lower()]
    )

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


def _enrich_agent_stale(
    result: ComparisonResult,
    *,
    warehouse_path: Path,
    current_head: str,
) -> ComparisonResult:
    """Enrich an IDENTICAL agent ComparisonResult to STALE if the sync-state HEAD differs.

    Only applies to IDENTICAL results — MODIFIED/MISSING are returned unchanged.
    If no sync-state entry exists, the result is returned unchanged (no enrichment).

    Args:
        result: ComparisonResult to potentially enrich.
        warehouse_path: Path to the warehouse (used as sync-state key).
        current_head: Current warehouse HEAD SHA.
    """
    if result.status != DeltaStatus.IDENTICAL:
        return result

    state = _read_global_sync_state()
    warehouses = state.get("warehouses", {})
    wh_entries = warehouses.get(str(warehouse_path), {})
    entry = wh_entries.get(result.path)

    if entry is None:
        return result  # No sync-state entry — can't determine STALE

    recorded_head = entry.get("warehouse_head", "")
    if recorded_head and recorded_head != current_head:
        # Warehouse has advanced since last install — mark as STALE
        stale_statuses = {agent: DeltaStatus.STALE for agent in result.agent_statuses}
        return ComparisonResult(
            path=result.path,
            status=DeltaStatus.STALE,
            local_hash=result.local_hash,
            warehouse_hash=result.warehouse_hash,
            agent_statuses=stale_statuses,
        )

    return result


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


def _bundled_skill_names() -> set[str]:
    """Return the set of skill names that are managed by abc (bundled)."""
    bundled_dir = Path(__file__).parent / "data" / "skills"
    if not bundled_dir.exists():
        return set()
    return {
        d.name
        for d in bundled_dir.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    }


def _find_global_untracked_skills() -> dict[str, list[str]]:
    """Return non-bundled skill directories found in the global skill dirs.

    Scans ~/.claude/skills/ (Claude Code) and ~/.config/opencode/skills/ (OpenCode).
    Excludes abc-bundled skills so only accidentally-global user skills are surfaced.
    Returns a mapping of tool name → sorted list of skill names.
    """
    global_skill_dirs: dict[str, Path] = {
        "claudecode": Path.home() / ".claude" / "skills",
        "opencode": Path.home() / ".config" / "opencode" / "skills",
    }
    bundled = _bundled_skill_names()
    result: dict[str, list[str]] = {}
    for tool, skills_dir in global_skill_dirs.items():
        if skills_dir.is_dir():
            names = sorted(
                d.name
                for d in skills_dir.iterdir()
                if d.is_dir() and (d / "SKILL.md").exists() and d.name not in bundled
            )
            if names:
                result[tool] = names
    return result


def _find_project_level_agents(project_root: Path) -> dict[str, list[str]]:
    """Return project-scoped agent files per tool that live outside the global dirs.

    Checks .claude/agents/ (Claude Code) and .opencode/agents/ (OpenCode) under
    the given project root.  Returns a mapping of tool name → sorted list of
    agent file names (README.md excluded).
    """
    project_agent_dirs: dict[str, Path] = {
        "claudecode": project_root / ".claude" / "agents",
        "opencode": project_root / ".opencode" / "agents",
    }
    result: dict[str, list[str]] = {}
    for tool, agents_dir in project_agent_dirs.items():
        if agents_dir.is_dir():
            files = sorted(
                f.name
                for f in agents_dir.iterdir()
                if f.is_file() and f.name != "README.md"
            )
            if files:
                result[tool] = files
    return result


def _build_agents_paths() -> dict[str, Path]:
    """Return a mapping of tool name → global agents directory for detected tools.

    This is the shared detection logic used by both `abc delta` and
    `abc contribute` so both commands always compare/read from the same
    global agent locations.
    """
    agents_paths: dict[str, Path] = {}
    for tool in _detect_agents_global():
        if tool == "opencode":
            agents_paths["opencode"] = Path.home() / ".config" / "opencode" / "agents"
        elif tool == "claudecode":
            agents_paths["claudecode"] = Path.home() / ".claude" / "agents"
    return agents_paths


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

        # Relink sync-state if warehouse path has changed
        _relink_global_sync_state(warehouse_path)

        # Build skills_paths via shared helper — same logic used by contribute.
        project_root = Path.cwd()

        comparator = DeltaComparator(
            warehouse_path=warehouse_path,
            artifacts_path=artifacts_dir,
            skills_paths=_build_skills_paths(project_root),
            agents_paths=_build_agents_paths(),
        )

        if file:
            # Detailed diff for specific file
            _show_detailed_diff(comparator, beacon_settings, file, no_color)
        else:
            # Summary view
            _show_delta_summary(
                comparator, beacon_settings, warehouse_path, project_root
            )

    except Exception as e:
        console.print(f"\n[red]Error:[/red] Delta comparison failed: {e}")
        logger.exception("Delta comparison failed")
        sys.exit(1)


def _show_delta_summary(
    comparator: DeltaComparator,
    beacon_settings: BeaconSettings,
    warehouse_path: Path | None = None,
    project_root: Path | None = None,
) -> None:
    """Show summary of all artifact differences."""
    summary = comparator.compare_from_config(beacon_settings)

    # Gather agent comparison results — discover from global agent dirs + warehouse
    # so agents that exist globally but not yet in the warehouse show as ADDED.
    agent_results = []
    if comparator.agents_paths and warehouse_path is not None:
        current_head = _get_warehouse_head_sha(warehouse_path) or ""

        # Collect all unique agent file names across all global tool dirs and warehouse
        seen_rel_paths: set[str] = set()

        # First: files in global dirs (source of truth for new agents)
        for _tool, agents_dir in comparator.agents_paths.items():
            if agents_dir.is_dir():
                for agent_file in sorted(agents_dir.rglob("*")):
                    if agent_file.is_file() and agent_file.name != "README.md":
                        # Reconstruct warehouse-relative path: agents/<filename>
                        rel_path = "agents/" + agent_file.name
                        seen_rel_paths.add(rel_path)

        # Second: files in warehouse/agents/ that may not be in any global dir (MISSING)
        warehouse_agents_dir = warehouse_path / "agents"
        if warehouse_agents_dir.is_dir():
            for agent_file in sorted(warehouse_agents_dir.rglob("*")):
                if agent_file.is_file() and agent_file.name != "README.md":
                    rel_path = str(agent_file.relative_to(warehouse_path))
                    seen_rel_paths.add(rel_path)

        for rel_path in sorted(seen_rel_paths):
            result = comparator._compare_agent_file(rel_path)
            result = _enrich_agent_stale(
                result, warehouse_path=warehouse_path, current_head=current_head
            )
            agent_results.append(result)

    untracked = _find_untracked_local_files(
        comparator, beacon_settings, comparator.artifacts_path
    )

    # Detect project-scoped agents (not part of the global/contribution flow)
    project_level_agents: dict[str, list[str]] = (
        _find_project_level_agents(project_root) if project_root is not None else {}
    )

    # Detect non-bundled skills accidentally placed in global skill dirs
    global_untracked_skills = _find_global_untracked_skills()

    has_agent_diffs = any(r.status != DeltaStatus.IDENTICAL for r in agent_results)

    if (
        not summary.has_differences
        and not untracked
        and not has_agent_diffs
        and not project_level_agents
        and not global_untracked_skills
    ):
        console.print(
            "[green]No differences found. Local artifacts match local warehouse.[/green]"
        )
        return

    tracked_diffs = [r for r in summary.results if r.status != DeltaStatus.IDENTICAL]

    _STATUS_MARKUP: dict[DeltaStatus, str] = {
        DeltaStatus.MODIFIED: "[yellow]modified[/yellow]",
        DeltaStatus.ADDED: "[green]added[/green]",
        DeltaStatus.MISSING: "[red]missing[/red]",
        DeltaStatus.STALE: "[dim cyan]stale[/dim cyan]",
    }
    _AGENT_STATUS_MARKUP: dict[DeltaStatus, str] = {
        DeltaStatus.MODIFIED: "[yellow]modified[/yellow]",
        DeltaStatus.ADDED: "[green]added[/green]",
        DeltaStatus.MISSING: "[red]missing[/red]",
        DeltaStatus.IDENTICAL: "[dim]identical[/dim]",
        DeltaStatus.STALE: "[dim cyan]stale[/dim cyan]",
    }

    # --- Tracked Artifacts section ---
    if tracked_diffs:
        # Collect all agent names present across skill rows to build columns
        tracked_agents: list[str] = []
        for result in tracked_diffs:
            if result.is_skill and result.agent_statuses:
                for a in result.agent_statuses:
                    if a not in tracked_agents:
                        tracked_agents.append(a)

        rows: list[tuple[str, str, dict[str, str]]] = []
        for result in tracked_diffs:
            status_markup = _STATUS_MARKUP.get(result.status, result.status.value)
            agent_cells: dict[str, str] = {}
            if result.is_skill and result.agent_statuses:
                for a, s in result.agent_statuses.items():
                    agent_cells[a] = _AGENT_STATUS_MARKUP.get(s, s.value)
            rows.append((status_markup, result.path, agent_cells))

        console.print()
        console.print(_render_delta_table(rows, "Tracked Artifacts", tracked_agents))

    # Classify agents for summary counts (always, even if no section rendered)
    stale_agents: list[str] = []
    added_agents: list[str] = []
    modified_agents: list[str] = []
    for result in agent_results:
        if result.status == DeltaStatus.STALE:
            stale_agents.append(result.path)
        elif result.status == DeltaStatus.ADDED:
            added_agents.append(result.path)
        elif result.status == DeltaStatus.MODIFIED:
            modified_agents.append(result.path)

    # --- Untracked Artifacts section ---
    if untracked:
        if tracked_diffs:
            console.rule(style="dim")

        # Collect all agent names present across untracked skill rows
        untracked_agents: list[str] = []
        for _rel_path, agents in untracked:
            for a in agents:
                if a not in untracked_agents:
                    untracked_agents.append(a)

        rows = []
        for rel_path, agents in untracked:
            agent_cells = {a: "[green]added[/green]" for a in agents}
            rows.append(("[green]added[/green]", rel_path, agent_cells))

        console.print()
        console.print(
            _render_delta_table(
                rows,
                "Untracked Artifacts [dim](not in beacon.yaml)[/dim]",
                untracked_agents,
            )
        )

    # --- Agents section ---
    if agent_results:
        if tracked_diffs or untracked:
            console.rule(style="dim")

        # Collect all tool names present across agent rows
        agent_tools: list[str] = []
        for result in agent_results:
            if result.agent_statuses:
                for t in result.agent_statuses:
                    if t not in agent_tools:
                        agent_tools.append(t)

        rows = []
        for result in agent_results:
            status_markup: str = (
                _STATUS_MARKUP.get(result.status) or result.status.value
            )
            agent_cells: dict[str, str] = {}
            if result.agent_statuses:
                for t, s in result.agent_statuses.items():
                    agent_cells[t] = _AGENT_STATUS_MARKUP.get(s) or s.value
            rows.append((status_markup, result.path, agent_cells))

        console.print()
        console.print(
            _render_delta_table(
                rows,
                "Agents [dim](global)[/dim]",
                agent_tools,
            )
        )

    # --- Project-scoped agents reminder ---
    if project_level_agents:
        if agent_results or tracked_diffs or untracked:
            console.rule(style="dim")

        # Collect all unique agent filenames and tools in a stable order
        proj_tools: list[str] = sorted(project_level_agents.keys())
        proj_files: list[str] = sorted(
            {f for files in project_level_agents.values() for f in files}
        )

        table = Table(
            title="Project-scoped Agents [dim](promote to global to include in contribution flow)[/dim]",
            title_style="bold yellow",
            title_justify="left",
            show_header=True,
            header_style="dim",
            box=None,
            padding=(0, 2, 0, 0),
        )
        table.add_column("Agent file")
        for tool in proj_tools:
            table.add_column(tool, no_wrap=True)

        for fname in proj_files:
            cells = [
                "[yellow]project[/yellow]"
                if fname in project_level_agents.get(tool, [])
                else ""
                for tool in proj_tools
            ]
            table.add_row(fname, *cells)

        console.print()
        console.print(table)

    # --- Global untracked skills reminder ---
    if global_untracked_skills:
        if project_level_agents or agent_results or tracked_diffs or untracked:
            console.rule(style="dim")

        global_skill_tools: list[str] = sorted(global_untracked_skills.keys())
        global_skill_names: list[str] = sorted(
            {s for names in global_untracked_skills.values() for s in names}
        )

        table = Table(
            title="Global Skills [dim](not in project skill dirs — not tracked in warehouse)[/dim]",
            title_style="bold yellow",
            title_justify="left",
            show_header=True,
            header_style="dim",
            box=None,
            padding=(0, 2, 0, 0),
        )
        table.add_column("Skill")
        for tool in global_skill_tools:
            table.add_column(tool, no_wrap=True)

        for skill_name in global_skill_names:
            cells = [
                "[yellow]global[/yellow]"
                if skill_name in global_untracked_skills.get(tool, [])
                else ""
                for tool in global_skill_tools
            ]
            table.add_row(skill_name, *cells)

        console.print()
        console.print(table)

    # Summary counts
    console.print("\n[bold]Summary:[/bold]")
    if summary.modified:
        console.print(f"  [yellow]Modified:[/yellow] {len(summary.modified)} files")
    if summary.added:
        console.print(f"  [green]Added:[/green] {len(summary.added)} files")
    if untracked:
        console.print(f"  [green]Untracked:[/green] {len(untracked)} files")
    if summary.missing:
        console.print(f"  [red]Missing:[/red] {len(summary.missing)} files")
    if summary.identical:
        console.print(f"  [dim]Identical:[/dim] {len(summary.identical)} files")
    if added_agents:
        console.print(
            f"  [green]New agent(s):[/green] {len(added_agents)} (not yet in warehouse)"
        )
    if modified_agents:
        console.print(f"  [yellow]Modified agent(s):[/yellow] {len(modified_agents)}")
    if stale_agents:
        console.print(f"  [dim cyan]Stale:[/dim cyan] {len(stale_agents)} agent(s)")
    if project_level_agents:
        total = sum(len(v) for v in project_level_agents.values())
        console.print(
            f"  [yellow]Project-scoped agent(s):[/yellow] {total} (not in global dirs)"
        )
    if global_untracked_skills:
        total = sum(len(v) for v in global_untracked_skills.values())
        console.print(
            f"  [yellow]Global skill(s):[/yellow] {total} (in global dir, not tracked)"
        )

    # Tips
    if summary.missing:
        console.print(
            "\n[dim]Tip: Run 'abc sync' to download missing artifacts from warehouse.[/dim]"
        )
    if summary.modified:
        console.print(
            "[dim]Tip: Run 'abc delta <file>' to see detailed diff for a modified file.[/dim]"
        )
    if untracked and (added_agents or modified_agents):
        console.print(
            "[dim]Tip: Run 'abc contribute' to push untracked artifacts and agent changes to the warehouse.[/dim]"
        )
    elif untracked:
        console.print(
            "[dim]Tip: Run 'abc contribute' to push untracked local artifacts to the warehouse.[/dim]"
        )
    elif added_agents or modified_agents:
        console.print(
            "[dim]Tip: Run 'abc contribute' to push agent changes to the warehouse.[/dim]"
        )
    if stale_agents:
        console.print(
            "[dim]Tip: Run 'abc install agents/<name>' to update stale agent definitions.[/dim]"
        )
    if project_level_agents:
        console.print(
            "[dim]Tip: To promote a project-scoped agent, move it to the global agents dir "
            "and run 'abc contribute' — or ask your coding agent to do it for you.[/dim]"
        )
    if global_untracked_skills:
        console.print(
            "[dim]Tip: Global skills are not tracked in the warehouse. Move them to the "
            "project skill dir (.claude/skills/ or .opencode/skills/) and run "
            "'abc contribute' — or ask your coding agent to do it for you.[/dim]"
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


def _render_delta_table(
    rows: list[tuple[str, str, dict[str, str]]],
    title: str,
    agents: list[str],
) -> Table:
    """Render a delta section as a Rich table.

    Each row is a (status_markup, artifact_path, agent_cells) tuple where
    agent_cells maps agent name → markup string (empty string if not applicable).
    Agent columns are only added when at least one skill row is present (agents != []).
    """
    table = Table(
        title=title,
        title_style="bold",
        title_justify="left",
        show_header=True,
        header_style="dim",
        box=None,
        padding=(0, 2, 0, 0),
    )
    table.add_column("Status", no_wrap=True)
    table.add_column("Artifact")
    for agent in agents:
        table.add_column(agent, no_wrap=True)

    for status_markup, path, agent_cells in rows:
        agent_values = [agent_cells.get(a, "") for a in agents]
        table.add_row(status_markup, path, *agent_values)

    return table


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
) -> list[tuple[str, list[str]]]:
    """Return local artifact files that are not covered by any beacon.yaml pattern.

    Returns a list of (relative_path, agents) tuples. For skills found in live
    agent directories, agents lists which agents have the skill (e.g. ["opencode",
    "claudecode"]). For knowledge/context files from artifacts_dir, agents is [].

    NOTE: .agentic-beacon/artifacts/skills/ is intentionally excluded from the
    artifacts_dir scan. That directory is a one-way intermediary used only during
    'abc sync' to stage skill files before wiring them to live agent directories
    (.opencode/skills/, .claude/skills/). It is never a source of truth for delta —
    skills are always compared against their live agent installation, not the snapshot.
    """
    tracked = _collect_artifact_paths(comparator, beacon_settings)

    # Scan artifacts_dir for untracked knowledge and context files.
    # Explicitly skip the skills/ subdirectory — it is a one-way sync staging area
    # and must not be treated as a canonical source for delta comparisons.
    artifacts_untracked: list[str] = []
    if artifacts_dir.exists():
        for file_path in sorted(artifacts_dir.rglob("*")):
            if file_path.is_file() and file_path.name != _SYNC_STATE_FILENAME:
                rel = str(file_path.relative_to(artifacts_dir))
                if rel.startswith("skills/"):
                    continue  # skills live in agent dirs, not here
                if rel not in tracked:
                    artifacts_untracked.append(rel)

    # Scan live agent skill directories — the canonical location for installed skills.
    # Group by rel_path so a skill present in multiple agent dirs is reported once
    # with all agents listed.
    skill_agents: dict[str, list[str]] = {}
    for agent, skills_root in comparator.skills_paths.items():
        if skills_root.exists():
            for file_path in sorted(skills_root.rglob("*")):
                if file_path.is_file():
                    rel = str(Path("skills") / file_path.relative_to(skills_root))
                    if rel not in tracked:
                        skill_agents.setdefault(rel, []).append(agent)

    result: list[tuple[str, list[str]]] = []
    for rel in artifacts_untracked:
        result.append((rel, []))
    for rel in sorted(skill_agents):
        result.append((rel, skill_agents[rel]))

    return result


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
@click.option(
    "--exclude-unregistered",
    is_flag=True,
    help="Only contribute artifacts already tracked in beacon.yaml; skip untracked local artifacts",
)
def contribute(
    *,
    file: str | None,
    dry_run: bool,
    skip_git_check: bool,
    manual_git: bool,
    exclude_unregistered: bool,
) -> None:
    """Copy local artifact changes back to the warehouse for sharing.

    After editing synced artifacts and verifying they work with your agent,
    use this command to copy them back to the warehouse so the whole team
    benefits from the improvements.

    Untracked local artifacts (not in beacon.yaml) are included by default.
    Use --exclude-unregistered to contribute only tracked artifacts.

    Without a FILE argument, all modified and added artifacts are contributed.

    Examples:

        abc contribute                                  # All modified/added (incl. untracked)

        abc contribute knowledge/python/type-hints.md   # Single file

        abc contribute --dry-run                        # Preview only

        abc contribute --manual-git                     # Skip auto PR creation

        abc contribute --exclude-unregistered           # Only tracked artifacts
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

        # Check that abc sync has been run and the snapshot is current with
        # the warehouse HEAD (skip if --dry-run or --skip-git-check)
        if not dry_run and not skip_git_check:
            sync_error = _check_sync_state(artifacts_dir, warehouse_path)
            if sync_error:
                console.print(f"[yellow]Warning:[/yellow] {sync_error}")
                sys.exit(1)

        beacon_settings = BeaconSettings.from_yaml(beacon_yaml)
        project_root = Path.cwd()
        comparator = DeltaComparator(
            warehouse_path=warehouse_path,
            artifacts_path=artifacts_dir,
            skills_paths=_build_skills_paths(project_root),
            agents_paths=_build_agents_paths(),
        )

        if dry_run:
            console.print("[dim]Dry run — no files will be copied.[/dim]\n")

        if file:
            if not dry_run:
                # Preview what will be contributed, then confirm
                console.print("[dim]Preview:[/dim]\n")
                preview = _contribute_single(
                    comparator,
                    beacon_settings,
                    warehouse_path,
                    artifacts_dir,
                    file,
                    dry_run=True,
                    project_root=project_root,
                )
                if preview and not click.confirm(
                    "\nProceed with contribute?", default=True
                ):
                    console.print("[dim]Aborted.[/dim]")
                    return
            contributed = _contribute_single(
                comparator,
                beacon_settings,
                warehouse_path,
                artifacts_dir,
                file,
                dry_run,
                project_root=project_root,
            )
        else:
            if not dry_run:
                # Preview what will be contributed, then confirm
                console.print("[dim]Preview:[/dim]\n")
                preview = _contribute_all(
                    comparator,
                    beacon_settings,
                    warehouse_path,
                    artifacts_dir,
                    dry_run=True,
                    project_root=project_root,
                    include_unregistered=not exclude_unregistered,
                )
                if preview and not click.confirm(
                    "\nProceed with contribute?", default=True
                ):
                    console.print("[dim]Aborted.[/dim]")
                    return
            contributed = _contribute_all(
                comparator,
                beacon_settings,
                warehouse_path,
                artifacts_dir,
                dry_run,
                project_root=project_root,
                include_unregistered=not exclude_unregistered,
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
    dry_run: bool = False,
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

    # Genuinely different versions across agents.
    # During a dry-run preview, skip the interactive prompt and just report the conflict.
    if dry_run:
        console.print(
            f"\n[yellow]Conflict:[/yellow] '{relative_path}' has been modified differently "
            "across agents — you will be prompted to choose when you confirm.\n"
        )
        return next(iter(candidates.values()))  # placeholder; not used in dry-run

    # Prompt the user to choose
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


def _propagate_skill_to_agents(
    project_root: Path, relative_path: str, source_path: Path
) -> None:
    """After contributing a skill to the warehouse, propagate the contributed
    content to all configured agents' live copies.

    This prevents the infinite delta cycle where contributing one agent's
    modified version leaves other agents' stale copies flagged as MODIFIED.
    After this call all live copies converge to the contributed content.

    ``relative_path`` is the skill-relative warehouse path, e.g.
    ``skills/foo/SKILL.md``.  ``source_path`` is the absolute path of the
    file that was just written to the warehouse.
    """
    content = source_path.read_text(encoding="utf-8")
    # Extract skill name from "skills/<name>/SKILL.md"
    parts = Path(relative_path).parts
    if len(parts) < 2:
        return
    skill_name = parts[1]

    description = _extract_skill_description(content)
    agents = _detect_agents(project_root)
    for agent in agents:
        try:
            if agent == "opencode":
                _install_skill_opencode(project_root, skill_name, content, description)
            else:
                _install_skill_claudecode(project_root, skill_name, content)
        except Exception as e:
            console.print(
                f"  [yellow]Warning:[/yellow] could not propagate '{skill_name}' to {agent}: {e}"
            )


def _resolve_agent_contribute_source(
    comparator: DeltaComparator,
    relative_path: str,
    dry_run: bool = False,
) -> Path | None:
    """Resolve which global agent file to read when contributing back to the warehouse.

    Agent files live in global directories (~/.config/opencode/agents/ or
    ~/.claude/agents/). The logic mirrors _resolve_skill_contribute_source:

    - No agents configured → return None (nothing to contribute).
    - One tool has a modified copy → use it.
    - Multiple tools modified with identical content → use any.
    - Multiple tools modified with different content → prompt user to choose.
    - No tool has a modified copy → return None (identical to warehouse).

    Returns the absolute Path of the file to copy, or None if nothing to contribute.
    """
    if not comparator.agents_paths:
        return None

    result = comparator._compare_agent_file(relative_path)

    modified_tools = [
        tool
        for tool, status in result.agent_statuses.items()
        if status == DeltaStatus.MODIFIED
    ]

    if not modified_tools:
        return None

    candidates: dict[str, Path] = {}
    for tool in modified_tools:
        live_path = comparator._agent_live_path(tool, relative_path)
        if live_path.exists():
            candidates[tool] = live_path

    if not candidates:
        return None

    if len(candidates) == 1:
        return next(iter(candidates.values()))

    # Multiple tools have modified copies — check if they are identical
    hashes = {tool: comparator.compute_hash(path) for tool, path in candidates.items()}
    if len(set(hashes.values())) == 1:
        return next(iter(candidates.values()))

    # Genuinely different — prompt or report
    if dry_run:
        console.print(
            f"\n[yellow]Conflict:[/yellow] '{relative_path}' has been modified differently "
            "across tools — you will be prompted to choose when you confirm.\n"
        )
        return next(iter(candidates.values()))  # placeholder; not used in dry-run

    console.print(
        f"\n[yellow]Conflict:[/yellow] '{relative_path}' has been modified differently across tools:\n"
    )
    tool_list = list(candidates.keys())
    for i, tool in enumerate(tool_list, 1):
        console.print(f"  [{i}] {tool}")
        console.print(f"      [dim]{candidates[tool]}[/dim]")
    console.print()
    valid = [str(i) for i in range(1, len(tool_list) + 1)]
    while True:
        raw = click.prompt(
            f"Which version to contribute to the warehouse? ({'/'.join(valid)})",
            default="",
            show_default=False,
        ).strip()
        if raw in valid:
            break
        console.print(f"  [red]Invalid choice.[/red] Enter {' or '.join(valid)}.")

    chosen = tool_list[int(raw) - 1]
    console.print(f"  Using [bold]{chosen}[/bold] version.\n")
    return candidates[chosen]


def _contribute_single(
    comparator: DeltaComparator,
    beacon_settings: BeaconSettings,
    warehouse_path: Path,
    artifacts_dir: Path,
    file_path: str,
    dry_run: bool,
    project_root: Path,
) -> list[tuple[str, str]]:
    """Contribute a single artifact back to the warehouse.

    For skills: reads from the live agent directory rather than the artifact
    snapshot, matching the same source that abc delta inspects.
    For agents: reads from the global agent directory (~/.config/opencode/agents/
    or ~/.claude/agents/).

    Does NOT auto-register untracked files in beacon.yaml — use ``abc adopt``
    for discovery and opt-in.

    Returns a list of (path, status_label) tuples for contributed files.
    """
    is_skill = file_path.startswith("skills/") and bool(comparator.skills_paths)
    is_agent = file_path.startswith("agents/") and bool(comparator.agents_paths)

    if is_skill:
        # Resolve the live agent source (may prompt user if multiple agents conflict)
        local_path = _resolve_skill_contribute_source(
            comparator, file_path, artifacts_dir, dry_run=dry_run
        )
        if local_path is None:
            console.print(
                f"[yellow]Nothing to contribute.[/yellow] "
                f"'{file_path}' is identical to the warehouse version across all agents."
            )
            return []
    elif is_agent:
        local_path = _resolve_agent_contribute_source(
            comparator, file_path, dry_run=dry_run
        )
        if local_path is None:
            console.print(
                f"[yellow]Nothing to contribute.[/yellow] "
                f"'{file_path}' is identical to the warehouse version across all tools."
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

    if not is_skill and not is_agent:
        result = comparator.compare_file(file_path)
        if result.status == DeltaStatus.IDENTICAL:
            console.print(
                f"[yellow]Nothing to contribute.[/yellow] "
                f"'{file_path}' is identical to the warehouse version."
            )
            return []

    dest_existed = (warehouse_path / file_path).exists()
    _copy_to_warehouse(local_path, warehouse_path / file_path, file_path, dry_run)
    if is_skill and not dry_run:
        _propagate_skill_to_agents(project_root, file_path, local_path)
    status_label = "modified" if dest_existed else "added"
    return [(file_path, status_label)]


def _contribute_all(
    comparator: DeltaComparator,
    beacon_settings: BeaconSettings,
    warehouse_path: Path,
    artifacts_dir: Path,
    dry_run: bool,
    project_root: Path,
    include_unregistered: bool = False,
) -> list[tuple[str, str]]:
    """Contribute all tracked modified/added artifacts and modified agents to the warehouse.

    Covers three sources:
    1. Tracked artifacts (knowledge/skills/contexts) declared in beacon.yaml that
       have local modifications or additions.
    2. Unregistered local files not in beacon.yaml (when include_unregistered=True).
    3. Agent definition files (~/.config/opencode/agents/, ~/.claude/agents/) that
       differ from the warehouse — these are always included regardless of beacon.yaml.

    For skills: reads from live agent directories. If multiple agents have
    conflicting modifications the user is prompted to choose per-skill.
    For agents: reads from the global agent directory. If multiple tools have
    conflicting modifications the user is prompted to choose.

    Returns a list of (path, status_label) tuples for contributed files.
    """
    summary = comparator.compare_from_config(beacon_settings)
    contributable = summary.modified + summary.added

    unregistered_paths: list[str] = []
    if include_unregistered:
        unregistered_paths = [
            p
            for p, _agents in _find_untracked_local_files(
                comparator, beacon_settings, artifacts_dir
            )
        ]

    # Collect modified/added agent paths (no beacon.yaml entry needed)
    # Discover from global dirs so agents not yet in warehouse appear as ADDED.
    agent_paths: list[str] = []
    if comparator.agents_paths:
        seen_rel_paths: set[str] = set()
        for _tool, agents_dir in comparator.agents_paths.items():
            if agents_dir.is_dir():
                for agent_file in sorted(agents_dir.rglob("*")):
                    if agent_file.is_file() and agent_file.name != "README.md":
                        seen_rel_paths.add("agents/" + agent_file.name)
        warehouse_agents_dir = warehouse_path / "agents"
        if warehouse_agents_dir.is_dir():
            for agent_file in sorted(warehouse_agents_dir.rglob("*")):
                if agent_file.is_file() and agent_file.name != "README.md":
                    seen_rel_paths.add(str(agent_file.relative_to(warehouse_path)))
        for rel_path in sorted(seen_rel_paths):
            result = comparator._compare_agent_file(rel_path)
            if result.status in (DeltaStatus.MODIFIED, DeltaStatus.ADDED):
                agent_paths.append(rel_path)

    if not contributable and not unregistered_paths and not agent_paths:
        console.print(
            "[green]Nothing to contribute.[/green] "
            "All local artifacts match the warehouse."
        )
        return []

    contributed: list[tuple[str, str]] = []

    for result in contributable:
        is_skill = result.path.startswith("skills/") and bool(comparator.skills_paths)

        if is_skill:
            local_path = _resolve_skill_contribute_source(
                comparator, result.path, artifacts_dir, dry_run=dry_run
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
        if is_skill and not dry_run:
            _propagate_skill_to_agents(project_root, result.path, local_path)
        status_label = "modified" if result.status == DeltaStatus.MODIFIED else "added"
        contributed.append((result.path, status_label))

    for rel_path in unregistered_paths:
        is_skill = rel_path.startswith("skills/") and bool(comparator.skills_paths)
        if is_skill:
            # Skills live in live agent dirs, not in artifacts_dir.
            # Pick the first agent copy that exists on disk.
            local_path = None
            for _agent, skills_root in comparator.skills_paths.items():
                parts = Path(rel_path).parts
                skill_relative = (
                    Path(*parts[1:]) if parts[0] == "skills" else Path(rel_path)
                )
                candidate = skills_root / skill_relative
                if candidate.exists():
                    local_path = candidate
                    break
            if local_path is None:
                console.print(
                    f"  [yellow]Skipping[/yellow] {rel_path} (not found in any agent dir)"
                )
                continue
        else:
            local_path = artifacts_dir / rel_path
        _copy_to_warehouse(local_path, warehouse_path / rel_path, rel_path, dry_run)
        contributed.append((rel_path, "added"))

    # Contribute modified agent definitions (always included, no beacon.yaml entry)
    for rel_path in agent_paths:
        local_path = _resolve_agent_contribute_source(
            comparator, rel_path, dry_run=dry_run
        )
        if local_path is None:
            console.print(
                f"  [yellow]Skipping[/yellow] {rel_path} (no modified copy found)"
            )
            continue
        _copy_to_warehouse(local_path, warehouse_path / rel_path, rel_path, dry_run)
        contributed.append((rel_path, "modified"))

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
    git_add_args = " ".join(contributed)
    console.print(f"  git add {git_add_args}")
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

    r = _git(["add", "--", *paths])
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


def _confirm_prune(orphans: list[OrphanInfo], *, dry_run: bool = False) -> list[str]:
    """Prompt the user to confirm deletion of orphaned artifacts.

    Orphans are files that exist in artifacts/ but are no longer listed in
    beacon.yaml AND exist in the warehouse (so they were previously synced).
    Files that do not exist in the warehouse are new contributions and are
    never passed here.

    Modified orphans (local content differs from warehouse) are listed
    separately with a stronger warning.

    In dry-run mode this function always returns an empty list (nothing to
    actually delete) but still prints the preview list.

    Returns:
        List of relative paths the user confirmed for deletion.
        Empty list if the user said no, or if dry_run=True.
    """
    if not orphans:
        return []

    safe = [o for o in orphans if not o.is_modified]
    modified = [o for o in orphans if o.is_modified]

    console.print(
        "\n[yellow]The following artifact(s) are no longer in beacon.yaml:[/yellow]"
    )
    for o in safe:
        console.print(f"  [dim]•[/dim] {o.rel_path}")
    if modified:
        console.print(
            "\n[red]These artifact(s) have local modifications and are no longer in beacon.yaml:[/red]"
        )
        for o in modified:
            console.print(f"  [red]•[/red] {o.rel_path} [dim](locally modified)[/dim]")

    if dry_run:
        console.print(
            "\n  [dim]Dry run — no files will be deleted. "
            "Run without --dry-run to apply.[/dim]"
        )
        return []

    # Always ask, even for the safe (unmodified) list
    if not click.confirm(
        f"\nDelete {len(orphans)} artifact(s) from .agentic-beacon/artifacts/?",
        default=False,
    ):
        console.print("  [dim]Skipped — orphaned artifacts left in place.[/dim]")
        return []

    # For modified files, ask again individually
    confirmed: list[str] = []
    for o in safe:
        confirmed.append(o.rel_path)
    for o in modified:
        if click.confirm(
            f"  Delete '{o.rel_path}' (has local changes — changes will be lost)?",
            default=False,
        ):
            confirmed.append(o.rel_path)
        else:
            console.print(f"  [dim]Kept: {o.rel_path}[/dim]")

    return confirmed


def _unwire_pruned_artifacts(
    project_root: Path, pruned_paths: list[str], artifacts_dir: Path
) -> None:
    """Remove wiring for pruned artifacts from agent config files.

    For each pruned path:
    - If it's a context (contexts/**/*.md): remove from opencode.json instructions
      and from CLAUDE.md @-references.
    - If it's a skill (skills/<name>/SKILL.md): remove .opencode/skills/<name>/
      and .claude/skills/<name>/ directories.

    Args:
        project_root: Project root directory.
        pruned_paths: Relative paths (under artifacts/) that were deleted.
        artifacts_dir: Path to .agentic-beacon/artifacts/.
    """
    for rel_path in pruned_paths:
        parts = Path(rel_path).parts
        if not parts:
            continue

        artifact_type = parts[0]

        if artifact_type == "contexts":
            # Path inside artifacts_dir
            artifact_abs = artifacts_dir / rel_path
            rel_to_project = str(artifact_abs.relative_to(project_root))
            _unwire_context_opencode(project_root, rel_to_project)
            _unwire_context_claudecode(project_root, rel_to_project)

        elif artifact_type == "skills" and len(parts) >= 2:
            skill_name = parts[1]
            _unwire_skill(project_root, skill_name)


def _unwire_context_opencode(project_root: Path, rel_path: str) -> None:
    """Remove a context path from opencode.json instructions."""
    opencode_json = project_root / "opencode.json"
    if not opencode_json.exists():
        return
    try:
        data = json.loads(opencode_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    instructions: list[str] = data.get("instructions", [])
    if rel_path in instructions:
        instructions.remove(rel_path)
        data["instructions"] = instructions
        opencode_json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        logger.debug("Unwired context from opencode.json: {}", rel_path)


def _unwire_context_claudecode(project_root: Path, rel_path: str) -> None:
    """Remove a context @-reference from CLAUDE.md."""
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
        return
    ref = f"@{rel_path}"
    content = claude_md.read_text(encoding="utf-8")
    if ref not in content:
        return
    # Remove the line containing the reference
    lines = content.splitlines(keepends=True)
    new_lines = [line for line in lines if line.strip() != ref]
    claude_md.write_text("".join(new_lines), encoding="utf-8")
    logger.debug("Unwired context from CLAUDE.md: {}", rel_path)


def _unwire_skill(project_root: Path, skill_name: str) -> None:
    """Remove a skill's wiring directories for all detected agents."""
    opencode_skill = project_root / ".opencode" / "skills" / skill_name
    if opencode_skill.exists():
        shutil.rmtree(opencode_skill, ignore_errors=True)
        logger.debug("Removed OpenCode skill dir: {}", opencode_skill)

    opencode_cmd = project_root / ".opencode" / "command" / f"{skill_name}.md"
    if opencode_cmd.exists():
        opencode_cmd.unlink(missing_ok=True)
        logger.debug("Removed OpenCode command stub: {}", opencode_cmd)

    claude_skill = project_root / ".claude" / "skills" / skill_name
    if claude_skill.exists():
        shutil.rmtree(claude_skill, ignore_errors=True)
        logger.debug("Removed Claude skill dir: {}", claude_skill)


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
    project_root: Path,
    artifacts_dir: Path,
    force: bool = False,
    preserve: bool = False,
) -> tuple[list[str], list[str]]:
    """Install all synced skills for detected agents.

    Respects soft-block flags: --force overwrites without prompt, --preserve skips
    conflicting live skill files.

    Returns (installed, errors) where each entry is '<skill> (<agent>)'.
    Uses fallback_to_all so skills are always wired regardless of whether agent
    config files exist yet.
    """
    agents = _detect_agents(project_root, fallback_to_all=True)

    skills_dir = artifacts_dir / "skills"
    if not skills_dir.exists():
        return [], []

    skill_dirs = sorted(d for d in skills_dir.iterdir() if d.is_dir())
    if not skill_dirs:
        return [], []

    # Compute wiring conflicts (live skill files that differ from what we'd write)
    wiring_conflicts: list[tuple[str, str, str]] = []  # (agent, skill_name, dest_path)
    for skill_dir in skill_dirs:
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        content = skill_md.read_text(encoding="utf-8")
        name = skill_dir.name
        for agent in agents:
            if agent == "opencode":
                dest = project_root / ".opencode" / "skills" / name / "SKILL.md"
            else:
                dest = project_root / ".claude" / "skills" / name / "SKILL.md"
            if dest.exists() and dest.read_text(encoding="utf-8") != content:
                wiring_conflicts.append((agent, name, str(dest)))

    if wiring_conflicts:
        conflict_paths = [str(dest) for _, _, dest in wiring_conflicts]
        overwrite = _handle_soft_block(conflict_paths, force=force, preserve=preserve)
        if not overwrite:
            preserve = True  # skip conflicting live skill files

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
            # Check if this specific wiring target is a conflict we should skip
            conflicting_agents_skills = {(a, n) for a, n, _ in wiring_conflicts}
            if preserve and (agent, name) in conflicting_agents_skills:
                continue  # Skip this wiring target

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


_ALL_KNOWN_AGENTS = ["opencode", "claudecode"]


def _detect_agents(project_root: Path, *, fallback_to_all: bool = False) -> list[str]:
    """Detect which agent tools are configured in the project.

    When fallback_to_all=True and no config files are found, returns all known
    agents so callers can wire unconditionally (e.g. skill installation).
    """
    agents = []
    if (project_root / "opencode.json").exists():
        agents.append("opencode")
    if (project_root / ".claude").exists() or (project_root / "CLAUDE.md").exists():
        agents.append("claudecode")
    if not agents and fallback_to_all:
        return list(_ALL_KNOWN_AGENTS)
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

    # Return True only if SKILL.md was written (command stub updates are transparent)
    return not skill_unchanged


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


def _do_reset(project_root: Path) -> None:
    """Force-overwrite all synced artifacts from warehouse. Used by both reset and update."""
    beacon_dir = project_root / ".agentic-beacon"

    if not beacon_dir.exists():
        console.print(f"[red]Error:[/red] No warehouse connected at {project_root}")
        console.print("Run 'abc warehouse connect' first.")
        sys.exit(1)

    if not (beacon_dir / "beacon.yaml").exists():
        console.print("[red]Error:[/red] No beacon.yaml found.")
        console.print("Run 'abc setup' to create artifact configuration.")
        sys.exit(1)

    console.print("[blue]Resetting artifacts from warehouse...[/blue]")

    try:
        from .core.settings import BeaconSettings, WarehouseSettings

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
            # Force overwrite: remove destination first so idempotent check doesn't skip
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

        console.print("\n[bold green]✓ Reset complete![/bold green]")
        console.print(f"  [blue]Overwritten:[/blue] {overwritten_count} files")
        new_count = (
            copied_count - overwritten_count if copied_count > overwritten_count else 0
        )
        if new_count:
            console.print(f"  [blue]New:[/blue] {new_count} files")
        if error_count > 0:
            console.print(f"  [red]Errors:[/red] {error_count} files")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Reset failed")
        sys.exit(1)


@main.command(name="reset")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Path to project root (auto-detected if not provided)",
)
def reset_cmd(*, project: Path | None) -> None:
    """Force-overwrite all synced artifacts from the warehouse.

    Overwrites any local modifications without prompting.
    Use this when you want to discard local changes and resync from the warehouse.
    """
    project_root = project or find_project_root()
    _do_reset(project_root)


@main.command(name="update", hidden=True)
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Path to project root (auto-detected if not provided)",
)
def update(*, project: Path | None) -> None:
    """[Deprecated] Use 'abc reset' instead.

    Update existing synced artifacts from warehouse (re-runs sync, overwrites changes).
    """
    console.print(
        "[yellow]Deprecation warning:[/yellow] 'abc update' is deprecated. "
        "Use 'abc reset' instead."
    )
    project_root = project or find_project_root()
    _do_reset(project_root)


@main.command(name="list")
@click.argument(
    "artifact_type",
    required=False,
    type=click.Choice(
        ["agents", "knowledge", "skills", "contexts"], case_sensitive=False
    ),
    default=None,
)
def list_cmd(*, artifact_type: str | None) -> None:
    """List artifacts synced to the current project.

    ARTIFACT_TYPE filters output to a single type. Omit to show all.

    Reads from .agentic-beacon/artifacts/. Run 'abc sync' first to populate.
    For agents, shows globally installed files from ~/.config/opencode/agents/
    and ~/.claude/agents/.

    Example:
        abc list
        abc list knowledge
        abc list skills
        abc list contexts
        abc list agents
    """
    # Special case: agents are globally installed, not project-scoped
    if artifact_type == "agents":
        _list_global_agents()
        return

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
        _show_bundled_skills_status()
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

    _show_bundled_skills_status()

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
