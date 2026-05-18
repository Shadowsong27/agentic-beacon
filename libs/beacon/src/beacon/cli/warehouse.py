"""Warehouse management subcommands (abc warehouse ...)."""

import os
import sys
from pathlib import Path

import click
from loguru import logger
from rich.console import Console
from rich.table import Table

from beacon.core.manifest.workspace import WorkspaceConfig
from beacon.domains.distribution.distributor import WarehouseDistributor
from beacon.domains.distribution.upgrader import WarehouseUpgrader
from beacon.domains.setup.initializer import WarehouseInitializer
from beacon.domains.warehouse.connector import connect_to_warehouse
from beacon.domains.warehouse.contribute import contribute
from beacon.domains.warehouse.lint import LintReport, lint_warehouse
from beacon.domains.warehouse.status import status as warehouse_status

console = Console()


@click.group()
def warehouse() -> None:
    """Warehouse management commands (init, connect, list, contribute, status)."""
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

    Creates a complete warehouse structure with contexts, skills, and agents.
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
        console.print(f"  {step}. Customize contexts, skills, and agents")
        console.print(f"  {step + 1}. git remote add origin <your-repo-url>")
        console.print(f"  {step + 2}. git push -u origin main")
        console.print(f"  {step + 3}. Run 'abc adopt' to wire agents.")

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
@click.option(
    "--main-branch",
    type=str,
    default=None,
    help=(
        "Override the warehouse's main branch (e.g. 'dev'). "
        "Defaults to accepting 'main' or 'master'."
    ),
)
def connect(*, path: Path | None, main_branch: str | None) -> None:
    """
    Connect project to a local warehouse.

    Creates .agentic-beacon/config.toml with warehouse connection.
    The warehouse is validated before accepting the connection.
    Only existing local filesystem paths are accepted.

    Example:
        abc warehouse connect --path ~/org-warehouse
        abc warehouse connect --path ~/org-warehouse --main-branch dev
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

    raw_path = str(path)

    # Reject URLs and non-local paths
    if raw_path.startswith(("http://", "https://", "git://", "file://")):
        console.print(
            f"\n[red]Error:[/red] Local path required. URLs are not supported: {raw_path}"
        )
        sys.exit(1)

    if raw_path.startswith("git@"):
        console.print(
            f"\n[red]Error:[/red] Local path required. Git SSH URLs are not supported: {raw_path}"
        )
        sys.exit(1)

    warehouse_path = path.expanduser().resolve()

    if not warehouse_path.exists():
        console.print(f"\n[red]Error:[/red] Path does not exist: {warehouse_path}")
        sys.exit(1)

    if not warehouse_path.is_dir():
        console.print(f"\n[red]Error:[/red] Path is not a directory: {warehouse_path}")
        sys.exit(1)

    console.print(f"\n[blue]Validating:[/blue] {warehouse_path}")

    try:
        result = connect_to_warehouse(
            project_root=Path.cwd(),
            warehouse_path=warehouse_path,
            main_branch=main_branch,
        )
    except Exception as e:
        console.print(f"\n[red]Error:[/red] Failed to save connection: {e}")
        logger.exception("Connection failed")
        sys.exit(1)

    if not result.valid:
        console.print("\n[red bold]✗ Invalid warehouse structure[/red bold]\n")
        for error in result.errors:
            console.print(f"  [red]✗[/red] {error}")
        console.print(
            "\n[dim]Run `abc warehouse init demo-warehouse` to see a valid warehouse structure[/dim]"
        )
        sys.exit(1)

    console.print("[green]✓[/green] Warehouse structure validated")
    console.print("[green]✓[/green] Connection saved")

    # PER-130 round-1 (LOW finding): agent-dir gitignore entries are NOT
    # added during connect — `abc sync` is the authoritative gate, and
    # adding them eagerly here churns the .gitignore for projects that
    # will never declare agents.
    if result.gitignore_updated:
        console.print("[green]✓[/green] Updated .gitignore")

    console.print("\n[bold green]✓ Connected to warehouse[/bold green]")
    console.print(f"  [blue]Location:[/blue] {warehouse_path}")

    console.print("\n[bold]Next Steps:[/bold]")
    console.print("  1. Run 'abc setup' to configure artifacts")
    console.print("  2. Run 'abc sync' to sync artifacts")


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


@warehouse.command(name="contribute")
@click.option(
    "-m",
    "--message",
    type=str,
    required=True,
    help="Commit message",
)
@click.option(
    "--push",
    is_flag=True,
    help="Push the commit to the remote after committing",
)
@click.option(
    "--paths",
    "paths",
    multiple=True,
    type=str,
    help=(
        "Warehouse-relative path to commit (repeatable). When omitted, "
        "commits all beacon.yaml-tracked dirty paths (current behavior)."
    ),
)
def warehouse_contribute(*, message: str, push: bool, paths: tuple[str, ...]) -> None:
    """Commit changes in the warehouse working tree.

    Stages and commits files tracked by beacon.yaml that have uncommitted
    changes in the warehouse clone.

    Example:
        abc warehouse contribute -m "Update python standards"
        abc warehouse contribute -m "Fix typo" --push
        abc warehouse contribute -m "Update skill" --paths skills/foo/SKILL.md
        abc warehouse contribute -m "Split commit" --paths a.md --paths b.md
    """
    try:
        result = contribute(
            project_root=Path.cwd(),
            message=message,
            push=push,
            paths=tuple(paths) or None,
        )
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Contribute failed")
        sys.exit(1)

    if result.status == "no_changes":
        if result.dirty_outside_scope_count > 0:
            console.print(
                f"[yellow]Note: {result.dirty_outside_scope_count} dirty file(s) in warehouse outside this project's beacon.yaml scope.[/yellow]"
            )
            console.print(
                "[yellow]Run 'abc warehouse status --all' to see them, or contribute from a project that tracks them.[/yellow]"
            )
        else:
            console.print("[yellow]No uncommitted changes to contribute.[/yellow]")
        return

    if result.status == "committed":
        console.print(f"[green]✓ Committed:[/green] {result.committed_sha}")
        console.print(f"  [blue]Message:[/blue] {result.message}")
        return

    if result.status == "push_failed":
        console.print(f"[yellow]⚠ Push failed:[/yellow] {result.message}")
        console.print(f"  [dim]Commit preserved locally: {result.committed_sha}[/dim]")
        sys.exit(1)


@warehouse.command(name="status")
@click.argument("path", required=False, type=str)
@click.option(
    "--all",
    "all_paths",
    is_flag=True,
    help="Show unfiltered warehouse working-tree status",
)
def warehouse_status_cmd(*, path: str | None, all_paths: bool) -> None:
    """Show warehouse working tree status.

    Without arguments: lists modified files tracked by beacon.yaml.
    With PATH: shows unified diff for that single file.

    Example:
        abc warehouse status
        abc warehouse status knowledge/python/standards.md
        abc warehouse status --all
    """
    try:
        result = warehouse_status(
            project_root=Path.cwd(),
            path=path,
            all_paths=all_paths,
        )
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Status failed")
        sys.exit(1)

    if path:
        if result.diff:
            console.print(result.diff)
        else:
            console.print("[dim]No diff for the specified path.[/dim]")
        return

    if not result.modifications:
        if result.dirty_outside_scope_count > 0:
            console.print(
                f"[yellow]Note: {result.dirty_outside_scope_count} dirty file(s) in warehouse outside this project's beacon.yaml scope.[/yellow]"
            )
            console.print(
                "[yellow]Run 'abc warehouse status --all' to see them, or contribute from a project that tracks them.[/yellow]"
            )
        else:
            console.print("[green]✓ Working tree is clean.[/green]")
    else:
        console.print("[bold]Modified files:[/bold]")
        for entry in result.modifications:
            status_label = {
                "M": "[yellow]modified[/yellow]",
                "A": "[green]added[/green]",
                "D": "[red]deleted[/red]",
                "??": "[cyan]untracked[/cyan]",
            }.get(entry.status, f"[{entry.status}]")
            console.print(f"  {status_label} {entry.path}")

    if result.has_upstream:
        if result.ahead or result.behind:
            console.print(
                f"\n[dim]Branch is {result.ahead or 0} ahead, {result.behind or 0} behind upstream[/dim]"
            )
    else:
        console.print("\n[yellow]No upstream configured for this branch.[/yellow]")


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


def _print_lint_report(report: LintReport, _console: Console | None = None) -> None:
    """Print lint findings grouped by artifact path with Rich formatting.

    `artifact_path` and `finding.message` originate from warehouse files and
    link text — anything containing `[`, `]`, or text that looks like Rich
    markup would otherwise be interpreted by Rich's console parser. Both are
    routed through `rich.markup.escape()` before interpolation so a hostile
    or accidentally-formatted message cannot spoof or corrupt CI output.

    Args:
        report: The lint report to display.
        _console: Optional Console instance (defaults to module-level console).
    """
    from rich.markup import escape

    c = _console if _console is not None else console
    if not report:
        c.print("[green]✓ Lint passed.[/green]")
        return

    # Group findings by artifact path (preserve sorted order from LintReport)
    from itertools import groupby

    for artifact_path, group_iter in groupby(
        report.findings, key=lambda f: f.artifact_path
    ):
        group = list(group_iter)
        c.print(f"[bold]{escape(artifact_path)}[/bold]")
        for finding in group:
            c.print(f"  [red]error:[/red] {escape(finding.message)}")

    # Summary line
    n = len(report.findings)
    # Count unique artifact paths
    unique_paths = len({f.artifact_path for f in report.findings})
    c.print(f"\n[red]Found {n} error(s) across {unique_paths} file(s).[/red]")


@warehouse.command(name="lint")
@click.argument(
    "warehouse_path",
    # No exists=True / file_okay=False: lint_warehouse + WarehouseValidator
    # already emit structured findings for missing / file-typed paths
    # ("Path not found", "Path is not a directory"). Letting Click reject
    # before lint runs would short-circuit the documented exit-1 finding flow.
    type=click.Path(path_type=Path),
    required=False,
    default=None,
)
def warehouse_lint(*, warehouse_path: Path | None) -> None:
    """Validate a warehouse directory end-to-end.

    Runs every Beacon-owned artifact validation rule against the warehouse at
    WAREHOUSE_PATH (defaults to the current directory when omitted).

    Validates: structure, skill frontmatter, skill context references,
    agent manifest, agent frontmatter (name + description), and knowledge
    link integrity.

    Exits 0 when no errors found; exits 1 when any errors are found.

    \b
    Examples:
        abc warehouse lint
        abc warehouse lint /path/to/warehouse
    """
    target = warehouse_path or Path.cwd()
    report = lint_warehouse(target)
    _print_lint_report(report)
    sys.exit(1 if report.findings else 0)
