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
    _install_skill_claudecode,
    _install_skill_opencode,
    _update_agent_gitignores,
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


def test_wire_skills_post_sync_idempotent_opencode(project_with_skill):
    """Second call returns empty installed list when skill files are unchanged."""
    project = project_with_skill
    (project / "opencode.json").write_text(json.dumps({}))
    artifacts_dir = project / ".agentic-beacon" / "artifacts"

    installed_first, _ = _wire_skills_post_sync(project, artifacts_dir)
    installed_second, errors = _wire_skills_post_sync(project, artifacts_dir)

    assert any("test-skill" in e for e in installed_first)
    assert installed_second == []
    assert errors == []


def test_wire_skills_post_sync_idempotent_claudecode(project_with_skill):
    """Second call returns empty installed list for claudecode when skill is unchanged."""
    project = project_with_skill
    (project / ".claude").mkdir()
    artifacts_dir = project / ".agentic-beacon" / "artifacts"

    installed_first, _ = _wire_skills_post_sync(project, artifacts_dir)
    installed_second, errors = _wire_skills_post_sync(project, artifacts_dir)

    assert any("test-skill" in e for e in installed_first)
    assert installed_second == []
    assert errors == []


def test_wire_skills_post_sync_reinstalls_when_content_changes(project_with_skill):
    """Skill is re-installed when the SKILL.md content changes."""
    project = project_with_skill
    (project / "opencode.json").write_text(json.dumps({}))
    artifacts_dir = project / ".agentic-beacon" / "artifacts"

    _wire_skills_post_sync(project, artifacts_dir)

    # Update the artifact SKILL.md
    skill_md = artifacts_dir / "skills" / "test-skill" / "SKILL.md"
    skill_md.write_text(SAMPLE_SKILL_MD + "\n## New Section\nExtra content.\n")

    installed_second, errors = _wire_skills_post_sync(project, artifacts_dir)

    assert any("test-skill" in e for e in installed_second)
    assert errors == []


# ---------------------------------------------------------------------------
# Unit tests: _update_agent_gitignores
# ---------------------------------------------------------------------------


def test_update_agent_gitignores_creates_claude_gitignore(tmp_path):
    (tmp_path / ".claude").mkdir()
    _update_agent_gitignores(tmp_path)
    content = (tmp_path / ".claude" / ".gitignore").read_text()
    assert "skills/" in content


def test_update_agent_gitignores_creates_opencode_gitignore(tmp_path):
    (tmp_path / ".opencode").mkdir()
    _update_agent_gitignores(tmp_path)
    content = (tmp_path / ".opencode" / ".gitignore").read_text()
    assert "skills/" in content
    assert "command/" in content


def test_update_agent_gitignores_skips_when_no_agent_dirs(tmp_path):
    _update_agent_gitignores(tmp_path)
    assert not (tmp_path / ".claude" / ".gitignore").exists()
    assert not (tmp_path / ".opencode" / ".gitignore").exists()


def test_update_agent_gitignores_idempotent(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".opencode").mkdir()
    _update_agent_gitignores(tmp_path)
    _update_agent_gitignores(tmp_path)
    claude_content = (tmp_path / ".claude" / ".gitignore").read_text()
    opencode_content = (tmp_path / ".opencode" / ".gitignore").read_text()
    assert claude_content.count("skills/") == 1
    assert opencode_content.count("skills/") == 1
    assert opencode_content.count("command/") == 1


def test_update_agent_gitignores_appends_to_existing_gitignore(tmp_path):
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    (claude_dir / ".gitignore").write_text("settings.local.json\n")
    _update_agent_gitignores(tmp_path)
    content = (claude_dir / ".gitignore").read_text()
    assert "settings.local.json" in content
    assert "skills/" in content


# ---------------------------------------------------------------------------
# Unit tests: _install_skill_opencode / _install_skill_claudecode
# ---------------------------------------------------------------------------


def test_install_skill_opencode_returns_true_on_first_install(tmp_path):
    changed = _install_skill_opencode(
        tmp_path, "my-skill", SAMPLE_SKILL_MD, "A test skill"
    )

    assert changed is True
    assert (tmp_path / ".opencode" / "skills" / "my-skill" / "SKILL.md").exists()
    assert (tmp_path / ".opencode" / "command" / "my-skill.md").exists()


