"""Integration tests for commit_pending_session + rollback.

Covers tasks 6.5 and 6.6:
- test_happy_path: 2 accept / 1 reject / 1 defer → all 4 invariants hold
- test_rollback_on_symlink_failure: injected failure → files restored
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
# Fixtures / helpers
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
        ["git", "config", "user.name", "Test"],
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


@pytest.fixture()
def warehouse(tmp_path: Path) -> Path:
    wh = tmp_path / "warehouse"
    wh.mkdir()
    _git_init(wh)
    for d in ["contexts", "skills", "knowledge"]:
        (wh / d).mkdir()
    (wh / "contexts" / "ctx-a.md").write_text("# Ctx A\n")
    (wh / "contexts" / "ctx-b.md").write_text("# Ctx B\n")
    (wh / "contexts" / "ctx-c.md").write_text("# Ctx C\n")
    (wh / "knowledge" / "k.md").write_text("# Knowledge\n")
    _git_commit(wh, "initial warehouse")
    return wh


@pytest.fixture()
def project(tmp_path: Path, warehouse: Path) -> dict:
    """Create a fixture project. Returns a dict of important paths."""
    p = tmp_path / "project"
    p.mkdir()
    ab = p / ".agentic-beacon"
    ab.mkdir()
    artifacts = ab / "artifacts"
    artifacts.mkdir()

    beacon_yaml = ab / "beacon.yaml"
    beacon_yaml.write_text("artifacts:\n  contexts: []\n  skills: []\n  agents: []\n")

    write_last_adopt(p, datetime(2026, 5, 1, tzinfo=UTC))

    # Pending with 4 entries
    entries = [
        PendingEntry(
            path="contexts/ctx-a.md",
            type="context",
            action="created",
            source="record-knowledge",
            created_at=datetime(2026, 5, 6, 12, 0, 0, tzinfo=UTC),
        ),
        PendingEntry(
            path="contexts/ctx-b.md",
            type="context",
            action="created",
            source="record-knowledge",
            created_at=datetime(2026, 5, 6, 12, 0, 0, tzinfo=UTC),
        ),
        PendingEntry(
            path="contexts/ctx-reject.md",
            type="context",
            action="created",
            source="record-knowledge",
            created_at=datetime(2026, 5, 6, 12, 0, 0, tzinfo=UTC),
        ),
        PendingEntry(
            path="contexts/ctx-c.md",
            type="context",
            action="created",
            source="record-knowledge",
            created_at=datetime(2026, 5, 6, 12, 0, 0, tzinfo=UTC),
        ),
    ]
    m = PendingManifest(pending=entries)
    m.to_yaml(ab / "pending.yaml")

    return {
        "root": p,
        "ab": ab,
        "beacon_yaml": beacon_yaml,
        "artifacts": artifacts,
        "pending_yaml": ab / "pending.yaml",
        "last_adopt": ab / ".last-adopt",
    }


def _snapshot(paths: dict) -> tuple[bytes, bytes, bytes]:
    return (
        paths["beacon_yaml"].read_bytes(),
        paths["pending_yaml"].read_bytes(),
        paths["last_adopt"].read_bytes(),
    )


# ─────────────────────────────────────────────────────────────
# Task 6.5: Happy path integration test
# ─────────────────────────────────────────────────────────────


def test_happy_path(project: dict, warehouse: Path):
    """6.5: 2 accept / 1 reject / 1 defer → all 4 invariants hold simultaneously."""
    candidates = [
        AdoptCandidate(
            artifact_type="contexts",
            path="contexts/ctx-a.md",
            source="record-knowledge",
        ),
        AdoptCandidate(
            artifact_type="contexts",
            path="contexts/ctx-b.md",
            source="record-knowledge",
        ),
        AdoptCandidate(
            artifact_type="contexts",
            path="contexts/ctx-reject.md",
            source="record-knowledge",
        ),
        AdoptCandidate(
            artifact_type="contexts",
            path="contexts/ctx-c.md",
            source="record-knowledge",
        ),
    ]
    session_state = {
        "contexts/ctx-a.md": "accept",
        "contexts/ctx-b.md": "accept",
        "contexts/ctx-reject.md": "reject",
        "contexts/ctx-c.md": "defer",
    }
    commit_time = datetime(2026, 5, 7, 15, 0, 0, tzinfo=UTC)

    commit_pending_session(
        session_state,
        candidates,
        project["root"],
        warehouse,
        project["artifacts"],
        project["beacon_yaml"],
        commit_time=commit_time,
    )

    # Invariant 1: beacon.yaml has 2 accepted contexts
    with open(project["beacon_yaml"]) as f:
        data = yaml.safe_load(f)
    assert "contexts/ctx-a.md" in data["artifacts"]["contexts"]
    assert "contexts/ctx-b.md" in data["artifacts"]["contexts"]
    assert "contexts/ctx-c.md" not in data["artifacts"]["contexts"]

    # Invariant 2: Symlinks for accepted entries
    assert (project["artifacts"] / "contexts" / "ctx-a.md").exists()
    assert (project["artifacts"] / "contexts" / "ctx-b.md").exists()
    assert not (project["artifacts"] / "contexts" / "ctx-c.md").exists()

    # Invariant 3: pending.yaml has only the deferred entry
    manifest = PendingManifest.from_yaml(project["pending_yaml"])
    remaining = [e.path for e in manifest.pending]
    assert remaining == ["contexts/ctx-c.md"]

    # Invariant 4: .last-adopt set to commit timestamp
    assert read_last_adopt(project["root"]) == commit_time

    assert "contexts/ctx-reject.md" not in data["artifacts"]["contexts"]


# ─────────────────────────────────────────────────────────────
# Task 6.6: Rollback on symlink failure
# ─────────────────────────────────────────────────────────────


def test_rollback_on_symlink_failure(project: dict, warehouse: Path):
    """6.6: Injected symlink failure mid-commit → all 3 files restored, error identifies entry."""
    pre = _snapshot(project)

    candidates = [
        AdoptCandidate(artifact_type="contexts", path="contexts/ctx-a.md"),
        AdoptCandidate(artifact_type="contexts", path="contexts/ctx-b.md"),
        AdoptCandidate(artifact_type="contexts", path="contexts/ctx-c.md"),
    ]
    session_state = {
        "contexts/ctx-a.md": "accept",
        "contexts/ctx-b.md": "accept",
        "contexts/ctx-c.md": "accept",
    }

    call_count = [0]

    def _failing_on_second(artifact_paths: list[str], **kwargs):
        call_count[0] += 1
        if call_count[0] == 2:
            raise RuntimeError("injected failure on ctx-b.md")

    with pytest.raises(CommitError) as exc_info:
        commit_pending_session(
            session_state,
            candidates,
            project["root"],
            warehouse,
            project["artifacts"],
            project["beacon_yaml"],
            _symlink_sync_fn=_failing_on_second,
        )

    # All 3 files restored
    post = _snapshot(project)
    assert pre == post, "All three files must be byte-identical after rollback"

    # Error message identifies the failing entry
    assert "ctx-b.md" in str(exc_info.value)
