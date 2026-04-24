"""Delta view functions for the contribution domain.

User-facing output formatting for `abc delta` and `abc contribute` commands.
"""

import fnmatch
from pathlib import Path

from rich.console import Console
from rich.table import Table

from beacon.core.manifest.beacon import BeaconManifest
from beacon.domains.distribution.delta import (
    ComparisonResult,
    DeltaComparator,
    DeltaStatus,
    enrich_tracked_stale,
)
from beacon.domains.distribution.state import SYNC_STATE_FILENAME, read_sync_sha
from beacon.utils.git import get_warehouse_head_sha

console = Console()


def show_delta_summary(
    comparator: DeltaComparator,
    beacon_settings: BeaconManifest,
    warehouse_path: Path | None = None,
    project_root: Path | None = None,
) -> None:
    """Show summary of all artifact differences."""
    from beacon.domains.artifact.agent import (
        enrich_agent_stale,
        find_project_level_agents,
    )

    summary = comparator.compare_from_config(beacon_settings)

    # Re-classify MODIFIED tracked artifacts as STALE when the local copy has not been
    # touched since the last sync and the warehouse has since moved forward.
    # Falls back silently when git is unavailable or the snapshot is current.
    if warehouse_path is not None:
        summary = enrich_tracked_stale(
            summary,
            warehouse_path=warehouse_path,
            artifacts_path=comparator.artifacts_path,
            comparator=comparator,
        )

    # After enrichment, detect if any artifacts are still MODIFIED while the snapshot
    # is stale — these represent genuine local edits on top of an outdated snapshot.
    snapshot_stale = False
    if warehouse_path is not None:
        recorded_sha = read_sync_sha(comparator.artifacts_path)
        current_sha = get_warehouse_head_sha(warehouse_path)
        if recorded_sha and current_sha and recorded_sha != current_sha:
            snapshot_stale = True

    # Gather agent comparison results — discover from global agent dirs + warehouse
    # so agents that exist globally but not yet in the warehouse show as ADDED.
    agent_results = []
    if comparator.agents_paths and warehouse_path is not None:
        current_head = get_warehouse_head_sha(warehouse_path) or ""

        # Collect all unique agent file names across all global tool dirs and warehouse
        seen_rel_paths: set[str] = set()

        # First: files in global dirs (source of truth for new agents)
        for _tool, agents_dir in comparator.agents_paths.items():
            if agents_dir.is_dir():
                for agent_file in sorted(agents_dir.rglob("*")):
                    if agent_file.is_file() and agent_file.name != "README.md":
                        # Reconstruct warehouse-relative path: agents/<filename>
                        rel_path = "agents/" + agent_file.name
                        seen_rel_paths.add(rel_path)

        # Second: files in warehouse/agents/ that may not be in any global dir (MISSING)
        warehouse_agents_dir = warehouse_path / "agents"
        if warehouse_agents_dir.is_dir():
            for agent_file in sorted(warehouse_agents_dir.rglob("*")):
                if agent_file.is_file() and agent_file.name != "README.md":
                    rel_path = str(agent_file.relative_to(warehouse_path))
                    seen_rel_paths.add(rel_path)

        for rel_path in sorted(seen_rel_paths):
            result = comparator.compare_agent_file(rel_path)
            result = enrich_agent_stale(
                result,
                warehouse_path=warehouse_path,
                current_head=current_head,
                comparator=comparator,
            )
            agent_results.append(result)

    ignore_skill_patterns = beacon_settings.ignore.skills

    untracked = find_untracked_local_files(
        comparator, beacon_settings, comparator.artifacts_path, ignore_skill_patterns
    )

    # Detect project-scoped agents (not part of the global/contribution flow)
    project_level_agents: dict[str, list[str]] = (
        find_project_level_agents(project_root) if project_root is not None else {}
    )

    # Detect non-bundled skills accidentally placed in global skill dirs
    from beacon.domains.artifact.skill import find_global_untracked_skills

    global_untracked_skills = find_global_untracked_skills(ignore_skill_patterns)

    has_agent_diffs = any(r.status != DeltaStatus.IDENTICAL for r in agent_results)

    if (
        not summary.has_differences
        and not untracked
        and not has_agent_diffs
        and not project_level_agents
        and not global_untracked_skills
    ):
        console.print(
            "[green]No differences found. Local artifacts match local warehouse.[/green]"
        )
        return

    tracked_diffs = [r for r in summary.results if r.status != DeltaStatus.IDENTICAL]

    _STATUS_MARKUP: dict[DeltaStatus, str] = {
        DeltaStatus.MODIFIED: "[yellow]modified[/yellow]",
        DeltaStatus.ADDED: "[green]added[/green]",
        DeltaStatus.MISSING: "[red]missing[/red]",
        DeltaStatus.STALE: "[dim cyan]stale[/dim cyan]",
        DeltaStatus.PENDING: "[dim]pending[/dim]",
    }
    _AGENT_STATUS_MARKUP: dict[DeltaStatus, str] = {
        DeltaStatus.MODIFIED: "[yellow]modified[/yellow]",
        DeltaStatus.ADDED: "[green]added[/green]",
        DeltaStatus.MISSING: "[red]missing[/red]",
        DeltaStatus.IDENTICAL: "[dim]synced[/dim]",
        DeltaStatus.STALE: "[dim cyan]stale[/dim cyan]",
        DeltaStatus.PENDING: "[dim]pending[/dim]",
    }

    # --- Tracked Artifacts section ---
    if tracked_diffs:
        # Collect agent names for skill columns
        tracked_agents: list[str] = []
        for result in tracked_diffs:
            if result.is_skill and result.agent_statuses:
                for a in result.agent_statuses:
                    if a not in tracked_agents:
                        tracked_agents.append(a)

        # Group knowledge node file results and skill results separately from standalone entries
        node_entries = knowledge_node_entries(
            beacon_settings, comparator.warehouse_path
        )
        node_file_groups, skill_groups, standalone_results = partition_tracked_diffs(
            tracked_diffs, node_entries
        )

        console.print()

        has_grouped = bool(skill_groups or node_file_groups)

        if standalone_results:
            rows: list[tuple[str, str, dict[str, str]]] = []
            for result in standalone_results:
                sm = _STATUS_MARKUP.get(result.status, result.status.value)
                agent_cells: dict[str, str] = {}
                if result.is_skill and result.agent_statuses:
                    for a, s in result.agent_statuses.items():
                        agent_cells[a] = _AGENT_STATUS_MARKUP.get(s, s.value)
                rows.append((sm, result.path, agent_cells))
            console.print(render_delta_table(rows, "Tracked Artifacts", tracked_agents))
        elif has_grouped:
            console.print("[bold]Tracked Artifacts[/bold]")

        for skill_dir in sorted(skill_groups.keys()):
            console.print()
            render_skill_group(
                skill_dir,
                skill_groups[skill_dir],
                _STATUS_MARKUP,
                _AGENT_STATUS_MARKUP,
                tracked_agents,
            )

        for node_path in sorted(node_file_groups.keys()):
            console.print()
            render_knowledge_node_group(
                node_path,
                node_file_groups[node_path],
                _STATUS_MARKUP,
                comparator.warehouse_path,
            )

    # Classify agents for summary counts (always, even if no section rendered)
    stale_agents: list[str] = []
    added_agents: list[str] = []
    modified_agents: list[str] = []
    for result in agent_results:
        if result.status == DeltaStatus.STALE:
            stale_agents.append(result.path)
        elif result.status == DeltaStatus.ADDED:
            added_agents.append(result.path)
        elif result.status == DeltaStatus.MODIFIED:
            modified_agents.append(result.path)

    # --- Untracked Artifacts section ---
    if untracked:
        if tracked_diffs:
            console.rule(style="dim")

        # Partition untracked into skills and non-skills
        untracked_skill_groups: dict[str, list[tuple[str, list[str]]]] = {}
        untracked_non_skill: list[tuple[str, list[str]]] = []

        for rel_path, agents in untracked:
            parts = Path(rel_path).parts
            if len(parts) >= 2 and parts[0] == "skills":
                skill_dir = f"{parts[0]}/{parts[1]}"
                untracked_skill_groups.setdefault(skill_dir, []).append(
                    (rel_path, agents)
                )
            else:
                untracked_non_skill.append((rel_path, agents))

        # Collect all agent names present across untracked skill rows
        untracked_agents: list[str] = []
        for _rel_path, agents in untracked:
            for a in agents:
                if a not in untracked_agents:
                    untracked_agents.append(a)

        console.print()
        console.print(
            "[bold]Untracked Artifacts[/bold] [dim](not in beacon.yaml)[/dim]"
        )

        # Render non-skill untracked items in a table
        if untracked_non_skill:
            rows = []
            for rel_path, agents in untracked_non_skill:
                agent_cells = {a: "[green]added[/green]" for a in agents}
                rows.append(("[green]added[/green]", rel_path, agent_cells))
            console.print()
            console.print(render_delta_table(rows, "", untracked_agents))

        # Render skill groups
        for skill_dir in sorted(untracked_skill_groups.keys()):
            console.print()
            skill_items = untracked_skill_groups[skill_dir]
            badge = f"  [dim][{len(skill_items)} added][/dim]"
            console.print(f"[bold]{skill_dir}/[/bold]{badge}")

            table = Table(
                show_header=True,
                header_style="dim",
                box=None,
                padding=(0, 2, 0, 2),
            )
            table.add_column("Status", no_wrap=True)
            table.add_column("File")
            for agent in untracked_agents:
                table.add_column(agent, no_wrap=True)

            for rel_path, agents in sorted(skill_items, key=lambda x: x[0]):
                prefix = skill_dir + "/"
                file_name = rel_path.removeprefix(prefix)
                agent_cells = [
                    "[green]added[/green]" if a in agents else ""
                    for a in untracked_agents
                ]
                table.add_row("[green]added[/green]", file_name, *agent_cells)

            console.print(table)

    # --- Agents section — only show when there are diffs ---
    if has_agent_diffs:
        if tracked_diffs or untracked:
            console.rule(style="dim")

        # Collect all tool names present across agent rows
        agent_tools: list[str] = []
        for result in agent_results:
            if result.agent_statuses:
                for t in result.agent_statuses:
                    if t not in agent_tools:
                        agent_tools.append(t)

        rows = []
        for result in agent_results:
            status_markup: str = (
                _STATUS_MARKUP.get(result.status) or result.status.value
            )
            agent_cells: dict[str, str] = {}
            if result.agent_statuses:
                for t, s in result.agent_statuses.items():
                    agent_cells[t] = _AGENT_STATUS_MARKUP.get(s) or s.value
            rows.append((status_markup, result.path, agent_cells))

        console.print()
        console.print(
            render_delta_table(
                rows,
                "Agents [dim](global)[/dim]",
                agent_tools,
            )
        )

    # --- Project-scoped agents reminder ---
    if project_level_agents:
        if has_agent_diffs or tracked_diffs or untracked:
            console.rule(style="dim")

        # Collect all unique agent filenames and tools in a stable order
        proj_tools: list[str] = sorted(project_level_agents.keys())
        proj_files: list[str] = sorted(
            {f for files in project_level_agents.values() for f in files}
        )

        table = Table(
            title="Project-scoped Agents [dim](promote to global to include in contribution flow)[/dim]",
            title_style="bold yellow",
            title_justify="left",
            show_header=True,
            header_style="dim",
            box=None,
            padding=(0, 2, 0, 0),
        )
        table.add_column("Agent file")
        for tool in proj_tools:
            table.add_column(tool, no_wrap=True)

        for fname in proj_files:
            cells = [
                "[yellow]project[/yellow]"
                if fname in project_level_agents.get(tool, [])
                else ""
                for tool in proj_tools
            ]
            table.add_row(fname, *cells)

        console.print()
        console.print(table)

    # --- Global untracked skills reminder ---
    if global_untracked_skills:
        if project_level_agents or agent_results or tracked_diffs or untracked:
            console.rule(style="dim")

        global_skill_tools: list[str] = sorted(global_untracked_skills.keys())
        global_skill_names: list[str] = sorted(
            {s for names in global_untracked_skills.values() for s in names}
        )

        table = Table(
            show_header=True,
            header_style="dim",
            box=None,
            padding=(0, 2, 0, 0),
        )
        table.add_column("Skill")
        for tool in global_skill_tools:
            table.add_column(tool, no_wrap=True)

        for skill_name in global_skill_names:
            cells = [
                "[yellow]global[/yellow]"
                if skill_name in global_untracked_skills.get(tool, [])
                else ""
                for tool in global_skill_tools
            ]
            table.add_row(skill_name, *cells)

        console.print()
        console.print(
            "[bold yellow]Global Skills[/bold yellow] [dim](not tracked in warehouse)[/dim]"
        )
        console.print(table)

    # Summary counts
    console.print("\n[bold]Summary:[/bold]")
    if summary.stale:
        console.print(
            f"  [dim cyan]Stale:[/dim cyan] {len(summary.stale)} artifact(s) — warehouse updated, run 'abc sync'"
        )
    if summary.modified:
        console.print(f"  [yellow]Modified:[/yellow] {len(summary.modified)} files")
    if summary.added:
        console.print(f"  [green]Added:[/green] {len(summary.added)} files")
    if untracked:
        console.print(f"  [green]Untracked:[/green] {len(untracked)} files")
    if summary.missing:
        console.print(f"  [red]Missing:[/red] {len(summary.missing)} files")
    if summary.identical:
        console.print(f"  [dim]Identical:[/dim] {len(summary.identical)} files")
    if added_agents:
        console.print(
            f"  [green]New agent(s):[/green] {len(added_agents)} (not yet in warehouse)"
        )
    if modified_agents:
        console.print(f"  [yellow]Modified agent(s):[/yellow] {len(modified_agents)}")
    if stale_agents:
        console.print(f"  [dim cyan]Stale agent(s):[/dim cyan] {len(stale_agents)}")
    if project_level_agents:
        total = sum(len(v) for v in project_level_agents.values())
        console.print(
            f"  [yellow]Project-scoped agent(s):[/yellow] {total} (not in global dirs)"
        )
    if global_untracked_skills:
        total = sum(len(v) for v in global_untracked_skills.values())
        console.print(
            f"  [yellow]Global skill(s):[/yellow] {total} (in global dir, not tracked)"
        )

    # Tips
    if summary.stale or stale_agents:
        console.print(
            "\n[dim]Tip: Run 'abc sync' to pull upstream artifact changes.[/dim]"
        )
    if stale_agents:
        console.print(
            "[dim]Tip: Run 'abc install agents/<name>' to update stale agent definitions.[/dim]"
        )
    if summary.missing:
        console.print(
            "[dim]Tip: Run 'abc sync' to download missing artifacts from warehouse.[/dim]"
        )
    if summary.modified and snapshot_stale:
        # Snapshot is stale AND some files are still genuinely MODIFIED (user edited them
        # on top of an old snapshot). Warn that sync won't overwrite local edits.
        console.print(
            "\n[yellow]Note:[/yellow] Your snapshot is outdated and some artifacts have local edits.\n"
            "  Run 'abc sync' first — locally modified files will be preserved by default.\n"
            "    abc sync"
        )
    elif summary.modified:
        console.print(
            "[dim]Tip: Run 'abc delta <file>' to see detailed diff for a modified file.[/dim]"
        )
    if untracked and (added_agents or modified_agents):
        console.print(
            "[dim]Tip: Run 'abc contribute' to push untracked artifacts and agent changes to the warehouse.[/dim]"
        )
    elif untracked:
        console.print(
            "[dim]Tip: Run 'abc contribute' to push untracked local artifacts to the warehouse.[/dim]"
        )
    elif added_agents or modified_agents:
        console.print(
            "[dim]Tip: Run 'abc contribute' to push agent changes to the warehouse.[/dim]"
        )
    if project_level_agents:
        console.print(
            "[dim]Tip: To promote a project-scoped agent, move it to the global agents dir "
            "and run 'abc contribute' — or ask your coding agent to do it for you.[/dim]"
        )
    if global_untracked_skills:
        console.print(
            "[dim]Tip: Global skills are not tracked in the warehouse. Move them to the "
            "project skill dir (.claude/skills/ or .opencode/skills/) and run "
            "'abc contribute' — or ask your coding agent to do it for you.[/dim]"
        )


