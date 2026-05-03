"""Tests for abc sync post-sync wiring: opencode.json, CLAUDE.md, skills.

Covers the three helper functions introduced in the auto-wiring feature:
  - wire_contexts_opencode
  - wire_contexts_claudecode
  - wire_skills_post_sync

And integration tests through the full `abc sync` CLI command.
"""

import json
import os
import subprocess
from unittest.mock import patch

import pytest
from beacon.cli.main import main
from beacon.domains.artifact.agent import update_agent_gitignores
from beacon.domains.artifact.skill import (
    _install_skill_claudecode,
    _install_skill_opencode,
    normalize_skill_entry,
    skill_name_from_entry,
    wire_single_skill,
    wire_skills_post_sync,
)
from beacon.domains.setup.wiring import wire_contexts_claudecode, wire_contexts_opencode
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
# Unit tests: wire_contexts_opencode
# ---------------------------------------------------------------------------


def testwire_contexts_opencode_appends_paths(project_with_contexts):
    project = project_with_contexts
    (project / "opencode.json").write_text(json.dumps({"instructions": []}))

    artifacts_dir = project / ".agentic-beacon" / "artifacts"
    added = wire_contexts_opencode(project, artifacts_dir)

    assert len(added) == 2
    data = json.loads((project / "opencode.json").read_text())
    assert ".agentic-beacon/artifacts/contexts/global.md" in data["instructions"]
    assert ".agentic-beacon/artifacts/contexts/python.md" in data["instructions"]


def testwire_contexts_opencode_idempotent(project_with_contexts):
    project = project_with_contexts
    (project / "opencode.json").write_text(json.dumps({"instructions": []}))
    artifacts_dir = project / ".agentic-beacon" / "artifacts"

    wire_contexts_opencode(project, artifacts_dir)
    added_second = wire_contexts_opencode(project, artifacts_dir)

    assert added_second == []
    data = json.loads((project / "opencode.json").read_text())
    # No duplicates
    instructions = data["instructions"]
    assert len(instructions) == len(set(instructions))


def testwire_contexts_opencode_skips_if_no_opencode_json(project_with_contexts):
    project = project_with_contexts
    artifacts_dir = project / ".agentic-beacon" / "artifacts"

    added = wire_contexts_opencode(project, artifacts_dir)

    assert added == []


def testwire_contexts_opencode_skips_if_no_contexts(tmp_path):
    (tmp_path / "opencode.json").write_text(json.dumps({"instructions": []}))
    artifacts_dir = tmp_path / ".agentic-beacon" / "artifacts"
    artifacts_dir.mkdir(parents=True)

    added = wire_contexts_opencode(tmp_path, artifacts_dir)

    assert added == []
    data = json.loads((tmp_path / "opencode.json").read_text())
    assert data["instructions"] == []


def testwire_contexts_opencode_preserves_existing_instructions(
    project_with_contexts,
):
    project = project_with_contexts
    existing = ["some/existing/instruction.md"]
    (project / "opencode.json").write_text(json.dumps({"instructions": existing}))
    artifacts_dir = project / ".agentic-beacon" / "artifacts"

    wire_contexts_opencode(project, artifacts_dir)

    data = json.loads((project / "opencode.json").read_text())
    assert "some/existing/instruction.md" in data["instructions"]
    assert len(data["instructions"]) == 3  # 1 existing + 2 new contexts


def testwire_contexts_opencode_handles_missing_instructions_key(
    project_with_contexts,
):
    project = project_with_contexts
    # opencode.json without an "instructions" key
    (project / "opencode.json").write_text(json.dumps({"model": "gpt-4"}))
    artifacts_dir = project / ".agentic-beacon" / "artifacts"

    added = wire_contexts_opencode(project, artifacts_dir)

    assert len(added) == 2
    data = json.loads((project / "opencode.json").read_text())
    assert "instructions" in data


# ---------------------------------------------------------------------------
# Unit tests: wire_contexts_claudecode
# ---------------------------------------------------------------------------


def testwire_contexts_claudecode_appends_refs(project_with_contexts):
    project = project_with_contexts
    (project / "CLAUDE.md").write_text("# Project\n")
    artifacts_dir = project / ".agentic-beacon" / "artifacts"

    added = wire_contexts_claudecode(project, artifacts_dir)

    assert len(added) == 2
    content = (project / "CLAUDE.md").read_text()
    assert "@.agentic-beacon/artifacts/contexts/global.md" in content
    assert "@.agentic-beacon/artifacts/contexts/python.md" in content


def testwire_contexts_claudecode_idempotent(project_with_contexts):
    project = project_with_contexts
    (project / "CLAUDE.md").write_text("# Project\n")
    artifacts_dir = project / ".agentic-beacon" / "artifacts"

    wire_contexts_claudecode(project, artifacts_dir)
    added_second = wire_contexts_claudecode(project, artifacts_dir)

    assert added_second == []
    content = (project / "CLAUDE.md").read_text()
    assert content.count("@.agentic-beacon/artifacts/contexts/global.md") == 1


def testwire_contexts_claudecode_skips_if_no_claude_md(project_with_contexts):
    project = project_with_contexts
    artifacts_dir = project / ".agentic-beacon" / "artifacts"

    added = wire_contexts_claudecode(project, artifacts_dir)

    assert added == []


