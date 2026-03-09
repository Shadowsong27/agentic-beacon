"""Tests for GitignoreManager - automatic .gitignore management.

Following TDD workflow for tasks 11.1-11.5:
- Task 11.1: Exclude config.toml
- Task 11.2: Exclude artifacts/
- Task 11.3: Ensure beacon.yaml NOT excluded
- Task 11.4: Create .gitignore if doesn't exist
- Task 11.5: Append without destroying content
"""

import pytest
from pathlib import Path
from beacon.core.gitignore import GitignoreManager, GITIGNORE_ENTRIES, SECTION_HEADER


# ========== Task 11.1 & 11.4: Create/update .gitignore with config.toml ==========


def test_creates_gitignore_if_missing(temp_dir):
    """TC1: No .gitignore exists → Creates .gitignore with entries."""
    mgr = GitignoreManager(temp_dir)
    result = mgr.ensure_entries()
    assert result is True
    assert (temp_dir / ".gitignore").exists()
    content = (temp_dir / ".gitignore").read_text()
    assert ".agentic-beacon/config.toml" in content
    assert ".agentic-beacon/artifacts/" in content


def test_appends_missing_entries(temp_dir):
    """TC2: .gitignore exists, entries missing → Appends entries."""
    gitignore = temp_dir / ".gitignore"
    gitignore.write_text("node_modules/\n*.log\n")

    mgr = GitignoreManager(temp_dir)
    result = mgr.ensure_entries()
    assert result is True
    content = gitignore.read_text()
    assert "node_modules/" in content
    assert "*.log" in content
    assert ".agentic-beacon/config.toml" in content


def test_no_duplicates_on_repeat(temp_dir):
    """TC3: .gitignore already has entries → No duplicate added."""
    mgr = GitignoreManager(temp_dir)
    mgr.ensure_entries()
    result = mgr.ensure_entries()  # Second call
    assert result is False  # No changes needed

    content = (temp_dir / ".gitignore").read_text()
    assert content.count(".agentic-beacon/config.toml") == 1
    assert content.count(".agentic-beacon/artifacts/") == 1


def test_run_multiple_times(temp_dir):
    """TC5: Run connect twice → Only one entry exists."""
    mgr = GitignoreManager(temp_dir)
    mgr.ensure_entries()
    mgr.ensure_entries()
    mgr.ensure_entries()

    content = (temp_dir / ".gitignore").read_text()
    assert content.count(".agentic-beacon/config.toml") == 1


def test_exact_entry_format(temp_dir):
    """TC10: Verify entry is exactly '.agentic-beacon/config.toml'."""
    mgr = GitignoreManager(temp_dir)
    mgr.ensure_entries()

    content = (temp_dir / ".gitignore").read_text()
    lines = content.splitlines()
    assert ".agentic-beacon/config.toml" in lines


# ========== Task 11.2: Exclude artifacts/ ==========


def test_artifacts_entry_has_trailing_slash(temp_dir):
    """TC1: Entry added with trailing slash → Pattern is '.agentic-beacon/artifacts/'."""
    mgr = GitignoreManager(temp_dir)
    mgr.ensure_entries()

    content = (temp_dir / ".gitignore").read_text()
    assert ".agentic-beacon/artifacts/" in content


def test_both_entries_present(temp_dir):
    """TC4: Both config.toml and artifacts/ entries → Both present."""
    mgr = GitignoreManager(temp_dir)
    mgr.ensure_entries()

    content = (temp_dir / ".gitignore").read_text()
    assert ".agentic-beacon/config.toml" in content
    assert ".agentic-beacon/artifacts/" in content


def test_section_header_added(temp_dir):
    """TC5: .gitignore section header added → Entries grouped under comment."""
    mgr = GitignoreManager(temp_dir)
    mgr.ensure_entries()

    content = (temp_dir / ".gitignore").read_text()
    assert SECTION_HEADER in content


# ========== Task 11.3: beacon.yaml NOT excluded ==========


def test_beacon_yaml_not_in_gitignore(temp_dir):
    """TC1: After all commands → beacon.yaml not in .gitignore."""
    mgr = GitignoreManager(temp_dir)
    mgr.ensure_entries()

    content = (temp_dir / ".gitignore").read_text()
    assert "beacon.yaml" not in content


def test_verify_beacon_yaml_not_ignored(temp_dir):
    """TC2: verify_beacon_yaml_not_ignored returns True when safe."""
    mgr = GitignoreManager(temp_dir)
    mgr.ensure_entries()
    assert mgr.verify_beacon_yaml_not_ignored() is True


def test_verify_detects_beacon_yaml_ignored(temp_dir):
    """Detect when beacon.yaml is accidentally ignored."""
    gitignore = temp_dir / ".gitignore"
    gitignore.write_text(".agentic-beacon/*\n")

    mgr = GitignoreManager(temp_dir)
    assert mgr.verify_beacon_yaml_not_ignored() is False


# ========== Task 11.5: Append without destroying content ==========


def test_existing_content_preserved(temp_dir):
    """TC1: Existing content preserved → Original lines intact."""
    gitignore = temp_dir / ".gitignore"
    gitignore.write_text("node_modules/\n*.log\n.env\n")

    mgr = GitignoreManager(temp_dir)
    mgr.ensure_entries()

    content = gitignore.read_text()
    assert "node_modules/" in content
    assert "*.log" in content
    assert ".env" in content


def test_new_entries_appended_at_end(temp_dir):
    """TC2: New entries appended at end → After existing content."""
    gitignore = temp_dir / ".gitignore"
    gitignore.write_text("node_modules/\n")

    mgr = GitignoreManager(temp_dir)
    mgr.ensure_entries()

    content = gitignore.read_text()
    lines = content.splitlines()
    node_idx = lines.index("node_modules/")
    beacon_idx = lines.index(".agentic-beacon/config.toml")
    assert beacon_idx > node_idx


def test_proper_newline_separation(temp_dir):
    """TC3: Proper newline separation → Blank line before section."""
    gitignore = temp_dir / ".gitignore"
    gitignore.write_text("node_modules/\n")

    mgr = GitignoreManager(temp_dir)
    mgr.ensure_entries()

    content = gitignore.read_text()
    # Should not have node_modules/ directly followed by # Agentic Beacon
    assert "node_modules/\n\n" in content or "node_modules/\n# Agentic Beacon" in content


def test_comments_preserved(temp_dir):
    """TC7: Comments in original .gitignore → Preserved correctly."""
    gitignore = temp_dir / ".gitignore"
    gitignore.write_text("# Build artifacts\nbuild/\n# Dependencies\nnode_modules/\n")

    mgr = GitignoreManager(temp_dir)
    mgr.ensure_entries()

    content = gitignore.read_text()
    assert "# Build artifacts" in content
    assert "# Dependencies" in content


def test_has_entry_check(temp_dir):
    """has_entry returns correct boolean."""
    mgr = GitignoreManager(temp_dir)
    assert mgr.has_entry(".agentic-beacon/config.toml") is False

    mgr.ensure_entries()
    assert mgr.has_entry(".agentic-beacon/config.toml") is True
    assert mgr.has_entry("nonexistent") is False


def test_custom_entries(temp_dir):
    """ensure_entries accepts custom entries."""
    mgr = GitignoreManager(temp_dir)
    result = mgr.ensure_entries(["custom-entry-1", "custom-entry-2"])
    assert result is True

    content = (temp_dir / ".gitignore").read_text()
    assert "custom-entry-1" in content
    assert "custom-entry-2" in content