def test_install_skill_opencode_returns_false_when_unchanged(tmp_path):
    _install_skill_opencode(tmp_path, "my-skill", SAMPLE_SKILL_MD, "A test skill")
    changed = _install_skill_opencode(
        tmp_path, "my-skill", SAMPLE_SKILL_MD, "A test skill"
    )

    assert changed is False


def test_install_skill_opencode_returns_true_when_content_changes(tmp_path):
    _install_skill_opencode(tmp_path, "my-skill", SAMPLE_SKILL_MD, "A test skill")
    changed = _install_skill_opencode(
        tmp_path, "my-skill", SAMPLE_SKILL_MD + "\n## Extra\n", "A test skill"
    )

    assert changed is True


def test_install_skill_opencode_updates_file_content_when_changed(tmp_path):
    _install_skill_opencode(tmp_path, "my-skill", SAMPLE_SKILL_MD, "A test skill")
    new_content = SAMPLE_SKILL_MD + "\n## Extra\n"
    _install_skill_opencode(tmp_path, "my-skill", new_content, "A test skill")

    skill_file = tmp_path / ".opencode" / "skills" / "my-skill" / "SKILL.md"
    assert skill_file.read_text() == new_content


def test_install_skill_claudecode_returns_true_on_first_install(tmp_path):
    changed = _install_skill_claudecode(tmp_path, "my-skill", SAMPLE_SKILL_MD)

    assert changed is True
    assert (tmp_path / ".claude" / "skills" / "my-skill" / "SKILL.md").exists()


def test_install_skill_claudecode_returns_false_when_unchanged(tmp_path):
    _install_skill_claudecode(tmp_path, "my-skill", SAMPLE_SKILL_MD)
    changed = _install_skill_claudecode(tmp_path, "my-skill", SAMPLE_SKILL_MD)

    assert changed is False


def test_install_skill_claudecode_returns_true_when_content_changes(tmp_path):
    _install_skill_claudecode(tmp_path, "my-skill", SAMPLE_SKILL_MD)
    changed = _install_skill_claudecode(
        tmp_path, "my-skill", SAMPLE_SKILL_MD + "\n## Extra\n"
    )

    assert changed is True


def test_install_skill_claudecode_updates_file_content_when_changed(tmp_path):
    _install_skill_claudecode(tmp_path, "my-skill", SAMPLE_SKILL_MD)
    new_content = SAMPLE_SKILL_MD + "\n## Extra\n"
    _install_skill_claudecode(tmp_path, "my-skill", new_content)

    skill_file = tmp_path / ".claude" / "skills" / "my-skill" / "SKILL.md"
    assert skill_file.read_text() == new_content


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
    opencode_gitignore = (project / ".opencode" / ".gitignore").read_text()
    assert "skills/" in opencode_gitignore
    assert "command/" in opencode_gitignore


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


def test_sync_does_not_report_installed_skills_on_second_run(
    full_sync_project, monkeypatch
):
    """Regression: abc sync should not print 'Installed N skill(s)' when skills
    are already up-to-date (idempotent skill wiring)."""
    project, runner = full_sync_project
    monkeypatch.chdir(project)
    (project / "opencode.json").write_text(json.dumps({}))

    result_first = runner.invoke(main, ["sync"])
    result_second = runner.invoke(main, ["sync"])

    assert result_first.exit_code == 0
    assert result_second.exit_code == 0
    assert "installed" in result_first.output.lower()
    assert "installed" not in result_second.output.lower()


def test_sync_reports_installed_skills_again_after_warehouse_update(
    full_sync_project, monkeypatch, valid_warehouse
):
    """Skills should be re-installed (and reported) when warehouse content changes."""
    project, runner = full_sync_project
    monkeypatch.chdir(project)
    (project / "opencode.json").write_text(json.dumps({}))

    runner.invoke(main, ["sync"])

    # Update the skill in the warehouse
    updated_content = SAMPLE_SKILL_MD + "\n## New Section\nExtra content.\n"
    (valid_warehouse / "skills" / "my-skill" / "SKILL.md").write_text(updated_content)

    result_second = runner.invoke(main, ["sync"])

    assert result_second.exit_code == 0
    assert "installed" in result_second.output.lower()
    # Verify the updated content was actually propagated
    installed_skill = project / ".opencode" / "skills" / "my-skill" / "SKILL.md"
    assert "New Section" in installed_skill.read_text()
