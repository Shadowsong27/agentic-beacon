"""Unit tests for beacon.utils.display.format_regular_file_conflict."""

from beacon.core.exceptions import AgentWireConflict
from beacon.utils.display import format_regular_file_conflict


def test_format_regular_file_conflict_singular(tmp_path):
    """Single conflict: output mentions '1 agent', rm command, mv command, abc adopt."""
    dest = tmp_path / ".claude" / "agents" / "spec-planner.md"
    conflicts = [
        AgentWireConflict(dest=dest, agent_name="spec-planner", tool="claudecode")
    ]

    output = format_regular_file_conflict(conflicts)

    assert "Cannot wire 1 agent" in output
    assert "rm " in output
    assert "mv " in output
    assert "abc adopt" in output
    assert "spec-planner.user.md" in output


def test_format_regular_file_conflict_plural(tmp_path):
    """Three conflicts: output mentions '3 agents', three rm lines, three mv lines."""
    conflicts = [
        AgentWireConflict(
            dest=tmp_path / ".claude" / "agents" / f"agent-{i}.md",
            agent_name=f"agent-{i}",
            tool="claudecode",
        )
        for i in range(3)
    ]

    output = format_regular_file_conflict(conflicts)

    assert "Cannot wire 3 agents" in output
    assert output.count("rm ") == 3
    assert output.count("mv ") == 3


def test_format_regular_file_conflict_uses_relative_paths_when_possible(
    tmp_path, monkeypatch
):
    """When dest is under CWD, output shows the relative path, not the absolute one."""
    monkeypatch.chdir(tmp_path)
    dest = tmp_path / ".claude" / "agents" / "spec-planner.md"
    conflicts = [
        AgentWireConflict(dest=dest, agent_name="spec-planner", tool="claudecode")
    ]

    output = format_regular_file_conflict(conflicts)

    # Relative path present
    assert ".claude/agents/spec-planner.md" in output
    # Absolute prefix absent
    assert str(tmp_path) not in output
