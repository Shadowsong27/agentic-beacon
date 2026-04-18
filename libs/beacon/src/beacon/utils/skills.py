"""Skill utility functions for Beacon CLI."""

import fnmatch
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from ..core.manifest import ArtifactsConfig, BeaconManifest

console = Console()


def _bundled_global_skill_dirs() -> dict[str, Path]:
    """Return global agent skill directories for bundled skill installation.

    These are the user-level skill dirs read by opencode and Claude Code
    regardless of which project is active.
    """
    return {
        "opencode": Path.home() / ".config" / "opencode" / "skills",
        "claudecode": Path.home() / ".claude" / "skills",
    }


def _bundled_skill_names() -> set[str]:
    """Return the set of skill names that are managed by abc (bundled)."""
    bundled_dir = Path(__file__).parent.parent / "data" / "skills"
    if not bundled_dir.exists():
        return set()
    return {
        d.name
        for d in bundled_dir.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    }


def _build_skills_paths(project_root: Path) -> dict[str, Path]:
    """Return a mapping of agent name → live skills directory for detected agents.

    This is the shared detection logic used by both `abc delta` and
    `abc contribute` so both commands always compare/read from the same
    live agent locations.
    """
    from .agents import _detect_agents

    skills_paths: dict[str, Path] = {}
    for agent in _detect_agents(project_root):
        if agent == "opencode":
            skills_paths["opencode"] = project_root / ".opencode" / "skills"
        elif agent == "claudecode":
            skills_paths["claudecode"] = project_root / ".claude" / "skills"
    return skills_paths


def _find_global_untracked_skills(
    ignore_patterns: list[str] | None = None,
) -> dict[str, list[str]]:
    """Return non-bundled skill directories found in the global skill dirs.

    Scans ~/.claude/skills/ (Claude Code) and ~/.config/opencode/skills/ (OpenCode).
    Excludes abc-bundled skills and any skill names matching ignore_patterns (fnmatch).
    Returns a mapping of tool name → sorted list of skill names.
    """
    global_skill_dirs = _bundled_global_skill_dirs()
    bundled = _bundled_skill_names()
    patterns = ignore_patterns or []
    result: dict[str, list[str]] = {}
    for tool, skills_dir in global_skill_dirs.items():
        if skills_dir.is_dir():
            names = sorted(
                d.name
                for d in skills_dir.iterdir()
                if d.is_dir()
                and (d / "SKILL.md").exists()
                and d.name not in bundled
                and not any(fnmatch.fnmatch(d.name, p) for p in patterns)
            )
            if names:
                result[tool] = names
    return result


def _install_bundled_skills_globally() -> tuple[list[str], list[str]]:
    """Install abc-bundled skills into global agent skill directories.

    Writes directly to ~/.config/opencode/skills/ and ~/.claude/skills/,
    bypassing the warehouse and any per-project agent detection.  Skills
    are available in every project as soon as they are installed.

    # Bundled skills are abc-package-managed — not user content; exempt from soft block

    Returns (installed, errors) where each entry is '<skill> (<agent>)'.
    """
    bundled_skills_dir = Path(__file__).parent.parent / "data" / "skills"
    if not bundled_skills_dir.exists():
        return [], []

    global_dirs = _bundled_global_skill_dirs()
    installed: list[str] = []
    errors: list[str] = []

    for skill_dir in sorted(bundled_skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        content = skill_md.read_text(encoding="utf-8")
        name = skill_dir.name

        for agent, skills_root in global_dirs.items():
            try:
                dest = skills_root / name / "SKILL.md"
                if dest.exists() and dest.read_text(encoding="utf-8") == content:
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content, encoding="utf-8")
                installed.append(f"{name} ({agent})")
            except Exception as e:
                errors.append(f"{name} ({agent}): {e}")

    return installed, errors


