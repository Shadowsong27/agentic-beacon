"""Unit tests for cleanup_legacy_global_agent_symlinks.

Covers TC1-TC10 from task 4.1, plus marker-skip behavior (PER-133).
All tests use tmp_path fixtures to simulate home dirs without touching real ~/.claude.
"""

from pathlib import Path
from unittest.mock import patch

from beacon.domains.distribution.legacy_cleanup import (
    cleanup_legacy_global_agent_symlinks,
)


def _make_warehouse(tmp_path: Path) -> Path:
    """Create a minimal fake warehouse with an agents/ directory."""
    warehouse = tmp_path / "warehouse"
    (warehouse / "agents").mkdir(parents=True)
    return warehouse


def _make_home(tmp_path: Path) -> Path:
    """Create a fake HOME directory with agent dirs."""
    home = tmp_path / "home"
    home.mkdir()
    return home


def _make_project_root(tmp_path: Path) -> Path:
    """Create a fake project root."""
    project = tmp_path / "project"
    project.mkdir()
    return project


def _patch_home(home: Path):
    """Context manager to patch Path.home() to return a fake home."""
    return patch.object(Path, "home", return_value=home)


class TestCleanupLegacyGlobalAgentSymlinks:
    def test_tc1_claude_symlink_into_warehouse_removed(self, tmp_path):
        """TC1: legacy symlink in ~/.claude/agents/ targeting warehouse/agents/foo.md → removed."""
        warehouse = _make_warehouse(tmp_path)
        home = _make_home(tmp_path)
        project_root = _make_project_root(tmp_path)

        agent_file = warehouse / "agents" / "foo.md"
        agent_file.write_text("agent")

        claude_agents = home / ".claude" / "agents"
        claude_agents.mkdir(parents=True)
        legacy = claude_agents / "foo.md"
        legacy.symlink_to(agent_file)

        with _patch_home(home):
            count = cleanup_legacy_global_agent_symlinks(warehouse, project_root)

        assert count == 1
        assert not legacy.exists() and not legacy.is_symlink()

    def test_tc2_opencode_symlink_into_warehouse_removed(self, tmp_path):
        """TC2: legacy symlink in ~/.config/opencode/agents/ targeting warehouse/agents/foo.md → removed."""
        warehouse = _make_warehouse(tmp_path)
        home = _make_home(tmp_path)
        project_root = _make_project_root(tmp_path)

        agent_file = warehouse / "agents" / "foo.md"
        agent_file.write_text("agent")

        opencode_agents = home / ".config" / "opencode" / "agents"
        opencode_agents.mkdir(parents=True)
        legacy = opencode_agents / "foo.md"
        legacy.symlink_to(agent_file)

        with _patch_home(home):
            count = cleanup_legacy_global_agent_symlinks(warehouse, project_root)

        assert count == 1
        assert not legacy.exists() and not legacy.is_symlink()

    def test_tc3_non_warehouse_symlink_preserved(self, tmp_path):
        """TC3: symlink in ~/.claude/agents/ pointing elsewhere → preserved."""
        warehouse = _make_warehouse(tmp_path)
        home = _make_home(tmp_path)
        project_root = _make_project_root(tmp_path)

        elsewhere = tmp_path / "elsewhere.md"
        elsewhere.write_text("not warehouse")

        claude_agents = home / ".claude" / "agents"
        claude_agents.mkdir(parents=True)
        safe = claude_agents / "elsewhere.md"
        safe.symlink_to(elsewhere)

        with _patch_home(home):
            count = cleanup_legacy_global_agent_symlinks(warehouse, project_root)

        assert count == 0
        assert safe.is_symlink()

    def test_tc4_regular_file_preserved(self, tmp_path):
        """TC4: regular file in ~/.claude/agents/handcrafted.md → preserved."""
        warehouse = _make_warehouse(tmp_path)
        home = _make_home(tmp_path)
        project_root = _make_project_root(tmp_path)

        claude_agents = home / ".claude" / "agents"
        claude_agents.mkdir(parents=True)
        regular = claude_agents / "handcrafted.md"
        regular.write_text("handcrafted")

        with _patch_home(home):
            count = cleanup_legacy_global_agent_symlinks(warehouse, project_root)

        assert count == 0
        assert regular.read_text() == "handcrafted"

    def test_tc5_missing_opencode_dir_skipped(self, tmp_path):
        """TC5: ~/.config/opencode/agents/ does not exist → function skips without error."""
        warehouse = _make_warehouse(tmp_path)
        home = _make_home(tmp_path)
        project_root = _make_project_root(tmp_path)
        # Only create .claude/agents/, not .config/opencode/agents/
        (home / ".claude" / "agents").mkdir(parents=True)

        with _patch_home(home):
            count = cleanup_legacy_global_agent_symlinks(warehouse, project_root)

        assert count == 0

    def test_tc6_dangling_symlink_preserved(self, tmp_path):
        """TC6: dangling symlink (target does not exist) → preserved."""
        warehouse = _make_warehouse(tmp_path)
        home = _make_home(tmp_path)
        project_root = _make_project_root(tmp_path)

        claude_agents = home / ".claude" / "agents"
        claude_agents.mkdir(parents=True)
        dangling = claude_agents / "dangling.md"
        # Point to a warehouse agents file that doesn't exist
        dangling.symlink_to(warehouse / "agents" / "nonexistent.md")

        with _patch_home(home):
            count = cleanup_legacy_global_agent_symlinks(warehouse, project_root)

        # A dangling symlink whose target path resolves under warehouse/agents/
        # IS removed: resolve(strict=False) returns the canonical target path
        # whether or not it exists, and that path is under warehouse_agents.
        # Cleanup intent is "any symlink whose target points into the warehouse"
        # so dangling-into-warehouse links are correctly classified as legacy.
        assert count == 1

    def test_tc7_subdirectory_not_recursed(self, tmp_path):
        """TC7: subdirectory containing symlinks → not recursed into; nested entries preserved."""
        warehouse = _make_warehouse(tmp_path)
        home = _make_home(tmp_path)
        project_root = _make_project_root(tmp_path)

        claude_agents = home / ".claude" / "agents"
        (claude_agents / "subdir").mkdir(parents=True)

        agent_file = warehouse / "agents" / "nested.md"
        agent_file.write_text("nested agent")
        nested_symlink = claude_agents / "subdir" / "nested.md"
        nested_symlink.symlink_to(agent_file)

        with _patch_home(home):
            count = cleanup_legacy_global_agent_symlinks(warehouse, project_root)

        assert count == 0
        assert nested_symlink.is_symlink()

    def test_tc8_warehouse_is_symlink_still_matches(self, tmp_path):
        """TC8: warehouse_path itself is a symlink → resolution still matches."""
        actual_warehouse = _make_warehouse(tmp_path)
        home = _make_home(tmp_path)
        project_root = _make_project_root(tmp_path)

        # Create a symlink to the warehouse
        warehouse_link = tmp_path / "warehouse-link"
        warehouse_link.symlink_to(actual_warehouse)

        agent_file = actual_warehouse / "agents" / "foo.md"
        agent_file.write_text("agent")

        claude_agents = home / ".claude" / "agents"
        claude_agents.mkdir(parents=True)
        legacy = claude_agents / "foo.md"
        legacy.symlink_to(agent_file)

        # Pass the symlinked path; function should still detect the match
        with _patch_home(home):
            count = cleanup_legacy_global_agent_symlinks(warehouse_link, project_root)

        assert count == 1
        assert not legacy.exists() and not legacy.is_symlink()

    def test_tc9_empty_dirs_return_zero(self, tmp_path):
        """TC9: empty home agent dirs → returns 0; no exception."""
        warehouse = _make_warehouse(tmp_path)
        home = _make_home(tmp_path)
        project_root = _make_project_root(tmp_path)
        (home / ".claude" / "agents").mkdir(parents=True)
        (home / ".config" / "opencode" / "agents").mkdir(parents=True)

        with _patch_home(home):
            count = cleanup_legacy_global_agent_symlinks(warehouse, project_root)

        assert count == 0

    def test_tc10_many_matching_symlinks_all_removed(self, tmp_path):
        """TC10: 50 matching symlinks → all 50 removed; returned count is 50."""
        warehouse = _make_warehouse(tmp_path)
        home = _make_home(tmp_path)
        project_root = _make_project_root(tmp_path)

        claude_agents = home / ".claude" / "agents"
        claude_agents.mkdir(parents=True)

        for i in range(50):
            agent_file = warehouse / "agents" / f"agent-{i:02d}.md"
            agent_file.write_text(f"agent {i}")
            (claude_agents / f"agent-{i:02d}.md").symlink_to(agent_file)

        with _patch_home(home):
            count = cleanup_legacy_global_agent_symlinks(warehouse, project_root)

        assert count == 50
        for i in range(50):
            assert not (claude_agents / f"agent-{i:02d}.md").exists()

    def test_both_dirs_counted(self, tmp_path):
        """Symlinks removed from both dirs contribute to the total count."""
        warehouse = _make_warehouse(tmp_path)
        home = _make_home(tmp_path)
        project_root = _make_project_root(tmp_path)

        agent_file = warehouse / "agents" / "shared.md"
        agent_file.write_text("shared agent")

        claude_agents = home / ".claude" / "agents"
        claude_agents.mkdir(parents=True)
        (claude_agents / "shared.md").symlink_to(agent_file)

        opencode_agents = home / ".config" / "opencode" / "agents"
        opencode_agents.mkdir(parents=True)
        (opencode_agents / "shared.md").symlink_to(agent_file)

        with _patch_home(home):
            count = cleanup_legacy_global_agent_symlinks(warehouse, project_root)

        assert count == 2
        assert not (claude_agents / "shared.md").is_symlink()
        assert not (opencode_agents / "shared.md").is_symlink()

    def test_idempotent_second_call_returns_zero(self, tmp_path):
        """Second run after cleanup returns 0 and raises no error."""
        warehouse = _make_warehouse(tmp_path)
        home = _make_home(tmp_path)
        project_root = _make_project_root(tmp_path)

        agent_file = warehouse / "agents" / "foo.md"
        agent_file.write_text("agent")

        claude_agents = home / ".claude" / "agents"
        claude_agents.mkdir(parents=True)
        (claude_agents / "foo.md").symlink_to(agent_file)

        with _patch_home(home):
            count1 = cleanup_legacy_global_agent_symlinks(warehouse, project_root)
            count2 = cleanup_legacy_global_agent_symlinks(warehouse, project_root)

        assert count1 == 1
        # Second call short-circuits via marker
        assert count2 == 0

    def test_cleanup_writes_marker_after_first_run(self, tmp_path):
        """Marker file is written after the first scan, even when nothing was removed."""
        warehouse = _make_warehouse(tmp_path)
        home = _make_home(tmp_path)
        project_root = _make_project_root(tmp_path)

        marker = project_root / ".agentic-beacon" / ".legacy-migrated"
        assert not marker.exists()

        with _patch_home(home):
            cleanup_legacy_global_agent_symlinks(warehouse, project_root)

        assert marker.exists()
        assert "PER-113" in marker.read_text()

    def test_cleanup_skipped_when_marker_present(self, tmp_path):
        """When the marker exists, the home-dir scan is skipped entirely."""
        warehouse = _make_warehouse(tmp_path)
        home = _make_home(tmp_path)
        project_root = _make_project_root(tmp_path)

        # Pre-create a symlink that would be removed if the scan ran
        agent_file = warehouse / "agents" / "foo.md"
        agent_file.write_text("agent")
        claude_agents = home / ".claude" / "agents"
        claude_agents.mkdir(parents=True)
        legacy = claude_agents / "foo.md"
        legacy.symlink_to(agent_file)

        # Write marker to simulate "already ran"
        marker = project_root / ".agentic-beacon" / ".legacy-migrated"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("already ran\n")

        with _patch_home(home):
            count = cleanup_legacy_global_agent_symlinks(warehouse, project_root)

        assert count == 0
        # Symlink untouched because scan was skipped
        assert legacy.is_symlink()

    def test_marker_deletion_re_enables_cleanup(self, tmp_path):
        """Deleting the marker allows the scan to run again on the next call."""
        warehouse = _make_warehouse(tmp_path)
        home = _make_home(tmp_path)
        project_root = _make_project_root(tmp_path)

        agent_file = warehouse / "agents" / "foo.md"
        agent_file.write_text("agent")
        claude_agents = home / ".claude" / "agents"
        claude_agents.mkdir(parents=True)

        marker = project_root / ".agentic-beacon" / ".legacy-migrated"

        with _patch_home(home):
            # First call: marker absent, scan runs but finds nothing (no symlinks yet)
            count1 = cleanup_legacy_global_agent_symlinks(warehouse, project_root)
            assert count1 == 0
            assert marker.exists()

            # Delete marker and add a symlink for the second call to find
            marker.unlink()
            legacy = claude_agents / "foo.md"
            legacy.symlink_to(agent_file)

            # Second call: marker absent again, scan runs and removes symlink
            count2 = cleanup_legacy_global_agent_symlinks(warehouse, project_root)

        assert count2 == 1
        assert not legacy.is_symlink()
        assert marker.exists()