def show_detailed_diff(
    comparator: DeltaComparator,
    beacon_settings: BeaconManifest,
    file_path: str,
    no_color: bool,
) -> None:
    """Show detailed diff for a specific file."""
    import sys

    # Check if file is tracked in beacon.yaml
    all_paths = collect_artifact_paths(comparator, beacon_settings)
    if file_path not in all_paths:
        console.print(
            f"[red]Error:[/red] File '{file_path}' is not tracked in beacon.yaml."
        )
        console.print("Only artifacts declared in beacon.yaml can be compared.")
        sys.exit(1)

    # Compare the specific file
    result = comparator.compare_file(file_path)

    if result.status == DeltaStatus.IDENTICAL:
        console.print(
            f"[green]No differences found.[/green] Local and warehouse versions of '{file_path}' are identical."
        )
        return

    if result.status == DeltaStatus.MISSING:
        console.print(
            f"[red][Missing][/red] '{file_path}' has not been synced locally."
        )
        console.print("[dim]Run 'abc sync' to download it.[/dim]")
        return

    if result.status == DeltaStatus.ADDED:
        console.print(
            f"[green][Added][/green] '{file_path}' exists locally but not in warehouse."
        )
        return

    # Show detailed diff
    console.print(f"\n[bold]Diff: {file_path}[/bold]\n")
    diff_output = comparator.detailed_diff(file_path, color=not no_color)
    if diff_output:
        console.print(diff_output)
    else:
        console.print("[dim]No differences to display.[/dim]")


