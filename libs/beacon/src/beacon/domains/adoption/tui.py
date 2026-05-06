"""Textual TUI for interactive artifact selection and unadoption.

Provides:
- AdoptApp: textual TUI for interactive selection and unadoption
- make_cb_id: generate valid Textual widget IDs from warehouse paths
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Static, Tree

from beacon.domains.adoption.discovery import classify_artifact_type
from beacon.domains.adoption.models import AdoptCandidate, AdoptResult

if TYPE_CHECKING:
    pass


# ─────────────────────────────────────────────────────────────
# Tree helpers
# ─────────────────────────────────────────────────────────────


def iter_selectable_leaves(node):
    """Yield tree nodes that have a 'selected' key in their data, recursively."""
    if node.data is not None and "selected" in node.data:
        yield node
    else:
        for child in node.children:
            yield from iter_selectable_leaves(child)


def _folder_label(name: str, all_selected: bool, any_selected: bool) -> str:
    """Render a grouping folder label with a checkbox reflecting child selection state.

    - all selected  → [x] name/
    - some selected → [-] name/
    - none selected → [ ] name/
    """
    if all_selected:
        checkbox = "[bold cyan]\\[x][/bold cyan]"
    elif any_selected:
        checkbox = "[bold yellow]\\[-][/bold yellow]"
    else:
        checkbox = "[dim]\\[ ][/dim]"
    return f"{checkbox} [dim white]{name}/[/dim white]"


def _refresh_ancestor_folders(node) -> None:
    """Walk up the tree from node, refreshing every pure grouping-folder ancestor.

    A pure grouping folder has ``data={"folder": name}`` (no ``"selected"`` key).
    Its label is recomputed from the selection state of all its selectable descendants.
    """
    parent = node.parent
    while parent is not None:
        data = parent.data
        if data is not None and "folder" in data and "selected" not in data:
            leaves = list(iter_selectable_leaves(parent))
            if leaves:
                any_sel = any(lf.data.get("selected", False) for lf in leaves)
                all_sel = all(lf.data.get("selected", False) for lf in leaves)
                parent.set_label(_folder_label(data["folder"], all_sel, any_sel))
        parent = parent.parent


def _refresh_all_folders(node) -> None:
    """Recursively refresh every grouping-folder label in a subtree (bottom-up).

    Used after bulk select-all / select-none operations where every folder
    needs to be updated at once.
    """
    for child in node.children:
        _refresh_all_folders(child)
    data = node.data
    if data is not None and "folder" in data and "selected" not in data:
        leaves = list(iter_selectable_leaves(node))
        if leaves:
            any_sel = any(lf.data.get("selected", False) for lf in leaves)
            all_sel = all(lf.data.get("selected", False) for lf in leaves)
            node.set_label(_folder_label(data["folder"], all_sel, any_sel))


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
    "agents": (
        "AI agent definitions • declared per-project in beacon.yaml & installed globally",
        "understanding-agent-skills.md",
    ),
}

_ARTIFACT_ICONS: dict[str, str] = {
    "contexts": "📄",
    "skills": "🔧",
    "agents": "🤖",
}


def make_cb_id(path: str) -> str:
    """Generate a valid Textual widget ID from a warehouse path."""
    return "cb_" + re.sub(r"[^a-zA-Z0-9_-]", "_", path.rstrip("/"))


def _agent_name_from_path(path: str) -> str:
    """Extract agent stem from path like 'agents/name.md'."""
    if path.startswith("agents/"):
        path = path[7:]
    if path.endswith(".md"):
        path = path[:-3]
    return path


def _format_provenance(required_by: list[str]) -> str:
    """Format provenance text, capping at 3 agents + '+N more'."""
    if not required_by:
        return ""
    display = required_by[:3]
    suffix = ""
    if len(required_by) > 3:
        suffix = f" +{len(required_by) - 3} more"
    return f" (required by {', '.join(display)}{suffix})"


def _leaf_label(
    path: str,
    selected: bool,
    commits_ago: int | None = None,
    adopted_tag: bool = False,
    provenance: str = "",
) -> str:
    checkbox = "[bold cyan]\\[x][/bold cyan]" if selected else "[dim]\\[ ][/dim]"
    label = f"{checkbox} [cyan]{path}[/cyan]"
    if provenance:
        label += f" [dim yellow]{provenance}[/dim yellow]"
    if commits_ago is not None:
        plural = "s" if commits_ago != 1 else ""
        label += f" [dim yellow]\\[added {commits_ago} commit{plural} ago][/dim yellow]"
    return label


class AdoptInnerApp(App[AdoptResult]):
    """Inner Textual App for the adoption TUI.

    Extracted from AdoptApp for testability.
    """

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

    def __init__(
        self,
        candidates: list[AdoptCandidate],
        adopted_paths: list[str],
        project_name: str = "",
        warehouse_name: str = "",
        warehouse_path: Path | None = None,
        show_all_default: bool = False,
    ) -> None:
        super().__init__()
        self._candidates = candidates
        self._adopted_paths = adopted_paths
        self._project_name = project_name
        self._warehouse_name = warehouse_name
        self._warehouse_path = warehouse_path
        self._show_all = show_all_default
        self._current_docs_url: str = ""
        # Project-scoped-agents state
        self._required_by: dict[str, list[str]] = {}
        self._user_explicit: dict[str, bool] = {}
        self._status_message: str = ""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static("", id="meta-panel")
        yield Tree("root", id="tree")
        yield Static("", id="desc-panel")
        yield Footer()

    def on_mount(self) -> None:
        self.theme = "catppuccin-mocha"
        parts: list[str] = []
        if self._project_name:
            parts.append(f"[dim]project:[/dim] [bold]{self._project_name}[/bold]")
        if self._warehouse_name:
            parts.append(f"[dim]warehouse:[/dim] [bold]{self._warehouse_name}[/bold]")
        unadopted_n = len(self._candidates)
        adopted_n = len(self._adopted_paths)
        parts.append(
            f"[dim]{unadopted_n} unadopted[/dim]  [dim]{adopted_n} adopted[/dim]"
        )
        self.query_one("#meta-panel", Static).update("  " + "   │   ".join(parts))
        self._rebuild_tree()

    def _load_agent_skills(self, agent_path: str) -> list[str]:
        """Load required skills for an agent from agents.yaml."""
        if self._warehouse_path is None:
            return []
        try:
            from beacon.core.dependencies.manifest import load_agent_manifest

            manifest = load_agent_manifest(self._warehouse_path)
            if manifest is None:
                return []
            agent_name = _agent_name_from_path(agent_path)
            entry = manifest.agents.get(agent_name)
            if entry is None:
                return []
            return list(entry.skills)
        except Exception:
            return []

    def _rebuild_tree(self) -> None:
        tree = self.query_one("#tree", Tree)
        tree.root.remove_children()
        tree.show_root = False
        tree.root.expand()

        by_type: dict[str, list[tuple]] = {}

        if not self._show_all:
            for c in self._candidates:
                by_type.setdefault(c.artifact_type, []).append(
                    (c.path, c.description, False, c.commits_ago, False)
                )
        else:
            for c in self._candidates:
                by_type.setdefault(c.artifact_type, []).append(
                    (c.path, c.description, False, c.commits_ago, False)
                )
            unadopted_paths = {c.path for c in self._candidates}
            for path in self._adopted_paths:
                if path in unadopted_paths:
                    continue
                atype = classify_artifact_type(path)
                if atype is None:
                    atype = path.split("/")[0] if "/" in path else "contexts"
                by_type.setdefault(atype, []).append((path, "", True, None, True))

        for atype in ["contexts", "skills", "agents"]:
            type_items = by_type.get(atype, [])
            if not type_items:
                continue
            icon = _ARTIFACT_ICONS.get(atype, "📂")
            section_desc, docs_path = _SECTION_META.get(atype, ("", ""))
            docs_url = f"{_DOCS_BASE}/{docs_path}" if docs_path else ""
            docs_link = (
                f"  [dim][link={docs_url}]docs ↗[/link][/dim]" if docs_url else ""
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
            for (
                path,
                desc,
                selected,
                commits_ago_val,
                orig_adopted,
            ) in type_items:
                prov = ""
                if atype == "skills":
                    req_list = self._required_by.get(path, [])
                    prov = _format_provenance(req_list)
                folder.add_leaf(
                    _leaf_label(
                        path,
                        selected,
                        commits_ago_val,
                        orig_adopted and self._show_all,
                        provenance=prov,
                    ),
                    data={
                        "path": path,
                        "desc": desc,
                        "selected": selected,
                        "originally_adopted": orig_adopted,
                        "commits_ago": commits_ago_val,
                        "artifact_type": atype,
                    },
                )

    def on_tree_node_highlighted(self, event) -> None:
        data = event.node.data
        panel = self.query_one("#desc-panel", Static)
        if data and data.get("docs_url"):
            self._current_docs_url = data["docs_url"]
            panel.update(
                f"[dim]docs:[/dim]  {data['docs_url']}  "
                "[dim]([bold]o[/bold] to open in browser)[/dim]"
            )
        elif data and data.get("desc"):
            self._current_docs_url = ""
            panel.update(f"[dim]desc:[/dim]  {data['desc']}")
        else:
            self._current_docs_url = ""
            if self._status_message:
                panel.update(f"[yellow]{self._status_message}[/yellow]")
                self._status_message = ""
            else:
                mode = "all" if self._show_all else "unadopted"
                panel.update(
                    f"[dim]showing {mode} — "
                    "[dim]space[/dim] toggle  [dim]enter[/dim] confirm  "
                    "[dim]a[/dim] all  [dim]n[/dim] none  [dim]t[/dim] toggle view"
                )

    def _set_skill_selected(self, skill_path: str, selected: bool) -> None:
        """Update a skill leaf's selected state by path."""
        tree = self.query_one("#tree", Tree)
        for section_node in tree.root.children:
            for leaf in iter_selectable_leaves(section_node):
                if leaf.data.get("path") == skill_path:
                    leaf.data["selected"] = selected
                    req_list = self._required_by.get(skill_path, [])
                    prov = _format_provenance(req_list)
                    leaf.set_label(
                        _leaf_label(
                            skill_path,
                            selected,
                            leaf.data.get("commits_ago"),
                            leaf.data.get("originally_adopted", False)
                            and self._show_all,
                            provenance=prov,
                        )
                    )
                    _refresh_ancestor_folders(leaf)
                    break

    def _toggle_node_selection(self, node) -> None:
        if node is None:
            return
        data = node.data
        if data is not None and "selected" in data:
            atype = data.get("artifact_type", "")
            path = data["path"]

            # Hard-lock: reject unticking a skill that is required by an agent
            if atype == "skills" and data["selected"]:
                req_list = self._required_by.get(path, [])
                if req_list:
                    agents = ", ".join(req_list[:3])
                    if len(req_list) > 3:
                        agents += f" +{len(req_list) - 3} more"
                    self._status_message = f"Required by: {agents} — untick agent first"
                    panel = self.query_one("#desc-panel", Static)
                    panel.update(f"[yellow]{self._status_message}[/yellow]")
                    return

            new_state = not data["selected"]
            data["selected"] = new_state

            # Track user_explicit for skills
            if atype == "skills":
                if new_state:
                    self._user_explicit[path] = True

            # Agent tick propagation
            if atype == "agents" and new_state:
                skills = self._load_agent_skills(path)
                for skill_name in skills:
                    skill_path = f"skills/{skill_name}/"
                    self._required_by.setdefault(skill_path, [])
                    if path not in self._required_by[skill_path]:
                        self._required_by[skill_path].append(path)
                    self._set_skill_selected(skill_path, True)
            elif atype == "agents" and not new_state:
                # Agent untick: remove from required_by
                skills = self._load_agent_skills(path)
                for skill_name in skills:
                    skill_path = f"skills/{skill_name}/"
                    if skill_path in self._required_by:
                        self._required_by[skill_path] = [
                            p for p in self._required_by[skill_path] if p != path
                        ]
                        if not self._required_by[
                            skill_path
                        ] and not self._user_explicit.get(skill_path, False):
                            self._set_skill_selected(skill_path, False)

            node.set_label(
                _leaf_label(
                    data.get("display_name") or data["path"],
                    data["selected"],
                    data.get("commits_ago"),
                    data.get("originally_adopted", False) and self._show_all,
                    provenance=_format_provenance(self._required_by.get(path, []))
                    if atype == "skills"
                    else "",
                )
            )
            _refresh_ancestor_folders(node)
        elif data is not None and "folder" in data:
            leaves = list(iter_selectable_leaves(node))
            new_state = not all(lf.data.get("selected", False) for lf in leaves)
            for lf in leaves:
                lf.data["selected"] = new_state
                lf.set_label(
                    _leaf_label(
                        lf.data.get("display_name") or lf.data["path"],
                        new_state,
                        lf.data.get("commits_ago"),
                        lf.data.get("originally_adopted", False) and self._show_all,
                    )
                )
            any_sel = new_state
            all_sel = new_state
            node.set_label(_folder_label(data["folder"], all_sel, any_sel))
            _refresh_ancestor_folders(node)
        else:
            node.toggle()

    def action_toggle_selection(self) -> None:
        tree = self.query_one("#tree", Tree)
        self._toggle_node_selection(tree.cursor_node)

    def on_tree_node_selected(self, event) -> None:
        self._toggle_node_selection(event.node)

    def action_confirm(self) -> None:
        tree = self.query_one("#tree", Tree)
        to_adopt: list[str] = []
        to_unadopt: list[str] = []
        for section_node in tree.root.children:
            for leaf in iter_selectable_leaves(section_node):
                path = leaf.data["path"]
                selected = leaf.data.get("selected", False)
                orig_adopted = leaf.data.get("originally_adopted", False)
                if not orig_adopted and selected:
                    to_adopt.append(path)
                elif orig_adopted and not selected:
                    to_unadopt.append(path)
        self.exit(AdoptResult(to_adopt=to_adopt, to_unadopt=to_unadopt))

    def action_cancel(self) -> None:
        self.exit(AdoptResult())

    def action_toggle_view(self) -> None:
        self._show_all = not self._show_all
        self._rebuild_tree()
        panel = self.query_one("#desc-panel", Static)
        mode = "all artifacts" if self._show_all else "unadopted artifacts"
        panel.update(f"[dim]showing {mode} — press [bold]t[/bold] to toggle view[/dim]")

    def action_open_docs(self) -> None:
        if self._current_docs_url:
            self.open_url(self._current_docs_url)

    def action_select_all(self) -> None:
        tree = self.query_one("#tree", Tree)
        for section_node in tree.root.children:
            for leaf in iter_selectable_leaves(section_node):
                leaf.data["selected"] = True
                path = leaf.data["path"]
                atype = leaf.data.get("artifact_type", "")
                if atype == "skills":
                    self._user_explicit[path] = True
                leaf.set_label(
                    _leaf_label(
                        leaf.data.get("display_name") or leaf.data["path"],
                        True,
                        leaf.data.get("commits_ago"),
                        leaf.data.get("originally_adopted", False) and self._show_all,
                    )
                )
            _refresh_all_folders(section_node)

    def action_select_none(self) -> None:
        tree = self.query_one("#tree", Tree)
        for section_node in tree.root.children:
            for leaf in iter_selectable_leaves(section_node):
                leaf.data["selected"] = False
                leaf.set_label(
                    _leaf_label(
                        leaf.data.get("display_name") or leaf.data["path"],
                        False,
                        leaf.data.get("commits_ago"),
                        leaf.data.get("originally_adopted", False) and self._show_all,
                    )
                )
            _refresh_all_folders(section_node)
        self._required_by.clear()
        self._user_explicit.clear()


class AdoptApp:
    """Textual TUI for interactive artifact selection and unadoption.

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
        warehouse_path: Path | None = None,
    ) -> None:
        self.candidates = candidates
        self.adopted_paths = adopted_paths
        self.project_name = project_name
        self.warehouse_name = warehouse_name
        self.warehouse_path = warehouse_path

    def run(self) -> AdoptResult:
        """Launch TUI and return AdoptResult (empty lists on cancel)."""
        inner = AdoptInnerApp(
            self.candidates,
            self.adopted_paths,
            self.project_name,
            self.warehouse_name,
            self.warehouse_path,
        )
        result = inner.run()
        return result if result is not None else AdoptResult()
