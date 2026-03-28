"""Integration tests: abc contribute warehouse git cleanliness check.

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

    for d in ("agents", "contexts", "knowledge", "skills", "docs"):
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
    """Project with a synced artifact ready to contribute back to warehouse_git."""
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

    # Sync first so local artifact exists
    runner = CliRunner()
    runner.invoke(main, ["sync"])

    # Locally modify the synced artifact so there is something to contribute
    synced = beacon_dir / "artifacts" / "knowledge" / "lesson.md"
    synced.write_text("# Lesson\nImproved locally.\n")

    return project, warehouse_git, runner


# ---------------------------------------------------------------------------
# Clean warehouse — contribute proceeds
# ---------------------------------------------------------------------------


def test_contribute_proceeds_when_warehouse_is_clean(connected_project):
    """abc contribute succeeds when the warehouse working tree is clean."""
    project, warehouse, runner = connected_project

    result = runner.invoke(main, ["contribute", "knowledge/lesson.md"])

    assert result.exit_code == 0
    assert "Improved locally." in (warehouse / "knowledge" / "lesson.md").read_text()


# ---------------------------------------------------------------------------
# Unstaged modification in warehouse — contribute blocked
# ---------------------------------------------------------------------------


def test_contribute_blocked_on_unstaged_warehouse_modification(connected_project):
    """abc contribute exits with an error when the warehouse has an unstaged modification."""
    project, warehouse, runner = connected_project

    # Dirty the warehouse independently of the local artifact
    (warehouse / "knowledge" / "lesson.md").write_text(
        "# Lesson\nSomeone else edited.\n"
    )

    result = runner.invoke(main, ["contribute", "knowledge/lesson.md"])

    assert result.exit_code != 0
    assert "uncommitted changes" in result.output


# ---------------------------------------------------------------------------
# Staged modification in warehouse — contribute blocked
# ---------------------------------------------------------------------------


def test_contribute_blocked_on_staged_warehouse_modification(connected_project):
    """abc contribute exits with an error when the warehouse has staged uncommitted changes."""
    project, warehouse, runner = connected_project

    (warehouse / "knowledge" / "lesson.md").write_text("# Lesson\nStaged.\n")
    _git(["add", "knowledge/lesson.md"], warehouse)

    result = runner.invoke(main, ["contribute", "knowledge/lesson.md"])

    assert result.exit_code != 0
    assert "uncommitted changes" in result.output


# ---------------------------------------------------------------------------
# Untracked file in warehouse — contribute blocked
# ---------------------------------------------------------------------------


def test_contribute_blocked_on_untracked_warehouse_file(connected_project):
    """abc contribute exits with an error when the warehouse contains an untracked file."""
    project, warehouse, runner = connected_project

    (warehouse / "knowledge" / "draft.md").write_text("# Draft\n")

    result = runner.invoke(main, ["contribute", "knowledge/lesson.md"])

    assert result.exit_code != 0
    assert "uncommitted changes" in result.output


# ---------------------------------------------------------------------------
# Default (no file) — blocked on dirty warehouse
# ---------------------------------------------------------------------------


def test_contribute_all_blocked_on_dirty_warehouse(connected_project):
    """abc contribute (no file) is also blocked when the warehouse is dirty."""
    project, warehouse, runner = connected_project

    (warehouse / "knowledge" / "draft.md").write_text("# Draft\n")

    result = runner.invoke(main, ["contribute"])

    assert result.exit_code != 0
    assert "uncommitted changes" in result.output


# ---------------------------------------------------------------------------
# --skip-git-check bypasses the block
# ---------------------------------------------------------------------------


def test_contribute_skip_git_check_proceeds_despite_dirty_warehouse(connected_project):
    """abc contribute --skip-git-check completes even when the warehouse is dirty."""
    project, warehouse, runner = connected_project

    # Dirty the warehouse with an untracked file
    (warehouse / "knowledge" / "draft.md").write_text("# Draft\n")

    result = runner.invoke(
        main, ["contribute", "knowledge/lesson.md", "--skip-git-check"]
    )

    assert result.exit_code == 0
    # The local improvement was written to the warehouse despite dirtiness
    assert "Improved locally." in (warehouse / "knowledge" / "lesson.md").read_text()


# ---------------------------------------------------------------------------
# --dry-run bypasses the git check entirely
# ---------------------------------------------------------------------------


def test_contribute_dry_run_bypasses_git_check(connected_project):
    """abc contribute --dry-run does not perform the git check and exits 0."""
    project, warehouse, runner = connected_project

    # Dirty the warehouse
    (warehouse / "knowledge" / "lesson.md").write_text("# Lesson\nDirty.\n")

    result = runner.invoke(main, ["contribute", "knowledge/lesson.md", "--dry-run"])

    assert result.exit_code == 0
    assert "uncommitted changes" not in result.output
    # Warehouse should be unchanged (dry-run copies nothing)
    assert "Dirty." in (warehouse / "knowledge" / "lesson.md").read_text()


# ---------------------------------------------------------------------------
# After committing dirty warehouse changes — contribute proceeds again
# ---------------------------------------------------------------------------


def test_contribute_proceeds_after_committing_warehouse_changes(connected_project):
    """abc contribute succeeds once dirty warehouse changes are committed and re-synced."""
    project, warehouse, runner = connected_project

    # Dirty the warehouse
    (warehouse / "knowledge" / "unrelated.md").write_text("# Unrelated\n")

    # Verify blocked
    blocked = runner.invoke(main, ["contribute", "knowledge/lesson.md"])
    assert blocked.exit_code != 0

    # Commit the warehouse changes
    _git(["add", "."], warehouse)
    _git(["commit", "-m", "add unrelated"], warehouse)

    # Re-sync so the snapshot is current with the new warehouse HEAD, then
    # re-apply the local modification (sync --force overwrites local changes)
    runner.invoke(main, ["sync", "--force"])
    synced = project / ".agentic-beacon" / "artifacts" / "knowledge" / "lesson.md"
    synced.write_text("# Lesson\nImproved locally.\n")

    # Now contribute should succeed
    result = runner.invoke(main, ["contribute", "knowledge/lesson.md"])
    assert result.exit_code == 0
    assert "Improved locally." in (warehouse / "knowledge" / "lesson.md").read_text()


# ---------------------------------------------------------------------------
# Non-git warehouse — check skipped, contribute proceeds
# ---------------------------------------------------------------------------


def test_contribute_proceeds_when_warehouse_has_no_git(tmp_path, monkeypatch):
    """abc contribute proceeds silently when the warehouse has no .git directory."""
    wh = tmp_path / "warehouse"
    wh.mkdir()
    for d in ("contexts", "knowledge", "skills", "docs"):
        (wh / d).mkdir()
    (wh / "README.md").write_text("# Warehouse\n")
    (wh / "knowledge" / "lesson.md").write_text("# Lesson\nOriginal.\n")

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

    runner = CliRunner()
    runner.invoke(main, ["sync"])

    synced = beacon_dir / "artifacts" / "knowledge" / "lesson.md"
    synced.write_text("# Lesson\nImproved.\n")

    result = runner.invoke(main, ["contribute", "knowledge/lesson.md"])

    assert result.exit_code == 0
    assert "Improved." in (wh / "knowledge" / "lesson.md").read_text()
