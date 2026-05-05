"""Textual TUI for interactive artifact selection and unadoption.

Provides:
- AdoptApp: textual TUI for interactive selection and unadoption
- make_cb_id: generate valid Textual widget IDs from warehouse paths
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

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
        "AI agent definitions • installed globally to ~/.claude/agents & ~/.config/opencode/agents",
        "understanding-agent-skills.md",
    ),
}


def make_cb_id(path: str) -> str:
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
                        atype = classify_artifact_type(path)
                        if atype is None:
                            # Infer type from first path segment
                            atype = path.split("/")[0] if "/" in path else "contexts"
                        by_type.setdefault(atype, []).append(
                            (path, "", True, None, True)
                        )

                for atype in ["contexts", "skills", "agents"]:
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
                """Toggle a leaf node's selection state.

                For pure grouping folders (data has ``"folder"`` key), toggle all
                descendant leaves instead: if any are unselected, select all; if all
                are already selected, deselect all.
                """
                if node is None:
                    return
                data = node.data
                if data is not None and "selected" in data:
                    # Leaf node — toggle it and refresh ancestor folder labels.
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
                    _refresh_ancestor_folders(node)
                elif data is not None and "folder" in data:
                    # Grouping folder — toggle all descendant leaves.
                    leaves = list(iter_selectable_leaves(node))
                    new_state = not all(lf.data.get("selected", False) for lf in leaves)
                    for lf in leaves:
                        lf.data["selected"] = new_state
                        lf.set_label(
                            _leaf_label(
                                lf.data.get("display_name") or lf.data["path"],
                                new_state,
                                lf.data.get("commits_ago"),
                                lf.data.get("originally_adopted", False)
                                and self_inner._show_all,
                            )
                        )
                    # Refresh this folder and its ancestors.
                    any_sel = new_state
                    all_sel = new_state
                    node.set_label(_folder_label(data["folder"], all_sel, any_sel))
                    _refresh_ancestor_folders(node)
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
                    for leaf in iter_selectable_leaves(section_node):
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
                    for leaf in iter_selectable_leaves(section_node):
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
                    _refresh_all_folders(section_node)

            def action_select_none(self_inner) -> None:  # noqa: N805
                tree = self_inner.query_one("#tree", Tree)
                for section_node in tree.root.children:
                    for leaf in iter_selectable_leaves(section_node):
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
                    _refresh_all_folders(section_node)

        result = _InnerApp().run()
        return result if result is not None else AdoptResult()