def format_skill_agent_statuses(agent_statuses: dict) -> str:
    """Format per-agent skill statuses for display.

    e.g. "opencode: modified, claudecode: identical"
    """

    label = {
        DeltaStatus.MODIFIED: "modified",
        DeltaStatus.MISSING: "missing",
        DeltaStatus.ADDED: "added",
        DeltaStatus.IDENTICAL: "identical",
    }
    parts = [
        f"{agent}: {label.get(status, status.value)}"
        for agent, status in agent_statuses.items()
    ]
    return ", ".join(parts)


def knowledge_node_entries(
    beacon_settings: BeaconManifest, warehouse_path: Path
) -> list[str]:
    """Return the knowledge node paths (directory entries) declared in beacon.yaml.

    Only non-glob patterns that point to a warehouse directory are treated as nodes.
    Returned longest-first so that nested nodes match before their parents.
    """
    nodes = []
    for pattern in beacon_settings.artifacts.knowledge:
        if "*" not in pattern and "?" not in pattern:
            node_path = pattern.rstrip("/")
            if (warehouse_path / node_path).is_dir():
                nodes.append(node_path)
    return sorted(nodes, key=len, reverse=True)


def skill_entries(tracked_diffs: list[ComparisonResult]) -> list[str]:
    """Return skill directory paths present in tracked diffs.

    Extracts the skill directory (e.g. "skills/my-skill") from each skill result
    and returns unique entries longest-first so nested paths match correctly.
    """
    dirs: set[str] = set()
    for result in tracked_diffs:
        if result.is_skill:
            parts = Path(result.path).parts
            if len(parts) >= 2 and parts[0] == "skills":
                dirs.add(f"{parts[0]}/{parts[1]}")
    return sorted(dirs, key=len, reverse=True)


