"""Tests for abc install command."""

import json

import pytest
import yaml
from beacon.cli.main import main
from click.testing import CliRunner

SAMPLE_SKILL_MD = """\
---
name: code-reviewer
description: Run a structured code review
license: MIT
---

# Skill: Code Reviewer

## Purpose
Reviews code for quality.

## Process
1. Analyse the diff
2. Report findings
"""

SAMPLE_CONTEXT_MD = """\
# Python Standards

Use type annotations everywhere.
"""

SAMPLE_KNOWLEDGE_MD = """\
# Decision: Use Pydantic

We use Pydantic for all data models.
"""


@pytest.fixture
def connected_project(tmp_path, monkeypatch):
    """Project with a warehouse connected and artifacts in the warehouse."""
    monkeypatch.chdir(tmp_path)

    # Warehouse
    warehouse = tmp_path / "warehouse"
    (warehouse / "skills" / "code-reviewer").mkdir(parents=True)
    (warehouse / "skills" / "code-reviewer" / "SKILL.md").write_text(SAMPLE_SKILL_MD)
    (warehouse / "contexts").mkdir()
    (warehouse / "contexts" / "python.md").write_text(SAMPLE_CONTEXT_MD)
    (warehouse / "knowledge" / "decisions").mkdir(parents=True)
    (warehouse / "knowledge" / "decisions" / "use-pydantic.md").write_text(
        SAMPLE_KNOWLEDGE_MD
    )

    # .agentic-beacon connected to warehouse
    beacon_dir = tmp_path / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "config.toml").write_text(
        f'[warehouse]\nlocal_path = "{warehouse}"\n'
    )

    return tmp_path


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------


def test_install_skill_copies_to_artifacts(connected_project):
    runner = CliRunner()
    result = runner.invoke(main, ["install", "skills/code-reviewer"])

    assert result.exit_code == 0, result.output
    skill_md = (
        connected_project
        / ".agentic-beacon"
        / "artifacts"
        / "skills"
        / "code-reviewer"
        / "SKILL.md"
    )
    assert skill_md.exists()
    assert skill_md.read_text() == SAMPLE_SKILL_MD


def test_install_skill_wires_opencode(connected_project):
    (connected_project / "opencode.json").write_text("{}")
    runner = CliRunner()
    result = runner.invoke(main, ["install", "skills/code-reviewer"])

    assert result.exit_code == 0, result.output
    assert (
        connected_project / ".opencode" / "skills" / "code-reviewer" / "SKILL.md"
    ).exists()
    assert (
        connected_project / ".opencode" / "command" / "abc-code-reviewer.md"
    ).exists()
    opencode_gitignore = (connected_project / ".opencode" / ".gitignore").read_text()
    assert "skills/" in opencode_gitignore
    assert "command/" in opencode_gitignore


def test_install_skill_wires_claudecode(connected_project):
    (connected_project / ".claude").mkdir()
    runner = CliRunner()
    result = runner.invoke(
        main, ["install", "skills/code-reviewer", "--agent", "claudecode"]
    )

    assert result.exit_code == 0, result.output
    assert (
        connected_project / ".claude" / "skills" / "code-reviewer" / "SKILL.md"
    ).exists()
    claude_gitignore = (connected_project / ".claude" / ".gitignore").read_text()
    assert "skills/" in claude_gitignore


def test_install_skill_no_agent_detected_wires_for_both(connected_project):
    """When no agent config exists, abc install wires the skill for both agents."""
    runner = CliRunner()
    result = runner.invoke(main, ["install", "skills/code-reviewer"])

    assert result.exit_code == 0, result.output
    # Artifact copied
    assert (
        connected_project
        / ".agentic-beacon"
        / "artifacts"
        / "skills"
        / "code-reviewer"
        / "SKILL.md"
    ).exists()
    # Wired to both agent directories
    assert (
        connected_project / ".opencode" / "skills" / "code-reviewer" / "SKILL.md"
    ).exists()
    assert (
        connected_project / ".claude" / "skills" / "code-reviewer" / "SKILL.md"
    ).exists()


def test_install_skill_no_agent_config_content_matches(connected_project):
    """Wired skill files match the artifact content."""
    runner = CliRunner()
    runner.invoke(main, ["install", "skills/code-reviewer"])

    opencode_content = (
        connected_project / ".opencode" / "skills" / "code-reviewer" / "SKILL.md"
    ).read_text()
    claude_content = (
        connected_project / ".claude" / "skills" / "code-reviewer" / "SKILL.md"
    ).read_text()

    assert opencode_content == SAMPLE_SKILL_MD
    assert claude_content == SAMPLE_SKILL_MD


def test_install_skill_no_agent_config_gitignores_created(connected_project):
    """Agent gitignores are created for both directories on install."""
    runner = CliRunner()
    runner.invoke(main, ["install", "skills/code-reviewer"])

    assert "skills/" in (connected_project / ".opencode" / ".gitignore").read_text()
    assert "skills/" in (connected_project / ".claude" / ".gitignore").read_text()


def test_install_skill_no_agent_config_idempotent(connected_project):
    """Running abc install twice produces no duplicate entries or errors."""
    runner = CliRunner()
    result1 = runner.invoke(main, ["install", "skills/code-reviewer"])
    result2 = runner.invoke(main, ["install", "skills/code-reviewer"])

    assert result1.exit_code == 0, result1.output
    assert result2.exit_code == 0, result2.output
    # Content unchanged on second run
    assert (
        connected_project / ".opencode" / "skills" / "code-reviewer" / "SKILL.md"
    ).read_text() == SAMPLE_SKILL_MD


