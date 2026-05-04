"""Unit tests for abc warehouse status.

Implements TC set from task 4.2.
"""

import os
import subprocess

import pytest
from beacon.domains.warehouse.status import status


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
def status_warehouse(tmp_path):
    """Create a real git repo as the warehouse."""
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
    return wh


@pytest.fixture
def status_project(tmp_path, status_warehouse, monkeypatch):
    """Create a project connected to the warehouse."""
    project = tmp_path / "project"
    project.mkdir()
    beacon_dir = project / ".agentic-beacon"
    beacon_dir.mkdir()

    config = beacon_dir / "config.toml"
    config.write_text(f'[warehouse]\nlocal_path = "{status_warehouse}"\n')

    beacon_yaml = beacon_dir / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  contexts:\n"
        "    - contexts/test.md\n"
        "    - contexts/other.md\n"
        "  skills: []\n"
        "  agents: []\n"
    )

    (status_warehouse / "contexts").mkdir()
    (status_warehouse / "contexts" / "test.md").write_text("# Test\n")
    (status_warehouse / "contexts" / "other.md").write_text("# Other\n")
    (status_warehouse / "untracked.md").write_text("# Untracked\n")

    # Commit files so they are tracked by git
    env = _git_env()
    subprocess.run(
        ["git", "add", "."],
        cwd=status_warehouse,
        env=env,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Add test files"],
        cwd=status_warehouse,
        env=env,
        check=True,
        capture_output=True,
    )

    # Ensure CWD is the project so WorkspaceConfig finds config.toml
    monkeypatch.chdir(project)

    return project, status_warehouse


class TestStatus:
    """TCs from task 4.2."""

    def test_clean_tree(self, status_project):
        """TC1: Clean warehouse -> empty modifications list."""
        project, wh = status_project
        result = status(project)
        assert result.modifications == []
        # No upstream -> ahead/behind are None (production behavior)
        assert result.has_upstream is False
        assert result.ahead is None
        assert result.behind is None

    def test_modified_tracked_files_listed(self, status_project):
        """TC2: Modified tracked files matching beacon.yaml -> listed."""
        project, wh = status_project
        (wh / "contexts" / "test.md").write_text("# Test\nmodified\n")

        result = status(project)
        assert any(
            m.status == "M" and m.path == "contexts/test.md"
            for m in result.modifications
        )

    def test_modified_untracked_files_not_listed(self, status_project):
        """Modified files NOT tracked by beacon.yaml -> NOT listed."""
        project, wh = status_project
        (wh / "untracked.md").write_text("# Untracked\nmodified\n")

        result = status(project)
        paths = [m.path for m in result.modifications]
        # untracked.md won't appear because it's not in beacon.yaml
        assert not any("untracked" in p for p in paths)

    def test_all_flag_shows_unfiltered(self, status_project):
        """TC6: --all equivalent -> no beacon.yaml filter."""
        project, wh = status_project
        (wh / "untracked.md").write_text("# Untracked\nmodified\n")

        result = status(project, all_paths=True)
        assert any(m.path == "untracked.md" for m in result.modifications)

    def test_filenames_are_complete_with_leading_space_status(self, status_project):
        """Leading-space porcelain codes keep the full filename intact."""
        project, wh = status_project
        filename = "contexts/full-filename-regression.md"
        target = wh / filename
        target.write_text("# Full filename\n")

        env = _git_env()
        subprocess.run(
            ["git", "add", filename],
            cwd=wh,
            env=env,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add regression file"],
            cwd=wh,
            env=env,
            check=True,
            capture_output=True,
        )

        target.write_text("# Full filename\nmodified\n")

        beacon_yaml = project / ".agentic-beacon" / "beacon.yaml"
        beacon_yaml.write_text(
            "artifacts:\n"
            "  contexts:\n"
            "    - contexts/test.md\n"
            "    - contexts/other.md\n"
            f"    - {filename}\n"
            "  skills: []\n"
            "  agents: []\n"
        )

        result = status(project)
        assert any(m.path == filename for m in result.modifications)

    def test_ahead_behind_with_upstream(self, status_project, tmp_path):
        """TC3: Warehouse branch 3 commits ahead of upstream -> ahead=3."""
        project, wh = status_project
        bare = tmp_path / "upstream.git"
        bare.mkdir()
        env = _git_env()
        subprocess.run(
            ["git", "init", "--bare"],
            cwd=bare,
            env=env,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "remote", "add", "origin", str(bare)],
            cwd=wh,
            env=env,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "push", "-u", "origin", "HEAD"],
            cwd=wh,
            env=env,
            check=True,
            capture_output=True,
        )

        # Make 3 local commits
        for i in range(3):
            (wh / "contexts" / "test.md").write_text(f"# Test\ncommit {i}\n")
            subprocess.run(
                ["git", "add", "."],
                cwd=wh,
                env=env,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", f"commit {i}"],
                cwd=wh,
                env=env,
                check=True,
                capture_output=True,
            )

        result = status(project)
        assert result.ahead == 3
        assert result.behind == 0
        assert result.has_upstream is True

    def test_no_upstream(self, status_project):
        """TC4: No upstream configured -> has_upstream=False, ahead=None, behind=None."""
        project, wh = status_project
        result = status(project)
        assert result.has_upstream is False
        assert result.ahead is None
        assert result.behind is None

    def test_single_file_path_returns_diff(self, status_project):
        """TC5: path argument -> returns diff string for that file."""
        project, wh = status_project
        (wh / "contexts" / "test.md").write_text("# Test\nmodified\n")

        result = status(project, path="contexts/test.md")
        assert result.diff is not None
        # The diff contains the modified line
        assert "modified" in result.diff

    def test_untracked_path_raises(self, status_project):
        """TC5 variant: path not tracked -> raises ValueError."""
        project, wh = status_project
        with pytest.raises(ValueError) as exc_info:
            status(project, path="untracked.md")
        assert "not tracked" in str(exc_info.value).lower()