def testwire_contexts_claudecode_finds_dotclaude_claude_md(project_with_contexts):
    project = project_with_contexts
    claude_dir = project / ".claude"
    claude_dir.mkdir()
    (claude_dir / "CLAUDE.md").write_text("# Project\n")
    artifacts_dir = project / ".agentic-beacon" / "artifacts"

    added = wire_contexts_claudecode(project, artifacts_dir)

    assert len(added) == 2
    content = (claude_dir / "CLAUDE.md").read_text()
    assert "@.agentic-beacon/artifacts/contexts/global.md" in content


# ---------------------------------------------------------------------------
# Unit tests: wire_skills_post_sync
# ---------------------------------------------------------------------------


def test_wire_skills_post_sync_installs_for_opencode(project_with_skill):
    project = project_with_skill
    (project / "opencode.json").write_text(json.dumps({}))

    artifacts_dir = project / ".agentic-beacon" / "artifacts"
    installed, errors = wire_skills_post_sync(project, artifacts_dir)

    assert errors == []
    assert any("test-skill" in entry and "opencode" in entry for entry in installed)
    assert (project / ".opencode" / "skills" / "test-skill" / "SKILL.md").exists()
    assert (project / ".opencode" / "command" / "test-skill.md").exists()


def test_wire_skills_post_sync_installs_for_claudecode(project_with_skill):
    project = project_with_skill
    (project / ".claude").mkdir()

    artifacts_dir = project / ".agentic-beacon" / "artifacts"
    installed, errors = wire_skills_post_sync(project, artifacts_dir)

    assert errors == []
    assert any("test-skill" in entry and "claudecode" in entry for entry in installed)
    assert (project / ".claude" / "skills" / "test-skill" / "SKILL.md").exists()


def test_wire_skills_post_sync_wires_for_all_agents_when_none_detected(
    project_with_skill,
):
    """When no agent config files exist, skills are wired for both agents by default."""
    project = project_with_skill
    artifacts_dir = project / ".agentic-beacon" / "artifacts"

    installed, errors = wire_skills_post_sync(project, artifacts_dir)

    assert errors == []
    assert any("test-skill" in e and "opencode" in e for e in installed)
    assert any("test-skill" in e and "claudecode" in e for e in installed)
    assert (project / ".opencode" / "skills" / "test-skill" / "SKILL.md").exists()
    assert (project / ".claude" / "skills" / "test-skill" / "SKILL.md").exists()


def test_wire_skills_post_sync_skips_if_no_skills(tmp_path):
    (tmp_path / "opencode.json").write_text(json.dumps({}))
    artifacts_dir = tmp_path / ".agentic-beacon" / "artifacts"
    artifacts_dir.mkdir(parents=True)

    installed, errors = wire_skills_post_sync(tmp_path, artifacts_dir)

    assert installed == []
    assert errors == []


def test_wire_skills_post_sync_idempotent_opencode(project_with_skill):
    """Second call returns empty installed list when skill files are unchanged."""
    project = project_with_skill
    (project / "opencode.json").write_text(json.dumps({}))
    artifacts_dir = project / ".agentic-beacon" / "artifacts"

    installed_first, _ = wire_skills_post_sync(project, artifacts_dir)
    installed_second, errors = wire_skills_post_sync(project, artifacts_dir)

    assert any("test-skill" in e for e in installed_first)
    assert installed_second == []
    assert errors == []


def test_wire_skills_post_sync_idempotent_claudecode(project_with_skill):
    """Second call returns empty installed list for claudecode when skill is unchanged."""
    project = project_with_skill
    (project / ".claude").mkdir()
    artifacts_dir = project / ".agentic-beacon" / "artifacts"

    installed_first, _ = wire_skills_post_sync(project, artifacts_dir)
    installed_second, errors = wire_skills_post_sync(project, artifacts_dir)

    assert any("test-skill" in e for e in installed_first)
    assert installed_second == []
    assert errors == []


def test_wire_skills_post_sync_reinstalls_when_content_changes(project_with_skill):
    """Skill is re-installed when the SKILL.md content changes (force mode)."""
    project = project_with_skill
    (project / "opencode.json").write_text(json.dumps({}))
    artifacts_dir = project / ".agentic-beacon" / "artifacts"

    wire_skills_post_sync(project, artifacts_dir)

    # Update the artifact SKILL.md
    skill_md = artifacts_dir / "skills" / "test-skill" / "SKILL.md"
    skill_md.write_text(SAMPLE_SKILL_MD + "\n## New Section\nExtra content.\n")

    # force=True bypasses the soft-block (non-interactive mode would otherwise block)
    installed_second, errors = wire_skills_post_sync(project, artifacts_dir, force=True)

    assert any("test-skill" in e for e in installed_second)
    assert errors == []


# ---------------------------------------------------------------------------
# Unit tests: update_agent_gitignores
# ---------------------------------------------------------------------------


def test_update_agent_gitignores_creates_claude_gitignore(tmp_path):
    (tmp_path / ".claude").mkdir()
    update_agent_gitignores(tmp_path)
    content = (tmp_path / ".claude" / ".gitignore").read_text()
    assert "skills/" in content


def test_update_agent_gitignores_creates_opencode_gitignore(tmp_path):
    (tmp_path / ".opencode").mkdir()
    update_agent_gitignores(tmp_path)
    content = (tmp_path / ".opencode" / ".gitignore").read_text()
    assert "skills/" in content
    assert "command/" in content


def test_update_agent_gitignores_skips_when_no_agent_dirs(tmp_path):
    update_agent_gitignores(tmp_path)
    assert not (tmp_path / ".claude" / ".gitignore").exists()
    assert not (tmp_path / ".opencode" / ".gitignore").exists()


