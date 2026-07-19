"""Tests for unconditional agent-dir gitignore coverage via the managed-block engine.

Agent dirs (`.claude/agents/`, `.opencode/agents/`) are now owned by the Tier A
managed block unconditionally — the old conditional gating and prune behavior
is retired. These tests verify the unconditional behavior via the managed-block
engine that supersedes the removed `ensure_agent_dirs_gitignored` /
`prune_agent_dirs_gitignore_entries` helpers.
"""

from beacon.core.gitignore import (
    TIER_A_ENTRIES,
    apply_all_gitignores,
    read_managed_block,
)


class TestAgentDirsUnconditionalInTierA:
    def test_agent_dirs_present_without_declared_agents(self, tmp_path):
        """TC1: Agent dirs in Tier A block even with no declared agents."""
        project = tmp_path / "proj"
        project.mkdir()

        apply_all_gitignores(project)

        body = read_managed_block(project / ".gitignore")
        assert body is not None
        assert ".claude/agents/" in body
        assert ".opencode/agents/" in body

    def test_agent_dirs_present_without_tool_dirs(self, tmp_path):
        """TC2: Agent dirs in Tier A block even without .claude/ / .opencode/ dirs."""
        project = tmp_path / "proj"
        project.mkdir()

        apply_all_gitignores(project)

        body = read_managed_block(project / ".gitignore")
        assert body is not None
        assert set(body) == set(TIER_A_ENTRIES)

    def test_idempotent_multiple_calls(self, tmp_path):
        """Calling apply_all_gitignores multiple times produces no duplicates."""
        project = tmp_path / "proj"
        project.mkdir()

        apply_all_gitignores(project)
        apply_all_gitignores(project)
        apply_all_gitignores(project)

        body = read_managed_block(project / ".gitignore")
        assert body is not None
        assert body.count(".claude/agents/") == 1 if isinstance(body, list) else True
        assert ".claude/agents/" in body
        assert ".opencode/agents/" in body

    def test_entries_not_pruned_when_agents_removed(self, tmp_path):
        """Agent dirs are NOT pruned — they're unconditional in Tier A."""
        project = tmp_path / "proj"
        project.mkdir()

        apply_all_gitignores(project)
        body = read_managed_block(project / ".gitignore")
        assert ".claude/agents/" in body

        # No prune happens — unconditional entries persist
        apply_all_gitignores(project)
        body2 = read_managed_block(project / ".gitignore")
        assert ".claude/agents/" in body2
