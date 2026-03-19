"""Tests for warehouse git cleanliness check on abc sync and abc contribute."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from beacon.cli import _check_warehouse_git_clean, main
from click.testing import CliRunner

# ========== Unit tests for _check_warehouse_git_clean ==========


def test_clean_repo_returns_none(tmp_path):
    """Clean warehouse (empty porcelain output) → returns None."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        result = _check_warehouse_git_clean(tmp_path)
    assert result is None


def test_dirty_repo_returns_error_message(tmp_path):
    """Dirty warehouse (non-empty porcelain output) → returns error message."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=" M knowledge/file.md\n", returncode=0)
        result = _check_warehouse_git_clean(tmp_path)
    assert result is not None
    assert "uncommitted changes" in result
    assert "--skip-git-check" in result


def test_no_git_dir_returns_none(tmp_path):
    """Warehouse without .git directory → returns None (skip silently)."""
    result = _check_warehouse_git_clean(tmp_path)
    assert result is None


def test_git_not_installed_returns_none(tmp_path, capsys):
    """git binary not found → returns None (skip with warning)."""
    (tmp_path / ".git").mkdir()
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = _check_warehouse_git_clean(tmp_path)
    assert result is None


def test_git_timeout_returns_none(tmp_path):
    """git status times out → returns None (skip with warning)."""
    (tmp_path / ".git").mkdir()
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 10)):
        result = _check_warehouse_git_clean(tmp_path)
    assert result is None


def test_error_message_contains_warehouse_path(tmp_path):
    """Error message includes a recognisable warehouse path."""
    (tmp_path / ".git").mkdir()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="M  file.md\n", returncode=0)
        result = _check_warehouse_git_clean(tmp_path)
    assert result is not None
    # Path may be abbreviated with ~ for home dir; either way it should appear
    short = str(tmp_path).replace(str(Path.home()), "~")
    assert short in result


# ========== Shared fixture ==========


@pytest.fixture
def connected_project(tmp_path, monkeypatch):
    """Project connected to a warehouse, with beacon.yaml configured."""
    monkeypatch.chdir(tmp_path)

    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    for d in ("contexts", "knowledge", "skills", "docs"):
        (warehouse / d).mkdir()
    (warehouse / "README.md").write_text("# Warehouse")
    knowledge_file = warehouse / "knowledge" / "lesson.md"
    knowledge_file.write_text("# Lesson\n")

    beacon_dir = tmp_path / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "config.toml").write_text(
        f'[warehouse]\nlocal_path = "{warehouse}"\n'
    )
    (beacon_dir / "beacon.yaml").write_text(
        "artifacts:\n  knowledge:\n    - knowledge/lesson.md\n  skills: []\n  contexts: []\n"
    )

    return {"project": tmp_path, "warehouse": warehouse, "beacon_dir": beacon_dir}


# ========== abc sync integration tests ==========


def test_sync_blocked_when_warehouse_dirty(connected_project):
    """abc sync exits with error when warehouse has uncommitted changes."""
    runner = CliRunner()
    warehouse = connected_project["warehouse"]
    (warehouse / ".git").mkdir()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout=" M knowledge/lesson.md\n", returncode=0
        )
        result = runner.invoke(main, ["sync"])

    assert result.exit_code != 0
    assert "uncommitted changes" in result.output


def test_sync_proceeds_when_warehouse_clean(connected_project):
    """abc sync proceeds when warehouse git tree is clean."""
    runner = CliRunner()
    warehouse = connected_project["warehouse"]
    (warehouse / ".git").mkdir()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        result = runner.invoke(main, ["sync"])

    assert result.exit_code == 0


def test_sync_skip_git_check_bypasses_block(connected_project):
    """abc sync --skip-git-check proceeds even when warehouse is dirty."""
    runner = CliRunner()
    warehouse = connected_project["warehouse"]
    (warehouse / ".git").mkdir()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout=" M knowledge/lesson.md\n", returncode=0
        )
        result = runner.invoke(main, ["sync", "--skip-git-check"])

    assert result.exit_code == 0


def test_sync_dry_run_bypasses_git_check(connected_project):
    """abc sync --dry-run skips the git check entirely."""
    runner = CliRunner()
    warehouse = connected_project["warehouse"]
    (warehouse / ".git").mkdir()

    # subprocess.run should NOT be called for the git check during dry-run
    with patch("beacon.cli._check_warehouse_git_clean") as mock_check:
        result = runner.invoke(main, ["sync", "--dry-run"])

    mock_check.assert_not_called()
    assert result.exit_code == 0


def test_sync_no_git_dir_proceeds(connected_project):
    """abc sync proceeds silently when warehouse has no .git directory."""
    runner = CliRunner()
    # No .git dir created — check is skipped
    result = runner.invoke(main, ["sync"])
    assert result.exit_code == 0


# ========== abc contribute integration tests ==========


@pytest.fixture
def connected_project_with_artifact(connected_project):
    """Extends connected_project with a synced local artifact ready to contribute."""
    beacon_dir = connected_project["beacon_dir"]
    artifacts_knowledge = beacon_dir / "artifacts" / "knowledge"
    artifacts_knowledge.mkdir(parents=True)
    (artifacts_knowledge / "lesson.md").write_text("# Lesson\n\nModified locally.\n")
    return connected_project


def test_contribute_blocked_when_warehouse_dirty(connected_project_with_artifact):
    """abc contribute exits with error when warehouse has uncommitted changes."""
    runner = CliRunner()
    warehouse = connected_project_with_artifact["warehouse"]
    (warehouse / ".git").mkdir()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout=" M knowledge/lesson.md\n", returncode=0
        )
        result = runner.invoke(main, ["contribute", "knowledge/lesson.md"])

    assert result.exit_code != 0
    assert "uncommitted changes" in result.output


def test_contribute_proceeds_when_warehouse_clean(connected_project_with_artifact):
    """abc contribute proceeds when warehouse git tree is clean."""
    runner = CliRunner()
    warehouse = connected_project_with_artifact["warehouse"]
    (warehouse / ".git").mkdir()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        result = runner.invoke(main, ["contribute", "knowledge/lesson.md"])

    assert result.exit_code == 0


def test_contribute_skip_git_check_bypasses_block(connected_project_with_artifact):
    """abc contribute --skip-git-check proceeds even when warehouse is dirty."""
    runner = CliRunner()
    warehouse = connected_project_with_artifact["warehouse"]
    (warehouse / ".git").mkdir()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout=" M knowledge/lesson.md\n", returncode=0
        )
        result = runner.invoke(
            main, ["contribute", "knowledge/lesson.md", "--skip-git-check"]
        )

    assert result.exit_code == 0


def test_contribute_dry_run_bypasses_git_check(connected_project_with_artifact):
    """abc contribute --dry-run skips the git check entirely."""
    runner = CliRunner()
    warehouse = connected_project_with_artifact["warehouse"]
    (warehouse / ".git").mkdir()

    with patch("beacon.cli._check_warehouse_git_clean") as mock_check:
        result = runner.invoke(main, ["contribute", "knowledge/lesson.md", "--dry-run"])

    mock_check.assert_not_called()
    assert result.exit_code == 0


def test_contribute_all_blocked_when_warehouse_dirty(connected_project_with_artifact):
    """abc contribute --all exits with error when warehouse has uncommitted changes."""
    runner = CliRunner()
    warehouse = connected_project_with_artifact["warehouse"]
    (warehouse / ".git").mkdir()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="?? new-file.md\n", returncode=0)
        result = runner.invoke(main, ["contribute", "--all"])

    assert result.exit_code != 0
    assert "uncommitted changes" in result.output


def test_contribute_no_git_dir_proceeds(connected_project_with_artifact):
    """abc contribute proceeds silently when warehouse has no .git directory."""
    runner = CliRunner()
    # No .git dir — check skipped
    result = runner.invoke(main, ["contribute", "knowledge/lesson.md"])
    assert result.exit_code == 0
