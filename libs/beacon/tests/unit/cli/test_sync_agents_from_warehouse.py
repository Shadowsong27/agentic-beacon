"""Tests for sync_agents_from_warehouse() — covers PER-112 fresh-machine fallback."""

from pathlib import Path

import pytest
from beacon.domains.artifact.agent import sync_agents_from_warehouse

AGENT_CONTENT = """\
---
name: code-reviewer
description: Reviews code changes
---
# Code Reviewer Agent
"""


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    return home


@pytest.fixture
def warehouse_with_agent(tmp_path):
    wh = tmp_path / "warehouse"
    (wh / "agents").mkdir(parents=True)
    (wh / "agents" / "code-reviewer.md").write_text(AGENT_CONTENT)
    return wh


def test_fresh_machine_creates_both_global_dirs(
    fake_home, warehouse_with_agent, capsys
):
    """PER-112: when neither ~/.claude nor ~/.config/opencode exists, sync still
    installs to both canonical paths instead of silently no-op'ing."""
    assert not (fake_home / ".claude").exists()
    assert not (fake_home / ".config" / "opencode").exists()

    sync_agents_from_warehouse(warehouse_with_agent, force=True)

    claude_dest = fake_home / ".claude" / "agents" / "code-reviewer.md"
    opencode_dest = fake_home / ".config" / "opencode" / "agents" / "code-reviewer.md"
    assert claude_dest.is_symlink()
    assert claude_dest.resolve() == (
        warehouse_with_agent / "agents" / "code-reviewer.md"
    ).resolve()
    assert opencode_dest.is_symlink()
    assert opencode_dest.resolve() == (
        warehouse_with_agent / "agents" / "code-reviewer.md"
    ).resolve()


def test_fresh_machine_prints_warning(fake_home, warehouse_with_agent, capsys):
    """User must see why both dirs were created — silent fallback is a regression."""
    sync_agents_from_warehouse(warehouse_with_agent, force=True)

    out = capsys.readouterr().out
    assert "No agent tools detected" in out


def test_only_claude_dir_present_installs_only_to_claude(
    fake_home, warehouse_with_agent
):
    """When ~/.claude exists but ~/.config/opencode does not, install only to claudecode."""
    (fake_home / ".claude").mkdir()

    sync_agents_from_warehouse(warehouse_with_agent, force=True)

    claude_dest = fake_home / ".claude" / "agents" / "code-reviewer.md"
    opencode_dest = fake_home / ".config" / "opencode" / "agents" / "code-reviewer.md"
    assert claude_dest.is_symlink()
    assert not opencode_dest.exists()


def test_only_opencode_dir_present_installs_only_to_opencode(
    fake_home, warehouse_with_agent
):
    """When ~/.config/opencode exists but ~/.claude does not, install only to opencode."""
    (fake_home / ".config" / "opencode").mkdir(parents=True)

    sync_agents_from_warehouse(warehouse_with_agent, force=True)

    claude_dest = fake_home / ".claude" / "agents" / "code-reviewer.md"
    opencode_dest = fake_home / ".config" / "opencode" / "agents" / "code-reviewer.md"
    assert opencode_dest.is_symlink()
    assert not claude_dest.exists()


def test_warehouse_without_agents_dir_returns_silently(fake_home, tmp_path, capsys):
    """No warehouse agents/ dir → no-op, no fallback warning."""
    wh = tmp_path / "empty-warehouse"
    wh.mkdir()

    sync_agents_from_warehouse(wh, force=True)

    out = capsys.readouterr().out
    assert "No agent tools detected" not in out


def test_warehouse_with_empty_agents_dir_returns_silently(
    fake_home, tmp_path, capsys
):
    """agents/ dir present but no *.md files → no-op, no fallback warning."""
    wh = tmp_path / "warehouse"
    (wh / "agents").mkdir(parents=True)

    sync_agents_from_warehouse(wh, force=True)

    out = capsys.readouterr().out
    assert "No agent tools detected" not in out