def test_update_agent_gitignores_idempotent(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".opencode").mkdir()
    update_agent_gitignores(tmp_path)
    update_agent_gitignores(tmp_path)
    claude_content = (tmp_path / ".claude" / ".gitignore").read_text()
    opencode_content = (tmp_path / ".opencode" / ".gitignore").read_text()
    assert claude_content.count("skills/") == 1
    assert opencode_content.count("skills/") == 1
    assert opencode_content.count("command/") == 1


def test_update_agent_gitignores_appends_to_existing_gitignore(tmp_path):
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    (claude_dir / ".gitignore").write_text("settings.local.json\n")
    update_agent_gitignores(tmp_path)
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


GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "t@t.local",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "t@t.local",
}


@pytest.fixture
def full_sync_project(tmp_path, valid_warehouse):
    """Connected project with contexts and skills in beacon.yaml."""
    # Add context to warehouse
    (valid_warehouse / "contexts" / "global.md").write_text("# Global context")

    # Add skill to warehouse
    skill_dir = valid_warehouse / "skills" / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(SAMPLE_SKILL_MD)

    # Commit new files
    subprocess.run(
        ["git", "add", "."],
        cwd=valid_warehouse,
        env=GIT_ENV,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Add artifacts"],
        cwd=valid_warehouse,
        env=GIT_ENV,
        check=True,
        capture_output=True,
    )

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

    with patch("beacon.cli.sync.is_interactive", return_value=False):
        result = runner.invoke(main, ["sync"])

    assert result.exit_code == 0
    assert "manual" in result.output.lower() or "wire" in result.output.lower()


def test_sync_interactive_init_opencode_json(full_sync_project, monkeypatch):
    project, runner = full_sync_project
    monkeypatch.chdir(project)
    # No opencode.json, no CLAUDE.md; user answers yes/no to prompts

    with patch("beacon.cli.sync.is_interactive", return_value=True):
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

    with patch("beacon.cli.sync.is_interactive", return_value=True):
        # "n" for opencode.json (contexts), "y" for CLAUDE.md (contexts),
        # "n" for opencode.json (skills), "n" for CLAUDE.md (skills)
        # (CLAUDE.md alone doesn't create .claude/ so skill prompt also fires)
        result = runner.invoke(main, ["sync"], input="n\ny\nn\nn\n")

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
    """After warehouse skill edits, the live .opencode/skills/ copy must reflect
    the update. Under the symlink-based wiring model the live skill file is a
    symlink into the warehouse, so warehouse edits are visible immediately
    without needing sync to rewrite anything — but sync must remain idempotent
    and the live content must match the warehouse."""
    project, runner = full_sync_project
    monkeypatch.chdir(project)
    (project / "opencode.json").write_text(json.dumps({}))

    runner.invoke(main, ["sync"])

    # Update the skill in the warehouse
    updated_content = SAMPLE_SKILL_MD + "\n## New Section\nExtra content.\n"
    (valid_warehouse / "skills" / "my-skill" / "SKILL.md").write_text(updated_content)

    # Commit the update
    subprocess.run(
        ["git", "add", "."],
        cwd=valid_warehouse,
        env=GIT_ENV,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Update skill"],
        cwd=valid_warehouse,
        env=GIT_ENV,
        check=True,
        capture_output=True,
    )

    result_second = runner.invoke(main, ["sync", "--force"])

    assert result_second.exit_code == 0
    # Verify the updated content is visible through the live skill file (symlink).
    installed_skill = project / ".opencode" / "skills" / "my-skill" / "SKILL.md"
    assert installed_skill.exists()
    assert installed_skill.is_symlink()
    assert "New Section" in installed_skill.read_text()


# ---------------------------------------------------------------------------
# Skill wiring: no agent config prompt
# ---------------------------------------------------------------------------


@pytest.fixture
def skills_only_project(tmp_path, valid_warehouse):
    """Connected project with skills but NO contexts in beacon.yaml."""
    skill_dir = valid_warehouse / "skills" / "my-skill"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(SAMPLE_SKILL_MD)

    # Commit new files
    subprocess.run(
        ["git", "add", "."],
        cwd=valid_warehouse,
        env=GIT_ENV,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Add skill"],
        cwd=valid_warehouse,
        env=GIT_ENV,
        check=True,
        capture_output=True,
    )

    project = tmp_path / "project"
    project.mkdir()

    beacon_dir = project / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "config.toml").write_text(
        f'[warehouse]\nlocal_path = "{valid_warehouse}"\n'
    )
    (beacon_dir / "beacon.yaml").write_text(
        "artifacts:\n"
        "  contexts: []\n"
        "  skills:\n"
        "    - skills/my-skill/**/*\n"
        "  knowledge: []\n"
    )

    runner = CliRunner()
    return project, runner


def test_sync_skill_no_agent_config_wires_for_both_agents(
    skills_only_project, monkeypatch
):
    """Skills are wired to both agent directories even when no agent config exists."""
    project, runner = skills_only_project
    monkeypatch.chdir(project)

    result = runner.invoke(main, ["sync"])

    assert result.exit_code == 0
    assert "installed" in result.output.lower()
    assert "my-skill" in result.output.lower()
    assert (project / ".opencode" / "skills" / "my-skill" / "SKILL.md").exists()
    assert (project / ".claude" / "skills" / "my-skill" / "SKILL.md").exists()


