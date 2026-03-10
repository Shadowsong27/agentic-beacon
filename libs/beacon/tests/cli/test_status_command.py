"""Tests for abc status command.

Regression tests for:
- Bug #2: status showed ✗ for synced contexts and skills due to wrong path construction
"""
import pytest
from pathlib import Path
from click.testing import CliRunner
from beacon.cli import main


@pytest.fixture
def connected_project(valid_warehouse, temp_dir, monkeypatch):
    """Project directory with warehouse connected and some content synced."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    # Add content to the warehouse
    (valid_warehouse / "contexts" / "AGENTS.md").write_text("# Global Context")
    skills_dir = valid_warehouse / "skills" / "code-review"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text("# Code Review Skill")
    (valid_warehouse / "knowledge" / "python.md").write_text("# Python Standards")

    # Connect
    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])

    # Write beacon.yaml with full paths (as produced by sync)
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  knowledge:\n"
        "    - knowledge/python.md\n"
        "  skills:\n"
        "    - skills/code-review/SKILL.md\n"
        "  contexts:\n"
        "    - contexts/AGENTS.md\n"
    )

    # Sync so artifacts exist
    runner.invoke(main, ["sync"])

    return project_dir, runner


# ========== Regression: Bug #2 — status wrong path checks ==========


def test_status_shows_check_for_synced_context(connected_project):
    """Regression #2: status must show ✓ for a context that has been synced.

    Previously used (artifacts_dir / "contexts" / f"AGENTS.{ctx}.md") where
    ctx was already a full path like "contexts/AGENTS.md", producing a double-
    prefixed path that never existed.
    """
    project_dir, runner = connected_project

    result = runner.invoke(main, ["status"])

    assert result.exit_code == 0
    # The contexts table row for "contexts/AGENTS.md" should show ✓ not ✗
    assert "✗ contexts/AGENTS.md" not in result.output, (
        "Status showed ✗ for a context that is synced"
    )
    assert "✓" in result.output


def test_status_shows_check_for_synced_skill(connected_project):
    """Regression #2: status must show ✓ for a skill that has been synced.

    Previously used (artifacts_dir / "skills" / skill) where skill was already
    a full path like "skills/code-review/SKILL.md", producing a double-prefixed
    path that never existed.
    """
    project_dir, runner = connected_project

    result = runner.invoke(main, ["status"])

    assert result.exit_code == 0
    assert "✗ skills/code-review/SKILL.md" not in result.output, (
        "Status showed ✗ for a skill that is synced"
    )
    assert "✓" in result.output


def test_status_shows_cross_for_unsynced_context(valid_warehouse, temp_dir, monkeypatch):
    """Status shows ✗ for a context declared in beacon.yaml but not yet synced."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  knowledge: []\n"
        "  skills: []\n"
        "  contexts:\n"
        "    - contexts/AGENTS.md\n"
    )

    # Manually create artifacts dir but NOT the context file
    (project_dir / ".agentic-beacon" / "artifacts").mkdir()

    result = runner.invoke(main, ["status"])

    assert result.exit_code == 0
    assert "✗ contexts/AGENTS.md" in result.output


def test_status_shows_warehouse_path(connected_project):
    """Status displays the connected warehouse path."""
    project_dir, runner = connected_project

    result = runner.invoke(main, ["status"])

    assert result.exit_code == 0
    assert "Warehouse:" in result.output


def test_status_without_connection_shows_message(temp_dir, monkeypatch):
    """Status with no .agentic-beacon dir gives a clear not-connected message."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    result = runner.invoke(main, ["status"])

    assert result.exit_code == 0
    assert "warehouse" in result.output.lower() or "connected" in result.output.lower()
