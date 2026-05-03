"""Tests for install_agent_global() helper."""

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


@pytest.fixture
def source_agent(tmp_path):
    source = tmp_path / "warehouse" / "agents" / "code-reviewer.md"
    source.parent.mkdir(parents=True)
    source.write_text(AGENT_CONTENT)
    return source


def test_target_not_exist_links_and_returns_true(fake_home, source_agent):
    result = install_agent_global("opencode", "code-reviewer.md", source_agent)

    assert result is True
    dest = _opencode_agents(fake_home) / "code-reviewer.md"
    assert dest.is_symlink()
    assert dest.resolve() == source_agent.resolve()
    assert dest.read_text() == AGENT_CONTENT


def test_correct_symlink_skips_returns_false(fake_home, source_agent):
    dest = _opencode_agents(fake_home) / "code-reviewer.md"
    dest.parent.mkdir(parents=True)
    dest.symlink_to(source_agent)
    mtime_before = dest.lstat().st_mtime

    result = install_agent_global("opencode", "code-reviewer.md", source_agent)

    assert result is False
    assert dest.is_symlink()
    assert dest.lstat().st_mtime == mtime_before


def test_identical_regular_file_is_replaced_with_symlink(fake_home, source_agent):
    dest = _opencode_agents(fake_home) / "code-reviewer.md"
    dest.parent.mkdir(parents=True)
    dest.write_text(AGENT_CONTENT)

    result = install_agent_global("opencode", "code-reviewer.md", source_agent)

    assert result is True
    assert dest.is_symlink()
    assert dest.resolve() == source_agent.resolve()


def test_different_regular_file_replaced_after_caller_confirms(fake_home, source_agent):
    dest = _opencode_agents(fake_home) / "code-reviewer.md"
    dest.parent.mkdir(parents=True)
    dest.write_text("# Old content\n")

    result = install_agent_global("opencode", "code-reviewer.md", source_agent)

    assert result is True
    assert dest.is_symlink()
    assert dest.read_text() == AGENT_CONTENT


def test_broken_symlink_is_repaired(fake_home, source_agent):
    dest = _opencode_agents(fake_home) / "code-reviewer.md"
    dest.parent.mkdir(parents=True)
    dest.symlink_to(source_agent.parent / "missing.md")

    result = install_agent_global("opencode", "code-reviewer.md", source_agent)

    assert result is True
    assert dest.is_symlink()
    assert dest.resolve() == source_agent.resolve()


def test_parent_dir_not_exist_auto_creates(fake_home, source_agent):
    result = install_agent_global("claudecode", "my-agent.md", source_agent)

    assert result is True
    dest = _claudecode_agents(fake_home) / "my-agent.md"
    assert dest.is_symlink()


def test_opencode_resolves_to_config_opencode(fake_home, source_agent):
    install_agent_global("opencode", "code-reviewer.md", source_agent)

    expected = fake_home / ".config" / "opencode" / "agents" / "code-reviewer.md"
    assert expected.is_symlink()
    # Claude Code dir should NOT be created
    claude_dest = fake_home / ".claude" / "agents" / "code-reviewer.md"
    assert not claude_dest.exists()


def test_claudecode_resolves_to_claude_agents(fake_home, source_agent):
    install_agent_global("claudecode", "code-reviewer.md", source_agent)

    expected = fake_home / ".claude" / "agents" / "code-reviewer.md"
    assert expected.is_symlink()
    # OpenCode dir should NOT be created
    opencode_dest = fake_home / ".config" / "opencode" / "agents" / "code-reviewer.md"
    assert not opencode_dest.exists()