def test_sync_skill_no_agent_config_no_prompt(skills_only_project, monkeypatch):
    """No agent-init prompts are shown when no agent config exists — skills wire unconditionally."""
    project, runner = skills_only_project
    monkeypatch.chdir(project)

    with patch("beacon.cli.sync.is_interactive", return_value=True):
        result = runner.invoke(main, ["sync"])

    assert result.exit_code == 0
    assert "initialize" not in result.output.lower()
    assert "no agent config" not in result.output.lower()
    assert "installed" in result.output.lower()


def test_sync_skill_dry_run_does_not_prompt(skills_only_project, monkeypatch):
    """Dry run never triggers the no-agent-config prompt for skills."""
    project, runner = skills_only_project
    monkeypatch.chdir(project)

    with patch("beacon.cli.sync.is_interactive", return_value=True):
        result = runner.invoke(main, ["sync", "--dry-run"])

    assert result.exit_code == 0
    assert "no agent config" not in result.output.lower()
    assert "initialize" not in result.output.lower()
    # No wiring notes either
    assert "manual wiring required" not in result.output.lower()


def test_sync_skill_empty_skills_dir_no_prompt(tmp_path, valid_warehouse, monkeypatch):
    """No skills in beacon.yaml means no skill-wiring prompt fires."""
    project = tmp_path / "project"
    project.mkdir()

    beacon_dir = project / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "config.toml").write_text(
        f'[warehouse]\nlocal_path = "{valid_warehouse}"\n'
    )
    (beacon_dir / "beacon.yaml").write_text(
        "artifacts:\n  contexts: []\n  skills: []\n  knowledge: []\n"
    )

    monkeypatch.chdir(project)
    runner = CliRunner()

    with patch("beacon.cli.sync.is_interactive", return_value=False):
        result = runner.invoke(main, ["sync"])

    assert result.exit_code == 0
    assert "skills synced" not in result.output.lower()
    assert "manual wiring" not in result.output.lower()


def test_sync_skill_dir_without_skill_md_no_prompt(
    skills_only_project, monkeypatch, valid_warehouse
):
    """Skill directories without SKILL.md do not trigger the no-agent-config prompt."""
    project, runner = skills_only_project
    monkeypatch.chdir(project)

    # Remove the SKILL.md from the warehouse skill so sync copies a dir without it
    (valid_warehouse / "skills" / "my-skill" / "SKILL.md").unlink()
    (valid_warehouse / "skills" / "my-skill" / "README.md").write_text("# Not a skill")

    # Commit the changes
    subprocess.run(
        ["git", "add", "."],
        cwd=valid_warehouse,
        env=GIT_ENV,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Update skill"],
        cwd=valid_warehouse,
        env=GIT_ENV,
        check=True,
        capture_output=True,
    )

    # Update beacon.yaml to match
    beacon_yaml = project / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  contexts: []\n"
        "  skills:\n"
        "    - skills/my-skill/**/*\n"
        "  knowledge: []\n"
    )

    with patch("beacon.cli.sync.is_interactive", return_value=False):
        result = runner.invoke(main, ["sync"])

    assert result.exit_code == 0
    # No prompt because no valid SKILL.md files
    assert "skills synced" not in result.output.lower()


# ---------------------------------------------------------------------------
# No-agent-config fallback: comprehensive edge cases
# ---------------------------------------------------------------------------


def test_wire_skills_fallback_idempotent(project_with_skill):
    """Second call with no agent config returns empty installed (skill unchanged)."""
    project = project_with_skill
    artifacts_dir = project / ".agentic-beacon" / "artifacts"

    installed_first, _ = wire_skills_post_sync(project, artifacts_dir)
    installed_second, errors = wire_skills_post_sync(project, artifacts_dir)

    assert any("test-skill" in e for e in installed_first)
    assert installed_second == []
    assert errors == []
    # Files still exist
    assert (project / ".opencode" / "skills" / "test-skill" / "SKILL.md").exists()
    assert (project / ".claude" / "skills" / "test-skill" / "SKILL.md").exists()


def test_wire_skills_fallback_force_overwrites_conflict(project_with_skill):
    """Force flag overwrites a modified live skill file when no agent config."""
    project = project_with_skill
    artifacts_dir = project / ".agentic-beacon" / "artifacts"

    # Pre-install a modified version of the skill
    opencode_skill = project / ".opencode" / "skills" / "test-skill" / "SKILL.md"
    opencode_skill.parent.mkdir(parents=True)
    opencode_skill.write_text("# local modification")

    installed, errors = wire_skills_post_sync(project, artifacts_dir, force=True)

    assert errors == []
    assert any("test-skill" in e and "opencode" in e for e in installed)
    assert opencode_skill.read_text() == SAMPLE_SKILL_MD


def test_wire_skills_fallback_preserve_skips_conflict(project_with_skill):
    """Preserve flag skips a modified live skill file when no agent config."""
    project = project_with_skill
    artifacts_dir = project / ".agentic-beacon" / "artifacts"

    opencode_skill = project / ".opencode" / "skills" / "test-skill" / "SKILL.md"
    opencode_skill.parent.mkdir(parents=True)
    opencode_skill.write_text("# local modification")

    installed, errors = wire_skills_post_sync(project, artifacts_dir, preserve=True)

    assert errors == []
    # opencode skipped due to conflict; claudecode installed
    assert not any("test-skill" in e and "opencode" in e for e in installed)
    assert any("test-skill" in e and "claudecode" in e for e in installed)
    assert opencode_skill.read_text() == "# local modification"


