"""Unit tests for abc warehouse contribute.

Implements TC set from task 4.1.
"""

import os
import subprocess

import pytest
from beacon.domains.warehouse.contribute import contribute


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
def contrib_warehouse(tmp_path):
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
def contrib_project(tmp_path, contrib_warehouse, monkeypatch):
    """Create a project connected to the warehouse."""
    project = tmp_path / "project"
    project.mkdir()
    beacon_dir = project / ".agentic-beacon"
    beacon_dir.mkdir()

    # config.toml
    config = beacon_dir / "config.toml"
    config.write_text(f'[warehouse]\nlocal_path = "{contrib_warehouse}"\n')

    # beacon.yaml with tracked paths
    beacon_yaml = beacon_dir / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  contexts:\n    - contexts/test.md\n  skills: []\n\n"
    )

    # Create the tracked file in warehouse and commit it
    (contrib_warehouse / "contexts").mkdir()
    (contrib_warehouse / "contexts" / "test.md").write_text("# Test\n")
    env = _git_env()
    subprocess.run(
        ["git", "add", "."],
        cwd=contrib_warehouse,
        env=env,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Add test files"],
        cwd=contrib_warehouse,
        env=env,
        check=True,
        capture_output=True,
    )

    # Ensure CWD is the project so WorkspaceConfig finds config.toml
    monkeypatch.chdir(project)

    return project, contrib_warehouse


@pytest.fixture
def contrib_project_multi(tmp_path, monkeypatch):
    """Create a project connected to a warehouse with 3 tracked files (a, b, c)."""
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

    project = tmp_path / "project"
    project.mkdir()
    beacon_dir = project / ".agentic-beacon"
    beacon_dir.mkdir()

    config = beacon_dir / "config.toml"
    config.write_text(f'[warehouse]\nlocal_path = "{wh}"\n')

    beacon_yaml = beacon_dir / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  contexts:\n"
        "    - contexts/a.md\n"
        "    - contexts/b.md\n"
        "    - contexts/c.md\n"
        "  skills: []\n\n"
    )

    # Create and commit all three files
    (wh / "contexts").mkdir()
    for name in ("a.md", "b.md", "c.md"):
        (wh / "contexts" / name).write_text(f"# {name}\n")
    subprocess.run(
        ["git", "add", "."],
        cwd=wh,
        env=env,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Add a/b/c"],
        cwd=wh,
        env=env,
        check=True,
        capture_output=True,
    )

    monkeypatch.chdir(project)
    return project, wh


