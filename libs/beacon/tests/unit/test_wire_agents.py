"""Unit tests for wire_agent_claudecode, wire_agent_opencode, and unwire_agent.

Covers TC1-TC5 from tasks 1.1, TC1-TC3 from task 1.2, and TC1-TC4 from task 1.3.
"""

from pathlib import Path

import pytest
from beacon.core.exceptions import BeaconSyncError
from beacon.domains.setup.wiring import (
    _snapshot_agent_path,
    unwire_agent,
    unwire_agent_with_undo,
    unwire_pruned_artifacts,
    wire_agent_claudecode,
    wire_agent_opencode,
    wire_agents_atomically,
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


# ---------------------------------------------------------------------------
# Finding 1: unwire_agent / unwire_agent_with_undo preserve regular files
# ---------------------------------------------------------------------------


def test_unwire_agent_preserves_regular_file(tmp_path):
    """Regular file at .claude/agents/<name>.md must NOT be deleted by unwire_agent."""
    target = tmp_path / ".claude" / "agents" / "spec-planner.md"
    target.parent.mkdir(parents=True)
    target.write_text("user-authored content")

    unwire_agent(tmp_path, "spec-planner")

    assert target.exists() and not target.is_symlink()
    assert target.read_text() == "user-authored content"


def test_unwire_agent_with_undo_preserves_regular_file(tmp_path):
    """Regular file at the agent path must NOT be deleted by unwire_agent_with_undo."""
    target = tmp_path / ".opencode" / "agents" / "spec-planner.md"
    target.parent.mkdir(parents=True)
    target.write_text("user-authored content")

    removed = unwire_agent_with_undo(tmp_path, "spec-planner")

    assert target.exists() and target.read_text() == "user-authored content"
    assert removed == []  # nothing removed → nothing to roll back


# ---------------------------------------------------------------------------
# Finding 3: wire_agent_* refuse to overwrite regular files
# ---------------------------------------------------------------------------


def test_wire_agent_claudecode_refuses_to_overwrite_regular_file(tmp_path):
    """Regular file at dest must cause BeaconSyncError, not FileExistsError or silent overwrite."""
    from beacon.core.exceptions import BeaconSyncError

    target = tmp_path / ".claude" / "agents" / "spec-planner.md"
    target.parent.mkdir(parents=True)
    target.write_text("user-authored content")

    artifact_file = tmp_path / "warehouse" / "agents" / "spec-planner.md"
    artifact_file.parent.mkdir(parents=True)
    artifact_file.write_text("warehouse content")

    with pytest.raises(BeaconSyncError) as exc:
        wire_agent_claudecode(tmp_path, artifact_file)
    assert "regular file" in str(exc.value)
    assert target.read_text() == "user-authored content"  # not overwritten


def test_wire_agent_opencode_refuses_to_overwrite_regular_file(tmp_path):
    """Same as above but for opencode side."""
    from beacon.core.exceptions import BeaconSyncError

    target = tmp_path / ".opencode" / "agents" / "spec-planner.md"
    target.parent.mkdir(parents=True)
    target.write_text("user-authored content")

    artifact_file = tmp_path / "warehouse" / "agents" / "spec-planner.md"
    artifact_file.parent.mkdir(parents=True)
    artifact_file.write_text("warehouse content")

    with pytest.raises(BeaconSyncError) as exc:
        wire_agent_opencode(tmp_path, artifact_file)
    assert "regular file" in str(exc.value)
    assert target.read_text() == "user-authored content"


# ---------------------------------------------------------------------------
# _snapshot_agent_path (PER-131)
# ---------------------------------------------------------------------------


class TestSnapshotAgentPath:
    def test_missing_returns_missing_none(self, tmp_path):
        """Path that does not exist → ('missing', None)."""
        p = tmp_path / "nope.md"
        assert _snapshot_agent_path(p) == ("missing", None)

    def test_regular_file_returns_regular_file_none(self, tmp_path):
        """Regular file at path → ('regular_file', None)."""
        p = tmp_path / "file.md"
        p.write_text("user content")
        assert _snapshot_agent_path(p) == ("regular_file", None)

    def test_symlink_returns_symlink_with_target(self, tmp_path):
        """Symlink at path → ('symlink', target). Target captured even if dangling."""
        target = tmp_path / "target.md"
        target.write_text("artifact content")
        link = tmp_path / "link.md"
        link.symlink_to(target)

        kind, captured = _snapshot_agent_path(link)
        assert kind == "symlink"
        assert captured == target

    def test_dangling_symlink_returns_symlink_with_target(self, tmp_path):
        """Dangling symlink (target deleted) still snapshots as ('symlink', target)."""
        target = tmp_path / "ghost.md"
        link = tmp_path / "link.md"
        link.symlink_to(target)
        # target never created — symlink is dangling

        kind, captured = _snapshot_agent_path(link)
        assert kind == "symlink"
        assert captured == target


# ---------------------------------------------------------------------------
# wire_agents_atomically (PER-131)
# ---------------------------------------------------------------------------


def _make_artifact(base: Path, name: str, content: str = "x") -> Path:
    """Create an artifact file under base/agents/ and return its Path."""
    artifact = base / "agents" / name
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(content)
    return artifact


class TestWireAgentsAtomically:
    def test_empty_list_is_noop(self, tmp_path):
        """No agents → helper returns without touching anything."""
        project = tmp_path / "proj"
        project.mkdir()

        wire_agents_atomically(project, [], {"claudecode", "opencode"})

        # No directories should have been created by the helper itself.
        assert not (project / ".claude" / "agents").exists()
        assert not (project / ".opencode" / "agents").exists()

    def test_happy_path_single_tool(self, tmp_path):
        """One agent, one tool, missing dest → wired symlink."""
        project = tmp_path / "proj"
        project.mkdir()
        artifact = _make_artifact(tmp_path / "warehouse", "spec-planner.md")

        wire_agents_atomically(project, [artifact], {"claudecode"})

        dest = project / ".claude" / "agents" / "spec-planner.md"
        assert dest.is_symlink()
        assert dest.readlink() == artifact

    def test_happy_path_dual_tool(self, tmp_path):
        """One agent, both tools detected → wired in both."""
        project = tmp_path / "proj"
        project.mkdir()
        artifact = _make_artifact(tmp_path / "warehouse", "spec-planner.md")

        wire_agents_atomically(project, [artifact], {"claudecode", "opencode"})

        for tool in (".claude", ".opencode"):
            dest = project / tool / "agents" / "spec-planner.md"
            assert dest.is_symlink(), f"{dest} must be a symlink"
            assert dest.readlink() == artifact

    def test_rollback_unwires_when_second_agent_fails(self, tmp_path):
        """First agent wires; second raises → first is unwired (rollback)."""
        project = tmp_path / "proj"
        project.mkdir()

        artifact_a = _make_artifact(tmp_path / "warehouse", "agent-a.md")
        artifact_b = _make_artifact(tmp_path / "warehouse", "agent-b.md")

        # Plant a regular-file blocker at agent-b's claudecode dest so the
        # SECOND wire_agent_claudecode call raises BeaconSyncError.
        blocker = project / ".claude" / "agents" / "agent-b.md"
        blocker.parent.mkdir(parents=True, exist_ok=True)
        blocker.write_text("user content")

        with pytest.raises(BeaconSyncError):
            wire_agents_atomically(project, [artifact_a, artifact_b], {"claudecode"})

        # agent-a's destination must be rolled back (no symlink left).
        dest_a = project / ".claude" / "agents" / "agent-a.md"
        assert not dest_a.is_symlink() and not dest_a.exists()

        # User's regular file at agent-b's dest must be untouched.
        assert blocker.read_text() == "user content"

    def test_rollback_restores_prior_symlink_target(self, tmp_path):
        """Pre-existing symlink at dest → wire replaces → rollback restores prior target.

        This exercises the 'symlink' branch of _rollback that the missing→wired
        integration tests don't cover.
        """
        project = tmp_path / "proj"
        project.mkdir()

        # Pre-existing symlink at agent-a's dest → /tmp/.../old-target
        old_target = tmp_path / "old-target.md"
        old_target.write_text("old content")
        dest_a = project / ".claude" / "agents" / "agent-a.md"
        dest_a.parent.mkdir(parents=True, exist_ok=True)
        dest_a.symlink_to(old_target)

        # New artifact-a (different from old_target) — wire will replace.
        artifact_a = _make_artifact(tmp_path / "warehouse", "agent-a.md", "new")
        artifact_b = _make_artifact(tmp_path / "warehouse", "agent-b.md")

        # Blocker on agent-b's claudecode dest → second wire raises.
        blocker = project / ".claude" / "agents" / "agent-b.md"
        blocker.write_text("user content")

        with pytest.raises(BeaconSyncError):
            wire_agents_atomically(project, [artifact_a, artifact_b], {"claudecode"})

        # agent-a's dest must be restored to point at old_target, NOT artifact_a.
        assert dest_a.is_symlink(), "agent-a dest must remain a symlink"
        assert dest_a.readlink() == old_target, (
            f"agent-a must be restored to old-target; "
            f"current readlink={dest_a.readlink()}"
        )

    def test_rollback_preserves_user_regular_file(self, tmp_path):
        """A regular-file snapshot is recorded but rollback must not touch it.

        The wire helpers refuse to overwrite regular files, so the wire never
        succeeded for that path and rollback's regular_file branch is a no-op.
        """
        project = tmp_path / "proj"
        project.mkdir()

        # User-owned regular file at the very FIRST destination — wire fails
        # immediately.
        dest = project / ".claude" / "agents" / "agent-a.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("user content")

        artifact_a = _make_artifact(tmp_path / "warehouse", "agent-a.md")

        with pytest.raises(BeaconSyncError):
            wire_agents_atomically(project, [artifact_a], {"claudecode"})

        # User's file is preserved verbatim.
        assert dest.read_text() == "user content"
        assert not dest.is_symlink()

    def test_unknown_tool_in_detected_set_is_ignored(self, tmp_path):
        """Tool keys not in {'claudecode', 'opencode'} are silently ignored.

        Forward-compat guard: future tool additions must be opt-in via explicit
        if-branches in the helper, not via the detected_tools set alone.
        """
        project = tmp_path / "proj"
        project.mkdir()
        artifact = _make_artifact(tmp_path / "warehouse", "spec-planner.md")

        wire_agents_atomically(project, [artifact], {"claudecode", "future-tool"})

        # Only claudecode wired; future-tool was ignored.
        assert (project / ".claude" / "agents" / "spec-planner.md").is_symlink()
        assert not (project / ".future-tool").exists()
