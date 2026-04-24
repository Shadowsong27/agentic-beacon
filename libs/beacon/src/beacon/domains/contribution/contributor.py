"""Contribute utility functions for Beacon CLI."""

import datetime
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from rich.console import Console

from beacon.core.exceptions import ContributeError
from beacon.core.manifest.beacon import BeaconManifest
from beacon.domains.distribution.delta import DeltaComparator, DeltaStatus

console = Console()


def resolve_skill_contribute_source(
    comparator: DeltaComparator,
    relative_path: str,
    artifacts_dir: Path,
    dry_run: bool = False,
    chooser: Callable[[dict[str, Path]], str] | None = None,
) -> Path | None:
    """Resolve which file to read when contributing a skill back to the warehouse.

    Skills live in agent-specific directories (.opencode/skills/, .claude/skills/).
    We need to decide which copy to contribute when multiple agents are present.

    Rules:
    - No agents configured → fall back to artifact snapshot (backward compat).
    - One agent modified/added → use that agent's copy.
    - Multiple agents modified/added with identical content → use any (they agree).
    - Multiple agents modified/added with different content → call ``chooser`` to pick.
    - No agent has a modified or added copy → return None.

    ``chooser`` receives a dict of {agent_name: path} and must return the chosen
    agent name. Defaults to picking the first candidate (non-interactive).

    Returns the absolute Path of the file to copy, or None if nothing to contribute.
    """
    if not comparator.skills_paths:
        # No agents detected — fall back to artifact snapshot
        return artifacts_dir / relative_path

    result = comparator.compare_file(relative_path)

    # Collect agents whose live copy differs from warehouse (modified or added)
    changed_agents = [
        agent
        for agent, status in result.agent_statuses.items()
        if status in (DeltaStatus.MODIFIED, DeltaStatus.ADDED)
    ]

    if not changed_agents:
        # Nothing changed in any live dir — nothing to contribute
        return None

    # Build the candidate paths for changed agents
    candidates: dict[str, Path] = {}
    for agent in changed_agents:
        live_path = comparator.skill_live_path(agent, relative_path)
        if live_path.exists():
            candidates[agent] = live_path

    if not candidates:
        return None

    if len(candidates) == 1:
        return next(iter(candidates.values()))

    # Multiple agents have changed versions — check if they are identical
    hashes = {
        agent: comparator.compute_hash(path) for agent, path in candidates.items()
    }
    unique_hashes = set(hashes.values())

    if len(unique_hashes) == 1:
        # All changed copies are identical — pick the first one
        return next(iter(candidates.values()))

    # Genuinely different versions across agents.
    # During a dry-run preview, skip the interactive prompt and just report the conflict.
    if dry_run:
        console.print(
            f"\n[yellow]Conflict:[/yellow] '{relative_path}' has been modified differently "
            "across agents — you will be prompted to choose when you confirm.\n"
        )
        return next(iter(candidates.values()))  # placeholder; not used in dry-run

    # Delegate the choice to the caller-supplied chooser (CLI owns interactive UX).
    console.print(
        f"\n[yellow]Conflict:[/yellow] '{relative_path}' has been modified differently across agents:\n"
    )
    agent_list = list(candidates.keys())
    for i, agent in enumerate(agent_list, 1):
        live_path = candidates[agent]
        console.print(f"  [{i}] {agent}")
        console.print(f"      [dim]{live_path}[/dim]")
    console.print()

    _chooser = chooser or (lambda c: next(iter(c)))
    chosen_agent = _chooser(candidates)
    console.print(f"  Using [bold]{chosen_agent}[/bold] version.\n")
    return candidates[chosen_agent]


def _get_skill_dir_from_path(relative_path: str) -> str:
    """Extract skill directory from a path like 'skills/foo/SKILL.md'."""
    parts = Path(relative_path).parts
    if len(parts) >= 2 and parts[0] == "skills":
        return f"{parts[0]}/{parts[1]}"
    return relative_path


