"""Contribute command for the abc CLI."""

import sys
from pathlib import Path

import click
from loguru import logger
from rich.console import Console

from beacon.core.manifest.beacon import BeaconManifest
from beacon.core.manifest.workspace import WorkspaceConfig
from beacon.domains.artifact.agent import build_agents_paths
from beacon.domains.artifact.skill import build_skills_paths
from beacon.domains.contribution.contributor import (
    auto_git_contribute,
    contribute_all,
    contribute_single,
    print_contribute_next_steps,
)
from beacon.domains.distribution.delta import DeltaComparator
from beacon.domains.distribution.state import check_sync_state
from beacon.utils.git import (
    check_warehouse_git_clean,
)

console = Console()


@click.command()
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
        warehouse_settings = WorkspaceConfig()
        warehouse_path = Path(warehouse_settings.warehouse.local_path)

        if not warehouse_path.exists():
            console.print(
                f"[red]Error:[/red] Warehouse path no longer exists: {warehouse_path}"
            )
            console.print(
                "Run 'abc warehouse connect --path <warehouse>' to reconnect."
            )
            sys.exit(1)

        if not dry_run and not skip_git_check:
            git_error = check_warehouse_git_clean(warehouse_path)
            if git_error:
                console.print(f"[red]Error:[/red] {git_error}")
                sys.exit(1)

        artifacts_dir = beacon_dir / "artifacts"

        if not dry_run and not skip_git_check:
            sync_error = check_sync_state(artifacts_dir, warehouse_path)
            if sync_error:
                console.print(f"[yellow]Warning:[/yellow] {sync_error}")
                sys.exit(1)

        beacon_settings = BeaconManifest.from_yaml(beacon_yaml)
        project_root = Path.cwd()
        comparator = DeltaComparator(
            warehouse_path=warehouse_path,
            artifacts_path=artifacts_dir,
            skills_paths=build_skills_paths(project_root),
            agents_paths=build_agents_paths(),
        )
        ignore_skill_patterns = beacon_settings.ignore.skills

        if dry_run:
            console.print("[dim]Dry run — no files will be copied.[/dim]\n")

        if file:
            if not dry_run:
                console.print("[dim]Preview:[/dim]\n")
                preview = contribute_single(
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
            contributed = contribute_single(
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
                console.print("[dim]Preview:[/dim]\n")
                preview = contribute_all(
                    comparator,
                    beacon_settings,
                    warehouse_path,
                    artifacts_dir,
                    dry_run=True,
                    project_root=project_root,
                    include_unregistered=not exclude_unregistered,
                    ignore_skill_patterns=ignore_skill_patterns,
                )
                if preview and not click.confirm(
                    "\nProceed with contribute?", default=True
                ):
                    console.print("[dim]Aborted.[/dim]")
                    return
            contributed = contribute_all(
                comparator,
                beacon_settings,
                warehouse_path,
                artifacts_dir,
                dry_run,
                project_root=project_root,
                include_unregistered=not exclude_unregistered,
                ignore_skill_patterns=ignore_skill_patterns,
            )

        if not dry_run and contributed:
            if manual_git:
                print_contribute_next_steps(warehouse_path, [p for p, _ in contributed])
            else:
                auto_git_contribute(warehouse_path, contributed)

    except Exception as e:
        console.print(f"\n[red]Error:[/red] Contribute failed: {e}")
        logger.exception("Contribute failed")
        sys.exit(1)
