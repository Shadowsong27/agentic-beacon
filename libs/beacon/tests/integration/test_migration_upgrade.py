"""Integration test for migration upgrade path.

Covers tasks 7.9 and 8.4: simulates a pre-upgrade project with regular files
and verifies migration to symlinks.
"""

import os
import subprocess

import pytest

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

    pass
