"""Agent operations for the artifact domain."""

from pathlib import Path

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
    """
    targets = []
    if (project_root / ".claude").exists():
        targets.append("claudecode")
    if (project_root / ".opencode").exists():
        targets.append("opencode")
    return targets


def update_agent_gitignores(project_root: Path) -> None:
    """Append .claude/agents/ and .opencode/agents/ entries to the project .gitignore.

    Idempotent: if the entries are already present they are not added again.
    Creates the .gitignore file if it does not exist.

    Args:
        project_root: Project root directory (must be a directory).

    Raises:
        FileNotFoundError: If project_root is not a directory.
    """
    if not project_root.is_dir():
        raise FileNotFoundError(f"project_root is not a directory: {project_root}")

    gitignore_path = project_root / ".gitignore"
    entries_to_add = [".claude/agents/", ".opencode/agents/"]

    if gitignore_path.exists():
        existing_content = gitignore_path.read_text(encoding="utf-8")
        existing_lines = set(existing_content.splitlines())
    else:
        existing_content = ""
        existing_lines = set()

    missing = [e for e in entries_to_add if e not in existing_lines]
    if not missing:
        return

    if existing_content and not existing_content.endswith("\n"):
        prefix = "\n"
    else:
        prefix = ""

    new_content = existing_content + prefix + "\n".join(missing) + "\n"
    gitignore_path.write_text(new_content, encoding="utf-8")
