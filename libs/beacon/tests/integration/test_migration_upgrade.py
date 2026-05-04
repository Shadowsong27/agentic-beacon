"""Integration test for migration upgrade path.

Covers tasks 7.9 and 8.4: simulates a pre-upgrade project with regular files
and verifies migration to symlinks.
"""

import os
import subprocess

import pytest
from beacon.cli.main import main
from click.testing import CliRunner

pytestmark = pytest.mark.integration


def _git_env():
    """Return git environment with test author info."""
    return {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "t@t.local",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "t@t.local",
    }


@pytest.fixture
def migration_warehouse(tmp_path):
    """Create a warehouse with files for migration tests."""
    wh = tmp_path / "warehouse"
    wh.mkdir()
    env = _git_env()
    subprocess.run(["git", "init"], cwd=wh, env=env, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=wh,
        env=env,
        check=True,
        capture_output=True,
    )

    # Create required warehouse structure
    (wh / "agents").mkdir()
    (wh / "contexts").mkdir()
    (wh / "knowledge").mkdir()
    (wh / "skills").mkdir()
    (wh / "docs").mkdir()
    (wh / "README.md").write_text("# Test Warehouse\n")

    (wh / "knowledge" / "unchanged.md").write_text("# Unchanged\noriginal\n")
    (wh / "knowledge" / "modified_contrib.md").write_text("# Contrib\noriginal\n")
    (wh / "knowledge" / "modified_discard.md").write_text("# Discard\noriginal\n")

    subprocess.run(
        ["git", "add", "."], cwd=wh, env=env, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Add files"],
        cwd=wh,
        env=env,
        check=True,
        capture_output=True,
    )

    return wh


