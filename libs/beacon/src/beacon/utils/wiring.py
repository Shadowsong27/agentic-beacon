"""Wiring utility functions for Beacon CLI."""

import json
import shutil
import sys
from pathlib import Path

import click
from loguru import logger
from rich.console import Console

console = Console()


def _create_beacon_template(path: Path) -> None:
    """Create empty beacon.yaml template with commented examples."""
    template = """\
# beacon.yaml - Declare which warehouse artifacts this project needs.
# Run 'abc sync' after editing to download artifacts.
#
# Supports glob patterns: knowledge/languages/python/**/*.md
# Skills are tracked at the directory level: skills/code-review/

artifacts:
  knowledge: []
    # Examples:
    # - knowledge/languages/python/**/*.md
    # - knowledge/infrastructure/docker-standards.md

  skills: []
    # Examples:
    # - skills/code-review/
    # - skills/generate-unit-tests/
    # Note: abc bundled skills (e.g. record-knowledge) are installed globally
    #       into ~/.config/opencode/skills/ and ~/.claude/skills/ by 'abc sync'
    #       — they are not project-scoped and need no entry here.

  contexts: []
    # Examples:
    # - contexts/README.md
    # - contexts/teams/backend/README.md

# ignore: Suppress skills installed by external tools (e.g. openspec) from
#   appearing in 'abc delta' and 'abc contribute'. Supports fnmatch patterns.
#
# ignore:
#   skills:
#     - "openspec-*"
#     - "opsx-*"
"""
    path.write_text(template)


def _install_project_setup_skill(beacon_dir: Path) -> None:
    """Install project-setup skill and generate warehouse catalog.

    This generates a warehouse catalog file that AI agents can read
    to understand what artifacts are available and populate beacon.yaml.
    """
    from ..core.settings import WarehouseSettings
    from .catalog import _generate_warehouse_catalog

    try:
        config_file = beacon_dir / "config.toml"
        if not config_file.exists():
            return

        settings = WarehouseSettings()
        warehouse_path = Path(settings.warehouse.local_path)

        if not warehouse_path.exists():
            console.print(
                "[yellow]Warning:[/yellow] Warehouse path not found, skipping catalog generation"
            )
            return

        # Generate warehouse catalog
        catalog = _generate_warehouse_catalog(warehouse_path)
        catalog_path = beacon_dir / "warehouse-catalog.md"
        catalog_path.write_text(catalog, encoding="utf-8")

    except Exception as e:
        console.print(f"[yellow]Warning:[/yellow] Could not generate catalog: {e}")


