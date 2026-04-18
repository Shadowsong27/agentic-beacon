"""Artifact adoption logic for the abc adopt command.

Provides:
- AdoptCandidate: data model for an adoptable warehouse artifact
- AdoptResult: return value from AdoptApp.run()
- discover_adoptable(): full-scan discovery with recent-commit annotation
- AdoptApp: textual TUI for interactive selection and unadoption
- apply_adoption(): update beacon.yaml with selected/removed artifacts
- _count_unadopted_since(): lightweight count for sync notification
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from beacon.core.manifest.beacon import BeaconManifest

# ─────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────

_ADOPTABLE_TYPES = ("contexts", "skills", "knowledge", "agents")
_NEW_TAG_MAX_COMMITS = (
    5  # only show "[added N commits ago]" if within this many commits
)
_KNOWLEDGE_SUBTYPES = frozenset(("decisions", "lessons", "facts"))


@dataclass
class AdoptCandidate:
    """A warehouse artifact that can be adopted into beacon.yaml."""

    artifact_type: str  # "contexts" | "skills" | "knowledge"
    path: str  # warehouse-relative path (e.g. "contexts/foo.md", "skills/bar/")
    description: str = ""
    is_new: bool = True  # kept for backward compat; prefer commits_ago is not None
    commits_ago: int | None = None  # set when added within _NEW_TAG_MAX_COMMITS commits


@dataclass
class AdoptResult:
    """Result returned by AdoptApp.run()."""

    to_adopt: list[str] = field(default_factory=list)
    to_unadopt: list[str] = field(default_factory=list)


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


def _find_knowledge_node_for_file(file_path: str) -> str | None:
    """Find the knowledge node path for a file under knowledge/.

    A node is identified by the first path segment that is decisions/lessons/facts.
    E.g. "knowledge/global/decisions/foo.md" → "knowledge/global"
         "knowledge/languages/python/lessons/bar.md" → "knowledge/languages/python"
    Returns None if the file is not under a knowledge subtype directory.
    """
    parts = file_path.split("/")
    for i, part in enumerate(parts):
        if part in _KNOWLEDGE_SUBTYPES:
            return "/".join(parts[:i])
    return None


def _is_knowledge_node(dir_path: Path) -> bool:
    """Return True if dir_path directly contains decisions/, lessons/, or facts/."""
    return any((dir_path / st).is_dir() for st in _KNOWLEDGE_SUBTYPES)


def _collect_knowledge_nodes(
    current: Path, warehouse_path: Path, nodes: list[str]
) -> None:
    """Recursively collect knowledge node paths (warehouse-relative) into nodes.

    Recursion always continues — a directory can be both a node and a parent of
    child nodes (e.g. data-platform/ has its own decisions/ AND sub-nodes clickhouse/, dbt/).
    """
    if _is_knowledge_node(current):
        nodes.append(str(current.relative_to(warehouse_path)).replace("\\", "/"))
    for child in sorted(current.iterdir()):
        if (
            child.is_dir()
            and not child.name.startswith(".")
            and child.name not in _KNOWLEDGE_SUBTYPES
        ):
            _collect_knowledge_nodes(child, warehouse_path, nodes)


def _list_knowledge_nodes(warehouse_path: Path) -> list[str]:
    """Return all warehouse-relative knowledge node paths.

    Only directories that directly contain decisions/, lessons/, or facts/ are nodes.
    Grouping/parent folders are excluded.
    """
    knowledge_dir = warehouse_path / "knowledge"
    if not knowledge_dir.exists():
        return []
    nodes: list[str] = []
    _collect_knowledge_nodes(knowledge_dir, warehouse_path, nodes)
    return nodes


def _global_agent_dirs() -> list[Path]:
    """Return candidate global agent directories for all supported tools."""
    return [
        Path.home() / ".config" / "opencode" / "agents",
        Path.home() / ".claude" / "agents",
    ]


def _is_agent_installed(agent_path: str) -> bool:
    """Return True if the warehouse agent is installed in any global agent directory."""
    filename = Path(agent_path).name
    return any((d / filename).exists() for d in _global_agent_dirs())


def _is_adopted(path: str, beacon_settings: BeaconManifest) -> bool:
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


def _build_new_file_commits_map(
    warehouse_path: Path,
    max_commits: int = _NEW_TAG_MAX_COMMITS,
) -> dict[str, int]:
    """Return {file_path: commits_ago} for files first added in the last max_commits commits.

    commits_ago is 1-indexed: 1 = added in HEAD, 2 = added in HEAD~1, etc.
    Returns empty dict if git is unavailable or no added files found.
    """
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(warehouse_path),
                "log",
                f"-{max_commits}",
                "--diff-filter=A",
                "--name-only",
                "--pretty=format:BEACON_COMMIT_MARKER",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {}
    if result.returncode != 0:
        return {}

    file_map: dict[str, int] = {}
    commit_index = 0
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped == "BEACON_COMMIT_MARKER":
            commit_index += 1
        elif stripped and commit_index > 0:
            if stripped not in file_map:
                file_map[stripped] = commit_index
    return file_map


def _annotate_with_commits_ago(
    candidates: list[AdoptCandidate],
    warehouse_path: Path,
) -> None:
    """Set commits_ago on candidates added within _NEW_TAG_MAX_COMMITS commits of HEAD."""
    file_map = _build_new_file_commits_map(warehouse_path)
    if not file_map:
        return
    for candidate in candidates:
        prefix = candidate.path.rstrip("/")
        min_n: int | None = None
        for file_path, n in file_map.items():
            if file_path == prefix or file_path.startswith(prefix + "/"):
                if min_n is None or n < min_n:
                    min_n = n
        if min_n is not None:
            candidate.commits_ago = min_n


def _build_candidates(
    warehouse_path: Path,
    paths: list[str],
    beacon_settings: BeaconManifest,
    *,
    is_new: bool,
) -> list[AdoptCandidate]:
    """Build AdoptCandidate list from a list of warehouse-relative file paths.

    Skills are grouped by directory; knowledge is grouped at subdomain level.
    """
    seen_skill_dirs: set[str] = set()
    seen_knowledge_subdirs: set[str] = set()
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
        elif artifact_type == "knowledge":
            knowledge_node = _find_knowledge_node_for_file(path)
            if knowledge_node is None:
                continue  # file not under decisions/lessons/facts — not a valid node
            if knowledge_node in seen_knowledge_subdirs:
                continue
            if _is_adopted(knowledge_node, beacon_settings):
                continue
            seen_knowledge_subdirs.add(knowledge_node)
            candidates.append(
                AdoptCandidate(
                    artifact_type="knowledge",
                    path=knowledge_node,
                    description="",
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
    beacon_settings: BeaconManifest,
) -> list[AdoptCandidate]:
    """Full-scan mode: return every warehouse artifact not in beacon.yaml."""
    from beacon.distributor import WarehouseDistributor

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

    # Knowledge — discover nodes (dirs with decisions/lessons/facts) directly
    for knowledge_path in _list_knowledge_nodes(warehouse_path):
        if not _is_adopted(knowledge_path, beacon_settings):
            desc = ""
            node_dir = warehouse_path / knowledge_path
            for f in sorted(node_dir.rglob("*.md")):
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

    # Agents — list_available returns paths like "agents/code-reviewer.md"
    # "adopted" means installed in a global agent directory, not beacon.yaml
    for agent_path in available.get("agents", []):
        if not _is_agent_installed(agent_path):
            desc = _extract_description(warehouse_path, agent_path)
            candidates.append(
                AdoptCandidate(
                    artifact_type="agents",
                    path=agent_path,
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
    beacon_settings: BeaconManifest,
    sync_sha: str | None = None,
    *,
    show_all: bool = False,
) -> tuple[list[AdoptCandidate], list[str]]:
    """Discover warehouse artifacts available to adopt.

    Always performs a full warehouse scan and annotates candidates with
    commits_ago when they were added within _NEW_TAG_MAX_COMMITS commits of HEAD.

    Args:
        warehouse_path: Path to the warehouse root.
        beacon_settings: Parsed beacon.yaml settings.
        sync_sha: Kept for backward compatibility; no longer used for discovery.
        show_all: Kept for backward compatibility; full scan is always used.

    Returns:
        (candidates, updated_adopted_paths) where:
        - candidates: unadopted AdoptCandidates with commits_ago annotated
        - updated_adopted_paths: always empty (retained for API compatibility)
    """
    candidates = _discover_all(warehouse_path, beacon_settings)
    _annotate_with_commits_ago(candidates, warehouse_path)
    return candidates, []


def _count_unadopted_since(
    warehouse_path: Path,
    beacon_settings: BeaconManifest,
    sync_sha: str,
) -> int:
    """Lightweight count of new warehouse artifacts since sync_sha not in beacon.yaml.

    Uses only git diff + path comparison — no file reads for descriptions.
    """
    new_paths = _run_git_diff(warehouse_path, sync_sha, "A")
    seen_skill_dirs: set[str] = set()
    seen_knowledge_nodes: set[str] = set()
    count = 0

    for path in new_paths:
        artifact_type = _classify_artifact_type(path)
        if artifact_type is None or artifact_type == "agents":
            continue
        if artifact_type == "skills":
            skill_dir = _skill_dir_from_path(path)
            skill_key = skill_dir.rstrip("/")
            if skill_key in seen_skill_dirs:
                continue
            if not _is_adopted(skill_dir, beacon_settings):
                seen_skill_dirs.add(skill_key)
                count += 1
        elif artifact_type == "knowledge":
            # Beacon.yaml stores node-level paths; check at node level
            node = _find_knowledge_node_for_file(path)
            if node is None:
                continue
            if node in seen_knowledge_nodes:
                continue
            if not _is_adopted(node, beacon_settings):
                seen_knowledge_nodes.add(node)
                count += 1
        else:
            if not _is_adopted(path, beacon_settings):
                count += 1

    return count


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
) -> None:
    """Prompt to delete local artifact files for unadopted entries.

    Always requires confirmation.  Files that differ from the warehouse copy
    are flagged as locally modified so the user can make an informed choice.
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

    for _, path, _ in to_delete:
        for parent in path.parents:
            if parent == artifacts_dir:
                break
            try:
                parent.rmdir()
            except OSError:
                break

    console.print(f"[green]✓[/green] Deleted {deleted} file(s).")


