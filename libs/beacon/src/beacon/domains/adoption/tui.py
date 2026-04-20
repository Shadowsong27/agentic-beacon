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
                        atype = classify_artifact_type(path)
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

        result = _InnerApp().run()
        return result if result is not None else AdoptResult()
