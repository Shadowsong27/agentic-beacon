"""Unit tests for the repurposed update_agent_gitignores function.

Covers TC1-TC5 from task 2.2.
"""

import pytest
from beacon.domains.artifact.agent import update_agent_gitignores

EXPECTED_ENTRIES = [".claude/agents/", ".opencode/agents/"]


class TestUpdateAgentGitignores:
    def test_tc1_no_gitignore_creates_with_both_entries(self, tmp_path):
        """TC1: no .gitignore exists → file is created with both entries."""
        project = tmp_path / "proj"
        project.mkdir()

        update_agent_gitignores(project)

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

        update_agent_gitignores(project)

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

        update_agent_gitignores(project)

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

        update_agent_gitignores(project)

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
            update_agent_gitignores(non_dir)

    def test_idempotent_multiple_calls(self, tmp_path):
        """Calling update_agent_gitignores multiple times produces no duplicates."""
        project = tmp_path / "proj"
        project.mkdir()

        update_agent_gitignores(project)
        update_agent_gitignores(project)
        update_agent_gitignores(project)

        content_lines = (project / ".gitignore").read_text().splitlines()
        assert content_lines.count(".claude/agents/") == 1
        assert content_lines.count(".opencode/agents/") == 1
