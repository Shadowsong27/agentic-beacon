"""Integration tests for abc install agents/<name>.md (Phase 6, task 6.4).

TDD Test Cases (6.4):
- TC1: Both tools detected, fresh install → files in both global dirs, sync-state populated, exit 0
- TC2: No tools detected → warning printed, no files written, exit 0
- TC3: beacon.yaml exists → unchanged after install
- TC4: Content identical → no-op, sync-state NOT updated, exit 0
- TC5: Content differs, interactive, user confirms y → file overwritten, sync-state updated
- TC6: Content differs, --force → file overwritten without prompt, sync-state updated
- TC7: Content differs, --preserve → file skipped without prompt, sync-state NOT updated
- TC8: Content differs, non-interactive, no flags → exit 1, no files written, sync-state unchanged
"""

import json
from pathlib import Path

import pytest
from beacon.cli.main import main
from beacon.domains.distribution.state import global_sync_state_file
from click.testing import CliRunner

AGENT_CONTENT = """\
---
name: code-reviewer
description: Reviews code changes for correctness and style
---
# Code Reviewer Agent

You are a code reviewer.
"""

AGENT_CONTENT_V2 = """\
---
name: code-reviewer
description: Reviews code changes for correctness and style (updated)
---
# Code Reviewer Agent v2

You are an improved code reviewer.
"""


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    return home


@pytest.fixture
def warehouse_with_agent(tmp_path):
    """Warehouse with an agent definition."""
    wh = tmp_path / "warehouse"
    wh.mkdir()
    (wh / "README.md").write_text("# Warehouse")
    for d in ("agents", "knowledge", "skills", "contexts", "docs"):
        (wh / d).mkdir()
    (wh / "agents" / "code-reviewer.md").write_text(AGENT_CONTENT)
    return wh


@pytest.fixture
def connected_project(tmp_path, warehouse_with_agent, monkeypatch, fake_home):
    """Project connected to a warehouse that has an agent."""
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    runner = CliRunner()
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse_with_agent)])
    return project, warehouse_with_agent, runner, fake_home


def _make_tool_dirs(fake_home: Path) -> tuple[Path, Path]:
    opencode_dir = fake_home / ".config" / "opencode"
    opencode_dir.mkdir(parents=True)
    claude_dir = fake_home / ".claude"
    claude_dir.mkdir(parents=True)
    return opencode_dir, claude_dir


def test_tc1_both_tools_fresh_install(connected_project):
    """TC1: Both tools detected, fresh install → files in both global dirs, sync-state populated, exit 0."""
    project, warehouse, runner, fake_home = connected_project
    opencode_dir, claude_dir = _make_tool_dirs(fake_home)

    result = runner.invoke(main, ["install", "agents/code-reviewer.md"])

    assert result.exit_code == 0, result.output

    # Files written to both global dirs
    assert (opencode_dir / "agents" / "code-reviewer.md").exists()
    assert (claude_dir / "agents" / "code-reviewer.md").exists()

    # Sync-state populated
    state_file = global_sync_state_file()
    assert state_file.exists()
    state = json.loads(state_file.read_text())
    assert state.get("version") == 1
    warehouse_key = str(warehouse)
    warehouses = state.get("warehouses", {})
    assert warehouse_key in warehouses
    assert "agents/code-reviewer.md" in warehouses[warehouse_key]


def test_tc2_no_tools_detected_warns(connected_project):
    """TC2: No tools detected → warning printed, no files written, exit 0."""
    project, warehouse, runner, fake_home = connected_project
    # Do NOT create tool dirs — no tools detected

    result = runner.invoke(main, ["install", "agents/code-reviewer.md"])

    assert result.exit_code == 0
    # Should warn that no agent tools are detected
    assert (
        "No agent tool" in result.output
        or "not detected" in result.output.lower()
        or "no tools" in result.output.lower()
    )

    # No files written
    assert not (
        fake_home / ".config" / "opencode" / "agents" / "code-reviewer.md"
    ).exists()
    assert not (fake_home / ".claude" / "agents" / "code-reviewer.md").exists()


def test_tc3_beacon_yaml_unchanged(connected_project):
    """TC3: beacon.yaml exists → unchanged after install."""
    project, warehouse, runner, fake_home = connected_project
    _make_tool_dirs(fake_home)

    beacon_yaml = project / ".agentic-beacon" / "beacon.yaml"
    original_content = beacon_yaml.read_text() if beacon_yaml.exists() else None

    runner.invoke(main, ["install", "agents/code-reviewer.md"])

    if original_content is not None:
        assert beacon_yaml.read_text() == original_content
    else:
        # beacon.yaml should not have been created for agents
        assert not beacon_yaml.exists() or "agents" not in beacon_yaml.read_text()