def partition_tracked_diffs(
    tracked_diffs: list[ComparisonResult],
    node_entries: list[str],
) -> tuple[
    dict[str, list[ComparisonResult]],
    dict[str, list[ComparisonResult]],
    list[ComparisonResult],
]:
    """Split tracked diffs into per-node file groups, skill groups, and standalone results.

    Returns (node_file_groups, skill_groups, standalone_results).
    node_file_groups maps node_path → list of file-level ComparisonResults that live
    under that node (path starts with node + "/").
    skill_groups maps skill_dir → list of file-level ComparisonResults for that skill.
    standalone_results contains everything else — including single-node MISSING results
    whose path equals the node path exactly (not a sub-file).
    """
    skill_dirs = skill_entries(tracked_diffs)
    node_file_groups: dict[str, list[ComparisonResult]] = {}
    skill_groups: dict[str, list[ComparisonResult]] = {}
    standalone_results: list[ComparisonResult] = []

    for result in tracked_diffs:
        matched_skill = None
        for skill_dir in skill_dirs:
            if result.path.startswith(skill_dir + "/"):
                matched_skill = skill_dir
                break
        if matched_skill:
            skill_groups.setdefault(matched_skill, []).append(result)
            continue

        matched_node = None
        for node in node_entries:
            if result.path.startswith(node + "/"):
                matched_node = node
                break
        if matched_node:
            node_file_groups.setdefault(matched_node, []).append(result)
        else:
            standalone_results.append(result)

    return node_file_groups, skill_groups, standalone_results