def _iter_selectable_leaves(node):
    """Yield tree nodes that have a 'selected' key in their data, recursively."""
    if node.data is not None and "selected" in node.data:
        yield node
    else:
        for child in node.children:
            yield from _iter_selectable_leaves(child)


# ─────────────────────────────────────────────────────────────
# Textual TUI
# ─────────────────────────────────────────────────────────────

_ADOPT_CSS = """
Screen {
    background: $surface-darken-1;
}

#meta-panel {
    height: 4;
    background: $surface-lighten-1;
    border-bottom: solid $surface-lighten-2;
    padding: 1 2;
    color: $text-muted;
}

#tree {
    background: transparent;
    padding: 1 2;
    scrollbar-gutter: stable;
    height: 1fr;
}

#tree > .tree--cursor {
    background: $surface-lighten-1;
    color: $text;
    text-style: none;
}

#desc-panel {
    height: 4;
    background: $surface;
    border-top: solid $surface-lighten-2;
    padding: 0 2;
    color: $text-muted;
}
"""

_DOCS_BASE = "https://github.com/Shadowsong27/agentic-beacon/blob/main/docs"

_SECTION_META: dict[str, tuple[str, str]] = {
    # type → (one-line description, docs path relative to _DOCS_BASE)
    "contexts": (
        "Project-scoped AI context files injected into every agent session",
        "artifact-type-matrix.md",
    ),
    "skills": (
        "Reusable AI workflows and automations shared across projects",
        "artifact-type-matrix.md",
    ),
    "knowledge": (
        "Structured domain knowledge and reference documentation",
        "artifact-type-matrix.md",
    ),
    "agents": (
        "AI agent definitions • installed globally to ~/.claude/agents & ~/.config/opencode/agents",
        "understanding-agent-skills.md",
    ),
}


