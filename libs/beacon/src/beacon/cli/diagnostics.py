"""Doctor/diagnostics command for the abc CLI."""

from pathlib import Path

import click
from rich.console import Console

from beacon.core.manifest.beacon import BeaconManifest
from beacon.core.manifest.workspace import WorkspaceConfig
from beacon.domains.setup.diagnostics import run_project_diagnostics
from beacon.utils.display import print_doctor_summary
from beacon.utils.git import find_project_root

console = Console()


@click.command()
@click.option(
    "--fix",
    is_flag=True,
    help="Automatically repair fixable issues.",
)
def doctor(*, fix: bool) -> None:
    """Diagnose the health of the current project's beacon configuration.

    Checks:
    \b
      • Warehouse connection (config.toml present, local_path reachable)
      • beacon.yaml parseable and structurally valid
      • Skill entries: skill directories exist in the warehouse
      • Context entries: context files exist in the warehouse

    Use --fix to automatically repair fixable issues.
    """

    issues: list[str] = []
    fixes_applied: list[str] = []

    def _ok(msg: str) -> None:
        console.print(f"  [green]✓[/green] {msg}")

    def _warn(msg: str, detail: str = "") -> None:
        issues.append(msg)
        console.print(f"  [yellow]⚠[/yellow]  {msg}")
        if detail:
            console.print(f"       [dim]{detail}[/dim]")

    def _err(msg: str, detail: str = "") -> None:
        issues.append(msg)
        console.print(f"  [red]✗[/red]  {msg}")
        if detail:
            console.print(f"       [dim]{detail}[/dim]")

    console.print("[bold]Running beacon doctor…[/bold]\n")

    try:
        project_root = find_project_root()
        beacon_dir = project_root / ".agentic-beacon"
        beacon_yaml = beacon_dir / "beacon.yaml"
        _ok(f"Project root: {project_root}")
    except SystemExit:
        _err("Could not locate project root (.agentic-beacon directory not found)")
        console.print(
            "\n[dim]Run [bold]abc warehouse connect[/bold] to set up a project.[/dim]"
        )
        return

    config_toml = beacon_dir / "config.toml"
    warehouse_path: Path | None = None

    if not config_toml.exists():
        _err(
            "Warehouse not connected (config.toml missing)",
            "Run: abc warehouse connect",
        )
    else:
        try:
            ws = WorkspaceConfig()
            warehouse_path = Path(ws.warehouse.local_path)
            if warehouse_path.is_dir():
                _ok(f"Warehouse connected: {warehouse_path}")
            else:
                _err(
                    f"Warehouse path does not exist: {warehouse_path}",
                    "Run: abc warehouse connect",
                )
                warehouse_path = None
        except Exception as exc:
            _err(f"Could not read warehouse settings: {exc}")
            warehouse_path = None

    beacon_settings = None
    if not beacon_yaml.exists():
        _err("beacon.yaml not found", "Run: abc setup")
    else:
        try:
            beacon_settings = BeaconManifest.from_yaml(beacon_yaml)
            _ok("beacon.yaml is valid YAML")
        except Exception as exc:
            _err(f"beacon.yaml parse error: {exc}")

    if beacon_settings is None:
        console.print(
            "\n[bold red]Cannot continue checks without a valid beacon.yaml.[/bold red]"
        )
        print_doctor_summary(issues, fixes_applied)
        return

    skill_entries: list[str] = list(beacon_settings.artifacts.skills)
    context_entries: list[str] = list(beacon_settings.artifacts.contexts)

    if warehouse_path:
        missing_skills: list[str] = []
        for entry in skill_entries:
            skill_dir = warehouse_path / entry.rstrip("/")
            if not skill_dir.is_dir():
                missing_skills.append(entry)
        if missing_skills:
            _err(
                f"Skill entries: {len(missing_skills)} skill(s) missing from warehouse",
            )
            for p in missing_skills:
                console.print(f"       [dim]{p}[/dim]")
        else:
            _ok(f"Skill entries: all {len(skill_entries)} skill(s) exist in warehouse")

    if warehouse_path:
        missing_contexts: list[str] = []
        for entry in context_entries:
            ctx_file = warehouse_path / entry
            if not ctx_file.exists():
                missing_contexts.append(entry)
        if missing_contexts:
            _err(
                f"Context entries: {len(missing_contexts)} context(s) missing from warehouse",
            )
            for p in missing_contexts:
                console.print(f"       [dim]{p}[/dim]")
        else:
            _ok(
                f"Context entries: all {len(context_entries)} context(s) exist in warehouse"
            )

    # Single domain call: repair + checks
    project_issues, gitignore_fixes = run_project_diagnostics(
        project_root, warehouse_path, beacon_settings, fix
    )
    for msg in gitignore_fixes:
        fixes_applied.append(msg)
        console.print(f"  [green]✓[/green] {msg}")
    for issue in project_issues:
        if issue.severity == "warn":
            _warn(issue.message, issue.detail)
        else:
            _err(issue.message, issue.detail)

    print_doctor_summary(issues, fixes_applied)
