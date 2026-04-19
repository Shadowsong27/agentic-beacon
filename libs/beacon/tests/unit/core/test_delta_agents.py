"""Tests for Phase 7: DeltaStatus.STALE, _agent_live_path, _compare_agent_file.

TDD Test Cases for DeltaStatus.STALE (7.1):
- TC1: DeltaStatus.STALE is a valid enum member
- TC2: Priority map in _compare_skill_file() does not reference STALE

TDD Test Cases for _agent_live_path (7.2):
- TC1: agent="opencode", "agents/code-reviewer.md" → ~/.config/opencode/agents/code-reviewer.md
- TC2: agent="claudecode", "agents/code-reviewer.md" → ~/.claude/agents/code-reviewer.md
- TC3: Nested path "agents/sub/name.md" → strips only "agents/" prefix

TDD Test Cases for _compare_agent_file (7.4):
- TC1: Global file absent → MISSING
- TC2: Global file identical to warehouse → IDENTICAL
- TC3: Global file differs from warehouse → MODIFIED
- TC4: No tools detected (agents_paths empty) → empty result, no error
- TC5: Warehouse agents/ dir is empty → no agent rows iterated, no error
"""

import inspect
from pathlib import Path

import pytest
from beacon.domains.distribution.delta import DeltaComparator, DeltaStatus


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    return home


def _make_comparator(tmp_path: Path) -> tuple[DeltaComparator, Path, Path]:
    warehouse = tmp_path / "warehouse"
    artifacts = tmp_path / "artifacts"
    warehouse.mkdir()
    artifacts.mkdir()
    (warehouse / "agents").mkdir()
    comp = DeltaComparator(
        warehouse_path=warehouse,
        artifacts_path=artifacts,
    )
    return comp, warehouse, artifacts


# ---------------------------------------------------------------------------
# 7.1 DeltaStatus.STALE
# ---------------------------------------------------------------------------


def test_delta_status_stale_is_valid_enum_member():
    """TC1: DeltaStatus.STALE is a valid enum member."""
    assert hasattr(DeltaStatus, "STALE")
    assert DeltaStatus.STALE.value == "stale"


def test_compare_skill_file_priority_map_excludes_stale(tmp_path):
    """TC2: Priority map in _compare_skill_file() does not reference STALE."""
    comp, warehouse, artifacts = _make_comparator(tmp_path)
    # Inspect source code of _compare_skill_file for the priority dict
    source = inspect.getsource(comp._compare_skill_file)
    # The priority map should not include STALE
    assert "STALE" not in source.split("priority")[1].split("}")[0]


# ---------------------------------------------------------------------------
# 7.2 _agent_live_path
# ---------------------------------------------------------------------------


def test_agent_live_path_opencode(tmp_path, fake_home):
    """TC1: agent="opencode" → ~/.config/opencode/agents/code-reviewer.md"""
    comp, _, _ = _make_comparator(tmp_path)
    result = comp._agent_live_path("opencode", "agents/code-reviewer.md")
    expected = fake_home / ".config" / "opencode" / "agents" / "code-reviewer.md"
    assert result == expected


def test_agent_live_path_claudecode(tmp_path, fake_home):
    """TC2: agent="claudecode" → ~/.claude/agents/code-reviewer.md"""
    comp, _, _ = _make_comparator(tmp_path)
    result = comp._agent_live_path("claudecode", "agents/code-reviewer.md")
    expected = fake_home / ".claude" / "agents" / "code-reviewer.md"
    assert result == expected


def test_agent_live_path_strips_agents_prefix_only(tmp_path, fake_home):
    """TC3: Nested path "agents/sub/name.md" → strips only agents/ prefix."""
    comp, _, _ = _make_comparator(tmp_path)
    result = comp._agent_live_path("opencode", "agents/sub/name.md")
    expected = fake_home / ".config" / "opencode" / "agents" / "sub" / "name.md"
    assert result == expected


# ---------------------------------------------------------------------------
# 7.4 _compare_agent_file
# ---------------------------------------------------------------------------


AGENT_CONTENT = "---\nname: code-reviewer\n---\n# Agent\n"
AGENT_CONTENT_MODIFIED = "---\nname: code-reviewer\n---\n# Agent (modified)\n"


def test_compare_agent_file_missing(tmp_path, fake_home):
    """TC1: Global file absent → MISSING."""
    comp, warehouse, _ = _make_comparator(tmp_path)
    (warehouse / "agents" / "code-reviewer.md").write_text(AGENT_CONTENT)

    # Set up agents_paths with a tool dir (no actual agent file there)
    opencode_dir = fake_home / ".config" / "opencode"
    opencode_dir.mkdir(parents=True)
    comp.agents_paths = {"opencode": opencode_dir / "agents"}

    result = comp._compare_agent_file("agents/code-reviewer.md")

    assert result.agent_statuses["opencode"] == DeltaStatus.MISSING


def test_compare_agent_file_identical(tmp_path, fake_home):
    """TC2: Global file identical to warehouse → IDENTICAL."""
    comp, warehouse, _ = _make_comparator(tmp_path)
    (warehouse / "agents" / "code-reviewer.md").write_text(AGENT_CONTENT)

    opencode_agents = fake_home / ".config" / "opencode" / "agents"
    opencode_agents.mkdir(parents=True)
    (opencode_agents / "code-reviewer.md").write_text(AGENT_CONTENT)
    comp.agents_paths = {"opencode": opencode_agents}

    result = comp._compare_agent_file("agents/code-reviewer.md")

    assert result.agent_statuses["opencode"] == DeltaStatus.IDENTICAL


def test_compare_agent_file_modified(tmp_path, fake_home):
    """TC3: Global file differs from warehouse → MODIFIED."""
    comp, warehouse, _ = _make_comparator(tmp_path)
    (warehouse / "agents" / "code-reviewer.md").write_text(AGENT_CONTENT)

    opencode_agents = fake_home / ".config" / "opencode" / "agents"
    opencode_agents.mkdir(parents=True)
    (opencode_agents / "code-reviewer.md").write_text(AGENT_CONTENT_MODIFIED)
    comp.agents_paths = {"opencode": opencode_agents}

    result = comp._compare_agent_file("agents/code-reviewer.md")

    assert result.agent_statuses["opencode"] == DeltaStatus.MODIFIED


def test_compare_agent_file_no_tools(tmp_path, fake_home):
    """TC4: No tools detected (agents_paths empty) → empty result, no error."""
    comp, warehouse, _ = _make_comparator(tmp_path)
    (warehouse / "agents" / "code-reviewer.md").write_text(AGENT_CONTENT)
    comp.agents_paths = {}

    result = comp._compare_agent_file("agents/code-reviewer.md")

    assert result.agent_statuses == {}
    assert result.path == "agents/code-reviewer.md"
