"""Integration tests: abc sync warehouse git cleanliness check.

Uses a real git repository in the warehouse — no mocking of subprocess.
All tests are marked `integration` and can be run independently:

    pytest -m integration
"""

import subprocess

import pytest
from beacon.cli import main
from click.testing import CliRunner

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd) -> None:
    """Run a git command in cwd, raising on failure."""
    subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=True,
        capture_output=True,
    )


@pytest.fixture
def warehouse_git(tmp_path):
    """A valid warehouse directory backed by a real git repository with one clean commit."""
    wh = tmp_path / "warehouse"
    wh.mkdir()

    for d in ("contexts", "knowledge", "skills", "docs"):
        (wh / d).mkdir()
    (wh / "README.md").write_text("# Test Warehouse\n")
    (wh / "knowledge" / "lesson.md").write_text("# Lesson\nOriginal content.\n")

    _git(["init"], wh)
    _git(["config", "user.email", "test@test.com"], wh)
    _git(["config", "user.name", "Test"], wh)
    _git(["add", "."], wh)
    _git(["commit", "-m", "initial commit"], wh)

    return wh


@pytest.fixture
def connected_project(tmp_path, warehouse_git, monkeypatch):
    """Project directory wired to warehouse_git with beacon.yaml configured."""
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    beacon_dir = project / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "config.toml").write_text(
        f'[warehouse]\nlocal_path = "{warehouse_git}"\n'
    )
    (beacon_dir / "beacon.yaml").write_text(
        "artifacts:\n"
        "  knowledge:\n"
        "    - knowledge/lesson.md\n"
        "  skills: []\n"
        "  contexts: []\n"
    )

    return project, warehouse_git, CliRunner()


# ---------------------------------------------------------------------------
# Clean warehouse — sync proceeds
# ---------------------------------------------------------------------------


def test_sync_proceeds_when_warehouse_is_clean(connected_project):
    """abc sync succeeds when the warehouse working tree has no uncommitted changes."""
    project, warehouse, runner = connected_project

    result = runner.invoke(main, ["sync"])

    assert result.exit_code == 0
    assert (
        project / ".agentic-beacon" / "artifacts" / "knowledge" / "lesson.md"
    ).exists()


# ---------------------------------------------------------------------------
# Branch guard — warehouse must be on main/master branch
# ---------------------------------------------------------------------------


def test_sync_blocked_when_warehouse_on_feature_branch(connected_project):
    """abc sync exits with an error when the warehouse is on a non-main branch."""
    project, warehouse, runner = connected_project

    _git(["checkout", "-b", "feat/experimental"], warehouse)

    result = runner.invoke(main, ["sync"])

    assert result.exit_code != 0
    assert "feat/experimental" in result.output
    assert "--skip-git-check" in result.output


def test_sync_blocked_when_warehouse_in_detached_head(connected_project):
    """abc sync exits with an error when the warehouse is in detached HEAD state."""
    project, warehouse, runner = connected_project

    sha_result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(warehouse),
        capture_output=True,
        text=True,
        check=True,
    )
    sha = sha_result.stdout.strip()
    _git(["checkout", sha], warehouse)

    result = runner.invoke(main, ["sync"])

    assert result.exit_code != 0
    assert "detached" in result.output
    assert "--skip-git-check" in result.output


def test_sync_skip_git_check_bypasses_branch_guard(connected_project):
    """abc sync --skip-git-check proceeds even when warehouse is on a feature branch."""
    project, warehouse, runner = connected_project

    _git(["checkout", "-b", "feat/experimental"], warehouse)

    result = runner.invoke(main, ["sync", "--skip-git-check"])

    assert result.exit_code == 0
    synced = project / ".agentic-beacon" / "artifacts" / "knowledge" / "lesson.md"
    assert synced.exists()


def test_sync_dry_run_bypasses_branch_guard(connected_project):
    """abc sync --dry-run does not check the branch and exits 0."""
    project, warehouse, runner = connected_project

    _git(["checkout", "-b", "feat/experimental"], warehouse)

    result = runner.invoke(main, ["sync", "--dry-run"])

    assert result.exit_code == 0
    assert "feat/experimental" not in result.output


def test_sync_proceeds_after_switching_back_to_main(connected_project):
    """abc sync succeeds once the warehouse is switched back to main."""
    project, warehouse, runner = connected_project

    _git(["checkout", "-b", "feat/experimental"], warehouse)
    blocked = runner.invoke(main, ["sync"])
    assert blocked.exit_code != 0

    _git(["checkout", "main"], warehouse)
    result = runner.invoke(main, ["sync"])

    assert result.exit_code == 0
    synced = project / ".agentic-beacon" / "artifacts" / "knowledge" / "lesson.md"
    assert synced.exists()


def test_sync_proceeds_on_master_branch(tmp_path, monkeypatch):
    """abc sync proceeds when the warehouse is on 'master' (accepted alias for main)."""
    wh = tmp_path / "warehouse"
    wh.mkdir()
    for d in ("contexts", "knowledge", "skills", "docs"):
        (wh / d).mkdir()
    (wh / "README.md").write_text("# Warehouse\n")
    (wh / "knowledge" / "lesson.md").write_text("# Lesson\n")

    subprocess.run(
        ["git", "init", "-b", "master"],
        cwd=str(wh),
        check=True,
        capture_output=True,
    )
    _git(["config", "user.email", "test@test.com"], wh)
    _git(["config", "user.name", "Test"], wh)
    _git(["add", "."], wh)
    _git(["commit", "-m", "initial"], wh)

    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    beacon_dir = project / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "config.toml").write_text(f'[warehouse]\nlocal_path = "{wh}"\n')
    (beacon_dir / "beacon.yaml").write_text(
        "artifacts:\n  knowledge:\n    - knowledge/lesson.md\n  skills: []\n  contexts: []\n"
    )

    result = CliRunner().invoke(main, ["sync"])

    assert result.exit_code == 0
    assert (
        project / ".agentic-beacon" / "artifacts" / "knowledge" / "lesson.md"
    ).exists()


