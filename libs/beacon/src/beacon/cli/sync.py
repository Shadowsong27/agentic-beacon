"""Sync-related commands for the abc CLI."""

import sys
from pathlib import Path

import click
from loguru import logger
from rich.console import Console
from rich.table import Table

from beacon.core.exceptions import BeaconSyncError, ResetError
from beacon.core.manifest.beacon import BeaconManifest
from beacon.core.manifest.workspace import WorkspaceConfig
from beacon.domains.artifact.agent import (
    build_agents_paths,
)
from beacon.domains.artifact.skill import (
    build_skills_paths,
    print_bundled_install_result,
    show_bundled_skills_status,
)
from beacon.domains.contribution.delta_view import (
    show_delta_summary,
    show_detailed_diff,
)
from beacon.domains.distribution.delta import DeltaComparator
from beacon.domains.distribution.orchestrator import run_sync
from beacon.domains.distribution.reset import (
    count_synced_files,
    remove_artifacts_dir,
    reset_artifacts,
)
from beacon.domains.distribution.state import relink_global_sync_state
from beacon.domains.setup.wiring import (
    init_claude_md,
    init_opencode_json,
    wire_contexts_claudecode,
    wire_contexts_opencode,
)
from beacon.utils.display import is_interactive
from beacon.utils.git import find_project_root

console = Console()


@click.command()
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

    if dry_run:
        console.print("[dim]Dry run — no files will be copied or pruned.[/dim]\n")

    console.print("\n[blue]Syncing artifacts from warehouse...[/blue]\n")

    def log_fn(msg: str) -> None:
        console.print(f"  {msg}")

    try:
        result = run_sync(
            preserve=preserve,
            force=force,
            verbose=verbose_flag,
            dry_run=dry_run,
            skip_git_check=skip_git_check,
            log_fn=log_fn if (verbose_flag or dry_run) else None,
        )
    except BeaconSyncError as e:
        console.print(f"[red]Error:[/red] {e}")
        if e.hint:
            console.print(f"\n  [dim]{e.hint}[/dim]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Error:[/red] Sync failed: {e}")
        logger.exception("Sync failed")
        sys.exit(1)

    # ── Summary output ──
    if result.no_artifacts:
        console.print(
            "[yellow]No artifacts configured in beacon.yaml. Nothing to sync.[/yellow]"
        )

    action_word = "Would copy" if result.dry_run else "Copied"
    done_label = "Dry run complete" if result.dry_run else "Sync complete"
    console.print(f"\n[bold green]✓ {done_label}[/bold green]")
    console.print(f"  [blue]{action_word}:[/blue] {result.summary.copied} files")
    console.print(f"  [blue]Unchanged:[/blue] {result.summary.skipped} files")
    if result.summary.preserved > 0:
        console.print(
            f"  [yellow]{'Would preserve' if result.dry_run else 'Preserved'}:[/yellow] "
            f"{result.summary.preserved} locally modified files"
        )
        if not result.dry_run:
            console.print("  [dim]Use 'abc delta' to review local changes.[/dim]")
    if result.dry_run and result.orphans:
        console.print(
            f"  [yellow]Would remove:[/yellow] {len(result.orphans)} artifact(s) "
            f"no longer in beacon.yaml (confirmation required)"
        )
    elif result.summary.pruned > 0:
        console.print(
            f"  [yellow]Removed:[/yellow] "
            f"{result.summary.pruned} artifact(s) no longer in beacon.yaml"
        )
    if result.summary.errors > 0:
        console.print(f"  [red]Errors:[/red] {result.summary.errors} files")
        for path, msg in result.summary.failed_files:
            console.print(f"    [red]✗[/red] {path}: {msg}")

    if result.dry_run:
        console.print("\n  [dim]Run without --dry-run to apply these changes.[/dim]")
        return

    # ── Wiring output ──
    if result.oc_added:
        console.print(
            f"\n[green]✓[/green] Wired {len(result.oc_added)} context(s) into opencode.json"
        )
    if result.cc_added:
        console.print(
            f"[green]✓[/green] Wired {len(result.cc_added)} context(s) into CLAUDE.md"
        )

    if result.wired_skills:
        console.print(
            f"[green]✓[/green] Installed {len(result.wired_skills)} skill(s) "
            f"({', '.join(result.wired_skills)})"
        )
    if result.wire_errors:
        for err in result.wire_errors:
            console.print(f"  [yellow]⚠[/yellow] Skill wiring: {err}")

    if result.wiring_notes:
        console.print("\n[bold]Manual wiring required:[/bold]")
        for note in result.wiring_notes:
            console.print(note)

    if result.agent_config_init_needed:
        if is_interactive():
            console.print(
                "\n[yellow]No agent config detected.[/yellow] "
                "Set one up to wire contexts automatically."
            )
            if click.confirm("  Initialize opencode.json?", default=False):
                init_opencode_json(result.project_root)
                oc_init = wire_contexts_opencode(
                    result.project_root, result.artifacts_dir
                )
                if oc_init:
                    console.print(
                        f"[green]✓[/green] Created opencode.json and "
                        f"wired {len(oc_init)} context(s)"
                    )
            if click.confirm("  Initialize CLAUDE.md?", default=False):
                init_claude_md(result.project_root)
                cc_init = wire_contexts_claudecode(
                    result.project_root, result.artifacts_dir
                )
                if cc_init:
                    console.print(
                        f"[green]✓[/green] Created CLAUDE.md and "
                        f"wired {len(cc_init)} context(s)"
                    )
        else:
            console.print(
                "\n[bold]Manual wiring required:[/bold]\n"
                "  Contexts synced — wire them into your agent config:\n"
                '  [bold]opencode.json[/bold] → add to "instructions" array:\n'
                '    ".agentic-beacon/artifacts/contexts/<name>.md"\n'
                "  [bold]CLAUDE.md[/bold] → add a line per context:\n"
                "    @.agentic-beacon/artifacts/contexts/<name>.md"
            )

    print_bundled_install_result(result.bundled_installed, result.bundled_skipped)

    if result.adoption_notification:
        console.print(f"\n[cyan]{result.adoption_notification}[/cyan]")


