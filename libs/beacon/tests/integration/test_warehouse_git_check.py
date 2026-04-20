"""Tests for warehouse git cleanliness check on abc sync and abc contribute."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from beacon.cli.main import main
from beacon.domains.distribution.state import check_sync_state, write_sync_state
from beacon.domains.warehouse.git_health import (
    GitHealthResult,
    check_warehouse_git_clean,
)
from click.testing import CliRunner

# ========== Unit tests for check_warehouse_git_clean ==========


def test_clean_repo_returns_ok(tmp_path):
    """Clean warehouse (empty porcelain output) → ok=True."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        result = check_warehouse_git_clean(tmp_path)
    assert result.ok is True


def test_dirty_repo_returns_error_message(tmp_path):
    """Dirty warehouse (non-empty porcelain output) → ok=False with error message."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=" M knowledge/file.md\n", returncode=0)
        result = check_warehouse_git_clean(tmp_path)
    assert result.ok is False
    assert "uncommitted changes" in result.error_message


def test_no_git_dir_returns_ok(tmp_path):
    """Warehouse without .git directory → ok=True (skip silently)."""
    result = check_warehouse_git_clean(tmp_path)
    assert result.ok is True


def test_git_not_installed_returns_ok(tmp_path, capsys):
    """git binary not found → ok=True (skip with warning)."""
    (tmp_path / ".git").mkdir()
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = check_warehouse_git_clean(tmp_path)
    assert result.ok is True
    assert result.warning_message is not None


def test_git_timeout_returns_ok(tmp_path):
    """git status times out → ok=True (skip with warning)."""
    (tmp_path / ".git").mkdir()
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 10)):
        result = check_warehouse_git_clean(tmp_path)
    assert result.ok is True
    assert result.warning_message is not None


def test_error_message_contains_warehouse_path(tmp_path):
    """Error message includes a recognisable warehouse path."""
    (tmp_path / ".git").mkdir()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="M  file.md\n", returncode=0)
        result = check_warehouse_git_clean(tmp_path)
    assert result.ok is False
    # Path may be abbreviated with ~ for home dir; either way it should appear
    short = str(tmp_path).replace(str(Path.home()), "~")
    assert short in result.error_message


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

    with (
        patch("subprocess.run") as mock_run,
        patch(
            "beacon.domains.distribution.orchestrator.check_warehouse_on_main_branch",
            return_value=GitHealthResult(ok=True),
        ),
    ):
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
    with patch(
        "beacon.domains.distribution.orchestrator.check_warehouse_git_clean"
    ) as mock_check:
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

    with (
        patch("subprocess.run") as mock_run,
        patch("beacon.cli.contribute.check_sync_state", return_value=None),
    ):
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        result = runner.invoke(main, ["contribute", "knowledge/lesson.md"], input="y\n")

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
            main,
            ["contribute", "knowledge/lesson.md", "--skip-git-check"],
            input="y\n",
        )

    assert result.exit_code == 0


def test_contribute_dry_run_bypasses_git_check(connected_project_with_artifact):
    """abc contribute --dry-run skips the git check entirely."""
    runner = CliRunner()
    warehouse = connected_project_with_artifact["warehouse"]
    (warehouse / ".git").mkdir()

    with patch("beacon.cli.contribute.check_warehouse_git_clean") as mock_check:
        result = runner.invoke(main, ["contribute", "knowledge/lesson.md", "--dry-run"])

    mock_check.assert_not_called()
    assert result.exit_code == 0


def test_contribute_all_blocked_when_warehouse_dirty(connected_project_with_artifact):
    """abc contribute (no file) exits with error when warehouse has uncommitted changes."""
    runner = CliRunner()
    warehouse = connected_project_with_artifact["warehouse"]
    (warehouse / ".git").mkdir()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="?? new-file.md\n", returncode=0)
        result = runner.invoke(main, ["contribute"])

    assert result.exit_code != 0
    assert "uncommitted changes" in result.output


def test_contribute_no_git_dir_proceeds(connected_project_with_artifact):
    """abc contribute proceeds silently when warehouse has no .git directory."""
    runner = CliRunner()
    # No .git dir — check skipped
    result = runner.invoke(main, ["contribute", "knowledge/lesson.md"], input="y\n")
    assert result.exit_code == 0


# ========== Unit tests for Gap 1: remote-behind check ==========


def test_clean_up_to_date_repo_returns_ok(tmp_path):
    """Clean warehouse that is current with remote → ok=True."""
    (tmp_path / ".git").mkdir()
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=0),  # git status --porcelain
            MagicMock(stdout="", returncode=0),  # git fetch --quiet
            MagicMock(stdout="0\n", returncode=0),  # git rev-list --count HEAD..@{u}
        ]
        result = check_warehouse_git_clean(tmp_path)
    assert result.ok is True


def test_behind_remote_returns_error(tmp_path):
    """Warehouse behind its remote by N commits → ok=False with error message."""
    (tmp_path / ".git").mkdir()
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=0),  # git status --porcelain (clean)
            MagicMock(stdout="", returncode=0),  # git fetch --quiet
            MagicMock(stdout="3\n", returncode=0),  # 3 commits behind
        ]
        result = check_warehouse_git_clean(tmp_path)
    assert result.ok is False
    assert "behind" in result.error_message
    assert "3" in result.error_message
    assert "git pull" in result.error_message
    assert "--skip-git-check" in result.hint


def test_no_upstream_configured_returns_ok(tmp_path):
    """rev-list fails (no upstream) → ok=True, skip silently."""
    (tmp_path / ".git").mkdir()
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=0),  # git status --porcelain (clean)
            MagicMock(stdout="", returncode=0),  # git fetch --quiet
            MagicMock(stdout="", returncode=128),  # no upstream → non-zero exit
        ]
        result = check_warehouse_git_clean(tmp_path)
    assert result.ok is True


def test_fetch_timeout_returns_ok_with_warning(tmp_path, capsys):
    """git fetch timeout → ok=True (skip with warning)."""
    (tmp_path / ".git").mkdir()
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=0),  # git status --porcelain
            subprocess.TimeoutExpired("git", 15),  # git fetch times out
        ]
        result = check_warehouse_git_clean(tmp_path)
    assert result.ok is True


def test_write_sync_state_records_sha(tmp_path):
    """write_sync_state writes warehouse HEAD SHA to .sync-state file."""
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    (warehouse / ".git").mkdir()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="abc123\n", returncode=0)
        write_sync_state(artifacts_dir, warehouse)

    state_file = artifacts_dir / ".sync-state"
    assert state_file.exists()
    assert state_file.read_text().strip() == "abc123"


def test_write_sync_state_skips_when_no_git(tmp_path):
    """write_sync_state does nothing when warehouse has no git repo."""
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    # No .git dir

    write_sync_state(artifacts_dir, warehouse)

    state_file = artifacts_dir / ".sync-state"
    assert not state_file.exists()


def test_check_sync_state_returns_none_when_sha_matches(tmp_path):
    """check_sync_state returns None when recorded SHA matches warehouse HEAD."""
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    (artifacts_dir / "knowledge").mkdir()
    (artifacts_dir / "knowledge" / "file.md").write_text("content")
    (artifacts_dir / ".sync-state").write_text("deadbeef\n")
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    (warehouse / ".git").mkdir()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="deadbeef\n", returncode=0)
        result = check_sync_state(artifacts_dir, warehouse)

    assert result is None


def test_check_sync_state_warns_when_sha_differs(tmp_path):
    """check_sync_state returns error when snapshot is based on older warehouse commit."""
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    (artifacts_dir / "knowledge").mkdir()
    (artifacts_dir / "knowledge" / "file.md").write_text("content")
    (artifacts_dir / ".sync-state").write_text("oldsha\n")
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    (warehouse / ".git").mkdir()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="newsha\n", returncode=0)
        result = check_sync_state(artifacts_dir, warehouse)

    assert result is not None
    assert "stale" in result or "older" in result
    assert "abc sync" in result
    assert "--skip-git-check" in result


def test_check_sync_state_warns_when_no_state_file(tmp_path):
    """check_sync_state warns when artifacts exist but no .sync-state file."""
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    (artifacts_dir / "knowledge").mkdir()
    (artifacts_dir / "knowledge" / "file.md").write_text("content")
    # No .sync-state file
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    (warehouse / ".git").mkdir()

    result = check_sync_state(artifacts_dir, warehouse)

    assert result is not None
    assert "abc sync" in result


def test_check_sync_state_warns_when_artifacts_empty(tmp_path):
    """check_sync_state warns when artifacts directory is empty (sync never run)."""
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    # Empty — no files, no .sync-state
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    (warehouse / ".git").mkdir()

    result = check_sync_state(artifacts_dir, warehouse)

    assert result is not None
    assert "abc sync" in result


def test_check_sync_state_returns_none_when_no_git(tmp_path):
    """check_sync_state returns None when warehouse has no git (check skipped)."""
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    # No .git dir

    result = check_sync_state(artifacts_dir, warehouse)

    assert result is None


# ========== Integration tests for Gap 2: contribute blocked on stale snapshot ==========


def test_contribute_blocked_when_sync_state_stale(connected_project_with_artifact):
    """abc contribute exits when the sync snapshot is stale."""
    runner = CliRunner()
    beacon_dir = connected_project_with_artifact["beacon_dir"]
    warehouse = connected_project_with_artifact["warehouse"]
    (warehouse / ".git").mkdir()

    # Write a stale .sync-state (old SHA)
    artifacts_dir = beacon_dir / "artifacts"
    (artifacts_dir / ".sync-state").write_text("oldsha\n")

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=0),  # git status --porcelain
            MagicMock(stdout="", returncode=0),  # git fetch
            MagicMock(stdout="0\n", returncode=0),  # rev-list (up to date)
            MagicMock(stdout="newsha\n", returncode=0),  # rev-parse HEAD (sync check)
        ]
        result = runner.invoke(main, ["contribute", "knowledge/lesson.md"])

    assert result.exit_code != 0
    assert "abc sync" in result.output


def test_contribute_blocked_when_no_sync_run(connected_project):
    """abc contribute exits when artifacts directory is empty (sync never run)."""
    runner = CliRunner()
    warehouse = connected_project["warehouse"]
    (warehouse / ".git").mkdir()
    # No artifacts directory populated

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=0),  # git status --porcelain
            MagicMock(stdout="", returncode=0),  # git fetch
            MagicMock(stdout="0\n", returncode=0),  # rev-list (up to date)
        ]
        result = runner.invoke(main, ["contribute", "knowledge/lesson.md"])

    assert result.exit_code != 0
    assert "abc sync" in result.output


def test_contribute_skip_git_check_bypasses_sync_state(connected_project_with_artifact):
    """abc contribute --skip-git-check bypasses sync-state check."""
    runner = CliRunner()
    beacon_dir = connected_project_with_artifact["beacon_dir"]
    warehouse = connected_project_with_artifact["warehouse"]
    (warehouse / ".git").mkdir()

    # Write a stale .sync-state (old SHA)
    artifacts_dir = beacon_dir / "artifacts"
    (artifacts_dir / ".sync-state").write_text("oldsha\n")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        result = runner.invoke(
            main,
            ["contribute", "knowledge/lesson.md", "--skip-git-check"],
            input="y\n",
        )

    assert result.exit_code == 0


# ========== Unit tests for Gap 3: targeted git add ==========


def test_auto_git_uses_targeted_add(tmp_path):
    """_auto_git_contribute stages only contributed files, not all warehouse files."""
    from beacon.domains.contribution.contributor import auto_git_contribute

    (tmp_path / ".git").mkdir()
    contributed = [
        ("knowledge/lesson.md", "modified"),
        ("contexts/global.md", "added"),
    ]

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        auto_git_contribute(tmp_path, contributed)

    # Find the git add call
    add_call = next(
        (c for c in mock_run.call_args_list if "add" in c.args[0]),
        None,
    )
    assert add_call is not None
    args = add_call.args[0]
    # Should be targeted: git add -- knowledge/lesson.md contexts/global.md
    assert "--" in args
    assert "knowledge/lesson.md" in args
    assert "contexts/global.md" in args
    # Must NOT use git add .
    assert "." not in args[args.index("--") :]


# ========== Unit tests for check_warehouse_on_main_branch ==========

from beacon.domains.warehouse.git_health import (  # noqa: E402
    check_warehouse_on_main_branch,
)


def test_on_main_branch_returns_ok(tmp_path):
    """Warehouse on 'main' → ok=True."""
    (tmp_path / ".git").mkdir()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="main\n", returncode=0)
        result = check_warehouse_on_main_branch(tmp_path)
    assert result.ok is True


def test_on_master_branch_returns_ok(tmp_path):
    """Warehouse on 'master' → ok=True (accepted alias)."""
    (tmp_path / ".git").mkdir()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="master\n", returncode=0)
        result = check_warehouse_on_main_branch(tmp_path)
    assert result.ok is True


def test_on_feature_branch_returns_error(tmp_path):
    """Warehouse on a non-main branch → ok=False with error message."""
    (tmp_path / ".git").mkdir()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="feat/my-experiment\n", returncode=0)
        result = check_warehouse_on_main_branch(tmp_path)
    assert result.ok is False
    assert "feat/my-experiment" in result.error_message
    assert "git checkout main" in result.error_message


def test_detached_head_returns_error(tmp_path):
    """Warehouse in detached HEAD state → ok=False with error message."""
    (tmp_path / ".git").mkdir()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", returncode=128)
        result = check_warehouse_on_main_branch(tmp_path)
    assert result.ok is False
    assert "detached" in result.error_message


def test_no_git_dir_returns_ok_branch_check(tmp_path):
    """Warehouse without .git → ok=True (skip silently)."""
    result = check_warehouse_on_main_branch(tmp_path)
    assert result.ok is True


def test_git_not_found_returns_ok_branch_check(tmp_path):
    """git not installed → ok=True (skip silently)."""
    (tmp_path / ".git").mkdir()
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = check_warehouse_on_main_branch(tmp_path)
    assert result.ok is True


# ========== Integration tests: abc sync branch guard ==========


def test_sync_blocked_when_warehouse_on_feature_branch(connected_project):
    """abc sync exits with error when warehouse is on a non-main branch."""
    runner = CliRunner()
    warehouse = connected_project["warehouse"]
    (warehouse / ".git").mkdir()

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=0),  # git status (clean)
            MagicMock(stdout="", returncode=0),  # git fetch
            MagicMock(stdout="0\n", returncode=0),  # rev-list (up to date)
            MagicMock(stdout="feat/my-thing\n", returncode=0),  # symbolic-ref
        ]
        result = runner.invoke(main, ["sync"])

    assert result.exit_code != 0
    assert "feat/my-thing" in result.output
    assert "--skip-git-check" in result.output


def test_sync_proceeds_when_warehouse_on_main(connected_project):
    """abc sync proceeds when warehouse is on main branch."""
    runner = CliRunner()
    warehouse = connected_project["warehouse"]
    (warehouse / ".git").mkdir()

    with (
        patch("subprocess.run") as mock_run,
        patch(
            "beacon.domains.distribution.orchestrator.check_warehouse_on_main_branch",
            return_value=GitHealthResult(ok=True),
        ),
    ):
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        result = runner.invoke(main, ["sync"])

    assert result.exit_code == 0


def test_sync_skip_git_check_bypasses_branch_guard(connected_project):
    """abc sync --skip-git-check bypasses the branch check."""
    runner = CliRunner()
    warehouse = connected_project["warehouse"]
    (warehouse / ".git").mkdir()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="feat/my-thing\n", returncode=0)
        result = runner.invoke(main, ["sync", "--skip-git-check"])

    assert result.exit_code == 0


def test_sync_dry_run_bypasses_branch_guard(connected_project):
    """abc sync --dry-run skips the branch check entirely."""
    runner = CliRunner()
    warehouse = connected_project["warehouse"]
    (warehouse / ".git").mkdir()

    with patch(
        "beacon.domains.distribution.orchestrator.check_warehouse_on_main_branch"
    ) as mock_branch:
        result = runner.invoke(main, ["sync", "--dry-run"])

    mock_branch.assert_not_called()
    assert result.exit_code == 0
