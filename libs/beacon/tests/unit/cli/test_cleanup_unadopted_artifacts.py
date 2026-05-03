"""Unit tests for cleanup_unadopted_artifacts.

Test Cases:
- TC1: clean file listed and removed on confirm
- TC2: locally modified file still listed and removed (no special flag shown)
- TC3: file not in warehouse still listed and removed
- TC4: user declines confirmation → files kept
- TC5: directory-level unadoption (skill dir) → all files collected and listed
- TC6: no local files for unadopted entry → no prompt shown (nothing to do)
- TC7: skill unadoption with project_root → live agent copies are also deleted
"""

from click.testing import CliRunner


def _invoke_cleanup(
    unadoptions, artifacts_dir, warehouse_path, confirm=True, project_root=None
):
    """Call cleanup_unadopted_artifacts via Click's test CliRunner."""
    import click
    from beacon.domains.adoption.apply import cleanup_unadopted_artifacts

    @click.command()
    def _cmd():
        cleanup_unadopted_artifacts(
            unadoptions, artifacts_dir, warehouse_path, project_root=project_root
        )

    runner = CliRunner()
    input_str = "y\n" if confirm else "n\n"
    return runner.invoke(_cmd, input=input_str)


class TestCleanupUnadoptedArtifacts:
    def test_tc1_clean_file_listed_and_removed_on_confirm(self, tmp_path):
        """TC1: file is listed and removed on confirm."""
        artifacts = tmp_path / "artifacts"
        warehouse = tmp_path / "warehouse"
        (artifacts / "contexts").mkdir(parents=True)
        (warehouse / "contexts").mkdir(parents=True)

        content = "# Context doc"
        (artifacts / "contexts" / "foo.md").write_text(content)
        (warehouse / "contexts" / "foo.md").write_text(content)

        result = _invoke_cleanup(
            ["contexts/foo.md"], artifacts, warehouse, confirm=True
        )

        assert result.exit_code == 0
        assert "foo.md" in result.output
        assert not (artifacts / "contexts" / "foo.md").exists()

    def test_tc2_modified_file_listed_and_removed(self, tmp_path):
        """TC2: locally modified file is listed and removed without special flag."""
        artifacts = tmp_path / "artifacts"
        warehouse = tmp_path / "warehouse"
        (artifacts / "contexts").mkdir(parents=True)
        (warehouse / "contexts").mkdir(parents=True)

        (artifacts / "contexts" / "foo.md").write_text("# Local edit")
        (warehouse / "contexts" / "foo.md").write_text("# Warehouse version")

        result = _invoke_cleanup(
            ["contexts/foo.md"], artifacts, warehouse, confirm=True
        )

        assert result.exit_code == 0
        assert "foo.md" in result.output
        assert not (artifacts / "contexts" / "foo.md").exists()

    def test_tc3_file_not_in_warehouse_still_listed(self, tmp_path):
        """TC3: file exists locally but not in warehouse → still listed."""
        artifacts = tmp_path / "artifacts"
        warehouse = tmp_path / "warehouse"
        (artifacts / "contexts").mkdir(parents=True)
        warehouse.mkdir(parents=True)

        (artifacts / "contexts" / "local-only.md").write_text("# Local only")

        result = _invoke_cleanup(
            ["contexts/local-only.md"], artifacts, warehouse, confirm=True
        )

        assert result.exit_code == 0
        assert "local-only.md" in result.output

    def test_tc4_user_declines_files_kept(self, tmp_path):
        """TC4: user answers 'n' → files are not removed."""
        artifacts = tmp_path / "artifacts"
        warehouse = tmp_path / "warehouse"
        (artifacts / "contexts").mkdir(parents=True)
        (warehouse / "contexts").mkdir(parents=True)

        content = "# Content"
        (artifacts / "contexts" / "foo.md").write_text(content)
        (warehouse / "contexts" / "foo.md").write_text(content)

        result = _invoke_cleanup(
            ["contexts/foo.md"], artifacts, warehouse, confirm=False
        )

        assert "Skipped" in result.output
        assert (artifacts / "contexts" / "foo.md").exists()

    def test_tc5_directory_unadoption_collects_all_files(self, tmp_path):
        """TC5: unadopting a skill dir collects all files within it."""
        artifacts = tmp_path / "artifacts"
        warehouse = tmp_path / "warehouse"
        skill = artifacts / "skills" / "my-tool"
        skill.mkdir(parents=True)
        wskill = warehouse / "skills" / "my-tool"
        wskill.mkdir(parents=True)

        content = "# Skill"
        (skill / "SKILL.md").write_text(content)
        (skill / "usage.md").write_text(content)
        (wskill / "SKILL.md").write_text(content)
        (wskill / "usage.md").write_text(content)

        result = _invoke_cleanup(["skills/my-tool"], artifacts, warehouse, confirm=True)

        assert "SKILL.md" in result.output
        assert "usage.md" in result.output
        assert not (artifacts / "skills" / "my-tool").exists()

    def test_tc6_no_local_files_no_prompt(self, tmp_path):
        """TC6: unadopted entry has no local files → silent, no prompt."""
        artifacts = tmp_path / "artifacts"
        warehouse = tmp_path / "warehouse"
        artifacts.mkdir(parents=True)
        warehouse.mkdir(parents=True)

        result = _invoke_cleanup(["contexts/nonexistent.md"], artifacts, warehouse)

        assert result.exit_code == 0
        assert "Unlink" not in result.output
        assert "Delete" not in result.output

    def test_tc7_skill_unadoption_also_deletes_live_agent_copies(self, tmp_path):
        """TC7: unadopting a skill with project_root removes live .opencode and .claude copies."""
        project_root = tmp_path / "project"
        artifacts = project_root / ".agentic-beacon" / "artifacts"
        warehouse = tmp_path / "warehouse"

        content = "# Skill content"

        # Staging copy
        staging_skill = artifacts / "skills" / "my-tool"
        staging_skill.mkdir(parents=True)
        (staging_skill / "SKILL.md").write_text(content)

        # Warehouse copy
        warehouse_skill = warehouse / "skills" / "my-tool"
        warehouse_skill.mkdir(parents=True)
        (warehouse_skill / "SKILL.md").write_text(content)

        # Live opencode copy
        (project_root / "opencode.json").write_text("{}")
        opencode_skill = project_root / ".opencode" / "skills" / "my-tool"
        opencode_skill.mkdir(parents=True)
        (opencode_skill / "SKILL.md").write_text(content)

        # Live claudecode copy
        claudecode_skill = project_root / ".claude" / "skills" / "my-tool"
        claudecode_skill.mkdir(parents=True)
        (claudecode_skill / "SKILL.md").write_text(content)

        result = _invoke_cleanup(
            ["skills/my-tool/"],
            artifacts,
            warehouse,
            confirm=True,
            project_root=project_root,
        )

        assert result.exit_code == 0
        assert not (staging_skill / "SKILL.md").exists(), (
            "staging copy should be removed"
        )
        assert not (opencode_skill / "SKILL.md").exists(), (
            ".opencode live copy should be removed"
        )
        assert not (claudecode_skill / "SKILL.md").exists(), (
            ".claude live copy should be removed"
        )
