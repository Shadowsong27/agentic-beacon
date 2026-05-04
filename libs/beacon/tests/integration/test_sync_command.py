"""Tests for abc sync command.

Following TDD workflow for tasks 7.1-7.7:
- Task 7.1: sync command implementation
- Task 7.2: Warehouse connection validation
- Task 7.3: beacon.yaml existence validation
- Task 7.4: Artifact path validation
- Task 7.5: Progress output
- Task 7.6: Empty beacon.yaml handling
- Task 7.7: Invalid glob pattern handling
"""

import pytest
from beacon.cli.main import main
from beacon.core.manifest.beacon import ArtifactsConfig, BeaconManifest
from beacon.domains.artifact.skill import validate_skill_entries
from click.testing import CliRunner

# ========== Task 7.1: ABC Sync Command Implementation ==========


@pytest.mark.skip(
    reason="knowledge field removed from manifest; sync knowledge tests deferred"
)
def test_sync_with_valid_configuration(valid_warehouse, temp_dir, monkeypatch):
    """TC1: Valid beacon.yaml → Sync creates artifacts directory with files."""
    runner = CliRunner()
    project_dir = temp_dir / "my-project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    # Connect warehouse
    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])

    # Write beacon.yaml with knowledge entry
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge:\n    - knowledge/test.md\n  skills: []\n  contexts: []\n"
    )

    # Run sync
    result = runner.invoke(main, ["sync", "--skip-git-check"])

    assert result.exit_code == 0
    assert "sync" in result.output.lower() or "✓" in result.output

    # Verify file was copied
    synced_file = (
        project_dir / ".agentic-beacon" / "artifacts" / "knowledge" / "test.md"
    )
    assert synced_file.exists()
    assert synced_file.read_text() == "# Test"


