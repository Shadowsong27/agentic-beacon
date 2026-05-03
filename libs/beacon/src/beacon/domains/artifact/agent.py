"""Agent operations for the artifact domain."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from beacon.utils.display import is_interactive
from beacon.utils.interaction import OverwriteDecision, resolve_conflict

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

    Shared detection logic used by `abc install` (and historically by
    per-project agent-drift tooling) so writes/reads hit the same global
    agent locations.
    """
    agents_paths: dict[str, Path] = {}
    for tool in detect_agents_global():
        if tool == "opencode":
            agents_paths["opencode"] = Path.home() / ".config" / "opencode" / "agents"
        elif tool == "claudecode":
            agents_paths["claudecode"] = Path.home() / ".claude" / "agents"
    return agents_paths


def _agent_link_conflicts(dest: Path, source_file: Path) -> bool:
    """Return whether replacing dest with a warehouse symlink needs confirmation."""
    if not dest.exists() and not dest.is_symlink():
        return False

    if dest.is_symlink():
        try:
            if dest.resolve(strict=True) == source_file.resolve(strict=True):
                return False
        except FileNotFoundError:
            return False

    if dest.is_dir():
        return True

    try:
        return dest.read_text(encoding="utf-8") != source_file.read_text(
            encoding="utf-8"
        )
    except OSError:
        return True


def install_agent_global(agent: str, agent_name: str, source_file: Path) -> bool:
    """Link an agent definition file into the global agent directory for a tool.

    Creates parent dirs if needed.
    Returns True if the symlink was created or repaired, False if already correct.
    Conflict handling is the caller's responsibility (soft block pre-check).

    Args:
        agent: Tool name — "opencode" or "claudecode".
        agent_name: Filename (e.g. "code-reviewer.md").
        source_file: Warehouse-side agent file to link to.
    """
    agent_dirs = global_agent_dirs()
    source = source_file.resolve(strict=True)
    dest = agent_dirs[agent] / agent_name

    if dest.is_symlink():
        try:
            if dest.resolve(strict=True) == source:
                return False
        except FileNotFoundError:
            pass

    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_symlink() or dest.exists():
        if dest.is_dir() and not dest.is_symlink():
            raise IsADirectoryError(f"Expected agent file, found directory: {dest}")
        dest.unlink()
    dest.symlink_to(source)
    return True


def uninstall_agent_global(agent_name: str) -> int:
    """Remove an agent definition file from all global agent directories.

    Returns the number of directories from which the agent was removed.
    """
    removed_count = 0
    for agent_dir in global_agent_dirs().values():
        target = agent_dir / agent_name
        if target.exists() or target.is_symlink():
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
    compares each against the global agent dirs for detected tools, and links any
    that are out-of-date.  A single Y/N prompt is shown when conflicts exist
    (unless --force or --preserve are supplied).

    Args:
        warehouse_path: Absolute path to the connected warehouse root.
        force: Overwrite conflicting files without prompting.
        preserve: Skip conflicting files without prompting.
    """
    agents_dir = warehouse_path / "agents"
    if not agents_dir.is_dir():
        return

    agent_files = sorted(
        af for af in agents_dir.rglob("*.md") if af.name != "README.md"
    )
    if not agent_files:
        return

    tools = detect_agents_global()
    if not tools:
        return

    agent_dirs = global_agent_dirs()

    # Build list of (relative_path, source_file, agent_name) tuples
    entries: list[tuple[str, Path, str]] = []
    for af in agent_files:
        rel = str(af.relative_to(warehouse_path))  # e.g. "agents/code-reviewer.md"
        agent_name = af.name
        entries.append((rel, af, agent_name))

    # Detect conflicts: files that exist in global dirs but differ from warehouse
    conflicts: list[str] = []
    for _rel, source_file, agent_name in entries:
        for tool in tools:
            dest = agent_dirs[tool] / agent_name
            if _agent_link_conflicts(dest, source_file):
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

    # Link
    installed: list[str] = []
    skipped: list[str] = []
    for _rel, source_file, agent_name in entries:
        for tool in tools:
            dest = agent_dirs[tool] / agent_name
            is_conflict = str(dest) in conflicts

            if effective_preserve and is_conflict:
                skipped.append(agent_name)
                continue

            linked = install_agent_global(tool, agent_name, source_file)
            if linked:
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

    Loads warehouse settings, performs soft-block conflict detection against global
    agent dirs, and creates warehouse symlinks in each detected tool dir. Does NOT
    update beacon.yaml.
    """
    from beacon.core.manifest.workspace import WorkspaceConfig

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

    agent_name = Path(artifact).name

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
        if _agent_link_conflicts(dest, agent_file):
            conflicts.append(str(dest))

    resolution = resolve_conflict(
        force=force, preserve=preserve, has_conflicts=bool(conflicts)
    )
    if resolution == OverwriteDecision.SKIP:
        preserve = True  # skip conflicting files
    elif resolution == OverwriteDecision.NEEDS_CONFIRMATION:
        # Non-interactive mode with conflicts — cannot prompt; refuse to proceed.
        conflict_list = "\n".join(f"  • {p}" for p in conflicts)
        console.print(
            f"\n[yellow]Warning:[/yellow] {len(conflicts)} global agent file(s) "
            f"differ from the warehouse:\n{conflict_list}\n"
        )
        console.print(
            "[red]Error:[/red] Non-interactive mode — cannot prompt for overwrite.\n"
            "Use --force to overwrite or --preserve to skip conflicting files."
        )
        sys.exit(1)

    written_any = False
    for tool in tools:
        dest = agent_dirs[tool] / agent_name
        is_conflict = str(dest) in conflicts

        if preserve and is_conflict:
            console.print(f"[yellow]Skipped[/yellow] {dest} (preserved local version)")
            continue

        linked = install_agent_global(tool, agent_name, agent_file)
        if linked:
            console.print(f"[green]Linked[/green] {artifact} → {dest}")
            written_any = True
        else:
            console.print(f"[dim]Up to date[/dim] {dest}")

    if not written_any and not conflicts:
        console.print(
            f"[dim]{artifact} is already up to date in all tool directories.[/dim]"
        )
