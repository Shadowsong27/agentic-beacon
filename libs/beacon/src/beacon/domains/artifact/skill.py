"""Skill operations for the artifact domain."""

import fnmatch
import os
import shutil
import sys
from collections.abc import Callable
from pathlib import Path

from rich.console import Console
from rich.table import Table

from beacon.core.file_filter import SKILL_IGNORE_PATTERNS, is_skill_file
from beacon.core.manifest.beacon import ArtifactsConfig, BeaconManifest
from beacon.domains.artifact.agent import detect_agents
from beacon.utils.interaction import OverwriteDecision, resolve_conflict

_BUNDLED_DATA_DIR = Path(__file__).parent.parent.parent / "data"
BUNDLED_SKILLS_DIR = _BUNDLED_DATA_DIR / "skills"

console = Console()


def bundled_global_skill_dirs() -> dict[str, Path]:
    """Return global agent skill directories for bundled skill installation.

    These are the user-level skill dirs read by opencode and Claude Code
    regardless of which project is active.
    """
    return {
        "opencode": Path.home() / ".config" / "opencode" / "skills",
        "claudecode": Path.home() / ".claude" / "skills",
    }


def bundled_skill_names() -> set[str]:
    """Return the set of skill names that are managed by abc (bundled)."""
    bundled_dir = BUNDLED_SKILLS_DIR
    if not bundled_dir.exists():
        return set()
    return {
        d.name
        for d in bundled_dir.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    }


def build_skills_paths(project_root: Path) -> dict[str, Path]:
    """Return a mapping of agent name → live skills directory for detected agents.

    Shared detection logic used by `abc install` (and historically by
    per-project skill-drift tooling) so writes/reads hit the same live agent
    locations.
    """
    skills_paths: dict[str, Path] = {}
    for agent in detect_agents(project_root):
        if agent == "opencode":
            skills_paths["opencode"] = project_root / ".opencode" / "skills"
        elif agent == "claudecode":
            skills_paths["claudecode"] = project_root / ".claude" / "skills"
    return skills_paths


def find_global_untracked_skills(
    ignore_patterns: list[str] | None = None,
) -> dict[str, list[str]]:
    """Return non-bundled skill directories found in the global skill dirs.

    Scans ~/.claude/skills/ (Claude Code) and ~/.config/opencode/skills/ (OpenCode).
    Excludes abc-bundled skills and any skill names matching ignore_patterns (fnmatch).
    Returns a mapping of tool name → sorted list of skill names.
    """
    global_skill_dirs = bundled_global_skill_dirs()
    bundled = bundled_skill_names()
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


