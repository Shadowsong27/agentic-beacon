"""Contribute utility functions for Beacon CLI."""

import datetime
import shutil
import subprocess
from pathlib import Path

from rich.console import Console

from beacon.core.delta import DeltaComparator, DeltaStatus
from beacon.core.manifest.beacon import BeaconManifest

console = Console()


def _resolve_skill_contribute_source(
    comparator: DeltaComparator,
    relative_path: str,
    artifacts_dir: Path,
    dry_run: bool = False,
) -> Path | None:
    """Resolve which file to read when contributing a skill back to the warehouse.

    Skills live in agent-specific directories (.opencode/skills/, .claude/skills/).
    We need to decide which copy to contribute when multiple agents are present.

    Rules:
    - No agents configured → fall back to artifact snapshot (backward compat).
    - One agent modified → use that agent's copy.
    - Multiple agents modified with identical content → use any (they agree).
    - Multiple agents modified with different content → prompt user to choose.
    - No agent has a modified copy (IDENTICAL/MISSING/ADDED) → return None,
      letting the caller decide (IDENTICAL means nothing to contribute).

    Returns the absolute Path of the file to copy, or None if nothing to contribute.
    Exits with an error message if the user cancels the prompt.
    """
    import click

    if not comparator.skills_paths:
        # No agents detected — fall back to artifact snapshot
        return artifacts_dir / relative_path

    result = comparator.compare_file(relative_path)

    # Collect agents whose live copy differs from warehouse
    modified_agents = [
        agent
        for agent, status in result.agent_statuses.items()
        if status == DeltaStatus.MODIFIED
    ]

    if not modified_agents:
        # Nothing modified in any live dir — nothing to contribute
        return None

    # Build the candidate paths for modified agents
    candidates: dict[str, Path] = {}
    for agent in modified_agents:
        live_path = comparator._skill_live_path(agent, relative_path)
        if live_path.exists():
            candidates[agent] = live_path

    if not candidates:
        return None

    if len(candidates) == 1:
        return next(iter(candidates.values()))

    # Multiple agents have modified versions — check if they are identical
    hashes = {
        agent: comparator.compute_hash(path) for agent, path in candidates.items()
    }
    unique_hashes = set(hashes.values())

    if len(unique_hashes) == 1:
        # All modified copies are identical — pick the first one
        return next(iter(candidates.values()))

    # Genuinely different versions across agents.
    # During a dry-run preview, skip the interactive prompt and just report the conflict.
    if dry_run:
        console.print(
            f"\n[yellow]Conflict:[/yellow] '{relative_path}' has been modified differently "
            "across agents — you will be prompted to choose when you confirm.\n"
        )
        return next(iter(candidates.values()))  # placeholder; not used in dry-run

    # Prompt the user to choose
    console.print(
        f"\n[yellow]Conflict:[/yellow] '{relative_path}' has been modified differently across agents:\n"
    )
    agent_list = list(candidates.keys())
    for i, agent in enumerate(agent_list, 1):
        live_path = candidates[agent]
        console.print(f"  [{i}] {agent}")
        console.print(f"      [dim]{live_path}[/dim]")

    console.print()
    valid = [str(i) for i in range(1, len(agent_list) + 1)]
    while True:
        raw = click.prompt(
            f"Which version to contribute to the warehouse? ({'/'.join(valid)})",
            default="",
            show_default=False,
        ).strip()
        if raw in valid:
            break
        console.print(f"  [red]Invalid choice.[/red] Enter {' or '.join(valid)}.")

    chosen_agent = agent_list[int(raw) - 1]
    console.print(f"  Using [bold]{chosen_agent}[/bold] version.\n")
    return candidates[chosen_agent]