def test_wire_skills_fallback_multiple_skills(tmp_path):
    """All skills in the artifacts dir are wired for both agents when none detected."""
    for name in ("skill-a", "skill-b", "skill-c"):
        skill_dir = tmp_path / ".agentic-beacon" / "artifacts" / "skills" / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(SAMPLE_SKILL_MD.replace("test-skill", name))

    artifacts_dir = tmp_path / ".agentic-beacon" / "artifacts"
    installed, errors = wire_skills_post_sync(tmp_path, artifacts_dir)

    assert errors == []
    assert len(installed) == 6  # 3 skills × 2 agents
    for name in ("skill-a", "skill-b", "skill-c"):
        assert (tmp_path / ".opencode" / "skills" / name / "SKILL.md").exists()
        assert (tmp_path / ".claude" / "skills" / name / "SKILL.md").exists()


def test_wire_skills_fallback_content_matches_artifact(project_with_skill):
    """Wired skill files contain exactly the artifact content."""
    project = project_with_skill
    artifacts_dir = project / ".agentic-beacon" / "artifacts"

    wire_skills_post_sync(project, artifacts_dir)

    opencode_content = (
        project / ".opencode" / "skills" / "test-skill" / "SKILL.md"
    ).read_text()
    claude_content = (
        project / ".claude" / "skills" / "test-skill" / "SKILL.md"
    ).read_text()

    assert opencode_content == SAMPLE_SKILL_MD
    assert claude_content == SAMPLE_SKILL_MD


def test_sync_no_agent_config_gitignores_created(skills_only_project, monkeypatch):
    """abc sync creates agent gitignores for both directories when no config exists."""
    project, runner = skills_only_project
    monkeypatch.chdir(project)

    runner.invoke(main, ["sync"])

    assert (project / ".opencode" / ".gitignore").exists()
    assert (project / ".claude" / ".gitignore").exists()
    opencode_gi = (project / ".opencode" / ".gitignore").read_text()
    assert "skills/" in opencode_gi
    claude_gi = (project / ".claude" / ".gitignore").read_text()
    assert "skills/" in claude_gi


def test_sync_no_agent_config_dry_run_does_not_wire(skills_only_project, monkeypatch):
    """Dry-run does not create any skill files even with the fallback active."""
    project, runner = skills_only_project
    monkeypatch.chdir(project)

    result = runner.invoke(main, ["sync", "--dry-run"])

    assert result.exit_code == 0
    assert not (project / ".opencode" / "skills").exists()
    assert not (project / ".claude" / "skills").exists()


def test_sync_full_project_skills_wired_even_when_contexts_need_agent_config(
    full_sync_project, monkeypatch
):
    """When no agent config exists, skills wire unconditionally while contexts still prompt."""
    project, runner = full_sync_project
    monkeypatch.chdir(project)

    with patch("beacon.cli.sync.is_interactive", return_value=False):
        result = runner.invoke(main, ["sync"])

    assert result.exit_code == 0
    # Skills wired to both agents
    assert (project / ".opencode" / "skills" / "my-skill" / "SKILL.md").exists()
    assert (project / ".claude" / "skills" / "my-skill" / "SKILL.md").exists()
    assert "installed" in result.output.lower()
    # Contexts still need manual wiring (no opencode.json / CLAUDE.md)
    assert "manual wiring required" in result.output.lower()


def test_sync_no_agent_config_second_run_idempotent(skills_only_project, monkeypatch):
    """Second abc sync with no agent config wires nothing new and prints no install line."""
    project, runner = skills_only_project
    monkeypatch.chdir(project)

    runner.invoke(main, ["sync"])
    result_second = runner.invoke(main, ["sync"])

    assert result_second.exit_code == 0
    assert "installed" not in result_second.output.lower()
    # Files still present
    assert (project / ".opencode" / "skills" / "my-skill" / "SKILL.md").exists()
    assert (project / ".claude" / "skills" / "my-skill" / "SKILL.md").exists()


def test_sync_fallback_wires_for_both_even_when_one_config_exists(
    skills_only_project, monkeypatch
):
    """When only one agent config exists, the detected agent is used (not the fallback)."""
    project, runner = skills_only_project
    monkeypatch.chdir(project)

    # Only opencode configured
    (project / "opencode.json").write_text("{}")
    result = runner.invoke(main, ["sync"])

    assert result.exit_code == 0
    assert (project / ".opencode" / "skills" / "my-skill" / "SKILL.md").exists()
    # claudecode NOT wired — detection found opencode, fallback not triggered
    assert not (project / ".claude" / "skills" / "my-skill" / "SKILL.md").exists()


# ---------------------------------------------------------------------------
# Agent sync: sync_agents_from_warehouse via abc sync
# ---------------------------------------------------------------------------

SAMPLE_AGENT_MD = "You are a helpful assistant specialized in Python.\n"


def _make_agent_project(tmp_path, monkeypatch):
    """Build a minimal connected project with an agents/ dir in the warehouse."""
    wh = tmp_path / "warehouse"
    for d in ("agents", "knowledge", "skills", "contexts", "docs"):
        (wh / d).mkdir(parents=True)
    (wh / "README.md").write_text("# WH")
    (wh / "agents" / "code-reviewer.md").write_text(SAMPLE_AGENT_MD)

    # Init git
    subprocess.run(
        ["git", "init"], cwd=wh, env=GIT_ENV, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "add", "."], cwd=wh, env=GIT_ENV, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=wh,
        env=GIT_ENV,
        check=True,
        capture_output=True,
    )

    project = tmp_path / "project"
    project.mkdir()
    beacon_dir = project / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "config.toml").write_text(f'[warehouse]\nlocal_path = "{wh}"\n')
    (beacon_dir / "beacon.yaml").write_text(
        "artifacts:\n  knowledge: []\n  skills: []\n  contexts: []\n"
    )
    monkeypatch.chdir(project)
    return wh, project


