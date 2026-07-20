"""Wiring functions for Beacon CLI setup and sync flows."""

import json
import re
import shutil
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import NamedTuple

import click
from loguru import logger
from rich.console import Console

from beacon.core.exceptions import (
    AgentWireConflict,
    RegularFileConflictError,
)
from beacon.domains.artifact.agent import snapshot_agent_path

console = Console()

# ---------------------------------------------------------------------------
# Context-reference reconciler (AB-96)
# ---------------------------------------------------------------------------

ARTIFACT_REF_PREFIX = ".agentic-beacon/artifacts/"

_ATPATH_LINE_RE = re.compile(r"^@(.+)$")


class ReferenceReconcileResult(NamedTuple):
    """Outcome of reconciling references in a single config file."""

    added: list[str]
    removed: list[str]

    def __bool__(self) -> bool:
        return bool(self.added or self.removed)


def desired_context_refs(effective_contexts: set[str]) -> list[str]:
    """Build the sorted list of desired artifact-context references.

    Each effective-context name is mapped to
    ``.agentic-beacon/artifacts/contexts/{name}.md``, preserving any subpath
    (slashes in the name).
    """
    return sorted(
        f"{ARTIFACT_REF_PREFIX}contexts/{name}.md" for name in effective_contexts
    )


def _resolve_opencode_json(project_root: Path) -> Path | None:
    """Resolve opencode.json (root preferred; .opencode/ fallback)."""
    for candidate in (
        project_root / "opencode.json",
        project_root / ".opencode" / "opencode.json",
    ):
        if candidate.exists():
            return candidate
    return None


def _resolve_claude_md(project_root: Path) -> Path | None:
    """Resolve CLAUDE.md (.claude/CLAUDE.md preferred, then root)."""
    for candidate in (
        project_root / ".claude" / "CLAUDE.md",
        project_root / "CLAUDE.md",
    ):
        if candidate.exists():
            return candidate
    return None


def _reconcile_opencode_json(
    project_root: Path,
    desired_refs: list[str],
    *,
    dry_run: bool = False,
) -> ReferenceReconcileResult:
    """Reconcile opencode.json ``instructions`` to the desired reference set.

    Only entries starting with ``ARTIFACT_REF_PREFIX`` are managed.  The
    ``$schema`` key and user-authored entries are preserved in their original
    relative order.  Writes only when content changes.
    """
    opencode_json = _resolve_opencode_json(project_root)
    if opencode_json is None:
        return ReferenceReconcileResult(added=[], removed=[])

    try:
        data = json.loads(opencode_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ReferenceReconcileResult(added=[], removed=[])

    instructions: list[str] = data.get("instructions", [])
    if not isinstance(instructions, list):
        return ReferenceReconcileResult(added=[], removed=[])

    owned: list[str] = [x for x in instructions if x.startswith(ARTIFACT_REF_PREFIX)]
    kept: list[str] = [x for x in instructions if not x.startswith(ARTIFACT_REF_PREFIX)]

    desired_set = set(desired_refs)
    owned_set = set(owned)

    added = sorted(desired_set - owned_set)
    removed = sorted(owned_set - desired_set)

    if not added and not removed:
        return ReferenceReconcileResult(added=[], removed=[])

    if dry_run:
        return ReferenceReconcileResult(added=added, removed=removed)

    new_instructions = kept + desired_refs
    data["instructions"] = new_instructions
    opencode_json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    return ReferenceReconcileResult(added=added, removed=removed)


def _reconcile_claude_md(
    project_root: Path,
    desired_refs: list[str],
    *,
    dry_run: bool = False,
) -> ReferenceReconcileResult:
    """Reconcile CLAUDE.md ``@``-includes to the desired reference set.

    Only lines whose stripped form starts with ``@ARTIFACT_REF_PREFIX`` are
    managed.  Non-artifact lines (``@AGENTS.md``, etc.) are preserved
    verbatim.  Writes only when content changes.
    """
    claude_md = _resolve_claude_md(project_root)
    if claude_md is None:
        return ReferenceReconcileResult(added=[], removed=[])

    content = claude_md.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)

    owned_refs: set[str] = set()
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        m = _ATPATH_LINE_RE.match(stripped)
        if m:
            path = m.group(1).strip()
            if path.startswith(ARTIFACT_REF_PREFIX):
                owned_refs.add(path)
                continue
        new_lines.append(line)

    desired_set = set(desired_refs)
    added = sorted(desired_set - owned_refs)
    removed = sorted(owned_refs - desired_set)

    if not added and not removed:
        return ReferenceReconcileResult(added=[], removed=[])

    if dry_run:
        return ReferenceReconcileResult(added=added, removed=removed)

    for ref in added:
        new_lines.append(f"@{ref}\n")

    new_content = "".join(new_lines)

    claude_md.write_text(new_content, encoding="utf-8")

    return ReferenceReconcileResult(added=added, removed=removed)