def _propagate_skill_to_agents(
    project_root: Path, relative_path: str, source_path: Path
) -> None:
    """After contributing a skill file to the warehouse, propagate all files in
    that skill directory to every configured agent's live copy.

    This prevents the delta cycle where contributing one agent's modified version
    leaves other agents' copies flagged as MODIFIED.

    ``relative_path`` is the warehouse-relative path, e.g. ``skills/foo/SKILL.md``.
    ``source_path`` is the absolute path of the file written to the warehouse.
    """
    from beacon.domains.artifact.agent import detect_agents
    from beacon.domains.artifact.skill import wire_single_skill

    parts = Path(relative_path).parts
    if len(parts) < 2:
        return
    skill_name = parts[1]

    # Propagate the entire skill directory, not just the contributed file
    warehouse_skill_dir = source_path.parent
    # Walk up until we reach the skills/<name> level
    while warehouse_skill_dir.name != skill_name:
        parent = warehouse_skill_dir.parent
        if parent == warehouse_skill_dir:
            return  # Safety: avoid infinite loop
        warehouse_skill_dir = parent

    agents = detect_agents(project_root)
    for agent in agents:
        try:
            wire_single_skill(project_root, skill_name, warehouse_skill_dir, agent)
        except Exception as e:
            console.print(
                f"  [yellow]Warning:[/yellow] could not propagate '{skill_name}' to {agent}: {e}"
            )


def _resolve_agent_contribute_source(
    comparator: DeltaComparator,
    relative_path: str,
    dry_run: bool = False,
) -> Path | None:
    """Resolve which global agent file to read when contributing back to the warehouse.

    Agent files live in global directories (~/.config/opencode/agents/ or
    ~/.claude/agents/). The logic mirrors _resolve_skill_contribute_source:

    - No agents configured → return None (nothing to contribute).
    - One tool has a modified or new copy → use it.
    - Multiple tools modified/added with identical content → use any.
    - Multiple tools modified/added with different content → prompt user to choose.
    - No tool has a modified or new copy → return None (identical to warehouse).

    Returns the absolute Path of the file to copy, or None if nothing to contribute.
    """
    import click

    if not comparator.agents_paths:
        return None

    result = comparator._compare_agent_file(relative_path)

    contributable_tools = [
        tool
        for tool, status in result.agent_statuses.items()
        if status in (DeltaStatus.MODIFIED, DeltaStatus.ADDED)
    ]

    if not contributable_tools:
        return None

    candidates: dict[str, Path] = {}
    for tool in contributable_tools:
        live_path = comparator._agent_live_path(tool, relative_path)
        if live_path.exists():
            candidates[tool] = live_path

    if not candidates:
        return None

    if len(candidates) == 1:
        return next(iter(candidates.values()))

    # Multiple tools have modified copies — check if they are identical
    hashes = {tool: comparator.compute_hash(path) for tool, path in candidates.items()}
    if len(set(hashes.values())) == 1:
        return next(iter(candidates.values()))

    # Genuinely different — prompt or report
    if dry_run:
        console.print(
            f"\n[yellow]Conflict:[/yellow] '{relative_path}' has been modified differently "
            "across tools — you will be prompted to choose when you confirm.\n"
        )
        return next(iter(candidates.values()))  # placeholder; not used in dry-run

    console.print(
        f"\n[yellow]Conflict:[/yellow] '{relative_path}' has been modified differently across tools:\n"
    )
    tool_list = list(candidates.keys())
    for i, tool in enumerate(tool_list, 1):
        console.print(f"  [{i}] {tool}")
        console.print(f"      [dim]{candidates[tool]}[/dim]")
    console.print()
    valid = [str(i) for i in range(1, len(tool_list) + 1)]
    while True:
        raw = click.prompt(
            f"Which version to contribute to the warehouse? ({'/'.join(valid)})",
            default="",
            show_default=False,
        ).strip()
        if raw in valid:
            break
        console.print(f"  [red]Invalid choice.[/red] Enter {' or '.join(valid)}.")

    chosen = tool_list[int(raw) - 1]
    console.print(f"  Using [bold]{chosen}[/bold] version.\n")
    return candidates[chosen]


