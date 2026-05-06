"""Tests for three-way TUI mark transitions and no-mutation guarantee.

Covers tasks 5.1–5.4:
- TC1-TC5: per-entry action state transitions (accept/reject/defer)
- 5.3 TC1-TC3: files unchanged during mark phase
- 5.4: snapshot tests for transitions and display
"""

from __future__ import annotations

import filecmp
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest

from beacon.core.manifest.pending import PendingEntry, PendingManifest
from beacon.domains.adoption.last_adopt import write_last_adopt
from beacon.domains.adoption.models import AdoptCandidate
from beacon.domains.adoption.tui import AdoptInnerApp


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────


def _make_candidates(n: int = 3) -> list[AdoptCandidate]:
    """Return n AdoptCandidate instances for testing."""
    candidates = []
    for i in range(n):
        candidates.append(
            AdoptCandidate(
                artifact_type="contexts",
                path=f"contexts/item-{i}.md",
                source="record-knowledge",
                action="created",
            )
        )
    return candidates


def _get_session_action(app: AdoptInnerApp, path: str) -> str:
    """Return the three-way action for the given path from app's session state."""
    return app._session_actions.get(path, "defer")


def _find_node(app: AdoptInnerApp, path: str):
    """Walk the TUI tree to find the node with data['path'] == path."""

    def walk(node):
        if node.data and node.data.get("path") == path:
            return node
        for child in node.children:
            r = walk(child)
            if r is not None:
                return r
        return None

    tree = app.query_one("#tree")
    return walk(tree.root)