@click.command()
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

        artifacts_dir = beacon_dir / "artifacts"
        beacon_settings = BeaconManifest.from_yaml(beacon_yaml)

        relink_global_sync_state(warehouse_path)

        project_root = Path.cwd()

        comparator = DeltaComparator(
            warehouse_path=warehouse_path,
            artifacts_path=artifacts_dir,
            skills_paths=build_skills_paths(project_root),
            agents_paths=build_agents_paths(),
        )

        if file:
            show_detailed_diff(comparator, beacon_settings, file, no_color)
        else:
            show_delta_summary(
                comparator, beacon_settings, warehouse_path, project_root
            )

    except Exception as e:
        console.print(f"\n[red]Error:[/red] Delta comparison failed: {e}")
        logger.exception("Delta comparison failed")
        sys.exit(1)


@click.command(name="reset")
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
    console.print("[blue]Resetting artifacts from warehouse...[/blue]")

    try:
        overwritten_count, new_count, error_count = reset_artifacts(project_root)

        console.print("\n[bold green]✓ Reset complete![/bold green]")
        console.print(f"  [blue]Overwritten:[/blue] {overwritten_count} files")
        if new_count:
            console.print(f"  [blue]New:[/blue] {new_count} files")
        if error_count > 0:
            console.print(f"  [red]Errors:[/red] {error_count} files")

    except ResetError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Reset failed")
        sys.exit(1)


@click.command(name="update", hidden=True)
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
    reset_cmd.callback(project=project)


@click.command()
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Path to project root (auto-detected if not provided)",
)
@click.confirmation_option(prompt="Are you sure you want to remove synced artifacts?")
def clean(*, project: Path | None) -> None:
    """Remove synced artifacts from project (.agentic-beacon/artifacts/)."""
    project_root = project or find_project_root()
    removed = remove_artifacts_dir(project_root)

    if removed:
        console.print(f"[green]✓ Removed:[/green] {removed}")
    else:
        artifacts_dir = project_root / ".agentic-beacon" / "artifacts"
        console.print(f"[yellow]No artifacts found at {artifacts_dir}[/yellow]")


@click.command()
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

    config_file = beacon_dir / "config.toml"
    if config_file.exists():
        try:
            warehouse_settings = WorkspaceConfig()
            console.print(
                f"[blue]Warehouse:[/blue] {warehouse_settings.warehouse.local_path}"
            )
        except Exception:
            console.print(f"[blue]Config:[/blue] {config_file}")

    if not artifacts_dir.exists():
        console.print("\n[yellow]No artifacts synced yet.[/yellow]")
        console.print("Run 'abc sync' to download artifacts from warehouse.")
        show_bundled_skills_status()
        sys.exit(0)

    if beacon_yaml.exists():
        beacon_settings = BeaconManifest.from_yaml(beacon_yaml)

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

    show_bundled_skills_status()

    file_count = count_synced_files(project_root)
    console.print(f"[blue]Artifacts location:[/blue] {artifacts_dir}")
    console.print(f"[blue]Total synced files:[/blue] {file_count}")
