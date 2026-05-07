"""Unit tests for commit_pending_session + rollback in apply.py.

Covers task 6.2 (commit) and 6.3 (rollback) TDD test cases.
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from beacon.core.manifest.pending import PendingEntry, PendingManifest
from beacon.domains.adoption.apply import CommitError, commit_pending_session
from beacon.domains.adoption.last_adopt import read_last_adopt, write_last_adopt
from beacon.domains.adoption.models import AdoptCandidate

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────


def _git_init(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=path,
        check=True,
        capture_output=True,
    )


def _git_commit(path: Path, msg: str = "add files") -> None:
    subprocess.run(["git", "add", "-A"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", msg],
        cwd=path,
        check=True,
        capture_output=True,
    )


def _make_warehouse(tmp_path: Path) -> Path:
    wh = tmp_path / "warehouse"
    wh.mkdir()
    _git_init(wh)
    for d in ["contexts", "skills", "knowledge"]:
        (wh / d).mkdir()
    (wh / ".gitkeep").write_text("")
    _git_commit(wh, "initial")
    return wh


def _make_project(tmp_path: Path, wh: Path) -> tuple[Path, Path, Path, Path]:
    """Create project root with beacon.yaml, pending.yaml, .last-adopt.

    Returns (project_root, beacon_yaml, artifacts_path, ab_dir).
    """
    project = tmp_path / "project"
    project.mkdir()
    ab = project / ".agentic-beacon"
    ab.mkdir()
    artifacts = ab / "artifacts"
    artifacts.mkdir()

    beacon_yaml = ab / "beacon.yaml"
    beacon_yaml.write_text("artifacts:\n  contexts: []\n  skills: []\n  agents: []\n")

    pending_yaml = ab / "pending.yaml"
    pending_yaml.write_text("pending: []\n")

    write_last_adopt(project, datetime(2026, 5, 1, tzinfo=UTC))

    return project, beacon_yaml, artifacts, ab


def _pending_entry(
    path: str,
    entry_type: str = "context",
    action: str = "created",
    source: str = "record-knowledge",
) -> PendingEntry:
    return PendingEntry(
        path=path,
        type=entry_type,  # type: ignore[arg-type]
        action=action,  # type: ignore[arg-type]
        source=source,
        created_at=datetime(2026, 5, 6, 12, 0, 0, tzinfo=UTC),
    )


def _write_pending(project: Path, entries: list[PendingEntry]) -> None:
    m = PendingManifest(pending=entries)
    m.to_yaml(project / ".agentic-beacon" / "pending.yaml")


def _candidate(path: str, artifact_type: str = "contexts") -> AdoptCandidate:
    return AdoptCandidate(
        artifact_type=artifact_type, path=path, source="record-knowledge"
    )


# ─────────────────────────────────────────────────────────────
# Task 6.2: Commit transaction invariants
# ─────────────────────────────────────────────────────────────


def test_tc1_accept_only_updates_beacon_and_pending(tmp_path):
    """TC1: 2 accept / 0 reject / 0 defer → beacon.yaml +2, pending empty."""
    wh = _make_warehouse(tmp_path)
    # Add context files to warehouse
    ctx1 = wh / "contexts" / "foo.md"
    ctx2 = wh / "contexts" / "bar.md"
    ctx1.write_text("# Foo\n")
    ctx2.write_text("# Bar\n")
    _git_commit(wh, "add contexts")

    project, beacon_yaml, artifacts, ab = _make_project(tmp_path, wh)

    entries = [
        _pending_entry("contexts/foo.md"),
        _pending_entry("contexts/bar.md"),
    ]
    _write_pending(project, entries)

    candidates = [
        _candidate("contexts/foo.md"),
        _candidate("contexts/bar.md"),
    ]
    session_state = {"contexts/foo.md": "accept", "contexts/bar.md": "accept"}

    commit_pending_session(
        session_state, candidates, project, wh, artifacts, beacon_yaml
    )

    # beacon.yaml should have 2 new entries
    with open(beacon_yaml) as f:
        data = yaml.safe_load(f)
    assert "contexts/foo.md" in data["artifacts"]["contexts"]
    assert "contexts/bar.md" in data["artifacts"]["contexts"]

    # pending.yaml should be empty
    manifest = PendingManifest.from_yaml(ab / "pending.yaml")
    assert manifest.pending == []

    # symlinks should exist
    assert (artifacts / "contexts" / "foo.md").exists()
    assert (artifacts / "contexts" / "bar.md").exists()


def test_tc2_reject_only_clears_pending_warehouse_unchanged(tmp_path):
    """TC2: 0 accept / 2 reject / 0 defer → pending.yaml empty, warehouse unchanged."""
    wh = _make_warehouse(tmp_path)
    warehouse_file = wh / "knowledge" / "lesson.md"
    warehouse_file.write_text("# Lesson\n")
    _git_commit(wh, "add lesson")

    project, beacon_yaml, artifacts, ab = _make_project(tmp_path, wh)

    entries = [
        _pending_entry("contexts/rejected.md"),
        _pending_entry("contexts/foo.md"),
    ]
    _write_pending(project, entries)

    # Pre-capture warehouse file content
    original_content = warehouse_file.read_bytes()

    # Pre-capture beacon.yaml content
    original_beacon = beacon_yaml.read_bytes()

    candidates = [
        _candidate("contexts/rejected.md"),
        _candidate("contexts/foo.md"),
    ]
    session_state = {"contexts/rejected.md": "reject", "contexts/foo.md": "reject"}

    commit_pending_session(
        session_state, candidates, project, wh, artifacts, beacon_yaml
    )

    # pending.yaml should be empty
    manifest = PendingManifest.from_yaml(ab / "pending.yaml")
    assert manifest.pending == []

    # warehouse file unchanged
    assert warehouse_file.read_bytes() == original_content

    # beacon.yaml unchanged
    assert beacon_yaml.read_bytes() == original_beacon


def test_tc3_defer_only_keeps_pending_advances_last_adopt(tmp_path):
    """TC3: 0 accept / 0 reject / 2 defer → pending.yaml unchanged, .last-adopt advanced."""
    wh = _make_warehouse(tmp_path)
    project, beacon_yaml, artifacts, ab = _make_project(tmp_path, wh)

    entries = [
        _pending_entry("contexts/foo.md"),
        _pending_entry("contexts/bar.md"),
    ]
    _write_pending(project, entries)
    original_pending = (ab / "pending.yaml").read_bytes()
    original_beacon = beacon_yaml.read_bytes()

    candidates = [
        _candidate("contexts/foo.md"),
        _candidate("contexts/bar.md"),
    ]
    session_state = {"contexts/foo.md": "defer", "contexts/bar.md": "defer"}

    commit_time = datetime(2026, 5, 7, 10, 0, 0, tzinfo=UTC)
    commit_pending_session(
        session_state,
        candidates,
        project,
        wh,
        artifacts,
        beacon_yaml,
        commit_time=commit_time,
    )

    # pending.yaml unchanged (both deferred)
    assert (ab / "pending.yaml").read_bytes() == original_pending

    # beacon.yaml unchanged
    assert beacon_yaml.read_bytes() == original_beacon

    # .last-adopt advanced
    after_last_adopt = read_last_adopt(project)
    assert after_last_adopt == commit_time


def test_tc4_mixed_2_1_1_all_invariants(tmp_path):
    """TC4: Mixed 2 accept / 1 reject / 1 defer → all invariants."""
    wh = _make_warehouse(tmp_path)
    ctx1 = wh / "contexts" / "ctx-a.md"
    ctx2 = wh / "contexts" / "ctx-b.md"
    ctx1.write_text("# Ctx A\n")
    ctx2.write_text("# Ctx B\n")
    _git_commit(wh, "add contexts")

    project, beacon_yaml, artifacts, ab = _make_project(tmp_path, wh)
    warehouse_knowledge = wh / "knowledge" / "k.md"
    warehouse_knowledge.write_text("# Knowledge\n")
    _git_commit(wh, "add knowledge")
    original_knowledge = warehouse_knowledge.read_bytes()

    entries = [
        _pending_entry("contexts/ctx-a.md"),
        _pending_entry("contexts/ctx-b.md"),
        _pending_entry("contexts/rejected.md"),
        _pending_entry("contexts/ctx-c.md"),
    ]
    _write_pending(project, entries)

    candidates = [
        _candidate("contexts/ctx-a.md"),
        _candidate("contexts/ctx-b.md"),
        _candidate("contexts/rejected.md"),
        _candidate("contexts/ctx-c.md"),
    ]
    session_state = {
        "contexts/ctx-a.md": "accept",
        "contexts/ctx-b.md": "accept",
        "contexts/rejected.md": "reject",
        "contexts/ctx-c.md": "defer",
    }

    commit_time = datetime(2026, 5, 7, 12, 0, 0, tzinfo=UTC)
    commit_pending_session(
        session_state,
        candidates,
        project,
        wh,
        artifacts,
        beacon_yaml,
        commit_time=commit_time,
    )

    # beacon.yaml has the 2 accepted contexts
    with open(beacon_yaml) as f:
        data = yaml.safe_load(f)
    assert "contexts/ctx-a.md" in data["artifacts"]["contexts"]
    assert "contexts/ctx-b.md" in data["artifacts"]["contexts"]

    # Symlinks for accepted entries
    assert (artifacts / "contexts" / "ctx-a.md").exists()
    assert (artifacts / "contexts" / "ctx-b.md").exists()

    # pending.yaml has only the deferred entry
    manifest = PendingManifest.from_yaml(ab / "pending.yaml")
    remaining_paths = [e.path for e in manifest.pending]
    assert remaining_paths == ["contexts/ctx-c.md"]

    # .last-adopt advanced
    assert read_last_adopt(project) == commit_time

    # Warehouse file for rejected entry unchanged
    assert warehouse_knowledge.read_bytes() == original_knowledge


def test_accepted_contexts_and_skills_trigger_post_sync_wiring(tmp_path):
    """Accepted beacon artifacts run the post-sync wiring hook before commit completes."""
    wh = _make_warehouse(tmp_path)
    (wh / "contexts" / "ctx.md").write_text("# Context\n")
    skill_dir = wh / "skills" / "helper"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\ndescription: Helper\n---\n")
    _git_commit(wh, "add context and skill")

    project, beacon_yaml, artifacts, ab = _make_project(tmp_path, wh)
    entries = [
        _pending_entry("contexts/ctx.md"),
        _pending_entry("skills/helper/", entry_type="skill"),
    ]
    _write_pending(project, entries)

    wired_paths: list[str] = []

    def _record_wiring(accepted: list[AdoptCandidate]) -> None:
        wired_paths.extend(c.path for c in accepted)

    commit_pending_session(
        {"contexts/ctx.md": "accept", "skills/helper/": "accept"},
        [
            _candidate("contexts/ctx.md"),
            _candidate("skills/helper/", artifact_type="skills"),
        ],
        project,
        wh,
        artifacts,
        beacon_yaml,
        _post_sync_wiring_fn=_record_wiring,
    )

    assert wired_paths == ["contexts/ctx.md", "skills/helper/"]


def test_tc6_last_adopt_advances_only_on_success(tmp_path):
    """TC6: .last-adopt advances ONLY on successful commit, never on partial state."""
    wh = _make_warehouse(tmp_path)
    project, beacon_yaml, artifacts, ab = _make_project(tmp_path, wh)

    original_last_adopt = read_last_adopt(project)
    entries = [_pending_entry("contexts/foo.md")]
    _write_pending(project, entries)

    candidates = [_candidate("contexts/foo.md")]
    session_state = {"contexts/foo.md": "accept"}

    def _failing_sync(*args, **kwargs):
        raise RuntimeError("forced sync failure")

    with pytest.raises(CommitError):
        commit_pending_session(
            session_state,
            candidates,
            project,
            wh,
            artifacts,
            beacon_yaml,
            _symlink_sync_fn=_failing_sync,
        )

    # .last-adopt must NOT have advanced
    assert read_last_adopt(project) == original_last_adopt


# ─────────────────────────────────────────────────────────────
# Task 6.3: Rollback on failure
# ─────────────────────────────────────────────────────────────


def _snapshot(project: Path, beacon_yaml: Path, ab: Path) -> tuple[bytes, bytes, bytes]:
    """Snapshot byte-content of the three tracked files."""
    pending_path = ab / "pending.yaml"
    last_adopt_path = ab / ".last-adopt"
    return (
        beacon_yaml.read_bytes() if beacon_yaml.exists() else b"",
        pending_path.read_bytes() if pending_path.exists() else b"",
        last_adopt_path.read_bytes() if last_adopt_path.exists() else b"",
    )


def test_tc1_symlink_failure_on_second_entry_rolls_back(tmp_path):
    """TC1: Symlink failure on entry 2 of 3 → raise + 3 files restored."""
    wh = _make_warehouse(tmp_path)
    for name in ["a.md", "b.md", "c.md"]:
        (wh / "contexts" / name).write_text(f"# {name}\n")
    _git_commit(wh, "add contexts")

    project, beacon_yaml, artifacts, ab = _make_project(tmp_path, wh)
    entries = [
        _pending_entry("contexts/a.md"),
        _pending_entry("contexts/b.md"),
        _pending_entry("contexts/c.md"),
    ]
    _write_pending(project, entries)

    pre = _snapshot(project, beacon_yaml, ab)

    candidates = [
        _candidate("contexts/a.md"),
        _candidate("contexts/b.md"),
        _candidate("contexts/c.md"),
    ]
    session_state = {
        "contexts/a.md": "accept",
        "contexts/b.md": "accept",
        "contexts/c.md": "accept",
    }

    call_count = [0]

    def _failing_on_second(artifact_paths, **kwargs):
        call_count[0] += 1
        if call_count[0] == 2:
            raise RuntimeError("injected sync failure on b.md")

    with pytest.raises(CommitError):
        commit_pending_session(
            session_state,
            candidates,
            project,
            wh,
            artifacts,
            beacon_yaml,
            _symlink_sync_fn=_failing_on_second,
        )

    post = _snapshot(project, beacon_yaml, ab)
    assert pre == post, "All three files must be restored after rollback"


def test_tc4_error_message_includes_failing_entry_path(tmp_path):
    """TC4: Error message includes the failing entry's path."""
    wh = _make_warehouse(tmp_path)
    (wh / "contexts" / "tricky.md").write_text("# Tricky\n")
    _git_commit(wh, "add tricky")

    project, beacon_yaml, artifacts, ab = _make_project(tmp_path, wh)
    _write_pending(project, [_pending_entry("contexts/tricky.md")])

    candidates = [_candidate("contexts/tricky.md")]
    session_state = {"contexts/tricky.md": "accept"}

    def _fail(*args, **kwargs):
        raise RuntimeError("forced failure")

    with pytest.raises(CommitError) as exc_info:
        commit_pending_session(
            session_state,
            candidates,
            project,
            wh,
            artifacts,
            beacon_yaml,
            _symlink_sync_fn=_fail,
        )

    assert "contexts/tricky.md" in str(exc_info.value)
