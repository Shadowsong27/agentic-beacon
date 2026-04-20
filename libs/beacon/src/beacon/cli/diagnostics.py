"""Doctor/diagnostics command for the abc CLI."""

from pathlib import Path

import click
from rich.console import Console

from beacon.core.manifest.beacon import BeaconManifest
from beacon.core.manifest.workspace import WorkspaceConfig
from beacon.domains.adoption.discovery import (
    find_knowledge_node_for_file,
    is_knowledge_node,
)
from beacon.utils.display import print_doctor_summary
from beacon.utils.git import find_project_root

console = Console()


@click.command()
@click.option(
    "--fix",
    is_flag=True,
    help="Automatically repair fixable issues (e.g. migrate file-level knowledge paths to node-level).",
)
def doctor(*, fix: bool) -> None:
    """Diagnose the health of the current project's beacon configuration.

    Checks:
    \b
      • Warehouse connection (config.toml present, local_path reachable)
      • beacon.yaml parseable and structurally valid
      • Knowledge entries: file-level paths migrated to node-level
      • Knowledge entries: node directories exist in the warehouse
      • Skill entries: skill directories exist in the warehouse
      • Context entries: context files exist in the warehouse

    Use --fix to automatically repair file-level knowledge path entries.
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

    knowledge_entries: list[str] = list(beacon_settings.artifacts.knowledge)
    skill_entries: list[str] = list(beacon_settings.artifacts.skills)
    context_entries: list[str] = list(beacon_settings.artifacts.contexts)

    file_level: list[tuple[str, str | None]] = []
    for entry in knowledge_entries:
        if entry.endswith(".md") or any(
            seg in entry.split("/") for seg in ("decisions", "lessons", "facts")
        ):
            node = find_knowledge_node_for_file(entry)
            file_level.append((entry, node))

    if not file_level:
        _ok(
            f"Knowledge entries: {len(knowledge_entries)} registered, all at node level"
        )
    else:
        _warn(
            f"Knowledge entries: {len(file_level)} file-level path(s) should be node-level",
            "Use --fix to auto-migrate, or update beacon.yaml manually.",
        )
        for old, suggested in file_level:
            arrow = (
                f"  →  [green]{suggested}[/green]"
                if suggested
                else "  [red](no node found — check warehouse structure)[/red]"
            )
            console.print(f"       [dim]{old}[/dim]{arrow}")

        if fix:
            new_entries: list[str] = []
            seen: set[str] = set()
            for entry in knowledge_entries:
                if entry.endswith(".md") or any(
                    seg in entry.split("/") for seg in ("decisions", "lessons", "facts")
                ):
                    node = find_knowledge_node_for_file(entry)
                    if node and node not in seen:
                        new_entries.append(node)
                        seen.add(node)
                        fixes_applied.append(f"  {entry}  →  {node}")
                    elif not node:
                        if entry not in seen:
                            new_entries.append(entry)
                            seen.add(entry)
                else:
                    if entry not in seen:
                        new_entries.append(entry)
                        seen.add(entry)
            beacon_settings.artifacts.knowledge = new_entries
            beacon_settings.to_yaml(beacon_yaml)
            beacon_settings = BeaconManifest.from_yaml(beacon_yaml)
            knowledge_entries = list(beacon_settings.artifacts.knowledge)
            console.print(
                f"       [green]Fixed:[/green] migrated {len(fixes_applied)} knowledge path(s) to node level"
            )

    if warehouse_path:
        missing_nodes: list[str] = []
        invalid_nodes: list[str] = []
        for entry in knowledge_entries:
            node_dir = warehouse_path / entry
            if not node_dir.exists():
                missing_nodes.append(entry)
            elif not is_knowledge_node(node_dir):
                invalid_nodes.append(entry)

        if missing_nodes:
            _err(
                f"Knowledge entries: {len(missing_nodes)} node(s) missing from warehouse",
                "These paths do not exist in the warehouse directory.",
            )
            for p in missing_nodes:
                console.print(f"       [dim]{p}[/dim]")

        if invalid_nodes:
            _warn(
                f"Knowledge entries: {len(invalid_nodes)} path(s) point to non-node directories",
                "These directories have no decisions/, lessons/, or facts/ subfolders.",
            )
            for p in invalid_nodes:
                console.print(f"       [dim]{p}[/dim]")

        if not missing_nodes and not invalid_nodes:
            _ok(
                f"Knowledge entries: all {len(knowledge_entries)} node(s) exist in warehouse"
            )

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

    print_doctor_summary(issues, fixes_applied)
