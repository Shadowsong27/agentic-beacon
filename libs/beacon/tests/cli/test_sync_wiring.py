"""Tests for abc sync post-sync wiring: opencode.json, CLAUDE.md, skills.

Covers the three helper functions introduced in the auto-wiring feature:
  - _wire_contexts_opencode
  - _wire_contexts_claudecode
  - _wire_skills_post_sync

And integration tests through the full `abc sync` CLI command.
"""

import json
from unittest.mock import patch

import pytest
from beacon.cli import (
    _wire_contexts_claudecode,
    _wire_contexts_opencode,
    _wire_skills_post_sync,
    main,
)
from click.testing import CliRunner

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_SKILL_MD = """\
---
name: test-skill
description: A test skill
license: MIT
compatibility: opencode
---

# Skill: Test Skill

## Purpose
Does something useful.
"""


@pytest.fixture
def project_with_contexts(tmp_path):
    """Project dir with synced context artifacts."""
    artifacts_contexts = tmp_path / ".agentic-beacon" / "artifacts" / "contexts"
    artifacts_contexts.mkdir(parents=True)
    (artifacts_contexts / "global.md").write_text("# Global context")
    (artifacts_contexts / "python.md").write_text("# Python context")
    return tmp_path


@pytest.fixture
def project_with_skill(tmp_path):
    """Project dir with a synced skill artifact."""
    skill_dir = tmp_path / ".agentic-beacon" / "artifacts" / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(SAMPLE_SKILL_MD)
    return tmp_path


# ---------------------------------------------------------------------------
# Unit tests: _wire_contexts_opencode
# ---------------------------------------------------------------------------


def test_wire_contexts_opencode_appends_paths(project_with_contexts):
    project = project_with_contexts
    (project / "opencode.json").write_text(json.dumps({"instructions": []}))

    artifacts_dir = project / ".agentic-beacon" / "artifacts"
    added = _wire_contexts_opencode(project, artifacts_dir)

    assert len(added) == 2
    data = json.loads((project / "opencode.json").read_text())
    assert ".agentic-beacon/artifacts/contexts/global.md" in data["instructions"]
    assert ".agentic-beacon/artifacts/contexts/python.md" in data["instructions"]


def test_wire_contexts_opencode_idempotent(project_with_contexts):
    project = project_with_contexts
    (project / "opencode.json").write_text(json.dumps({"instructions": []}))
    artifacts_dir = project / ".agentic-beacon" / "artifacts"

    _wire_contexts_opencode(project, artifacts_dir)
    added_second = _wire_contexts_opencode(project, artifacts_dir)

    assert added_second == []
    data = json.loads((project / "opencode.json").read_text())
    # No duplicates
    instructions = data["instructions"]
    assert len(instructions) == len(set(instructions))


def test_wire_contexts_opencode_skips_if_no_opencode_json(project_with_contexts):
    project = project_with_contexts
    artifacts_dir = project / ".agentic-beacon" / "artifacts"

    added = _wire_contexts_opencode(project, artifacts_dir)

    assert added == []


def test_wire_contexts_opencode_skips_if_no_contexts(tmp_path):
    (tmp_path / "opencode.json").write_text(json.dumps({"instructions": []}))
    artifacts_dir = tmp_path / ".agentic-beacon" / "artifacts"
    artifacts_dir.mkdir(parents=True)

    added = _wire_contexts_opencode(tmp_path, artifacts_dir)

    assert added == []
    data = json.loads((tmp_path / "opencode.json").read_text())
    assert data["instructions"] == []


def test_wire_contexts_opencode_preserves_existing_instructions(
    project_with_contexts,
):
    project = project_with_contexts
    existing = ["some/existing/instruction.md"]
    (project / "opencode.json").write_text(json.dumps({"instructions": existing}))
    artifacts_dir = project / ".agentic-beacon" / "artifacts"

    _wire_contexts_opencode(project, artifacts_dir)

    data = json.loads((project / "opencode.json").read_text())
    assert "some/existing/instruction.md" in data["instructions"]
    assert len(data["instructions"]) == 3  # 1 existing + 2 new contexts


def test_wire_contexts_opencode_handles_missing_instructions_key(
    project_with_contexts,
):
    project = project_with_contexts
    # opencode.json without an "instructions" key
    (project / "opencode.json").write_text(json.dumps({"model": "gpt-4"}))
    artifacts_dir = project / ".agentic-beacon" / "artifacts"

    added = _wire_contexts_opencode(project, artifacts_dir)

    assert len(added) == 2
    data = json.loads((project / "opencode.json").read_text())
    assert "instructions" in data


