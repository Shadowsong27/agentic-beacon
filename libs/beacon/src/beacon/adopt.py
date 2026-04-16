"""Artifact adoption logic for the abc adopt command.

Provides:
- AdoptCandidate: data model for an adoptable warehouse artifact
- discover_adoptable(): git-diff or full-scan discovery
- AdoptApp: textual TUI for interactive selection
- apply_adoption(): update beacon.yaml with selected artifacts
- _count_unadopted_since(): lightweight count for sync notification
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core.settings import BeaconSettings

# ─────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────

_ADOPTABLE_TYPES = ("contexts", "skills", "knowledge")


@dataclass
class AdoptCandidate:
    """A warehouse artifact that can be adopted into beacon.yaml."""

    artifact_type: str  # "contexts" | "skills" | "knowledge"
    path: str  # warehouse-relative path (e.g. "contexts/foo.md", "skills/bar/")
    description: str = ""
    is_new: bool = True  # True = found via git-diff, False = found via --all scan


# ─────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────


def _classify_artifact_type(path: str) -> str | None:
    """Return artifact_type for a warehouse-relative path, or None if not adoptable."""
    for atype in _ADOPTABLE_TYPES:
        if path.startswith(atype + "/"):
            return atype
    return None


def _skill_dir_from_path(path: str) -> str:
    """Convert any file under a skill dir to the directory form with trailing slash.

    E.g. "skills/foo/SKILL.md" → "skills/foo/"
    """
    parts = path.split("/")
    if len(parts) >= 2:
        return f"skills/{parts[1]}/"
    return path


def _is_adopted(path: str, beacon_settings: BeaconSettings) -> bool:
    """Return True if path is already declared in beacon.yaml.

    Handles exact matches and glob patterns (e.g. ``knowledge/**/*.md``).
    Skill directory paths are matched with and without trailing slash.
    """
    normalized = path.rstrip("/")
    all_beacon = (
        beacon_settings.artifacts.contexts
        + beacon_settings.artifacts.knowledge
        + beacon_settings.artifacts.skills
    )
    for bp in all_beacon:
        bp_norm = bp.rstrip("/")
        if bp_norm == normalized:
            return True
        if fnmatch.fnmatch(normalized, bp_norm):
            return True
    return False


def _extract_skill_description(content: str) -> str:
    """Extract description from SKILL.md YAML frontmatter or markdown bold syntax."""
    if content.startswith("---"):
        try:
            end = content.index("---", 3)
            for line in content[3:end].splitlines():
                if line.startswith("description:"):
                    return line.split(":", 1)[1].strip()
        except ValueError:
            pass
    # Fallback: **description:** text
    match = re.search(r"\*\*description:\*\*\s*(.+)", content)
    if match:
        return match.group(1).strip()
    return ""


def _extract_heading_description(content: str) -> str:
    """Extract the first # Heading from markdown content."""
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return ""


def _extract_description(warehouse_path: Path, candidate_path: str) -> str:
    """Extract a human-readable description from a warehouse artifact."""
    artifact_type = _classify_artifact_type(candidate_path)
    if artifact_type == "skills":
        parts = candidate_path.split("/")
        if len(parts) >= 2:
            skill_md = warehouse_path / "skills" / parts[1] / "SKILL.md"
            if skill_md.exists():
                return _extract_skill_description(skill_md.read_text(encoding="utf-8"))
    else:
        file_path = warehouse_path / candidate_path
        if file_path.exists():
            return _extract_heading_description(file_path.read_text(encoding="utf-8"))
    return ""


def _run_git_diff(warehouse_path: Path, old_sha: str, diff_filter: str) -> list[str]:
    """Run git diff --name-only with the given filter and return file paths."""
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(warehouse_path),
                "diff",
                "--name-only",
                f"--diff-filter={diff_filter}",
                f"{old_sha}..HEAD",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    return [p for p in result.stdout.strip().splitlines() if p]