def _wire_contexts_opencode(project_root: Path, artifacts_dir: Path) -> list[str]:
    """Append synced context paths to opencode.json instructions.

    Returns the list of paths that were newly added (empty if nothing changed
    or opencode.json does not exist).
    """
    opencode_json = project_root / "opencode.json"
    if not opencode_json.exists():
        return []

    contexts_dir = artifacts_dir / "contexts"
    if not contexts_dir.exists():
        return []

    ctx_files = sorted(contexts_dir.rglob("*.md"))
    if not ctx_files:
        return []

    try:
        data = json.loads(opencode_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    instructions: list[str] = data.get("instructions", [])
    added: list[str] = []

    for ctx_file in ctx_files:
        rel_path = str(ctx_file.relative_to(project_root))
        if rel_path not in instructions:
            instructions.append(rel_path)
            added.append(rel_path)

    if added:
        data["instructions"] = instructions
        opencode_json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    return added


def _wire_contexts_claudecode(project_root: Path, artifacts_dir: Path) -> list[str]:
    """Append synced context @-references to CLAUDE.md.

    Checks .claude/CLAUDE.md then root CLAUDE.md. Returns the list of paths
    that were newly added (empty if nothing changed or no CLAUDE.md found).
    """
    claude_md = next(
        (
            p
            for p in [
                project_root / ".claude" / "CLAUDE.md",
                project_root / "CLAUDE.md",
            ]
            if p.exists()
        ),
        None,
    )
    if claude_md is None:
        return []

    contexts_dir = artifacts_dir / "contexts"
    if not contexts_dir.exists():
        return []

    ctx_files = sorted(contexts_dir.rglob("*.md"))
    if not ctx_files:
        return []

    existing = claude_md.read_text(encoding="utf-8")
    lines_to_append: list[str] = []
    added: list[str] = []

    for ctx_file in ctx_files:
        rel_path = str(ctx_file.relative_to(project_root))
        ref = f"@{rel_path}"
        if ref not in existing:
            lines_to_append.append(ref)
            added.append(rel_path)

    if lines_to_append:
        separator = "\n" if existing.endswith("\n") else "\n\n"
        claude_md.write_text(
            existing + separator + "\n".join(lines_to_append) + "\n",
            encoding="utf-8",
        )

    return added


def _init_opencode_json(project_root: Path) -> None:
    """Create a minimal opencode.json if one does not already exist."""
    opencode_json = project_root / "opencode.json"
    if not opencode_json.exists():
        data = {"$schema": "https://opencode.ai/config.json", "instructions": []}
        opencode_json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _init_claude_md(project_root: Path) -> None:
    """Create an empty CLAUDE.md at the project root if none exists."""
    claude_md = project_root / "CLAUDE.md"
    if not claude_md.exists():
        claude_md.write_text("", encoding="utf-8")


def _confirm_prune(orphans: list, *, dry_run: bool = False) -> list[str]:
    """Prompt the user to confirm deletion of orphaned artifacts.

    Orphans are files that exist in artifacts/ but are no longer listed in
    beacon.yaml AND exist in the warehouse (so they were previously synced).
    Files that do not exist in the warehouse are new contributions and are
    never passed here.

    Modified orphans (local content differs from warehouse) are listed
    separately with a stronger warning.

    In dry-run mode this function always returns an empty list (nothing to
    actually delete) but still prints the preview list.

    Returns:
        List of relative paths the user confirmed for deletion.
        Empty list if the user said no, or if dry_run=True.
    """
    if not orphans:
        return []

    safe = [o for o in orphans if not o.is_modified]
    modified = [o for o in orphans if o.is_modified]

    console.print(
        "\n[yellow]The following artifact(s) are no longer in beacon.yaml:[/yellow]"
    )
    for o in safe:
        console.print(f"  [dim]•[/dim] {o.rel_path}")
    if modified:
        console.print(
            "\n[red]These artifact(s) have local modifications and are no longer in beacon.yaml:[/red]"
        )
        for o in modified:
            console.print(f"  [red]•[/red] {o.rel_path} [dim](locally modified)[/dim]")

    if dry_run:
        console.print(
            "\n  [dim]Dry run — no files will be deleted. "
            "Run without --dry-run to apply.[/dim]"
        )
        return []

    # Always ask, even for the safe (unmodified) list
    if not click.confirm(
        f"\nDelete {len(orphans)} artifact(s) from .agentic-beacon/artifacts/?",
        default=False,
    ):
        console.print("  [dim]Skipped — orphaned artifacts left in place.[/dim]")
        return []

    # For modified files, ask again individually
    confirmed: list[str] = []
    for o in safe:
        confirmed.append(o.rel_path)
    for o in modified:
        if click.confirm(
            f"  Delete '{o.rel_path}' (has local changes — changes will be lost)?",
            default=False,
        ):
            confirmed.append(o.rel_path)
        else:
            console.print(f"  [dim]Kept: {o.rel_path}[/dim]")

    return confirmed


def _unwire_pruned_artifacts(
    project_root: Path, pruned_paths: list[str], artifacts_dir: Path
) -> None:
    """Remove wiring for pruned artifacts from agent config files.

    For each pruned path:
    - If it's a context (contexts/**/*.md): remove from opencode.json instructions
      and from CLAUDE.md @-references.
    - If it's a skill (skills/<name>/SKILL.md): remove .opencode/skills/<name>/
      and .claude/skills/<name>/ directories.

    Args:
        project_root: Project root directory.
        pruned_paths: Relative paths (under artifacts/) that were deleted.
        artifacts_dir: Path to .agentic-beacon/artifacts/.
    """
    for rel_path in pruned_paths:
        parts = Path(rel_path).parts
        if not parts:
            continue

        artifact_type = parts[0]

        if artifact_type == "contexts":
            # Path inside artifacts_dir
            artifact_abs = artifacts_dir / rel_path
            rel_to_project = str(artifact_abs.relative_to(project_root))
            _unwire_context_opencode(project_root, rel_to_project)
            _unwire_context_claudecode(project_root, rel_to_project)

        elif artifact_type == "skills" and len(parts) >= 2:
            skill_name = parts[1]
            _unwire_skill(project_root, skill_name)


def _unwire_context_opencode(project_root: Path, rel_path: str) -> None:
    """Remove a context path from opencode.json instructions."""
    opencode_json = project_root / "opencode.json"
    if not opencode_json.exists():
        return
    try:
        data = json.loads(opencode_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    instructions: list[str] = data.get("instructions", [])
    if rel_path in instructions:
        instructions.remove(rel_path)
        data["instructions"] = instructions
        opencode_json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        logger.debug("Unwired context from opencode.json: {}", rel_path)


def _unwire_context_claudecode(project_root: Path, rel_path: str) -> None:
    """Remove a context @-reference from CLAUDE.md."""
    claude_md = next(
        (
            p
            for p in [
                project_root / ".claude" / "CLAUDE.md",
                project_root / "CLAUDE.md",
            ]
            if p.exists()
        ),
        None,
    )
    if claude_md is None:
        return
    ref = f"@{rel_path}"
    content = claude_md.read_text(encoding="utf-8")
    if ref not in content:
        return
    # Remove the line containing the reference
    lines = content.splitlines(keepends=True)
    new_lines = [line for line in lines if line.strip() != ref]
    claude_md.write_text("".join(new_lines), encoding="utf-8")
    logger.debug("Unwired context from CLAUDE.md: {}", rel_path)


def _unwire_skill(project_root: Path, skill_name: str) -> None:
    """Remove a skill's wiring directories for all detected agents."""
    opencode_skill = project_root / ".opencode" / "skills" / skill_name
    if opencode_skill.exists():
        shutil.rmtree(opencode_skill, ignore_errors=True)
        logger.debug("Removed OpenCode skill dir: {}", opencode_skill)

    opencode_cmd = project_root / ".opencode" / "command" / f"{skill_name}.md"
    if opencode_cmd.exists():
        opencode_cmd.unlink(missing_ok=True)
        logger.debug("Removed OpenCode command stub: {}", opencode_cmd)

    claude_skill = project_root / ".claude" / "skills" / skill_name
    if claude_skill.exists():
        shutil.rmtree(claude_skill, ignore_errors=True)
        logger.debug("Removed Claude skill dir: {}", claude_skill)


def _is_interactive() -> bool:
    """Return True if running in an interactive terminal."""
    return sys.stdin.isatty()