def render_knowledge_node_group(
    node_path: str,
    results: list[ComparisonResult],
    status_markup: dict[DeltaStatus, str],
    warehouse_path: Path,
) -> None:
    """Render a knowledge node group: a header line + indented file table.

    The header shows the node path and a breakdown badge.  Missing files are shown
    as a fraction of the total in the warehouse node (e.g. "2/5 missing") so the
    user can see at a glance whether the whole node or only part of it is absent.
    Other statuses show plain counts (e.g. "1 modified").
    """
    _STATUS_ORDER = [
        (DeltaStatus.MODIFIED, "modified", "[yellow]", "[/yellow]"),
        (DeltaStatus.MISSING, "missing", "[red]", "[/red]"),
        (DeltaStatus.ADDED, "added", "[green]", "[/green]"),
        (DeltaStatus.STALE, "stale", "[dim cyan]", "[/dim cyan]"),
    ]

    counts: dict[DeltaStatus, int] = {}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1

    # Total .md files in this node in the local warehouse — used to render
    # missing as a fraction so the user knows whether it's partial or complete.
    node_dir = warehouse_path / node_path
    total_in_node = sum(1 for f in node_dir.rglob("*.md") if f.is_file())

    badge_parts = []
    for status, label, open_tag, close_tag in _STATUS_ORDER:
        n = counts.get(status, 0)
        if not n:
            continue
        if status == DeltaStatus.MISSING and total_in_node > 0:
            badge_parts.append(f"{open_tag}{n}/{total_in_node} {label}{close_tag}")
        else:
            badge_parts.append(f"{open_tag}{n} {label}{close_tag}")

    badge = "  [dim][" + " · ".join(badge_parts) + "][/dim]" if badge_parts else ""
    console.print(f"[bold]{node_path}[/bold]{badge}")

    prefix = node_path + "/"
    table = Table(
        show_header=True,
        header_style="dim",
        box=None,
        padding=(0, 2, 0, 2),
    )
    table.add_column("Status", no_wrap=True)
    table.add_column("File")

    for result in sorted(results, key=lambda r: r.path):
        rel = result.path.removeprefix(prefix)
        sm = status_markup.get(result.status, result.status.value)
        table.add_row(sm, rel)

    console.print(table)