def _build_candidates(
    warehouse_path: Path,
    paths: list[str],
    beacon_settings: BeaconSettings,
    *,
    is_new: bool,
) -> list[AdoptCandidate]:
    """Build AdoptCandidate list from a list of warehouse-relative file paths.

    Skills are grouped by directory so multiple files in one skill produce a
    single candidate.
    """
    seen_skill_dirs: set[str] = set()
    candidates: list[AdoptCandidate] = []

    for path in paths:
        artifact_type = _classify_artifact_type(path)
        if artifact_type is None:
            continue

        if artifact_type == "skills":
            skill_dir = _skill_dir_from_path(path)
            skill_key = skill_dir.rstrip("/")
            if skill_key in seen_skill_dirs:
                continue
            if _is_adopted(skill_dir, beacon_settings):
                continue
            seen_skill_dirs.add(skill_key)
            skill_md = (
                warehouse_path / "skills" / skill_key.split("/", 1)[-1] / "SKILL.md"
            )
            desc = (
                _extract_skill_description(skill_md.read_text(encoding="utf-8"))
                if skill_md.exists()
                else ""
            )
            candidates.append(
                AdoptCandidate(
                    artifact_type="skills",
                    path=skill_dir,
                    description=desc,
                    is_new=is_new,
                )
            )
        else:
            if _is_adopted(path, beacon_settings):
                continue
            desc = _extract_description(warehouse_path, path)
            candidates.append(
                AdoptCandidate(
                    artifact_type=artifact_type,
                    path=path,
                    description=desc,
                    is_new=is_new,
                )
            )

    return candidates


def _discover_all(
    warehouse_path: Path,
    beacon_settings: BeaconSettings,
) -> list[AdoptCandidate]:
    """Full-scan mode: return every warehouse artifact not in beacon.yaml."""
    from .distributor import WarehouseDistributor

    distributor = WarehouseDistributor(
        warehouse_root=warehouse_path,
        target_root=warehouse_path,  # target_root unused here
    )
    available = distributor.list_available()

    candidates: list[AdoptCandidate] = []

    # Contexts — list_available returns paths like "contexts/foo.md"
    for ctx_path in available.get("contexts", []):
        if not _is_adopted(ctx_path, beacon_settings):
            desc = _extract_description(warehouse_path, ctx_path)
            candidates.append(
                AdoptCandidate(
                    artifact_type="contexts",
                    path=ctx_path,
                    description=desc,
                    is_new=False,
                )
            )

    # Knowledge — list_available returns scope names like "python" or "languages/python"
    for scope in available.get("knowledge", []):
        knowledge_path = f"knowledge/{scope}"
        if not _is_adopted(knowledge_path, beacon_settings):
            desc = ""
            scope_dir = warehouse_path / "knowledge" / scope
            if scope_dir.is_dir():
                for f in sorted(scope_dir.rglob("*.md")):
                    candidate_desc = _extract_heading_description(
                        f.read_text(encoding="utf-8")
                    )
                    if candidate_desc:
                        desc = candidate_desc
                        break
            candidates.append(
                AdoptCandidate(
                    artifact_type="knowledge",
                    path=knowledge_path,
                    description=desc,
                    is_new=False,
                )
            )

    # Skills — list_available returns skill names like "example-skill"
    for skill_name in available.get("skills", []):
        skill_path = f"skills/{skill_name}/"
        if not _is_adopted(skill_path, beacon_settings):
            skill_md = warehouse_path / "skills" / skill_name / "SKILL.md"
            desc = (
                _extract_skill_description(skill_md.read_text(encoding="utf-8"))
                if skill_md.exists()
                else ""
            )
            candidates.append(
                AdoptCandidate(
                    artifact_type="skills",
                    path=skill_path,
                    description=desc,
                    is_new=False,
                )
            )

    return candidates


# ─────────────────────────────────────────────────────────────
# Public API: discovery
# ─────────────────────────────────────────────────────────────