class TestSyncAgentsFromWarehouse:
    def test_installs_agent_to_opencode_global_dir(
        self, tmp_path, monkeypatch, isolated_home
    ):
        """abc sync links warehouse agents into ~/.config/opencode/agents/."""
        (isolated_home / ".config" / "opencode").mkdir(parents=True)
        wh, project = _make_agent_project(tmp_path, monkeypatch)

        runner = CliRunner()
        result = runner.invoke(main, ["sync", "--skip-git-check"])

        assert result.exit_code == 0, result.output
        dest = isolated_home / ".config" / "opencode" / "agents" / "code-reviewer.md"
        assert dest.is_symlink()
        assert dest.resolve() == (wh / "agents" / "code-reviewer.md").resolve()
        assert dest.read_text() == SAMPLE_AGENT_MD

    def test_installs_agent_to_claudecode_global_dir(
        self, tmp_path, monkeypatch, isolated_home
    ):
        """abc sync links warehouse agents into ~/.claude/agents/."""
        (isolated_home / ".claude").mkdir(parents=True)
        wh, project = _make_agent_project(tmp_path, monkeypatch)

        runner = CliRunner()
        result = runner.invoke(main, ["sync", "--skip-git-check"])

        assert result.exit_code == 0, result.output
        dest = isolated_home / ".claude" / "agents" / "code-reviewer.md"
        assert dest.is_symlink()
        assert dest.resolve() == (wh / "agents" / "code-reviewer.md").resolve()
        assert dest.read_text() == SAMPLE_AGENT_MD

    def test_installs_to_both_tools_when_both_present(
        self, tmp_path, monkeypatch, isolated_home
    ):
        """When both opencode and claudecode are installed, both get the agent."""
        (isolated_home / ".config" / "opencode").mkdir(parents=True)
        (isolated_home / ".claude").mkdir(parents=True)
        wh, project = _make_agent_project(tmp_path, monkeypatch)

        runner = CliRunner()
        result = runner.invoke(main, ["sync", "--skip-git-check"])

        assert result.exit_code == 0, result.output
        opencode_dest = (
            isolated_home / ".config" / "opencode" / "agents" / "code-reviewer.md"
        )
        claude_dest = isolated_home / ".claude" / "agents" / "code-reviewer.md"
        assert opencode_dest.is_symlink()
        assert claude_dest.is_symlink()
        assert opencode_dest.resolve() == (wh / "agents" / "code-reviewer.md").resolve()
        assert claude_dest.resolve() == (wh / "agents" / "code-reviewer.md").resolve()
        assert "code-reviewer" in result.output

    def test_skips_agents_when_warehouse_has_no_agents_dir(
        self, tmp_path, monkeypatch, isolated_home
    ):
        """Warehouse without agents/ dir: sync completes without installing any agents."""
        (isolated_home / ".config" / "opencode").mkdir(parents=True)

        wh = tmp_path / "warehouse"
        for d in ("knowledge", "skills", "contexts", "docs"):
            (wh / d).mkdir(parents=True)
        (wh / "README.md").write_text("# WH")

        # Init git
        subprocess.run(
            ["git", "init"], cwd=wh, env=GIT_ENV, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "add", "."], cwd=wh, env=GIT_ENV, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=wh,
            env=GIT_ENV,
            check=True,
            capture_output=True,
        )

        project = tmp_path / "project"
        project.mkdir()
        beacon_dir = project / ".agentic-beacon"
        beacon_dir.mkdir()
        (beacon_dir / "config.toml").write_text(f'[warehouse]\nlocal_path = "{wh}"\n')
        (beacon_dir / "beacon.yaml").write_text(
            "artifacts:\n  knowledge: []\n  skills: []\n  contexts: []\n"
        )
        monkeypatch.chdir(project)

        runner = CliRunner()
        result = runner.invoke(main, ["sync", "--skip-git-check"])

        assert result.exit_code == 0, result.output
        assert not (isolated_home / ".config" / "opencode" / "agents").exists()

    def test_idempotent_when_already_up_to_date(
        self, tmp_path, monkeypatch, isolated_home
    ):
        """Running sync twice does not re-link agent files that are already current."""
        agents_dir = isolated_home / ".config" / "opencode" / "agents"
        agents_dir.mkdir(parents=True)

        wh, project = _make_agent_project(tmp_path, monkeypatch)
        runner = CliRunner()
        result = runner.invoke(main, ["sync", "--skip-git-check"])
        assert result.exit_code == 0, result.output

        dest = agents_dir / "code-reviewer.md"
        assert dest.is_symlink()
        mtime_before = dest.lstat().st_mtime

        result = runner.invoke(main, ["sync", "--skip-git-check"])
        assert result.exit_code == 0, result.output

        mtime_after = dest.lstat().st_mtime
        assert mtime_before == mtime_after

    def test_force_overwrites_conflicting_agent(
        self, tmp_path, monkeypatch, isolated_home
    ):
        """--force overwrites a diverged local agent without prompting."""
        agents_dir = isolated_home / ".config" / "opencode" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "code-reviewer.md").write_text("old local content\n")

        wh, project = _make_agent_project(tmp_path, monkeypatch)
        runner = CliRunner()
        result = runner.invoke(main, ["sync", "--force", "--skip-git-check"])

        assert result.exit_code == 0, result.output
        dest = agents_dir / "code-reviewer.md"
        assert dest.is_symlink()
        assert dest.resolve() == (wh / "agents" / "code-reviewer.md").resolve()
        assert dest.read_text() == SAMPLE_AGENT_MD

    def test_non_interactive_conflict_skips_without_prompt(
        self, tmp_path, monkeypatch, isolated_home
    ):
        """In non-interactive mode, conflicting agents are skipped automatically."""
        agents_dir = isolated_home / ".config" / "opencode" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "code-reviewer.md").write_text("diverged content\n")

        wh, project = _make_agent_project(tmp_path, monkeypatch)
        runner = CliRunner()
        result = runner.invoke(main, ["sync", "--skip-git-check"])

        assert result.exit_code == 0, result.output
        assert (agents_dir / "code-reviewer.md").read_text() == "diverged content\n"


