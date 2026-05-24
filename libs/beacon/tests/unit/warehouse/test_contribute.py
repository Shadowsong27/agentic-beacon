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

    def test_untracked_files_not_staged_with_only_tracked(self, contrib_project):
        """only_tracked=True: edits only non-beacon.yaml paths -> NOT staged.

        Under the PER-203 default, an untracked dirty file IS committable
        (covered by TestWarehouseScopedDefault). This test pins down the
        legacy project-filter behavior, which now lives behind --only-tracked.
        """
        project, wh = contrib_project
        # Create a file not in beacon.yaml
        (wh / "untracked.md").write_text("# Untracked\n")

        result = contribute(
            project, message="Should be no changes", push=False, only_tracked=True
        )
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

    def test_pre_staged_unrelated_file_not_committed_with_only_tracked(
        self, contrib_project
    ):
        """only_tracked=True: pre-staged unrelated changes left staged, not committed.

        Under the PER-203 default, a dirty unrelated file IS committed (the
        skill caller is expected to use --paths for fine-grained control).
        This test pins down the legacy behavior under --only-tracked.
        """
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

        result = contribute(
            project, message="Commit tracked only", push=False, only_tracked=True
        )

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

    def test_contribute_paths_validates_membership_with_only_tracked(
        self, contrib_project_multi
    ):
        """only_tracked=True: paths=(D,) not in beacon.yaml raises ValueError mentioning D."""
        project, wh = contrib_project_multi
        with pytest.raises(ValueError) as exc_info:
            contribute(
                project,
                message="should fail",
                push=False,
                paths=("contexts/d.md",),
                only_tracked=True,
            )
        assert "contexts/d.md" in str(exc_info.value)
        assert "not tracked by beacon.yaml" in str(exc_info.value)

    def test_contribute_paths_to_nondirty_file_rejected(self, contrib_project_multi):
        """Default: paths=(D,) where D is not dirty in warehouse → ValueError."""
        project, wh = contrib_project_multi
        # contexts/d.md doesn't exist at all, so it has no porcelain status
        with pytest.raises(ValueError) as exc_info:
            contribute(
                project,
                message="should fail",
                push=False,
                paths=("contexts/d.md",),
            )
        assert "contexts/d.md" in str(exc_info.value)
        assert "not dirty" in str(exc_info.value)

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

    def test_contribute_paths_leading_dot_slash(self, contrib_project_multi):
        """Leading './' is normalized away before membership check."""
        project, wh = contrib_project_multi
        env = _git_env()

        (wh / "contexts" / "a.md").write_text("# a modified\n")

        result = contribute(
            project,
            message="commit with ./prefix",
            push=False,
            paths=("./contexts/a.md",),
        )
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

    def test_contribute_paths_double_slash(self, contrib_project_multi):
        """Redundant '//' separators are collapsed."""
        project, wh = contrib_project_multi
        env = _git_env()

        (wh / "contexts" / "a.md").write_text("# a modified\n")

        result = contribute(
            project,
            message="commit with double slash",
            push=False,
            paths=("contexts//a.md",),
        )
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

    def test_contribute_paths_absolute_rejected(self, contrib_project_multi):
        """Absolute paths raise ValueError."""
        project, wh = contrib_project_multi
        with pytest.raises(ValueError) as exc_info:
            contribute(
                project,
                message="should fail",
                push=False,
                paths=("/absolute/path.md",),
            )
        assert "absolute" in str(exc_info.value).lower()

    def test_contribute_paths_dotdot_rejected(self, contrib_project_multi):
        """Paths with '..' raise ValueError."""
        project, wh = contrib_project_multi
        with pytest.raises(ValueError) as exc_info:
            contribute(
                project,
                message="should fail",
                push=False,
                paths=("../outside.md",),
            )
        assert "parent-directory" in str(exc_info.value).lower()


class TestDirtyOutsideScope:
    """Tests for PER-159: out-of-scope dirty file count in contribute."""

    def test_no_changes_with_outside_scope_dirty_returns_count_only_tracked(
        self, contrib_project
    ):
        """only_tracked=True: dirty file outside beacon.yaml -> no_changes with count >= 1.

        Under the PER-203 default, the untracked file would be committed, so
        this signal only makes sense in the legacy project-scoped mode.
        """
        project, wh = contrib_project
        (wh / "untracked.md").write_text("# Untracked\nmodified\n")

        result = contribute(project, message="x", push=False, only_tracked=True)
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


