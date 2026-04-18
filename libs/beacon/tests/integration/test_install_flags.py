"""Tests for abc install --preserve and --force flags (Phase 10, task 10.4).

TDD Test Cases (10.4):
- TC1: --preserve, file differs → skipped, no prompt
- TC2: --force, file differs → overwritten, no prompt
- TC3: --force + --preserve → exits 1 with mutual-exclusion error
- TC4: No flags, file differs, interactive → soft block prompt shown
"""

import pytest
from beacon.cli import main
from click.testing import CliRunner


@pytest.fixture
def warehouse_with_knowledge(tmp_path):
    wh = tmp_path / "warehouse"
    wh.mkdir()
    (wh / "README.md").write_text("# Warehouse")
    for d in ("agents", "knowledge", "skills", "contexts", "docs"):
        (wh / d).mkdir()
    (wh / "knowledge" / "lesson.md").write_text("# Lesson\nWarehouse content.\n")
    return wh


@pytest.fixture
def project_with_conflict(tmp_path, warehouse_with_knowledge, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    runner = CliRunner()
    runner.invoke(
        main, ["warehouse", "connect", "--path", str(warehouse_with_knowledge)]
    )
    beacon_yaml = project / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge:\n    - knowledge/lesson.md\n  skills: []\n  contexts: []\n"
    )
    runner.invoke(main, ["sync", "--skip-git-check"])

    # Modify the local artifact to create a conflict
    local_file = project / ".agentic-beacon" / "artifacts" / "knowledge" / "lesson.md"
    local_file.write_text("# Lesson\nLocally modified.\n")

    return project, warehouse_with_knowledge, runner, local_file


def test_tc1_preserve_skips_conflict_no_prompt(project_with_conflict):
    """TC1: --preserve, file differs → skipped without prompt."""
    project, warehouse, runner, local_file = project_with_conflict

    result = runner.invoke(main, ["install", "knowledge/lesson.md", "--preserve"])

    assert result.exit_code == 0
    # File should NOT be overwritten
    assert "Locally modified" in local_file.read_text()


def test_tc2_force_overwrites_without_prompt(project_with_conflict):
    """TC2: --force, file differs → overwritten without prompt."""
    project, warehouse, runner, local_file = project_with_conflict

    result = runner.invoke(main, ["install", "knowledge/lesson.md", "--force"])

    assert result.exit_code == 0
    # File should be overwritten with warehouse content
    assert "Warehouse content" in local_file.read_text()


def test_tc3_force_and_preserve_mutual_exclusion(tmp_path, monkeypatch):
    """TC3: --force + --preserve → exits 1 with mutual-exclusion error."""
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    runner = CliRunner()
    result = runner.invoke(
        main, ["install", "knowledge/lesson.md", "--force", "--preserve"]
    )

    assert result.exit_code == 1
    assert "mutually exclusive" in result.output.lower()


def test_tc4_no_flags_noninteractive_conflict_blocked(project_with_conflict):
    """TC4: No flags, file differs, non-interactive → soft block (exit 1)."""
    project, warehouse, runner, local_file = project_with_conflict

    # CliRunner is non-interactive by default
    result = runner.invoke(main, ["install", "knowledge/lesson.md"])

    assert result.exit_code == 1
    # File should NOT be overwritten
    assert "Locally modified" in local_file.read_text()