def reconcile_context_references(
    project_root: Path,
    desired_refs: list[str],
    *,
    dry_run: bool = False,
) -> ReferenceReconcileResult:
    """Reconcile context references in both ``opencode.json`` and ``CLAUDE.md``.

    Aggregates the add/remove result across both files.  Under ``dry_run``
    the delta is computed but no files are written.
    """
    oc_result = _reconcile_opencode_json(project_root, desired_refs, dry_run=dry_run)
    cl_result = _reconcile_claude_md(project_root, desired_refs, dry_run=dry_run)

    total_added = list(set(oc_result.added) | set(cl_result.added))
    total_removed = list(set(oc_result.removed) | set(cl_result.removed))

    return ReferenceReconcileResult(
        added=sorted(total_added),
        removed=sorted(total_removed),
    )


def create_beacon_template(path: Path) -> None:
    """Create empty beacon.yaml template with commented examples."""
    template = """\
# beacon.yaml - Declare which warehouse artifacts this project needs.
# Run 'abc sync' after editing to download artifacts.
#
# Skills are tracked at the directory level: skills/code-review/
# Agents are declared per-project in beacon.yaml.artifacts.agents.
# Use 'abc adopt' to wire agents into .claude/agents/ and .opencode/agents/.

artifacts:
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

  agents: []
    # Examples:
    # - agents/spec-planner.md
    # - agents/code-reviewer.md

# ignore: Suppress skills installed by external tools (e.g. openspec) from
#   appearing in warehouse-status reports. Supports fnmatch patterns.
#
# ignore:
#   skills:
#     - "openspec-*"
#     - "opsx-*"
"""
    path.write_text(template)


def wire_contexts_opencode(project_root: Path, artifacts_dir: Path) -> list[str]:
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


def wire_contexts_claudecode(project_root: Path, artifacts_dir: Path) -> list[str]:
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


class SetupResult(NamedTuple):
    """Outcome of setup_project — which files were newly created."""

    opencode_created: bool
    claude_created: bool


def setup_project(beacon_yaml: Path, project_root: Path) -> SetupResult:
    """Bootstrap all project-level scaffolding in one call.

    Creates beacon.yaml from the template and conditionally initializes
    opencode.json and CLAUDE.md (both are no-ops if the files already exist).
    Returns a SetupResult indicating which files were newly created.
    """
    create_beacon_template(beacon_yaml)
    opencode_created = init_opencode_json(project_root)
    claude_created = init_claude_md(project_root)
    return SetupResult(opencode_created=opencode_created, claude_created=claude_created)


def init_opencode_json(project_root: Path) -> bool:
    """Create a minimal opencode.json if one does not already exist.

    Returns True when the file was newly created, False when it already existed.
    """
    opencode_json = project_root / "opencode.json"
    if not opencode_json.exists():
        data = {"$schema": "https://opencode.ai/config.json", "instructions": []}
        opencode_json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return True
    return False