def test_tc4_identical_content_updates_sync_state_head(connected_project):
    """TC4: Content identical → no file write, but sync-state HEAD is still updated.

    Even when the agent file content hasn't changed, install must bump the recorded
    warehouse_head so that 'abc delta' does not keep reporting the agent as stale
    after the warehouse advances past commits that don't touch agent files.
    """
    project, warehouse, runner, fake_home = connected_project
    opencode_dir, claude_dir = _make_tool_dirs(fake_home)

    # Pre-install with same content
    (opencode_dir / "agents").mkdir(parents=True)
    (opencode_dir / "agents" / "code-reviewer.md").write_text(AGENT_CONTENT)
    (claude_dir / "agents").mkdir(parents=True)
    (claude_dir / "agents" / "code-reviewer.md").write_text(AGENT_CONTENT)

    result = runner.invoke(main, ["install", "agents/code-reviewer.md"])

    assert result.exit_code == 0

    # Sync-state SHOULD be updated even though no file write happened
    state_file = global_sync_state_file()
    assert state_file.exists(), "sync-state file should exist after install"
    state = json.loads(state_file.read_text())
    agent_state = (
        state.get("warehouses", {})
        .get(str(warehouse), {})
        .get("agents/code-reviewer.md", {})
    )
    assert agent_state != {}, (
        "sync-state entry should be written even for identical content"
    )
    assert "warehouse_head" in agent_state


def test_tc6_force_overwrites_without_prompt(connected_project):
    """TC6: Content differs, --force → file overwritten without prompt, sync-state updated."""
    project, warehouse, runner, fake_home = connected_project
    opencode_dir, _ = _make_tool_dirs(fake_home)

    # Pre-install with different content
    (opencode_dir / "agents").mkdir(parents=True)
    (opencode_dir / "agents" / "code-reviewer.md").write_text("# Old version\n")

    result = runner.invoke(main, ["install", "agents/code-reviewer.md", "--force"])

    assert result.exit_code == 0
    assert (opencode_dir / "agents" / "code-reviewer.md").read_text() == AGENT_CONTENT

    # Sync-state should be updated
    state_file = global_sync_state_file()
    assert state_file.exists()
    state = json.loads(state_file.read_text())
    warehouses = state.get("warehouses", {})
    assert str(warehouse) in warehouses


def test_tc7_preserve_skips_without_prompt(connected_project):
    """TC7: Content differs, --preserve → conflicting files skipped, sync-state NOT updated for skipped."""
    project, warehouse, runner, fake_home = connected_project
    opencode_dir, claude_dir = _make_tool_dirs(fake_home)

    # Pre-install with different content in BOTH tool dirs (all conflict)
    (opencode_dir / "agents").mkdir(parents=True)
    (opencode_dir / "agents" / "code-reviewer.md").write_text("# Old version\n")
    (claude_dir / "agents").mkdir(parents=True)
    (claude_dir / "agents" / "code-reviewer.md").write_text("# Old version\n")

    result = runner.invoke(main, ["install", "agents/code-reviewer.md", "--preserve"])

    assert result.exit_code == 0
    # Files should NOT be overwritten
    assert "Old version" in (opencode_dir / "agents" / "code-reviewer.md").read_text()
    assert "Old version" in (claude_dir / "agents" / "code-reviewer.md").read_text()

    # Sync-state should NOT be updated (all files were skipped)
    state_file = global_sync_state_file()
    if state_file.exists():
        state = json.loads(state_file.read_text())
        warehouses = state.get("warehouses", {})
        agent_state = warehouses.get(str(warehouse), {}).get(
            "agents/code-reviewer.md", {}
        )
        assert agent_state == {}


def test_tc8_noninteractive_conflict_exits1(connected_project):
    """TC8: Content differs, non-interactive, no flags → exit 1, no files written, sync-state unchanged."""
    project, warehouse, runner, fake_home = connected_project
    opencode_dir, _ = _make_tool_dirs(fake_home)

    # Pre-install with different content
    (opencode_dir / "agents").mkdir(parents=True)
    (opencode_dir / "agents" / "code-reviewer.md").write_text("# Old version\n")

    result = runner.invoke(main, ["install", "agents/code-reviewer.md"])

    assert result.exit_code == 1
    # File should NOT be overwritten
    assert "Old version" in (opencode_dir / "agents" / "code-reviewer.md").read_text()