class TestMigrationUpgrade:
    """Task 7.9: Migration upgrade-path integration test."""

    @pytest.mark.skip(
        reason="knowledge sync rewritten in chunk C / phase 8 of auto-pull-artifact-dependencies"
    )
    def test_migration_contribute_local(
        self, migration_warehouse, tmp_path, monkeypatch
    ):
        """
        1. Create pre-upgrade project with regular files
        2. Run abc sync --contribute-local
        3. Assert modified_contrib.md is contributed and symlinked
        """
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)

        runner = CliRunner()

        # Connect
        result = runner.invoke(
            main, ["warehouse", "connect", "--path", str(migration_warehouse)]
        )
        assert result.exit_code == 0

        # Setup
        result = runner.invoke(main, ["setup"])
        assert result.exit_code == 0

        beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
        beacon_yaml.write_text(
            "artifacts:\n"
            "  knowledge:\n"
            "    - knowledge/unchanged.md\n"
            "    - knowledge/modified_contrib.md\n"
            "    - knowledge/modified_discard.md\n"
            "  skills: []\n"
            "  contexts: []\n"
        )

        # Create regular files (pre-upgrade state)
        artifacts = project_dir / ".agentic-beacon" / "artifacts"
        (artifacts / "knowledge").mkdir(parents=True)
        (artifacts / "knowledge" / "unchanged.md").write_text("# Unchanged\noriginal\n")
        (artifacts / "knowledge" / "modified_contrib.md").write_text(
            "# Contrib\nLOCAL contrib content\n"
        )
        (artifacts / "knowledge" / "modified_discard.md").write_text(
            "# Discard\nLOCAL discard content\n"
        )

        # Run sync --contribute-local for the contrib file
        result = runner.invoke(main, ["sync", "--contribute-local", "--skip-git-check"])
        assert result.exit_code == 0, f"sync failed:\n{result.output}"

        # Verify modified_contrib.md is now a symlink and warehouse has local content
        contrib_link = artifacts / "knowledge" / "modified_contrib.md"
        assert contrib_link.is_symlink()
        wh_contrib = migration_warehouse / "knowledge" / "modified_contrib.md"
        assert "LOCAL contrib content" in wh_contrib.read_text()

    @pytest.mark.skip(
        reason="knowledge sync rewritten in chunk C / phase 8 of auto-pull-artifact-dependencies"
    )
    def test_migration_discard_local(self, migration_warehouse, tmp_path, monkeypatch):
        """
        1. Create pre-upgrade project with regular files
        2. Run abc sync --discard-local
        3. Assert modified_discard.md is discarded and symlinked
        """
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)

        runner = CliRunner()

        # Connect
        result = runner.invoke(
            main, ["warehouse", "connect", "--path", str(migration_warehouse)]
        )
        assert result.exit_code == 0

        # Setup
        result = runner.invoke(main, ["setup"])
        assert result.exit_code == 0

        beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
        beacon_yaml.write_text(
            "artifacts:\n"
            "  knowledge:\n"
            "    - knowledge/unchanged.md\n"
            "    - knowledge/modified_contrib.md\n"
            "    - knowledge/modified_discard.md\n"
            "  skills: []\n"
            "  contexts: []\n"
        )

        # Create regular files (pre-upgrade state)
        artifacts = project_dir / ".agentic-beacon" / "artifacts"
        (artifacts / "knowledge").mkdir(parents=True)
        (artifacts / "knowledge" / "unchanged.md").write_text("# Unchanged\noriginal\n")
        (artifacts / "knowledge" / "modified_contrib.md").write_text(
            "# Contrib\nLOCAL contrib content\n"
        )
        (artifacts / "knowledge" / "modified_discard.md").write_text(
            "# Discard\nLOCAL discard content\n"
        )

        # Run sync --discard-local for the discard file
        result = runner.invoke(main, ["sync", "--discard-local", "--skip-git-check"])
        assert result.exit_code == 0, f"sync failed:\n{result.output}"

        # Verify modified_discard.md is now a symlink and warehouse is unchanged
        discard_link = artifacts / "knowledge" / "modified_discard.md"
        assert discard_link.is_symlink()
        wh_discard = migration_warehouse / "knowledge" / "modified_discard.md"
        assert "original" in wh_discard.read_text()
        assert "LOCAL discard content" not in wh_discard.read_text()

    @pytest.mark.skip(
        reason="knowledge sync rewritten in chunk C / phase 8 of auto-pull-artifact-dependencies"
    )
    def test_migration_full_tree_symlinked(
        self, migration_warehouse, tmp_path, monkeypatch
    ):
        """
        Run --contribute-local to convert all regular files to symlinks.
        """
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)

        runner = CliRunner()

        # Connect
        result = runner.invoke(
            main, ["warehouse", "connect", "--path", str(migration_warehouse)]
        )
        assert result.exit_code == 0

        # Setup
        result = runner.invoke(main, ["setup"])
        assert result.exit_code == 0

        beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
        beacon_yaml.write_text(
            "artifacts:\n"
            "  knowledge:\n"
            "    - knowledge/unchanged.md\n"
            "    - knowledge/modified_contrib.md\n"
            "    - knowledge/modified_discard.md\n"
            "  skills: []\n"
            "  contexts: []\n"
        )

        # Create regular files (pre-upgrade state)
        artifacts = project_dir / ".agentic-beacon" / "artifacts"
        (artifacts / "knowledge").mkdir(parents=True)
        (artifacts / "knowledge" / "unchanged.md").write_text("# Unchanged\noriginal\n")
        (artifacts / "knowledge" / "modified_contrib.md").write_text(
            "# Contrib\nLOCAL contrib content\n"
        )
        (artifacts / "knowledge" / "modified_discard.md").write_text(
            "# Discard\nLOCAL discard content\n"
        )

        # Sync with --contribute-local converts ALL regular files
        result = runner.invoke(main, ["sync", "--contribute-local", "--skip-git-check"])
        assert result.exit_code == 0

        # Assert final project tree: 3 symlinks, 0 regular files under artifacts/
        files = list(artifacts.rglob("*"))
        symlinks = [f for f in files if f.is_symlink()]
        regular_files = [f for f in files if f.is_file() and not f.is_symlink()]
        assert len(symlinks) == 3, f"Expected 3 symlinks, got {len(symlinks)}"
        assert len(regular_files) == 0, (
            f"Expected 0 regular files, got {len(regular_files)}"
        )

        # Assert warehouse contains contributed content for both modified files
        wh_contrib = migration_warehouse / "knowledge" / "modified_contrib.md"
        assert "LOCAL contrib content" in wh_contrib.read_text()

        wh_discard = migration_warehouse / "knowledge" / "modified_discard.md"
        assert "LOCAL discard content" in wh_discard.read_text()
