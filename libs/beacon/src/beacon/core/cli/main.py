"""Main Click group and top-level subcommands for the abc CLI."""

import sys
from pathlib import Path

import click
from loguru import logger
from rich.console import Console
from rich.table import Table

from beacon.core.cli.warehouse import warehouse
from beacon.core.delta import DeltaComparator
from beacon.core.manifest.beacon import BeaconManifest
from beacon.core.manifest.workspace import WorkspaceConfig
from beacon.core.sync import SyncEngine
from beacon.utils.agents import (
    _build_agents_paths,
    _detect_agents,
    _detect_agents_global,
    _global_agent_dirs,
    _handle_install_agent,
    _install_agent_global,
    _list_global_agents,
    _sync_agents_from_warehouse,
    _update_agent_gitignores,
)
from beacon.utils.contribute import (
    _auto_git_contribute,
    _contribute_all,
    _contribute_single,
    _print_contribute_next_steps,
)
from beacon.utils.delta import (
    _show_delta_summary,
    _show_detailed_diff,
)
from beacon.utils.display import (
    _handle_soft_block,
    _print_doctor_summary,
)
from beacon.utils.git import (
    _check_warehouse_git_clean,
    _check_warehouse_on_main_branch,
    find_project_root,
)
from beacon.utils.skills import (
    _build_skills_paths,
    _install_bundled_skills_globally,
    _normalize_skill_entry,
    _print_bundled_install_result,
    _print_skill_next_steps,
    _show_bundled_skills_status,
    _skill_name_from_entry,
    _update_beacon_yaml,
    _validate_skill_entries,
    _wire_single_skill,
    _wire_skills_post_sync,
)
from beacon.utils.sync_state import (
    _check_sync_state,
    _read_sync_sha,
    _relink_global_sync_state,
    _write_sync_state,
)
from beacon.utils.wiring import (
    _confirm_prune,
    _create_beacon_template,
    _init_claude_md,
    _init_opencode_json,
    _install_project_setup_skill,
    _is_interactive,
    _unwire_pruned_artifacts,
    _wire_contexts_claudecode,
    _wire_contexts_opencode,
)

console = Console()


@click.group()
@click.version_option(package_name="agentic-beacon")
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
def main(*, verbose: bool) -> None:
    """Agentic Beacon CLI (abc) - Guide your agents with distributed knowledge."""
    if verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.remove()
        logger.add(sys.stderr, level="INFO")


main.add_command(warehouse)


