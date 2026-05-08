"""Unit tests for ensure_agent_dirs_gitignored and prune_agent_dirs_gitignore_entries.

Covers TC1-TC5 from task 2.2.
"""

import pytest
from beacon.domains.artifact.agent import (
    ensure_agent_dirs_gitignored,
    prune_agent_dirs_gitignore_entries,
)

EXPECTED_ENTRIES = [".claude/agents/", ".opencode/agents/"]


class TestEnsureAgentDirsGitignored:
    def test_tc1_no_gitignore_creates_with_both_entries(self, tmp_path):
        """TC1: no .gitignore exists → file is created with both entries."""
        project = tmp_path / "proj"
        project.mkdir()

        ensure_agent_dirs_gitignored(project)

        gitignore = project / ".gitignore"
        assert gitignore.exists()
        content_lines = gitignore.read_text().splitlines()
        for entry in EXPECTED_ENTRIES:
            assert entry in content_lines

    def test_tc2_existing_gitignore_preserves_content(self, tmp_path):
        """TC2: .gitignore exists with unrelated entries → both entries appended, originals preserved."""
        project = tmp_path / "proj"
        project.mkdir()
        gitignore = project / ".gitignore"
        original = "__pycache__/\n*.pyc\n"
        gitignore.write_text(original)

        ensure_agent_dirs_gitignored(project)

        content = gitignore.read_text()
        assert "__pycache__/" in content
        assert "*.pyc" in content
        for entry in EXPECTED_ENTRIES:
            assert entry in content.splitlines()

    def test_tc3_partial_entries_only_adds_missing(self, tmp_path):
        """TC3: .gitignore already has .claude/agents/ but not .opencode/agents/ → only missing entry appended."""
        project = tmp_path / "proj"
        project.mkdir()
        gitignore = project / ".gitignore"
        gitignore.write_text(".claude/agents/\n")

        ensure_agent_dirs_gitignored(project)

        content_lines = gitignore.read_text().splitlines()
        assert content_lines.count(".claude/agents/") == 1
        assert ".opencode/agents/" in content_lines

    def test_tc4_both_entries_present_no_op(self, tmp_path):
        """TC4: .gitignore already has both → no-op, file unchanged."""
        project = tmp_path / "proj"
        project.mkdir()
        gitignore = project / ".gitignore"
        original = ".claude/agents/\n.opencode/agents/\n"
        gitignore.write_text(original)

        ensure_agent_dirs_gitignored(project)

        # File should be byte-identical
        assert gitignore.read_text() == original
        # mtime may or may not change depending on OS; check content is canonical
        content_lines = gitignore.read_text().splitlines()
        assert content_lines.count(".claude/agents/") == 1
        assert content_lines.count(".opencode/agents/") == 1

    def test_tc5_nonexistent_project_root_raises(self, tmp_path):
        """TC5: project_root is not a directory → raises FileNotFoundError, no partial write."""
        non_dir = tmp_path / "not-a-dir.txt"
        non_dir.write_text("I am a file")

        with pytest.raises(FileNotFoundError):
            ensure_agent_dirs_gitignored(non_dir)

    def test_idempotent_multiple_calls(self, tmp_path):
        """Calling ensure_agent_dirs_gitignored multiple times produces no duplicates."""
        project = tmp_path / "proj"
        project.mkdir()

        ensure_agent_dirs_gitignored(project)
        ensure_agent_dirs_gitignored(project)
        ensure_agent_dirs_gitignored(project)

        content_lines = (project / ".gitignore").read_text().splitlines()
        assert content_lines.count(".claude/agents/") == 1
        assert content_lines.count(".opencode/agents/") == 1


class TestPruneAgentDirsGitignoreEntries:
    def test_tc1_missing_gitignore_no_op(self, tmp_path):
        """TC1: .gitignore missing → no-op, no file created."""
        project = tmp_path / "proj"
        project.mkdir()

        prune_agent_dirs_gitignore_entries(project)

        assert not (project / ".gitignore").exists()

    def test_tc2_both_entries_present_removes_them(self, tmp_path):
        """TC2: gitignore exists with both entries → both removed, other lines preserved."""
        project = tmp_path / "proj"
        project.mkdir()
        gitignore = project / ".gitignore"
        gitignore.write_text(
            "__pycache__/\n.claude/agents/\n.opencode/agents/\n*.pyc\n"
        )

        prune_agent_dirs_gitignore_entries(project)

        content_lines = gitignore.read_text().splitlines()
        assert ".claude/agents/" not in content_lines
        assert ".opencode/agents/" not in content_lines
        assert "__pycache__/" in content_lines
        assert "*.pyc" in content_lines

    def test_tc3_entries_absent_no_op(self, tmp_path):
        """TC3: gitignore exists without the entries → no-op (no modification)."""
        project = tmp_path / "proj"
        project.mkdir()
        gitignore = project / ".gitignore"
        original = "*.pyc\n__pycache__/\n"
        gitignore.write_text(original)

        prune_agent_dirs_gitignore_entries(project)

        assert gitignore.read_text() == original

    def test_tc4_only_one_entry_present(self, tmp_path):
        """TC4: only one of the two entries present → only that one is removed."""
        project = tmp_path / "proj"
        project.mkdir()
        gitignore = project / ".gitignore"
        gitignore.write_text("*.pyc\n.claude/agents/\n")

        prune_agent_dirs_gitignore_entries(project)

        content_lines = gitignore.read_text().splitlines()
        assert ".claude/agents/" not in content_lines
        assert ".opencode/agents/" not in content_lines
        assert "*.pyc" in content_lines

    def test_tc5_nonexistent_project_root_raises(self, tmp_path):
        """TC5: project_root is not a directory → raises FileNotFoundError."""
        non_dir = tmp_path / "not-a-dir.txt"
        non_dir.write_text("I am a file")

        with pytest.raises(FileNotFoundError):
            prune_agent_dirs_gitignore_entries(non_dir)

    def test_tc6_idempotent(self, tmp_path):
        """TC6: pruning twice produces the same result as pruning once."""
        project = tmp_path / "proj"
        project.mkdir()
        gitignore = project / ".gitignore"
        gitignore.write_text("__pycache__/\n.claude/agents/\n.opencode/agents/\n")

        prune_agent_dirs_gitignore_entries(project)
        content_after_first = gitignore.read_text()

        prune_agent_dirs_gitignore_entries(project)
        content_after_second = gitignore.read_text()

        assert content_after_first == content_after_second
        assert ".claude/agents/" not in content_after_second
        assert ".opencode/agents/" not in content_after_second
