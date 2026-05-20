"""Tests for abc doctor command."""

import json
import subprocess
from pathlib import Path

import pytest
from beacon.cli.main import main
from beacon.core.manifest.beacon import BeaconManifest
from click.testing import CliRunner


def _setup_project(
    tmp_path: Path,
    monkeypatch,
    *,
    beacon_yaml_content: str = "artifacts:\n  contexts: []\n  skills: []\n  knowledge: []\n",
    init_git: bool = True,
) -> tuple[Path, Path]:
    """Create a connected project and return (project_dir, warehouse_dir)."""
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    (warehouse / "contexts").mkdir()
    (warehouse / "skills").mkdir()
    (warehouse / "knowledge").mkdir()

    if init_git:
        subprocess.run(
            ["git", "init", str(warehouse)],
            capture_output=True,
            check=False,
        )

    beacon_dir = project / ".agentic-beacon"
    beacon_dir.mkdir()
    # Write config.toml (warehouse connection)
    (beacon_dir / "config.toml").write_text(
        f'[warehouse]\nlocal_path = "{warehouse}"\n'
    )
    # Write beacon.yaml
    (beacon_dir / "beacon.yaml").write_text(beacon_yaml_content)

    return project, warehouse


class TestDoctorHealthyProject:
    def test_all_checks_pass(self, tmp_path, monkeypatch):
        """All checks green when warehouse connected, yaml valid, entries match warehouse."""
        project, warehouse = _setup_project(tmp_path, monkeypatch)

        (warehouse / "contexts" / "team.md").write_text("# Team")
        skill_dir = warehouse / "skills" / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\ndescription: Skill\n---\n")
        (warehouse / "knowledge" / "python" / "facts").mkdir(parents=True)
        (warehouse / "knowledge" / "python" / "facts" / "basics.md").write_text(
            "# Python"
        )

        (project / ".agentic-beacon" / "beacon.yaml").write_text(
            "artifacts:\n"
            "  contexts:\n    - contexts/team.md\n"
            "  skills:\n    - skills/my-skill/\n"
            "  knowledge:\n    - knowledge/python\n"
        )

        runner = CliRunner()
        result = runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "✓" in result.output
        assert "1 issue" not in result.output

    def test_empty_entries_no_issues(self, tmp_path, monkeypatch):
        """Empty artifact lists pass all checks."""
        _setup_project(tmp_path, monkeypatch)
        runner = CliRunner()
        result = runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "Everything looks good" in result.output


class TestDoctorKnowledgeFilePaths:
    @pytest.mark.skip(
        reason="knowledge field removed from manifest; doctor knowledge checks deferred"
    )
    def test_detects_file_level_md_path(self, tmp_path, monkeypatch):
        """Path ending in .md is detected as a file-level issue."""
        _setup_project(
            tmp_path,
            monkeypatch,
            beacon_yaml_content=(
                "artifacts:\n  contexts: []\n  skills: []\n"
                "  knowledge:\n    - knowledge/python/decisions/typing.md\n"
            ),
        )
        runner = CliRunner()
        result = runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "file-level" in result.output.lower()
        assert "knowledge/python" in result.output

    @pytest.mark.skip(
        reason="knowledge field removed from manifest; doctor knowledge checks deferred"
    )
    def test_detects_subtype_segment_path(self, tmp_path, monkeypatch):
        """Path containing decisions/ segment is detected as file-level."""
        _setup_project(
            tmp_path,
            monkeypatch,
            beacon_yaml_content=(
                "artifacts:\n  contexts: []\n  skills: []\n"
                "  knowledge:\n    - knowledge/data-platform/clickhouse/lessons/bar.md\n"
            ),
        )
        runner = CliRunner()
        result = runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "file-level" in result.output.lower()
        assert "knowledge/data-platform/clickhouse" in result.output

    @pytest.mark.skip(
        reason="knowledge field removed from manifest; doctor knowledge checks deferred"
    )
    def test_fix_migrates_file_paths_to_node_level(self, tmp_path, monkeypatch):
        """--fix rewrites file-level entries to their node paths in beacon.yaml."""
        project, warehouse = _setup_project(
            tmp_path,
            monkeypatch,
            beacon_yaml_content=(
                "artifacts:\n  contexts: []\n  skills: []\n"
                "  knowledge:\n"
                "    - knowledge/python/decisions/typing.md\n"
                "    - knowledge/python/decisions/async.md\n"
            ),
        )
        (warehouse / "knowledge" / "python" / "decisions").mkdir(parents=True)

        runner = CliRunner()
        result = runner.invoke(main, ["doctor", "--fix"])
        assert result.exit_code == 0

        beacon_yaml = project / ".agentic-beacon" / "beacon.yaml"
        updated = BeaconManifest.from_yaml(beacon_yaml)
        assert updated.artifacts.knowledge == ["knowledge/python"]

    @pytest.mark.skip(
        reason="knowledge field removed from manifest; doctor knowledge checks deferred"
    )
    def test_fix_deduplicates_same_node(self, tmp_path, monkeypatch):
        """--fix deduplicates multiple file paths pointing to the same node."""
        project, _ = _setup_project(
            tmp_path,
            monkeypatch,
            beacon_yaml_content=(
                "artifacts:\n  contexts: []\n  skills: []\n"
                "  knowledge:\n"
                "    - knowledge/python/decisions/foo.md\n"
                "    - knowledge/python/lessons/bar.md\n"
                "    - knowledge/data-platform/facts/baz.md\n"
            ),
        )
        runner = CliRunner()
        result = runner.invoke(main, ["doctor", "--fix"])
        assert result.exit_code == 0

        beacon_yaml = project / ".agentic-beacon" / "beacon.yaml"
        updated = BeaconManifest.from_yaml(beacon_yaml)
        assert set(updated.artifacts.knowledge) == {
            "knowledge/python",
            "knowledge/data-platform",
        }

    @pytest.mark.skip(
        reason="knowledge field removed from manifest; doctor knowledge checks deferred"
    )
    def test_node_level_path_no_issue(self, tmp_path, monkeypatch):
        """Node-level knowledge path (no subtype segment, exists as node) passes."""
        project, warehouse = _setup_project(tmp_path, monkeypatch)
        (warehouse / "knowledge" / "python" / "facts").mkdir(parents=True)
        (project / ".agentic-beacon" / "beacon.yaml").write_text(
            "artifacts:\n  contexts: []\n  skills: []\n"
            "  knowledge:\n    - knowledge/python\n"
        )
        runner = CliRunner()
        result = runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "file-level" not in result.output.lower()


