"""Agent-related commands for the abc CLI."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from beacon.core.exceptions import WorkspaceConfigError
from beacon.core.manifest.beacon import BeaconManifest
from beacon.domains.distribution.artifact_listing import (
    list_artifacts_with_config_check,
)

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

    if artifact_type == "agents":
        try:
            artifacts = list_artifacts_with_config_check(beacon_dir, "agents")
        except WorkspaceConfigError as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        agent_files = artifacts.get("agents", [])
        if not agent_files:
            # Distinguish "declared but not synced" from "none declared at all"
            # so the user gets an actionable next step.
            beacon_yaml = beacon_dir / "beacon.yaml"
            declared_agents: list[str] = []
            if beacon_yaml.is_file():
                try:
                    declared_agents = BeaconManifest.from_yaml(
                        beacon_yaml
                    ).artifacts.agents
                except (OSError, ValueError):
                    pass
            if declared_agents:
                console.print(
                    f"[yellow]{len(declared_agents)} agent(s) declared in "
                    "beacon.yaml but not synced.[/yellow]"
                )
                console.print("Run 'abc sync' to wire them.")
            else:
                console.print("[yellow]No agents declared in beacon.yaml.[/yellow]")
                console.print("Run 'abc adopt' to wire agents from the warehouse.")
            return

        table = Table(title="Synced Agents")
        table.add_column("Agent", style="magenta")
        for rel in agent_files:
            table.add_row(Path(rel).stem)
        console.print(table)
        return

    try:
        artifacts = list_artifacts_with_config_check(beacon_dir, artifact_type)
    except WorkspaceConfigError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    if not artifacts_dir.exists():
        console.print("[red]Error:[/red] No synced artifacts found.")
        console.print("Run 'abc sync' to download artifacts from the warehouse.")
        sys.exit(1)

    section_config = {
        "contexts": ("Synced Contexts", "cyan", "Context"),
        "skills": ("Synced Skills", "yellow", "Skill"),
    }

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
