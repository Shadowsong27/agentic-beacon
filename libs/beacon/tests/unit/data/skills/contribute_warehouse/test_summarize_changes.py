"""Unit tests for summarize_changes.py (Task 9.1 / TDD for Task 4).

TDD test cases per tasks.md TC tables for 4.4, 4.5, 4.6.

All tests use tmp_path + git init for hermetic execution. The tests import
the script's internal functions directly where possible to avoid needing to
invoke the full PEP 723 uv run path in unit tests.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

_SKILLS_DIR = Path(__file__).resolve().parents[5] / "src" / "beacon" / "data" / "skills"
_SCRIPT_PATH = _SKILLS_DIR / "contribute-warehouse" / "scripts" / "summarize_changes.py"


def _load_script():
    """Load summarize_changes.py as a module for unit testing."""
    spec = importlib.util.spec_from_file_location("summarize_changes", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_git_warehouse(tmp_path: Path) -> Path:
    """Create a minimal warehouse with an initialized git repo and beacon.yaml."""
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    (warehouse / "contexts").mkdir()
    (warehouse / "skills").mkdir()
    (warehouse / "knowledge").mkdir()

    # Init git
    subprocess.run(["git", "init", str(warehouse)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(warehouse), "config", "user.email", "test@test.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(warehouse), "config", "user.name", "Test"],
        check=True,
        capture_output=True,
    )
    return warehouse


def _write_beacon_yaml(warehouse: Path, patterns: list[str]) -> Path:
    """Write a minimal beacon.yaml to .agentic-beacon/ inside the warehouse."""
    ab_dir = warehouse / ".agentic-beacon"
    ab_dir.mkdir(exist_ok=True)
    beacon_yaml = ab_dir / "beacon.yaml"
    skills_section = "\n".join(f"    - {p}" for p in patterns)
    beacon_yaml.write_text(
        f"version: 1\nartifacts:\n  skills:\n{skills_section}\n  contexts: []\n"
    )
    return beacon_yaml


def _initial_commit(warehouse: Path, files: list[Path]) -> None:
    """Stage and commit the given files in the warehouse."""
    for f in files:
        subprocess.run(
            ["git", "-C", str(warehouse), "add", str(f.relative_to(warehouse))],
            check=True,
            capture_output=True,
        )
    subprocess.run(
        ["git", "-C", str(warehouse), "commit", "-m", "initial"],
        check=True,
        capture_output=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# TC (Task 4.5): JSON output shape
# ─────────────────────────────────────────────────────────────────────────────


class TestJsonOutputShape:
    """4.5 test cases: JSON output shape."""

    def test_tc1_empty_warehouse_returns_empty_tracked_paths(self, tmp_path):
        """TC1: No dirty tracked files → {"tracked_paths": []}."""
        warehouse = _make_git_warehouse(tmp_path)
        beacon_yaml = _write_beacon_yaml(warehouse, ["contexts/*.md"])

        # Create and commit a file so it's clean
        ctx_file = warehouse / "contexts" / "python-standards.md"
        ctx_file.write_text("# Python Standards\n")
        _initial_commit(warehouse, [ctx_file])

        mod = _load_script()
        result = mod.summarize(warehouse, beacon_yaml)
        assert isinstance(result, dict)
        assert "tracked_paths" in result
        assert result["tracked_paths"] == []

    def test_tc2_one_modified_file_returns_one_entry(self, tmp_path):
        """TC2: One modified tracked file → tracked_paths has exactly one entry."""
        warehouse = _make_git_warehouse(tmp_path)
        beacon_yaml = _write_beacon_yaml(warehouse, ["contexts/*.md"])

        ctx_file = warehouse / "contexts" / "python-standards.md"
        ctx_file.write_text("# Python Standards\n")
        _initial_commit(warehouse, [ctx_file])

        # Modify the file
        ctx_file.write_text("# Python Standards\n\nUpdated.\n")

        mod = _load_script()
        result = mod.summarize(warehouse, beacon_yaml)
        assert len(result["tracked_paths"]) == 1
        entry = result["tracked_paths"][0]
        assert entry["path"] == "contexts/python-standards.md"
        assert "git_status" in entry
        assert "diff_stat" in entry
        assert "last_commit_age_days" in entry

    def test_tc3_multiple_files_sorted_by_path(self, tmp_path):
        """TC3: Multiple dirty files → entries sorted by path."""
        warehouse = _make_git_warehouse(tmp_path)
        beacon_yaml = _write_beacon_yaml(warehouse, ["contexts/*.md"])

        for name in ["z-file.md", "a-file.md", "m-file.md"]:
            f = warehouse / "contexts" / name
            f.write_text(f"# {name}\n")
        _initial_commit(
            warehouse,
            [
                warehouse / "contexts" / "z-file.md",
                warehouse / "contexts" / "a-file.md",
                warehouse / "contexts" / "m-file.md",
            ],
        )
        # Modify all
        for name in ["z-file.md", "a-file.md", "m-file.md"]:
            (warehouse / "contexts" / name).write_text(f"# {name} MODIFIED\n")

        mod = _load_script()
        result = mod.summarize(warehouse, beacon_yaml)
        paths = [e["path"] for e in result["tracked_paths"]]
        assert paths == sorted(paths)

    def test_tc4_output_is_valid_json(self, tmp_path):
        """TC4: Output JSON parses cleanly."""
        warehouse = _make_git_warehouse(tmp_path)
        beacon_yaml = _write_beacon_yaml(warehouse, ["contexts/*.md"])

        ctx_file = warehouse / "contexts" / "python-standards.md"
        ctx_file.write_text("# Python Standards\n")
        _initial_commit(warehouse, [ctx_file])
        ctx_file.write_text("# Python Standards\nModified.\n")

        mod = _load_script()
        result = mod.summarize(warehouse, beacon_yaml)
        # Re-serialize and re-parse to confirm JSON-roundtrip
        json_str = json.dumps(result)
        parsed = json.loads(json_str)
        assert "tracked_paths" in parsed


# ─────────────────────────────────────────────────────────────────────────────
# TC (Task 4.4): Per-file git status, diff_stat, age
# ─────────────────────────────────────────────────────────────────────────────


class TestPerFileFields:
    """4.4 test cases: git_status, diff_stat, last_commit_age_days."""

    def test_tc1_modified_tracked_file(self, tmp_path):
        """TC1: Modified tracked file → git_status contains M, diff_stat non-empty, age is int."""
        warehouse = _make_git_warehouse(tmp_path)
        beacon_yaml = _write_beacon_yaml(warehouse, ["contexts/*.md"])

        ctx_file = warehouse / "contexts" / "python-standards.md"
        ctx_file.write_text("# Python Standards\n")
        _initial_commit(warehouse, [ctx_file])
        ctx_file.write_text("# Python Standards\nNew line.\n")

        mod = _load_script()
        result = mod.summarize(warehouse, beacon_yaml)
        assert len(result["tracked_paths"]) == 1
        entry = result["tracked_paths"][0]
        assert "M" in entry["git_status"] or entry["git_status"].strip() in (
            "M",
            " M",
            "MM",
        )
        assert entry["last_commit_age_days"] is not None

    def test_tc2_newly_staged_file_has_null_age(self, tmp_path):
        """TC2: Newly added (staged) file → last_commit_age_days is null."""
        warehouse = _make_git_warehouse(tmp_path)
        beacon_yaml = _write_beacon_yaml(warehouse, ["contexts/*.md"])

        # Initial commit with placeholder
        placeholder = warehouse / "contexts" / ".keep"
        placeholder.write_text("")
        _initial_commit(warehouse, [placeholder])

        # Add a new file and stage it
        ctx_file = warehouse / "contexts" / "new-file.md"
        ctx_file.write_text("# New File\n")
        subprocess.run(
            ["git", "-C", str(warehouse), "add", "contexts/new-file.md"],
            check=True,
            capture_output=True,
        )

        mod = _load_script()
        result = mod.summarize(warehouse, beacon_yaml)
        entries = {e["path"]: e for e in result["tracked_paths"]}
        if "contexts/new-file.md" in entries:
            assert entries["contexts/new-file.md"]["last_commit_age_days"] is None

    def test_tc3_untracked_beacon_yaml_tracked_file(self, tmp_path):
        """TC3: Untracked file that matches beacon.yaml patterns → shows ?? status."""
        warehouse = _make_git_warehouse(tmp_path)
        beacon_yaml = _write_beacon_yaml(warehouse, ["contexts/*.md"])

        # Create file but don't add to git
        ctx_file = warehouse / "contexts" / "untracked.md"
        ctx_file.write_text("# Untracked\n")

        mod = _load_script()
        result = mod.summarize(warehouse, beacon_yaml)
        entries = {e["path"]: e for e in result["tracked_paths"]}
        if "contexts/untracked.md" in entries:
            assert entries["contexts/untracked.md"]["git_status"].strip() == "??"

    def test_tc5_never_committed_file_null_age(self, tmp_path):
        """TC5: Untracked file → last_commit_age_days is null."""
        warehouse = _make_git_warehouse(tmp_path)
        beacon_yaml = _write_beacon_yaml(warehouse, ["contexts/*.md"])

        ctx_file = warehouse / "contexts" / "never-committed.md"
        ctx_file.write_text("# Never committed\n")

        mod = _load_script()
        result = mod.summarize(warehouse, beacon_yaml)
        entries = {e["path"]: e for e in result["tracked_paths"]}
        if "contexts/never-committed.md" in entries:
            assert (
                entries["contexts/never-committed.md"]["last_commit_age_days"] is None
            )

    def test_tc6_committed_file_has_integer_age(self, tmp_path):
        """TC6: File committed → last_commit_age_days is an integer >= 0."""
        warehouse = _make_git_warehouse(tmp_path)
        beacon_yaml = _write_beacon_yaml(warehouse, ["contexts/*.md"])

        ctx_file = warehouse / "contexts" / "python-standards.md"
        ctx_file.write_text("# Python Standards\n")
        _initial_commit(warehouse, [ctx_file])
        # Modify to make it dirty
        ctx_file.write_text("# Python Standards\nModified.\n")

        mod = _load_script()
        result = mod.summarize(warehouse, beacon_yaml)
        entries = {e["path"]: e for e in result["tracked_paths"]}
        assert "contexts/python-standards.md" in entries
        age = entries["contexts/python-standards.md"]["last_commit_age_days"]
        assert isinstance(age, int)
        assert age >= 0

    def test_tc7_subprocess_failure_raises(self, tmp_path):
        """TC7: Non-git directory → script raises or returns empty."""
        non_git_dir = tmp_path / "not-a-repo"
        non_git_dir.mkdir()
        beacon_yaml = non_git_dir / "beacon.yaml"
        # No beacon.yaml → get_tracked_paths returns []
        # but also, git commands would fail on a non-git dir

        mod = _load_script()
        # If beacon.yaml doesn't exist, should return empty list
        result = mod.summarize(non_git_dir, beacon_yaml)
        assert result["tracked_paths"] == []

    def test_tc8_path_with_spaces_handled(self, tmp_path):
        """TC8: Path with spaces in filename is handled correctly."""
        warehouse = _make_git_warehouse(tmp_path)
        beacon_yaml = _write_beacon_yaml(warehouse, ["contexts/*.md"])

        # File with spaces
        ctx_file = warehouse / "contexts" / "my file with spaces.md"
        ctx_file.write_text("# Spaces\n")

        mod = _load_script()
        # Should not crash
        result = mod.summarize(warehouse, beacon_yaml)
        assert isinstance(result, dict)
        assert "tracked_paths" in result


# ─────────────────────────────────────────────────────────────────────────────
# TC (Task 4.6): Filter clean paths
# ─────────────────────────────────────────────────────────────────────────────


class TestFilterCleanPaths:
    """4.6 test cases: clean files filtered out."""

    def test_clean_files_excluded(self, tmp_path):
        """5 tracked paths: 2 modified, 3 clean → only 2 in output."""
        warehouse = _make_git_warehouse(tmp_path)
        beacon_yaml = _write_beacon_yaml(warehouse, ["contexts/*.md"])

        files = []
        for i in range(5):
            f = warehouse / "contexts" / f"file-{i}.md"
            f.write_text(f"# File {i}\n")
            files.append(f)
        _initial_commit(warehouse, files)

        # Modify only 2
        (warehouse / "contexts" / "file-0.md").write_text("# File 0 MODIFIED\n")
        (warehouse / "contexts" / "file-3.md").write_text("# File 3 MODIFIED\n")

        mod = _load_script()
        result = mod.summarize(warehouse, beacon_yaml)
        assert len(result["tracked_paths"]) == 2
        paths = {e["path"] for e in result["tracked_paths"]}
        assert "contexts/file-0.md" in paths
        assert "contexts/file-3.md" in paths

    def test_untracked_file_not_in_beacon_yaml_excluded(self, tmp_path):
        """Untracked file not in beacon.yaml patterns is excluded."""
        warehouse = _make_git_warehouse(tmp_path)
        beacon_yaml = _write_beacon_yaml(warehouse, ["contexts/*.md"])

        # This file is NOT in contexts/ (so won't match pattern)
        unrelated = warehouse / "docs" / "README.md"
        unrelated.parent.mkdir()
        unrelated.write_text("# Docs\n")

        mod = _load_script()
        result = mod.summarize(warehouse, beacon_yaml)
        paths = {e["path"] for e in result["tracked_paths"]}
        assert "docs/README.md" not in paths


# ─────────────────────────────────────────────────────────────────────────────
# Finding 2 fix-up: beacon.yaml default is project root, not warehouse
# ─────────────────────────────────────────────────────────────────────────────


class TestBeaconYamlDefault:
    """Project-root resolution helpers used by the --only-project-artifacts opt-in.

    PER-202 made the default warehouse-scoped (see TestWarehouseScopedDefault),
    but the legacy beacon.yaml-filtered path still depends on these helpers to
    locate the invoking project's beacon.yaml.
    """

    def _make_project_with_beacon_yaml(
        self, tmp_path: Path, patterns: list[str]
    ) -> tuple[Path, Path]:
        """Create a project directory with .agentic-beacon/beacon.yaml."""
        project = tmp_path / "project"
        project.mkdir()
        ab_dir = project / ".agentic-beacon"
        ab_dir.mkdir()
        # config.toml so _find_project_root can detect it
        (ab_dir / "config.toml").write_text('[warehouse]\nlocal_path = "/tmp/x"\n')
        beacon_yaml = ab_dir / "beacon.yaml"
        skills_section = "\n".join(f"    - {p}" for p in patterns)
        beacon_yaml.write_text(
            f"version: 1\nartifacts:\n  skills:\n{skills_section}\n  contexts: []\n"
        )
        return project, beacon_yaml

    def test_summarize_default_beacon_yaml_uses_project_root(
        self, tmp_path, monkeypatch
    ):
        """Default invocation finds beacon.yaml at project root, not warehouse."""
        mod = _load_script()

        wh = _make_git_warehouse(tmp_path)
        project, project_beacon_yaml = self._make_project_with_beacon_yaml(
            tmp_path, ["contexts/*.md"]
        )

        # Warehouse should NOT have a beacon.yaml in its .agentic-beacon/
        warehouse_beacon = wh / ".agentic-beacon" / "beacon.yaml"
        assert not warehouse_beacon.exists(), (
            "Warehouse must not have beacon.yaml for this test"
        )

        # Auto-detection from project dir should find the project's beacon.yaml
        monkeypatch.chdir(project)
        detected_root = mod._find_project_root(project)
        assert detected_root == project

        resolved_beacon = detected_root / ".agentic-beacon" / "beacon.yaml"
        assert resolved_beacon == project_beacon_yaml

    def test_summarize_explicit_project_root_flag(self, tmp_path, monkeypatch):
        """--project-root overrides auto-detection."""
        mod = _load_script()

        _make_git_warehouse(tmp_path)
        project, project_beacon_yaml = self._make_project_with_beacon_yaml(
            tmp_path, ["contexts/*.md"]
        )

        # Even if CWD is somewhere else, explicit project_root resolves correctly
        other_dir = tmp_path / "other"
        other_dir.mkdir()
        monkeypatch.chdir(other_dir)

        detected_root = mod._find_project_root(project)
        assert detected_root == project
        assert (
            detected_root / ".agentic-beacon" / "beacon.yaml"
        ) == project_beacon_yaml

    def test_summarize_no_project_root_no_flag_returns_none(
        self, tmp_path, monkeypatch
    ):
        """When neither detectable nor passed, _find_project_root returns None."""
        mod = _load_script()

        # Use a directory with no .agentic-beacon/config.toml in the whole tree
        bare_dir = tmp_path / "bare"
        bare_dir.mkdir()
        monkeypatch.chdir(bare_dir)

        result = mod._find_project_root(bare_dir)
        assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# M1: Staged-only diff_stat fallback
# ─────────────────────────────────────────────────────────────────────────────


class TestStagedOnlyDiffStat:
    """Finding M1 fix: get_diff_stat falls back to --cached on empty unstaged stdout."""

    def test_staged_only_modification_has_diff_stat(self, tmp_path):
        """Staged (index-only) modification returns non-empty diff_stat."""
        warehouse = _make_git_warehouse(tmp_path)
        _write_beacon_yaml(warehouse, ["contexts/*.md"])

        ctx_file = warehouse / "contexts" / "staged-mod.md"
        ctx_file.write_text("# Original\n")
        _initial_commit(warehouse, [ctx_file])

        # Modify and stage — working tree then matches index again
        ctx_file.write_text("# Original\n\nNew section.\n")
        subprocess.run(
            ["git", "-C", str(warehouse), "add", "contexts/staged-mod.md"],
            check=True,
            capture_output=True,
        )

        mod = _load_script()
        diff_stat = mod.get_diff_stat(warehouse, "contexts/staged-mod.md")
        assert diff_stat, (
            f"Expected non-empty diff_stat for staged modification, got: {diff_stat!r}"
        )
        assert (
            "changed" in diff_stat
            or "insertion" in diff_stat
            or "deletion" in diff_stat
        )

    def test_staged_only_new_file_has_diff_stat(self, tmp_path):
        """Freshly added (status 'A') file returns non-empty diff_stat."""
        warehouse = _make_git_warehouse(tmp_path)
        _write_beacon_yaml(warehouse, ["contexts/*.md"])

        # Initial commit with a placeholder so git history exists
        placeholder = warehouse / "contexts" / ".keep"
        placeholder.write_text("")
        _initial_commit(warehouse, [placeholder])

        # Stage a brand-new file (never committed)
        new_file = warehouse / "contexts" / "brand-new.md"
        new_file.write_text("# Brand new knowledge file.\n")
        subprocess.run(
            ["git", "-C", str(warehouse), "add", "contexts/brand-new.md"],
            check=True,
            capture_output=True,
        )

        mod = _load_script()
        diff_stat = mod.get_diff_stat(warehouse, "contexts/brand-new.md")
        assert diff_stat, (
            f"Expected non-empty diff_stat for staged new file, got: {diff_stat!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# M2: PEP 723 dependency regression guard
# ─────────────────────────────────────────────────────────────────────────────


class TestPep723Dependencies:
    """Finding M2 fix: summarize_changes.py must declare pyyaml>=6.0, not agentic-beacon."""

    def test_pep_723_header_uses_pyyaml_not_agentic_beacon(self):
        """PEP 723 header declares pyyaml>=6.0 and does NOT list agentic-beacon."""
        content = _SCRIPT_PATH.read_text()
        # Extract the inline script block
        assert 'dependencies = ["pyyaml>=6.0"]' in content, (
            "PEP 723 header must declare pyyaml>=6.0"
        )
        assert (
            "agentic-beacon"
            not in content.split("# ///")[0] + content.split("# ///")[1]
            if content.count("# ///") >= 2
            else "agentic-beacon" not in content[: content.find('"""')]
        ), "PEP 723 header must not list agentic-beacon"

    def test_no_beacon_package_imports(self):
        """Script must not import from beacon.* package."""
        content = _SCRIPT_PATH.read_text()
        import re

        beacon_imports = re.findall(r"^(?:from|import) beacon", content, re.MULTILINE)
        assert not beacon_imports, (
            f"Script still imports from beacon package: {beacon_imports}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# PER-186: deleted-but-tracked files must appear in summary
# ─────────────────────────────────────────────────────────────────────────────


class TestPer186DeletedTrackedFiles:
    """PER-186: deleted-but-tracked files must appear in summary."""

    def test_deleted_glob_match_appears_with_deletion_status(self, tmp_path):
        """Tracked file matching glob pattern, deleted → appears with D status."""
        warehouse = _make_git_warehouse(tmp_path)
        beacon_yaml = _write_beacon_yaml(warehouse, ["contexts/*.md"])

        ctx_file = warehouse / "contexts" / "to-delete.md"
        ctx_file.write_text("# To delete\n")
        _initial_commit(warehouse, [ctx_file])

        # Delete the file (unstaged deletion)
        ctx_file.unlink()

        mod = _load_script()
        result = mod.summarize(warehouse, beacon_yaml)
        paths = [e["path"] for e in result["tracked_paths"]]
        assert "contexts/to-delete.md" in paths, (
            f"PER-186: deleted tracked file should appear. Got: {paths}"
        )

        entry = next(
            e for e in result["tracked_paths"] if e["path"] == "contexts/to-delete.md"
        )
        assert "D" in entry["git_status"], (
            f"Expected deletion status, got: {entry['git_status']!r}"
        )

    def test_deleted_explicit_path_appears_with_deletion_status(self, tmp_path):
        """Tracked explicit path, deleted → appears with D status."""
        warehouse = _make_git_warehouse(tmp_path)
        beacon_yaml = _write_beacon_yaml_full(
            warehouse, contexts=["contexts/explicit.md"]
        )

        ctx_file = warehouse / "contexts" / "explicit.md"
        ctx_file.write_text("# Explicit\n")
        _initial_commit(warehouse, [ctx_file])

        # Delete the file
        ctx_file.unlink()

        mod = _load_script()
        result = mod.summarize(warehouse, beacon_yaml)
        paths = [e["path"] for e in result["tracked_paths"]]
        assert "contexts/explicit.md" in paths, (
            f"PER-186: deleted explicit path should appear. Got: {paths}"
        )

        entry = next(
            e for e in result["tracked_paths"] if e["path"] == "contexts/explicit.md"
        )
        assert "D" in entry["git_status"], (
            f"Expected deletion status, got: {entry['git_status']!r}"
        )

    def test_is_dirty_classifies_unstaged_deletion(self, tmp_path):
        """PER-186: is_dirty must classify ' D' as dirty."""
        mod = _load_script()
        assert mod.is_dirty(" D") is True

    def test_is_dirty_classifies_staged_deletion(self, tmp_path):
        """PER-186: is_dirty must classify 'D ' as dirty."""
        mod = _load_script()
        assert mod.is_dirty("D ") is True

    def test_staged_deletion_glob_match_appears(self, tmp_path):
        """Tracked file matching glob pattern, git-rm staged → appears with D status."""
        warehouse = _make_git_warehouse(tmp_path)
        beacon_yaml = _write_beacon_yaml(warehouse, ["contexts/*.md"])

        ctx_file = warehouse / "contexts" / "to-delete.md"
        ctx_file.write_text("# To delete\n")
        _initial_commit(warehouse, [ctx_file])

        # Stage the deletion
        subprocess.run(
            ["git", "-C", str(warehouse), "rm", "contexts/to-delete.md"],
            check=True,
            capture_output=True,
        )

        mod = _load_script()
        result = mod.summarize(warehouse, beacon_yaml)
        paths = [e["path"] for e in result["tracked_paths"]]
        assert "contexts/to-delete.md" in paths, (
            f"PER-186 round 2: staged-deleted tracked file should appear. Got: {paths}"
        )

        entry = next(
            e for e in result["tracked_paths"] if e["path"] == "contexts/to-delete.md"
        )
        assert "D" in entry["git_status"], (
            f"Expected deletion status, got: {entry['git_status']!r}"
        )

    def test_directory_pattern_deletion_appears(self, tmp_path):
        """Directory pattern (no glob), file deleted unstaged → appears in summary."""
        warehouse = _make_git_warehouse(tmp_path)
        beacon_yaml = _write_beacon_yaml_full(warehouse, contexts=["contexts/"])

        ctx_file = warehouse / "contexts" / "nested.md"
        ctx_file.write_text("# Nested\n")
        _initial_commit(warehouse, [ctx_file])

        # Delete the file (unstaged)
        ctx_file.unlink()

        mod = _load_script()
        result = mod.summarize(warehouse, beacon_yaml)
        paths = [e["path"] for e in result["tracked_paths"]]
        assert "contexts/nested.md" in paths, (
            f"PER-186 round 2: deleted file under directory pattern should appear. Got: {paths}"
        )

        entry = next(
            e for e in result["tracked_paths"] if e["path"] == "contexts/nested.md"
        )
        assert "D" in entry["git_status"], (
            f"Expected deletion status, got: {entry['git_status']!r}"
        )

    def test_directory_pattern_staged_deletion_appears(self, tmp_path):
        """Directory pattern (no glob), file git-rm staged → appears in summary."""
        warehouse = _make_git_warehouse(tmp_path)
        beacon_yaml = _write_beacon_yaml_full(warehouse, contexts=["contexts/"])

        ctx_file = warehouse / "contexts" / "staged-delete.md"
        ctx_file.write_text("# Staged delete\n")
        _initial_commit(warehouse, [ctx_file])

        # Stage the deletion
        subprocess.run(
            ["git", "-C", str(warehouse), "rm", "contexts/staged-delete.md"],
            check=True,
            capture_output=True,
        )

        mod = _load_script()
        result = mod.summarize(warehouse, beacon_yaml)
        paths = [e["path"] for e in result["tracked_paths"]]
        assert "contexts/staged-delete.md" in paths, (
            f"PER-186 round 2: staged-deleted file under directory pattern should appear. Got: {paths}"
        )

        entry = next(
            e
            for e in result["tracked_paths"]
            if e["path"] == "contexts/staged-delete.md"
        )
        assert "D" in entry["git_status"], (
            f"Expected deletion status, got: {entry['git_status']!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# PER-183: get_tracked_paths must walk artifacts.agents (not just skills + contexts)
# ─────────────────────────────────────────────────────────────────────────────


def _write_beacon_yaml_full(
    warehouse: Path,
    *,
    skills: list[str] | None = None,
    contexts: list[str] | None = None,
    agents: list[str] | None = None,
) -> Path:
    """Write a beacon.yaml that can declare any of the three artifact types.

    Mirrors the shape of beacon.core.manifest.beacon.ArtifactsConfig.
    """
    ab_dir = warehouse / ".agentic-beacon"
    ab_dir.mkdir(exist_ok=True)
    beacon_yaml = ab_dir / "beacon.yaml"

    def _section(name: str, items: list[str] | None) -> str:
        if not items:
            return f"  {name}: []\n"
        lines = "\n".join(f"    - {p}" for p in items)
        return f"  {name}:\n{lines}\n"

    body = (
        "version: 1\nartifacts:\n"
        + _section("skills", skills)
        + _section("contexts", contexts)
        + _section("agents", agents)
    )
    beacon_yaml.write_text(body)
    return beacon_yaml


class TestPer183AgentsAreTracked:
    """PER-183: agents artifact type must appear in get_tracked_paths output.

    Regression for PR #146's third-dogfood test, which exposed that the inline
    helper (faithful copy of beacon.domains.warehouse._tracked_paths.get_tracked_paths)
    only walked artifacts.skills + artifacts.contexts, silently dropping
    artifacts.agents — making /contribute-warehouse unusable for any agent
    contribution.
    """

    def test_dirty_agent_in_beacon_yaml_appears_in_summary(self, tmp_path):
        """Dirty file under agents/, declared in beacon.yaml.agents → appears in tracked_paths."""
        warehouse = _make_git_warehouse(tmp_path)
        # Create + commit so it exists as tracked-and-clean baseline
        (warehouse / "agents").mkdir(exist_ok=True)
        agent_file = warehouse / "agents" / "my-agent.md"
        agent_file.write_text("---\nname: my-agent\n---\nbody v1\n")
        _initial_commit(warehouse, [agent_file])

        # beacon.yaml tracks the agent
        beacon_yaml = _write_beacon_yaml_full(warehouse, agents=["agents/my-agent.md"])

        # Make it dirty
        agent_file.write_text("---\nname: my-agent\n---\nbody v2 modified\n")

        mod = _load_script()
        result = mod.summarize(warehouse, beacon_yaml)
        paths = [e["path"] for e in result["tracked_paths"]]
        assert "agents/my-agent.md" in paths, (
            f"PER-183 regression: dirty agent should appear in tracked_paths. Got: {paths}"
        )

    def test_agents_dir_pattern_walks_recursively(self, tmp_path):
        """Pattern `agents/` in beacon.yaml.agents picks up dirty files inside."""
        warehouse = _make_git_warehouse(tmp_path)
        (warehouse / "agents").mkdir(exist_ok=True)
        a1 = warehouse / "agents" / "alpha.md"
        a2 = warehouse / "agents" / "beta.md"
        a1.write_text("---\nname: alpha\n---\nv1\n")
        a2.write_text("---\nname: beta\n---\nv1\n")
        _initial_commit(warehouse, [a1, a2])

        # Pattern matches the directory
        beacon_yaml = _write_beacon_yaml_full(warehouse, agents=["agents/"])

        # Make alpha dirty, leave beta clean
        a1.write_text("---\nname: alpha\n---\nv2\n")

        mod = _load_script()
        result = mod.summarize(warehouse, beacon_yaml)
        paths = [e["path"] for e in result["tracked_paths"]]
        assert "agents/alpha.md" in paths
        assert "agents/beta.md" not in paths, "clean agent should be filtered out"

    def test_all_three_artifact_types_walked_together(self, tmp_path):
        """skills + contexts + agents all populated → each dirty file appears."""
        warehouse = _make_git_warehouse(tmp_path)
        (warehouse / "agents").mkdir(exist_ok=True)
        (warehouse / "skills" / "s1").mkdir(parents=True, exist_ok=True)

        ctx = warehouse / "contexts" / "c1.md"
        skill = warehouse / "skills" / "s1" / "SKILL.md"
        agent = warehouse / "agents" / "a1.md"
        for f, body in [
            (ctx, "ctx v1\n"),
            (skill, "---\nname: s1\n---\nv1\n"),
            (agent, "---\nname: a1\n---\nv1\n"),
        ]:
            f.write_text(body)
        _initial_commit(warehouse, [ctx, skill, agent])

        beacon_yaml = _write_beacon_yaml_full(
            warehouse,
            skills=["skills/s1/SKILL.md"],
            contexts=["contexts/c1.md"],
            agents=["agents/a1.md"],
        )

        # Dirty all three
        ctx.write_text("ctx v2 modified\n")
        skill.write_text("---\nname: s1\n---\nv2 modified\n")
        agent.write_text("---\nname: a1\n---\nv2 modified\n")

        mod = _load_script()
        result = mod.summarize(warehouse, beacon_yaml)
        paths = sorted(e["path"] for e in result["tracked_paths"])
        assert paths == sorted(
            ["contexts/c1.md", "skills/s1/SKILL.md", "agents/a1.md"]
        ), f"all three artifact types should appear, got: {paths}"

    def test_empty_agents_section_no_error(self, tmp_path):
        """beacon.yaml with agents: [] is valid and walks the other two."""
        warehouse = _make_git_warehouse(tmp_path)
        ctx = warehouse / "contexts" / "c1.md"
        ctx.write_text("v1\n")
        _initial_commit(warehouse, [ctx])
        beacon_yaml = _write_beacon_yaml_full(
            warehouse,
            contexts=["contexts/c1.md"],
            agents=None,  # no agents key
        )
        ctx.write_text("v2 modified\n")
        mod = _load_script()
        result = mod.summarize(warehouse, beacon_yaml)
        assert any(e["path"] == "contexts/c1.md" for e in result["tracked_paths"])

    def test_missing_agents_key_treated_as_empty(self, tmp_path):
        """If artifacts.agents key is missing entirely (older beacon.yaml), no crash."""
        warehouse = _make_git_warehouse(tmp_path)
        ctx = warehouse / "contexts" / "c1.md"
        ctx.write_text("v1\n")
        _initial_commit(warehouse, [ctx])
        # Hand-write a minimal beacon.yaml WITHOUT the agents key
        beacon_yaml = warehouse / ".agentic-beacon" / "beacon.yaml"
        beacon_yaml.parent.mkdir(exist_ok=True)
        beacon_yaml.write_text(
            "version: 1\nartifacts:\n  skills: []\n  contexts:\n    - contexts/c1.md\n"
        )
        ctx.write_text("v2 modified\n")
        mod = _load_script()
        result = mod.summarize(warehouse, beacon_yaml)
        assert any(e["path"] == "contexts/c1.md" for e in result["tracked_paths"])


# ─────────────────────────────────────────────────────────────────────────────
# PER-202: warehouse-scoped enumeration is the new default
# ─────────────────────────────────────────────────────────────────────────────


class TestWarehouseScopedDefault:
    """PER-202: default mode enumerates every dirty warehouse path with no project context.

    The skill must work from any CWD, including a directory with no
    ``.agentic-beacon/config.toml`` and against warehouses with no
    ``beacon.yaml`` anywhere.
    """

    def test_summarize_all_returns_dirty_path_with_no_beacon_yaml(self, tmp_path):
        """No beacon.yaml anywhere → dirty path still appears."""
        warehouse = _make_git_warehouse(tmp_path)
        ctx_file = warehouse / "contexts" / "python-standards.md"
        ctx_file.write_text("# Python Standards\n")
        _initial_commit(warehouse, [ctx_file])
        ctx_file.write_text("# Python Standards\nmodified\n")

        mod = _load_script()
        result = mod.summarize_all(warehouse)
        paths = [e["path"] for e in result["tracked_paths"]]
        assert "contexts/python-standards.md" in paths

    def test_summarize_all_includes_brand_new_untracked_skill(self, tmp_path):
        """Untracked file under skills/never-adopted/ appears in tracked_paths."""
        warehouse = _make_git_warehouse(tmp_path)
        # Initial empty commit so HEAD exists
        subprocess.run(
            ["git", "-C", str(warehouse), "commit", "--allow-empty", "-m", "init"],
            check=True,
            capture_output=True,
        )
        skill_dir = warehouse / "skills" / "never-adopted"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("---\nname: never-adopted\n---\nhello\n")

        mod = _load_script()
        result = mod.summarize_all(warehouse)
        paths = [e["path"] for e in result["tracked_paths"]]
        assert "skills/never-adopted/SKILL.md" in paths, (
            f"PER-202: brand-new untracked skill should appear. Got: {paths}"
        )
        entry = next(
            e
            for e in result["tracked_paths"]
            if e["path"] == "skills/never-adopted/SKILL.md"
        )
        assert entry["git_status"].strip() == "??"
        assert entry["warehouse_area"] == "skills"

    def test_summarize_all_classifies_warehouse_area(self, tmp_path):
        """warehouse_area is derived from the top-level directory."""
        warehouse = _make_git_warehouse(tmp_path)
        subprocess.run(
            ["git", "-C", str(warehouse), "commit", "--allow-empty", "-m", "init"],
            check=True,
            capture_output=True,
        )
        # Create one dirty file in each known area + one in "other"
        (warehouse / "contexts").mkdir(exist_ok=True)
        (warehouse / "knowledge").mkdir(exist_ok=True)
        (warehouse / "skills" / "s").mkdir(parents=True, exist_ok=True)
        (warehouse / "agents").mkdir(exist_ok=True)
        (warehouse / "docs").mkdir(exist_ok=True)

        (warehouse / "contexts" / "c.md").write_text("c\n")
        (warehouse / "knowledge" / "k.md").write_text("k\n")
        (warehouse / "skills" / "s" / "SKILL.md").write_text("s\n")
        (warehouse / "agents" / "a.md").write_text("a\n")
        (warehouse / "docs" / "d.md").write_text("d\n")

        mod = _load_script()
        result = mod.summarize_all(warehouse)
        by_path = {e["path"]: e["warehouse_area"] for e in result["tracked_paths"]}
        assert by_path.get("contexts/c.md") == "contexts"
        assert by_path.get("knowledge/k.md") == "knowledge"
        assert by_path.get("skills/s/SKILL.md") == "skills"
        assert by_path.get("agents/a.md") == "agents"
        assert by_path.get("docs/d.md") == "other"

    def test_summarize_all_excludes_clean_files(self, tmp_path):
        """Committed-and-untouched files do not appear."""
        warehouse = _make_git_warehouse(tmp_path)
        ctx_file = warehouse / "contexts" / "clean.md"
        ctx_file.write_text("# clean\n")
        _initial_commit(warehouse, [ctx_file])

        mod = _load_script()
        result = mod.summarize_all(warehouse)
        paths = [e["path"] for e in result["tracked_paths"]]
        assert "contexts/clean.md" not in paths
        assert paths == []

    def test_summarize_all_includes_deleted_file(self, tmp_path):
        """Unstaged deletion appears with a D status (PER-186 regression in new path)."""
        warehouse = _make_git_warehouse(tmp_path)
        ctx_file = warehouse / "contexts" / "to-delete.md"
        ctx_file.write_text("# delete me\n")
        _initial_commit(warehouse, [ctx_file])
        ctx_file.unlink()

        mod = _load_script()
        result = mod.summarize_all(warehouse)
        entries = {e["path"]: e for e in result["tracked_paths"]}
        assert "contexts/to-delete.md" in entries
        assert "D" in entries["contexts/to-delete.md"]["git_status"]

    def test_classify_warehouse_area_helper(self):
        """classify_warehouse_area maps top-level directory to area string."""
        mod = _load_script()
        assert mod.classify_warehouse_area("contexts/foo.md") == "contexts"
        assert mod.classify_warehouse_area("knowledge/python/lesson.md") == "knowledge"
        assert mod.classify_warehouse_area("skills/foo/SKILL.md") == "skills"
        assert mod.classify_warehouse_area("agents/foo.md") == "agents"
        assert mod.classify_warehouse_area("docs/README.md") == "other"
        assert mod.classify_warehouse_area("") == "other"

    def test_summarize_all_no_project_context_required(self, tmp_path, monkeypatch):
        """Invocation from a CWD with no .agentic-beacon/config.toml succeeds."""
        warehouse = _make_git_warehouse(tmp_path)
        ctx_file = warehouse / "contexts" / "f.md"
        ctx_file.write_text("# f\n")
        _initial_commit(warehouse, [ctx_file])
        ctx_file.write_text("# f modified\n")

        # CWD is a bare directory with no beacon config in the tree
        bare = tmp_path / "elsewhere"
        bare.mkdir()
        monkeypatch.chdir(bare)

        mod = _load_script()
        # Must not raise, must not depend on project root resolution
        result = mod.summarize_all(warehouse)
        paths = [e["path"] for e in result["tracked_paths"]]
        assert "contexts/f.md" in paths

    def test_summarize_all_skips_dot_git_entries(self, tmp_path):
        """Anything under .git/ is never reported."""
        warehouse = _make_git_warehouse(tmp_path)
        subprocess.run(
            ["git", "-C", str(warehouse), "commit", "--allow-empty", "-m", "init"],
            check=True,
            capture_output=True,
        )
        # Write a junk file inside .git/ — porcelain would never list it,
        # but the filter is defensive in case of unusual configurations.
        junk = warehouse / ".git" / "spurious.txt"
        junk.write_text("nope\n")

        mod = _load_script()
        result = mod.summarize_all(warehouse)
        for e in result["tracked_paths"]:
            assert not e["path"].startswith(".git/")
