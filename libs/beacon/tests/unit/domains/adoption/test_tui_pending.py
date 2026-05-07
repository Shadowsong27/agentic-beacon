"""Headless tests for the pending TODO section in the adopt TUI.

The pending list renders as flat selectable items at the top of the tree (no
parent folder, no nesting). y/n actions mark accept/reject; default is defer.
The warehouse browser sections render as folders below and are unaffected.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from beacon.core.manifest.pending import PendingEntry
from beacon.domains.adoption.models import AdoptCandidate, AdoptResult
from beacon.domains.adoption.tui import AdoptInnerApp

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────


def _entry(path: str, type_: str = "context", source: str = "record-knowledge"):
    return PendingEntry(
        path=path,
        type=type_,  # type: ignore[arg-type]
        action="created",
        source=source,
        created_at=datetime(2026, 5, 7, 12, 0, tzinfo=UTC),
    )


def _node_for_path(app: AdoptInnerApp, path: str):
    """Walk the tree to find the node whose data['path'] == path."""

    def walk(node):
        if node.data and node.data.get("path") == path:
            return node
        for child in node.children:
            r = walk(child)
            if r is not None:
                return r
        return None

    return walk(app.query_one("#tree").root)


def _set_cursor_to(app: AdoptInnerApp, node) -> None:
    """Move the tree cursor to *node* (so cursor-based actions resolve to it)."""
    tree = app.query_one("#tree")
    i = 0
    while True:
        candidate = tree.get_node_at_line(i)
        if candidate is None:
            raise AssertionError(
                f"Node not found in visible tree: {getattr(node, 'data', None)}"
            )
        if candidate is node:
            tree.cursor_line = i
            return
        i += 1


# ─────────────────────────────────────────────────────────────
# Tree shape: pending leaves at root level, no parent folder
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pending_leaves_render_flat_at_root(tmp_path):
    pending = [_entry("contexts/foo.md"), _entry("skills/bar/", "skill")]
    app = AdoptInnerApp([], pending, [], warehouse_path=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        root = app.query_one("#tree").root

        # Pending leaves are direct children of root (no parent folder).
        pending_paths = {
            child.data["path"]
            for child in root.children
            if child.data and child.data.get("pending")
        }
        assert pending_paths == {"contexts/foo.md", "skills/bar/"}


@pytest.mark.asyncio
async def test_no_pending_section_when_empty(tmp_path):
    """With zero pending entries the header and separator are not rendered."""
    cands = [AdoptCandidate(artifact_type="contexts", path="contexts/x.md")]
    app = AdoptInnerApp(cands, [], [], warehouse_path=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        root = app.query_one("#tree").root
        # No header or separator leaves; only the contexts folder.
        for child in root.children:
            assert not (child.data and child.data.get("pending"))
            assert not (child.data and child.data.get("header"))


@pytest.mark.asyncio
async def test_header_and_separator_are_non_interactive(tmp_path):
    pending = [_entry("contexts/foo.md")]
    app = AdoptInnerApp([], pending, [], warehouse_path=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        root = app.query_one("#tree").root
        headers = [c for c in root.children if c.data and c.data.get("header")]
        # One leading header + one trailing separator.
        assert len(headers) == 2
        for h in headers:
            assert "selected" not in h.data
            assert "pending" not in h.data


# ─────────────────────────────────────────────────────────────
# y / n action handlers
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pending_accept_marks_accept(tmp_path):
    pending = [_entry("contexts/foo.md")]
    app = AdoptInnerApp([], pending, [], warehouse_path=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        node = _node_for_path(app, "contexts/foo.md")
        _set_cursor_to(app, node)
        await pilot.pause()
        app.action_pending_accept()
        assert app._pending_actions["contexts/foo.md"] == "accept"


@pytest.mark.asyncio
async def test_pending_accept_toggles_back_to_defer(tmp_path):
    pending = [_entry("contexts/foo.md")]
    app = AdoptInnerApp([], pending, [], warehouse_path=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        node = _node_for_path(app, "contexts/foo.md")
        _set_cursor_to(app, node)
        await pilot.pause()
        app.action_pending_accept()
        app.action_pending_accept()
        assert "contexts/foo.md" not in app._pending_actions


@pytest.mark.asyncio
async def test_pending_reject_marks_reject(tmp_path):
    pending = [_entry("contexts/foo.md")]
    app = AdoptInnerApp([], pending, [], warehouse_path=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        node = _node_for_path(app, "contexts/foo.md")
        _set_cursor_to(app, node)
        await pilot.pause()
        app.action_pending_reject()
        assert app._pending_actions["contexts/foo.md"] == "reject"


@pytest.mark.asyncio
async def test_pending_reject_toggles_back_to_defer(tmp_path):
    pending = [_entry("contexts/foo.md")]
    app = AdoptInnerApp([], pending, [], warehouse_path=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        node = _node_for_path(app, "contexts/foo.md")
        _set_cursor_to(app, node)
        await pilot.pause()
        app.action_pending_reject()
        app.action_pending_reject()
        assert "contexts/foo.md" not in app._pending_actions


@pytest.mark.asyncio
async def test_y_on_pending_does_not_affect_other_entries(tmp_path):
    pending = [_entry("contexts/a.md"), _entry("contexts/b.md")]
    app = AdoptInnerApp([], pending, [], warehouse_path=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        node_a = _node_for_path(app, "contexts/a.md")
        _set_cursor_to(app, node_a)
        await pilot.pause()
        app.action_pending_accept()
        assert app._pending_actions == {"contexts/a.md": "accept"}


@pytest.mark.asyncio
async def test_y_and_n_are_noop_on_warehouse_leaves(tmp_path):
    """Pressing y on a warehouse leaf must not write to _pending_actions."""
    cands = [AdoptCandidate(artifact_type="contexts", path="contexts/wh.md")]
    app = AdoptInnerApp(cands, [], [], warehouse_path=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        node = _node_for_path(app, "contexts/wh.md")
        _set_cursor_to(app, node)
        await pilot.pause()
        app.action_pending_accept()
        app.action_pending_reject()
        assert app._pending_actions == {}


# ─────────────────────────────────────────────────────────────
# space cycles accept ↔ defer on a pending leaf
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_space_on_pending_cycles_accept_defer(tmp_path):
    pending = [_entry("contexts/foo.md")]
    app = AdoptInnerApp([], pending, [], warehouse_path=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        node = _node_for_path(app, "contexts/foo.md")
        _set_cursor_to(app, node)
        await pilot.pause()

        app.action_toggle_selection()
        assert app._pending_actions == {"contexts/foo.md": "accept"}

        app.action_toggle_selection()
        assert "contexts/foo.md" not in app._pending_actions


# ─────────────────────────────────────────────────────────────
# _finalize / AdoptResult shape
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_finalize_returns_pending_accept_and_reject(tmp_path):
    pending = [
        _entry("contexts/keep.md"),
        _entry("contexts/drop.md"),
        _entry("contexts/defer.md"),
    ]
    app = AdoptInnerApp([], pending, [], warehouse_path=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        app._pending_actions["contexts/keep.md"] = "accept"
        app._pending_actions["contexts/drop.md"] = "reject"
        app._finalize()

        result = app.return_value
        assert isinstance(result, AdoptResult)
        assert result.pending_accept == ["contexts/keep.md"]
        assert result.pending_reject == ["contexts/drop.md"]
        # Defaulted (deferred) entries don't show up in either list.
        assert "contexts/defer.md" not in result.pending_accept
        assert "contexts/defer.md" not in result.pending_reject


@pytest.mark.asyncio
async def test_finalize_warehouse_ticks_independent_of_pending(tmp_path):
    """Mixed session: warehouse adopt + pending accept land in distinct fields."""
    pending = [_entry("contexts/from-pending.md")]
    cands = [AdoptCandidate(artifact_type="contexts", path="contexts/from-wh.md")]
    app = AdoptInnerApp(cands, pending, [], warehouse_path=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Pending: accept
        app._pending_actions["contexts/from-pending.md"] = "accept"
        # Warehouse: tick
        wh_node = _node_for_path(app, "contexts/from-wh.md")
        wh_node.data["selected"] = True

        app._finalize()
        result = app.return_value

        assert result.to_adopt == ["contexts/from-wh.md"]
        assert result.pending_accept == ["contexts/from-pending.md"]
        assert result.to_unadopt == []
        assert result.pending_reject == []


# ─────────────────────────────────────────────────────────────
# Show-all toggle preserves pending_actions across rebuild
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_toggle_view_preserves_pending_actions(tmp_path):
    pending = [_entry("contexts/foo.md")]
    app = AdoptInnerApp([], pending, [], warehouse_path=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        app._pending_actions["contexts/foo.md"] = "accept"
        # Rebuild via show-all toggle.
        app.action_toggle_view()
        await pilot.pause()
        # Action survives the rebuild.
        assert app._pending_actions["contexts/foo.md"] == "accept"
        # Leaf still rendered with the marked action in its data.
        node = _node_for_path(app, "contexts/foo.md")
        assert node.data.get("pending_action") == "accept"


# ─────────────────────────────────────────────────────────────
# Excluded paths: pending entries should not also appear in warehouse browser
# (covered by CLI wiring; this test verifies the AdoptInnerApp correctly handles
# the case where the same path appears only in pending_entries.)
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pending_only_path_does_not_render_as_warehouse_leaf(tmp_path):
    """A path in pending_entries doesn't accidentally land in the warehouse tree."""
    pending = [_entry("contexts/foo.md")]
    app = AdoptInnerApp([], pending, [], warehouse_path=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        # The only node with path="contexts/foo.md" must be the pending leaf.
        node = _node_for_path(app, "contexts/foo.md")
        assert node.data.get("pending") is True
        assert "selected" not in node.data
