"""Tests for Claude Code external-import approval in the user's .claude.json."""

import json
import os
import stat

import pytest
from beacon.domains.setup import claude_approval
from beacon.domains.setup.claude_approval import (
    APPROVAL_FLAG,
    ApprovalStatus,
    ensure_claude_approval,
    inspect_claude_approval,
)

WIRED_AGENTS_MD = "# Project\n@.agentic-beacon/artifacts/contexts/x.md\n"


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "AGENTS.md").write_text(WIRED_AGENTS_MD)
    return root


@pytest.fixture
def config_path(isolated_claude_config):
    return isolated_claude_config / ".claude.json"


@pytest.fixture
def claude_on_path(monkeypatch):
    monkeypatch.setattr(claude_approval.shutil, "which", lambda name: "/bin/claude")


@pytest.fixture
def claude_absent(monkeypatch):
    monkeypatch.setattr(claude_approval.shutil, "which", lambda name: None)


def _key(project):
    return str(project.resolve())


def test_sets_flag_and_preserves_other_keys_mode_and_newline(
    project, config_path, claude_on_path
):
    original = {
        "numStartups": 7,
        "projects": {
            "/some/other": {"allowedTools": ["Bash"]},
            _key(project): {"allowedTools": [], "lastCost": 1.5},
        },
    }
    config_path.write_text(json.dumps(original))
    config_path.chmod(0o640)

    result = ensure_claude_approval(project)

    assert result.status is ApprovalStatus.APPROVED
    raw = config_path.read_text()
    assert not raw.endswith("\n")
    assert stat.S_IMODE(config_path.stat().st_mode) == 0o640
    after = json.loads(raw)
    expected = json.loads(json.dumps(original))
    expected["projects"][_key(project)][APPROVAL_FLAG] = True
    assert after == expected


@pytest.mark.parametrize(
    "initial",
    [
        {"numStartups": 1},
        {"numStartups": 1, "projects": {"/other": {}}},
    ],
    ids=["no-projects-key", "project-entry-absent"],
)
def test_creates_missing_projects_or_entry_with_only_the_flag(
    project, config_path, claude_on_path, initial
):
    config_path.write_text(json.dumps(initial) + "\n")

    result = ensure_claude_approval(project)

    assert result.status is ApprovalStatus.APPROVED
    after = json.loads(config_path.read_text())
    assert after["numStartups"] == 1
    assert after["projects"][_key(project)] == {APPROVAL_FLAG: True}
    assert config_path.read_text().endswith("\n")


def test_already_approved_leaves_file_untouched(project, config_path, claude_on_path):
    config_path.write_text(
        json.dumps({"projects": {_key(project): {APPROVAL_FLAG: True}}})
    )
    os.utime(config_path, ns=(1_000_000_000, 1_000_000_000))
    before_bytes = config_path.read_bytes()
    before_mtime = config_path.stat().st_mtime_ns

    result = ensure_claude_approval(project)

    assert result.status is ApprovalStatus.ALREADY_APPROVED
    assert result.ok
    assert config_path.read_bytes() == before_bytes
    assert config_path.stat().st_mtime_ns == before_mtime


def test_missing_config_is_reported_and_not_created(
    project, config_path, claude_on_path
):
    result = ensure_claude_approval(project)

    assert result.status is ApprovalStatus.CONFIG_MISSING
    assert not result.ok
    assert not config_path.exists()


def test_missing_config_without_claude_is_skipped(project, config_path, claude_absent):
    result = ensure_claude_approval(project)

    assert result.status is ApprovalStatus.CLAUDE_NOT_INSTALLED
    assert result.ok
    assert not config_path.exists()


@pytest.mark.parametrize(
    "text",
    [
        "{not json",
        "[]",
        '{"projects": []}',
        '{"projects": {"KEY": 5}}',
    ],
    ids=["invalid-json", "top-level-list", "projects-not-dict", "entry-not-dict"],
)
def test_malformed_config_is_reported_and_left_unchanged(
    project, config_path, claude_on_path, text
):
    config_path.write_text(text.replace("KEY", _key(project)))
    before = config_path.read_bytes()

    result = ensure_claude_approval(project)

    assert result.status is ApprovalStatus.CONFIG_MALFORMED
    assert not result.ok
    assert config_path.read_bytes() == before


@pytest.mark.parametrize(
    "agents_md",
    [None, "# Project\n@AGENTS.md-other\nNo imports here\n"],
    ids=["no-agents-md", "no-beacon-imports"],
)
def test_no_wired_contexts_is_not_needed_and_nothing_is_touched(
    tmp_path, config_path, claude_on_path, agents_md
):
    root = tmp_path / "project"
    root.mkdir()
    if agents_md is not None:
        (root / "AGENTS.md").write_text(agents_md)
    config_path.write_text('{"projects": {}}')
    before = config_path.read_bytes()

    result = ensure_claude_approval(root)

    assert result.status is ApprovalStatus.NOT_NEEDED
    assert config_path.read_bytes() == before


def test_symlinked_config_is_written_through(project, config_path, claude_on_path):
    real = config_path.parent / "real-claude.json"
    real.write_text('{"projects": {}}')
    config_path.symlink_to(real)

    result = ensure_claude_approval(project)

    assert result.status is ApprovalStatus.APPROVED
    assert config_path.is_symlink()
    data = json.loads(real.read_text())
    assert data["projects"][_key(project)][APPROVAL_FLAG] is True


def test_inspect_never_writes(project, config_path, claude_on_path):
    config_path.write_text('{"projects": {}}')
    before = config_path.read_bytes()

    result = inspect_claude_approval(project)

    assert result.status is ApprovalStatus.NOT_APPROVED
    assert not result.ok
    assert config_path.read_bytes() == before