# ---------------------------------------------------------------------------
# Unit tests: _wire_contexts_claudecode
# ---------------------------------------------------------------------------


def test_wire_contexts_claudecode_appends_refs(project_with_contexts):
    project = project_with_contexts
    (project / "CLAUDE.md").write_text("# Project\n")
    artifacts_dir = project / ".agentic-beacon" / "artifacts"

    added = _wire_contexts_claudecode(project, artifacts_dir)

    assert len(added) == 2
    content = (project / "CLAUDE.md").read_text()
    assert "@.agentic-beacon/artifacts/contexts/global.md" in content
    assert "@.agentic-beacon/artifacts/contexts/python.md" in content


def test_wire_contexts_claudecode_idempotent(project_with_contexts):
    project = project_with_contexts
    (project / "CLAUDE.md").write_text("# Project\n")
    artifacts_dir = project / ".agentic-beacon" / "artifacts"

    _wire_contexts_claudecode(project, artifacts_dir)
    added_second = _wire_contexts_claudecode(project, artifacts_dir)

    assert added_second == []
    content = (project / "CLAUDE.md").read_text()
    assert content.count("@.agentic-beacon/artifacts/contexts/global.md") == 1


def test_wire_contexts_claudecode_skips_if_no_claude_md(project_with_contexts):
    project = project_with_contexts
    artifacts_dir = project / ".agentic-beacon" / "artifacts"

    added = _wire_contexts_claudecode(project, artifacts_dir)

    assert added == []


def test_wire_contexts_claudecode_finds_dotclaude_claude_md(project_with_contexts):
    project = project_with_contexts
    claude_dir = project / ".claude"
    claude_dir.mkdir()
    (claude_dir / "CLAUDE.md").write_text("# Project\n")
    artifacts_dir = project / ".agentic-beacon" / "artifacts"

    added = _wire_contexts_claudecode(project, artifacts_dir)

    assert len(added) == 2
    content = (claude_dir / "CLAUDE.md").read_text()
    assert "@.agentic-beacon/artifacts/contexts/global.md" in content


# ---------------------------------------------------------------------------
# Unit tests: _wire_skills_post_sync
# ---------------------------------------------------------------------------


def test_wire_skills_post_sync_installs_for_opencode(project_with_skill):
    project = project_with_skill
    (project / "opencode.json").write_text(json.dumps({}))

    artifacts_dir = project / ".agentic-beacon" / "artifacts"
    installed, errors = _wire_skills_post_sync(project, artifacts_dir)

    assert errors == []
    assert any("test-skill" in entry and "opencode" in entry for entry in installed)
    assert (project / ".opencode" / "skills" / "test-skill" / "SKILL.md").exists()
    assert (project / ".opencode" / "command" / "test-skill.md").exists()


def test_wire_skills_post_sync_installs_for_claudecode(project_with_skill):
    project = project_with_skill
    (project / ".claude").mkdir()

    artifacts_dir = project / ".agentic-beacon" / "artifacts"
    installed, errors = _wire_skills_post_sync(project, artifacts_dir)

    assert errors == []
    assert any("test-skill" in entry and "claudecode" in entry for entry in installed)
    assert (project / ".claude" / "skills" / "test-skill" / "SKILL.md").exists()


def test_wire_skills_post_sync_skips_if_no_agents(project_with_skill):
    project = project_with_skill
    artifacts_dir = project / ".agentic-beacon" / "artifacts"

    installed, errors = _wire_skills_post_sync(project, artifacts_dir)

    assert installed == []
    assert errors == []


def test_wire_skills_post_sync_skips_if_no_skills(tmp_path):
    (tmp_path / "opencode.json").write_text(json.dumps({}))
    artifacts_dir = tmp_path / ".agentic-beacon" / "artifacts"
    artifacts_dir.mkdir(parents=True)

    installed, errors = _wire_skills_post_sync(tmp_path, artifacts_dir)

    assert installed == []
    assert errors == []


# ---------------------------------------------------------------------------
# Integration tests: abc sync end-to-end wiring
# ---------------------------------------------------------------------------


