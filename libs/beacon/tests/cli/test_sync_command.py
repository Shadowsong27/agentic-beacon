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

import yaml
from beacon.cli import (
    _detect_legacy_skill_entries,
    _migrate_beacon_yaml_skill_entries,
    main,
)
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


class TestDetectLegacySkillEntries:
    def test_detects_skill_md_entry(self):
        s = _make_beacon_settings(["skills/my-skill/SKILL.md"])
        assert _detect_legacy_skill_entries(s) == ["skills/my-skill/SKILL.md"]

    def test_detects_multiple_legacy_entries(self):
        s = _make_beacon_settings(
            ["skills/a/SKILL.md", "skills/b/SKILL.md", "skills/c/"]
        )
        legacy = _detect_legacy_skill_entries(s)
        assert legacy == ["skills/a/SKILL.md", "skills/b/SKILL.md"]

    def test_no_legacy_when_directory_entries(self):
        s = _make_beacon_settings(["skills/my-skill/", "skills/other"])
        assert _detect_legacy_skill_entries(s) == []

    def test_empty_skills_list(self):
        s = _make_beacon_settings([])
        assert _detect_legacy_skill_entries(s) == []


class TestMigrateBeaconYamlSkillEntries:
    def test_rewrites_file_entry_to_directory(self, tmp_path):
        beacon_yaml = tmp_path / "beacon.yaml"
        beacon_yaml.write_text(
            "artifacts:\n  knowledge: []\n"
            "  skills:\n    - skills/my-skill/SKILL.md\n  contexts: []\n"
        )
        _migrate_beacon_yaml_skill_entries(beacon_yaml, ["skills/my-skill/SKILL.md"])

        data = yaml.safe_load(beacon_yaml.read_text())
        assert data["artifacts"]["skills"] == ["skills/my-skill"]

    def test_rewrites_only_legacy_entries(self, tmp_path):
        beacon_yaml = tmp_path / "beacon.yaml"
        beacon_yaml.write_text(
            "artifacts:\n  knowledge: []\n"
            "  skills:\n    - skills/old/SKILL.md\n    - skills/new/\n  contexts: []\n"
        )
        _migrate_beacon_yaml_skill_entries(beacon_yaml, ["skills/old/SKILL.md"])

        data = yaml.safe_load(beacon_yaml.read_text())
        skills = data["artifacts"]["skills"]
        assert any(
            s.startswith("skills/old") and not s.endswith("SKILL.md") for s in skills
        )
        assert any(s.startswith("skills/new") for s in skills)
        assert "skills/old/SKILL.md" not in skills

    def test_deduplicates_after_migration(self, tmp_path):
        """If the directory entry already exists, don't add a duplicate."""
        beacon_yaml = tmp_path / "beacon.yaml"
        beacon_yaml.write_text(
            "artifacts:\n  knowledge: []\n"
            "  skills:\n    - skills/my-skill/SKILL.md\n    - skills/my-skill/\n  contexts: []\n"
        )
        _migrate_beacon_yaml_skill_entries(beacon_yaml, ["skills/my-skill/SKILL.md"])

        data = yaml.safe_load(beacon_yaml.read_text())
        assert data["artifacts"]["skills"].count("skills/my-skill") == 1


class TestSyncLegacyMigrationCheck:
    """Integration: abc sync migration check via CLI."""

    @staticmethod
    def _project_with_legacy_skill(tmp_path, monkeypatch):
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
            "artifacts:\n  knowledge: []\n"
            "  skills:\n    - skills/my-skill/SKILL.md\n  contexts: []\n"
        )
        monkeypatch.chdir(project)
        return project

    def test_warning_shown_for_legacy_entry(self, tmp_path, monkeypatch):
        """Legacy entries produce a warning in sync output."""
        self._project_with_legacy_skill(tmp_path, monkeypatch)
        runner = CliRunner()
        result = runner.invoke(main, ["sync", "--skip-git-check"])

        assert result.exit_code == 0
        assert "legacy" in result.output.lower() or "SKILL.md" in result.output

    def test_skip_migration_check_suppresses_warning(self, tmp_path, monkeypatch):
        """--skip-migration-check suppresses the migration warning entirely."""
        self._project_with_legacy_skill(tmp_path, monkeypatch)
        runner = CliRunner()
        result = runner.invoke(
            main, ["sync", "--skip-git-check", "--skip-migration-check"]
        )

        assert result.exit_code == 0
        assert "legacy" not in result.output.lower()
        assert "migrate" not in result.output.lower()

    def test_interactive_yes_migrates_beacon_yaml(self, tmp_path, monkeypatch):
        """Answering 'y' to the migration prompt rewrites beacon.yaml."""
        project = self._project_with_legacy_skill(tmp_path, monkeypatch)
        monkeypatch.setattr("beacon.cli._is_interactive", lambda: True)
        runner = CliRunner()
        result = runner.invoke(
            main, ["sync", "--skip-git-check"], input="y\n", catch_exceptions=False
        )

        assert result.exit_code == 0
        beacon_yaml = project / ".agentic-beacon" / "beacon.yaml"
        data = yaml.safe_load(beacon_yaml.read_text())
        assert "skills/my-skill" in data["artifacts"]["skills"]
        assert "skills/my-skill/SKILL.md" not in data["artifacts"]["skills"]

    def test_interactive_no_blocks_sync(self, tmp_path, monkeypatch):
        """Answering 'n' to the migration prompt exits with an error."""
        self._project_with_legacy_skill(tmp_path, monkeypatch)
        monkeypatch.setattr("beacon.cli._is_interactive", lambda: True)
        runner = CliRunner()
        result = runner.invoke(main, ["sync", "--skip-git-check"], input="n\n")

        assert result.exit_code != 0
        assert "Aborted" in result.output or "manually" in result.output

    def test_no_warning_when_no_legacy_entries(self, tmp_path, monkeypatch):
        """No migration warning when beacon.yaml uses directory-style entries."""
        wh = tmp_path / "warehouse"
        for d in ("agents", "knowledge", "skills", "contexts", "docs"):
            (wh / d).mkdir(parents=True)
        (wh / "README.md").write_text("# WH")
        (wh / "skills" / "my-skill").mkdir()
        (wh / "skills" / "my-skill" / "SKILL.md").write_text("# Skill\n")

        project = tmp_path / "project2"
        project.mkdir()
        beacon_dir = project / ".agentic-beacon"
        beacon_dir.mkdir()
        (beacon_dir / "config.toml").write_text(f'[warehouse]\nlocal_path = "{wh}"\n')
        (beacon_dir / "beacon.yaml").write_text(
            "artifacts:\n  knowledge: []\n"
            "  skills:\n    - skills/my-skill/\n  contexts: []\n"
        )
        monkeypatch.chdir(project)

        runner = CliRunner()
        result = runner.invoke(main, ["sync", "--skip-git-check"])

        assert result.exit_code == 0
        assert "legacy" not in result.output.lower()
        assert "migrate" not in result.output.lower()