def init_claude_md(project_root: Path) -> bool:
    """Create an empty CLAUDE.md at the project root if none exists.

    Returns True when the file was newly created, False when it already existed.
    """
    claude_md = project_root / "CLAUDE.md"
    if not claude_md.exists():
        claude_md.write_text("", encoding="utf-8")
        return True
    return False


def confirm_prune(orphans: list, *, dry_run: bool = False) -> list[str]:
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


def unwire_pruned_artifacts(
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
            pass

        elif artifact_type == "agents" and len(parts) >= 2:
            agent_filename = parts[1]  # e.g. "spec-planner.md"
            agent_name = Path(agent_filename).stem  # e.g. "spec-planner"
            unwire_agent(project_root, agent_name)

        elif artifact_type == "skills" and len(parts) >= 2:
            skill_name = parts[1]
            unwire_skill(project_root, skill_name)


def unwire_context_opencode(project_root: Path, rel_path: str) -> None:
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


def unwire_context_claudecode(project_root: Path, rel_path: str) -> None:
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


def unwire_skill(project_root: Path, skill_name: str) -> None:
    """Remove a skill's wiring directories for all detected agents."""
    opencode_skill = project_root / ".opencode" / "skills" / skill_name
    if opencode_skill.exists():
        shutil.rmtree(opencode_skill, ignore_errors=True)
        logger.debug("Removed OpenCode skill dir: {}", opencode_skill)

    # Remove current stub and legacy stub (old abc- prefix) for migration
    for cmd_name in (f"{skill_name}.md", f"abc-{skill_name}.md"):
        opencode_cmd = project_root / ".opencode" / "command" / cmd_name
        if opencode_cmd.exists():
            opencode_cmd.unlink(missing_ok=True)
            logger.debug("Removed OpenCode command stub: {}", opencode_cmd)

    claude_skill = project_root / ".claude" / "skills" / skill_name
    if claude_skill.exists():
        shutil.rmtree(claude_skill, ignore_errors=True)
        logger.debug("Removed Claude skill dir: {}", claude_skill)


def wire_agent_claudecode(project_root: Path, artifact_file: Path) -> Path:
    """Create a symlink at .claude/agents/<name>.md pointing at artifact_file.

    Idempotent: if the symlink already points at the same target, it is left
    unchanged. A stale symlink pointing at a different target is replaced.
    The parent directory is created if it does not exist.

    A regular file at the destination is user-owned content. Beacon will not
    overwrite it; a RegularFileConflictError (BeaconSyncError subclass) is
    raised with the conflicting destination attached.

    Args:
        project_root: Project root directory.
        artifact_file: Path to the artifact file (the symlink target).

    Returns:
        Path to the created (or existing) symlink.

    Raises:
        RegularFileConflictError: If a regular file already exists at the
            destination. Subclass of BeaconSyncError.
        OSError: If the parent directory cannot be created or the symlink
            cannot be written.
    """
    dest = project_root / ".claude" / "agents" / artifact_file.name
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.is_symlink():
        try:
            if dest.resolve(strict=False) == artifact_file.resolve(strict=False):
                return dest
        except OSError:
            pass
        dest.unlink()
    elif dest.exists():
        raise RegularFileConflictError(
            conflicts=[
                AgentWireConflict(
                    dest=dest,
                    agent_name=artifact_file.stem,
                    tool="claudecode",
                ),
            ],
        )

    dest.symlink_to(artifact_file)
    logger.debug("Wired agent to .claude/agents/: {}", dest.name)
    return dest


def wire_agent_opencode(project_root: Path, artifact_file: Path) -> Path:
    """Create a symlink at .opencode/agents/<name>.md pointing at artifact_file.

    Idempotent: if the symlink already points at the same target, it is left
    unchanged. A stale symlink pointing at a different target is replaced.
    The parent directory is created if it does not exist.

    A regular file at the destination is user-owned content. Beacon will not
    overwrite it; a RegularFileConflictError (BeaconSyncError subclass) is
    raised with the conflicting destination attached.

    Args:
        project_root: Project root directory.
        artifact_file: Path to the artifact file (the symlink target).

    Returns:
        Path to the created (or existing) symlink.

    Raises:
        RegularFileConflictError: If a regular file already exists at the
            destination. Subclass of BeaconSyncError.
        OSError: If the parent directory cannot be created or the symlink
            cannot be written.
    """
    dest = project_root / ".opencode" / "agents" / artifact_file.name
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.is_symlink():
        try:
            if dest.resolve(strict=False) == artifact_file.resolve(strict=False):
                return dest
        except OSError:
            pass
        dest.unlink()
    elif dest.exists():
        raise RegularFileConflictError(
            conflicts=[
                AgentWireConflict(
                    dest=dest,
                    agent_name=artifact_file.stem,
                    tool="opencode",
                ),
            ],
        )

    dest.symlink_to(artifact_file)
    logger.debug("Wired agent to .opencode/agents/: {}", dest.name)
    return dest


_LEGACY_PARTIAL_WRAPPER_FRONTMATTER = (
    "---\n"
    "description: >-\n"
    "  Internal fragment referenced by other agents \u2014 not a real agent.\n"
    "  Disabled at wire time by Beacon (PER-238).\n"
    "mode: subagent\n"
    "disable: true\n"
    "---\n\n"
)


def _is_beacon_owned_partial_wrapper(dest: Path) -> bool:
    """Return True if ``dest`` is a regular file Beacon previously wrote as a
    partial wrapper.

    We detect Beacon-owned wrappers by the exact legacy frontmatter prefix.
    Any other regular file at the destination is treated as user-owned.

    Returns False on any read error (treat as user-owned, defensively).
    """
    try:
        return dest.read_text(encoding="utf-8").startswith(
            _LEGACY_PARTIAL_WRAPPER_FRONTMATTER
        )
    except OSError:
        return False


def _is_beacon_owned_partial_symlink(path: Path, project_root: Path) -> bool:
    """Return True if ``path`` is a symlink Beacon previously created.

    Beacon-owned partial symlinks (pre-PER-238 layout) always pointed at a
    location inside the project's ``.agentic-beacon/artifacts/`` mirror.
    A symlink whose target resolves anywhere else is treated as
    user-owned: a contributor may have legitimately hand-symlinked their
    own partial into the tool dir, and sync must not silently delete it.

    Returns False on any read error (defensively treat as user-owned).
    """
    try:
        target = path.readlink()
    except OSError:
        return False

    # Resolve the symlink's target relative to the symlink's parent dir
    # so a relative target (the common Beacon shape) is judged correctly.
    if target.is_absolute():
        resolved = target
    else:
        resolved = (path.parent / target).resolve(strict=False)

    artifacts_root = (project_root / ".agentic-beacon" / "artifacts").resolve()
    try:
        resolved.relative_to(artifacts_root)
    except ValueError:
        return False
    return True


def _prune_stale_tool_dir_partials(
    project_root: Path,
    detected_tools: Iterable[str],
) -> list[Path]:
    """Prune Beacon-owned partials from legacy and transitional tool dirs.

    For each candidate path under ``.<tool>/agents/_partials/`` and
    ``.<tool>/agents/agent-partials/``:

    - Symlink whose target resolves inside ``.agentic-beacon/artifacts/``
      → Beacon-owned (legacy PER-164/PER-238 layout); unlink.
    - Symlink whose target resolves elsewhere → user-owned; preserve with a
      warning. Sync must not silently delete a contributor's own symlinked
      partial.
    - Regular file matching the legacy wrapper-frontmatter prefix (via
      ``_is_beacon_owned_partial_wrapper``) → Beacon-owned; unlink.
    - Any other regular file → user-owned; preserve with a warning.

    The ownership-aware policy mirrors the conflict-detection used by
    ``wire_agents_atomically`` for top-level agent paths and addresses the
    PR #159 round-2 review finding that symlinks were being deleted
    unconditionally.
    """
    pruned: list[Path] = []
    tool_roots = {
        "claudecode": project_root / ".claude" / "agents",
        "opencode": project_root / ".opencode" / "agents",
    }

    for tool in detected_tools:
        agents_root = tool_roots.get(tool)
        if agents_root is None:
            continue
        for rel_dir in (Path("_partials"), Path("agent-partials")):
            partial_root = agents_root / rel_dir
            if not partial_root.exists():
                continue
            for path in sorted(partial_root.rglob("*"), reverse=True):
                if path.is_symlink():
                    if _is_beacon_owned_partial_symlink(path, project_root):
                        path.unlink()
                        pruned.append(path)
                    else:
                        logger.warning(
                            "Preserving user-owned partial symlink {} during sync prune.",
                            path,
                        )
                elif path.is_file():
                    if _is_beacon_owned_partial_wrapper(path):
                        path.unlink()
                        pruned.append(path)
                    else:
                        logger.warning(
                            "Preserving user-owned partial path {} during sync prune.",
                            path,
                        )
            for directory in sorted(partial_root.rglob("*"), reverse=True):
                if directory.is_dir():
                    try:
                        directory.rmdir()
                    except OSError:
                        pass
            try:
                partial_root.rmdir()
            except OSError:
                pass
    return pruned


def wire_agents_atomically(
    project_root: Path,
    agent_artifact_files: list[Path],
    detected_tools: Iterable[str],
) -> None:
    """Wire each agent into every detected tool with snapshot-based rollback.

    For every (agent_artifact_file, tool) pair, snapshots the destination's
    pre-wire state, then calls the tool-specific wire_agent_* helper. If any
    wire raises, restores ALL previously-wired destinations to their pre-wire
    state and re-raises the original exception.

    Args:
        project_root: Root of the project (where .claude/ / .opencode/ live).
        agent_artifact_files: Resolved artifact symlink paths
            (e.g. <project>/.agentic-beacon/artifacts/agents/spec-planner.md).
        detected_tools: Iterable of tool keys detected for this project;
            entries outside {"claudecode", "opencode"} are silently ignored
            (forward-compat). Accepts list or set; in practice the orchestrator
            passes the list returned by `detect_agent_targets`.

    Raises:
        Whatever `wire_agent_claudecode` / `wire_agent_opencode` raise
        (typically RegularFileConflictError or BeaconSyncError) — re-raised AFTER rollback.

    Note:
        This helper covers ONLY the per-tool agent paths. It does not
        rollback artifact symlinks under .agentic-beacon/artifacts/agents/
        or any gitignore changes. Callers that need broader transactional
        scope (see apply.commit_session) should compose this with their
        own snapshot machinery in a future refactor.

        The internal _rollback closure is intentionally **best-effort** —
        per-path OSError during restore is logged via loguru.warning and
        swallowed so the original wire exception always surfaces to the
        caller. This differs from apply.py's commit_session rollback,
        which lets restore-step OSError propagate. Rationale: in the sync
        orchestrator the user's primary signal is the original wire
        failure (e.g. "regular file at .claude/agents/foo.md"); masking it
        with a downstream rollback OSError would degrade UX. apply.py
        operates at a tighter atomic boundary (single session commit) where
        any partial restore is itself a correctness concern worth raising.
    """
    # Stale-partial prune runs FIRST, intentionally outside the rollback
    # snapshot. Rationale: prune deletes ONLY Beacon-owned wrappers (gated by
    # _is_beacon_owned_partial_wrapper's exact-prefix check) and stale
    # symlinks; user-authored regular files at partial paths are preserved
    # with a warning. The prune is therefore (a) non-destructive of user
    # content and (b) idempotent — the next sync re-runs the same prune as a
    # no-op. Including it in the rollback transaction would force re-creating
    # Beacon-owned wrappers we just deleted intentionally; on a wire failure,
    # the next successful sync converges to the same end state. Reviewed in
    # PR #159 (gate-artifact-reference-paths phase 4).
    _prune_stale_tool_dir_partials(project_root, detected_tools)

    # Pre-flight: collect ALL regular-file conflicts before touching anything.
    # Aborts with a structured error so the caller can present every blocked
    # destination in one pass rather than failing on the first one found.
    # Use is_file() rather than exists() so a directory (or FIFO/socket) at the
    # dest path is left to surface as a different error class — the rm/mv
    # remediation commands shown in the conflict guide assume regular files.
    pre_conflicts: list[AgentWireConflict] = []
    for artifact_file in agent_artifact_files:
        leaf = artifact_file.name
        if "claudecode" in detected_tools:
            cc_dest = project_root / ".claude" / "agents" / leaf
            if cc_dest.is_file() and not cc_dest.is_symlink():
                pre_conflicts.append(
                    AgentWireConflict(
                        dest=cc_dest,
                        agent_name=artifact_file.stem,
                        tool="claudecode",
                    )
                )
        if "opencode" in detected_tools:
            oc_dest = project_root / ".opencode" / "agents" / leaf
            if oc_dest.is_file() and not oc_dest.is_symlink():
                pre_conflicts.append(
                    AgentWireConflict(
                        dest=oc_dest,
                        agent_name=artifact_file.stem,
                        tool="opencode",
                    )
                )

    if pre_conflicts:
        raise RegularFileConflictError(conflicts=pre_conflicts)

    snapshots: list[tuple[Path, str, Path | str | None]] = []

    def _rollback() -> None:
        for path, kind, prior in reversed(snapshots):
            try:
                if kind == "missing":
                    if path.is_symlink() or path.exists():
                        path.unlink()
                elif kind == "symlink":
                    assert isinstance(prior, Path)
                    if path.is_symlink():
                        if path.readlink() != prior:
                            path.unlink()
                            path.symlink_to(prior)
                    else:
                        if path.exists():
                            path.unlink()
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.symlink_to(prior)
                elif kind == "wrapper_file":
                    # PER-238 round-2: a refreshed wrapper must be restored
                    # to its pre-wire content if a later wire step fails.
                    assert isinstance(prior, str)
                    if path.is_symlink():
                        path.unlink()
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(prior, encoding="utf-8")
                # "regular_file" snapshots imply wire never succeeded for
                # that path (the wire helpers refuse to overwrite user-owned
                # regular files), so no restore is needed.
            except OSError as e:
                logger.warning(
                    "wire_agents_atomically: rollback step failed for "
                    "{} (kind={}, prior={}): {}. "
                    "Continuing with remaining snapshots; "
                    "post-failure state may be partially restored.",
                    path,
                    kind,
                    prior,
                    e,
                )

    try:
        for artifact_file in agent_artifact_files:
            leaf = artifact_file.name
            if "claudecode" in detected_tools:
                cc_dest = project_root / ".claude" / "agents" / leaf
                snapshots.append((cc_dest, *snapshot_agent_path(cc_dest)))
                wire_agent_claudecode(project_root, artifact_file)
            if "opencode" in detected_tools:
                oc_dest = project_root / ".opencode" / "agents" / leaf
                snapshots.append((oc_dest, *snapshot_agent_path(oc_dest)))
                wire_agent_opencode(project_root, artifact_file)

    except Exception:
        _rollback()
        raise


def _is_beacon_symlink(dest: Path, expected_artifact: Path) -> bool:
    """Return True if dest is a symlink whose resolved target matches expected_artifact.

    Handles both absolute and relative symlink targets. Returns False on any
    OSError (e.g. permission denied reading the link), treating the path as
    user-owned in that case.
    """
    try:
        raw_target = dest.readlink()
    except OSError:
        return False
    if not raw_target.is_absolute():
        raw_target = dest.parent / raw_target
    return raw_target.resolve(strict=False) == expected_artifact


def unwire_agent(project_root: Path, agent_name: str) -> None:
    """Remove project-local agent symlinks for the given agent.

    Only symlinks whose target resolves to .agentic-beacon/artifacts/agents/<name>.md
    are removed. Symlinks pointing elsewhere are preserved with a warning (treated as
    user-owned content). A regular file at the agent path is also left untouched.

    Removes both .claude/agents/<agent_name>.md and
    .opencode/agents/<agent_name>.md if they are Beacon-owned symlinks. Missing
    files are silently skipped. Does not traverse subdirectories.

    Args:
        project_root: Project root directory.
        agent_name: Stem name of the agent (without .md extension), or full
            filename. Only the leaf name is used to avoid path traversal.
    """
    # Normalise to leaf filename (prevent any subdirectory traversal)
    leaf = Path(agent_name).name
    if not leaf.endswith(".md"):
        leaf = leaf + ".md"

    expected_artifact = (
        project_root / ".agentic-beacon" / "artifacts" / "agents" / leaf
    ).resolve(strict=False)

    for dest in (
        project_root / ".claude" / "agents" / leaf,
        project_root / ".opencode" / "agents" / leaf,
    ):
        if dest.is_symlink():
            if not _is_beacon_symlink(dest, expected_artifact):
                logger.warning(
                    "Skipping unwire of {}: symlink points outside "
                    ".agentic-beacon/artifacts/agents/; treating as user-owned.",
                    dest,
                )
                continue
            dest.unlink()
            logger.debug("Unwired agent: {}", dest)
        elif dest.exists():
            logger.warning(
                "Skipping unwire of {}: regular file (not a Beacon symlink); "
                "left untouched. Remove manually if intended.",
                dest,
            )


def unwire_agent_with_undo(
    project_root: Path,
    agent_name: str,
    _unlink_fn: Callable[[Path], None] | None = None,
) -> list[tuple[Path, Path]]:
    """Remove project-local agent symlinks, returning (path, target) pairs for rollback.

    Only symlinks whose target resolves to .agentic-beacon/artifacts/agents/<name>.md
    are removed and recorded. Symlinks pointing elsewhere are preserved with a warning
    (treated as user-owned). A regular file at the agent path is also left untouched.

    Like unwire_agent but returns a list of (removed_path, original_target) tuples
    for each symlink removed, enabling callers to reconstruct them on rollback.
    User-owned symlinks that are skipped are NOT included in the returned list.

    Args:
        project_root: Project root directory.
        agent_name: Stem name of the agent (without .md extension), or full filename.
        _unlink_fn: Callable used to unlink each symlink; defaults to Path.unlink.
            Provided for testing rollback scenarios; production code never passes this.

    Returns:
        List of (path, target) pairs for each symlink successfully removed.
        User-owned symlinks and regular files at the agent paths are not included.
    """
    unlink_fn: Callable[[Path], None] = _unlink_fn or Path.unlink

    leaf = Path(agent_name).name
    if not leaf.endswith(".md"):
        leaf = leaf + ".md"

    expected_artifact = (
        project_root / ".agentic-beacon" / "artifacts" / "agents" / leaf
    ).resolve(strict=False)

    removed: list[tuple[Path, Path]] = []
    for dest in (
        project_root / ".claude" / "agents" / leaf,
        project_root / ".opencode" / "agents" / leaf,
    ):
        if dest.is_symlink():
            if not _is_beacon_symlink(dest, expected_artifact):
                logger.warning(
                    "Skipping unwire of {}: symlink points outside "
                    ".agentic-beacon/artifacts/agents/; treating as user-owned.",
                    dest,
                )
                continue
            target = dest.readlink()
            unlink_fn(dest)
            removed.append((dest, target))
            logger.debug("Unwired agent: {}", dest)
        elif dest.exists():
            logger.warning(
                "Skipping unwire of {}: regular file (not a Beacon symlink); "
                "left untouched. Remove manually if intended.",
                dest,
            )
    return removed


def has_synced_contexts(artifacts_dir: Path) -> bool:
    """Check if any context files exist in the artifacts directory."""
    contexts_dir = artifacts_dir / "contexts"
    if not contexts_dir.exists():
        return False
    return any(contexts_dir.rglob("*.md"))