def discover_adoptable(
    warehouse_path: Path,
    beacon_settings: BeaconSettings,
    sync_sha: str | None,
    *,
    show_all: bool = False,
) -> tuple[list[AdoptCandidate], list[str]]:
    """Discover warehouse artifacts available to adopt.

    Args:
        warehouse_path: Path to the warehouse root.
        beacon_settings: Parsed beacon.yaml settings.
        sync_sha: SHA from .sync-state (None if no prior sync).
        show_all: If True, scan the entire warehouse regardless of git history.

    Returns:
        (candidates, updated_adopted_paths) where:
        - candidates: unadopted AdoptCandidates
        - updated_adopted_paths: paths already in beacon.yaml but modified since sync
    """
    if show_all:
        return _discover_all(warehouse_path, beacon_settings), []

    if sync_sha is None:
        raise ValueError(
            "No sync baseline found. Run `abc sync` first to establish a warehouse "
            "cursor, then re-run `abc adopt`."
        )

    new_paths = _run_git_diff(warehouse_path, sync_sha, "A")
    modified_paths = _run_git_diff(warehouse_path, sync_sha, "M")

    candidates = _build_candidates(
        warehouse_path, new_paths, beacon_settings, is_new=True
    )

    # Updated adopted: adopted artifacts that were modified since last sync
    seen_skill_dirs: set[str] = set()
    updated_adopted: list[str] = []
    for path in modified_paths:
        artifact_type = _classify_artifact_type(path)
        if artifact_type is None:
            continue
        if artifact_type == "skills":
            skill_dir = _skill_dir_from_path(path)
            skill_key = skill_dir.rstrip("/")
            if skill_key in seen_skill_dirs:
                continue
            if _is_adopted(skill_dir, beacon_settings):
                seen_skill_dirs.add(skill_key)
                updated_adopted.append(skill_dir)
        else:
            if _is_adopted(path, beacon_settings):
                updated_adopted.append(path)

    return candidates, updated_adopted


def _count_unadopted_since(
    warehouse_path: Path,
    beacon_settings: BeaconSettings,
    sync_sha: str,
) -> int:
    """Lightweight count of new warehouse artifacts since sync_sha not in beacon.yaml.

    Uses only git diff + path comparison — no file reads for descriptions.
    """
    new_paths = _run_git_diff(warehouse_path, sync_sha, "A")
    seen_skill_dirs: set[str] = set()
    count = 0

    for path in new_paths:
        artifact_type = _classify_artifact_type(path)
        if artifact_type is None:
            continue
        if artifact_type == "skills":
            skill_dir = _skill_dir_from_path(path)
            skill_key = skill_dir.rstrip("/")
            if skill_key in seen_skill_dirs:
                continue
            if not _is_adopted(skill_dir, beacon_settings):
                seen_skill_dirs.add(skill_key)
                count += 1
        else:
            if not _is_adopted(path, beacon_settings):
                count += 1

    return count


# ─────────────────────────────────────────────────────────────
# Public API: beacon.yaml update
# ─────────────────────────────────────────────────────────────


def apply_adoption(beacon_yaml_path: Path, selections: list[AdoptCandidate]) -> None:
    """Append selected artifacts to beacon.yaml.

    Skills are normalised to directory form with trailing slash.
    Duplicates are silently skipped.
    """
    if not selections:
        return

    from .core.settings import BeaconSettings

    beacon_settings = BeaconSettings.from_yaml(beacon_yaml_path)

    for candidate in selections:
        if candidate.artifact_type == "contexts":
            if candidate.path not in beacon_settings.artifacts.contexts:
                beacon_settings.artifacts.contexts.append(candidate.path)
        elif candidate.artifact_type == "skills":
            # Normalise to directory form with trailing slash
            skill_path = candidate.path
            if not skill_path.endswith("/"):
                skill_path = skill_path + "/"
            if skill_path not in beacon_settings.artifacts.skills:
                beacon_settings.artifacts.skills.append(skill_path)
        elif candidate.artifact_type == "knowledge":
            if candidate.path not in beacon_settings.artifacts.knowledge:
                beacon_settings.artifacts.knowledge.append(candidate.path)

    beacon_settings.to_yaml(beacon_yaml_path)


