"""Headless state-machine tests for agent ↔ skill propagation in the TUI.

Covers task 5.8:
- TC1: tick agent → skills auto-tick with provenance
- TC2: untick skill while agent ticked → blocked (hard-lock)
- TC3a: untick agent → skill auto-unticks when not user-explicit
- TC3b: user-explicit tick survives agent untick
- TC4: multi-agent shared skill provenance
"""

import pytest
import yaml
from beacon.domains.adoption.models import AdoptCandidate
from beacon.domains.adoption.tui import AdoptInnerApp


def _make_warehouse(tmp_path, agents_yaml: dict, skill_names: list[str]):
    wh = tmp_path / "wh"
    wh.mkdir()
    (wh / "agents").mkdir()
    (wh / "agents" / "agents.yaml").write_text(yaml.safe_dump(agents_yaml))
    skills = wh / "skills"
    skills.mkdir()
    for s in skill_names:
        (skills / s).mkdir()
        (skills / s / "SKILL.md").write_text(f"---\nname: {s}\n---\n# {s}\n")
    return wh


def _candidates_for(agent_names: list[str], skill_names: list[str]):
    cands = []
    for a in agent_names:
        cands.append(AdoptCandidate(artifact_type="agents", path=f"agents/{a}.md"))
    for s in skill_names:
        cands.append(AdoptCandidate(artifact_type="skills", path=f"skills/{s}/"))
    return cands


def _node_for_path(app, path: str):
    """Walk the tree to find the node whose data['path'] == path."""

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


@pytest.mark.asyncio
async def test_tc1_tick_agent_auto_ticks_skills_with_provenance(tmp_path):
    wh = _make_warehouse(
        tmp_path, {"planner": {"skills": ["alpha", "beta"]}}, ["alpha", "beta"]
    )
    cands = _candidates_for(["planner"], ["alpha", "beta"])
    app = AdoptInnerApp(cands, [], [], warehouse_path=wh, show_all_default=False)
    async with app.run_test() as pilot:
        await pilot.pause()
        node = _node_for_path(app, "agents/planner.md")
        app._toggle_warehouse_node(node)
        await pilot.pause()
        assert app._required_by.get("skills/alpha/") == ["agents/planner.md"]
        assert app._required_by.get("skills/beta/") == ["agents/planner.md"]
        for skill_path in ("skills/alpha/", "skills/beta/"):
            sn = _node_for_path(app, skill_path)
            assert sn.data["selected"] is True


@pytest.mark.asyncio
async def test_tc2_hard_lock_untick_skill_blocked(tmp_path):
    wh = _make_warehouse(tmp_path, {"planner": {"skills": ["alpha"]}}, ["alpha"])
    cands = _candidates_for(["planner"], ["alpha"])
    app = AdoptInnerApp(cands, [], [], warehouse_path=wh, show_all_default=False)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Tick agent
        agent_node = _node_for_path(app, "agents/planner.md")
        app._toggle_warehouse_node(agent_node)
        await pilot.pause()

        # Skill should be ticked
        skill_node = _node_for_path(app, "skills/alpha/")
        assert skill_node.data["selected"] is True

        # Try to untick skill
        app._toggle_warehouse_node(skill_node)
        await pilot.pause()

        # Skill should still be ticked
        assert skill_node.data["selected"] is True
        # Status message should contain required info
        assert "Required by:" in app._status_message
        assert "agents/planner.md" in app._status_message


@pytest.mark.asyncio
async def test_tc3a_auto_untick_when_not_explicit(tmp_path):
    wh = _make_warehouse(tmp_path, {"planner": {"skills": ["alpha"]}}, ["alpha"])
    cands = _candidates_for(["planner"], ["alpha"])
    app = AdoptInnerApp(cands, [], [], warehouse_path=wh, show_all_default=False)
    async with app.run_test() as pilot:
        await pilot.pause()
        # Tick agent
        agent_node = _node_for_path(app, "agents/planner.md")
        app._toggle_warehouse_node(agent_node)
        await pilot.pause()

        # Skill auto-ticked
        skill_node = _node_for_path(app, "skills/alpha/")
        assert skill_node.data["selected"] is True
        assert app._user_explicit.get("skills/alpha/") is not True

        # Untick agent
        app._toggle_warehouse_node(agent_node)
        await pilot.pause()

        # Skill should auto-untick
        assert skill_node.data["selected"] is False
        assert app._required_by.get("skills/alpha/", []) == []


@pytest.mark.asyncio
async def test_tc3b_user_explicit_survives_agent_untick(tmp_path):
    wh = _make_warehouse(tmp_path, {"planner": {"skills": ["alpha"]}}, ["alpha"])
    cands = _candidates_for(["planner"], ["alpha"])
    app = AdoptInnerApp(cands, [], [], warehouse_path=wh, show_all_default=False)
    async with app.run_test() as pilot:
        await pilot.pause()
        # User explicitly ticks skill first
        skill_node = _node_for_path(app, "skills/alpha/")
        app._toggle_warehouse_node(skill_node)
        await pilot.pause()
        assert app._user_explicit.get("skills/alpha/") is True

        # Tick agent
        agent_node = _node_for_path(app, "agents/planner.md")
        app._toggle_warehouse_node(agent_node)
        await pilot.pause()

        # Skill stays ticked, gains provenance
        assert skill_node.data["selected"] is True
        assert app._required_by.get("skills/alpha/") == ["agents/planner.md"]

        # Untick agent
        app._toggle_warehouse_node(agent_node)
        await pilot.pause()

        # Skill should remain ticked because user_explicit is True
        assert skill_node.data["selected"] is True
        assert app._required_by.get("skills/alpha/", []) == []


@pytest.mark.asyncio
async def test_tc4_multi_agent_shared_skill_provenance(tmp_path):
    wh = _make_warehouse(
        tmp_path,
        {"planner": {"skills": ["shared"]}, "reviewer": {"skills": ["shared"]}},
        ["shared"],
    )
    cands = _candidates_for(["planner", "reviewer"], ["shared"])
    app = AdoptInnerApp(cands, [], [], warehouse_path=wh, show_all_default=False)
    async with app.run_test() as pilot:
        await pilot.pause()
        planner_node = _node_for_path(app, "agents/planner.md")
        reviewer_node = _node_for_path(app, "agents/reviewer.md")
        skill_node = _node_for_path(app, "skills/shared/")

        # Tick planner
        app._toggle_warehouse_node(planner_node)
        await pilot.pause()
        assert skill_node.data["selected"] is True
        assert app._required_by.get("skills/shared/") == ["agents/planner.md"]

        # Tick reviewer
        app._toggle_warehouse_node(reviewer_node)
        await pilot.pause()
        assert skill_node.data["selected"] is True
        assert app._required_by.get("skills/shared/") == [
            "agents/planner.md",
            "agents/reviewer.md",
        ]

        # Untick planner
        app._toggle_warehouse_node(planner_node)
        await pilot.pause()
        assert skill_node.data["selected"] is True
        assert app._required_by.get("skills/shared/") == ["agents/reviewer.md"]

        # Untick reviewer
        app._toggle_warehouse_node(reviewer_node)
        await pilot.pause()
        assert app._required_by.get("skills/shared/", []) == []
        assert skill_node.data["selected"] is False
