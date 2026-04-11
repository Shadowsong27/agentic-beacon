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

from beacon.cli import main
from beacon.core.settings import ArtifactsConfig, BeaconSettings
from click.testing import CliRunner

# ========== Task 7.1: ABC Sync Command Implementation ==========


def test_sync_with_valid_configuration(valid_warehouse, temp_dir, monkeypatch):
    """TC1: First sync with empty artifacts dir → All artifacts copied."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    # Create test files in warehouse
    (valid_warehouse / "knowledge" / "test.md").write_text("# Test")

    # Connect warehouse
    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])

    # Create beacon.yaml
    runner.invoke(main, ["setup", "--manual"])
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge:\n    - knowledge/test.md\n  skills: []\n  contexts: []\n"
    )

    # Run sync
    result = runner.invoke(main, ["sync"])

    assert result.exit_code == 0
    assert "sync" in result.output.lower() or "✓" in result.output

    # Verify file was copied
    synced_file = (
        project_dir / ".agentic-beacon" / "artifacts" / "knowledge" / "test.md"
    )
    assert synced_file.exists()
    assert synced_file.read_text() == "# Test"


def test_sync_is_idempotent(valid_warehouse, temp_dir, monkeypatch):
    """TC2: Second sync with no changes → No files copied (idempotent)."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    # Setup
    (valid_warehouse / "knowledge" / "test.md").write_text("# Test")
    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    runner.invoke(main, ["setup", "--manual"])
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge:\n    - knowledge/test.md\n  skills: []\n  contexts: []\n"
    )

    # First sync
    result1 = runner.invoke(main, ["sync"])
    assert result1.exit_code == 0

    synced_file = (
        project_dir / ".agentic-beacon" / "artifacts" / "knowledge" / "test.md"
    )
    mtime1 = synced_file.stat().st_mtime

    # Second sync - should be idempotent
    result2 = runner.invoke(main, ["sync"])
    assert result2.exit_code == 0

    # File should not have been re-copied
    mtime2 = synced_file.stat().st_mtime
    assert mtime2 == mtime1


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
    runner.invoke(main, ["setup", "--manual"])
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge:\n    - knowledge/python/*.md\n  skills: []\n  contexts: []\n"
    )

    result = runner.invoke(main, ["sync"])

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

    result = runner.invoke(main, ["sync"])

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

    result = runner.invoke(main, ["sync"])

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
    runner.invoke(main, ["setup", "--manual"])

    # beacon.yaml with empty lists
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge: []\n  skills: []\n  contexts: []\n"
    )

    result = runner.invoke(main, ["sync"])

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
    runner.invoke(main, ["setup", "--manual"])
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
    runner.invoke(main, ["setup", "--manual"])
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
    runner.invoke(main, ["setup", "--manual"])

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
# Legacy skill entry migration check
# ---------------------------------------------------------------------------


def _make_beacon_settings(skills: list[str]) -> BeaconSettings:
    return BeaconSettings(
        artifacts=ArtifactsConfig(knowledge=[], skills=skills, contexts=[])
    )


class TestSyncSkillEntryValidation:
    """abc sync rejects file-level skill entries as a hard boundary."""

    @staticmethod
    def _make_project(tmp_path, monkeypatch, skill_entry: str):
        wh = tmp_path / "warehouse"
        for d in ("agents", "knowledge", "skills", "contexts", "docs"):
            (wh / d).mkdir(parents=True)
        (wh / "README.md").write_text("# WH")
        (wh / "skills" / "my-skill").mkdir()
        (wh / "skills" / "my-skill" / "SKILL.md").write_text("# Skill\n")

        project = tmp_path / "project"
        project.mkdir()
        beacon_dir = project / ".agentic-beacon"
        beacon_dir.mkdir()
        (beacon_dir / "config.toml").write_text(f'[warehouse]\nlocal_path = "{wh}"\n')
        (beacon_dir / "beacon.yaml").write_text(
            f"artifacts:\n  knowledge: []\n  skills:\n    - {skill_entry}\n  contexts: []\n"
        )
        monkeypatch.chdir(project)
        return project

    def test_file_entry_is_hard_error(self, tmp_path, monkeypatch):
        """File-level skill entries always cause a non-zero exit."""
        self._make_project(tmp_path, monkeypatch, "skills/my-skill/SKILL.md")
        runner = CliRunner()
        result = runner.invoke(main, ["sync", "--skip-git-check"])

        assert result.exit_code != 0
        assert "skills/my-skill/SKILL.md" in result.output

    def test_any_file_extension_is_rejected(self, tmp_path, monkeypatch):
        """Any file-level entry (not just SKILL.md) is rejected."""
        self._make_project(tmp_path, monkeypatch, "skills/my-skill/config.yaml")
        runner = CliRunner()
        result = runner.invoke(main, ["sync", "--skip-git-check"])

        assert result.exit_code != 0

    def test_directory_entry_passes(self, tmp_path, monkeypatch):
        """Directory-style entries do not trigger the validation error."""
        self._make_project(tmp_path, monkeypatch, "skills/my-skill/")
        runner = CliRunner()
        result = runner.invoke(main, ["sync", "--skip-git-check"])

        assert result.exit_code == 0
        assert "Error" not in result.output or "skill" not in result.output.lower()
