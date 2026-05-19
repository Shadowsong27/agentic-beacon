"""Agent operations for the artifact domain."""

from pathlib import Path

from beacon.core.gitignore import GitignoreManager

_ALL_KNOWN_AGENTS = ["opencode", "claudecode"]


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


def detect_agent_targets(project_root: Path) -> list[str]:
    """Return tool keys whose project-local agent directories exist.

    For agent wiring per project-agent-wiring spec: gate on directory existence,
    NOT on tool config files (which is what detect_agents() checks).

    **Design note — gating signal choice (PER-123, closed).**

    A directory-existence gate is intentionally lenient: ``.claude/`` and
    ``.opencode/`` can be created by ``abc sync`` for non-agent artifacts
    (skill/context wiring), so this function may return a tool key for a
    machine where the tool binary is not actually installed. The resulting
    over-wiring produces extra symlinks under ``.claude/agents/`` /
    ``.opencode/agents/`` — both directories are gitignored, so the cost is
    bounded to wasted bytes.

    Tighter alternatives were considered and rejected:

    - ``shutil.which("claude")`` / ``shutil.which("opencode")`` introduces
      PATH-dependent variance: the same warehouse + project produces
      different wiring outcomes on different developer laptops. That kind
      of machine-local divergence is harder to debug than the current
      harmless over-wiring.
    - Marker-file checks (``CLAUDE.md`` / ``opencode.json``) would create
      an asymmetric ordering dependency where agent wiring requires the
      tool to have run at least once first. That breaks fresh-clone-then-
      ``abc sync`` flows.

    Net: spec-aligned over-wiring is acceptable. If a stronger signal is
    needed in the future, the OpenSpec scenarios in
    ``openspec/specs/project-agent-wiring/`` must be updated alongside the
    implementation.
    """
    targets = []
    if (project_root / ".claude").is_dir():
        targets.append("claudecode")
    if (project_root / ".opencode").is_dir():
        targets.append("opencode")
    return targets


def ensure_agent_dirs_gitignored(project_root: Path) -> None:
    """Ensure `.claude/agents/` and `.opencode/agents/` are in the project root .gitignore.

    Idempotent. Creates the .gitignore file if it does not exist. Delegates
    to `GitignoreManager.ensure_entries` so the agent-dir entries are
    consistent with the rest of Beacon's gitignore management (skill dirs,
    `.agentic-beacon/artifacts/`, etc.).

    Args:
        project_root: Project root directory (must be a directory).

    Raises:
        FileNotFoundError: If project_root is not a directory.
    """
    if not project_root.is_dir():
        raise FileNotFoundError(f"project_root is not a directory: {project_root}")

    GitignoreManager(project_root).ensure_entries(
        [".claude/agents/", ".opencode/agents/"]
    )


def prune_agent_dirs_gitignore_entries(project_root: Path) -> None:
    """Remove `.claude/agents/` and `.opencode/agents/` entries from the project root .gitignore.

    Used when all agents are removed from beacon.yaml — the entries are
    pruned so the project's .gitignore stays in sync with the declared
    artifact set. Idempotent: a no-op if .gitignore is missing or the
    entries are not present.

    Args:
        project_root: Project root directory (must be a directory).

    Raises:
        FileNotFoundError: If project_root is not a directory.
    """
    if not project_root.is_dir():
        raise FileNotFoundError(f"project_root is not a directory: {project_root}")

    GitignoreManager(project_root).remove_entries(
        [".claude/agents/", ".opencode/agents/"]
    )


def snapshot_agent_path(p: Path) -> tuple[str, Path | None]:
    """Snapshot a per-tool agent destination's pre-wire state.

    Used by transactional wiring helpers (e.g. wire_agents_atomically in
    domains/setup/wiring.py) to capture enough state to restore the
    destination if a later wire step fails.

    Returns:
        ("symlink", current_target) — already-wired symlink, target captured.
        ("regular_file", None)      — user-owned file at the destination.
        ("missing", None)           — nothing there yet.
    """
    if p.is_symlink():
        return ("symlink", p.readlink())
    if p.exists():
        return ("regular_file", None)
    return ("missing", None)