def render_skill_group(
    skill_dir: str,
    results: list[ComparisonResult],
    status_markup: dict[DeltaStatus, str],
    agent_status_markup: dict[DeltaStatus, str],
    agents: list[str],
) -> None:
    """Render a skill group: a header line + indented file table with per-agent columns.

    The header shows the skill directory and a breakdown badge.
    """
    _STATUS_ORDER = [
        (DeltaStatus.MODIFIED, "modified", "[yellow]", "[/yellow]"),
        (DeltaStatus.MISSING, "missing", "[red]", "[/red]"),
        (DeltaStatus.ADDED, "added", "[green]", "[/green]"),
        (DeltaStatus.STALE, "stale", "[dim cyan]", "[/dim cyan]"),
    ]

    counts: dict[DeltaStatus, int] = {}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1

    badge_parts = []
    for status, label, open_tag, close_tag in _STATUS_ORDER:
        n = counts.get(status, 0)
        if n:
            badge_parts.append(f"{open_tag}{n} {label}{close_tag}")

    badge = "  [dim][" + " · ".join(badge_parts) + "][/dim]" if badge_parts else ""
    console.print(f"[bold]{skill_dir}/[/bold]{badge}")

    prefix = skill_dir + "/"
    table = Table(
        show_header=True,
        header_style="dim",
        box=None,
        padding=(0, 2, 0, 2),
    )
    table.add_column("Status", no_wrap=True)
    table.add_column("File")
    for agent in agents:
        table.add_column(agent, no_wrap=True)

    for result in sorted(results, key=lambda r: r.path):
        rel = result.path.removeprefix(prefix)
        sm = status_markup.get(result.status, result.status.value)
        agent_cells = [
            agent_status_markup.get(result.agent_statuses.get(a), "")
            if result.agent_statuses
            else ""
            for a in agents
        ]
        table.add_row(sm, rel, *agent_cells)

    console.print(table)