@main.command()
@click.option(
    "--manual",
    is_flag=True,
    help="Create empty beacon.yaml template without interactive prompts",
)
@click.option(
    "--agent-assisted",
    is_flag=True,
    help="Install project-setup skill for agent-assisted configuration",
)
def setup(*, manual: bool, agent_assisted: bool) -> None:
    """
    Initialize project artifact configuration.

    Creates beacon.yaml file that declares which artifacts this project uses.
    Supports three workflows: agent-assisted, manual, or skip.

    Example:
        abc setup --manual  # Create empty template
        abc setup           # Interactive mode
    """
    if manual and agent_assisted:
        console.print(
            "[red]Error:[/red] --manual and --agent-assisted are mutually exclusive"
        )
        sys.exit(1)

    beacon_dir = Path.cwd() / ".agentic-beacon"
    if not beacon_dir.exists():
        console.print("[red]Error:[/red] No warehouse connected.")
        console.print("Run 'abc warehouse connect' first to connect to a warehouse.")
        sys.exit(1)

    config_file = beacon_dir / "config.toml"
    if not config_file.exists():
        console.print("[red]Error:[/red] No warehouse connected.")
        console.print("Run 'abc warehouse connect --path <warehouse>' first.")
        sys.exit(1)

    beacon_yaml = beacon_dir / "beacon.yaml"

    if beacon_yaml.exists():
        console.print("[yellow]Note:[/yellow] beacon.yaml already exists")
        if not click.confirm("Overwrite existing configuration?", default=False):
            console.print("Setup cancelled.")
            sys.exit(0)

    workflow = None
    if manual:
        workflow = "manual"
    elif agent_assisted:
        workflow = "agent-assisted"
    else:
        console.print("\n[bold]Setup Project Configuration[/bold]")
        console.print(
            "[dim]Choose how to configure artifacts for this project:[/dim]\n"
        )
        console.print(
            "  1. [cyan]Agent-assisted[/cyan] - Install project-setup skill for AI agent"
        )
        console.print(
            "  2. [green]Manual[/green] - Create empty template to edit yourself"
        )
        console.print("  3. [yellow]Skip[/yellow] - Configure later\n")

        choice = click.prompt(
            "Select workflow",
            type=click.Choice(["1", "2", "3"], case_sensitive=False),
            default="2",
        )

        if choice == "1":
            workflow = "agent-assisted"
        elif choice == "2":
            workflow = "manual"
        else:
            console.print("Skipped setup. Run 'abc setup' again when ready.")
            sys.exit(0)

    if workflow == "manual":
        _create_beacon_template(beacon_yaml)
        console.print("\n[bold green]✓ Created beacon.yaml template[/bold green]")
        console.print(f"  [blue]Location:[/blue] {beacon_yaml}")
        console.print("\n[bold]Next Steps:[/bold]")
        console.print("  1. Edit .agentic-beacon/beacon.yaml to specify artifacts")
        console.print("  2. Run 'abc sync' to download artifacts from warehouse")
        console.print("\n[bold]Artifact Types:[/bold]")
        console.print(
            "  • [cyan]knowledge[/cyan], [cyan]contexts[/cyan], [cyan]skills[/cyan] — project-scoped, tracked in beacon.yaml"
        )
        console.print(
            "  • [magenta]agents[/magenta] — globally installed on your machine (not in beacon.yaml)"
        )
        console.print(
            "    Agent definitions are installed globally — use [bold]abc install agents/<name>[/bold] to install them"
        )

    elif workflow == "agent-assisted":
        _create_beacon_template(beacon_yaml)
        _install_project_setup_skill(beacon_dir)
        console.print("\n[bold green]✓ Agent-assisted setup ready[/bold green]")
        console.print(f"  [blue]beacon.yaml:[/blue] {beacon_yaml}")
        console.print(f"  [blue]Catalog:[/blue] {beacon_dir / 'warehouse-catalog.md'}")
        console.print("\n[bold]Paste this into your agent:[/bold]")
        console.print(
            "\n[on dark_green] Read `.agentic-beacon/warehouse-catalog.md` to see "
            "what artifacts are available in the connected warehouse. Analyse this "
            "project, then update `.agentic-beacon/beacon.yaml` with the artifacts "
            "that are relevant. Run `abc sync` when done. [/on dark_green]\n"
        )


