"""Unit tests for GitignoreManager.remove_entries."""

from beacon.core.gitignore import GitignoreManager


class TestRemoveEntries:
    def test_remove_entries_no_file_returns_false(self, tmp_path):
        """gitignore missing → returns False, no file created."""
        mgr = GitignoreManager(tmp_path)
        result = mgr.remove_entries([".claude/agents/"])
        assert result is False
        assert not (tmp_path / ".gitignore").exists()

    def test_remove_entries_removes_only_matching_lines(self, tmp_path):
        """Preserves comments and unmatched entries; removes only exact matches."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(
            "# Agentic Beacon\n"
            "__pycache__/\n"
            ".claude/agents/\n"
            ".opencode/agents/\n"
            "*.pyc\n"
        )
        mgr = GitignoreManager(tmp_path)
        result = mgr.remove_entries([".claude/agents/", ".opencode/agents/"])
        assert result is True
        lines = gitignore.read_text().splitlines()
        assert ".claude/agents/" not in lines
        assert ".opencode/agents/" not in lines
        assert "# Agentic Beacon" in lines
        assert "__pycache__/" in lines
        assert "*.pyc" in lines

    def test_remove_entries_idempotent(self, tmp_path):
        """Running remove_entries twice produces the same result as once."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("__pycache__/\n.claude/agents/\n.opencode/agents/\n")
        mgr = GitignoreManager(tmp_path)
        mgr.remove_entries([".claude/agents/", ".opencode/agents/"])
        content_first = gitignore.read_text()

        result_second = mgr.remove_entries([".claude/agents/", ".opencode/agents/"])
        assert result_second is False  # nothing to remove the second time
        assert gitignore.read_text() == content_first

    def test_remove_entries_preserves_trailing_newline_when_present(self, tmp_path):
        """File with trailing newline keeps it after removal."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("__pycache__/\n.claude/agents/\n")
        mgr = GitignoreManager(tmp_path)
        mgr.remove_entries([".claude/agents/"])
        content = gitignore.read_text()
        assert content.endswith("\n")
        assert "__pycache__/" in content

    def test_remove_entries_no_trailing_newline_preserved(self, tmp_path):
        """File without trailing newline does not gain one after removal."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("__pycache__/\n.claude/agents/")
        mgr = GitignoreManager(tmp_path)
        mgr.remove_entries([".claude/agents/"])
        content = gitignore.read_text()
        assert not content.endswith("\n")
        assert "__pycache__/" in content

    def test_remove_entries_no_match_returns_false(self, tmp_path):
        """When no lines match, returns False and file is unchanged."""
        gitignore = tmp_path / ".gitignore"
        original = "*.pyc\n__pycache__/\n"
        gitignore.write_text(original)
        mgr = GitignoreManager(tmp_path)
        result = mgr.remove_entries([".claude/agents/"])
        assert result is False
        assert gitignore.read_text() == original