def _print_bundled_install_result(installed: list[str], errors: list[str]) -> None:
    """Print the result of a bundled skill install to the console."""
    if installed:
        names = ", ".join(s.split(" (")[0] for s in dict.fromkeys(installed))
        console.print(
            f"[green]✓[/green] Installed bundled skill(s) ({names}) "
            "[dim]— managed by abc, no beacon.yaml entry needed[/dim]"
        )
    for err in errors:
        console.print(f"  [yellow]⚠[/yellow] Bundled skill wiring: {err}")


def _show_bundled_skills_status() -> None:
    """Print bundled skill installation status for the status command.

    Checks global agent skill dirs — bundled skills are user-level,
    not per-project.
    """
    bundled_skills_dir = Path(__file__).parent.parent / "data" / "skills"
    if not bundled_skills_dir.exists():
        return

    skill_names = sorted(
        d.name
        for d in bundled_skills_dir.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    )
    if not skill_names:
        return

    global_dirs = _bundled_global_skill_dirs()

    table = Table(title="Bundled Skills (abc-managed, global)")
    table.add_column("Skill", style="yellow")
    for name in skill_names:
        installed_in_all = all(
            (skills_root / name / "SKILL.md").exists()
            for skills_root in global_dirs.values()
        )
        status_str = "[green]✓[/green]" if installed_in_all else "[red]✗[/red]"
        table.add_row(f"{status_str} {name}")
    console.print(table)
    console.print()


def _validate_skill_entries(beacon_settings: BeaconManifest) -> None:
    """Error if any skill entry in beacon.yaml uses a file path instead of a directory.

    Skills must be declared at the directory level (e.g. 'skills/my-skill/').
    File-level entries (e.g. 'skills/my-skill/SKILL.md') are not supported.
    """
    file_entries = [
        entry
        for entry in beacon_settings.artifacts.skills
        if Path(entry.rstrip("/")).suffix
    ]
    if not file_entries:
        return

    entry_list = "\n".join(f"  - {e}" for e in file_entries)
    console.print(
        f"\n[red]Error:[/red] beacon.yaml contains file-level skill entries:\n"
        f"{entry_list}\n\n"
        "Skills must be declared as directories (e.g. [bold]skills/my-skill/[/bold]).\n"
        "Update beacon.yaml and re-run 'abc sync'."
    )
    sys.exit(1)


def _migrate_beacon_yaml_skill_entries(
    beacon_yaml: Path, legacy_entries: list[str]
) -> None:
    """Rewrite beacon.yaml replacing file-level skill entries with directory form."""
    from ..core.manifest import BeaconManifest

    settings = BeaconManifest.from_yaml(beacon_yaml)
    migrated = []
    for entry in settings.artifacts.skills:
        if entry in legacy_entries:
            migrated.append(_normalize_skill_entry(entry))
        else:
            migrated.append(entry)
    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped = []
    for e in migrated:
        if e not in seen:
            seen.add(e)
            deduped.append(e)
    settings.artifacts.skills = deduped
    settings.to_yaml(beacon_yaml)


def _normalize_skill_entry(entry: str) -> str:
    """Normalize any skill beacon.yaml entry to canonical 'skills/<name>' form.

    Accepts old file-level entries ('skills/my-skill/SKILL.md'),
    new directory entries ('skills/my-skill/' or 'skills/my-skill'),
    and bare names ('my-skill').  Always returns 'skills/<name>' with no
    trailing slash.
    """
    p = Path(entry.rstrip("/"))
    # Strip file extension — old-style file-level entries
    if p.suffix:
        p = p.parent
    # Ensure the 'skills/' prefix is present
    if not p.parts or p.parts[0] != "skills":
        p = Path("skills") / p
    return str(p)


def _skill_name_from_entry(entry: str) -> str:
    """Extract the skill directory name from any beacon.yaml skill entry."""
    return Path(_normalize_skill_entry(entry)).name


def _extract_skill_description(content: str) -> str:
    """Extract description value from SKILL.md YAML frontmatter."""
    if not content.startswith("---"):
        return ""
    try:
        end = content.index("---", 3)
        for line in content[3:end].splitlines():
            if line.startswith("description:"):
                return line.split(":", 1)[1].strip()
    except ValueError:
        pass
    return ""


