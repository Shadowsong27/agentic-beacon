"""Textual TUI for interactive artifact adoption.

Two independent flows in one TUI:

1. Pending TODO (top section, only shown when pending.yaml has entries) —
   per-entry yes/no resolution. ``y`` = accept (adopt + remove from pending),
   ``n`` = reject (remove from pending). Unmarked entries stay in pending.yaml.

2. Warehouse browser (contexts/skills/agents sections) — diff between
   warehouse and beacon.yaml. ``space`` toggles a checkbox; ``t`` flips
   between unadopted-only and show-all (so adopted items can be unchecked
   to unadopt them). ``A`` = select all, ``N`` = select none.
"""

from __future__ import annotations

import re
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Static, Tree

from beacon.core.manifest.pending import PendingEntry
from beacon.domains.adoption.discovery import classify_artifact_type
from beacon.domains.adoption.models import AdoptCandidate, AdoptResult

# ─────────────────────────────────────────────────────────────
# Tree helpers
# ─────────────────────────────────────────────────────────────


def iter_selectable_leaves(node):
    """Yield warehouse-browser leaves (have a 'selected' key)."""
    if node.data is not None and "selected" in node.data:
        yield node
    else:
        for child in node.children:
            yield from iter_selectable_leaves(child)


def iter_pending_leaves(node):
    """Yield pending-TODO leaves (have a 'pending' key)."""
    if node.data is not None and node.data.get("pending"):
        yield node
    else:
        for child in node.children:
            yield from iter_pending_leaves(child)


def _folder_label(name: str, all_selected: bool, any_selected: bool) -> str:
    """Render a grouping folder label with a checkbox reflecting child selection state."""
    if all_selected:
        checkbox = "[bold cyan]\\[x][/bold cyan]"
    elif any_selected:
        checkbox = "[bold yellow]\\[-][/bold yellow]"
    else:
        checkbox = "[dim]\\[ ][/dim]"
    return f"{checkbox} [dim white]{name}/[/dim white]"


def _refresh_ancestor_folders(node) -> None:
    """Walk up the tree from node, refreshing every grouping-folder ancestor."""
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
    """Recursively refresh every grouping-folder label in a subtree."""
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

_PENDING_TYPE_TO_ARTIFACT_TYPE: dict[str, str] = {
    "skill": "skills",
    "context": "contexts",
    "agent": "agents",
}

# Pending action visual marks
_PENDING_MARKS: dict[str | None, str] = {
    "accept": "[bold green]\\[Y][/bold green]",
    "reject": "[bold red]\\[N][/bold red]",
    None: "[dim]\\[ ][/dim]",
}


# ─────────────────────────────────────────────────────────────
# Confirm modal
# ─────────────────────────────────────────────────────────────


class _ConfirmScreen(ModalScreen):
    """Modal confirm screen showing the impact summary before commit."""

    CSS = """
    _ConfirmScreen {
        align: center middle;
    }
    #confirm-panel {
        width: 70;
        height: auto;
        padding: 2 4;
        background: $surface;
        border: thick $primary;
    }
    """

    def __init__(
        self,
        *,
        n_adopt: int,
        n_unadopt: int,
        n_pending_accept: int,
        n_pending_reject: int,
        n_pending_defer: int,
    ) -> None:
        super().__init__()
        self._n_adopt = n_adopt
        self._n_unadopt = n_unadopt
        self._n_pending_accept = n_pending_accept
        self._n_pending_reject = n_pending_reject
        self._n_pending_defer = n_pending_defer

    def compose(self) -> ComposeResult:
        lines = ["[bold]Apply changes?[/bold]", ""]
        if self._n_adopt or self._n_unadopt:
            lines.append(
                f"  Warehouse: [bold green]{self._n_adopt}[/bold green] adopt  "
                f"[bold yellow]{self._n_unadopt}[/bold yellow] unadopt"
            )
        if self._n_pending_accept or self._n_pending_reject or self._n_pending_defer:
            lines.append(
                f"  Pending:   [bold green]{self._n_pending_accept}[/bold green] accept  "
                f"[bold red]{self._n_pending_reject}[/bold red] reject  "
                f"[dim]{self._n_pending_defer}[/dim] defer"
            )
        lines.extend(["", "[dim]Enter[/dim] to proceed  [dim]Escape[/dim] to cancel"])
        yield Static("\n".join(lines), id="confirm-panel")

    def on_key(self, event) -> None:
        if event.key == "enter":
            event.stop()
            self.dismiss(True)
        elif event.key in ("escape", "q"):
            event.stop()
            self.dismiss(False)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────


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
    """Render a warehouse-browser leaf label."""
    mark = "[bold cyan]\\[x][/bold cyan]" if selected else "[dim]\\[ ][/dim]"
    label = f"{mark} [cyan]{path}[/cyan]"
    if provenance:
        label += f" [dim yellow]{provenance}[/dim yellow]"
    if adopted_tag:
        label += " [dim](adopted)[/dim]"
    if commits_ago is not None:
        plural = "s" if commits_ago != 1 else ""
        label += f" [dim yellow]\\[added {commits_ago} commit{plural} ago][/dim yellow]"
    return label