def render_delta_table(
    rows: list[tuple[str, str, dict[str, str]]],
    title: str,
    agents: list[str],
) -> Table:
    """Render a delta section as a Rich table.

    Each row is a (status_markup, artifact_path, agent_cells) tuple where
    agent_cells maps agent name → markup string (empty string if not applicable).
    Agent columns are only added when at least one skill row is present (agents != []).
    """
    table = Table(
        title=title,
        title_style="bold",
        title_justify="left",
        show_header=True,
        header_style="dim",
        box=None,
        padding=(0, 2, 0, 0),
    )
    table.add_column("Status", no_wrap=True)
    table.add_column("Artifact")
    for agent in agents:
        table.add_column(agent, no_wrap=True)

    for status_markup, path, agent_cells in rows:
        agent_values = [agent_cells.get(a, "") for a in agents]
        table.add_row(status_markup, path, *agent_values)

    return table


def collect_artifact_paths(
    comparator: DeltaComparator, beacon_settings: BeaconManifest
) -> set:
    """Collect all artifact paths from beacon.yaml, expanding globs.

    Globs both the warehouse and local artifacts directory so that locally-added
    files (not yet in the warehouse) are included.
    """
    from beacon.domains.artifact.skill import (
        normalize_skill_entry,
        skill_name_from_entry,
    )
    from beacon.domains.distribution.sync_engine import SyncEngine

    sync_engine = SyncEngine(
        warehouse_path=comparator.warehouse_path,
        artifacts_path=comparator.artifacts_path,
    )
    paths: set[str] = set()
    for artifact_type in ["knowledge", "skills", "contexts"]:
        patterns = getattr(beacon_settings.artifacts, artifact_type)
        for pattern in patterns:
            if "*" in pattern or "?" in pattern or "[" in pattern:
                paths.update(sync_engine.expand_glob(pattern))
                # Also glob local artifacts to catch ADDED files
                if comparator.artifacts_path.exists():
                    for match in comparator.artifacts_path.glob(pattern):
                        if match.is_file():
                            paths.add(str(match.relative_to(comparator.artifacts_path)))
            elif artifact_type == "skills":
                # Expand skill directory entry to individual file paths
                skill_dir_entry = normalize_skill_entry(pattern)
                paths.update(sync_engine.expand_glob(f"{skill_dir_entry}/**/*"))
                # Also scan live agent dirs to catch ADDED files
                if comparator.skills_paths:
                    skill_name = skill_name_from_entry(pattern)
                    for _agent, agent_root in comparator.skills_paths.items():
                        agent_skill_dir = agent_root / skill_name
                        if agent_skill_dir.exists():
                            for f in agent_skill_dir.rglob("*"):
                                if f.is_file():
                                    rel = str(
                                        Path("skills")
                                        / skill_name
                                        / f.relative_to(agent_skill_dir)
                                    )
                                    paths.add(rel)
            elif artifact_type == "knowledge" and (
                pattern.endswith("/") or (comparator.warehouse_path / pattern).is_dir()
            ):
                # Node-level knowledge directory — expand to individual .md file paths,
                # mirroring the sync command which uses expand_glob(f"{pattern}/**/*.md").
                # Without this, delta sees synced files like knowledge/python/decisions/a.md
                # as untracked because `tracked` only contains the raw directory string.
                node_path = pattern.rstrip("/")
                paths.update(sync_engine.expand_glob(f"{node_path}/**/*.md"))
                # Also scan local artifacts to catch locally-added .md files not yet in warehouse
                if comparator.artifacts_path.exists():
                    local_node = comparator.artifacts_path / node_path
                    if local_node.exists():
                        for f in local_node.rglob("*.md"):
                            if f.is_file():
                                paths.add(str(f.relative_to(comparator.artifacts_path)))
            else:
                paths.add(pattern)
    return paths