def _wire_single_skill(
    project_root: Path,
    skill_name: str,
    skill_src_dir: Path,
    agent: str,
) -> bool:
    """Copy all files from skill_src_dir into the agent's live skill directory.

    Handles both Claude Code (.claude/skills/<name>/) and OpenCode
    (.opencode/skills/<name>/), regenerating the OpenCode command stub from
    SKILL.md frontmatter when present.

    Returns True if any file was written or updated.
    """
    if agent == "opencode":
        dest_root = project_root / ".opencode" / "skills" / skill_name
    else:
        dest_root = project_root / ".claude" / "skills" / skill_name

    dest_root.mkdir(parents=True, exist_ok=True)

    any_written = False
    for src_file in sorted(skill_src_dir.rglob("*")):
        if not src_file.is_file():
            continue
        rel = src_file.relative_to(skill_src_dir)
        dest_file = dest_root / rel
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        content = src_file.read_text(encoding="utf-8")
        if not dest_file.exists() or dest_file.read_text(encoding="utf-8") != content:
            dest_file.write_text(content, encoding="utf-8")
            any_written = True

    # OpenCode: regenerate command stub from SKILL.md frontmatter
    if agent == "opencode":
        skill_md = skill_src_dir / "SKILL.md"
        if skill_md.exists():
            description = _extract_skill_description(
                skill_md.read_text(encoding="utf-8")
            )
            stub = (
                f"---\ndescription: {description}\n---\n\n"
                f"Use the **skill** tool to load and execute the `{skill_name}` skill "
                f"with any provided arguments.\n"
            )
            command_dir = project_root / ".opencode" / "command"
            command_dir.mkdir(parents=True, exist_ok=True)
            stub_file = command_dir / f"{skill_name}.md"
            if not stub_file.exists() or stub_file.read_text(encoding="utf-8") != stub:
                stub_file.write_text(stub, encoding="utf-8")

    return any_written


def _wire_skills_post_sync(
    project_root: Path,
    artifacts_dir: Path,
    force: bool = False,
    preserve: bool = False,
) -> tuple[list[str], list[str]]:
    """Install all synced skills for detected agents.

    Respects soft-block flags: --force overwrites without prompt, --preserve skips
    conflicting live skill files.

    Returns (installed, errors) where each entry is '<skill> (<agent>)'.
    Uses fallback_to_all so skills are always wired regardless of whether agent
    config files exist yet.
    """
    from .agents import _detect_agents
    from .display import _handle_soft_block

    agents = _detect_agents(project_root, fallback_to_all=True)

    skills_dir = artifacts_dir / "skills"
    if not skills_dir.exists():
        return [], []

    skill_dirs = sorted(d for d in skills_dir.iterdir() if d.is_dir())
    if not skill_dirs:
        return [], []

    # Compute wiring conflicts: any live skill file that differs from what we'd write
    wiring_conflicts: list[tuple[str, str, str]] = []  # (agent, skill_name, dest_path)
    for skill_dir in skill_dirs:
        name = skill_dir.name
        for src_file in sorted(skill_dir.rglob("*")):
            if not src_file.is_file():
                continue
            rel_within_skill = src_file.relative_to(skill_dir)
            content = src_file.read_text(encoding="utf-8")
            for agent in agents:
                if agent == "opencode":
                    dest = (
                        project_root / ".opencode" / "skills" / name / rel_within_skill
                    )
                else:
                    dest = project_root / ".claude" / "skills" / name / rel_within_skill
                if dest.exists() and dest.read_text(encoding="utf-8") != content:
                    wiring_conflicts.append((agent, name, str(dest)))

    if wiring_conflicts:
        conflict_paths = [str(dest) for _, _, dest in wiring_conflicts]
        overwrite = _handle_soft_block(conflict_paths, force=force, preserve=preserve)
        if not overwrite:
            preserve = True  # skip conflicting live skill files

    installed: list[str] = []
    errors: list[str] = []
    conflicting_agents_skills = {(a, n) for a, n, _ in wiring_conflicts}

    for skill_dir in skill_dirs:
        name = skill_dir.name
        for agent in agents:
            if preserve and (agent, name) in conflicting_agents_skills:
                continue  # Skip this wiring target
            try:
                changed = _wire_single_skill(project_root, name, skill_dir, agent)
                if changed:
                    installed.append(f"{name} ({agent})")
            except Exception as e:
                errors.append(f"{name} ({agent}): {e}")

    return installed, errors