def propagate_skill_to_agents(
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


def resolve_agent_contribute_source(
    comparator: DeltaComparator,
    relative_path: str,
    dry_run: bool = False,
    chooser: Callable[[dict[str, Path]], str] | None = None,
) -> Path | None:
    """Resolve which global agent file to read when contributing back to the warehouse.

    Agent files live in global directories (~/.config/opencode/agents/ or
    ~/.claude/agents/). The logic mirrors resolve_skill_contribute_source:

    - No agents configured → return None (nothing to contribute).
    - One tool has a modified or new copy → use it.
    - Multiple tools modified/added with identical content → use any.
    - Multiple tools modified/added with different content → call ``chooser`` to pick.
    - No tool has a modified or new copy → return None (identical to warehouse).

    ``chooser`` receives a dict of {tool_name: path} and must return the chosen tool
    name. Defaults to picking the first candidate (non-interactive).

    Returns the absolute Path of the file to copy, or None if nothing to contribute.
    """
    if not comparator.agents_paths:
        return None

    result = comparator.compare_agent_file(relative_path)

    contributable_tools = [
        tool
        for tool, status in result.agent_statuses.items()
        if status in (DeltaStatus.MODIFIED, DeltaStatus.ADDED)
    ]

    if not contributable_tools:
        return None

    candidates: dict[str, Path] = {}
    for tool in contributable_tools:
        live_path = comparator.agent_live_path(tool, relative_path)
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

    # Genuinely different — report or delegate to caller-supplied chooser
    if dry_run:
        console.print(
            f"\n[yellow]Conflict:[/yellow] '{relative_path}' has been modified differently "
            "across tools — you will be prompted to choose when you confirm.\n"
        )
        return next(iter(candidates.values()))  # placeholder; not used in dry-run

    console.print(
        f"\n[yellow]Conflict:[/yellow] '{relative_path}' has been modified differently across tools:\n"
    )
    for i, (tool, path) in enumerate(candidates.items(), 1):
        console.print(f"  [{i}] {tool}")
        console.print(f"      [dim]{path}[/dim]")
    console.print()

    _chooser = chooser or (lambda c: next(iter(c)))
    chosen = _chooser(candidates)
    console.print(f"  Using [bold]{chosen}[/bold] version.\n")
    return candidates[chosen]


def contribute_single(
    comparator: DeltaComparator,
    beacon_settings: BeaconManifest,
    warehouse_path: Path,
    artifacts_dir: Path,
    file_path: str,
    dry_run: bool,
    project_root: Path,
    chooser: Callable[[dict[str, Path]], str] | None = None,
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
    is_skill = file_path.startswith("skills/") and bool(comparator.skills_paths)
    is_agent = file_path.startswith("agents/") and bool(comparator.agents_paths)

    if is_skill:
        # Resolve the live agent source (may invoke chooser if multiple agents conflict)
        local_path = resolve_skill_contribute_source(
            comparator, file_path, artifacts_dir, dry_run=dry_run, chooser=chooser
        )
        if local_path is None:
            console.print(
                f"[yellow]Nothing to contribute.[/yellow] "
                f"'{file_path}' is identical to the warehouse version across all agents."
            )
            return []
    elif is_agent:
        local_path = resolve_agent_contribute_source(
            comparator, file_path, dry_run=dry_run, chooser=chooser
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
            raise ContributeError(
                f"'{file_path}' does not exist locally.\n"
                "Create the file in .agentic-beacon/artifacts/ first, then contribute it."
            )

    if not is_skill and not is_agent:
        result = comparator.compare_file(file_path)
        if result.status == DeltaStatus.IDENTICAL:
            console.print(
                f"[yellow]Nothing to contribute.[/yellow] "
                f"'{file_path}' is identical to the warehouse version."
            )
            return []

    dest_existed = (warehouse_path / file_path).exists()
    copy_to_warehouse(local_path, warehouse_path / file_path, file_path, dry_run)
    if is_skill and not dry_run:
        propagate_skill_to_agents(project_root, file_path, local_path)
    status_label = "modified" if dest_existed else "added"
    return [(file_path, status_label)]


def contribute_all(
    comparator: DeltaComparator,
    beacon_settings: BeaconManifest,
    warehouse_path: Path,
    artifacts_dir: Path,
    dry_run: bool,
    project_root: Path,
    include_unregistered: bool = False,
    ignore_skill_patterns: list[str] | None = None,
    chooser: Callable[[dict[str, Path]], str] | None = None,
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
    from beacon.domains.contribution.delta_view import find_untracked_local_files

    summary = comparator.compare_from_config(beacon_settings)
    contributable = summary.modified + summary.added

    unregistered_paths: list[str] = []
    if include_unregistered:
        unregistered_paths = [
            p
            for p, _agents in find_untracked_local_files(
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
            result = comparator.compare_agent_file(rel_path)
            if result.status in (DeltaStatus.MODIFIED, DeltaStatus.ADDED):
                agent_paths.append(rel_path)

    if not contributable and not unregistered_paths and not agent_paths:
        console.print(
            "[green]Nothing to contribute.[/green] "
            "All local artifacts match the warehouse."
        )
        return []

    contributed: list[tuple[str, str]] = []

    # Separate skill and non-skill results
    skill_results = []
    non_skill_results = []
    for result in contributable:
        if result.path.startswith("skills/") and comparator.skills_paths:
            skill_results.append(result)
        else:
            non_skill_results.append(result)

    # Group skill results by skill directory and contribute as whole units
    skill_dirs: dict[str, list] = {}
    for result in skill_results:
        skill_dir = _get_skill_dir_from_path(result.path)
        skill_dirs.setdefault(skill_dir, []).append(result)

    for skill_dir, results in skill_dirs.items():
        # Use the first file to resolve which agent to contribute from
        first_file = results[0].path
        local_path = resolve_skill_contribute_source(
            comparator, first_file, artifacts_dir, dry_run=dry_run, chooser=chooser
        )
        if local_path is None:
            console.print(
                f"  [yellow]Skipping[/yellow] {skill_dir}/ "
                "(no modified live copy found)"
            )
            continue

        # Determine the source skill directory from the chosen file
        skill_name = Path(skill_dir).name
        source_dir = local_path.parent
        # Walk up to find the skill root directory
        while source_dir.name != skill_name and source_dir.parent != source_dir:
            source_dir = source_dir.parent

        if source_dir.name != skill_name:
            console.print(
                f"  [yellow]Skipping[/yellow] {skill_dir}/ "
                "(could not find skill directory)"
            )
            continue

        dest_dir = warehouse_path / skill_dir

        # Determine if this is a modification or addition based on warehouse state
        dest_existed = dest_dir.exists()
        status_label = "modified" if dest_existed else "added"

        # Copy entire skill directory
        if not dry_run:
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(source_dir, dest_dir)
        else:
            console.print(f"  Would contribute: {skill_dir}/ ({status_label})")

        # Propagate to all agents
        if not dry_run:
            skill_md = dest_dir / "SKILL.md"
            if skill_md.exists():
                propagate_skill_to_agents(
                    project_root, f"{skill_dir}/SKILL.md", skill_md
                )

        contributed.append((f"{skill_dir}/", status_label))

    # Handle non-skill results individually
    for result in non_skill_results:
        local_path = artifacts_dir / result.path
        if not local_path.exists():
            console.print(
                f"  [yellow]Skipping[/yellow] {result.path} (not found locally — run 'abc sync')"
            )
            continue

        copy_to_warehouse(
            local_path, warehouse_path / result.path, result.path, dry_run
        )
        status_label = "modified" if result.status == DeltaStatus.MODIFIED else "added"
        contributed.append((result.path, status_label))

    # Handle unregistered paths
    unregistered_skill_dirs: set[str] = set()
    unregistered_non_skill: list[str] = []

    for rel_path in unregistered_paths:
        if rel_path.startswith("skills/") and comparator.skills_paths:
            skill_dir = _get_skill_dir_from_path(rel_path)
            unregistered_skill_dirs.add(skill_dir)
        else:
            unregistered_non_skill.append(rel_path)

    # Contribute unregistered skills as whole directories
    for skill_dir in sorted(unregistered_skill_dirs):
        skill_name = Path(skill_dir).name
        # Pick the first agent that has this skill
        source_dir = None
        for _agent, skills_root in comparator.skills_paths.items():
            candidate = skills_root / skill_name
            if candidate.exists():
                source_dir = candidate
                break
        if source_dir is None:
            console.print(
                f"  [yellow]Skipping[/yellow] {skill_dir}/ (not found in any agent dir)"
            )
            continue

        dest_dir = warehouse_path / skill_dir
        dest_existed = dest_dir.exists()

        if not dry_run:
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(source_dir, dest_dir)
        else:
            console.print(f"  Would contribute: {skill_dir}/ (added)")

        if not dry_run:
            skill_md = dest_dir / "SKILL.md"
            if skill_md.exists():
                propagate_skill_to_agents(
                    project_root, f"{skill_dir}/SKILL.md", skill_md
                )

        contributed.append((f"{skill_dir}/", "added"))

    # Contribute unregistered non-skill files individually
    for rel_path in unregistered_non_skill:
        local_path = artifacts_dir / rel_path
        copy_to_warehouse(local_path, warehouse_path / rel_path, rel_path, dry_run)
        contributed.append((rel_path, "added"))

    # Contribute modified agent definitions (always included, no beacon.yaml entry)
    for rel_path in agent_paths:
        local_path = resolve_agent_contribute_source(
            comparator, rel_path, dry_run=dry_run, chooser=chooser
        )
        if local_path is None:
            console.print(
                f"  [yellow]Skipping[/yellow] {rel_path} (no modified copy found)"
            )
            continue
        copy_to_warehouse(local_path, warehouse_path / rel_path, rel_path, dry_run)
        contributed.append((rel_path, "modified"))

    return contributed


def copy_to_warehouse(
    local_path: Path, dest_path: Path, display_path: str, dry_run: bool
) -> None:
    """Copy a local artifact to the warehouse, creating parent dirs as needed."""
    if dry_run:
        console.print(f"  [dim]Would contribute:[/dim] {display_path}")
        return
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(local_path, dest_path)
    console.print(f"  [green]✓[/green] {display_path}")


def print_contribute_next_steps(warehouse_path: Path, contributed: list[str]) -> None:
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


def build_pr_body(contributed: list[tuple[str, str]]) -> str:
    """Build the PR body listing contributed artifacts with their status."""
    lines = ["## Contributed artifacts", ""]
    for path, status in contributed:
        lines.append(f"- `{path}` ({status})")
    return "\n".join(lines)


def auto_git_contribute(
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
        print_contribute_next_steps(warehouse_path, paths)
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
        print_contribute_next_steps(warehouse_path, paths)

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

    pr_body = build_pr_body(contributed)
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