def install_bundled_skills_globally() -> tuple[list[str], list[str]]:
    """Install abc-bundled skills into global agent skill directories.

    Writes directly to ~/.config/opencode/skills/ and ~/.claude/skills/,
    bypassing the warehouse and any per-project agent detection.  Skills
    are available in every project as soon as they are installed.

    # Bundled skills are abc-package-managed — not user content; exempt from soft block

    Returns (installed, errors) where each entry is '<skill> (<agent>)'.
    """
    if not BUNDLED_SKILLS_DIR.exists():
        return [], []

    global_dirs = bundled_global_skill_dirs()
    installed: list[str] = []
    errors: list[str] = []

    for skill_dir in sorted(BUNDLED_SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        content = skill_md.read_text(encoding="utf-8")
        name = skill_dir.name

        for agent, skills_root in global_dirs.items():
            try:
                dest_dir = skills_root / name
                dest = dest_dir / "SKILL.md"
                if (
                    not dest_dir.is_symlink()
                    and dest.exists()
                    and dest.read_text(encoding="utf-8") == content
                ):
                    continue
                if dest_dir.is_symlink():
                    dest_dir.unlink()
                elif dest_dir.exists():
                    shutil.rmtree(dest_dir)
                dest_dir.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(
                    skill_dir,
                    dest_dir,
                    ignore=shutil.ignore_patterns(*SKILL_IGNORE_PATTERNS),
                )
                installed.append(f"{name} ({agent})")
            except Exception as e:
                errors.append(f"{name} ({agent}): {e}")

    return installed, errors


def wire_bundled_skills_per_project(
    project_root: Path,
    agents: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Wire abc-bundled skills into the project's agent directories.

    Creates per-project skill copies and OpenCode command stubs so bundled
    skills are available as slash commands (e.g. /record-knowledge).

    Returns (installed, errors) where each entry is '<skill> (<agent>)'.
    """
    if not BUNDLED_SKILLS_DIR.exists():
        return [], []

    if agents is None:
        agents = detect_agents(project_root, fallback_to_all=True)

    installed: list[str] = []
    errors: list[str] = []

    for skill_dir in sorted(BUNDLED_SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        if not (skill_dir / "SKILL.md").exists():
            continue
        name = skill_dir.name

        for agent in agents:
            try:
                changed = wire_single_skill(project_root, name, skill_dir, agent)
                if changed:
                    installed.append(f"{name} ({agent})")
            except Exception as e:
                errors.append(f"{name} ({agent}): {e}")

    return installed, errors


def print_bundled_install_result(installed: list[str], errors: list[str]) -> None:
    """Print the result of a bundled skill install to the console."""
    if installed:
        names = ", ".join(s.split(" (")[0] for s in dict.fromkeys(installed))
        console.print(
            f"[green]✓[/green] Installed bundled skill(s) ({names}) "
            "[dim]— managed by abc, no beacon.yaml entry needed[/dim]"
        )
    for err in errors:
        console.print(f"  [yellow]⚠[/yellow] Bundled skill wiring: {err}")


def show_bundled_skills_status() -> None:
    """Print bundled skill installation status for the status command.

    Checks global agent skill dirs — bundled skills are user-level,
    not per-project.
    """
    if not BUNDLED_SKILLS_DIR.exists():
        return

    skill_names = sorted(
        d.name
        for d in BUNDLED_SKILLS_DIR.iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    )
    if not skill_names:
        return

    global_dirs = bundled_global_skill_dirs()

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


def validate_skill_entries(beacon_settings: BeaconManifest) -> None:
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
    from beacon.core.manifest.beacon import BeaconManifest

    settings = BeaconManifest.from_yaml(beacon_yaml)
    migrated = []
    for entry in settings.artifacts.skills:
        if entry in legacy_entries:
            migrated.append(normalize_skill_entry(entry))
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


def normalize_skill_entry(entry: str) -> str:
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


def skill_name_from_entry(entry: str) -> str:
    """Extract the skill directory name from any beacon.yaml skill entry."""
    return Path(normalize_skill_entry(entry)).name


def _extract_skill_description(content: str, skill_name: str = "") -> str:
    """Extract description value from SKILL.md YAML frontmatter.

    Falls back to a generic description using the skill name when frontmatter
    is missing or the description field is empty.
    """
    if not content.startswith("---"):
        return f"Use the {skill_name} skill" if skill_name else ""
    try:
        end = content.index("---", 3)
        for line in content[3:end].splitlines():
            if line.startswith("description:"):
                desc = line.split(":", 1)[1].strip()
                return (
                    desc
                    if desc
                    else f"Use the {skill_name} skill"
                    if skill_name
                    else ""
                )
    except ValueError:
        pass
    return f"Use the {skill_name} skill" if skill_name else ""


def _resolve_skill_source(src_file: Path) -> tuple[Path, bool]:
    """Resolve the true warehouse source for a skill file under artifacts/skills/.

    Returns (target_path, is_warehouse_symlink).

    - If src_file is a symlink, read its target (the warehouse file) and return
      (warehouse_path, True). artifacts/skills/ symlinks use absolute targets,
      so the returned path is absolute and stable.
    - If src_file is a regular file (bundled skill inside the installed
      agentic-beacon package), return (src_file, False).
    """
    if src_file.is_symlink():
        target = os.readlink(src_file)
        return Path(target), True
    return src_file, False


def _write_skill_file(dest_file: Path, target: Path, use_symlink: bool) -> bool:
    """Install a single skill file at dest_file.

    Warehouse skills are installed as symlinks pointing at target (the warehouse
    source) so edits propagate without re-sync. Bundled skills are installed as
    regular-file copies because their source path (site-packages) is unstable
    across package upgrades.

    Returns True if dest_file was created or changed, False if already correct.
    Cleans obstacles (wrong type, stale symlink, differing content) before writing.
    """
    dest_file.parent.mkdir(parents=True, exist_ok=True)

    if use_symlink:
        target_str = str(target)
        if dest_file.is_symlink():
            if os.readlink(dest_file) == target_str:
                return False
            dest_file.unlink()
        elif dest_file.exists():
            # Regular file from a previous copy-based install — replace with symlink.
            dest_file.unlink()
        dest_file.symlink_to(target_str)
        return True

    # Bundled skill path: copy content (bytes — skills may ship binary helpers).
    # Replace any pre-existing symlink.
    content = target.read_bytes()
    if dest_file.is_symlink():
        dest_file.unlink()
    elif dest_file.exists():
        if dest_file.read_bytes() == content:
            return False
        # Fall through to overwrite.
    dest_file.write_bytes(content)
    return True


def wire_single_skill(
    project_root: Path,
    skill_name: str,
    skill_src_dir: Path,
    agent: str,
) -> bool:
    """Install a skill into the agent's live skill directory.

    For warehouse-backed skills (skill_src_dir inside .agentic-beacon/artifacts/
    containing symlinks to the warehouse clone), creates per-file symlinks
    pointing directly at the warehouse source. This means edits in the
    warehouse propagate to every project instantly without re-running abc sync.

    For abc-bundled skills (skill_src_dir inside the installed agentic-beacon
    package containing regular files), copies content instead of symlinking,
    because site-packages paths are unstable across package upgrades.

    Always regenerates the OpenCode command stub from SKILL.md frontmatter so
    each skill is available as a slash command. Runs unconditionally per call
    so the stub stays current with the source description.

    Returns True if any file was written, updated, or relinked.
    """
    if agent == "opencode":
        dest_root = project_root / ".opencode" / "skills" / skill_name
    else:
        dest_root = project_root / ".claude" / "skills" / skill_name

    # A symlink or non-directory at dest_root blocks mkdir(exist_ok=True) because
    # os.path.isdir() returns False for non-directories. Clear any obstacle so
    # dest_root is always a real directory.
    if dest_root.is_symlink() or (dest_root.exists() and not dest_root.is_dir()):
        dest_root.unlink()
    dest_root.mkdir(parents=True, exist_ok=True)

    any_written = False
    for src_file in sorted(skill_src_dir.rglob("*")):
        if not is_skill_file(src_file):
            continue
        rel = src_file.relative_to(skill_src_dir)
        dest_file = dest_root / rel
        target, use_symlink = _resolve_skill_source(src_file)
        if _write_skill_file(dest_file, target, use_symlink):
            any_written = True

    # OpenCode: regenerate command stub from SKILL.md frontmatter every call so
    # the stub description stays in sync with the source SKILL.md.
    if agent == "opencode":
        skill_md = skill_src_dir / "SKILL.md"
        if skill_md.exists():
            description = _extract_skill_description(
                skill_md.read_text(encoding="utf-8"), skill_name
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


def wire_skills_post_sync(
    project_root: Path,
    artifacts_dir: Path,
    force: bool = False,
    preserve: bool = False,
    skill_conflict_callback: Callable[[list[str]], bool] | None = None,
) -> tuple[list[str], list[str]]:
    """Install all synced skills for detected agents.

    Respects soft-block flags: --force overwrites without prompt, --preserve skips
    conflicting live skill files.

    When neither flag is supplied and conflicts exist:
    - If skill_conflict_callback is provided, it is called with the list of
      conflicting destination paths and must return True to overwrite or False
      to preserve. The CLI wires this to an interactive `click.confirm`.
    - Otherwise (non-interactive, no callback), emits a visible warning listing
      the files and proceeds with overwrite. This preserves the pre-symlink
      default of replacing out-of-date skill copies without blocking CI or
      scripted flows. Use --preserve to keep local edits.

    .opencode/skills/ and .claude/skills/ are abc-managed gitignored state,
    not user-editable content, so the default-overwrite policy is correct for
    the common "upgrade from copy-based install to symlink-based install" path.

    Returns (installed, errors) where each entry is '<skill> (<agent>)'.
    Uses fallback_to_all so skills are always wired regardless of whether agent
    config files exist yet.
    """
    agents = detect_agents(project_root, fallback_to_all=True)

    skills_dir = artifacts_dir / "skills"
    if not skills_dir.exists():
        return [], []

    skill_dirs = sorted(d for d in skills_dir.iterdir() if d.is_dir())
    if not skill_dirs:
        return [], []

    # Compute wiring conflicts: any live regular file (not a symlink) that
    # differs from the warehouse source. Existing symlinks are never conflicts:
    # a wrong-target symlink is just a repair, which wire_single_skill handles
    # idempotently. Regular files at the destination indicate the user (or a
    # pre-symlink version of abc) wrote content locally, and the user should
    # decide whether to overwrite.
    wiring_conflicts: list[tuple[str, str, str]] = []  # (agent, skill_name, dest_path)
    for skill_dir in skill_dirs:
        name = skill_dir.name
        for src_file in sorted(skill_dir.rglob("*")):
            if not is_skill_file(src_file):
                continue
            rel_within_skill = src_file.relative_to(skill_dir)
            for agent in agents:
                if agent == "opencode":
                    dest = (
                        project_root / ".opencode" / "skills" / name / rel_within_skill
                    )
                else:
                    dest = project_root / ".claude" / "skills" / name / rel_within_skill
                # Skip if dest doesn't exist, or is a symlink (symlinks are
                # repaired idempotently in wire_single_skill).
                if dest.is_symlink() or not dest.exists():
                    continue
                # Regular file at dest — conflict only if content differs from warehouse.
                # Binary files (no UTF-8 content) are treated as non-conflicts for the
                # prompt and left to wire_single_skill to resolve idempotently; this
                # avoids failing the whole wiring pass on a single binary script.
                try:
                    warehouse_content = src_file.read_text(encoding="utf-8")
                    local_content = dest.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                if local_content != warehouse_content:
                    wiring_conflicts.append((agent, name, str(dest)))

    if wiring_conflicts:
        resolution = resolve_conflict(
            force=force, preserve=preserve, has_conflicts=True
        )
        if resolution == OverwriteDecision.SKIP:
            preserve = True  # skip conflicting live skill files
        elif resolution == OverwriteDecision.NEEDS_CONFIRMATION:
            conflict_paths = sorted({path for _, _, path in wiring_conflicts})
            if skill_conflict_callback is not None:
                if skill_conflict_callback(conflict_paths) is False:
                    preserve = True
                # else: proceed with overwrite
            else:
                # Non-interactive, no callback — proceed with overwrite (matches
                # pre-symlink default) but print a visible migration notice so
                # the user isn't surprised. .opencode/skills/ and
                # .claude/skills/ are abc-managed gitignored state; overwriting
                # diverged copies with warehouse content is the expected
                # upgrade path.
                console.print(
                    f"\n[yellow]Migrating [bold]{len(conflict_paths)}[/bold] "
                    "legacy skill file(s) to warehouse symlinks:[/yellow]"
                )
                for path in conflict_paths:
                    console.print(f"    • {path}", overflow="ellipsis", no_wrap=True)
                console.print(
                    "[dim]These files diverged from the warehouse and have "
                    "been replaced. Use --force to silence this notice.[/dim]"
                )

    installed: list[str] = []
    errors: list[str] = []
    conflicting_agents_skills = {(a, n) for a, n, _ in wiring_conflicts}

    for skill_dir in skill_dirs:
        name = skill_dir.name
        for agent in agents:
            if preserve and (agent, name) in conflicting_agents_skills:
                continue  # Skip this wiring target
            try:
                changed = wire_single_skill(project_root, name, skill_dir, agent)
                if changed:
                    installed.append(f"{name} ({agent})")
            except Exception as e:
                errors.append(f"{name} ({agent}): {e}")

    return installed, errors


def update_beacon_yaml(beacon_dir: Path, files: list[str]) -> None:
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
            dir_entry = normalize_skill_entry(path)
            already_tracked = any(
                normalize_skill_entry(e) == dir_entry for e in settings.artifacts.skills
            )
            if not already_tracked:
                settings.artifacts.skills.append(dir_entry)
        elif artifact_type == "contexts":
            if path not in settings.artifacts.contexts:
                settings.artifacts.contexts.append(path)

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


def print_skill_next_steps(agents: list[str]) -> None:
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