class TestContribute:
    """TCs from task 4.1."""

    def test_empty_message_raises(self, contrib_project):
        """TC3: Empty commit message -> raises ValueError before touching git."""
        project, _ = contrib_project
        with pytest.raises(ValueError):
            contribute(project, message="", push=False)
        with pytest.raises(ValueError):
            contribute(project, message="   ", push=False)

    def test_no_uncommitted_changes_returns_no_changes(self, contrib_project):
        """TC2: No uncommitted changes -> returns no_changes."""
        project, wh = contrib_project
        result = contribute(project, message="test", push=False)
        assert result.status == "no_changes"

    def test_successful_commit(self, contrib_project):
        """TC1: Warehouse has uncommitted edits -> commit created."""
        project, wh = contrib_project
        # Modify tracked file
        (wh / "contexts" / "test.md").write_text("# Test\nmodified\n")

        result = contribute(project, message="Update test", push=False)
        assert result.status == "committed"
        assert result.committed_sha

        # Verify with git log
        env = _git_env()
        log = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            cwd=wh,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Update test" in log.stdout

    def test_push_success(self, contrib_project, tmp_path):
        """TC6: Explicit push=True -> after commit, push ran."""
        project, wh = contrib_project
        # Create a bare upstream
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

        # Now modify and push
        (wh / "contexts" / "test.md").write_text("# Test\nmodified for push\n")
        result = contribute(project, message="Update for push", push=True)
        assert result.status == "committed"
        assert result.committed_sha

    def test_push_failure_preserves_commit(self, contrib_project):
        """TC6 variant: Push failure -> status push_failed, commit preserved."""
        project, wh = contrib_project
        (wh / "contexts" / "test.md").write_text("# Test\nmodified\n")

        # No upstream configured -> push will fail
        result = contribute(project, message="Update no upstream", push=True)
        assert result.status == "push_failed"
        assert result.committed_sha

        # Verify commit exists
        env = _git_env()
        log = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            cwd=wh,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Update no upstream" in log.stdout

    def test_git_commit_failure_raises_runtime_error(self, contrib_project):
        """TC from 7.4: git commit fails -> RuntimeError raised."""
        project, wh = contrib_project
        # Simulate git commit failure with a pre-commit hook that exits 1
        hook_dir = wh / ".git" / "hooks"
        hook_dir.mkdir(exist_ok=True)
        (hook_dir / "pre-commit").write_text("#!/bin/sh\nexit 1\n")
        (hook_dir / "pre-commit").chmod(0o755)

        (wh / "contexts" / "test.md").write_text("# Test\nmodified\n")

        with pytest.raises(RuntimeError) as exc_info:
            contribute(project, message="Should fail", push=False)
        assert (
            "Git commit failed" in str(exc_info.value)
            or "failed" in str(exc_info.value).lower()
        )

    def test_untracked_files_not_staged(self, contrib_project):
        """TC5: Commit succeeds but edits only non-beacon.yaml paths -> NOT staged."""
        project, wh = contrib_project
        # Create a file not in beacon.yaml
        (wh / "untracked.md").write_text("# Untracked\n")

        result = contribute(project, message="Should be no changes", push=False)
        assert result.status == "no_changes"

        # untracked.md should not be committed
        env = _git_env()
        log = subprocess.run(
            ["git", "diff", "HEAD", "--name-only"],
            cwd=wh,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "untracked.md" not in log.stdout

    def test_pre_staged_unrelated_file_not_committed(self, contrib_project):
        """Pre-staged unrelated changes are left staged, not included in commit."""
        project, wh = contrib_project
        env = _git_env()

        (wh / "contexts" / "test.md").write_text("# Test\ntracked change\n")
        (wh / "unrelated.md").write_text("# Unrelated\n")
        subprocess.run(
            ["git", "add", "unrelated.md"],
            cwd=wh,
            env=env,
            check=True,
            capture_output=True,
        )

        result = contribute(project, message="Commit tracked only", push=False)

        assert result.status == "committed"
        committed_files = subprocess.run(
            ["git", "show", "--name-only", "--format=", "HEAD"],
            cwd=wh,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "contexts/test.md" in committed_files.stdout
        assert "unrelated.md" not in committed_files.stdout

        staged_files = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=wh,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "unrelated.md" in staged_files.stdout


class TestContributePaths:
    """Tests for the --paths scoping feature (Finding 1 fix-up)."""

    def test_contribute_subset_commits_only_specified_paths(
        self, contrib_project_multi
    ):
        """Given 3 dirty tracked files A/B/C and paths=(A,), only A gets committed."""
        project, wh = contrib_project_multi
        env = _git_env()

        # Dirty all three files
        for name in ("a.md", "b.md", "c.md"):
            (wh / "contexts" / name).write_text(f"# {name} modified\n")

        result = contribute(
            project, message="commit only a", push=False, paths=("contexts/a.md",)
        )
        assert result.status == "committed"
        assert result.committed_sha

        # Only a.md should appear in HEAD
        committed_files = subprocess.run(
            ["git", "show", "--name-only", "--format=", "HEAD"],
            cwd=wh,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "contexts/a.md" in committed_files.stdout
        assert "contexts/b.md" not in committed_files.stdout
        assert "contexts/c.md" not in committed_files.stdout

        # B and C still dirty
        status = subprocess.run(
            ["git", "status", "--porcelain", "--", "contexts/b.md", "contexts/c.md"],
            cwd=wh,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "b.md" in status.stdout
        assert "c.md" in status.stdout

    def test_contribute_paths_validates_membership(self, contrib_project_multi):
        """paths=(D,) where D is not tracked raises ValueError mentioning D."""
        project, wh = contrib_project_multi
        with pytest.raises(ValueError) as exc_info:
            contribute(
                project,
                message="should fail",
                push=False,
                paths=("contexts/d.md",),
            )
        assert "contexts/d.md" in str(exc_info.value)

    def test_contribute_paths_empty_tuple_raises(self, contrib_project_multi):
        """paths=() raises ValueError with a clear message."""
        project, wh = contrib_project_multi
        with pytest.raises(ValueError) as exc_info:
            contribute(project, message="should fail", push=False, paths=())
        assert "empty" in str(exc_info.value).lower()

    def test_contribute_paths_none_preserves_existing_behavior(
        self, contrib_project_multi
    ):
        """paths=None commits all dirty tracked paths (existing behavior)."""
        project, wh = contrib_project_multi
        env = _git_env()

        # Dirty all three
        for name in ("a.md", "b.md", "c.md"):
            (wh / "contexts" / name).write_text(f"# {name} all modified\n")

        result = contribute(project, message="commit all", push=False, paths=None)
        assert result.status == "committed"

        committed_files = subprocess.run(
            ["git", "show", "--name-only", "--format=", "HEAD"],
            cwd=wh,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "contexts/a.md" in committed_files.stdout
        assert "contexts/b.md" in committed_files.stdout
        assert "contexts/c.md" in committed_files.stdout

    def test_contribute_paths_sequential_groups_leave_others_dirty(
        self, contrib_project_multi
    ):
        """Simulate multi-commit split: A then B; C remains dirty after both."""
        project, wh = contrib_project_multi
        env = _git_env()

        # Dirty all three
        for name in ("a.md", "b.md", "c.md"):
            (wh / "contexts" / name).write_text(f"# {name} for split\n")

        # First commit: only A
        r1 = contribute(
            project, message="commit a", push=False, paths=("contexts/a.md",)
        )
        assert r1.status == "committed"

        # Second commit: only B
        r2 = contribute(
            project, message="commit b", push=False, paths=("contexts/b.md",)
        )
        assert r2.status == "committed"

        # C still dirty
        status = subprocess.run(
            ["git", "status", "--porcelain", "--", "contexts/c.md"],
            cwd=wh,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "c.md" in status.stdout

        # Verify two separate commits were made
        log = subprocess.run(
            ["git", "log", "-2", "--format=%s"],
            cwd=wh,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "commit b" in log.stdout
        assert "commit a" in log.stdout


class TestDirtyOutsideScope:
    """Tests for PER-159: out-of-scope dirty file count in contribute."""

    def test_no_changes_with_outside_scope_dirty_returns_count(self, contrib_project):
        """Dirty file outside beacon.yaml -> no_changes with count >= 1."""
        project, wh = contrib_project
        (wh / "untracked.md").write_text("# Untracked\nmodified\n")

        result = contribute(project, message="x", push=False)
        assert result.status == "no_changes"
        assert result.dirty_outside_scope_count >= 1

    def test_no_changes_with_clean_tree_returns_zero_count(self, contrib_project):
        """Clean warehouse -> dirty_outside_scope_count == 0."""
        project, wh = contrib_project
        result = contribute(project, message="x", push=False)
        assert result.status == "no_changes"
        assert result.dirty_outside_scope_count == 0

    def test_commit_path_does_not_compute_outside_scope(self, contrib_project_multi):
        """Committed result has dirty_outside_scope_count == 0."""
        project, wh = contrib_project_multi

        # Dirty a tracked file
        (wh / "contexts" / "a.md").write_text("# a modified\n")

        result = contribute(project, message="commit a", push=False)
        assert result.status == "committed"
        assert result.dirty_outside_scope_count == 0
