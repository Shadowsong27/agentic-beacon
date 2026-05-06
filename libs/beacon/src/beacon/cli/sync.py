"""Sync-related commands for the abc CLI."""

import sys
from pathlib import Path

import click
from loguru import logger
from rich.console import Console

from beacon.core.exceptions import BeaconSyncError, DependencyError, ResetError
from beacon.core.manifest.beacon import BeaconManifest
from beacon.core.manifest.workspace import WorkspaceConfig
from beacon.domains.artifact.skill import (
    print_bundled_install_result,
    show_bundled_skills_status,
)
from beacon.domains.distribution.orchestrator import run_sync
from beacon.domains.distribution.reset import (
    count_synced_files,
    remove_artifacts_dir,
    reset_artifacts,
)
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
@click.option(
    "--force", is_flag=True, help="Overwrite conflicting files without prompting"
)
@click.option(
    "--verbose", "verbose_flag", is_flag=True, help="Show detailed sync output"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would be synced without making changes",
)
@click.option(
    "--skip-git-check",
    is_flag=True,
    help="Skip warehouse uncommitted-changes check",
)
@click.option(
    "--contribute-local",
    is_flag=True,
    help="Non-interactive: contribute all modified local files to warehouse",
)
@click.option(
    "--discard-local",
    is_flag=True,
    help="Non-interactive: discard all modified local files and replace with symlinks",
)
@click.option(
    "--yes",
    is_flag=True,
    help="Auto-accept adding missing agent-required skills to beacon.yaml",
)
def sync(
    *,
    force: bool,
    verbose_flag: bool,
    dry_run: bool,
    skip_git_check: bool,
    contribute_local: bool,
    discard_local: bool,
    yes: bool,
) -> None:
    """
    Sync artifacts from warehouse to project.

    Reads .agentic-beacon/beacon.yaml and creates symlinks under
    .agentic-beacon/artifacts/ pointing to the connected warehouse.

    Example:
        abc sync              # Sync all artifacts
        abc sync --force      # Overwrite all conflicts without prompting
        abc sync --verbose    # Show detailed output
        abc sync --dry-run    # Preview without making changes
    """
    if dry_run:
        console.print("[dim]Dry run — no files will be changed.[/dim]\n")

    console.print("\n[blue]Syncing artifacts from warehouse...[/blue]\n")

    def log_fn(msg: str) -> None:
        console.print(f"  {msg}")

    def _resolve(rel_path: str, diff: str) -> str:
        console.print(f"\nModified file: {rel_path}")
        if diff:
            console.print(diff)
        choice = click.prompt(
            "[c]ontribute / [d]iscard / [s]kip",
            type=click.Choice(["c", "d", "s"], case_sensitive=False),
            default="s",
        )
        return {"c": "contribute", "d": "discard", "s": "skip"}[choice.lower()]

    def _resolve_skill_conflicts(conflict_paths: list[str]) -> bool:
        """Prompt the user when live skill files differ from the warehouse.

        Returns True to overwrite (install warehouse symlinks), False to
        preserve local copies. Used by run_sync when neither --force nor
        --preserve are supplied and an interactive terminal is attached.
        """
        files_list = "\n".join(f"    • {p}" for p in conflict_paths)
        console.print(
            f"\n[yellow]Warning:[/yellow] {len(conflict_paths)} live skill "
            f"file(s) differ from the warehouse (typically leftover copies "
            f"from an older abc version):\n{files_list}\n"
        )
        return click.confirm(
            "Overwrite local skill file(s) with warehouse symlinks?",
            default=True,
        )

    def _gap_prompt(gap) -> bool:
        msg = (
            f"\nAgent '{gap.requiring_agent}' (declared in beacon.yaml) "
            f"requires skill '{gap.missing_skill}', "
            f"which is not declared in this project.\n\n"
            f"Add 'skills/{gap.missing_skill}/' to beacon.yaml and sync it?"
        )
        return click.confirm(msg, default=False)

    try:
        result = run_sync(
            force=force,
            verbose=verbose_flag,
            dry_run=dry_run,
            skip_git_check=skip_git_check,
            contribute_local=contribute_local,
            discard_local=discard_local,
            log_fn=log_fn if (verbose_flag or dry_run) else None,
            resolve_callback=_resolve if is_interactive() else None,
            skill_conflict_callback=(
                _resolve_skill_conflicts if is_interactive() else None
            ),
            auto_accept_gaps=yes,
            gap_prompt_callback=_gap_prompt if is_interactive() else None,
        )
    except DependencyError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
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

    action_word = "Would create" if result.dry_run else "Created"
    done_label = "Dry run complete" if result.dry_run else "Sync complete"
    console.print(f"\n[bold green]✓ {done_label}[/bold green]")
    console.print(f"  [blue]{action_word}:[/blue] {result.summary.created} symlinks")
    console.print(f"  [blue]Up to date:[/blue] {result.summary.skipped} symlinks")
    if result.summary.updated > 0:
        console.print(
            f"  [yellow]{'Would update' if result.dry_run else 'Updated'}:[/yellow] "
            f"{result.summary.updated} symlinks"
        )
    if result.dry_run and result.orphans:
        console.print(
            f"  [yellow]Would remove:[/yellow] {len(result.orphans)} orphan symlink(s) "
            f"no longer in beacon.yaml"
        )
    elif result.summary.removed > 0:
        console.print(
            f"  [yellow]Removed:[/yellow] "
            f"{result.summary.removed} orphan symlink(s) no longer in beacon.yaml"
        )
    if result.summary.errors > 0:
        console.print(f"  [red]Errors:[/red] {result.summary.errors} files")
        for path, msg in result.summary.failed_files:
            console.print(f"    [red]✗[/red] {path}: {msg}")

    if result.unresolved_files:
        console.print(
            f"\n[red]{len(result.unresolved_files)} file(s) require resolution:[/red]"
        )
        for path in result.unresolved_files:
            console.print(f"  • {path}")
        console.print(
            "\n  [dim]Run with --contribute-local or --discard-local to resolve automatically,"
            " or run interactively to choose per file.[/dim]"
        )
        sys.exit(1)

    if result.migration_resolved:
        console.print("\n[bold]Migration resolved:[/bold]")
        for path, action in result.migration_resolved.items():
            console.print(f"  {path}: {action}")

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
            from rich.table import Table

            table = Table(title="Configured Contexts")
            table.add_column("Context", style="cyan")
            for ctx in beacon_settings.artifacts.contexts:
                synced = (artifacts_dir / ctx).exists()
                status_str = "[green]✓[/green]" if synced else "[red]✗[/red]"
                table.add_row(f"{status_str} {ctx}")
            console.print(table)
            console.print()

        if beacon_settings.artifacts.skills:
            from rich.table import Table

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