# ---------------------------------------------------------------------------
# Multi-file skill: normalize_skill_entry, skill_name_from_entry,
# wire_single_skill, wire_skills_post_sync, abc sync
# ---------------------------------------------------------------------------

SAMPLE_SKILL_MD_MULTI = """\
---
name: pipeline-helper
description: Pipeline helper skill
---
# Pipeline Helper
"""


class TestNormalizeSkillEntry:
    def test_file_level_entry(self):
        assert normalize_skill_entry("skills/my-skill/SKILL.md") == "skills/my-skill"

    def test_directory_entry_with_slash(self):
        assert normalize_skill_entry("skills/my-skill/") == "skills/my-skill"

    def test_directory_entry_no_slash(self):
        assert normalize_skill_entry("skills/my-skill") == "skills/my-skill"

    def test_bare_name_gets_prefix(self):
        assert normalize_skill_entry("my-skill") == "skills/my-skill"

    def test_skill_name_from_entry_file(self):
        assert (
            skill_name_from_entry("skills/pipeline-helper/SKILL.md")
            == "pipeline-helper"
        )

    def test_skill_name_from_entry_dir(self):
        assert skill_name_from_entry("skills/pipeline-helper/") == "pipeline-helper"


class TestWireSingleSkill:
    def test_copies_all_files_to_claude(self, tmp_path):
        skill_src = tmp_path / "artifacts" / "skills" / "my-skill"
        skill_src.mkdir(parents=True)
        (skill_src / "SKILL.md").write_text(SAMPLE_SKILL_MD_MULTI)
        (skill_src / "helper.py").write_text("def run(): pass\n")

        wire_single_skill(tmp_path, "my-skill", skill_src, "claudecode")

        dest = tmp_path / ".claude" / "skills" / "my-skill"
        assert (dest / "SKILL.md").read_text() == SAMPLE_SKILL_MD_MULTI
        assert (dest / "helper.py").read_text() == "def run(): pass\n"

    def test_copies_all_files_to_opencode(self, tmp_path):
        skill_src = tmp_path / "artifacts" / "skills" / "my-skill"
        skill_src.mkdir(parents=True)
        (skill_src / "SKILL.md").write_text(SAMPLE_SKILL_MD_MULTI)
        (skill_src / "config.yaml").write_text("key: value\n")

        wire_single_skill(tmp_path, "my-skill", skill_src, "opencode")

        dest = tmp_path / ".opencode" / "skills" / "my-skill"
        assert (dest / "SKILL.md").exists()
        assert (dest / "config.yaml").read_text() == "key: value\n"

    def test_opencode_generates_command_stub(self, tmp_path):
        skill_src = tmp_path / "artifacts" / "skills" / "my-skill"
        skill_src.mkdir(parents=True)
        (skill_src / "SKILL.md").write_text(SAMPLE_SKILL_MD_MULTI)

        wire_single_skill(tmp_path, "my-skill", skill_src, "opencode")

        stub = tmp_path / ".opencode" / "command" / "my-skill.md"
        assert stub.exists()
        assert "Pipeline helper skill" in stub.read_text()

    def test_returns_true_when_file_written(self, tmp_path):
        skill_src = tmp_path / "artifacts" / "skills" / "s"
        skill_src.mkdir(parents=True)
        (skill_src / "SKILL.md").write_text("# S\n")

        assert wire_single_skill(tmp_path, "s", skill_src, "claudecode") is True

    def test_returns_false_when_already_up_to_date(self, tmp_path):
        skill_src = tmp_path / "artifacts" / "skills" / "s"
        skill_src.mkdir(parents=True)
        (skill_src / "SKILL.md").write_text("# S\n")

        wire_single_skill(tmp_path, "s", skill_src, "claudecode")
        assert wire_single_skill(tmp_path, "s", skill_src, "claudecode") is False

    def test_subdirectory_files_preserved(self, tmp_path):
        skill_src = tmp_path / "artifacts" / "skills" / "s"
        (skill_src / "sub").mkdir(parents=True)
        (skill_src / "SKILL.md").write_text("# S\n")
        (skill_src / "sub" / "util.py").write_text("x = 1\n")

        wire_single_skill(tmp_path, "s", skill_src, "claudecode")

        assert (tmp_path / ".claude" / "skills" / "s" / "sub" / "util.py").exists()