# Unstaged modification — sync blocked
# ---------------------------------------------------------------------------


def test_sync_blocked_on_unstaged_modification(connected_project):
    """abc sync exits with an error when the warehouse has an unstaged file modification."""
    project, warehouse, runner = connected_project

    # Modify a tracked file without staging
    (warehouse / "knowledge" / "lesson.md").write_text("# Lesson\nModified.\n")

    result = runner.invoke(main, ["sync"])

    assert result.exit_code != 0
    assert "uncommitted changes" in result.output


# ---------------------------------------------------------------------------
# Staged modification — sync blocked
# ---------------------------------------------------------------------------


def test_sync_blocked_on_staged_modification(connected_project):
    """abc sync exits with an error when the warehouse has staged but uncommitted changes."""
    project, warehouse, runner = connected_project

    (warehouse / "knowledge" / "lesson.md").write_text("# Lesson\nStaged change.\n")
    _git(["add", "knowledge/lesson.md"], warehouse)

    result = runner.invoke(main, ["sync"])

    assert result.exit_code != 0
    assert "uncommitted changes" in result.output


# ---------------------------------------------------------------------------
# Untracked new file — sync blocked
# ---------------------------------------------------------------------------


def test_sync_blocked_on_untracked_new_file(connected_project):
    """abc sync exits with an error when the warehouse has an untracked new file."""
    project, warehouse, runner = connected_project

    (warehouse / "knowledge" / "new-article.md").write_text("# New\n")

    result = runner.invoke(main, ["sync"])

    assert result.exit_code != 0
    assert "uncommitted changes" in result.output


# ---------------------------------------------------------------------------
# --skip-git-check bypasses the block
# ---------------------------------------------------------------------------


def test_sync_skip_git_check_proceeds_despite_dirty_warehouse(connected_project):
    """abc sync --skip-git-check completes even when the warehouse is dirty."""
    project, warehouse, runner = connected_project

    (warehouse / "knowledge" / "lesson.md").write_text("# Lesson\nDirty.\n")

    result = runner.invoke(main, ["sync", "--skip-git-check"])

    assert result.exit_code == 0
    # The file is still copied (from the dirty warehouse state)
    synced = project / ".agentic-beacon" / "artifacts" / "knowledge" / "lesson.md"
    assert synced.exists()


# ---------------------------------------------------------------------------
# --dry-run bypasses the git check entirely
# ---------------------------------------------------------------------------


def test_sync_dry_run_bypasses_git_check(connected_project):
    """abc sync --dry-run does not perform the git check and exits 0."""
    project, warehouse, runner = connected_project

    (warehouse / "knowledge" / "lesson.md").write_text("# Lesson\nDirty.\n")

    result = runner.invoke(main, ["sync", "--dry-run"])

    assert result.exit_code == 0
    assert "uncommitted changes" not in result.output


# ---------------------------------------------------------------------------
# After committing the dirty changes — sync proceeds again
# ---------------------------------------------------------------------------


def test_sync_proceeds_after_committing_warehouse_changes(connected_project):
    """abc sync succeeds once previously dirty warehouse changes are committed."""
    project, warehouse, runner = connected_project

    # Make dirty
    (warehouse / "knowledge" / "lesson.md").write_text("# Lesson\nUpdated.\n")

    # Verify blocked
    blocked = runner.invoke(main, ["sync"])
    assert blocked.exit_code != 0

    # Commit the changes
    _git(["add", "."], warehouse)
    _git(["commit", "-m", "update lesson"], warehouse)

    # Now sync should proceed
    result = runner.invoke(main, ["sync"])
    assert result.exit_code == 0
    synced = project / ".agentic-beacon" / "artifacts" / "knowledge" / "lesson.md"
    assert "Updated." in synced.read_text()


# ---------------------------------------------------------------------------
# Non-git warehouse — check skipped, sync proceeds
# ---------------------------------------------------------------------------


def test_sync_proceeds_when_warehouse_has_no_git(tmp_path, monkeypatch):
    """abc sync proceeds silently when the warehouse directory has no .git folder."""
    # Plain warehouse — no git init
    wh = tmp_path / "warehouse"
    wh.mkdir()
    for d in ("contexts", "knowledge", "skills", "docs"):
        (wh / d).mkdir()
    (wh / "README.md").write_text("# Warehouse\n")
    (wh / "knowledge" / "lesson.md").write_text("# Lesson\n")

    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    beacon_dir = project / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "config.toml").write_text(f'[warehouse]\nlocal_path = "{wh}"\n')
    (beacon_dir / "beacon.yaml").write_text(
        "artifacts:\n"
        "  knowledge:\n"
        "    - knowledge/lesson.md\n"
        "  skills: []\n"
        "  contexts: []\n"
    )

    result = CliRunner().invoke(main, ["sync"])

    assert result.exit_code == 0
    assert (
        project / ".agentic-beacon" / "artifacts" / "knowledge" / "lesson.md"
    ).exists()
