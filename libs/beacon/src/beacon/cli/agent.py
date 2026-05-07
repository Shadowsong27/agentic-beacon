"""Agent-related commands for the abc CLI."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from beacon.core.manifest.workspace import WorkspaceConfig
from beacon.domains.distribution.sync_engine import SyncEngine

console = Console()


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
    Agents are project-scoped and read from .agentic-beacon/artifacts/agents/.

    Example:
        abc list
        abc list knowledge
        abc list skills
        abc list contexts
        abc list agents
    """
    beacon_dir = Path.cwd() / ".agentic-beacon"
    artifacts_dir = beacon_dir / "artifacts"

    # Resolve the connected warehouse path from WorkspaceConfig only when a
    # config.toml is present. SyncEngine.list_artifacts() only reads
    # artifacts_path today, but the engine's __post_init__ resolves
    # warehouse_path; fall back to beacon_dir on unconnected projects so the
    # engine doesn't end up with a semantically-wrong Path.cwd(). A malformed
    # but present config.toml is allowed to propagate (the user should fix
    # their config rather than have abc list silently degrade).
    if (beacon_dir / "config.toml").is_file():
        warehouse_path = Path(WorkspaceConfig().warehouse.local_path)
    else:
        warehouse_path = beacon_dir

    engine = SyncEngine(warehouse_path=warehouse_path, artifacts_path=artifacts_dir)

    if artifact_type == "agents":
        artifacts = engine.list_artifacts("agents")
        agent_files = artifacts.get("agents", [])
        if not agent_files:
            console.print(
                "[yellow]No agents found in .agentic-beacon/artifacts/agents/.[/yellow]"
            )
            console.print(
                "Run 'abc adopt' or declare agents in beacon.yaml then 'abc sync'."
            )
            return

        table = Table(title="Synced Agents")
        table.add_column("Agent", style="magenta")
        for rel in agent_files:
            table.add_row(Path(rel).stem)
        console.print(table)
        return

    if not artifacts_dir.exists():
        console.print("[red]Error:[/red] No synced artifacts found.")
        console.print("Run 'abc sync' to download artifacts from the warehouse.")
        sys.exit(1)

    section_config = {
        "contexts": ("Synced Contexts", "cyan", "Context"),
        "skills": ("Synced Skills", "yellow", "Skill"),
    }

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
