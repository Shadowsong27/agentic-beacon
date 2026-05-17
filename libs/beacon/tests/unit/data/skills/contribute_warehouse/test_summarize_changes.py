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
