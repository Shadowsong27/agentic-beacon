"""Tests for install_agent_global() helper (Phase 6, task 6.3).

TDD Test Cases (6.1):
- TC1: Target file does not exist → writes file, returns True
- TC2: Target file exists with identical content → skips, returns False
- TC3: Target file exists with different content → overwrites (caller already confirmed), returns True
- TC4: Parent dir does not exist → auto-creates, writes file, returns True
- TC5: agent="opencode" → resolves to ~/.config/opencode/agents/<name>.md
- TC6: agent="claudecode" → resolves to ~/.claude/agents/<name>.md
"""

from pathlib import Path

import pytest
from beacon.domains.artifact.agent import install_agent_global

AGENT_CONTENT = """\
---
name: code-reviewer
description: Reviews code changes
---
# Code Reviewer Agent
"""


def _opencode_agents(fake_home: Path) -> Path:
    return fake_home / ".config" / "opencode" / "agents"


def _claudecode_agents(fake_home: Path) -> Path:
    return fake_home / ".claude" / "agents"


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    return home


def test_tc1_target_not_exist_writes_and_returns_true(fake_home):
    """TC1: Target file does not exist → writes file, returns True."""
    result = install_agent_global("opencode", "code-reviewer.md", AGENT_CONTENT)

    assert result is True
    dest = _opencode_agents(fake_home) / "code-reviewer.md"
    assert dest.exists()
    assert dest.read_text() == AGENT_CONTENT


def test_tc2_identical_content_skips_returns_false(fake_home):
    """TC2: Target file exists with identical content → skips, returns False."""
    dest = _opencode_agents(fake_home) / "code-reviewer.md"
    dest.parent.mkdir(parents=True)
    dest.write_text(AGENT_CONTENT)

    result = install_agent_global("opencode", "code-reviewer.md", AGENT_CONTENT)

    assert result is False
    # Content unchanged
    assert dest.read_text() == AGENT_CONTENT


def test_tc3_different_content_overwrites_returns_true(fake_home):
    """TC3: Target file exists with different content → overwrites, returns True."""
    dest = _opencode_agents(fake_home) / "code-reviewer.md"
    dest.parent.mkdir(parents=True)
    dest.write_text("# Old content\n")

    result = install_agent_global("opencode", "code-reviewer.md", AGENT_CONTENT)

    assert result is True
    assert dest.read_text() == AGENT_CONTENT


def test_tc4_parent_dir_not_exist_auto_creates(fake_home):
    """TC4: Parent dir does not exist → auto-creates, writes file, returns True."""
    # opencode dir doesn't exist at all
    result = install_agent_global("claudecode", "my-agent.md", AGENT_CONTENT)

    assert result is True
    dest = _claudecode_agents(fake_home) / "my-agent.md"
    assert dest.exists()


def test_tc5_opencode_resolves_to_config_opencode(fake_home):
    """TC5: agent="opencode" → resolves to ~/.config/opencode/agents/<name>.md"""
    install_agent_global("opencode", "code-reviewer.md", AGENT_CONTENT)

    expected = fake_home / ".config" / "opencode" / "agents" / "code-reviewer.md"
    assert expected.exists()
    # Claude Code dir should NOT be created
    claude_dest = fake_home / ".claude" / "agents" / "code-reviewer.md"
    assert not claude_dest.exists()


def test_tc6_claudecode_resolves_to_claude_agents(fake_home):
    """TC6: agent="claudecode" → resolves to ~/.claude/agents/<name>.md"""
    install_agent_global("claudecode", "code-reviewer.md", AGENT_CONTENT)

    expected = fake_home / ".claude" / "agents" / "code-reviewer.md"
    assert expected.exists()
    # OpenCode dir should NOT be created
    opencode_dest = fake_home / ".config" / "opencode" / "agents" / "code-reviewer.md"
    assert not opencode_dest.exists()