class TestPer203WarehouseScopedDefault:
    """PER-203: default is warehouse-scoped — any dirty warehouse path is committable.

    The legacy beacon.yaml filter survives behind only_tracked=True.
    """

    def test_brand_new_skill_path_commits_without_beacon_yaml_entry(
        self, contrib_project
    ):
        """A new skill folder not in beacon.yaml is committable via --paths under default."""
        project, wh = contrib_project
        env = _git_env()

        skill_dir = wh / "skills" / "brand-new"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("---\nname: brand-new\n---\nbody\n")

        result = contribute(
            project,
            message="feat(skills): add brand-new skill",
            push=False,
            paths=("skills/brand-new/SKILL.md",),
        )
        assert result.status == "committed"
        assert result.committed_sha

        committed_files = subprocess.run(
            ["git", "show", "--name-only", "--format=", "HEAD"],
            cwd=wh,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "skills/brand-new/SKILL.md" in committed_files.stdout

    def test_cross_project_knowledge_commits_without_beacon_yaml_entry(
        self, contrib_project
    ):
        """A knowledge file not in beacon.yaml is committable under default."""
        project, wh = contrib_project
        env = _git_env()

        knowledge_dir = wh / "knowledge" / "infrastructure"
        knowledge_dir.mkdir(parents=True)
        knowledge_file = knowledge_dir / "router-config.md"
        knowledge_file.write_text("# Router config\n")

        result = contribute(
            project,
            message="docs(knowledge): add router config",
            push=False,
            paths=("knowledge/infrastructure/router-config.md",),
        )
        assert result.status == "committed"

        committed_files = subprocess.run(
            ["git", "show", "--name-only", "--format=", "HEAD"],
            cwd=wh,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "knowledge/infrastructure/router-config.md" in committed_files.stdout

    def test_default_paths_none_commits_all_dirty(self, contrib_project):
        """Default (paths=None, only_tracked=False) commits ALL dirty paths.

        Includes paths not in beacon.yaml — that's the whole point of PER-203.
        """
        project, wh = contrib_project
        env = _git_env()

        # Dirty an in-beacon.yaml file + an out-of-beacon.yaml file
        (wh / "contexts" / "test.md").write_text("# Test modified\n")
        (wh / "scratch.md").write_text("# scratch\n")

        result = contribute(project, message="commit everything", push=False)
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
        assert "scratch.md" in committed_files.stdout

    def test_only_tracked_preserves_legacy_filter(self, contrib_project):
        """only_tracked=True: out-of-beacon.yaml dirty file is NOT committed."""
        project, wh = contrib_project
        env = _git_env()

        (wh / "contexts" / "test.md").write_text("# Test modified\n")
        (wh / "scratch.md").write_text("# scratch\n")

        result = contribute(
            project, message="commit tracked only", push=False, only_tracked=True
        )
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
        assert "scratch.md" not in committed_files.stdout

    def test_default_paths_none_with_no_dirty_files_returns_no_changes(
        self, contrib_project
    ):
        """Default mode: clean warehouse → no_changes."""
        project, wh = contrib_project
        result = contribute(project, message="x", push=False)
        assert result.status == "no_changes"
        assert result.dirty_outside_scope_count == 0

    def test_default_paths_to_dirty_brand_new_file_commits(self, contrib_project):
        """Default: --paths pointing to an untracked but dirty file commits it."""
        project, wh = contrib_project

        (wh / "fresh.md").write_text("# fresh\n")  # untracked

        result = contribute(
            project,
            message="add fresh",
            push=False,
            paths=("fresh.md",),
        )
        assert result.status == "committed"

    def test_default_paths_normalization_still_applied(self, contrib_project):
        """Default: leading './' and '//' are normalized before the dirty check."""
        project, wh = contrib_project
        (wh / "contexts" / "test.md").write_text("# normalized\n")

        result = contribute(
            project,
            message="normalize",
            push=False,
            paths=("./contexts//test.md",),
        )
        assert result.status == "committed"

    def test_default_paths_absolute_rejected(self, contrib_project):
        """Default: absolute paths still raise (path-shape validation runs first)."""
        project, wh = contrib_project
        with pytest.raises(ValueError) as exc_info:
            contribute(
                project,
                message="x",
                push=False,
                paths=("/absolute/foo.md",),
            )
        assert "absolute" in str(exc_info.value).lower()

    def test_default_paths_none_commits_rename_with_both_sides(self, contrib_project):
        """Default mode commits a rename cleanly — old deletion + new add.

        Regression for opencode-review PR #156 finding M1: enumerating dirty
        paths and committing only the destination of 'R old -> new' would
        leave the old-side deletion staged. The default path uses
        'git add -A' + unrestricted commit, which captures both sides.
        """
        project, wh = contrib_project
        env = _git_env()

        # git mv the tracked file → triggers an R record in porcelain
        subprocess.run(
            ["git", "-C", str(wh), "mv", "contexts/test.md", "contexts/renamed.md"],
            cwd=wh,
            env=env,
            check=True,
            capture_output=True,
        )

        result = contribute(project, message="rename test.md to renamed.md", push=False)
        assert result.status == "committed"

        committed_files = subprocess.run(
            ["git", "show", "--name-status", "--format=", "HEAD"],
            cwd=wh,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        # Both sides must appear: the deletion of the old name and the
        # addition of the new name (or a single rename record covering both).
        out = committed_files.stdout
        # After commit, the working tree + index must be clean — no leftover
        # staged deletion of the old path.
        post_status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=wh,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert post_status.stdout.strip() == "", (
            f"After rename commit, tree must be clean. Got: {post_status.stdout!r}"
        )
        assert "renamed.md" in out

    def test_default_paths_empty_string_rejected(self, contrib_project):
        """--paths "" must not commit the entire warehouse.

        Regression for opencode-review PR#156 round 8: previously
        normalize_relative_path("") returned "." which became the literal
        pathspec :(literal). and matched everything dirty in the warehouse.
        """
        project, wh = contrib_project
        (wh / "contexts" / "test.md").write_text("# modified\n")

        with pytest.raises(ValueError) as exc_info:
            contribute(
                project,
                message="should fail",
                push=False,
                paths=("",),
            )
        assert "empty" in str(exc_info.value).lower()

    def test_default_paths_dot_rejected(self, contrib_project):
        """--paths "." must not commit the entire warehouse.

        Companion to test_default_paths_empty_string_rejected — same root
        cause, alternative payload. ".", "./", and "" all collapse to the
        warehouse root and must be rejected by normalize_relative_path.
        """
        project, wh = contrib_project
        (wh / "contexts" / "test.md").write_text("# modified\n")

        with pytest.raises(ValueError) as exc_info:
            contribute(
                project,
                message="should fail",
                push=False,
                paths=(".",),
            )
        assert "warehouse root" in str(exc_info.value).lower()

    def test_default_paths_glob_pattern_rejected_not_expanded(self, contrib_project):
        """--paths '*.md' is treated as a literal filename, not a glob.

        Regression for opencode-review PR#156 round 6: without :(literal)
        pathspec magic, git would expand the glob and commit multiple files
        even though the CLI documents --paths as a single warehouse-relative
        filename. With the literal pathspec wrapping, '*.md' is looked up as
        an actual file with that exact name — which does not exist, so the
        dirty-check rejects it.
        """
        project, wh = contrib_project

        # Several real .md files are dirty
        (wh / "contexts" / "test.md").write_text("# modified\n")
        (wh / "scratch.md").write_text("# new\n")

        # Pre-fix: '*.md' would glob-expand to both files and commit them all.
        # Post-fix: the literal pathspec lookup fails the dirty check.
        with pytest.raises(ValueError) as exc_info:
            contribute(
                project,
                message="exploit attempt",
                push=False,
                paths=("*.md",),
            )
        assert "*.md" in str(exc_info.value)
        assert "not dirty" in str(exc_info.value)

    def test_default_paths_pathspec_magic_rejected_not_expanded(self, contrib_project):
        """--paths ':(glob)**/*.md' is treated as a literal filename, not pathspec magic.

        Regression for opencode-review PR#156 round 6: defends against the
        more explicit git-pathspec-DSL injection variant.
        """
        project, wh = contrib_project

        (wh / "contexts" / "test.md").write_text("# modified\n")
        (wh / "scratch.md").write_text("# new\n")

        with pytest.raises(ValueError) as exc_info:
            contribute(
                project,
                message="exploit attempt",
                push=False,
                paths=(":(glob)**/*.md",),
            )
        assert "not dirty" in str(exc_info.value)

    def test_default_paths_rename_source_in_paths_commits_both_sides(
        self, contrib_project
    ):
        """--paths <source-of-rename> pulls in the destination too.

        Regression for opencode-review PR#156 round 5: previously only
        destination -> source was mapped, so passing the rename source path
        committed just the deletion and left the new file staged. The
        bidirectional rename map fixes this — passing either side captures
        both.
        """
        project, wh = contrib_project
        env = _git_env()

        subprocess.run(
            ["git", "-C", str(wh), "mv", "contexts/test.md", "contexts/renamed.md"],
            cwd=wh,
            env=env,
            check=True,
            capture_output=True,
        )

        # User supplies the SOURCE path (now deleted from working tree)
        result = contribute(
            project,
            message="rename via --paths <source>",
            push=False,
            paths=("contexts/test.md",),
        )
        assert result.status == "committed"

        # Working tree + index must be clean.
        post_status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=wh,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert post_status.stdout.strip() == "", (
            f"After source-path rename commit, tree must be clean. "
            f"Got: {post_status.stdout!r}"
        )

    def test_default_paths_rename_with_arrow_in_source_commits_both_sides(
        self, contrib_project
    ):
        """--paths <dest> for a rename whose SOURCE contains ' -> '.

        Regression for opencode-review PR#156 round 4: the prior parser would
        split on the ' -> ' substring inside the source path, producing the
        wrong source name and leaving the actual source's deletion staged.
        The -z parser handles this correctly.
        """
        project, wh = contrib_project
        env = _git_env()

        # Create + commit a file whose name contains ' -> '
        (wh / "notes").mkdir(exist_ok=True)
        weird_src = wh / "notes" / "a -> b.md"
        weird_src.write_text("# weird\n")
        subprocess.run(
            ["git", "-C", str(wh), "add", "notes/a -> b.md"],
            cwd=wh,
            env=env,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(wh), "commit", "-m", "add weird-named file"],
            cwd=wh,
            env=env,
            check=True,
            capture_output=True,
        )

        # Rename via git mv to a plain destination
        subprocess.run(
            ["git", "-C", str(wh), "mv", "notes/a -> b.md", "notes/c.md"],
            cwd=wh,
            env=env,
            check=True,
            capture_output=True,
        )

        result = contribute(
            project,
            message="rename arrow-source file via --paths",
            push=False,
            paths=("notes/c.md",),
        )
        assert result.status == "committed"

        # Working tree + index clean: the deletion of 'notes/a -> b.md' was
        # picked up as part of the rename, not left dangling.
        post_status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=wh,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert post_status.stdout.strip() == "", (
            f"After arrow-source rename commit, tree must be clean. "
            f"Got: {post_status.stdout!r}"
        )

    def test_default_paths_rename_with_spaces_commits_both_sides(self, contrib_project):
        """--paths <dest-with-spaces> for a rename auto-expands source path.

        Regression for opencode-review PR#156 round 3: porcelain quotes paths
        containing whitespace (e.g. ``"contexts/new name.md"``), so the dict
        lookup in _expand_rename_sources must unquote them before matching
        against the user's unquoted --paths argument. Without unquoting, the
        rename source (`contexts/old name.md`) is never added to the commit
        pathspec and its staged deletion is left dangling.
        """
        project, wh = contrib_project
        env = _git_env()

        # Set up a tracked file with a space in the name
        spaced_old = wh / "contexts" / "old name.md"
        spaced_old.write_text("# spaced\n")
        subprocess.run(
            ["git", "-C", str(wh), "add", "contexts/old name.md"],
            cwd=wh,
            env=env,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(wh), "commit", "-m", "add spaced file"],
            cwd=wh,
            env=env,
            check=True,
            capture_output=True,
        )

        # git mv to a new name (also with a space)
        subprocess.run(
            [
                "git",
                "-C",
                str(wh),
                "mv",
                "contexts/old name.md",
                "contexts/new name.md",
            ],
            cwd=wh,
            env=env,
            check=True,
            capture_output=True,
        )

        result = contribute(
            project,
            message="rename spaced file via --paths",
            push=False,
            paths=("contexts/new name.md",),
        )
        assert result.status == "committed"

        # Working tree + index must be clean — the old-side deletion is
        # NOT left dangling.
        post_status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=wh,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert post_status.stdout.strip() == "", (
            f"After spaced rename commit, tree must be clean. "
            f"Got: {post_status.stdout!r}"
        )

    def test_default_paths_explicit_rename_dest_commits_both_sides(
        self, contrib_project
    ):
        """--paths <dest> for a rename auto-expands to include the source.

        Regression for opencode-review PR#156 round 2: previously, passing
        the destination of a git mv via --paths committed the new file but
        left the old-side deletion staged. _expand_rename_sources() now
        transparently includes the source path so the commit is atomic.
        """
        project, wh = contrib_project
        env = _git_env()

        subprocess.run(
            ["git", "-C", str(wh), "mv", "contexts/test.md", "contexts/renamed.md"],
            cwd=wh,
            env=env,
            check=True,
            capture_output=True,
        )

        result = contribute(
            project,
            message="rename via --paths",
            push=False,
            paths=("contexts/renamed.md",),
        )
        assert result.status == "committed"

        # Working tree + index must be clean — the old-side deletion is
        # NOT left dangling as a staged change.
        post_status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=wh,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert post_status.stdout.strip() == "", (
            f"After path-limited rename commit, tree must be clean. "
            f"Got: {post_status.stdout!r}"
        )

        # Both sides must appear in the commit.
        committed = subprocess.run(
            ["git", "show", "--name-status", "--format=", "HEAD"],
            cwd=wh,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "renamed.md" in committed.stdout

    def test_default_paths_none_handles_filename_with_arrow(self, contrib_project):
        """Default mode commits a file literally named 'a -> b.md' without misparsing.

        Regression for opencode-review PR #156 finding M2: the previous
        path-enumeration code would treat ' -> ' as a rename separator and
        produce the wrong pathspec, leaving the real file uncommitted.
        Switching the default to 'git add -A' sidesteps the parsing entirely.
        """
        project, wh = contrib_project
        env = _git_env()

        (wh / "notes").mkdir(exist_ok=True)
        weird = wh / "notes" / "a -> b.md"
        weird.write_text("# weird\n")

        result = contribute(project, message="add notes/a -> b.md", push=False)
        assert result.status == "committed"

        committed = subprocess.run(
            ["git", "show", "--name-only", "--format=", "HEAD"],
            cwd=wh,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        # Git quotes the special-char path in show output, so check substring.
        assert "a -> b.md" in committed.stdout, (
            f"Weird filename must be committed verbatim. Got: {committed.stdout!r}"
        )
        # Working tree must be clean — the real file is not left dangling.
        post_status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=wh,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert post_status.stdout.strip() == "", (
            f"Tree must be clean after commit. Got: {post_status.stdout!r}"
        )

    def test_default_excludes_dot_git_paths(self, contrib_project):
        """Default (paths=None): contents of .git/ never reach the commit."""
        project, wh = contrib_project
        env = _git_env()

        # Trick: write something inside .git/ — git status won't list it,
        # but defend that _all_dirty_paths drops anything under .git/.
        (wh / ".git" / "junk.txt").write_text("nope\n")
        (wh / "contexts" / "test.md").write_text("# test\n")

        result = contribute(project, message="commit", push=False)
        assert result.status == "committed"

        committed_files = subprocess.run(
            ["git", "show", "--name-only", "--format=", "HEAD"],
            cwd=wh,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert ".git" not in committed_files.stdout