def _update_beacon_yaml(beacon_dir: Path, files: list[str]) -> None:
    """Add installed file paths to beacon.yaml, creating it if absent."""
    beacon_yaml = beacon_dir / "beacon.yaml"

    if beacon_yaml.exists():
        try:
            settings = BeaconManifest.from_yaml(beacon_yaml)
        except Exception:
            return  # Don't corrupt a file we can't parse
    else:
        settings = BeaconManifest(artifacts=ArtifactsConfig())

    for path in files:
        parts = Path(path).parts
        artifact_type = parts[0] if parts else ""
        if artifact_type == "skills":
            # Normalize to directory form and deduplicate across old/new formats
            dir_entry = _normalize_skill_entry(path)
            already_tracked = any(
                _normalize_skill_entry(e) == dir_entry
                for e in settings.artifacts.skills
            )
            if not already_tracked:
                settings.artifacts.skills.append(dir_entry)
        elif artifact_type == "contexts":
            if path not in settings.artifacts.contexts:
                settings.artifacts.contexts.append(path)
        elif artifact_type == "knowledge":
            if path not in settings.artifacts.knowledge:
                settings.artifacts.knowledge.append(path)

    settings.to_yaml(beacon_yaml)


def _install_skill_opencode(
    project_root: Path, skill_name: str, content: str, description: str
) -> bool:
    """Install a skill for OpenCode: skill file + thin command stub.

    Returns True if files were written, False if already up-to-date.
    """
    skill_dest = project_root / ".opencode" / "skills" / skill_name
    skill_dest.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dest / "SKILL.md"

    stub = (
        f"---\ndescription: {description}\n---\n\n"
        f"Use the **skill** tool to load and execute the `{skill_name}` skill "
        f"with any provided arguments.\n"
    )
    command_dir = project_root / ".opencode" / "command"
    command_dir.mkdir(parents=True, exist_ok=True)
    stub_file = command_dir / f"{skill_name}.md"

    skill_unchanged = (
        skill_file.exists() and skill_file.read_text(encoding="utf-8") == content
    )
    stub_unchanged = (
        stub_file.exists() and stub_file.read_text(encoding="utf-8") == stub
    )

    if skill_unchanged and stub_unchanged:
        return False

    if not skill_unchanged:
        skill_file.write_text(content)
    if not stub_unchanged:
        stub_file.write_text(stub)

    # Return True only if SKILL.md was written (command stub updates are transparent)
    return not skill_unchanged


def _install_skill_claudecode(
    project_root: Path, skill_name: str, content: str
) -> bool:
    """Install a skill for Claude Code: copy SKILL.md to .claude/skills/<name>/.

    Returns True if the file was written, False if already up-to-date.
    """
    dest = project_root / ".claude" / "skills" / skill_name
    dest.mkdir(parents=True, exist_ok=True)
    dest_file = dest / "SKILL.md"

    if dest_file.exists() and dest_file.read_text(encoding="utf-8") == content:
        return False

    dest_file.write_text(content)
    return True


def _print_skill_next_steps(agents: list[str]) -> None:
    """Print agent-specific guidance after install."""
    console.print("\n[bold]Next Steps:[/bold]")
    if "opencode" in agents:
        console.print(
            "  [bold]OpenCode[/bold] — restart your session to pick up new commands"
        )
    if "claudecode" in agents:
        console.print(
            "  [bold]Claude Code[/bold] — skills are available as /skill-name in new sessions"
        )
