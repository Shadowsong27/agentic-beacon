"""Artifact adoption apply logic for the abc adopt command.

Provides:
- apply_adoption(): update beacon.yaml with selected/removed artifacts
- cleanup_unadopted_artifacts(): prompt to remove local artifact symlinks for unadopted entries
- warehouse_uncommitted_paths(): return set of relative paths with uncommitted changes
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from beacon.domains.adoption.models import AdoptCandidate

# ─────────────────────────────────────────────────────────────
# Public API: beacon.yaml update
# ─────────────────────────────────────────────────────────────


def apply_adoption(
    beacon_yaml_path: Path,
    selections: list[AdoptCandidate],
    unadoptions: list[str] | None = None,
) -> None:
    """Update beacon.yaml — append selected artifacts and remove unadopted ones.

    Skills are normalised to directory form with trailing slash.
    Duplicate additions are silently skipped.
    """
    if not selections and not unadoptions:
        return

    from beacon.core.manifest.beacon import BeaconManifest

    beacon_settings = BeaconManifest.from_yaml(beacon_yaml_path)

    for candidate in selections:
        if candidate.artifact_type == "agents":
            continue  # agents are managed globally, not via beacon.yaml
        if candidate.artifact_type == "contexts":
            if candidate.path not in beacon_settings.artifacts.contexts:
                beacon_settings.artifacts.contexts.append(candidate.path)
        elif candidate.artifact_type == "skills":
            skill_path = candidate.path
            if not skill_path.endswith("/"):
                skill_path = skill_path + "/"
            if skill_path not in beacon_settings.artifacts.skills:
                beacon_settings.artifacts.skills.append(skill_path)

    for path in unadoptions or []:
        norm = path.rstrip("/")
        beacon_settings.artifacts.contexts = [
            p for p in beacon_settings.artifacts.contexts if p.rstrip("/") != norm
        ]
        beacon_settings.artifacts.skills = [
            p for p in beacon_settings.artifacts.skills if p.rstrip("/") != norm
        ]

    beacon_settings.to_yaml(beacon_yaml_path)


def warehouse_uncommitted_paths(warehouse_path: Path) -> set[str]:
    """Return relative paths of files with uncommitted changes in the warehouse."""
    result = subprocess.run(
        ["git", "-C", str(warehouse_path), "status", "--porcelain"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    paths: set[str] = set()
    for line in result.stdout.splitlines():
        if len(line) >= 3:
            paths.add(line[3:].strip())
    return paths


def cleanup_unadopted_artifacts(
    unadoptions: list[str],
    artifacts_dir: Path,
    warehouse_path: Path,
    *,
    project_root: Path | None = None,
) -> None:
    """Prompt to remove local artifact symlinks for unadopted entries.

    Always requires confirmation.

    When project_root is provided, skill unadoptions also remove live agent
    copies under .opencode/skills/<name>/ and .claude/skills/<name>/.
    """
    import click
    from rich.console import Console

    console = Console()

    to_remove: list[tuple[str, Path]] = []

    for entry in unadoptions:
        entry_clean = entry.rstrip("/")
        local_entry = artifacts_dir / entry_clean

        if local_entry.is_dir():
            for f in local_entry.rglob("*"):
                if not f.is_file():
                    continue
                rel = str(f.relative_to(artifacts_dir))
                to_remove.append((rel, f))
        elif local_entry.is_file():
            rel = str(local_entry.relative_to(artifacts_dir))
            to_remove.append((rel, local_entry))

        parts = entry_clean.split("/")
        if project_root is not None and len(parts) >= 2 and parts[0] == "skills":
            from beacon.domains.artifact.skill import build_skills_paths

            skill_name = parts[1]
            for agent, live_skills_root in build_skills_paths(project_root).items():
                live_skill_dir = live_skills_root / skill_name
                if not live_skill_dir.is_dir():
                    continue
                for f in live_skill_dir.rglob("*"):
                    if not f.is_file():
                        continue
                    rel_within_skill = f.relative_to(live_skill_dir)
                    display_label = str(
                        Path(".opencode" if agent == "opencode" else ".claude")
                        / "skills"
                        / skill_name
                        / rel_within_skill
                    )
                    to_remove.append((display_label, f))

    if not to_remove:
        return

    symlink_count = sum(1 for _, path in to_remove if path.is_symlink())
    file_count = len(to_remove) - symlink_count

    if symlink_count > 0 and file_count == 0:
        noun = "symlink"
        action = "unlink"
    elif symlink_count > 0 and file_count > 0:
        noun = "reference"
        action = "remove"
    else:
        noun = "file"
        action = "delete"

    console.print()
    console.print(f"[bold]Local artifact {noun}s to {action}:[/bold]")
    for rel, _ in sorted(to_remove):
        console.print(f"  {rel}")

    confirmed = click.confirm(
        f"\n{action.capitalize()} {len(to_remove)} local {noun}(s)?", default=False
    )
    if not confirmed:
        console.print("[dim]Skipped cleanup.[/dim]")
        return

    removed = 0
    for _, path in to_remove:
        try:
            path.unlink()
            removed += 1
        except OSError:
            pass

    live_skill_roots: list[Path] = []
    if project_root is not None:
        from beacon.domains.artifact.skill import build_skills_paths

        for live_skills_root in build_skills_paths(project_root).values():
            for entry in unadoptions:
                entry_clean = entry.rstrip("/")
                parts = entry_clean.split("/")
                if len(parts) >= 2 and parts[0] == "skills":
                    live_skill_roots.append(live_skills_root / parts[1])

    for _, path in to_remove:
        for parent in path.parents:
            if parent == artifacts_dir:
                break
            if any(parent == r for r in live_skill_roots):
                break
            try:
                parent.rmdir()
            except OSError:
                break

    for live_skill_dir in live_skill_roots:
        try:
            live_skill_dir.rmdir()
        except OSError:
            pass

    console.print(f"[green]✓[/green] {action.capitalize()}ed {removed} {noun}(s).")