@pytest.fixture
def full_sync_project(tmp_path, valid_warehouse):
    """Connected project with contexts and skills in beacon.yaml."""
    # Add context to warehouse
    (valid_warehouse / "contexts" / "global.md").write_text("# Global context")

    # Add skill to warehouse
    skill_dir = valid_warehouse / "skills" / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(SAMPLE_SKILL_MD)

    project = tmp_path / "project"
    project.mkdir()

    # Build .agentic-beacon manually (avoids CWD dependency in fixture)
    beacon_dir = project / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "config.toml").write_text(
        f'[warehouse]\nlocal_path = "{valid_warehouse}"\n'
    )
    (beacon_dir / "beacon.yaml").write_text(
        "artifacts:\n"
        "  contexts:\n"
        "    - contexts/global.md\n"
        "  skills:\n"
        "    - skills/my-skill/**/*\n"
        "  knowledge: []\n"
    )

    runner = CliRunner()
    return project, runner


def test_sync_wires_contexts_to_opencode_json(full_sync_project, monkeypatch):
    project, runner = full_sync_project
    monkeypatch.chdir(project)
    (project / "opencode.json").write_text(json.dumps({"instructions": []}))

    result = runner.invoke(main, ["sync"])

    assert result.exit_code == 0
    data = json.loads((project / "opencode.json").read_text())
    assert ".agentic-beacon/artifacts/contexts/global.md" in data["instructions"]
    assert "wired" in result.output.lower()


def test_sync_wires_contexts_to_claude_md(full_sync_project, monkeypatch):
    project, runner = full_sync_project
    monkeypatch.chdir(project)
    (project / "CLAUDE.md").write_text("# Project\n")

    result = runner.invoke(main, ["sync"])

    assert result.exit_code == 0
    content = (project / "CLAUDE.md").read_text()
    assert "@.agentic-beacon/artifacts/contexts/global.md" in content
    assert "wired" in result.output.lower()


def test_sync_installs_skills(full_sync_project, monkeypatch):
    project, runner = full_sync_project
    monkeypatch.chdir(project)
    (project / "opencode.json").write_text(json.dumps({}))

    result = runner.invoke(main, ["sync"])

    assert result.exit_code == 0
    assert (project / ".opencode" / "skills" / "my-skill" / "SKILL.md").exists()
    assert (project / ".opencode" / "command" / "my-skill.md").exists()
    assert "installed" in result.output.lower()


def test_sync_wiring_is_idempotent(full_sync_project, monkeypatch):
    project, runner = full_sync_project
    monkeypatch.chdir(project)
    (project / "opencode.json").write_text(json.dumps({"instructions": []}))

    runner.invoke(main, ["sync"])
    runner.invoke(main, ["sync"])

    data = json.loads((project / "opencode.json").read_text())
    instructions = data["instructions"]
    # No duplicates
    assert len(instructions) == len(set(instructions))
    assert instructions.count(".agentic-beacon/artifacts/contexts/global.md") == 1


def test_sync_prints_manual_instructions_when_no_agent_config_non_interactive(
    full_sync_project, monkeypatch
):
    project, runner = full_sync_project
    monkeypatch.chdir(project)
    # No opencode.json, no CLAUDE.md; simulate non-interactive (CI) environment

    with patch("beacon.cli._is_interactive", return_value=False):
        result = runner.invoke(main, ["sync"])

    assert result.exit_code == 0
    assert "manual" in result.output.lower() or "wire" in result.output.lower()


def test_sync_interactive_init_opencode_json(full_sync_project, monkeypatch):
    project, runner = full_sync_project
    monkeypatch.chdir(project)
    # No opencode.json, no CLAUDE.md; user answers yes/no to prompts

    with patch("beacon.cli._is_interactive", return_value=True):
        # "y" for opencode.json prompt, "n" for CLAUDE.md prompt
        result = runner.invoke(main, ["sync"], input="y\nn\n")

    assert result.exit_code == 0
    assert (project / "opencode.json").exists()
    data = json.loads((project / "opencode.json").read_text())
    assert ".agentic-beacon/artifacts/contexts/global.md" in data["instructions"]
    assert not (project / "CLAUDE.md").exists()


def test_sync_interactive_init_claude_md(full_sync_project, monkeypatch):
    project, runner = full_sync_project
    monkeypatch.chdir(project)
    # No opencode.json, no CLAUDE.md; user answers no/yes to prompts

    with patch("beacon.cli._is_interactive", return_value=True):
        # "n" for opencode.json prompt, "y" for CLAUDE.md prompt
        result = runner.invoke(main, ["sync"], input="n\ny\n")

    assert result.exit_code == 0
    assert not (project / "opencode.json").exists()
    assert (project / "CLAUDE.md").exists()
    content = (project / "CLAUDE.md").read_text()
    assert "@.agentic-beacon/artifacts/contexts/global.md" in content
