"""Unit tests for detect_agent_targets — verifies directory-based gating (Bug 3 fix).

detect_agent_targets gates on directory existence (.claude/, .opencode/),
NOT on config files (opencode.json, CLAUDE.md), unlike detect_agents().
"""

from pathlib import Path

from beacon.domains.artifact.agent import detect_agent_targets


def test_detect_agent_targets_both_dirs_present(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".opencode").mkdir()
    assert set(detect_agent_targets(tmp_path)) == {"claudecode", "opencode"}


def test_detect_agent_targets_only_claude_dir(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    assert detect_agent_targets(tmp_path) == ["claudecode"]


def test_detect_agent_targets_only_opencode_dir_no_json(tmp_path: Path) -> None:
    (tmp_path / ".opencode").mkdir()
    # No opencode.json present — directory alone is sufficient
    assert detect_agent_targets(tmp_path) == ["opencode"]


def test_detect_agent_targets_neither_present(tmp_path: Path) -> None:
    assert detect_agent_targets(tmp_path) == []


def test_detect_agent_targets_only_claude_md_does_not_count(tmp_path: Path) -> None:
    # CLAUDE.md alone (no .claude/ dir) does NOT enable claudecode for agent wiring
    (tmp_path / "CLAUDE.md").touch()
    assert detect_agent_targets(tmp_path) == []


def test_detect_agent_targets_only_opencode_json_does_not_count(tmp_path: Path) -> None:
    # opencode.json alone (no .opencode/ dir) does NOT enable opencode for agent wiring
    (tmp_path / "opencode.json").write_text("{}")
    assert detect_agent_targets(tmp_path) == []
