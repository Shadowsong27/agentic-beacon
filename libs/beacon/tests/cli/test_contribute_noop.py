"""Tests for abc contribute no-op detection and agents scope exclusion (Phase 9, task 9.1).

TDD Test Cases (9.1):
- TC1: All project artifacts identical → "Nothing to contribute" printed, exit 0, no branch created
- TC2: At least one project artifact differs → proceeds to normal contribute flow
- TC3: Artifacts dir missing or empty → "Nothing to contribute" related exit 0
- TC4: Warehouse agents/ files differ from global installs → abc contribute ignores them, exits 0
"""

from pathlib import Path

import pytest
from beacon.cli import main
from click.testing import CliRunner


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    return home


@pytest.fixture
def warehouse_with_agent(tmp_path):
    """Warehouse with both a knowledge file and an agent definition."""
    wh = tmp_path / "warehouse"
    wh.mkdir()
    (wh / "README.md").write_text("# Warehouse")
    for d in ("agents", "knowledge", "skills", "contexts", "docs"):
        (wh / d).mkdir()
    (wh / "knowledge" / "lesson.md").write_text("# Lesson\nOriginal.\n")
    (wh / "agents" / "code-reviewer.md").write_text("# Reviewer\nWarehouse version.\n")
    return wh


@pytest.fixture
def connected_project(tmp_path, warehouse_with_agent, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    runner = CliRunner()
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse_with_agent)])
    beacon_yaml = project / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge:\n    - knowledge/lesson.md\n  skills: []\n  contexts: []\n"
    )
    runner.invoke(main, ["sync", "--skip-git-check"])
    return project, warehouse_with_agent, runner


def test_tc1_identical_artifacts_nothing_to_contribute(connected_project):
    """TC1: All project artifacts identical → Nothing to contribute, exit 0."""
    project, warehouse, runner = connected_project

    result = runner.invoke(main, ["contribute"])

    assert result.exit_code == 0
    assert (
        "Nothing to contribute" in result.output or "nothing" in result.output.lower()
    )


def test_tc2_modified_artifact_proceeds(connected_project):
    """TC2: At least one project artifact differs → proceeds to contribute flow."""
    project, warehouse, runner = connected_project

    # Modify local artifact
    local = project / ".agentic-beacon" / "artifacts" / "knowledge" / "lesson.md"
    local.write_text("# Lesson\nImproved.\n")

    result = runner.invoke(
        main, ["contribute", "knowledge/lesson.md", "--skip-git-check"]
    )

    assert result.exit_code == 0
    assert "Improved." in (warehouse / "knowledge" / "lesson.md").read_text()


def test_tc4_agents_not_in_contribute_scope(connected_project, fake_home):
    """TC4: Warehouse agents/ files differ from global installs → abc contribute ignores them."""
    project, warehouse, runner = connected_project

    # Install agent globally with different content
    claude_agents = fake_home / ".claude" / "agents"
    claude_agents.mkdir(parents=True)
    (claude_agents / "code-reviewer.md").write_text(
        "# Reviewer\nLocally modified version.\n"
    )

    # Project artifacts are all identical (no local changes)
    result = runner.invoke(main, ["contribute"])

    assert result.exit_code == 0
    assert (
        "Nothing to contribute" in result.output or "nothing" in result.output.lower()
    )
    # Warehouse agent should NOT have been modified
    assert (
        "Warehouse version" in (warehouse / "agents" / "code-reviewer.md").read_text()
    )