# ─────────────────────────────────────────────────────────────
# Task 5.1: Three-way mark transitions
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tc1_press_accept_sets_accept(tmp_path):
    """TC1: Press accept on row → state[row]='accept'."""
    candidates = _make_candidates(1)
    app = AdoptInnerApp(candidates, [], warehouse_path=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        node = _find_node(app, "contexts/item-0.md")
        assert node is not None
        app._mark_action(node, "accept")
        await pilot.pause()
        assert _get_session_action(app, "contexts/item-0.md") == "accept"


@pytest.mark.asyncio
async def test_tc2_press_reject_sets_reject(tmp_path):
    """TC2: Press reject on row → state[row]='reject'."""
    candidates = _make_candidates(1)
    app = AdoptInnerApp(candidates, [], warehouse_path=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        node = _find_node(app, "contexts/item-0.md")
        app._mark_action(node, "reject")
        await pilot.pause()
        assert _get_session_action(app, "contexts/item-0.md") == "reject"


@pytest.mark.asyncio
async def test_tc3_press_defer_sets_defer(tmp_path):
    """TC3: Press defer on row → state[row]='defer'."""
    candidates = _make_candidates(1)
    app = AdoptInnerApp(candidates, [], warehouse_path=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        node = _find_node(app, "contexts/item-0.md")
        app._mark_action(node, "defer")
        await pilot.pause()
        assert _get_session_action(app, "contexts/item-0.md") == "defer"


@pytest.mark.asyncio
async def test_tc4_toggle_accept_reject_defer_same_row(tmp_path):
    """TC4: Toggle accept→reject→defer same row → final state correct, no leakage."""
    candidates = _make_candidates(2)
    app = AdoptInnerApp(candidates, [], warehouse_path=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()

        node0 = _find_node(app, "contexts/item-0.md")
        node1 = _find_node(app, "contexts/item-1.md")

        app._mark_action(node0, "accept")
        await pilot.pause()
        assert _get_session_action(app, "contexts/item-0.md") == "accept"

        app._mark_action(node0, "reject")
        await pilot.pause()
        assert _get_session_action(app, "contexts/item-0.md") == "reject"

        app._mark_action(node0, "defer")
        await pilot.pause()
        assert _get_session_action(app, "contexts/item-0.md") == "defer"

        # node1 must be unaffected
        assert _get_session_action(app, "contexts/item-1.md") == "defer"


@pytest.mark.asyncio
async def test_tc5_default_state_is_defer(tmp_path):
    """TC5: Default (no key) state → 'defer'."""
    candidates = _make_candidates(3)
    app = AdoptInnerApp(candidates, [], warehouse_path=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        for c in candidates:
            assert _get_session_action(app, c.path) == "defer"


# ─────────────────────────────────────────────────────────────
# Task 5.2: Visual source label in leaf labels
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_source_label_visible_in_leaf(tmp_path):
    """Source label appears in leaf label when candidate has source set."""
    candidates = [
        AdoptCandidate(
            artifact_type="contexts",
            path="contexts/foo.md",
            source="record-knowledge",
        )
    ]
    app = AdoptInnerApp(candidates, [], warehouse_path=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        node = _find_node(app, "contexts/foo.md")
        label_str = str(node._label)
        assert "record-knowledge" in label_str


# ─────────────────────────────────────────────────────────────
# Task 5.3: No filesystem mutation during mark phase
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tc1_mark_then_cancel_files_unchanged(tmp_path):
    """TC1: Mark 3 rows then cancel → 3 tracked files byte-identical."""
    project = tmp_path / "project"
    project.mkdir()
    ab = project / ".agentic-beacon"
    ab.mkdir()

    # Create the three files before the TUI session
    beacon_yaml = project / "beacon.yaml"
    beacon_yaml.write_text("artifacts:\n  contexts: []\n  skills: []\n")
    pending_yaml = ab / "pending.yaml"
    pending_yaml.write_text("pending: []\n")
    last_adopt = ab / ".last-adopt"
    write_last_adopt(project, datetime(2026, 5, 1, tzinfo=timezone.utc))

    # Snapshot pre-session
    def snapshot() -> tuple[bytes, bytes, bytes]:
        return (
            beacon_yaml.read_bytes(),
            pending_yaml.read_bytes(),
            last_adopt.read_bytes(),
        )

    pre = snapshot()

    candidates = _make_candidates(3)
    app = AdoptInnerApp(candidates, [], warehouse_path=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        for c in candidates:
            node = _find_node(app, c.path)
            app._mark_action(node, "accept")
        await pilot.pause()
        app.action_cancel()
        await pilot.pause()

    post = snapshot()
    assert pre == post


@pytest.mark.asyncio
async def test_tc2_mark_all_accept_cancel_files_unchanged(tmp_path):
    """TC2: Mark all rows accept then cancel → still byte-identical."""
    project = tmp_path / "project"
    project.mkdir()
    ab = project / ".agentic-beacon"
    ab.mkdir()

    beacon_yaml = project / "beacon.yaml"
    beacon_yaml.write_text("artifacts:\n  contexts: []\n  skills: []\n")
    pending_yaml = ab / "pending.yaml"
    pending_yaml.write_text("pending: []\n")
    write_last_adopt(project, datetime(2026, 5, 1, tzinfo=timezone.utc))
    last_adopt = ab / ".last-adopt"

    pre = (beacon_yaml.read_bytes(), pending_yaml.read_bytes(), last_adopt.read_bytes())

    candidates = _make_candidates(5)
    app = AdoptInnerApp(candidates, [], warehouse_path=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        for c in candidates:
            node = _find_node(app, c.path)
            app._mark_action(node, "accept")
        await pilot.pause()
        app.action_cancel()

    post = (beacon_yaml.read_bytes(), pending_yaml.read_bytes(), last_adopt.read_bytes())
    assert pre == post


@pytest.mark.asyncio
async def test_tc3_no_marks_cancel_files_unchanged(tmp_path):
    """TC3: No marks then cancel → still byte-identical (defensive baseline)."""
    project = tmp_path / "project"
    project.mkdir()
    ab = project / ".agentic-beacon"
    ab.mkdir()

    beacon_yaml = project / "beacon.yaml"
    beacon_yaml.write_text("artifacts:\n  contexts: []\n  skills: []\n")
    pending_yaml = ab / "pending.yaml"
    pending_yaml.write_text("pending: []\n")
    write_last_adopt(project, datetime(2026, 5, 1, tzinfo=timezone.utc))
    last_adopt = ab / ".last-adopt"

    pre = (beacon_yaml.read_bytes(), pending_yaml.read_bytes(), last_adopt.read_bytes())

    candidates = _make_candidates(2)
    app = AdoptInnerApp(candidates, [], warehouse_path=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.action_cancel()

    post = (beacon_yaml.read_bytes(), pending_yaml.read_bytes(), last_adopt.read_bytes())
    assert pre == post


# ─────────────────────────────────────────────────────────────
# Task 5.4: Result collection reflects three-way choices
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_confirm_collects_three_way_choices(tmp_path):
    """action_confirm returns AdoptResult with to_adopt / to_reject / to_defer."""
    candidates = _make_candidates(3)
    app = AdoptInnerApp(candidates, [], warehouse_path=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()

        node0 = _find_node(app, "contexts/item-0.md")
        node1 = _find_node(app, "contexts/item-1.md")
        node2 = _find_node(app, "contexts/item-2.md")

        app._mark_action(node0, "accept")
        app._mark_action(node1, "reject")
        # item-2 stays defer (default)

        await pilot.pause()

        # Trigger confirm to get the result
        app.action_confirm()

    result = app.return_value
    assert result is not None
    assert "contexts/item-0.md" in result.to_adopt
    assert "contexts/item-1.md" in result.to_reject
    assert "contexts/item-2.md" in result.to_defer


# ─────────────────────────────────────────────────────────────
# Task 6.1: Confirm screen shows N accepted / N rejected / N deferred
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_apply_shows_confirm_screen_with_counts(tmp_path):
    """6.1: action_apply pushes a confirm screen summarising the three-way counts."""
    candidates = _make_candidates(4)
    app = AdoptInnerApp(candidates, [], warehouse_path=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()

        node0 = _find_node(app, "contexts/item-0.md")
        node1 = _find_node(app, "contexts/item-1.md")
        node2 = _find_node(app, "contexts/item-2.md")
        # item-3 stays defer

        app._mark_action(node0, "accept")
        app._mark_action(node1, "accept")
        app._mark_action(node2, "reject")

        await pilot.pause()
        app.action_apply()
        await pilot.pause()

        # Confirm screen must be the active (top) screen with the right counts
        screen = app.screen
        assert hasattr(screen, "_n_accept"), "Expected _ConfirmScreen to be active"
        assert screen._n_accept == 2
        assert screen._n_reject == 1
        assert screen._n_defer == 1


# ─────────────────────────────────────────────────────────────
# Task 6.4: Cancel from confirm screen leaves files unchanged
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cancel_from_confirm_screen_files_unchanged(tmp_path):
    """6.4: Mark rows, show confirm screen, cancel → three tracked files byte-identical."""
    project = tmp_path / "project"
    project.mkdir()
    ab = project / ".agentic-beacon"
    ab.mkdir()

    beacon_yaml = project / "beacon.yaml"
    beacon_yaml.write_text("artifacts:\n  contexts: []\n  skills: []\n")
    pending_yaml = ab / "pending.yaml"
    pending_yaml.write_text("pending: []\n")
    write_last_adopt(project, datetime(2026, 5, 1, tzinfo=timezone.utc))
    last_adopt = ab / ".last-adopt"

    pre = (beacon_yaml.read_bytes(), pending_yaml.read_bytes(), last_adopt.read_bytes())

    candidates = _make_candidates(3)
    app = AdoptInnerApp(candidates, [], warehouse_path=tmp_path)
    async with app.run_test() as pilot:
        await pilot.pause()
        for c in candidates:
            node = _find_node(app, c.path)
            app._mark_action(node, "accept")
        await pilot.pause()

        # Open confirm screen
        app.action_apply()
        await pilot.pause()

        # Cancel from confirm screen
        await pilot.press("escape")
        await pilot.pause()

        # Cancel the main app too (so we exit cleanly)
        app.action_cancel()
        await pilot.pause()

    post = (beacon_yaml.read_bytes(), pending_yaml.read_bytes(), last_adopt.read_bytes())
    assert pre == post