class TestDoctorMissingArtifacts:
    @pytest.mark.skip(
        reason="knowledge field removed from manifest; doctor knowledge checks deferred"
    )
    def test_missing_knowledge_node_flagged(self, tmp_path, monkeypatch):
        """Knowledge entry pointing to non-existent warehouse dir is flagged."""
        _setup_project(
            tmp_path,
            monkeypatch,
            beacon_yaml_content=(
                "artifacts:\n  contexts: []\n  skills: []\n"
                "  knowledge:\n    - knowledge/nonexistent\n"
            ),
        )
        runner = CliRunner()
        result = runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "missing" in result.output.lower() or "✗" in result.output

    def test_missing_skill_flagged(self, tmp_path, monkeypatch):
        """Skill entry pointing to non-existent directory is flagged."""
        _setup_project(
            tmp_path,
            monkeypatch,
            beacon_yaml_content=(
                "artifacts:\n  contexts: []\n"
                "  skills:\n    - skills/ghost-skill/\n"
                "  knowledge: []\n"
            ),
        )
        runner = CliRunner()
        result = runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "missing" in result.output.lower() or "✗" in result.output

    def test_missing_context_flagged(self, tmp_path, monkeypatch):
        """Context entry pointing to non-existent file is flagged."""
        _setup_project(
            tmp_path,
            monkeypatch,
            beacon_yaml_content=(
                "artifacts:\n"
                "  contexts:\n    - contexts/ghost.md\n"
                "  skills: []\n  knowledge: []\n"
            ),
        )
        runner = CliRunner()
        result = runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "missing" in result.output.lower() or "✗" in result.output


class TestDoctorProjectSideChecks:
    def test_catches_multiple_broken_links(self, tmp_path, monkeypatch):
        """Seed a project with multiple broken links; doctor catches each."""
        project, warehouse = _setup_project(tmp_path, monkeypatch, init_git=False)

        # 1. Dangling symlink
        artifacts = project / ".agentic-beacon" / "artifacts"
        dangling = artifacts / "contexts" / "dangling.md"
        dangling.parent.mkdir(parents=True)
        dangling.symlink_to(warehouse / "contexts" / "dangling.md")

        # 2. Symlink outside warehouse
        outside = tmp_path / "outside.md"
        outside.write_text("x")
        bad_link = artifacts / "contexts" / "outside.md"
        bad_link.symlink_to(outside)

        # 3. Regular file where symlink should be
        regular = artifacts / "skills" / "regular-skill" / "SKILL.md"
        regular.parent.mkdir(parents=True)
        regular.write_text("regular file")

        # 4. Broken @path reference in CLAUDE.md
        (project / "CLAUDE.md").write_text("@nonexistent.md\n")

        # 5. Broken @path reference in opencode.json
        data = {"instructions": [".agentic-beacon/artifacts/contexts/ghost.md"]}
        (project / "opencode.json").write_text(json.dumps(data))

        # 6. Stale glob in beacon.yaml
        (project / ".agentic-beacon" / "beacon.yaml").write_text(
            "artifacts:\n  contexts:\n    - contexts/*.md\n  skills: []\n  agents: []\n"
        )

        runner = CliRunner()
        result = runner.invoke(main, ["doctor"])
        assert result.exit_code == 0

        output = result.output
        assert "Dangling symlink" in output
        assert "outside warehouse" in output
        assert "Regular file where symlink should be" in output
        assert "Broken reference" in output
        assert "Stale glob" in output
        assert "not a git working tree" in output


class TestDoctorNoProject:
    def test_no_beacon_dir_reports_error(self, tmp_path, monkeypatch):
        """Running doctor outside a project reports an error and exits cleanly."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "✗" in result.output or "error" in result.output.lower()