def infer_artifact_type(file_path: str) -> str | None:
    """Infer artifact type from a relative path prefix.

    Returns "knowledge", "skills", "contexts", or None if unrecognisable.
    """
    first_part = Path(file_path).parts[0] if Path(file_path).parts else ""
    if first_part in ("knowledge", "skills", "contexts"):
        return first_part
    return None


def find_untracked_local_files(
    comparator: DeltaComparator,
    beacon_settings: BeaconManifest,
    artifacts_dir: Path,
    ignore_patterns: list[str] | None = None,
) -> list[tuple[str, list[str]]]:
    """Return local artifact files that are not covered by any beacon.yaml pattern.

    Returns a list of (relative_path, agents) tuples. For skills found in live
    agent directories, agents lists which agents have the skill (e.g. ["opencode",
    "claudecode"]). For knowledge/context files from artifacts_dir, agents is [].

    Skills whose names match any of ignore_patterns (fnmatch) are excluded.

    NOTE: .agentic-beacon/artifacts/skills/ is intentionally excluded from the
    artifacts_dir scan. That directory is a one-way intermediary used only during
    'abc sync' to stage skill files before wiring them to live agent directories
    (.opencode/skills/, .claude/skills/). It is never a source of truth for delta —
    skills are always compared against their live agent installation, not the snapshot.
    """
    tracked = collect_artifact_paths(comparator, beacon_settings)
    patterns = ignore_patterns or []

    # Scan artifacts_dir for untracked knowledge and context files.
    # Explicitly skip the skills/ subdirectory — it is a one-way sync staging area
    # and must not be treated as a canonical source for delta comparisons.
    artifacts_untracked: list[str] = []
    if artifacts_dir.exists():
        for file_path in sorted(artifacts_dir.rglob("*")):
            if file_path.is_file() and file_path.name != SYNC_STATE_FILENAME:
                rel = str(file_path.relative_to(artifacts_dir))
                if rel.startswith("skills/"):
                    continue  # skills live in agent dirs, not here
                if rel not in tracked:
                    artifacts_untracked.append(rel)

    # Scan live agent skill directories — the canonical location for installed skills.
    # Group by rel_path so a skill present in multiple agent dirs is reported once
    # with all agents listed.
    skill_agents: dict[str, list[str]] = {}
    for agent, skills_root in comparator.skills_paths.items():
        if skills_root.exists():
            for file_path in sorted(skills_root.rglob("*")):
                if file_path.is_file():
                    rel = str(Path("skills") / file_path.relative_to(skills_root))
                    if rel not in tracked:
                        # Extract the skill directory name (parts[1]) for pattern matching.
                        # e.g. "skills/openspec-apply-change/SKILL.md" → "openspec-apply-change"
                        skill_name = (
                            Path(rel).parts[1] if len(Path(rel).parts) > 1 else ""
                        )
                        if patterns and any(
                            fnmatch.fnmatch(skill_name, p) for p in patterns
                        ):
                            continue
                        skill_agents.setdefault(rel, []).append(agent)

    result: list[tuple[str, list[str]]] = []
    for rel in artifacts_untracked:
        result.append((rel, []))
    for rel in sorted(skill_agents):
        result.append((rel, skill_agents[rel]))

    return result
