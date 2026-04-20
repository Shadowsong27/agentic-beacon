"""Agent-related commands for the abc CLI."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from beacon.core.manifest.workspace import WorkspaceConfig
from beacon.domains.artifact.agent import (
    detect_agents,
    handle_install_agent,
    list_global_agents,
    sync_agents_from_warehouse,
    update_agent_gitignores,
)
from beacon.domains.artifact.skill import (
    print_skill_next_steps,
    skill_name_from_entry,
    update_beacon_yaml,
    wire_single_skill,
)
from beacon.domains.distribution.sync_engine import SyncEngine
from beacon.domains.setup.wiring import (
    wire_contexts_claudecode,
    wire_contexts_opencode,
)
from beacon.utils.display import handle_soft_block
from beacon.utils.git import (
    check_warehouse_git_clean,
    check_warehouse_on_main_branch,
)

console = Console()


@click.group()
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
        warehouse_settings = WorkspaceConfig()
        warehouse_path = Path(warehouse_settings.warehouse.local_path)
    except Exception as e:
        console.print(f"[red]Error:[/red] Could not load warehouse settings: {e}")
        sys.exit(1)

    if not skip_git_check:
        check_warehouse_git_clean(warehouse_path)
        check_warehouse_on_main_branch(warehouse_path)

    sync_agents_from_warehouse(warehouse_path, force=force, preserve=preserve)


@click.command(name="install")
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

    artifact_path = Path(artifact.rstrip("/"))
    if artifact_path.parts and artifact_path.parts[0] == "agents":
        handle_install_agent(artifact.rstrip("/"), force=force, preserve=preserve)
        return

    beacon_dir = Path.cwd() / ".agentic-beacon"
    if not beacon_dir.exists():
        console.print("[red]Error:[/red] No .agentic-beacon directory found.")
        console.print("Run 'abc warehouse connect' to connect to a warehouse first.")
        sys.exit(1)

    try:
        warehouse_settings = WorkspaceConfig()
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

    conflicts = engine.classify_conflicts(files_to_copy)
    overwrite = handle_soft_block(conflicts, force=force, preserve=preserve)
    if not overwrite and conflicts:
        preserve = True

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

    if copied > 0:
        update_beacon_yaml(beacon_dir, files_to_copy)

    artifact_type = Path(artifact).parts[0] if Path(artifact).parts else ""
    project_root = Path.cwd()
    detected_agents = (
        detect_agents(project_root, fallback_to_all=True)
        if not agent
        else [agent.lower()]
    )

    if artifact_type == "skills":
        skill_name = skill_name_from_entry(artifact)
        skill_src_dir = artifacts_dir / "skills" / skill_name
        if skill_src_dir.exists() and detected_agents:
            for target_agent in detected_agents:
                wire_single_skill(project_root, skill_name, skill_src_dir, target_agent)
            console.print(f"[green]✓[/green] Installed skill: {skill_name}")
            update_agent_gitignores(project_root)
            print_skill_next_steps(detected_agents)
        elif skill_src_dir.exists():
            console.print(
                "[green]✓[/green] Skill copied (no agent detected for wiring)"
            )
        else:
            console.print(
                f"[green]✓[/green] Artifact copied ({len(files_to_copy)} file(s))"
            )

    elif artifact_type == "contexts":
        wired_opencode = wire_contexts_opencode(project_root, artifacts_dir)
        wired_claudecode = wire_contexts_claudecode(project_root, artifacts_dir)
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


@click.command(name="list")
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
    if artifact_type == "agents":
        list_global_agents()
        return

    beacon_dir = Path.cwd() / ".agentic-beacon"
    artifacts_dir = beacon_dir / "artifacts"

    if not artifacts_dir.exists():
        console.print("[red]Error:[/red] No synced artifacts found.")
        console.print("Run 'abc sync' to download artifacts from the warehouse.")
        sys.exit(1)

    section_config = {
        "contexts": ("Synced Contexts", "cyan", "Context"),
        "knowledge": ("Synced Knowledge", "green", "File"),
        "skills": ("Synced Skills", "yellow", "Skill"),
    }

    engine = SyncEngine(warehouse_path=Path.cwd(), artifacts_path=artifacts_dir)
    artifacts = engine.list_artifacts(artifact_type)

    for section, files in artifacts.items():
        title, color, col_name = section_config[section]
        table = Table(title=title)
        table.add_column(col_name, style=color)
        for item in files:
            table.add_row(item)
        console.print(table)
        console.print()

    if not artifacts:
        label = artifact_type or "artifacts"
        console.print(
            f"[yellow]No {label} found in .agentic-beacon/artifacts/.[/yellow]"
        )
        console.print("Run 'abc sync' to download artifacts from the warehouse.")