def _pending_leaf_label(
    path: str,
    action: str | None,
    entry: PendingEntry,
) -> str:
    """Render a pending-TODO leaf label with action mark and source annotation."""
    mark = _PENDING_MARKS.get(action, _PENDING_MARKS[None])
    label = f"{mark} [cyan]{path}[/cyan]"
    label += f" [dim]({entry.type} via {entry.source})[/dim]"
    return label


# ─────────────────────────────────────────────────────────────
# Inner app
# ─────────────────────────────────────────────────────────────


class AdoptInnerApp(App[AdoptResult]):
    """Inner Textual App for the adoption TUI."""

    CSS = _ADOPT_CSS
    TITLE = "Agentic Beacon"
    SUB_TITLE = "Artifact Adoption"
    BINDINGS = [  # type: ignore[assignment]
        Binding("enter", "apply", "Apply", priority=True),
        Binding("escape", "cancel", "Cancel", priority=True),
        Binding("q", "cancel", "Quit"),
        Binding("space", "toggle_selection", "Toggle", priority=True),
        Binding("y", "pending_accept", "Yes"),
        Binding("n", "pending_reject", "No"),
        Binding("A", "select_all", "All"),
        Binding("N", "select_none", "None"),
        Binding("t", "toggle_view", "Show All"),
        Binding("o", "open_docs", "Open Docs"),
    ]

    def __init__(
        self,
        candidates: list[AdoptCandidate],
        pending_entries: list[PendingEntry],
        adopted_paths: list[str],
        project_name: str = "",
        warehouse_name: str = "",
        warehouse_path: Path | None = None,
        show_all_default: bool = False,
    ) -> None:
        super().__init__()
        self._candidates = candidates
        self._pending_entries = pending_entries
        self._pending_map = {e.path: e for e in pending_entries}
        self._adopted_paths = adopted_paths
        self._project_name = project_name
        self._warehouse_name = warehouse_name
        self._warehouse_path = warehouse_path
        self._show_all = show_all_default
        self._current_docs_url: str = ""
        # Project-scoped-agents propagation state
        self._required_by: dict[str, list[str]] = {}
        self._user_explicit: dict[str, bool] = {}
        self._status_message: str = ""
        # Pending TODO action map: path → "accept" | "reject"
        self._pending_actions: dict[str, str] = {}

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
        pending_n = len(self._pending_entries)
        parts.append(
            f"[dim]{unadopted_n} unadopted[/dim]  [dim]{adopted_n} adopted[/dim]"
            + (f"  [dim]{pending_n} pending[/dim]" if pending_n else "")
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

        # ── Pending TODO list (flat at top, only if non-empty) ──
        # Rendered as a flat list of selectable items at root level — no parent
        # folder — so it reads as an inbox, not a tree branch.
        if self._pending_entries:
            tree.root.add_leaf(
                "[bold white]📥 PENDING TODO[/bold white]"
                "  [dim](y=yes  n=no  default=defer)[/dim]",
                data={"header": True},
            )
            for entry in self._pending_entries:
                action = self._pending_actions.get(entry.path)
                tree.root.add_leaf(
                    _pending_leaf_label(entry.path, action, entry),
                    data={
                        "pending": True,
                        "path": entry.path,
                        "pending_type": entry.type,
                        "pending_action": action,
                        "desc": "",
                    },
                )
            # Visual separator between pending list and warehouse tree.
            tree.root.add_leaf(
                "[dim]─────────────────────────────[/dim]",
                data={"header": True},
            )

        # ── Warehouse browser sections ──
        # by_type tuples: (path, desc, selected, commits_ago, orig_adopted)
        by_type: dict[str, list[tuple]] = {}
        for c in self._candidates:
            by_type.setdefault(c.artifact_type, []).append(
                (c.path, c.description, False, c.commits_ago, False)
            )

        if self._show_all:
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
            for path, desc, selected, commits_ago_val, orig_adopted in type_items:
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

    # ── Description panel ──
    def on_tree_node_highlighted(self, event) -> None:
        data = event.node.data
        panel = self.query_one("#desc-panel", Static)
        if data and data.get("docs_url"):
            self._current_docs_url = data["docs_url"]
            panel.update(
                f"[dim]docs:[/dim]  {data['docs_url']}  "
                "[dim]([bold]o[/bold] to open in browser)[/dim]"
            )
        elif data and data.get("pending"):
            self._current_docs_url = ""
            entry = self._pending_map.get(data["path"])
            if entry is not None:
                panel.update(
                    f"[dim]pending:[/dim]  {entry.path}  "
                    f"[dim]({entry.type} via {entry.source})[/dim]   "
                    "[dim][bold]y[/bold] yes  [bold]n[/bold] no[/dim]"
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
                    f"[dim]warehouse: showing {mode} — "
                    "[bold]space[/bold] toggle  "
                    "[bold]A[/bold] all  [bold]N[/bold] none  "
                    "[bold]t[/bold] view[/dim]   "
                    "[dim]pending: [bold]y[/bold] yes  [bold]n[/bold] no[/dim]"
                )

    # ── Warehouse browser interactions ──
    def _set_skill_selected(self, skill_path: str, selected: bool) -> None:
        """Update a warehouse skill leaf's selected state by path."""
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

    def _toggle_warehouse_node(self, node) -> None:
        """Toggle the warehouse-browser leaf at *node* (or its folder)."""
        data = node.data
        if data is None:
            node.toggle()
            return

        if "selected" in data:
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

            if atype == "skills" and new_state:
                self._user_explicit[path] = True

            if atype == "agents" and new_state:
                skills = self._load_agent_skills(path)
                for skill_name in skills:
                    skill_path = f"skills/{skill_name}/"
                    self._required_by.setdefault(skill_path, [])
                    if path not in self._required_by[skill_path]:
                        self._required_by[skill_path].append(path)
                    self._set_skill_selected(skill_path, True)
            elif atype == "agents" and not new_state:
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
                    data["path"],
                    new_state,
                    data.get("commits_ago"),
                    data.get("originally_adopted", False) and self._show_all,
                    provenance=_format_provenance(self._required_by.get(path, []))
                    if atype == "skills"
                    else "",
                )
            )
            _refresh_ancestor_folders(node)
        elif "folder" in data:
            leaves = list(iter_selectable_leaves(node))
            new_state = not all(lf.data.get("selected", False) for lf in leaves)
            for lf in leaves:
                lf.data["selected"] = new_state
                lf.set_label(
                    _leaf_label(
                        lf.data["path"],
                        new_state,
                        lf.data.get("commits_ago"),
                        lf.data.get("originally_adopted", False) and self._show_all,
                    )
                )
            node.set_label(_folder_label(data["folder"], new_state, new_state))
            _refresh_ancestor_folders(node)
        else:
            node.toggle()

    # ── Pending TODO interactions ──
    def _set_pending_action(self, node, action: str | None) -> None:
        """Mark a pending-TODO leaf with action 'accept', 'reject', or None (defer)."""
        if node is None or node.data is None or not node.data.get("pending"):
            return
        path = node.data["path"]
        if action is None:
            self._pending_actions.pop(path, None)
        else:
            self._pending_actions[path] = action
        node.data["pending_action"] = action
        entry = self._pending_map[path]
        node.set_label(_pending_leaf_label(path, action, entry))

    def action_pending_accept(self) -> None:
        tree = self.query_one("#tree", Tree)
        node = tree.cursor_node
        if node is None or node.data is None or not node.data.get("pending"):
            return
        # Toggle: pressing y on an already-accepted entry clears it (defers).
        current = self._pending_actions.get(node.data["path"])
        self._set_pending_action(node, None if current == "accept" else "accept")

    def action_pending_reject(self) -> None:
        tree = self.query_one("#tree", Tree)
        node = tree.cursor_node
        if node is None or node.data is None or not node.data.get("pending"):
            return
        current = self._pending_actions.get(node.data["path"])
        self._set_pending_action(node, None if current == "reject" else "reject")

    def action_toggle_selection(self) -> None:
        tree = self.query_one("#tree", Tree)
        node = tree.cursor_node
        if node is None:
            return
        # On a pending leaf, space cycles accept ↔ defer (mirrors warehouse UX).
        if node.data is not None and node.data.get("pending"):
            current = self._pending_actions.get(node.data["path"])
            self._set_pending_action(node, None if current == "accept" else "accept")
            return
        self._toggle_warehouse_node(node)

    def on_tree_node_selected(self, event) -> None:
        node = event.node
        if node.data is not None and node.data.get("pending"):
            current = self._pending_actions.get(node.data["path"])
            self._set_pending_action(node, None if current == "accept" else "accept")
            return
        self._toggle_warehouse_node(node)

    # ── Apply / cancel ──
    def action_apply(self) -> None:
        if len(self.screen_stack) > 1:
            # Confirm modal already open — Enter dismisses it.
            self.screen.dismiss(True)
            return

        tree = self.query_one("#tree", Tree)

        n_adopt = 0
        n_unadopt = 0
        for section_node in tree.root.children:
            for leaf in iter_selectable_leaves(section_node):
                selected = leaf.data.get("selected", False)
                orig_adopted = leaf.data.get("originally_adopted", False)
                if not orig_adopted and selected:
                    n_adopt += 1
                elif orig_adopted and not selected:
                    n_unadopt += 1

        n_pending_accept = sum(
            1 for a in self._pending_actions.values() if a == "accept"
        )
        n_pending_reject = sum(
            1 for a in self._pending_actions.values() if a == "reject"
        )
        n_pending_defer = (
            len(self._pending_entries) - n_pending_accept - n_pending_reject
        )

        if (
            n_adopt == 0
            and n_unadopt == 0
            and n_pending_accept == 0
            and n_pending_reject == 0
        ):
            # Nothing to apply — exit with empty result.
            self.exit(AdoptResult())
            return

        def _on_confirm(proceed: bool | None) -> None:
            if proceed:
                self._finalize()

        self.push_screen(
            _ConfirmScreen(
                n_adopt=n_adopt,
                n_unadopt=n_unadopt,
                n_pending_accept=n_pending_accept,
                n_pending_reject=n_pending_reject,
                n_pending_defer=n_pending_defer,
            ),
            _on_confirm,
        )

    def _finalize(self) -> None:
        """Build the AdoptResult and exit."""
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

        pending_accept = [p for p, a in self._pending_actions.items() if a == "accept"]
        pending_reject = [p for p, a in self._pending_actions.items() if a == "reject"]

        self.exit(
            AdoptResult(
                to_adopt=to_adopt,
                to_unadopt=to_unadopt,
                pending_accept=pending_accept,
                pending_reject=pending_reject,
            )
        )

    def action_cancel(self) -> None:
        self.exit(AdoptResult())

    # ── Bulk / view actions ──
    def action_toggle_view(self) -> None:
        self._show_all = not self._show_all
        self._rebuild_tree()
        panel = self.query_one("#desc-panel", Static)
        mode = "all artifacts" if self._show_all else "unadopted artifacts"
        panel.update(
            f"[dim]warehouse: showing {mode} — press [bold]t[/bold] to toggle[/dim]"
        )

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
                        leaf.data["path"],
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
                        leaf.data["path"],
                        False,
                        leaf.data.get("commits_ago"),
                        leaf.data.get("originally_adopted", False) and self._show_all,
                    )
                )
            _refresh_all_folders(section_node)
        self._required_by.clear()
        self._user_explicit.clear()


# ─────────────────────────────────────────────────────────────
# Public wrapper
# ─────────────────────────────────────────────────────────────


class AdoptApp:
    """Textual TUI for interactive artifact adoption (warehouse browser + pending TODO).

    Usage::

        app = AdoptApp(candidates, pending_entries, adopted_paths, ...)
        result = app.run()  # blocks; returns AdoptResult
    """

    def __init__(
        self,
        candidates: list[AdoptCandidate],
        pending_entries: list[PendingEntry],
        adopted_paths: list[str],
        project_name: str = "",
        warehouse_name: str = "",
        warehouse_path: Path | None = None,
    ) -> None:
        self.candidates = candidates
        self.pending_entries = pending_entries
        self.adopted_paths = adopted_paths
        self.project_name = project_name
        self.warehouse_name = warehouse_name
        self.warehouse_path = warehouse_path

    def run(self) -> AdoptResult:
        """Launch TUI and return AdoptResult (empty lists on cancel)."""
        inner = AdoptInnerApp(
            self.candidates,
            self.pending_entries,
            self.adopted_paths,
            self.project_name,
            self.warehouse_name,
            self.warehouse_path,
        )
        result = inner.run()
        return result if result is not None else AdoptResult()