def _contribute_single(
    comparator: DeltaComparator,
    beacon_settings: BeaconManifest,
    warehouse_path: Path,
    artifacts_dir: Path,
    file_path: str,
    dry_run: bool,
    project_root: Path,
) -> list[tuple[str, str]]:
    """Contribute a single artifact back to the warehouse.

    For skills: reads from the live agent directory rather than the artifact
    snapshot, matching the same source that abc delta inspects.
    For agents: reads from the global agent directory (~/.config/opencode/agents/
    or ~/.claude/agents/).

    Does NOT auto-register untracked files in beacon.yaml — use ``abc adopt``
    for discovery and opt-in.

    Returns a list of (path, status_label) tuples for contributed files.
    """
    import sys

    is_skill = file_path.startswith("skills/") and bool(comparator.skills_paths)
    is_agent = file_path.startswith("agents/") and bool(comparator.agents_paths)

    if is_skill:
        # Resolve the live agent source (may prompt user if multiple agents conflict)
        local_path = _resolve_skill_contribute_source(
            comparator, file_path, artifacts_dir, dry_run=dry_run
        )
        if local_path is None:
            console.print(
                f"[yellow]Nothing to contribute.[/yellow] "
                f"'{file_path}' is identical to the warehouse version across all agents."
            )
            return []
    elif is_agent:
        local_path = _resolve_agent_contribute_source(
            comparator, file_path, dry_run=dry_run
        )
        if local_path is None:
            console.print(
                f"[yellow]Nothing to contribute.[/yellow] "
                f"'{file_path}' is identical to the warehouse version across all tools."
            )
            return []
    else:
        local_path = artifacts_dir / file_path
        if not local_path.exists():
            console.print(f"[red]Error:[/red] '{file_path}' does not exist locally.")
            console.print(
                "Create the file in .agentic-beacon/artifacts/ first, then contribute it."
            )
            sys.exit(1)

    if not is_skill and not is_agent:
        result = comparator.compare_file(file_path)
        if result.status == DeltaStatus.IDENTICAL:
            console.print(
                f"[yellow]Nothing to contribute.[/yellow] "
                f"'{file_path}' is identical to the warehouse version."
            )
            return []

    dest_existed = (warehouse_path / file_path).exists()
    _copy_to_warehouse(local_path, warehouse_path / file_path, file_path, dry_run)
    if is_skill and not dry_run:
        _propagate_skill_to_agents(project_root, file_path, local_path)
    status_label = "modified" if dest_existed else "added"
    return [(file_path, status_label)]