@main.command()
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
            git_error = _check_warehouse_git_clean(warehouse_path)
            if git_error:
                console.print(f"[red]Error:[/red] {git_error}")
                sys.exit(1)

        if not dry_run and not skip_git_check:
            branch_error = _check_warehouse_on_main_branch(warehouse_path)
            if branch_error:
                console.print(f"[red]Error:[/red] {branch_error}")
                sys.exit(1)

        beacon_settings = BeaconManifest.from_yaml(beacon_yaml)

        _validate_skill_entries(beacon_settings)

        total_artifacts = (
            len(beacon_settings.artifacts.knowledge)
            + len(beacon_settings.artifacts.skills)
            + len(beacon_settings.artifacts.contexts)
        )

        if total_artifacts == 0:
            console.print(
                "[yellow]No artifacts configured in beacon.yaml. Nothing to sync.[/yellow]"
            )
            _print_bundled_install_result(*_install_bundled_skills_globally())
            _sync_agents_from_warehouse(warehouse_path, force=force, preserve=preserve)
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
                    skill_dir_entry = _normalize_skill_entry(pattern)
                    matches = sync_engine.expand_glob(f"{skill_dir_entry}/**/*")
                    if matches:
                        artifact_paths.extend(matches)
                    else:
                        console.print(
                            f"  [yellow]Warning:[/yellow] No files found for skill: "
                            f"{_skill_name_from_entry(pattern)}"
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

        old_sync_sha = _read_sync_sha(artifacts_dir)

        if not dry_run:
            _write_sync_state(artifacts_dir, warehouse_path)

        if not dry_run:
            conflicts = sync_engine.classify_conflicts(artifact_paths)
            overwrite = _handle_soft_block(conflicts, force=force, preserve=preserve)
            if not overwrite and conflicts:
                preserve = True

        orphans = sync_engine.classify_orphans(artifact_paths)
        confirmed_prune: list[str] = []
        if orphans:
            confirmed_prune = _confirm_prune(orphans, dry_run=dry_run)

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
            _unwire_pruned_artifacts(project_root, summary.pruned_paths, artifacts_dir)

        if beacon_settings.artifacts.contexts:
            oc_added = _wire_contexts_opencode(project_root, artifacts_dir)
            if oc_added:
                console.print(
                    f"\n[green]✓[/green] Wired {len(oc_added)} context(s) into opencode.json"
                )

            cc_added = _wire_contexts_claudecode(project_root, artifacts_dir)
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
                    if not dry_run and _is_interactive():
                        console.print(
                            "\n[yellow]No agent config detected.[/yellow] "
                            "Set one up to wire contexts automatically."
                        )
                        if click.confirm("  Initialize opencode.json?", default=False):
                            _init_opencode_json(project_root)
                            oc_init = _wire_contexts_opencode(
                                project_root, artifacts_dir
                            )
                            if oc_init:
                                console.print(
                                    f"[green]✓[/green] Created opencode.json and "
                                    f"wired {len(oc_init)} context(s)"
                                )
                        if click.confirm("  Initialize CLAUDE.md?", default=False):
                            _init_claude_md(project_root)
                            cc_init = _wire_contexts_claudecode(
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
            wired_skills, wire_errors = _wire_skills_post_sync(
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

            _update_agent_gitignores(project_root)

        if wiring_notes:
            console.print("\n[bold]Manual wiring required:[/bold]")
            for note in wiring_notes:
                console.print(note)

        _print_bundled_install_result(*_install_bundled_skills_globally())

        _sync_agents_from_warehouse(warehouse_path, force=force, preserve=preserve)

        if old_sync_sha is not None:
            try:
                from beacon.adopt import _count_unadopted_since

                unadopted_count = _count_unadopted_since(
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


@main.group()
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
        _check_warehouse_git_clean(warehouse_path)
        _check_warehouse_on_main_branch(warehouse_path)

    _sync_agents_from_warehouse(warehouse_path, force=force, preserve=preserve)


@main.command(name="install")
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
        _handle_install_agent(artifact.rstrip("/"), force=force, preserve=preserve)
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
    overwrite = _handle_soft_block(conflicts, force=force, preserve=preserve)
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
        _update_beacon_yaml(beacon_dir, files_to_copy)

    artifact_type = Path(artifact).parts[0] if Path(artifact).parts else ""
    project_root = Path.cwd()
    detected_agents = (
        _detect_agents(project_root, fallback_to_all=True)
        if not agent
        else [agent.lower()]
    )

    if artifact_type == "skills":
        skill_name = _skill_name_from_entry(artifact)
        skill_src_dir = artifacts_dir / "skills" / skill_name
        if skill_src_dir.exists() and detected_agents:
            for target_agent in detected_agents:
                _wire_single_skill(
                    project_root, skill_name, skill_src_dir, target_agent
                )
            console.print(f"[green]✓[/green] Installed skill: {skill_name}")
            _update_agent_gitignores(project_root)
            _print_skill_next_steps(detected_agents)
        elif skill_src_dir.exists():
            console.print(
                "[green]✓[/green] Skill copied (no agent detected for wiring)"
            )
        else:
            console.print(
                f"[green]✓[/green] Artifact copied ({len(files_to_copy)} file(s))"
            )

    elif artifact_type == "contexts":
        wired_opencode = _wire_contexts_opencode(project_root, artifacts_dir)
        wired_claudecode = _wire_contexts_claudecode(project_root, artifacts_dir)
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


@main.command()
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

        _relink_global_sync_state(warehouse_path)

        project_root = Path.cwd()

        comparator = DeltaComparator(
            warehouse_path=warehouse_path,
            artifacts_path=artifacts_dir,
            skills_paths=_build_skills_paths(project_root),
            agents_paths=_build_agents_paths(),
        )

        if file:
            _show_detailed_diff(comparator, beacon_settings, file, no_color)
        else:
            _show_delta_summary(
                comparator, beacon_settings, warehouse_path, project_root
            )

    except Exception as e:
        console.print(f"\n[red]Error:[/red] Delta comparison failed: {e}")
        logger.exception("Delta comparison failed")
        sys.exit(1)


@main.command()
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
            git_error = _check_warehouse_git_clean(warehouse_path)
            if git_error:
                console.print(f"[red]Error:[/red] {git_error}")
                sys.exit(1)

        artifacts_dir = beacon_dir / "artifacts"

        if not dry_run and not skip_git_check:
            sync_error = _check_sync_state(artifacts_dir, warehouse_path)
            if sync_error:
                console.print(f"[yellow]Warning:[/yellow] {sync_error}")
                sys.exit(1)

        beacon_settings = BeaconManifest.from_yaml(beacon_yaml)
        project_root = Path.cwd()
        comparator = DeltaComparator(
            warehouse_path=warehouse_path,
            artifacts_path=artifacts_dir,
            skills_paths=_build_skills_paths(project_root),
            agents_paths=_build_agents_paths(),
        )
        ignore_skill_patterns = beacon_settings.ignore.skills

        if dry_run:
            console.print("[dim]Dry run — no files will be copied.[/dim]\n")

        if file:
            if not dry_run:
                console.print("[dim]Preview:[/dim]\n")
                preview = _contribute_single(
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
            contributed = _contribute_single(
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
                preview = _contribute_all(
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
            contributed = _contribute_all(
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
                _print_contribute_next_steps(
                    warehouse_path, [p for p, _ in contributed]
                )
            else:
                _auto_git_contribute(warehouse_path, contributed)

    except Exception as e:
        console.print(f"\n[red]Error:[/red] Contribute failed: {e}")
        logger.exception("Contribute failed")
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
            normalized = _normalize_skill_entry(skill_entry)
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


@main.command(name="reset")
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


@main.command(name="update", hidden=True)
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


@main.command(name="list")
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
        _list_global_agents()
        return

    beacon_dir = Path.cwd() / ".agentic-beacon"
    artifacts_dir = beacon_dir / "artifacts"

    if not artifacts_dir.exists():
        console.print("[red]Error:[/red] No synced artifacts found.")
        console.print("Run 'abc sync' to download artifacts from the warehouse.")
        sys.exit(1)

    types_to_show = (
        [artifact_type] if artifact_type else ["contexts", "knowledge", "skills"]
    )

    section_config = {
        "contexts": ("Synced Contexts", "cyan", "Context"),
        "knowledge": ("Synced Knowledge", "green", "File"),
        "skills": ("Synced Skills", "yellow", "Skill"),
    }

    any_shown = False
    for section in types_to_show:
        section_dir = artifacts_dir / section
        if not section_dir.exists():
            continue

        files = sorted(
            str(f.relative_to(artifacts_dir))
            for f in section_dir.rglob("*")
            if f.is_file() and not f.name.startswith(".")
        )

        if files:
            title, color, col_name = section_config[section]
            table = Table(title=title)
            table.add_column(col_name, style=color)
            for item in files:
                table.add_row(item)
            console.print(table)
            console.print()
            any_shown = True

    if not any_shown:
        label = artifact_type or "artifacts"
        console.print(
            f"[yellow]No {label} found in .agentic-beacon/artifacts/.[/yellow]"
        )
        console.print("Run 'abc sync' to download artifacts from the warehouse.")


@main.command()
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


@main.command()
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
        _show_bundled_skills_status()
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

    _show_bundled_skills_status()

    import os as _os

    file_count = sum(len(files) for _, _, files in _os.walk(str(artifacts_dir)))
    console.print(f"[blue]Artifacts location:[/blue] {artifacts_dir}")
    console.print(f"[blue]Total synced files:[/blue] {file_count}")


@main.command()
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview adoptable artifacts without modifying beacon.yaml.",
)
def adopt(*, dry_run: bool) -> None:
    """Adopt warehouse artifacts into beacon.yaml.

    Shows all unadopted artifacts by default. Press ``t`` in the TUI to toggle
    to a full view where you can also unadopt currently adopted artifacts.
    Artifacts added within the last few commits are tagged with how recent they are.
    """
    from beacon.adopt import (
        AdoptApp,
        AdoptCandidate,
        _is_agent_installed,
        apply_adoption,
        cleanup_unadopted_artifacts,
        discover_adoptable,
    )

    project_root = find_project_root()
    beacon_dir = project_root / ".agentic-beacon"
    artifacts_dir = beacon_dir / "artifacts"
    beacon_yaml = beacon_dir / "beacon.yaml"

    if not beacon_dir.exists():
        console.print(f"[red]Error:[/red] No warehouse connected at {project_root}")
        console.print("Run 'abc warehouse connect' first.")
        sys.exit(1)

    if not beacon_yaml.exists():
        console.print("[red]Error:[/red] No beacon.yaml found.")
        console.print("Run 'abc setup' to create artifact configuration.")
        sys.exit(1)

    try:
        warehouse_settings = WorkspaceConfig()
        warehouse_path = Path(warehouse_settings.warehouse.local_path)
    except Exception:
        console.print("[red]Error:[/red] Could not read warehouse connection settings.")
        console.print("Run 'abc warehouse connect' to connect to a warehouse.")
        sys.exit(1)

    beacon_settings = BeaconManifest.from_yaml(beacon_yaml)

    candidates, _ = discover_adoptable(warehouse_path, beacon_settings)

    if not candidates:
        console.print("[green]✓[/green] No unadopted warehouse artifacts found.")
        return

    if dry_run:
        table = Table(title="Unadopted Artifacts")
        table.add_column("Type", style="cyan")
        table.add_column("Path", style="white")
        table.add_column("Description", style="dim")
        table.add_column("Recently Added", style="yellow")

        for c in candidates:
            recently = (
                f"{c.commits_ago} commit{'s' if c.commits_ago != 1 else ''} ago"
                if c.commits_ago is not None
                else ""
            )
            table.add_row(c.artifact_type, c.path, c.description, recently)

        console.print(table)
        console.print("\n[dim]Run without --dry-run to interactively adopt.[/dim]")
        return

    if not _is_interactive():
        console.print("[bold]Unadopted artifacts:[/bold]")
        for c in candidates:
            desc = f" — {c.description}" if c.description else ""
            tag = (
                f" [added {c.commits_ago} commits ago]"
                if c.commits_ago is not None
                else ""
            )
            console.print(f"  [{c.artifact_type}] {c.path}{desc}{tag}")
        console.print(
            "\n[dim]Non-interactive mode. Edit beacon.yaml manually to adopt artifacts, "
            "then run [bold]abc sync[/bold].[/dim]"
        )
        return

    adopted_paths: list[str] = (
        beacon_settings.artifacts.contexts
        + beacon_settings.artifacts.skills
        + beacon_settings.artifacts.knowledge
    )
    try:
        from beacon.distributor import WarehouseDistributor

        distributor = WarehouseDistributor(
            warehouse_root=warehouse_path, target_root=warehouse_path
        )
        available_agents = distributor.list_available().get("agents", [])
        adopted_paths += [p for p in available_agents if _is_agent_installed(p)]
    except Exception:
        pass

    app = AdoptApp(
        candidates,
        adopted_paths,
        project_name=project_root.name,
        warehouse_name=warehouse_path.name,
    )
    result = app.run()

    if not result.to_adopt and not result.to_unadopt:
        console.print("[dim]No changes made.[/dim]")
        return

    path_to_candidate: dict[str, AdoptCandidate] = {c.path: c for c in candidates}
    agent_adoptions = [p for p in result.to_adopt if p.startswith("agents/")]
    non_agent_selections = [
        path_to_candidate[p]
        for p in result.to_adopt
        if p in path_to_candidate and not p.startswith("agents/")
    ]
    agent_unadoptions = [p for p in result.to_unadopt if p.startswith("agents/")]
    non_agent_unadoptions = [
        p for p in result.to_unadopt if not p.startswith("agents/")
    ]

    apply_adoption(beacon_yaml, non_agent_selections, unadoptions=non_agent_unadoptions)
    if non_agent_selections:
        console.print(
            f"[green]✓[/green] Added {len(non_agent_selections)} artifact(s) to beacon.yaml"
        )
    if non_agent_unadoptions:
        console.print(
            f"[yellow]−[/yellow] Removed {len(non_agent_unadoptions)} artifact(s) from beacon.yaml"
        )

    if agent_adoptions:
        tools = _detect_agents_global()
        installed_count = 0
        for agent_path in agent_adoptions:
            agent_file = warehouse_path / agent_path
            if not agent_file.exists():
                continue
            content = agent_file.read_text(encoding="utf-8")
            agent_name = agent_file.name
            for tool in tools:
                _install_agent_global(tool, agent_name, content)
            installed_count += 1
        if installed_count:
            console.print(
                f"[green]✓[/green] Installed {installed_count} agent(s) globally"
                + (f" for: {', '.join(tools)}" if tools else "")
            )

    if agent_unadoptions:
        removed_count = 0
        for agent_path in agent_unadoptions:
            agent_name = Path(agent_path).name
            for agent_dir in _global_agent_dirs().values():
                target = agent_dir / agent_name
                if target.exists():
                    target.unlink()
                    removed_count += 1
        if removed_count:
            console.print(
                f"[yellow]−[/yellow] Uninstalled {removed_count} agent(s) from global directories"
            )

    if non_agent_selections:
        try:
            sync_engine = SyncEngine(
                warehouse_path=warehouse_path,
                artifacts_path=artifacts_dir,
            )

            new_artifact_paths: list[str] = []
            for c in non_agent_selections:
                if c.artifact_type == "skills":
                    new_artifact_paths.append(c.path.rstrip("/") + "/")
                else:
                    new_artifact_paths.append(c.path)

            expanded: list[str] = []
            for pattern in new_artifact_paths:
                if "*" in pattern or "?" in pattern:
                    import glob as glob_mod

                    matches = [
                        str(Path(p).relative_to(warehouse_path))
                        for p in glob_mod.glob(
                            str(warehouse_path / pattern), recursive=True
                        )
                        if Path(p).is_file()
                    ]
                    expanded.extend(matches)
                elif pattern.endswith("/"):
                    skill_dir = warehouse_path / pattern.rstrip("/")
                    if skill_dir.is_dir():
                        for f in skill_dir.rglob("*"):
                            if f.is_file():
                                expanded.append(str(f.relative_to(warehouse_path)))
                elif (warehouse_path / pattern).is_dir():
                    for f in (warehouse_path / pattern).rglob("*.md"):
                        if f.is_file():
                            expanded.append(str(f.relative_to(warehouse_path)))
                else:
                    expanded.append(pattern)

            if expanded:
                sync_engine.sync_all(
                    artifact_paths=expanded,
                    preserve=False,
                    dry_run=False,
                )
                console.print(
                    f"[green]✓[/green] Synced and wired: "
                    f"{', '.join(c.path for c in non_agent_selections)}"
                )

                for c in non_agent_selections:
                    if c.artifact_type == "contexts":
                        _wire_contexts_opencode(project_root, artifacts_dir)
                        _wire_contexts_claudecode(project_root, artifacts_dir)
                        break

                has_skills = any(
                    c.artifact_type == "skills" for c in non_agent_selections
                )
                if has_skills:
                    _wire_skills_post_sync(project_root, artifacts_dir)

        except Exception as e:
            console.print(
                f"[yellow]⚠[/yellow] Post-adoption sync failed: {e}\n"
                "  Run [bold]abc sync[/bold] to sync and wire adopted artifacts."
            )

    if non_agent_unadoptions:
        cleanup_unadopted_artifacts(
            non_agent_unadoptions, artifacts_dir, warehouse_path
        )


@main.command()
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
    from beacon.adopt import _find_knowledge_node_for_file, _is_knowledge_node

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
        _print_doctor_summary(issues, fixes_applied)
        return

    knowledge_entries: list[str] = list(beacon_settings.artifacts.knowledge)
    skill_entries: list[str] = list(beacon_settings.artifacts.skills)
    context_entries: list[str] = list(beacon_settings.artifacts.contexts)

    file_level: list[tuple[str, str | None]] = []
    for entry in knowledge_entries:
        if entry.endswith(".md") or any(
            seg in entry.split("/") for seg in ("decisions", "lessons", "facts")
        ):
            node = _find_knowledge_node_for_file(entry)
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
                    node = _find_knowledge_node_for_file(entry)
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
            elif not _is_knowledge_node(node_dir):
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

    _print_doctor_summary(issues, fixes_applied)


if __name__ == "__main__":
    main()