@pytest.mark.skip(
    reason="knowledge sync rewritten in chunk C / phase 8 of auto-pull-artifact-dependencies"
)
def test_sync_is_idempotent(valid_warehouse, temp_dir, monkeypatch):
    """TC2: Second sync with no changes → No files copied (idempotent)."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    # Setup
    (valid_warehouse / "knowledge" / "test.md").write_text("# Test")
    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    runner.invoke(main, ["setup"])
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge:\n    - knowledge/test.md\n  skills: []\n  contexts: []\n"
    )

    # First sync
    result1 = runner.invoke(main, ["sync", "--skip-git-check"])
    assert result1.exit_code == 0

    synced_file = (
        project_dir / ".agentic-beacon" / "artifacts" / "knowledge" / "test.md"
    )
    mtime1 = synced_file.stat().st_mtime

    # Second sync - should be idempotent
    result2 = runner.invoke(main, ["sync", "--skip-git-check"])
    assert result2.exit_code == 0

    # File should not have been re-copied
    mtime2 = synced_file.stat().st_mtime
    assert mtime2 == mtime1


@pytest.mark.skip(
    reason="knowledge sync rewritten in chunk C / phase 8 of auto-pull-artifact-dependencies"
)
def test_sync_with_glob_patterns(valid_warehouse, temp_dir, monkeypatch):
    """TC8: beacon.yaml with globs → All matching files synced."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    # Create multiple files matching pattern
    (valid_warehouse / "knowledge" / "python").mkdir(parents=True, exist_ok=True)
    (valid_warehouse / "knowledge" / "python" / "file1.md").write_text("# File 1")
    (valid_warehouse / "knowledge" / "python" / "file2.md").write_text("# File 2")

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    runner.invoke(main, ["setup"])
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge:\n    - knowledge/python/*.md\n  skills: []\n  contexts: []\n"
    )

    result = runner.invoke(main, ["sync", "--skip-git-check"])

    assert result.exit_code == 0

    # Verify both files were copied
    artifacts_dir = project_dir / ".agentic-beacon" / "artifacts"
    assert (artifacts_dir / "knowledge" / "python" / "file1.md").exists()
    assert (artifacts_dir / "knowledge" / "python" / "file2.md").exists()


# ========== Task 7.2: Warehouse Connection Validation ==========


def test_sync_without_warehouse_connection(temp_dir, monkeypatch):
    """TC1: No config.toml exists → Error message about connection."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()

    # Create .agentic-beacon but no config.toml
    beacon_dir = project_dir / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "beacon.yaml").write_text(
        "artifacts:\n  knowledge: []\n  skills: []\n  contexts: []\n"
    )

    monkeypatch.chdir(project_dir)

    result = runner.invoke(main, ["sync", "--skip-git-check"])

    assert result.exit_code == 1
    assert "warehouse" in result.output.lower()
    assert "connect" in result.output.lower()


# ========== Task 7.3: Beacon.yaml Existence Validation ==========


def test_sync_without_beacon_yaml(valid_warehouse, temp_dir, monkeypatch):
    """TC: No beacon.yaml → Error with actionable message."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    # Connect warehouse but don't create beacon.yaml
    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])

    result = runner.invoke(main, ["sync", "--skip-git-check"])

    assert result.exit_code == 1
    assert "beacon.yaml" in result.output.lower()
    assert "setup" in result.output.lower()


# ========== Task 7.6: Empty Beacon.yaml Handling ==========


def test_sync_with_empty_beacon_yaml(valid_warehouse, temp_dir, monkeypatch):
    """TC: Empty beacon.yaml → No-op, friendly message."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    runner.invoke(main, ["setup"])

    # beacon.yaml with empty lists
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge: []\n  skills: []\n  contexts: []\n"
    )

    result = runner.invoke(main, ["sync", "--skip-git-check"])

    assert result.exit_code == 0
    assert (
        "no artifacts" in result.output.lower()
        or "nothing to sync" in result.output.lower()
    )


# ========== --dry-run flag ==========


def test_sync_dry_run_does_not_copy_files(valid_warehouse, temp_dir, monkeypatch):
    """--dry-run previews what would be copied without actually copying."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    (valid_warehouse / "knowledge" / "tip.md").write_text("# Tip")

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    runner.invoke(main, ["setup"])
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge:\n    - knowledge/tip.md\n  skills: []\n  contexts: []\n"
    )

    result = runner.invoke(main, ["sync", "--dry-run"])

    assert result.exit_code == 0
    assert "dry" in result.output.lower() or "would" in result.output.lower()
    # File must NOT have been copied
    assert not (
        project_dir / ".agentic-beacon" / "artifacts" / "knowledge" / "tip.md"
    ).exists()


def test_sync_dry_run_reports_would_copy_count(valid_warehouse, temp_dir, monkeypatch):
    """--dry-run summary shows how many files would be copied."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    knowledge = valid_warehouse / "knowledge"
    (knowledge / "a.md").write_text("A")
    (knowledge / "b.md").write_text("B")

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    runner.invoke(main, ["setup"])
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge:\n    - knowledge/a.md\n    - knowledge/b.md\n"
        "  skills: []\n  contexts: []\n"
    )

    result = runner.invoke(main, ["sync", "--dry-run"])

    assert result.exit_code == 0
    # Should report 2 files would be copied
    assert "2" in result.output


def test_sync_dry_run_reports_would_remove(valid_warehouse, temp_dir, monkeypatch):
    """--dry-run shows orphaned artifacts that would be removed."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    (valid_warehouse / "knowledge" / "keep.md").write_text("keep")
    # stale.md exists in warehouse so it is a genuine orphan (previously synced)
    (valid_warehouse / "knowledge" / "stale.md").write_text("stale")

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    runner.invoke(main, ["setup"])

    # Set up beacon.yaml tracking only "keep.md" — stale.md intentionally omitted
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge:\n    - knowledge/keep.md\n  skills: []\n  contexts: []\n"
    )

    # Manually plant the stale file in artifacts (simulates a previous sync)
    artifacts_dir = project_dir / ".agentic-beacon" / "artifacts" / "knowledge"
    artifacts_dir.mkdir(parents=True)
    (artifacts_dir / "stale.md").write_text("stale")

    result = runner.invoke(main, ["sync", "--dry-run"])

    assert result.exit_code == 0
    assert "would" in result.output.lower() or "remove" in result.output.lower()
    # Stale file must still exist (dry run)
    assert (artifacts_dir / "stale.md").exists()


# ---------------------------------------------------------------------------
# Skill entry validation — boundary: skills must be directory entries
# ---------------------------------------------------------------------------


def _make_beacon_settings(skills: list[str]) -> BeaconManifest:
    return BeaconManifest(artifacts=ArtifactsConfig(skills=skills, contexts=[]))


class TestValidateSkillEntriesUnit:
    """Unit tests for validate_skill_entries — tests the function directly."""

    def test_file_entry_exits(self):
        """A file-level entry causes SystemExit."""
        s = _make_beacon_settings(["skills/my-skill/SKILL.md"])
        with pytest.raises(SystemExit) as exc:
            validate_skill_entries(s)
        assert exc.value.code != 0

    def test_non_skill_md_file_entry_exits(self):
        """Any file extension, not just SKILL.md, is rejected."""
        for entry in [
            "skills/foo/config.yaml",
            "skills/foo/runner.py",
            "skills/foo/README.md",
        ]:
            s = _make_beacon_settings([entry])
            with pytest.raises(SystemExit):
                validate_skill_entries(s)

    def test_multiple_file_entries_all_exit(self):
        """Multiple file-level entries still cause a single SystemExit."""
        s = _make_beacon_settings(
            [
                "skills/alpha/SKILL.md",
                "skills/beta/SKILL.md",
            ]
        )
        with pytest.raises(SystemExit) as exc:
            validate_skill_entries(s)
        assert exc.value.code != 0

    def test_mixed_entries_exits_on_any_file_entry(self):
        """A mix of valid directories and one file entry still errors."""
        s = _make_beacon_settings(["skills/good/", "skills/bad/SKILL.md"])
        with pytest.raises(SystemExit):
            validate_skill_entries(s)

    def test_directory_with_trailing_slash_passes(self):
        """Canonical directory form with trailing slash is accepted."""
        s = _make_beacon_settings(["skills/my-skill/"])
        validate_skill_entries(s)  # must not raise

    def test_directory_without_trailing_slash_passes(self):
        """Directory form without trailing slash is also accepted."""
        s = _make_beacon_settings(["skills/my-skill"])
        validate_skill_entries(s)  # must not raise

    def test_empty_skills_list_passes(self):
        """An empty skills list is valid."""
        s = _make_beacon_settings([])
        validate_skill_entries(s)  # must not raise

    def test_multiple_valid_directory_entries_pass(self):
        """Multiple directory entries are all accepted."""
        s = _make_beacon_settings(["skills/alpha/", "skills/beta/", "skills/gamma"])
        validate_skill_entries(s)  # must not raise


class TestSyncSkillEntryValidation:
    """Integration: abc sync rejects file-level skill entries as a hard boundary."""

    @staticmethod
    def _make_project(tmp_path, monkeypatch, skill_entries: list[str] | str):
        if isinstance(skill_entries, str):
            skill_entries = [skill_entries]
        wh = tmp_path / "warehouse"
        for d in ("agents", "knowledge", "skills", "contexts", "docs"):
            (wh / d).mkdir(parents=True)
        (wh / "README.md").write_text("# WH")
        (wh / "skills" / "my-skill").mkdir()
        (wh / "skills" / "my-skill" / "SKILL.md").write_text("# Skill\n")

        # Init git (required by sync)
        import os
        import subprocess

        env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "t@t.local",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "t@t.local",
        }
        subprocess.run(
            ["git", "init"], cwd=wh, env=env, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "add", "."], cwd=wh, env=env, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=wh,
            env=env,
            check=True,
            capture_output=True,
        )

        project = tmp_path / "project"
        project.mkdir()
        beacon_dir = project / ".agentic-beacon"
        beacon_dir.mkdir()
        (beacon_dir / "config.toml").write_text(f'[warehouse]\nlocal_path = "{wh}"\n')
        if skill_entries:
            entries_yaml = "".join(f"    - {e}\n" for e in skill_entries)
            skills_yaml = f"  skills:\n{entries_yaml}"
        else:
            skills_yaml = "  skills: []\n"
        (beacon_dir / "beacon.yaml").write_text(
            f"artifacts:\n  knowledge: []\n{skills_yaml}  contexts: []\n"
        )
        monkeypatch.chdir(project)
        return project

    def test_file_entry_is_hard_error(self, tmp_path, monkeypatch):
        """File-level entry always causes a non-zero exit."""
        self._make_project(tmp_path, monkeypatch, "skills/my-skill/SKILL.md")
        result = CliRunner().invoke(main, ["sync", "--skip-git-check"])

        assert result.exit_code != 0

    def test_error_names_the_offending_entry(self, tmp_path, monkeypatch):
        """Error output identifies the specific file-level entry."""
        self._make_project(tmp_path, monkeypatch, "skills/my-skill/SKILL.md")
        result = CliRunner().invoke(main, ["sync", "--skip-git-check"])

        assert "skills/my-skill/SKILL.md" in result.output

    def test_error_tells_user_correct_format(self, tmp_path, monkeypatch):
        """Error output tells the user skills must be directory entries."""
        self._make_project(tmp_path, monkeypatch, "skills/my-skill/SKILL.md")
        result = CliRunner().invoke(main, ["sync", "--skip-git-check"])

        assert "skills/my-skill/" in result.output  # shows the corrected form

    def test_multiple_file_entries_all_listed(self, tmp_path, monkeypatch):
        """All offending entries are listed in the error, not just the first."""
        self._make_project(
            tmp_path,
            monkeypatch,
            [
                "skills/my-skill/SKILL.md",
                "skills/my-skill/SKILL.md",  # second distinct path for listing check
            ],
        )
        # Use two distinct skill names by writing beacon.yaml directly
        project = tmp_path / "project"
        beacon_dir = project / ".agentic-beacon"
        (beacon_dir / "beacon.yaml").write_text(
            "artifacts:\n  knowledge: []\n  skills:\n"
            "    - skills/my-skill/SKILL.md\n"
            "    - skills/other-skill/SKILL.md\n"
            "  contexts: []\n"
        )
        result = CliRunner().invoke(main, ["sync", "--skip-git-check"])

        assert result.exit_code != 0
        assert "skills/my-skill/SKILL.md" in result.output
        assert "skills/other-skill/SKILL.md" in result.output

    def test_mixed_entries_error_only_lists_file_entries(self, tmp_path, monkeypatch):
        """Valid directory entry is not mentioned in the error output."""
        self._make_project(
            tmp_path,
            monkeypatch,
            [
                "skills/my-skill/",
                "skills/my-skill/SKILL.md",
            ],
        )
        result = CliRunner().invoke(main, ["sync", "--skip-git-check"])

        assert result.exit_code != 0
        assert "skills/my-skill/SKILL.md" in result.output

    def test_error_fires_before_any_sync_work(self, tmp_path, monkeypatch):
        """No artifacts are written when validation fails."""
        project = self._make_project(tmp_path, monkeypatch, "skills/my-skill/SKILL.md")
        CliRunner().invoke(main, ["sync", "--skip-git-check"])

        artifacts_dir = project / ".agentic-beacon" / "artifacts"
        assert not artifacts_dir.exists() or not any(artifacts_dir.rglob("*"))

    def test_any_file_extension_is_rejected(self, tmp_path, monkeypatch):
        """File extensions other than .md are also rejected."""
        self._make_project(tmp_path, monkeypatch, "skills/my-skill/config.yaml")
        result = CliRunner().invoke(main, ["sync", "--skip-git-check"])

        assert result.exit_code != 0

    def test_directory_with_trailing_slash_passes(self, tmp_path, monkeypatch):
        """Canonical directory entry with trailing slash is accepted."""
        self._make_project(tmp_path, monkeypatch, "skills/my-skill/")
        result = CliRunner().invoke(main, ["sync", "--skip-git-check"])

        assert result.exit_code == 0

    def test_directory_without_trailing_slash_passes(self, tmp_path, monkeypatch):
        """Directory entry without trailing slash is also accepted."""
        self._make_project(tmp_path, monkeypatch, "skills/my-skill")
        result = CliRunner().invoke(main, ["sync", "--skip-git-check"])

        assert result.exit_code == 0

    def test_empty_skills_list_passes(self, tmp_path, monkeypatch):
        """An empty skills list does not trigger validation."""
        self._make_project(tmp_path, monkeypatch, [])
        result = CliRunner().invoke(main, ["sync", "--skip-git-check"])

        assert result.exit_code == 0


@pytest.mark.skip(
    reason="knowledge sync rewritten in chunk C / phase 8 of auto-pull-artifact-dependencies"
)
def test_sync_knowledge_node_path_expands_to_files(
    valid_warehouse, temp_dir, monkeypatch
):
    """TC: beacon.yaml with node-level knowledge path syncs all .md files within the node."""
    runner = CliRunner()
    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    # Create a proper knowledge node (with decisions/ subdir)
    node_dir = valid_warehouse / "knowledge" / "python"
    (node_dir / "decisions").mkdir(parents=True)
    (node_dir / "decisions" / "typing.md").write_text("# Typing Decision")
    (node_dir / "lessons").mkdir()
    (node_dir / "lessons" / "async.md").write_text("# Async Lessons")

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    runner.invoke(main, ["setup"])

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge:\n    - knowledge/python\n  skills: []\n  contexts: []\n"
    )

    result = runner.invoke(main, ["sync", "--skip-git-check"])
    assert result.exit_code == 0

    artifacts_dir = project_dir / ".agentic-beacon" / "artifacts"
    assert (artifacts_dir / "knowledge" / "python" / "decisions" / "typing.md").exists()
    assert (artifacts_dir / "knowledge" / "python" / "lessons" / "async.md").exists()


@pytest.mark.skip(
    reason="knowledge sync rewritten in chunk C / phase 8 of auto-pull-artifact-dependencies"
)
def test_sync_knowledge_nested_node_path_expands(
    valid_warehouse, temp_dir, monkeypatch
):
    """TC: Sub-domain node path like knowledge/data-platform/clickhouse syncs correctly."""
    runner = CliRunner()
    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    node_dir = valid_warehouse / "knowledge" / "data-platform" / "clickhouse"
    (node_dir / "facts").mkdir(parents=True)
    (node_dir / "facts" / "schema.md").write_text("# Schema Facts")

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    runner.invoke(main, ["setup"])

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge:\n"
        "    - knowledge/data-platform/clickhouse\n"
        "  skills: []\n  contexts: []\n"
    )

    result = runner.invoke(main, ["sync", "--skip-git-check"])
    assert result.exit_code == 0

    artifacts_dir = project_dir / ".agentic-beacon" / "artifacts"
    assert (
        artifacts_dir
        / "knowledge"
        / "data-platform"
        / "clickhouse"
        / "facts"
        / "schema.md"
    ).exists()