def _contribute_all(
    comparator: DeltaComparator,
    beacon_settings: BeaconManifest,
    warehouse_path: Path,
    artifacts_dir: Path,
    dry_run: bool,
    project_root: Path,
    include_unregistered: bool = False,
    ignore_skill_patterns: list[str] | None = None,
) -> list[tuple[str, str]]:
    """Contribute all tracked modified/added artifacts and modified agents to the warehouse.

    Covers three sources:
    1. Tracked artifacts (knowledge/skills/contexts) declared in beacon.yaml that
       have local modifications or additions.
    2. Unregistered local files not in beacon.yaml (when include_unregistered=True).
    3. Agent definition files (~/.config/opencode/agents/, ~/.claude/agents/) that
       differ from the warehouse — these are always included regardless of beacon.yaml.

    For skills: reads from live agent directories. If multiple agents have
    conflicting modifications the user is prompted to choose per-skill.
    For agents: reads from the global agent directory. If multiple tools have
    conflicting modifications the user is prompted to choose.

    Returns a list of (path, status_label) tuples for contributed files.
    """
    from .delta import _find_untracked_local_files

    summary = comparator.compare_from_config(beacon_settings)
    contributable = summary.modified + summary.added

    unregistered_paths: list[str] = []
    if include_unregistered:
        unregistered_paths = [
            p
            for p, _agents in _find_untracked_local_files(
                comparator, beacon_settings, artifacts_dir, ignore_skill_patterns
            )
        ]

    # Collect modified/added agent paths (no beacon.yaml entry needed)
    # Discover from global dirs so agents not yet in warehouse appear as ADDED.
    agent_paths: list[str] = []
    if comparator.agents_paths:
        seen_rel_paths: set[str] = set()
        for _tool, agents_dir in comparator.agents_paths.items():
            if agents_dir.is_dir():
                for agent_file in sorted(agents_dir.rglob("*")):
                    if agent_file.is_file() and agent_file.name != "README.md":
                        seen_rel_paths.add("agents/" + agent_file.name)
        warehouse_agents_dir = warehouse_path / "agents"
        if warehouse_agents_dir.is_dir():
            for agent_file in sorted(warehouse_agents_dir.rglob("*")):
                if agent_file.is_file() and agent_file.name != "README.md":
                    seen_rel_paths.add(str(agent_file.relative_to(warehouse_path)))
        for rel_path in sorted(seen_rel_paths):
            result = comparator._compare_agent_file(rel_path)
            if result.status in (DeltaStatus.MODIFIED, DeltaStatus.ADDED):
                agent_paths.append(rel_path)

    if not contributable and not unregistered_paths and not agent_paths:
        console.print(
            "[green]Nothing to contribute.[/green] "
            "All local artifacts match the warehouse."
        )
        return []

    contributed: list[tuple[str, str]] = []

    for result in contributable:
        is_skill = result.path.startswith("skills/") and bool(comparator.skills_paths)

        if is_skill:
            local_path = _resolve_skill_contribute_source(
                comparator, result.path, artifacts_dir, dry_run=dry_run
            )
            if local_path is None:
                console.print(
                    f"  [yellow]Skipping[/yellow] {result.path} "
                    "(no modified live copy found)"
                )
                continue
        else:
            local_path = artifacts_dir / result.path
            if not local_path.exists():
                console.print(
                    f"  [yellow]Skipping[/yellow] {result.path} (not found locally — run 'abc sync')"
                )
                continue

        _copy_to_warehouse(
            local_path, warehouse_path / result.path, result.path, dry_run
        )
        if is_skill and not dry_run:
            _propagate_skill_to_agents(project_root, result.path, local_path)
        status_label = "modified" if result.status == DeltaStatus.MODIFIED else "added"
        contributed.append((result.path, status_label))

    for rel_path in unregistered_paths:
        is_skill = rel_path.startswith("skills/") and bool(comparator.skills_paths)
        if is_skill:
            # Skills live in live agent dirs, not in artifacts_dir.
            # Pick the first agent copy that exists on disk.
            local_path = None
            for _agent, skills_root in comparator.skills_paths.items():
                parts = Path(rel_path).parts
                skill_relative = (
                    Path(*parts[1:]) if parts[0] == "skills" else Path(rel_path)
                )
                candidate = skills_root / skill_relative
                if candidate.exists():
                    local_path = candidate
                    break
            if local_path is None:
                console.print(
                    f"  [yellow]Skipping[/yellow] {rel_path} (not found in any agent dir)"
                )
                continue
        else:
            local_path = artifacts_dir / rel_path
        _copy_to_warehouse(local_path, warehouse_path / rel_path, rel_path, dry_run)
        contributed.append((rel_path, "added"))

    # Contribute modified agent definitions (always included, no beacon.yaml entry)
    for rel_path in agent_paths:
        local_path = _resolve_agent_contribute_source(
            comparator, rel_path, dry_run=dry_run
        )
        if local_path is None:
            console.print(
                f"  [yellow]Skipping[/yellow] {rel_path} (no modified copy found)"
            )
            continue
        _copy_to_warehouse(local_path, warehouse_path / rel_path, rel_path, dry_run)
        contributed.append((rel_path, "modified"))

    return contributed


def _copy_to_warehouse(
    local_path: Path, dest_path: Path, display_path: str, dry_run: bool
) -> None:
    """Copy a local artifact to the warehouse, creating parent dirs as needed."""
    if dry_run:
        console.print(f"  [dim]Would contribute:[/dim] {display_path}")
        return
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(local_path, dest_path)
    console.print(f"  [green]✓[/green] {display_path}")


def _print_contribute_next_steps(warehouse_path: Path, contributed: list[str]) -> None:
    """Print post-contribute git workflow (used when --manual-git is set)."""
    count = len(contributed)
    console.print(
        f"\n[bold green]✓ Contributed {count} file{'s' if count != 1 else ''} to warehouse[/bold green]"
    )
    console.print(f"  Warehouse: [dim]{warehouse_path}[/dim]\n")
    console.print("[bold]Next Steps — commit the changes in your warehouse:[/bold]")
    console.print(f"\n  cd {warehouse_path}")
    console.print("  git diff                    # Review what changed")
    git_add_args = " ".join(contributed)
    console.print(f"  git add {git_add_args}")
    console.print('  git commit -m "feat: <describe your improvements>"')
    console.print("  git push\n")
    console.print("[dim]Teammates get the changes on their next:[/dim]")
    console.print("  cd ~/team-warehouse && git pull")
    console.print("  cd my-project && abc sync")