def test_install_skill_explicit_agent_flag_skips_fallback(connected_project):
    """--agent flag targets only the specified agent; fallback is not triggered."""
    runner = CliRunner()
    result = runner.invoke(
        main, ["install", "skills/code-reviewer", "--agent", "opencode"]
    )

    assert result.exit_code == 0, result.output
    assert (
        connected_project / ".opencode" / "skills" / "code-reviewer" / "SKILL.md"
    ).exists()
    # claudecode NOT wired — explicit agent flag bypasses fallback
    assert not (
        connected_project / ".claude" / "skills" / "code-reviewer" / "SKILL.md"
    ).exists()


# ---------------------------------------------------------------------------
# Contexts
# ---------------------------------------------------------------------------


def test_install_context_copies_to_artifacts(connected_project):
    runner = CliRunner()
    result = runner.invoke(main, ["install", "contexts/python.md"])

    assert result.exit_code == 0, result.output
    ctx = connected_project / ".agentic-beacon" / "artifacts" / "contexts" / "python.md"
    assert ctx.exists()
    assert ctx.read_text() == SAMPLE_CONTEXT_MD


def test_install_context_without_md_extension(connected_project):
    runner = CliRunner()
    result = runner.invoke(main, ["install", "contexts/python"])

    assert result.exit_code == 0, result.output
    assert (
        connected_project / ".agentic-beacon" / "artifacts" / "contexts" / "python.md"
    ).exists()


def test_install_context_wires_opencode(connected_project):
    (connected_project / "opencode.json").write_text('{"instructions": []}')
    runner = CliRunner()
    result = runner.invoke(main, ["install", "contexts/python.md"])

    assert result.exit_code == 0, result.output
    data = json.loads((connected_project / "opencode.json").read_text())
    assert any("python.md" in p for p in data["instructions"])


def test_install_context_wires_claudecode(connected_project):
    claude_md = connected_project / "CLAUDE.md"
    claude_md.write_text("# Project\n")
    runner = CliRunner()
    result = runner.invoke(main, ["install", "contexts/python.md"])

    assert result.exit_code == 0, result.output
    content = claude_md.read_text()
    assert "@.agentic-beacon/artifacts/contexts/python.md" in content


# ---------------------------------------------------------------------------
# Knowledge
# ---------------------------------------------------------------------------


def test_install_knowledge_copies_to_artifacts(connected_project):
    runner = CliRunner()
    result = runner.invoke(main, ["install", "knowledge/decisions/use-pydantic.md"])

    assert result.exit_code == 0, result.output
    knowledge = (
        connected_project
        / ".agentic-beacon"
        / "artifacts"
        / "knowledge"
        / "decisions"
        / "use-pydantic.md"
    )
    assert knowledge.exists()
    assert knowledge.read_text() == SAMPLE_KNOWLEDGE_MD


# ---------------------------------------------------------------------------
# beacon.yaml update
# ---------------------------------------------------------------------------


def test_install_creates_beacon_yaml_when_absent(connected_project):
    runner = CliRunner()
    result = runner.invoke(main, ["install", "skills/code-reviewer"])

    assert result.exit_code == 0, result.output
    beacon_yaml = connected_project / ".agentic-beacon" / "beacon.yaml"
    assert beacon_yaml.exists()
    data = yaml.safe_load(beacon_yaml.read_text())
    assert "skills/code-reviewer" in data["artifacts"]["skills"]


def test_install_updates_existing_beacon_yaml(connected_project):
    beacon_yaml = connected_project / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  skills: []\n  contexts: []\n  knowledge: []\n"
    )

    runner = CliRunner()
    runner.invoke(main, ["install", "contexts/python.md"])

    data = yaml.safe_load(beacon_yaml.read_text())
    assert "contexts/python.md" in data["artifacts"]["contexts"]


def test_install_beacon_yaml_is_idempotent(connected_project):
    runner = CliRunner()
    runner.invoke(main, ["install", "skills/code-reviewer"])
    runner.invoke(main, ["install", "skills/code-reviewer"])

    beacon_yaml = connected_project / ".agentic-beacon" / "beacon.yaml"
    data = yaml.safe_load(beacon_yaml.read_text())
    skill_entries = [e for e in data["artifacts"]["skills"] if "code-reviewer" in e]
    assert len(skill_entries) == 1


def test_install_knowledge_added_to_beacon_yaml(connected_project):
    runner = CliRunner()
    runner.invoke(main, ["install", "knowledge/decisions/use-pydantic.md"])

    beacon_yaml = connected_project / ".agentic-beacon" / "beacon.yaml"
    data = yaml.safe_load(beacon_yaml.read_text())
    assert "knowledge/decisions/use-pydantic.md" in data["artifacts"]["knowledge"]


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_install_error_artifact_not_found(connected_project):
    runner = CliRunner()
    result = runner.invoke(main, ["install", "skills/nonexistent"])

    assert result.exit_code != 0
    assert "not found" in result.output.lower()


def test_install_error_without_beacon_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["install", "skills/code-reviewer"])

    assert result.exit_code != 0
    assert ".agentic-beacon" in result.output


# ---------------------------------------------------------------------------
# abc skill install is removed
# ---------------------------------------------------------------------------


def test_skill_subcommand_does_not_exist():
    runner = CliRunner()
    result = runner.invoke(main, ["skill", "install", "my-skill"])
    assert result.exit_code != 0