class TestWireSkillsPostSyncMultiFile:
    def test_all_files_wired_to_claude(self, tmp_path):
        """wire_skills_post_sync copies every file in the skill dir, not just SKILL.md."""
        skill_dir = tmp_path / ".agentic-beacon" / "artifacts" / "skills" / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(SAMPLE_SKILL_MD_MULTI)
        (skill_dir / "helper.py").write_text("def run(): pass\n")
        (tmp_path / ".claude").mkdir()

        wire_skills_post_sync(tmp_path, tmp_path / ".agentic-beacon" / "artifacts")

        dest = tmp_path / ".claude" / "skills" / "my-skill"
        assert (dest / "SKILL.md").exists()
        assert (dest / "helper.py").read_text() == "def run(): pass\n"

    def test_conflict_detected_on_companion_file(self, tmp_path):
        """Conflict detection triggers when a companion file (not SKILL.md) differs."""
        skill_dir = tmp_path / ".agentic-beacon" / "artifacts" / "skills" / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(SAMPLE_SKILL_MD_MULTI)
        (skill_dir / "helper.py").write_text("def run(): pass\n")

        # Pre-install a different helper.py
        live_dir = tmp_path / ".claude" / "skills" / "my-skill"
        live_dir.mkdir(parents=True)
        (live_dir / "SKILL.md").write_text(SAMPLE_SKILL_MD_MULTI)
        (live_dir / "helper.py").write_text("def run(): return 42\n")

        installed, errors = wire_skills_post_sync(
            tmp_path,
            tmp_path / ".agentic-beacon" / "artifacts",
            preserve=True,
        )

        # Should be skipped due to conflict + preserve
        assert not installed
        # helper.py must remain unchanged
        assert (live_dir / "helper.py").read_text() == "def run(): return 42\n"


class TestSyncMultiFileSkillIntegration:
    """Integration: abc sync with a multi-file skill in the warehouse."""

    @pytest.fixture
    def multi_file_skill_project(self, tmp_path):
        wh = tmp_path / "warehouse"
        for d in ("agents", "knowledge", "skills", "contexts", "docs"):
            (wh / d).mkdir(parents=True)
        (wh / "README.md").write_text("# WH")

        skill_dir = wh / "skills" / "pipeline-helper"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(SAMPLE_SKILL_MD_MULTI)
        (skill_dir / "runner.py").write_text("def main(): pass\n")
        (skill_dir / "config.yaml").write_text("timeout: 30\n")

        # Init git
        subprocess.run(
            ["git", "init"], cwd=wh, env=GIT_ENV, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "add", "."], cwd=wh, env=GIT_ENV, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=wh,
            env=GIT_ENV,
            check=True,
            capture_output=True,
        )

        project = tmp_path / "project"
        project.mkdir()
        beacon_dir = project / ".agentic-beacon"
        beacon_dir.mkdir()
        (beacon_dir / "config.toml").write_text(f'[warehouse]\nlocal_path = "{wh}"\n')
        # New directory-style entry
        (beacon_dir / "beacon.yaml").write_text(
            "artifacts:\n  knowledge: []\n"
            "  skills:\n    - skills/pipeline-helper/\n  contexts: []\n"
        )
        (project / ".claude").mkdir()
        return project, wh

    def test_all_skill_files_synced_to_artifacts(
        self, multi_file_skill_project, monkeypatch
    ):
        project, _ = multi_file_skill_project
        monkeypatch.chdir(project)
        runner = CliRunner()
        result = runner.invoke(main, ["sync", "--skip-git-check"])

        assert result.exit_code == 0
        artifacts = (
            project / ".agentic-beacon" / "artifacts" / "skills" / "pipeline-helper"
        )
        assert (artifacts / "SKILL.md").exists()
        assert (artifacts / "runner.py").exists()
        assert (artifacts / "config.yaml").exists()

    def test_all_skill_files_wired_to_live_dir(
        self, multi_file_skill_project, monkeypatch
    ):
        project, _ = multi_file_skill_project
        monkeypatch.chdir(project)
        runner = CliRunner()
        runner.invoke(main, ["sync", "--skip-git-check"])

        live = project / ".claude" / "skills" / "pipeline-helper"
        assert (live / "SKILL.md").exists()
        assert (live / "runner.py").read_text() == "def main(): pass\n"
        assert (live / "config.yaml").read_text() == "timeout: 30\n"

    def test_file_level_skill_entry_is_rejected(self, tmp_path, monkeypatch):
        """File-level skill entries (e.g. 'skills/foo/SKILL.md') are a hard error."""
        wh = tmp_path / "warehouse"
        for d in ("agents", "knowledge", "skills", "contexts", "docs"):
            (wh / d).mkdir(parents=True)
        (wh / "README.md").write_text("# WH")
        skill_dir = wh / "skills" / "old-style"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Old\n")

        # Init git
        subprocess.run(
            ["git", "init"], cwd=wh, env=GIT_ENV, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "add", "."], cwd=wh, env=GIT_ENV, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=wh,
            env=GIT_ENV,
            check=True,
            capture_output=True,
        )

        project = tmp_path / "project"
        project.mkdir()
        beacon_dir = project / ".agentic-beacon"
        beacon_dir.mkdir()
        (beacon_dir / "config.toml").write_text(f'[warehouse]\nlocal_path = "{wh}"\n')
        (beacon_dir / "beacon.yaml").write_text(
            "artifacts:\n  knowledge: []\n"
            "  skills:\n    - skills/old-style/SKILL.md\n  contexts: []\n"
        )
        monkeypatch.chdir(project)

        runner = CliRunner()
        result = runner.invoke(main, ["sync", "--skip-git-check"])

        assert result.exit_code != 0
        assert "skills/old-style/SKILL.md" in result.output