def _build_pr_body(contributed: list[tuple[str, str]]) -> str:
    """Build the PR body listing contributed artifacts with their status."""
    lines = ["## Contributed artifacts", ""]
    for path, status in contributed:
        lines.append(f"- `{path}` ({status})")
    return "\n".join(lines)


def _auto_git_contribute(
    warehouse_path: Path,
    contributed: list[tuple[str, str]],
) -> None:
    """Create a branch, commit, push, and open a PR for contributed artifacts.

    Falls back to manual-git output if .git is absent, any git step fails,
    gh is not installed, or the remote is not GitHub.
    """
    paths = [p for p, _ in contributed]
    count = len(paths)

    if not (warehouse_path / ".git").exists():
        console.print(
            "[yellow]Warning:[/yellow] Warehouse has no .git — skipping auto git workflow."
        )
        _print_contribute_next_steps(warehouse_path, paths)
        return

    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    branch = f"contrib/{timestamp}"

    def _git(args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(warehouse_path), *args],
            capture_output=True,
            text=True,
            timeout=30,
        )

    def _fallback(reason: str, detail: str = "") -> None:
        console.print(
            f"[yellow]Warning:[/yellow] {reason} — falling back to manual git."
        )
        if detail:
            console.print(f"  [dim]{detail}[/dim]")
        _print_contribute_next_steps(warehouse_path, paths)

    try:
        r = _git(["checkout", "-b", branch])
        if r.returncode != 0:
            _fallback("Could not create branch", r.stderr.strip())
            return
    except FileNotFoundError:
        _fallback("git not found")
        return
    except subprocess.TimeoutExpired:
        _fallback("git timed out")
        return

    r = _git(["add", "--", *paths])
    if r.returncode != 0:
        _fallback("git add failed", r.stderr.strip())
        return

    r = _git(["commit", "-m", "feat: contribute warehouse artifacts"])
    if r.returncode != 0:
        _fallback("git commit failed", r.stderr.strip())
        return

    r = _git(["push", "-u", "origin", branch])
    if r.returncode != 0:
        _fallback("git push failed", r.stderr.strip())
        return

    pr_body = _build_pr_body(contributed)
    try:
        r = subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--title",
                "feat: contribute warehouse artifacts",
                "--body",
                pr_body,
            ],
            cwd=str(warehouse_path),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if r.returncode != 0:
            console.print(
                "[yellow]Warning:[/yellow] Could not create PR — branch pushed, create PR manually."
            )
            if r.stderr.strip():
                console.print(f"  [dim]{r.stderr.strip()}[/dim]")
            console.print(
                f"\n[bold green]✓ Contributed {count} file{'s' if count != 1 else ''} to warehouse[/bold green]"
            )
            console.print(f"  Branch: [dim]{branch}[/dim]")
            return

        pr_url = r.stdout.strip()
        console.print(
            f"\n[bold green]✓ Contributed {count} file{'s' if count != 1 else ''} to warehouse[/bold green]"
        )
        console.print(f"  PR: [blue]{pr_url}[/blue]")

    except FileNotFoundError:
        console.print(
            "[yellow]Warning:[/yellow] gh not installed — branch pushed, create PR manually."
        )
        console.print(
            f"\n[bold green]✓ Contributed {count} file{'s' if count != 1 else ''} to warehouse[/bold green]"
        )
        console.print(f"  Branch: [dim]{branch}[/dim]")
        console.print(f"  cd {warehouse_path} && gh pr create")
    except subprocess.TimeoutExpired:
        console.print(
            "[yellow]Warning:[/yellow] gh timed out — branch pushed, create PR manually."
        )
        console.print(
            f"\n[bold green]✓ Contributed {count} file{'s' if count != 1 else ''} to warehouse[/bold green]"
        )
        console.print(f"  Branch: [dim]{branch}[/dim]")
