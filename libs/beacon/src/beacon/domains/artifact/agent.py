"""Agent operations for the artifact domain."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from beacon.domains.distribution.delta import ComparisonResult, DeltaComparator
from beacon.domains.distribution.state import (
    relink_global_sync_state,
    write_agent_sync_state,
)
from beacon.utils.display import is_interactive
from beacon.utils.git import hash_content

console = Console()

_ALL_KNOWN_AGENTS = ["opencode", "claudecode"]


def global_agent_dirs() -> dict[str, Path]:
    """Return global agent definition directories per tool."""
    return {
        "opencode": Path.home() / ".config" / "opencode" / "agents",
        "claudecode": Path.home() / ".claude" / "agents",
    }


def detect_agents_global() -> list[str]:
    """Detect which agent tools are available on this machine via home-dir paths.

    Checks only home-directory paths (not project-relative paths).
    Returns list of tool names: 'opencode' and/or 'claudecode'.
    """
    tools = []
    opencode_dir = Path.home() / ".config" / "opencode"
    if opencode_dir.is_dir():
        tools.append("opencode")
    claudecode_dir = Path.home() / ".claude"
    if claudecode_dir.is_dir():
        tools.append("claudecode")
    return tools


def read_agent_definition(agent_file: Path) -> str | None:
    """Read an agent definition file from the warehouse.

    Returns None if the file does not exist or cannot be read.
    """
    if not agent_file.exists():
        return None
    return agent_file.read_text(encoding="utf-8")


def detect_agents(project_root: Path, *, fallback_to_all: bool = False) -> list[str]:
    """Detect which agent tools are configured in the project.

    When fallback_to_all=True and no config files are found, returns all known
    agents so callers can wire unconditionally (e.g. skill installation).
    """
    agents = []
    if (project_root / "opencode.json").exists():
        agents.append("opencode")
    if (project_root / ".claude").exists() or (project_root / "CLAUDE.md").exists():
        agents.append("claudecode")
    if not agents and fallback_to_all:
        return list(_ALL_KNOWN_AGENTS)
    return agents


def build_agents_paths() -> dict[str, Path]:
    """Return a mapping of tool name → global agents directory for detected tools.

    This is the shared detection logic used by both `abc delta` and
    `abc contribute` so both commands always compare/read from the same
    global agent locations.
    """
    agents_paths: dict[str, Path] = {}
    for tool in detect_agents_global():
        if tool == "opencode":
            agents_paths["opencode"] = Path.home() / ".config" / "opencode" / "agents"
        elif tool == "claudecode":
            agents_paths["claudecode"] = Path.home() / ".claude" / "agents"
    return agents_paths


def install_agent_global(agent: str, agent_name: str, content: str) -> bool:
    """Write an agent definition file to the global agent directory for a tool.

    Creates parent dirs if needed.
    Returns True if the file was written, False if content was identical (skipped).
    Conflict handling is the caller's responsibility (soft block pre-check).

    Args:
        agent: Tool name — "opencode" or "claudecode".
        agent_name: Filename (e.g. "code-reviewer.md").
        content: File content to write.
    """
    agent_dirs = global_agent_dirs()
    dest = agent_dirs[agent] / agent_name
    if dest.exists() and dest.read_text(encoding="utf-8") == content:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    return True


def uninstall_agent_global(agent_name: str) -> int:
    """Remove an agent definition file from all global agent directories.

    Returns the number of directories from which the agent was removed.
    """
    removed_count = 0
    for agent_dir in global_agent_dirs().values():
        target = agent_dir / agent_name
        if target.exists():
            target.unlink()
            removed_count += 1
    return removed_count


def list_global_agents() -> None:
    """Display globally installed agent files from all detected tool directories."""
    agent_dirs = global_agent_dirs()

    # Union of all agent filenames across detected tools, deduplicated
    seen: dict[str, list[str]] = {}  # filename -> list of tools that have it
    for tool, agent_dir in agent_dirs.items():
        if not agent_dir.exists():
            continue
        for f in sorted(agent_dir.rglob("*.md")):
            if f.is_file() and not f.name.startswith("."):
                name = f.name
                seen.setdefault(name, []).append(tool)

    if not seen:
        console.print("[yellow]No agents found.[/yellow]")
        console.print("Install agents with: abc install agents/<name>.md")
        return

    table = Table(title="Installed Agents (Global)")
    table.add_column("Agent", style="magenta")
    table.add_column("Tools", style="dim")
    for name in sorted(seen):
        table.add_row(name, ", ".join(seen[name]))
    console.print(table)


def find_project_level_agents(project_root: Path) -> dict[str, list[str]]:
    """Return project-scoped agent files per tool that live outside the global dirs.

    Checks .claude/agents/ (Claude Code) and .opencode/agents/ (OpenCode) under
    the given project root.  Returns a mapping of tool name → sorted list of
    agent file names (README.md excluded).
    """
    project_agent_dirs: dict[str, Path] = {
        "claudecode": project_root / ".claude" / "agents",
        "opencode": project_root / ".opencode" / "agents",
    }
    result: dict[str, list[str]] = {}
    for tool, agents_dir in project_agent_dirs.items():
        if agents_dir.is_dir():
            files = sorted(
                f.name
                for f in agents_dir.iterdir()
                if f.is_file() and f.name != "README.md"
            )
            if files:
                result[tool] = files
    return result


def update_agent_gitignores(project_root: Path) -> None:
    """Add gitignore entries to agent subdirectory .gitignore files.

    Updates .claude/.gitignore and .opencode/.gitignore if those directories
    exist, creating the gitignore files if needed.
    """
    from beacon.core.gitignore import GitignoreManager

    claude_dir = project_root / ".claude"
    if claude_dir.is_dir():
        GitignoreManager(claude_dir).ensure_entries(["skills/"])

    opencode_dir = project_root / ".opencode"
    if opencode_dir.is_dir():
        GitignoreManager(opencode_dir).ensure_entries(["skills/", "command/"])


def sync_agents_from_warehouse(
    warehouse_path: Path,
    *,
    force: bool = False,
    preserve: bool = False,
) -> None:
    """Sync all agent definition files from the warehouse into global tool directories.

    Called as part of `abc sync`. Finds every *.md under warehouse/agents/,
    compares each against the global agent dirs for detected tools, and installs
    any that are out-of-date.  A single Y/N prompt is shown when conflicts exist
    (unless --force or --preserve are supplied).

    Args:
        warehouse_path: Absolute path to the connected warehouse root.
        force: Overwrite conflicting files without prompting.
        preserve: Skip conflicting files without prompting.
    """
    agents_dir = warehouse_path / "agents"
    if not agents_dir.is_dir():
        return

    agent_files = sorted(agents_dir.rglob("*.md"))
    if not agent_files:
        return

    tools = detect_agents_global()
    if not tools:
        return

    agent_dirs = global_agent_dirs()

    # Build list of (relative_path, content, agent_name) tuples
    entries: list[tuple[str, str, str]] = []
    for af in agent_files:
        rel = str(af.relative_to(warehouse_path))  # e.g. "agents/code-reviewer.md"
        content = af.read_text(encoding="utf-8")
        agent_name = af.name
        entries.append((rel, content, agent_name))

    # Detect conflicts: files that exist in global dirs but differ from warehouse
    conflicts: list[str] = []
    for _rel, content, agent_name in entries:
        for tool in tools:
            dest = agent_dirs[tool] / agent_name
            if dest.exists() and dest.read_text(encoding="utf-8") != content:
                conflicts.append(str(dest))

    # Single Y/N prompt for all conflicts together
    effective_preserve = preserve
    if conflicts and not force and not preserve:
        conflict_list = "\n".join(f"  • {p}" for p in conflicts)
        console.print(
            f"\n[yellow]Warning:[/yellow] {len(conflicts)} global agent file(s) "
            f"differ from the warehouse and will be overwritten:\n{conflict_list}\n"
        )
        if is_interactive():
            if not click.confirm(
                "Overwrite local agent files with warehouse versions?", default=False
            ):
                effective_preserve = True
        else:
            console.print(
                "[dim]Non-interactive mode — skipping agent overwrite. "
                "Use --force to overwrite or --preserve to suppress this warning.[/dim]"
            )
            effective_preserve = True

    # Install
    installed: list[str] = []
    skipped: list[str] = []
    for rel, content, agent_name in entries:
        for tool in tools:
            dest = agent_dirs[tool] / agent_name
            is_conflict = str(dest) in conflicts

            if effective_preserve and is_conflict:
                skipped.append(agent_name)
                continue

            written = install_agent_global(tool, agent_name, content)
            # Always update sync-state HEAD, even when content is unchanged.
            # Without this, 'abc delta' keeps reporting agents as stale after a
            # sync that found nothing to write (warehouse advanced, content same).
            write_agent_sync_state(warehouse_path, rel, hash_content(content))
            if written:
                installed.append(agent_name)

    if installed:
        unique = sorted(set(installed))
        console.print(
            f"\n[green]✓[/green] Synced {len(unique)} global agent(s) from warehouse "
            f"({', '.join(unique)})"
        )
    if skipped:
        unique_skipped = sorted(set(skipped))
        console.print(
            f"  [yellow]Skipped {len(unique_skipped)} agent(s) with local changes "
            f"(use --force to overwrite): {', '.join(unique_skipped)}[/yellow]"
        )


def handle_install_agent(
    artifact: str, *, force: bool = False, preserve: bool = False
) -> None:
    """Handle 'abc install agents/<name>.md' — global install for all detected tools.

    Loads warehouse settings, reads the agent file, performs soft-block conflict
    detection against global agent dirs, writes to each detected tool dir, and
    records sync-state for each successful write. Does NOT update beacon.yaml.
    """
    from beacon.core.manifest.workspace import WorkspaceConfig
    from beacon.utils.display import handle_soft_block

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

    agent_file = warehouse_path / artifact
    if not agent_file.exists():
        console.print(f"[red]Error:[/red] Agent not found in warehouse: {artifact}")
        sys.exit(1)

    content = agent_file.read_text(encoding="utf-8")
    agent_name = Path(artifact).name

    # Relink sync state if warehouse path has changed
    relink_global_sync_state(warehouse_path)

    # Detect tools
    tools = detect_agents_global()
    if not tools:
        console.print(
            "[yellow]Warning:[/yellow] No agent tools detected "
            "(neither ~/.config/opencode/ nor ~/.claude/ found)."
        )
        console.print("Install OpenCode or Claude Code and re-run to install agent.")
        return

    # Soft-block pre-check: check for conflicting global agent files
    agent_dirs = global_agent_dirs()
    conflicts: list[str] = []
    for tool in tools:
        dest = agent_dirs[tool] / agent_name
        if dest.exists() and dest.read_text(encoding="utf-8") != content:
            conflicts.append(str(dest))

    overwrite = handle_soft_block(conflicts, force=force, preserve=preserve)
    if not overwrite and conflicts:
        preserve = True  # skip conflicting files

    written_any = False
    for tool in tools:
        dest = agent_dirs[tool] / agent_name
        is_conflict = str(dest) in conflicts

        if preserve and is_conflict:
            console.print(f"[yellow]Skipped[/yellow] {dest} (preserved local version)")
            continue

        written = install_agent_global(tool, agent_name, content)
        # Always update sync-state HEAD, even when content is unchanged.
        # Without this, 'abc delta' keeps reporting the agent as stale after
        # install finds nothing to write (warehouse advanced, content same).
        write_agent_sync_state(warehouse_path, artifact, hash_content(content))
        if written:
            console.print(f"[green]Installed[/green] {artifact} → {dest}")
            written_any = True
        else:
            console.print(f"[dim]Up to date[/dim] {dest}")

    if not written_any and not conflicts:
        console.print(
            f"[dim]{artifact} is already up to date in all tool directories.[/dim]"
        )


def enrich_agent_stale(
    result: ComparisonResult,
    *,
    warehouse_path: Path,
    current_head: str,
    comparator: "DeltaComparator | None" = None,
) -> ComparisonResult:
    """Enrich agent ComparisonResults to STALE when the warehouse has advanced.

    Handles two cases:

    IDENTICAL → STALE:
        The installed file still matches the warehouse, but the warehouse HEAD has
        advanced AND the warehouse file content changed.  Without enrichment this
        would look fine but a newer version is available.

    MODIFIED → STALE (per-agent):
        The installed file no longer matches the warehouse, but the *user* didn't
        touch it — the warehouse updated it.  Detected by comparing the live global
        agent hash against the recorded content_hash; if they match the user's copy
        is still at the installed version, so the difference is purely upstream.
        Requires ``comparator`` to hash the live files.

    MISSING / ADDED results are returned unchanged.
    If no sync-state entry exists, the result is returned unchanged.

    Args:
        result: ComparisonResult to potentially enrich.
        warehouse_path: Path to the warehouse (used as sync-state key).
        current_head: Current warehouse HEAD SHA.
        comparator: DeltaComparator used to hash live agent files (needed for
            MODIFIED → STALE detection).  If None, that branch is skipped.
    """
    from beacon.domains.distribution.delta import ComparisonResult, DeltaStatus
    from beacon.domains.distribution.state import read_global_sync_state

    if result.status not in (DeltaStatus.IDENTICAL, DeltaStatus.MODIFIED):
        return result

    state = read_global_sync_state()
    warehouses = state.get("warehouses", {})
    wh_entries = warehouses.get(str(warehouse_path), {})
    entry = wh_entries.get(result.path)

    if entry is None:
        return result  # No sync-state entry — can't determine STALE

    recorded_head = entry.get("warehouse_head", "")
    recorded_content_hash = entry.get("content_hash", "")
    current_warehouse_hash = result.warehouse_hash

    if not recorded_head or recorded_head == current_head:
        return result  # Warehouse hasn't advanced — no enrichment needed

    # Warehouse HEAD has advanced. Check whether the warehouse file content changed.
    if (
        recorded_content_hash
        and current_warehouse_hash
        and recorded_content_hash == current_warehouse_hash
    ):
        return result  # Content unchanged despite HEAD advancing — not stale

    # Warehouse file content has changed since last install.

    if result.status == DeltaStatus.IDENTICAL:
        # All agents still match the warehouse — but warehouse has a newer version.
        stale_statuses = {agent: DeltaStatus.STALE for agent in result.agent_statuses}
        return ComparisonResult(
            path=result.path,
            status=DeltaStatus.STALE,
            local_hash=result.local_hash,
            warehouse_hash=result.warehouse_hash,
            agent_statuses=stale_statuses,
        )

    # result.status == MODIFIED: check each MODIFIED agent individually.
    # If the live global file still has the installed content_hash the user
    # hasn't changed it — the warehouse changed it.  That agent is STALE.
    # If the live file hash differs from both warehouse and installed hash the
    # user made a local edit — that agent stays MODIFIED.
    if comparator is None or not recorded_content_hash:
        return result  # Can't distinguish — leave as MODIFIED

    new_agent_statuses = dict(result.agent_statuses)
    changed = False
    for agent, status in result.agent_statuses.items():
        if status != DeltaStatus.MODIFIED:
            continue
        live_file = comparator.agent_live_path(agent, result.path)
        if not live_file.exists():
            continue
        live_hash = comparator.compute_hash(live_file)
        if live_hash == recorded_content_hash:
            # Live file is still at the installed version → warehouse updated it
            new_agent_statuses[agent] = DeltaStatus.STALE
            changed = True

    if not changed:
        return result

    # Recompute aggregate across the updated per-agent statuses.
    # Priority: ADDED > MODIFIED > STALE > MISSING > IDENTICAL
    _priority = {
        DeltaStatus.ADDED: 4,
        DeltaStatus.MODIFIED: 3,
        DeltaStatus.STALE: 2,
        DeltaStatus.MISSING: 1,
        DeltaStatus.IDENTICAL: 0,
    }
    new_aggregate = max(new_agent_statuses.values(), key=lambda s: _priority.get(s, 0))
    return ComparisonResult(
        path=result.path,
        status=new_aggregate,
        local_hash=result.local_hash,
        warehouse_hash=result.warehouse_hash,
        agent_statuses=new_agent_statuses,
    )