# ─────────────────────────────────────────────────────────────
# Textual TUI
# ─────────────────────────────────────────────────────────────


def _make_cb_id(path: str) -> str:
    """Generate a valid Textual widget ID from a warehouse path."""
    return "cb_" + re.sub(r"[^a-zA-Z0-9_-]", "_", path.rstrip("/"))


class AdoptApp:
    """Textual TUI for interactive artifact selection.

    Lazy-imports textual so the module can be imported in environments where
    textual is not installed (tests that mock it out, etc.).

    Usage::

        app = AdoptApp(candidates, updated_adopted)
        selected_paths = app.run()  # blocks; returns list[str] or []
    """

    def __init__(
        self,
        candidates: list[AdoptCandidate],
        updated_adopted: list[str],
    ) -> None:
        self.candidates = candidates
        self.updated_adopted = updated_adopted

    def run(self) -> list[str]:
        """Launch TUI and return selected artifact paths (empty list on cancel)."""
        from textual.app import App, ComposeResult
        from textual.binding import Binding
        from textual.containers import VerticalScroll
        from textual.widgets import Checkbox, Footer, Header, Static

        candidates = self.candidates
        updated_adopted = self.updated_adopted

        class _InnerApp(App[list[str]]):
            BINDINGS = [  # type: ignore[assignment]
                Binding("enter", "confirm", "Confirm"),
                Binding("escape", "cancel", "Cancel"),
                Binding("q", "cancel", "Quit"),
                Binding("a", "select_all", "Select All"),
                Binding("n", "select_none", "Select None"),
            ]

            def __init__(self_inner) -> None:  # noqa: N805
                super().__init__()
                # Map checkbox widget id → candidate path
                self_inner._path_by_id: dict[str, str] = {}
                self_inner._candidates = candidates
                self_inner._updated_adopted = updated_adopted

            def compose(self_inner) -> ComposeResult:  # noqa: N805
                yield Header(show_clock=False)
                with VerticalScroll():
                    # Group candidates by artifact_type
                    by_type: dict[str, list[AdoptCandidate]] = {}
                    for c in self_inner._candidates:
                        by_type.setdefault(c.artifact_type, []).append(c)

                    for atype in ["contexts", "skills", "knowledge"]:
                        type_candidates = by_type.get(atype, [])
                        if not type_candidates:
                            continue
                        yield Static(f"[bold]{atype.capitalize()}[/bold]")
                        for c in type_candidates:
                            cb_id = _make_cb_id(c.path)
                            self_inner._path_by_id[cb_id] = c.path
                            label = c.path
                            if c.description:
                                label = f"{c.path} — {c.description}"
                            yield Checkbox(label, id=cb_id, value=False)

                    if self_inner._updated_adopted:
                        yield Static(
                            "\n[dim]Already adopted (updated) — run `abc sync` to refresh:[/dim]"
                        )
                        for upd_path in self_inner._updated_adopted:
                            yield Static(f"  [dim]{upd_path}[/dim]")

                yield Footer()

            def action_confirm(self_inner) -> None:  # noqa: N805
                selected = []
                for cb in self_inner.query(Checkbox):
                    if cb.value and cb.id and cb.id in self_inner._path_by_id:
                        selected.append(self_inner._path_by_id[cb.id])
                self_inner.exit(selected)

            def action_cancel(self_inner) -> None:  # noqa: N805
                self_inner.exit([])

            def action_select_all(self_inner) -> None:  # noqa: N805
                for cb in self_inner.query(Checkbox):
                    cb.value = True

            def action_select_none(self_inner) -> None:  # noqa: N805
                for cb in self_inner.query(Checkbox):
                    cb.value = False

        result = _InnerApp().run()
        return result if result is not None else []
