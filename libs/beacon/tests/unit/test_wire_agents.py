"""Unit tests for wire_agent_claudecode, wire_agent_opencode, and unwire_agent.

Covers TC1-TC5 from tasks 1.1, TC1-TC3 from task 1.2, and TC1-TC4 from task 1.3.
"""

from pathlib import Path

import pytest
from beacon.domains.setup.wiring import (
    unwire_agent,
    unwire_pruned_artifacts,
    wire_agent_claudecode,
    wire_agent_opencode,
)

# ---------------------------------------------------------------------------
# wire_agent_claudecode
# ---------------------------------------------------------------------------


class TestWireAgentClaudecode:
    def test_tc1_creates_parent_dir_and_symlink(self, tmp_path):
        """TC1: project has no .claude/agents/ → directory is created and symlink written."""
        project = tmp_path / "proj"
        project.mkdir()
        artifact = tmp_path / "artifact" / "agents" / "spec-planner.md"
        artifact.parent.mkdir(parents=True)
        artifact.write_text("agent content")

        result = wire_agent_claudecode(project, artifact)

        expected = project / ".claude" / "agents" / "spec-planner.md"
        assert result == expected
        assert expected.is_symlink()
        assert expected.readlink() == artifact

    def test_tc2_idempotent_same_symlink(self, tmp_path):
        """TC2: project already has .claude/agents/spec-planner.md as identical symlink → no-op."""
        project = tmp_path / "proj"
        project.mkdir()
        artifact = tmp_path / "artifact" / "spec-planner.md"
        artifact.parent.mkdir(parents=True)
        artifact.write_text("agent content")

        # Wire once
        dest = project / ".claude" / "agents" / "spec-planner.md"
        dest.parent.mkdir(parents=True)
        dest.symlink_to(artifact)
        mtime_before = dest.lstat().st_mtime

        result = wire_agent_claudecode(project, artifact)

        # Should return same path, no error, mtime unchanged (no re-link)
        assert result == dest
        assert dest.is_symlink()
        assert dest.lstat().st_mtime == mtime_before

    def test_tc3_replaces_stale_symlink(self, tmp_path):
        """TC3: stale symlink pointing at old artifact path → reconciled to new."""
        project = tmp_path / "proj"
        project.mkdir()
        old_target = tmp_path / "old.md"
        old_target.write_text("old")
        new_target = tmp_path / "new.md"
        new_target.write_text("new")

        # Create stale symlink
        dest = project / ".claude" / "agents" / "new.md"
        dest.parent.mkdir(parents=True)
        dest.symlink_to(old_target)

        result = wire_agent_claudecode(project, new_target)

        assert result == dest
        assert dest.is_symlink()
        assert dest.readlink() == new_target

    def test_tc4_artifact_missing_still_creates_symlink(self, tmp_path):
        """TC4: artifact_file does not exist → symlink still created (lazy resolution)."""
        project = tmp_path / "proj"
        project.mkdir()
        artifact = tmp_path / "artifact" / "missing.md"

        result = wire_agent_claudecode(project, artifact)

        expected = project / ".claude" / "agents" / "missing.md"
        assert result == expected
        assert expected.is_symlink()
        assert expected.readlink() == artifact

    def test_tc5_readonly_filesystem_raises(self, tmp_path):
        """TC5: read-only project root → raises OSError."""
        project = tmp_path / "proj"
        project.mkdir(mode=0o555)
        artifact = tmp_path / "spec-planner.md"
        artifact.write_text("agent")

        try:
            with pytest.raises(OSError):
                wire_agent_claudecode(project, artifact)
        finally:
            project.chmod(0o755)


# ---------------------------------------------------------------------------
# wire_agent_opencode
# ---------------------------------------------------------------------------


class TestWireAgentOpencode:
    def test_tc1_creates_parent_dir_and_symlink(self, tmp_path):
        """TC1: fresh project → directory created and symlink written."""
        project = tmp_path / "proj"
        project.mkdir()
        artifact = tmp_path / "artifact" / "agents" / "spec-planner.md"
        artifact.parent.mkdir(parents=True)
        artifact.write_text("agent content")

        result = wire_agent_opencode(project, artifact)

        expected = project / ".opencode" / "agents" / "spec-planner.md"
        assert result == expected
        assert expected.is_symlink()
        assert expected.readlink() == artifact

    def test_tc2_idempotent_same_symlink(self, tmp_path):
        """TC2: idempotent re-run → no error, no duplicate."""
        project = tmp_path / "proj"
        project.mkdir()
        artifact = tmp_path / "spec-planner.md"
        artifact.write_text("agent content")

        dest = project / ".opencode" / "agents" / "spec-planner.md"
        dest.parent.mkdir(parents=True)
        dest.symlink_to(artifact)
        mtime_before = dest.lstat().st_mtime

        result = wire_agent_opencode(project, artifact)

        assert result == dest
        assert dest.lstat().st_mtime == mtime_before

    def test_tc3_replaces_stale_symlink(self, tmp_path):
        """TC3: stale symlink pointing at old artifact path → updated to new target."""
        project = tmp_path / "proj"
        project.mkdir()
        old_target = tmp_path / "old.md"
        old_target.write_text("old")
        new_target = tmp_path / "new.md"
        new_target.write_text("new")

        dest = project / ".opencode" / "agents" / "new.md"
        dest.parent.mkdir(parents=True)
        dest.symlink_to(old_target)

        result = wire_agent_opencode(project, new_target)

        assert result == dest
        assert dest.is_symlink()
        assert dest.readlink() == new_target


