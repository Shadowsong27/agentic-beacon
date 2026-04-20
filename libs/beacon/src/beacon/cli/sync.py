"""Sync-related commands for the abc CLI."""

import sys
from pathlib import Path

import click
from loguru import logger
from rich.console import Console
from rich.table import Table

from beacon.core.manifest.beacon import BeaconManifest
from beacon.core.manifest.workspace import WorkspaceConfig
from beacon.domains.artifact.agent import (
    build_agents_paths,
    sync_agents_from_warehouse,
    update_agent_gitignores,
)
from beacon.domains.artifact.skill import (
    build_skills_paths,
    install_bundled_skills_globally,
    normalize_skill_entry,
    print_bundled_install_result,
    show_bundled_skills_status,
    skill_name_from_entry,
    validate_skill_entries,
    wire_skills_post_sync,
)
from beacon.domains.contribution.delta_view import (
    show_delta_summary,
    show_detailed_diff,
)
from beacon.domains.distribution.delta import DeltaComparator
from beacon.domains.distribution.state import (
    read_sync_sha,
    relink_global_sync_state,
    write_sync_state,
)
from beacon.domains.distribution.sync_engine import SyncEngine
from beacon.domains.setup.wiring import (
    confirm_prune,
    init_claude_md,
    init_opencode_json,
    is_interactive,
    unwire_pruned_artifacts,
    wire_contexts_claudecode,
    wire_contexts_opencode,
)
from beacon.utils.display import handle_soft_block
from beacon.utils.git import (
    check_warehouse_git_clean,
    check_warehouse_on_main_branch,
    find_project_root,
)

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
            console.print("The warehouse may have been moved or deleted.")
            console.print(
                "Run 'abc warehouse connect --path <warehouse>' to reconnect."
            )
            sys.exit(1)

        if not dry_run and not skip_git_check:
            git_error = check_warehouse_git_clean(warehouse_path)
            if git_error:
                console.print(f"[red]Error:[/red] {git_error}")
                sys.exit(1)

        if not dry_run and not skip_git_check:
            branch_error = check_warehouse_on_main_branch(warehouse_path)
            if branch_error:
                console.print(f"[red]Error:[/red] {branch_error}")
                sys.exit(1)

        beacon_settings = BeaconManifest.from_yaml(beacon_yaml)

        validate_skill_entries(beacon_settings)

        total_artifacts = (
            len(beacon_settings.artifacts.knowledge)
            + len(beacon_settings.artifacts.skills)
            + len(beacon_settings.artifacts.contexts)
        )

        if total_artifacts == 0:
            console.print(
                "[yellow]No artifacts configured in beacon.yaml. Nothing to sync.[/yellow]"
            )
            print_bundled_install_result(*install_bundled_skills_globally())
            sync_agents_from_warehouse(warehouse_path, force=force, preserve=preserve)
            sys.exit(0)

        artifacts_dir = beacon_dir / "artifacts"
        artifacts_dir.mkdir(exist_ok=True)

        sync_engine = SyncEngine(
            warehouse_path=warehouse_path, artifacts_path=artifacts_dir
        )

        if dry_run:
            console.print("[dim]Dry run — no files will be copied or pruned.[/dim]\n")

        artifact_paths = []
        console.print("\n[blue]Syncing artifacts from warehouse...[/blue]\n")

        for artifact_type in ["knowledge", "skills", "contexts"]:
            artifacts_list = getattr(beacon_settings.artifacts, artifact_type)
            for pattern in artifacts_list:
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
                elif artifact_type == "skills":
                    skill_dir_entry = normalize_skill_entry(pattern)
                    matches = sync_engine.expand_glob(f"{skill_dir_entry}/**/*")
                    if matches:
                        artifact_paths.extend(matches)
                    else:
                        console.print(
                            f"  [yellow]Warning:[/yellow] No files found for skill: "
                            f"{skill_name_from_entry(pattern)}"
                        )
                elif (
                    artifact_type == "knowledge" and (warehouse_path / pattern).is_dir()
                ):
                    matches = sync_engine.expand_glob(f"{pattern}/**/*.md")
                    if matches:
                        artifact_paths.extend(matches)
                    else:
                        console.print(
                            f"  [yellow]Warning:[/yellow] No .md files found under: {pattern}"
                        )
                else:
                    artifact_paths.append(pattern)

        old_sync_sha = read_sync_sha(artifacts_dir)

        if not dry_run:
            write_sync_state(artifacts_dir, warehouse_path)

        if not dry_run:
            conflicts = sync_engine.classify_conflicts(artifact_paths)
            overwrite = handle_soft_block(conflicts, force=force, preserve=preserve)
            if not overwrite and conflicts:
                preserve = True

        orphans = sync_engine.classify_orphans(artifact_paths)
        confirmed_prune: list[str] = []
        if orphans:
            confirmed_prune = confirm_prune(orphans, dry_run=dry_run)

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

        if not dry_run:
            from beacon.core.gitignore import GitignoreManager

            gitignore_mgr = GitignoreManager(Path.cwd())
            gitignore_mgr.ensure_entries()

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

        project_root = Path.cwd()
        wiring_notes: list[str] = []

        if summary.pruned_paths:
            unwire_pruned_artifacts(project_root, summary.pruned_paths, artifacts_dir)

        if beacon_settings.artifacts.contexts:
            oc_added = wire_contexts_opencode(project_root, artifacts_dir)
            if oc_added:
                console.print(
                    f"\n[green]✓[/green] Wired {len(oc_added)} context(s) into opencode.json"
                )

            cc_added = wire_contexts_claudecode(project_root, artifacts_dir)
            if cc_added:
                console.print(
                    f"[green]✓[/green] Wired {len(cc_added)} context(s) into CLAUDE.md"
                )

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
                    if not dry_run and is_interactive():
                        console.print(
                            "\n[yellow]No agent config detected.[/yellow] "
                            "Set one up to wire contexts automatically."
                        )
                        if click.confirm("  Initialize opencode.json?", default=False):
                            init_opencode_json(project_root)
                            oc_init = wire_contexts_opencode(
                                project_root, artifacts_dir
                            )
                            if oc_init:
                                console.print(
                                    f"[green]✓[/green] Created opencode.json and "
                                    f"wired {len(oc_init)} context(s)"
                                )
                        if click.confirm("  Initialize CLAUDE.md?", default=False):
                            init_claude_md(project_root)
                            cc_init = wire_contexts_claudecode(
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
            wired_skills, wire_errors = wire_skills_post_sync(
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

            update_agent_gitignores(project_root)

        if wiring_notes:
            console.print("\n[bold]Manual wiring required:[/bold]")
            for note in wiring_notes:
                console.print(note)

        print_bundled_install_result(*install_bundled_skills_globally())

        sync_agents_from_warehouse(warehouse_path, force=force, preserve=preserve)

        if old_sync_sha is not None:
            try:
                from beacon.domains.adoption.adopter import count_unadopted_since

                unadopted_count = count_unadopted_since(
                    warehouse_path, beacon_settings, old_sync_sha
                )
                if unadopted_count > 0:
                    console.print(
                        f"\n[cyan]{unadopted_count} new artifact(s) available "
                        f"-- run [bold]abc adopt[/bold] to review[/cyan]"
                    )
            except Exception:
                pass

    except Exception as e:
        console.print(f"\n[red]Error:[/red] Sync failed: {e}")
        logger.exception("Sync failed")
        sys.exit(1)


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
        warehouse_settings = WorkspaceConfig()
        warehouse_path = Path(warehouse_settings.warehouse.local_path)
        beacon_settings = BeaconManifest.from_yaml(beacon_dir / "beacon.yaml")

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

        for skill_entry in beacon_settings.artifacts.skills:
            normalized = normalize_skill_entry(skill_entry)
            skill_dir = warehouse_path / normalized
            if skill_dir.exists() and skill_dir.is_dir():
                artifact_paths.extend(sync_engine.expand_glob(f"{normalized}/**/*"))
            else:
                artifact_paths.append(normalized)

        copied_count = 0
        overwritten_count = 0
        error_count = 0

        for artifact_path in artifact_paths:
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
    _do_reset(project_root)


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
    project_root = project or find_project_root()
    _do_reset(project_root)


@click.command()
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

    import os as _os

    file_count = sum(len(files) for _, _, files in _os.walk(str(artifacts_dir)))
    console.print(f"[blue]Artifacts location:[/blue] {artifacts_dir}")
    console.print(f"[blue]Total synced files:[/blue] {file_count}")
