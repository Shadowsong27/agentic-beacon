"""Unit tests for beacon.domains.setup.diagnostics."""

import json

from beacon.core.manifest.beacon import BeaconManifest
from beacon.domains.setup.diagnostics import (
    _check_path_references,
    _check_platform,
    _check_stale_globs,
    _check_symlink_hygiene,
    _check_warehouse_git,
    _is_glob_pattern,
    run_project_diagnostics,
    run_project_health_checks,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_manifest(**kwargs) -> BeaconManifest:
    defaults = {"contexts": [], "skills": [], "agents": []}
    defaults.update(kwargs)
    return BeaconManifest(artifacts=defaults)


# ---------------------------------------------------------------------------
# _is_glob_pattern
# ---------------------------------------------------------------------------


class TestIsGlobPattern:
    def test_asterisk_is_glob(self):
        assert _is_glob_pattern("skills/*")

    def test_question_is_glob(self):
        assert _is_glob_pattern("contexts/?.md")

    def test_bracket_is_glob(self):
        assert _is_glob_pattern("agents/[ab].md")

    def test_plain_path_is_not_glob(self):
        assert not _is_glob_pattern("skills/my-skill/")


# ---------------------------------------------------------------------------
# Symlink hygiene
# ---------------------------------------------------------------------------


class TestSymlinkHygiene:
    def test_no_artifacts_dir_returns_empty(self, tmp_path):
        issues = _check_symlink_hygiene(tmp_path, tmp_path / "warehouse")
        assert issues == []

    def test_good_symlink_passes(self, tmp_path):
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()
        (warehouse / "contexts").mkdir()
        (warehouse / "contexts" / "team.md").write_text("# Team")

        artifacts = tmp_path / ".agentic-beacon" / "artifacts"
        artifacts.mkdir(parents=True)
        ctx_link = artifacts / "contexts" / "team.md"
        ctx_link.parent.mkdir(parents=True)
        ctx_link.symlink_to(warehouse / "contexts" / "team.md")

        issues = _check_symlink_hygiene(tmp_path, warehouse)
        assert issues == []

    def test_dangling_symlink_flagged(self, tmp_path):
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()

        artifacts = tmp_path / ".agentic-beacon" / "artifacts"
        artifacts.mkdir(parents=True)
        ctx_link = artifacts / "contexts" / "team.md"
        ctx_link.parent.mkdir(parents=True)
        ctx_link.symlink_to(warehouse / "contexts" / "team.md")

        issues = _check_symlink_hygiene(tmp_path, warehouse)
        assert len(issues) == 1
        assert "Dangling symlink" in issues[0].message
        assert issues[0].severity == "error"

    def test_symlink_outside_warehouse_flagged(self, tmp_path):
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()
        other = tmp_path / "other"
        other.mkdir()
        (other / "file.md").write_text("x")

        artifacts = tmp_path / ".agentic-beacon" / "artifacts"
        artifacts.mkdir(parents=True)
        ctx_link = artifacts / "contexts" / "team.md"
        ctx_link.parent.mkdir(parents=True)
        ctx_link.symlink_to(other / "file.md")

        issues = _check_symlink_hygiene(tmp_path, warehouse)
        assert len(issues) == 1
        assert "outside warehouse" in issues[0].message
        assert issues[0].severity == "error"

    def test_regular_file_where_symlink_should_be(self, tmp_path):
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()

        artifacts = tmp_path / ".agentic-beacon" / "artifacts"
        artifacts.mkdir(parents=True)
        ctx_file = artifacts / "contexts" / "team.md"
        ctx_file.parent.mkdir(parents=True)
        ctx_file.write_text("regular file")

        issues = _check_symlink_hygiene(tmp_path, warehouse)
        assert len(issues) == 1
        assert "Regular file where symlink should be" in issues[0].message
        assert issues[0].severity == "error"


# ---------------------------------------------------------------------------
# @path references
# ---------------------------------------------------------------------------


class TestPathReferences:
    def test_claude_md_broken_reference(self, tmp_path):
        (tmp_path / "CLAUDE.md").write_text("@nonexistent.md\n")
        manifest = _make_manifest()
        issues = _check_path_references(tmp_path, manifest)
        assert len(issues) == 1
        assert "Broken reference" in issues[0].message
        assert issues[0].severity == "error"

    def test_claude_md_unmanaged_reference(self, tmp_path):
        (tmp_path / ".agentic-beacon" / "artifacts" / "contexts").mkdir(parents=True)
        (
            tmp_path / ".agentic-beacon" / "artifacts" / "contexts" / "team.md"
        ).write_text("# Team")
        (tmp_path / "CLAUDE.md").write_text(
            "@.agentic-beacon/artifacts/contexts/team.md\n"
        )
        manifest = _make_manifest(contexts=[])
        issues = _check_path_references(tmp_path, manifest)
        assert len(issues) == 1
        assert "Unmanaged reference" in issues[0].message
        assert issues[0].severity == "warn"

    def test_claude_md_wired_reference_no_issue(self, tmp_path):
        (tmp_path / ".agentic-beacon" / "artifacts" / "contexts").mkdir(parents=True)
        (
            tmp_path / ".agentic-beacon" / "artifacts" / "contexts" / "team.md"
        ).write_text("# Team")
        (tmp_path / "CLAUDE.md").write_text(
            "@.agentic-beacon/artifacts/contexts/team.md\n"
        )
        manifest = _make_manifest(contexts=["contexts/team.md"])
        issues = _check_path_references(tmp_path, manifest)
        assert issues == []

    def test_claude_md_absolute_path_flagged_as_non_portable(self, tmp_path):
        (tmp_path / "CLAUDE.md").write_text(
            "@/Users/someone/warehouse/contexts/team.md\n"
        )
        manifest = _make_manifest()
        issues = _check_path_references(tmp_path, manifest)
        assert len(issues) == 1
        assert "Non-portable absolute path" in issues[0].message
        assert issues[0].severity == "error"

    def test_opencode_json_broken_reference(self, tmp_path):
        data = {"instructions": [".agentic-beacon/artifacts/contexts/ghost.md"]}
        (tmp_path / "opencode.json").write_text(json.dumps(data))
        manifest = _make_manifest()
        issues = _check_path_references(tmp_path, manifest)
        assert len(issues) == 1
        assert "Broken reference" in issues[0].message

    def test_opencode_json_wired_reference_no_issue(self, tmp_path):
        (tmp_path / ".agentic-beacon" / "artifacts" / "contexts").mkdir(parents=True)
        (
            tmp_path / ".agentic-beacon" / "artifacts" / "contexts" / "team.md"
        ).write_text("# Team")
        data = {"instructions": [".agentic-beacon/artifacts/contexts/team.md"]}
        (tmp_path / "opencode.json").write_text(json.dumps(data))
        manifest = _make_manifest(contexts=["contexts/team.md"])
        issues = _check_path_references(tmp_path, manifest)
        assert issues == []

    def test_opencode_json_non_path_instructions_skipped(self, tmp_path):
        data = {"instructions": ["Be helpful", "Use Python"]}
        (tmp_path / "opencode.json").write_text(json.dumps(data))
        manifest = _make_manifest()
        issues = _check_path_references(tmp_path, manifest)
        assert issues == []

    def test_bare_artifact_path_resolved(self, tmp_path):
        (tmp_path / ".agentic-beacon" / "artifacts" / "contexts").mkdir(parents=True)
        (
            tmp_path / ".agentic-beacon" / "artifacts" / "contexts" / "team.md"
        ).write_text("# Team")
        (tmp_path / "CLAUDE.md").write_text("@contexts/team.md\n")
        manifest = _make_manifest(contexts=["contexts/team.md"])
        issues = _check_path_references(tmp_path, manifest)
        assert issues == []

    def test_glob_entry_matches_referenced_path(self, tmp_path):
        (tmp_path / ".agentic-beacon" / "artifacts" / "contexts").mkdir(parents=True)
        (tmp_path / ".agentic-beacon" / "artifacts" / "contexts" / "foo.md").write_text(
            "# Foo"
        )
        (tmp_path / "CLAUDE.md").write_text(
            "@.agentic-beacon/artifacts/contexts/foo.md\n"
        )
        manifest = _make_manifest(contexts=["contexts/*.md"])
        issues = _check_path_references(tmp_path, manifest)
        assert issues == []

    def test_glob_entry_does_not_match_other_directory(self, tmp_path):
        (tmp_path / ".agentic-beacon" / "artifacts" / "skills" / "foo").mkdir(
            parents=True
        )
        (
            tmp_path / ".agentic-beacon" / "artifacts" / "skills" / "foo" / "SKILL.md"
        ).write_text("# Skill")
        (tmp_path / "CLAUDE.md").write_text(
            "@.agentic-beacon/artifacts/skills/foo/SKILL.md\n"
        )
        manifest = _make_manifest(contexts=["contexts/*.md"])
        issues = _check_path_references(tmp_path, manifest)
        assert len(issues) == 1
        assert "Unmanaged reference" in issues[0].message
        assert issues[0].severity == "warn"

    def test_project_local_existing_reference_not_warned(self, tmp_path):
        (tmp_path / "AGENTS.md").write_text("# Agents")
        (tmp_path / "CLAUDE.md").write_text("@AGENTS.md\n")
        manifest = _make_manifest()
        issues = _check_path_references(tmp_path, manifest)
        assert issues == []

    def test_project_local_missing_reference_is_warned(self, tmp_path):
        (tmp_path / "CLAUDE.md").write_text("@docs/missing.md\n")
        manifest = _make_manifest()
        issues = _check_path_references(tmp_path, manifest)
        assert len(issues) == 1
        assert "Broken reference" in issues[0].message
        assert issues[0].severity == "error"

    def test_artifact_reference_unmanaged_still_warned(self, tmp_path):
        (tmp_path / ".agentic-beacon" / "artifacts" / "contexts").mkdir(parents=True)
        (tmp_path / ".agentic-beacon" / "artifacts" / "contexts" / "foo.md").write_text(
            "# Foo"
        )
        (tmp_path / "CLAUDE.md").write_text(
            "@.agentic-beacon/artifacts/contexts/foo.md\n"
        )
        manifest = _make_manifest(contexts=[])
        issues = _check_path_references(tmp_path, manifest)
        assert len(issues) == 1
        assert "Unmanaged reference" in issues[0].message
        assert issues[0].severity == "warn"


# ---------------------------------------------------------------------------
# Stale globs
# ---------------------------------------------------------------------------


class TestStaleGlobs:
    def test_stale_glob_flagged(self, tmp_path):
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()
        (warehouse / "contexts").mkdir()

        manifest = _make_manifest(contexts=["contexts/*.md"])
        issues = _check_stale_globs(warehouse, manifest)
        assert len(issues) == 1
        assert "Stale glob" in issues[0].message
        assert "contexts/*.md" in issues[0].detail
        assert issues[0].severity == "error"

    def test_active_glob_passes(self, tmp_path):
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()
        (warehouse / "contexts").mkdir()
        (warehouse / "contexts" / "team.md").write_text("# Team")

        manifest = _make_manifest(contexts=["contexts/*.md"])
        issues = _check_stale_globs(warehouse, manifest)
        assert issues == []

    def test_non_glob_entries_ignored(self, tmp_path):
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()

        manifest = _make_manifest(skills=["skills/my-skill/"])
        issues = _check_stale_globs(warehouse, manifest)
        assert issues == []

    def test_stale_skill_glob(self, tmp_path):
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()
        (warehouse / "skills").mkdir()

        manifest = _make_manifest(skills=["skills/code-*/"])
        issues = _check_stale_globs(warehouse, manifest)
        assert len(issues) == 1
        assert "skills" in issues[0].message

    def test_stale_glob_directory_only_matches_is_flagged(self, tmp_path):
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()
        # Create directories matching the glob but no files inside
        (warehouse / "skills" / "code-review").mkdir(parents=True)
        (warehouse / "skills" / "code-lint").mkdir(parents=True)

        manifest = _make_manifest(skills=["skills/code-*/"])
        issues = _check_stale_globs(warehouse, manifest)
        assert len(issues) == 1
        assert "Stale glob" in issues[0].message
        assert "skills" in issues[0].message

    def test_no_manifest_returns_empty(self, tmp_path):
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()
        issues = _check_stale_globs(warehouse, None)
        assert issues == []


# ---------------------------------------------------------------------------
# Warehouse git sanity
# ---------------------------------------------------------------------------


class TestWarehouseGit:
    def test_git_present_no_issue(self, tmp_path):
        (tmp_path / ".git").mkdir()
        issues = _check_warehouse_git(tmp_path)
        assert issues == []

    def test_no_git_flagged(self, tmp_path):
        issues = _check_warehouse_git(tmp_path)
        assert len(issues) == 1
        assert "not a git working tree" in issues[0].message
        assert issues[0].severity == "warn"


# ---------------------------------------------------------------------------
# Platform check
# ---------------------------------------------------------------------------


class TestPlatformCheck:
    def test_darwin_no_issue(self, monkeypatch):
        monkeypatch.setattr("sys.platform", "darwin")
        issues = _check_platform()
        assert issues == []

    def test_linux_no_issue(self, monkeypatch):
        monkeypatch.setattr("sys.platform", "linux")
        issues = _check_platform()
        assert issues == []

    def test_windows_warns(self, monkeypatch):
        monkeypatch.setattr("sys.platform", "win32")
        issues = _check_platform()
        assert len(issues) == 1
        assert "Windows" in issues[0].message
        assert issues[0].severity == "warn"

    def test_cygwin_warns(self, monkeypatch):
        monkeypatch.setattr("sys.platform", "cygwin")
        issues = _check_platform()
        assert len(issues) == 1
        assert "Windows" in issues[0].message


# ---------------------------------------------------------------------------
# run_project_health_checks
# ---------------------------------------------------------------------------


class TestRunProjectHealthChecks:
    def test_all_checks_combined(self, tmp_path):
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()
        (warehouse / "contexts").mkdir()

        artifacts = tmp_path / ".agentic-beacon" / "artifacts"
        artifacts.mkdir(parents=True)
        bad_link = artifacts / "contexts" / "ghost.md"
        bad_link.parent.mkdir(parents=True)
        bad_link.symlink_to(warehouse / "contexts" / "ghost.md")

        (tmp_path / "CLAUDE.md").write_text("@nonexistent.md\n")

        manifest = _make_manifest(contexts=["contexts/*.md"])
        issues = run_project_health_checks(tmp_path, warehouse, manifest)

        messages = [i.message for i in issues]
        assert any("Dangling symlink" in m for m in messages)
        assert any("Broken reference" in m for m in messages)
        assert any("Stale glob" in m for m in messages)
        assert any("not a git working tree" in m for m in messages)

    def test_no_warehouse_skips_warehouse_checks(self, tmp_path):
        manifest = _make_manifest()
        issues = run_project_health_checks(tmp_path, None, manifest)
        messages = {i.message for i in issues}
        assert "Dangling symlink" not in messages
        assert "Stale glob" not in messages

    def test_no_manifest_skips_manifest_checks(self, tmp_path):
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()
        (warehouse / ".git").mkdir()
        issues = run_project_health_checks(tmp_path, warehouse, None)
        messages = {i.message for i in issues}
        assert "Stale glob" not in messages


# ---------------------------------------------------------------------------
# run_project_diagnostics
# ---------------------------------------------------------------------------


class TestRunProjectDiagnostics:
    def test_fix_true_repairs_drift(self, tmp_path):
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()
        (warehouse / ".git").mkdir()
        (tmp_path / ".agentic-beacon" / "beacon.yaml").parent.mkdir(parents=True)
        (tmp_path / ".agentic-beacon" / "beacon.yaml").write_text(
            "artifacts:\n  contexts: []\n  skills: []\n  agents: []\n"
        )
        beacon_dir = tmp_path / ".agentic-beacon"
        beacon_yaml = beacon_dir / "beacon.yaml"
        from beacon.core.manifest.beacon import BeaconManifest

        manifest = BeaconManifest.from_yaml(beacon_yaml)
        issues, fixes = run_project_diagnostics(tmp_path, warehouse, manifest, fix=True)
        assert len(fixes) > 0, "Expected non-empty fixes on drifted project"
        managed_issues = [
            i
            for i in issues
            if "gitignore" in i.message.lower()
            and ("Tier A" in i.message or "Tier B" in i.message)
        ]
        assert len(managed_issues) == 0, (
            f"After repair, managed-block drift must not appear: {[i.message for i in managed_issues]}"
        )

    def test_fix_false_returns_no_fixes(self, tmp_path):
        issues, fixes = run_project_diagnostics(tmp_path, None, None, fix=False)
        assert fixes == []
        assert isinstance(issues, list)
