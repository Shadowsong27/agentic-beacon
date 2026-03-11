"""Tests for abc skill install command."""

import pytest
from beacon.cli import main
from click.testing import CliRunner

SAMPLE_SKILL_MD = """\
---
name: my-skill
description: A sample skill for testing
license: MIT
compatibility: opencode
---

# Skill: My Skill

## Purpose
Does something useful.

## Process
1. Step one
2. Step two
"""


@pytest.fixture
def project_with_synced_skill(tmp_path, monkeypatch):
    """Project directory with a synced skill artifact and warehouse connected."""
    monkeypatch.chdir(tmp_path)

    # .agentic-beacon structure
    beacon_dir = tmp_path / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "config.toml").write_text(
        '[warehouse]\nlocal_path = "/some/warehouse"\n'
    )

    skill_dir = beacon_dir / "artifacts" / "skills" / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(SAMPLE_SKILL_MD)

    return tmp_path


# ---------------------------------------------------------------------------
# Claude Code installation
# ---------------------------------------------------------------------------


def test_skill_install_claudecode_copies_skill_md(project_with_synced_skill):
    tmp_path = project_with_synced_skill
    runner = CliRunner()

    # Create .claude/ so auto-detection picks it up
    (tmp_path / ".claude").mkdir()

    result = runner.invoke(
        main, ["skill", "install", "my-skill", "--agent", "claudecode"]
    )

    assert result.exit_code == 0, result.output
    installed = tmp_path / ".claude" / "skills" / "my-skill" / "SKILL.md"
    assert installed.exists()
    assert installed.read_text() == SAMPLE_SKILL_MD


def test_skill_install_claudecode_is_idempotent(project_with_synced_skill):
    tmp_path = project_with_synced_skill
    runner = CliRunner()
    (tmp_path / ".claude").mkdir()

    runner.invoke(main, ["skill", "install", "my-skill", "--agent", "claudecode"])
    result = runner.invoke(
        main, ["skill", "install", "my-skill", "--agent", "claudecode"]
    )

    assert result.exit_code == 0
    assert (tmp_path / ".claude" / "skills" / "my-skill" / "SKILL.md").exists()


# ---------------------------------------------------------------------------
# OpenCode installation
# ---------------------------------------------------------------------------


def test_skill_install_opencode_creates_skill_and_stub(project_with_synced_skill):
    tmp_path = project_with_synced_skill
    runner = CliRunner()

    result = runner.invoke(
        main, ["skill", "install", "my-skill", "--agent", "opencode"]
    )

    assert result.exit_code == 0, result.output

    # Full skill file
    skill_file = tmp_path / ".opencode" / "skills" / "my-skill" / "SKILL.md"
    assert skill_file.exists()
    assert skill_file.read_text() == SAMPLE_SKILL_MD

    # Thin command stub
    command_file = tmp_path / ".opencode" / "command" / "my-skill.md"
    assert command_file.exists()
    stub = command_file.read_text()
    assert "description: A sample skill for testing" in stub
    assert "my-skill" in stub
    # Stub should not contain full skill body
    assert "Step one" not in stub


# ---------------------------------------------------------------------------
# --all flag
# ---------------------------------------------------------------------------


def test_skill_install_all_installs_every_synced_skill(project_with_synced_skill):
    tmp_path = project_with_synced_skill

    # Add a second skill
    second_dir = tmp_path / ".agentic-beacon" / "artifacts" / "skills" / "other-skill"
    second_dir.mkdir()
    (second_dir / "SKILL.md").write_text(
        "---\nname: other-skill\ndescription: Another skill\n---\n\n# Skill: Other\n"
    )

    runner = CliRunner()
    result = runner.invoke(main, ["skill", "install", "--all", "--agent", "claudecode"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / ".claude" / "skills" / "my-skill" / "SKILL.md").exists()
    assert (tmp_path / ".claude" / "skills" / "other-skill" / "SKILL.md").exists()


# ---------------------------------------------------------------------------
# Auto-detection
# ---------------------------------------------------------------------------


def test_skill_install_autodetects_claudecode(project_with_synced_skill):
    tmp_path = project_with_synced_skill
    (tmp_path / ".claude").mkdir()

    runner = CliRunner()
    result = runner.invoke(main, ["skill", "install", "my-skill"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / ".claude" / "skills" / "my-skill" / "SKILL.md").exists()


def test_skill_install_autodetects_opencode(project_with_synced_skill):
    tmp_path = project_with_synced_skill
    (tmp_path / "opencode.json").write_text("{}")

    runner = CliRunner()
    result = runner.invoke(main, ["skill", "install", "my-skill"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / ".opencode" / "skills" / "my-skill" / "SKILL.md").exists()
    assert (tmp_path / ".opencode" / "command" / "my-skill.md").exists()


def test_skill_install_autodetects_both_agents(project_with_synced_skill):
    tmp_path = project_with_synced_skill
    (tmp_path / "opencode.json").write_text("{}")
    (tmp_path / ".claude").mkdir()

    runner = CliRunner()
    result = runner.invoke(main, ["skill", "install", "my-skill"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / ".claude" / "skills" / "my-skill" / "SKILL.md").exists()
    assert (tmp_path / ".opencode" / "command" / "my-skill.md").exists()


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_skill_install_errors_without_name_or_all(project_with_synced_skill):
    runner = CliRunner()
    result = runner.invoke(main, ["skill", "install"])
    assert result.exit_code != 0


def test_skill_install_errors_when_skill_not_synced(project_with_synced_skill):
    runner = CliRunner()
    result = runner.invoke(
        main, ["skill", "install", "nonexistent-skill", "--agent", "claudecode"]
    )
    assert result.exit_code != 0
    assert "not found" in result.output.lower()


def test_skill_install_errors_without_beacon_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        main, ["skill", "install", "my-skill", "--agent", "claudecode"]
    )
    assert result.exit_code != 0
    assert ".agentic-beacon" in result.output


def test_skill_install_errors_when_no_agent_detected(project_with_synced_skill):
    """No opencode.json and no .claude/ → cannot auto-detect."""
    runner = CliRunner()
    result = runner.invoke(main, ["skill", "install", "my-skill"])
    assert result.exit_code != 0
    assert "detect" in result.output.lower() or "agent" in result.output.lower()
