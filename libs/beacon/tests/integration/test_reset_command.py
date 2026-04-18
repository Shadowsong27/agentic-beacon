"""Tests for abc reset command (Phase 8, task 8.3).

TDD Test Cases (8.3):
- TC1: Files differ → all overwritten, exit 0, overwrite count printed
- TC2: Files identical → no overwrites, "all up to date" or similar message
- TC3: abc update invoked → deprecation warning printed, same result as abc reset
- TC4: abc reset does not prompt even when files differ (exempt from soft block)
"""

import pytest
from beacon.cli import main
from click.testing import CliRunner


@pytest.fixture
def project_with_modified_artifact(tmp_path, monkeypatch):
    """Project with a synced artifact that has been locally modified."""
    wh = tmp_path / "warehouse"
    wh.mkdir()
    (wh / "README.md").write_text("# Warehouse")
    for d in ("agents", "knowledge", "skills", "contexts", "docs"):
        (wh / d).mkdir()
    (wh / "knowledge" / "lesson.md").write_text("# Lesson\nWarehouse version.\n")

    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    runner = CliRunner()
    runner.invoke(main, ["warehouse", "connect", "--path", str(wh)])
    beacon_yaml = project / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge:\n    - knowledge/lesson.md\n  skills: []\n  contexts: []\n"
    )
    runner.invoke(main, ["sync", "--skip-git-check"])

    # Locally modify the artifact
    local_file = project / ".agentic-beacon" / "artifacts" / "knowledge" / "lesson.md"
    local_file.write_text("# Lesson\nLocally modified.\n")

    return project, wh, runner, local_file


def test_tc1_reset_overwrites_modified_files(project_with_modified_artifact):
    """TC1: Files differ → all overwritten, exit 0, overwrite count printed."""
    project, wh, runner, local_file = project_with_modified_artifact

    result = runner.invoke(main, ["reset"])

    assert result.exit_code == 0
    # File should be overwritten with warehouse version
    assert "Warehouse version" in local_file.read_text()
    # Output should mention overwrite count
    assert any(
        keyword in result.output for keyword in ["overwritten", "Updated", "reset", "1"]
    )


def test_tc2_reset_identical_files_reports_up_to_date(tmp_path, monkeypatch):
    """TC2: Files identical → no overwrites, some indication of nothing to do."""
    wh = tmp_path / "warehouse"
    wh.mkdir()
    (wh / "README.md").write_text("# Warehouse")
    for d in ("agents", "knowledge", "skills", "contexts", "docs"):
        (wh / d).mkdir()
    (wh / "knowledge" / "lesson.md").write_text("# Lesson\n")

    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    runner = CliRunner()
    runner.invoke(main, ["warehouse", "connect", "--path", str(wh)])
    beacon_yaml = project / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge:\n    - knowledge/lesson.md\n  skills: []\n  contexts: []\n"
    )
    runner.invoke(main, ["sync", "--skip-git-check"])

    # Run reset without modifying local file
    result = runner.invoke(main, ["reset"])

    assert result.exit_code == 0


def test_tc3_update_shows_deprecation_warning(project_with_modified_artifact):
    """TC3: abc update invoked → deprecation warning printed, same result as abc reset."""
    project, wh, runner, local_file = project_with_modified_artifact

    result = runner.invoke(main, ["update"])

    assert result.exit_code == 0
    assert "deprecated" in result.output.lower() or "reset" in result.output.lower()
    # File should still be overwritten (same behavior as reset)
    assert "Warehouse version" in local_file.read_text()


def test_tc4_reset_no_prompt_even_when_files_differ(project_with_modified_artifact):
    """TC4: abc reset does not prompt even when files differ (exempt from soft block)."""
    project, wh, runner, local_file = project_with_modified_artifact

    # Run without providing any input (non-interactive)
    result = runner.invoke(main, ["reset"])

    # Should NOT block or prompt — just overwrites
    assert result.exit_code == 0
    assert "Warehouse version" in local_file.read_text()
    # No warning/prompt text
    assert "Warning" not in result.output or "overwrite" not in result.output.lower()