def _make_cb_id(path: str) -> str:
    """Generate a valid Textual widget ID from a warehouse path."""
    return "cb_" + re.sub(r"[^a-zA-Z0-9_-]", "_", path.rstrip("/"))


class AdoptApp:
    """Textual TUI for interactive artifact selection and unadoption.

    Lazy-imports textual so the module can be imported in environments where
    textual is not installed (tests that mock it out, etc.).

    Default view shows all unadopted artifacts. Press ``t`` to toggle to
    "show all" mode where adopted artifacts are pre-checked and can be
    unchecked to unadopt them.

    Usage::

        app = AdoptApp(candidates, adopted_paths, project_name="my-project", warehouse_name="my-warehouse")
        result = app.run()  # blocks; returns AdoptResult
    """

    def __init__(
        self,
        candidates: list[AdoptCandidate],
        adopted_paths: list[str],
        project_name: str = "",
        warehouse_name: str = "",
    ) -> None:
        self.candidates = candidates
        self.adopted_paths = adopted_paths
        self.project_name = project_name
        self.warehouse_name = warehouse_name

    def run(self) -> AdoptResult:
        """Launch TUI and return AdoptResult (empty lists on cancel)."""
        from textual.app import App, ComposeResult
        from textual.binding import Binding
        from textual.widgets import Footer, Header, Static, Tree

        candidates = self.candidates
        adopted_paths = self.adopted_paths
        project_name = self.project_name
        warehouse_name = self.warehouse_name

        _ARTIFACT_ICONS: dict[str, str] = {
            "contexts": "📄",
            "skills": "🔧",
            "knowledge": "📚",
            "agents": "🤖",
        }

        def _leaf_label(
            path: str,
            selected: bool,
            commits_ago: int | None = None,
            adopted_tag: bool = False,
        ) -> str:
            checkbox = (
                "[bold cyan]\\[x][/bold cyan]" if selected else "[dim]\\[ ][/dim]"
            )
            label = f"{checkbox} [cyan]{path}[/cyan]"
            if commits_ago is not None:
                plural = "s" if commits_ago != 1 else ""
                label += f" [dim yellow]\\[added {commits_ago} commit{plural} ago][/dim yellow]"
            return label

        class _InnerApp(App[AdoptResult]):
            CSS = _ADOPT_CSS
            TITLE = "Agentic Beacon"
            SUB_TITLE = "Artifact Adoption"
            BINDINGS = [  # type: ignore[assignment]
                Binding("enter", "confirm", "Confirm", priority=True),
                Binding("escape", "cancel", "Cancel", priority=True),
                Binding("q", "cancel", "Quit"),
                Binding("space", "toggle_selection", "Toggle", priority=True),
                Binding("a", "select_all", "Select All"),
                Binding("n", "select_none", "Select None"),
                Binding("t", "toggle_view", "Show All"),
                Binding("o", "open_docs", "Open Docs"),
            ]

            def __init__(self_inner) -> None:  # noqa: N805
                super().__init__()
                self_inner._candidates = candidates
                self_inner._adopted_paths = adopted_paths
                self_inner._show_all = False
                self_inner._current_docs_url: str = ""

            def compose(self_inner) -> ComposeResult:  # noqa: N805
                yield Header(show_clock=False)
                yield Static("", id="meta-panel")
                yield Tree("root", id="tree")
                yield Static("", id="desc-panel")
                yield Footer()

            def on_mount(self_inner) -> None:  # noqa: N805
                self_inner.theme = "catppuccin-mocha"
                # Meta panel: project + warehouse info
                parts: list[str] = []
                if project_name:
                    parts.append(f"[dim]project:[/dim] [bold]{project_name}[/bold]")
                if warehouse_name:
                    parts.append(f"[dim]warehouse:[/dim] [bold]{warehouse_name}[/bold]")
                unadopted_n = len(self_inner._candidates)
                adopted_n = len(self_inner._adopted_paths)
                parts.append(
                    f"[dim]{unadopted_n} unadopted[/dim]  [dim]{adopted_n} adopted[/dim]"
                )
                self_inner.query_one("#meta-panel", Static).update(
                    "  " + "   │   ".join(parts)
                )
                self_inner._rebuild_tree()

            def _rebuild_tree(self_inner) -> None:  # noqa: N805
                tree = self_inner.query_one("#tree", Tree)
                tree.root.remove_children()
                tree.show_root = False
                tree.root.expand()

                # Build display items based on current view mode
                by_type: dict[str, list[tuple]] = {}

                if not self_inner._show_all:
                    for c in self_inner._candidates:
                        by_type.setdefault(c.artifact_type, []).append(
                            (c.path, c.description, False, c.commits_ago, False)
                        )
                else:
                    # Unadopted candidates (unchecked)
                    for c in self_inner._candidates:
                        by_type.setdefault(c.artifact_type, []).append(
                            (c.path, c.description, False, c.commits_ago, False)
                        )
                    # Adopted paths (pre-checked)
                    unadopted_paths = {c.path for c in self_inner._candidates}
                    for path in self_inner._adopted_paths:
                        if path in unadopted_paths:
                            continue
                        atype = _classify_artifact_type(path)
                        if atype is None:
                            # Infer type from first path segment
                            atype = path.split("/")[0] if "/" in path else "contexts"
                        by_type.setdefault(atype, []).append(
                            (path, "", True, None, True)
                        )

                def _build_knowledge_subtree(
                    parent_node, items, depth_prefix: str = ""
                ) -> None:
                    """Recursively build nested knowledge subtree.

                    Non-node parent folders become expandable branches.
                    Only nodes get checkboxes. A node that is also a parent folder
                    (dual-role, e.g. data-platform/ that has its own decisions/ AND
                    child nodes clickhouse/, dbt/) renders its checkbox on the folder
                    label so it is selectable in-place.
                    """
                    direct: list[tuple] = []
                    subgroups: dict[str, list[tuple]] = {}
                    for (
                        full_path,
                        desc,
                        selected,
                        commits_ago_val,
                        orig_adopted,
                    ) in items:
                        rel = full_path[len("knowledge/") :]
                        if depth_prefix:
                            rel = rel[len(depth_prefix) + 1 :]
                        slash_idx = rel.find("/")
                        if slash_idx == -1:
                            direct.append(
                                (
                                    full_path,
                                    rel,
                                    desc,
                                    selected,
                                    commits_ago_val,
                                    orig_adopted,
                                )
                            )
                        else:
                            group = rel[:slash_idx]
                            subgroups.setdefault(group, []).append(
                                (
                                    full_path,
                                    desc,
                                    selected,
                                    commits_ago_val,
                                    orig_adopted,
                                )
                            )
                    # direct items that are also group keys (dual-role nodes)
                    dual_role: dict[str, tuple] = {
                        name: item
                        for item in direct
                        for name in [item[1]]
                        if name in subgroups
                    }
                    for (
                        full_path,
                        name,
                        desc,
                        selected,
                        commits_ago_val,
                        orig_adopted,
                    ) in sorted(direct, key=lambda x: x[1]):
                        if name in dual_role:
                            continue  # rendered as a folder-node below
                        parent_node.add_leaf(
                            _leaf_label(
                                name,
                                selected,
                                commits_ago_val,
                                orig_adopted and self_inner._show_all,
                            ),
                            data={
                                "path": full_path,
                                "display_name": name,
                                "desc": desc,
                                "selected": selected,
                                "originally_adopted": orig_adopted,
                                "commits_ago": commits_ago_val,
                            },
                        )
                    for group_name in sorted(subgroups.keys()):
                        sub_prefix = (
                            group_name
                            if not depth_prefix
                            else f"{depth_prefix}/{group_name}"
                        )
                        dual = dual_role.get(group_name)
                        if dual:
                            # Folder is also a node — give it a checkbox
                            fp, _, d_desc, d_sel, d_cago, d_orig = dual
                            sub_node = parent_node.add(
                                _leaf_label(
                                    f"{group_name}/",
                                    d_sel,
                                    d_cago,
                                    d_orig and self_inner._show_all,
                                ),
                                expand=True,
                                data={
                                    "path": fp,
                                    "display_name": f"{group_name}/",
                                    "desc": d_desc,
                                    "selected": d_sel,
                                    "originally_adopted": d_orig,
                                    "commits_ago": d_cago,
                                },
                            )
                        else:
                            sub_node = parent_node.add(
                                f"[dim white]{group_name}/[/dim white]",
                                expand=True,
                                data={"folder": group_name},
                            )
                        _build_knowledge_subtree(
                            sub_node, subgroups[group_name], sub_prefix
                        )

                for atype in ["contexts", "skills", "knowledge", "agents"]:
                    type_items = by_type.get(atype, [])
                    if not type_items:
                        continue
                    icon = _ARTIFACT_ICONS.get(atype, "📂")
                    section_desc, docs_path = _SECTION_META.get(atype, ("", ""))
                    docs_url = f"{_DOCS_BASE}/{docs_path}" if docs_path else ""
                    docs_link = (
                        f"  [dim][link={docs_url}]docs ↗[/link][/dim]"
                        if docs_url
                        else ""
                    )
                    section_label = (
                        f"[bold white]{icon} {atype}[/bold white]"
                        f"  [dim]{section_desc}[/dim]"
                        f"{docs_link}"
                    )
                    folder = tree.root.add(
                        section_label,
                        expand=True,
                        data={"docs_url": docs_url, "section": atype},
                    )
                    if atype == "knowledge":
                        _build_knowledge_subtree(folder, type_items)
                    else:
                        for (
                            path,
                            desc,
                            selected,
                            commits_ago_val,
                            orig_adopted,
                        ) in type_items:
                            folder.add_leaf(
                                _leaf_label(
                                    path,
                                    selected,
                                    commits_ago_val,
                                    orig_adopted and self_inner._show_all,
                                ),
                                data={
                                    "path": path,
                                    "desc": desc,
                                    "selected": selected,
                                    "originally_adopted": orig_adopted,
                                    "commits_ago": commits_ago_val,
                                },
                            )

            def on_tree_node_highlighted(
                self_inner, event: Tree.NodeHighlighted
            ) -> None:  # noqa: N805
                data = event.node.data
                panel = self_inner.query_one("#desc-panel", Static)
                if data and data.get("docs_url"):
                    # Folder/section node — show docs URL + open hint
                    self_inner._current_docs_url = data["docs_url"]
                    panel.update(
                        f"[dim]docs:[/dim]  {data['docs_url']}  "
                        "[dim]([bold]o[/bold] to open in browser)[/dim]"
                    )
                elif data and data.get("desc"):
                    self_inner._current_docs_url = ""
                    panel.update(f"[dim]desc:[/dim]  {data['desc']}")
                else:
                    self_inner._current_docs_url = ""
                    mode = "all" if self_inner._show_all else "unadopted"
                    panel.update(
                        f"[dim]showing {mode} — "
                        "[dim]space[/dim] toggle  [dim]enter[/dim] confirm  "
                        "[dim]a[/dim] all  [dim]n[/dim] none  [dim]t[/dim] toggle view"
                    )

            def _toggle_node_selection(self_inner, node) -> None:  # noqa: N805
                """Toggle a leaf node's selection state, or expand/collapse a folder."""
                if node is None:
                    return
                data = node.data
                if data is not None and "selected" in data:
                    data["selected"] = not data["selected"]
                    node.set_label(
                        _leaf_label(
                            data.get("display_name") or data["path"],
                            data["selected"],
                            data.get("commits_ago"),
                            data.get("originally_adopted", False)
                            and self_inner._show_all,
                        )
                    )
                else:
                    node.toggle()

            def action_toggle_selection(self_inner) -> None:  # noqa: N805
                tree = self_inner.query_one("#tree", Tree)
                self_inner._toggle_node_selection(tree.cursor_node)

            def on_tree_node_selected(self_inner, event: Tree.NodeSelected) -> None:  # noqa: N805
                self_inner._toggle_node_selection(event.node)

            def action_confirm(self_inner) -> None:  # noqa: N805
                tree = self_inner.query_one("#tree", Tree)
                to_adopt: list[str] = []
                to_unadopt: list[str] = []
                for section_node in tree.root.children:
                    for leaf in _iter_selectable_leaves(section_node):
                        path = leaf.data["path"]
                        selected = leaf.data.get("selected", False)
                        orig_adopted = leaf.data.get("originally_adopted", False)
                        if not orig_adopted and selected:
                            to_adopt.append(path)
                        elif orig_adopted and not selected:
                            to_unadopt.append(path)
                self_inner.exit(AdoptResult(to_adopt=to_adopt, to_unadopt=to_unadopt))

            def action_cancel(self_inner) -> None:  # noqa: N805
                self_inner.exit(AdoptResult())

            def action_toggle_view(self_inner) -> None:  # noqa: N805
                self_inner._show_all = not self_inner._show_all
                self_inner._rebuild_tree()
                panel = self_inner.query_one("#desc-panel", Static)
                mode = (
                    "all artifacts" if self_inner._show_all else "unadopted artifacts"
                )
                panel.update(
                    f"[dim]showing {mode} — press [bold]t[/bold] to toggle view[/dim]"
                )

            def action_open_docs(self_inner) -> None:  # noqa: N805
                if self_inner._current_docs_url:
                    self_inner.open_url(self_inner._current_docs_url)

            def action_select_all(self_inner) -> None:  # noqa: N805
                tree = self_inner.query_one("#tree", Tree)
                for section_node in tree.root.children:
                    for leaf in _iter_selectable_leaves(section_node):
                        leaf.data["selected"] = True
                        leaf.set_label(
                            _leaf_label(
                                leaf.data.get("display_name") or leaf.data["path"],
                                True,
                                leaf.data.get("commits_ago"),
                                leaf.data.get("originally_adopted", False)
                                and self_inner._show_all,
                            )
                        )

            def action_select_none(self_inner) -> None:  # noqa: N805
                tree = self_inner.query_one("#tree", Tree)
                for section_node in tree.root.children:
                    for leaf in _iter_selectable_leaves(section_node):
                        leaf.data["selected"] = False
                        leaf.set_label(
                            _leaf_label(
                                leaf.data.get("display_name") or leaf.data["path"],
                                False,
                                leaf.data.get("commits_ago"),
                                leaf.data.get("originally_adopted", False)
                                and self_inner._show_all,
                            )
                        )

        result = _InnerApp().run()
        return result if result is not None else AdoptResult()
