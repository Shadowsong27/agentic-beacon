"""Artifact adoption apply logic for the abc adopt command.

Provides:
- apply_adoption(): update beacon.yaml with selected/removed artifacts
- cleanup_unadopted_artifacts(): prompt to delete local artifact files for unadopted entries
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

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
        elif candidate.artifact_type == "knowledge":
            if candidate.path not in beacon_settings.artifacts.knowledge:
                beacon_settings.artifacts.knowledge.append(candidate.path)

    for path in unadoptions or []:
        norm = path.rstrip("/")
        beacon_settings.artifacts.contexts = [
            p for p in beacon_settings.artifacts.contexts if p.rstrip("/") != norm
        ]
        beacon_settings.artifacts.skills = [
            p for p in beacon_settings.artifacts.skills if p.rstrip("/") != norm
        ]
        beacon_settings.artifacts.knowledge = [
            p for p in beacon_settings.artifacts.knowledge if p.rstrip("/") != norm
        ]

    beacon_settings.to_yaml(beacon_yaml_path)


def cleanup_unadopted_artifacts(
    unadoptions: list[str],
    artifacts_dir: Path,
    warehouse_path: Path,
    *,
    project_root: Path | None = None,
) -> None:
    """Prompt to delete local artifact files for unadopted entries.

    Always requires confirmation.  Files that differ from the warehouse copy
    are flagged as locally modified so the user can make an informed choice.

    When project_root is provided, skill unadoptions also remove live agent
    copies under .opencode/skills/<name>/ and .claude/skills/<name>/.
    """
    import hashlib

    import click
    from rich.console import Console
    from rich.table import Table

    console = Console()

    def _sha256(path: Path) -> str:
        h = hashlib.sha256()
        h.update(path.read_bytes())
        return h.hexdigest()

    to_delete: list[tuple[str, Path, bool]] = []

    for entry in unadoptions:
        entry_clean = entry.rstrip("/")
        local_entry = artifacts_dir / entry_clean

        if local_entry.is_dir():
            for f in local_entry.rglob("*"):
                if not f.is_file():
                    continue
                rel = str(f.relative_to(artifacts_dir))
                warehouse_file = warehouse_path / rel
                if warehouse_file.exists():
                    modified = _sha256(f) != _sha256(warehouse_file)
                else:
                    modified = True
                to_delete.append((rel, f, modified))
        elif local_entry.is_file():
            rel = str(local_entry.relative_to(artifacts_dir))
            warehouse_file = warehouse_path / rel
            if warehouse_file.exists():
                modified = _sha256(local_entry) != _sha256(warehouse_file)
            else:
                modified = True
            to_delete.append((rel, local_entry, modified))

        parts = entry_clean.split("/")
        if project_root is not None and len(parts) >= 2 and parts[0] == "skills":
            from beacon.domains.artifact.skill import build_skills_paths

            skill_name = parts[1]
            warehouse_skill_dir = warehouse_path / "skills" / skill_name
            for agent, live_skills_root in build_skills_paths(project_root).items():
                live_skill_dir = live_skills_root / skill_name
                if not live_skill_dir.is_dir():
                    continue
                for f in live_skill_dir.rglob("*"):
                    if not f.is_file():
                        continue
                    rel_within_skill = f.relative_to(live_skill_dir)
                    warehouse_file = warehouse_skill_dir / rel_within_skill
                    if warehouse_file.exists():
                        modified = _sha256(f) != _sha256(warehouse_file)
                    else:
                        modified = True
                    display_label = str(
                        Path(".opencode" if agent == "opencode" else ".claude")
                        / "skills"
                        / skill_name
                        / rel_within_skill
                    )
                    to_delete.append((display_label, f, modified))

    if not to_delete:
        return

    has_modified = any(m for _, _, m in to_delete)

    table = Table(show_header=True, header_style="dim", box=None, padding=(0, 2, 0, 0))
    table.add_column("File")
    table.add_column("Status")
    for rel, _, modified in sorted(to_delete):
        status = (
            "[yellow]⚠ locally modified[/yellow]" if modified else "[dim]clean[/dim]"
        )
        table.add_row(rel, status)

    console.print()
    console.print("[bold]Local artifact files to delete:[/bold]")
    console.print(table)
    if has_modified:
        console.print(
            "[yellow]⚠ Some files have local edits that are not in the warehouse.[/yellow]"
        )

    confirmed = click.confirm(f"Delete {len(to_delete)} local file(s)?", default=False)
    if not confirmed:
        console.print("[dim]Skipped cleanup. Files remain in artifacts/.[/dim]")
        return

    deleted = 0
    for _, path, _ in to_delete:
        try:
            path.unlink()
            deleted += 1
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

    for _, path, _ in to_delete:
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

    console.print(f"[green]✓[/green] Deleted {deleted} file(s).")