# ---------------------------------------------------------------------------
# unwire_agent
# ---------------------------------------------------------------------------


class TestUnwireAgent:
    def _make_symlinks(self, project: Path, agent_name: str) -> tuple[Path, Path]:
        """Helper to create both agent symlinks."""
        claude_dest = project / ".claude" / "agents" / f"{agent_name}.md"
        opencode_dest = project / ".opencode" / "agents" / f"{agent_name}.md"
        claude_dest.parent.mkdir(parents=True, exist_ok=True)
        opencode_dest.parent.mkdir(parents=True, exist_ok=True)
        claude_dest.symlink_to("/tmp/fake.md")
        opencode_dest.symlink_to("/tmp/fake.md")
        return claude_dest, opencode_dest

    def test_tc1_both_symlinks_removed(self, tmp_path):
        """TC1: both symlinks present → both removed."""
        project = tmp_path / "proj"
        project.mkdir()
        claude_dest, opencode_dest = self._make_symlinks(project, "spec-planner")

        unwire_agent(project, "spec-planner")

        assert not claude_dest.exists() and not claude_dest.is_symlink()
        assert not opencode_dest.exists() and not opencode_dest.is_symlink()

    def test_tc2_only_claude_symlink_present(self, tmp_path):
        """TC2: only Claude symlink present → it is removed; OpenCode absence is not an error."""
        project = tmp_path / "proj"
        project.mkdir()
        claude_dest = project / ".claude" / "agents" / "spec-planner.md"
        claude_dest.parent.mkdir(parents=True)
        claude_dest.symlink_to("/tmp/fake.md")

        # Should not raise
        unwire_agent(project, "spec-planner")

        assert not claude_dest.exists() and not claude_dest.is_symlink()

    def test_tc3_neither_symlink_present_no_error(self, tmp_path):
        """TC3: neither symlink present → no-op, no exception."""
        project = tmp_path / "proj"
        project.mkdir()

        # Should not raise
        unwire_agent(project, "spec-planner")

    def test_tc4_subdirectory_characters_are_sanitised(self, tmp_path):
        """TC4: agent_name with subdirectory chars → only leaf name used."""
        project = tmp_path / "proj"
        project.mkdir()

        # Wire a real symlink at the expected leaf location
        agent_name = "team/reviewer"
        leaf = "reviewer"
        dest = project / ".claude" / "agents" / f"{leaf}.md"
        dest.parent.mkdir(parents=True)
        dest.symlink_to("/tmp/fake.md")

        unwire_agent(project, agent_name)

        # The leaf symlink is removed
        assert not dest.exists() and not dest.is_symlink()
        # Nothing outside .claude/agents/ was touched
        parent_dir = project / ".claude" / "agents" / "team"
        assert not parent_dir.exists()

    def test_stem_without_extension_works(self, tmp_path):
        """agent_name without .md extension is accepted."""
        project = tmp_path / "proj"
        project.mkdir()
        dest = project / ".claude" / "agents" / "my-agent.md"
        dest.parent.mkdir(parents=True)
        dest.symlink_to("/tmp/fake.md")

        unwire_agent(project, "my-agent")

        assert not dest.exists() and not dest.is_symlink()

    def test_agent_name_with_md_extension_works(self, tmp_path):
        """agent_name with .md extension is also accepted."""
        project = tmp_path / "proj"
        project.mkdir()
        dest = project / ".claude" / "agents" / "my-agent.md"
        dest.parent.mkdir(parents=True)
        dest.symlink_to("/tmp/fake.md")

        unwire_agent(project, "my-agent.md")

        assert not dest.exists() and not dest.is_symlink()


# ---------------------------------------------------------------------------
# unwire_pruned_artifacts — agents handling
# ---------------------------------------------------------------------------


class TestUnwirePrunedArtifactsAgents:
    def test_tc_agents_path_calls_unwire_agent(self, tmp_path):
        """unwire_pruned_artifacts with agents/ path calls unwire_agent."""
        project = tmp_path / "proj"
        project.mkdir()
        artifacts_dir = project / ".agentic-beacon" / "artifacts"
        artifacts_dir.mkdir(parents=True)

        # Create a wired agent symlink
        dest = project / ".claude" / "agents" / "spec-planner.md"
        dest.parent.mkdir(parents=True)
        dest.symlink_to("/tmp/fake.md")

        unwire_pruned_artifacts(project, ["agents/spec-planner.md"], artifacts_dir)

        assert not dest.exists() and not dest.is_symlink()

    def test_tc_agents_and_skills_both_handled(self, tmp_path):
        """unwire_pruned_artifacts handles a mix of agents and skills."""
        project = tmp_path / "proj"
        project.mkdir()
        artifacts_dir = project / ".agentic-beacon" / "artifacts"
        artifacts_dir.mkdir(parents=True)

        agent_dest = project / ".claude" / "agents" / "code-reviewer.md"
        agent_dest.parent.mkdir(parents=True)
        agent_dest.symlink_to("/tmp/fake.md")

        # Skills are handled separately — just verify no error thrown
        unwire_pruned_artifacts(
            project,
            ["agents/code-reviewer.md", "skills/some-skill/SKILL.md"],
            artifacts_dir,
        )

        assert not agent_dest.exists() and not agent_dest.is_symlink()
