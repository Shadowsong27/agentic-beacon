"""Unit tests for commit_session() — atomic commit across warehouse + pending flows."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from beacon.core.manifest.pending import PendingEntry, PendingManifest
from beacon.domains.adoption.apply import CommitError, commit_session
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
    for d in ["contexts", "skills", "agents", "knowledge"]:
        (wh / d).mkdir()
    (wh / ".gitkeep").write_text("")
    _git_commit(wh, "initial")
    return wh


def _make_project(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    """Create a project root with empty beacon.yaml + pending.yaml.

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

    return project, beacon_yaml, artifacts, ab


def _pending_entry(
    path: str,
    entry_type: str = "context",
    source: str = "record-knowledge",
) -> PendingEntry:
    return PendingEntry(
        path=path,
        type=entry_type,  # type: ignore[arg-type]
        action="created",
        source=source,
        created_at=datetime(2026, 5, 6, 12, 0, 0, tzinfo=UTC),
    )


def _write_pending(project: Path, entries: list[PendingEntry]) -> None:
    PendingManifest(pending=entries).to_yaml(
        project / ".agentic-beacon" / "pending.yaml"
    )


def _candidate(path: str, artifact_type: str = "contexts") -> AdoptCandidate:
    return AdoptCandidate(artifact_type=artifact_type, path=path)


def _read_beacon_artifacts(beacon_yaml: Path) -> dict:
    raw = yaml.safe_load(beacon_yaml.read_text())
    return raw.get("artifacts", {})


def _noop_sync(*args, **kwargs) -> None:
    """Sync that does nothing — used for unit tests that don't exercise symlinks."""
    return


def _noop_post_sync(*args, **kwargs) -> None:
    return


# ─────────────────────────────────────────────────────────────
# Pending TODO flow
# ─────────────────────────────────────────────────────────────


def test_pending_accept_adds_to_beacon_and_removes_from_pending(tmp_path):
    wh = _make_warehouse(tmp_path)
    (wh / "contexts" / "foo.md").write_text("# Foo\n")
    _git_commit(wh, "add foo")

    project, beacon_yaml, artifacts, ab = _make_project(tmp_path)
    pending_entries = [_pending_entry("contexts/foo.md", "context")]
    _write_pending(project, pending_entries)

    commit_session(
        to_adopt=[],
        to_unadopt=[],
        pending_accept=["contexts/foo.md"],
        pending_reject=[],
        candidates=[],
        pending_entries=pending_entries,
        project_root=project,
        warehouse_path=wh,
        artifacts_path=artifacts,
        beacon_yaml_path=beacon_yaml,
        _symlink_sync_fn=_noop_sync,
        _post_sync_wiring_fn=_noop_post_sync,
    )

    artifacts_data = _read_beacon_artifacts(beacon_yaml)
    assert "contexts/foo.md" in artifacts_data["contexts"]

    final_pending = PendingManifest.from_yaml(ab / "pending.yaml")
    assert final_pending.pending == []


def test_pending_reject_removes_from_pending_only(tmp_path):
    wh = _make_warehouse(tmp_path)
    project, beacon_yaml, artifacts, ab = _make_project(tmp_path)
    pending_entries = [_pending_entry("contexts/foo.md", "context")]
    _write_pending(project, pending_entries)

    commit_session(
        to_adopt=[],
        to_unadopt=[],
        pending_accept=[],
        pending_reject=["contexts/foo.md"],
        candidates=[],
        pending_entries=pending_entries,
        project_root=project,
        warehouse_path=wh,
        artifacts_path=artifacts,
        beacon_yaml_path=beacon_yaml,
        _symlink_sync_fn=_noop_sync,
        _post_sync_wiring_fn=_noop_post_sync,
    )

    artifacts_data = _read_beacon_artifacts(beacon_yaml)
    assert "contexts/foo.md" not in artifacts_data["contexts"]

    final_pending = PendingManifest.from_yaml(ab / "pending.yaml")
    assert final_pending.pending == []


def test_pending_defer_keeps_entry_in_pending(tmp_path):
    wh = _make_warehouse(tmp_path)
    project, beacon_yaml, artifacts, ab = _make_project(tmp_path)
    pending_entries = [
        _pending_entry("contexts/foo.md", "context"),
        _pending_entry("contexts/bar.md", "context"),
    ]
    _write_pending(project, pending_entries)

    commit_session(
        to_adopt=[],
        to_unadopt=[],
        pending_accept=["contexts/foo.md"],  # only foo accepted
        pending_reject=[],
        candidates=[],
        pending_entries=pending_entries,
        project_root=project,
        warehouse_path=wh,
        artifacts_path=artifacts,
        beacon_yaml_path=beacon_yaml,
        _symlink_sync_fn=_noop_sync,
        _post_sync_wiring_fn=_noop_post_sync,
    )

    final_pending = PendingManifest.from_yaml(ab / "pending.yaml")
    paths = {e.path for e in final_pending.pending}
    assert paths == {"contexts/bar.md"}  # bar deferred, stays


# ─────────────────────────────────────────────────────────────
# Warehouse browser flow
# ─────────────────────────────────────────────────────────────


def test_to_adopt_adds_paths_to_beacon(tmp_path):
    wh = _make_warehouse(tmp_path)
    project, beacon_yaml, artifacts, ab = _make_project(tmp_path)

    commit_session(
        to_adopt=["contexts/cicd.md"],
        to_unadopt=[],
        pending_accept=[],
        pending_reject=[],
        candidates=[_candidate("contexts/cicd.md", "contexts")],
        pending_entries=[],
        project_root=project,
        warehouse_path=wh,
        artifacts_path=artifacts,
        beacon_yaml_path=beacon_yaml,
        _symlink_sync_fn=_noop_sync,
        _post_sync_wiring_fn=_noop_post_sync,
    )

    artifacts_data = _read_beacon_artifacts(beacon_yaml)
    assert "contexts/cicd.md" in artifacts_data["contexts"]


def test_to_unadopt_removes_paths_from_beacon(tmp_path):
    wh = _make_warehouse(tmp_path)
    project, beacon_yaml, artifacts, ab = _make_project(tmp_path)
    beacon_yaml.write_text(
        "artifacts:\n  contexts:\n  - contexts/old.md\n  skills: []\n  agents: []\n"
    )

    commit_session(
        to_adopt=[],
        to_unadopt=["contexts/old.md"],
        pending_accept=[],
        pending_reject=[],
        candidates=[],
        pending_entries=[],
        project_root=project,
        warehouse_path=wh,
        artifacts_path=artifacts,
        beacon_yaml_path=beacon_yaml,
        _symlink_sync_fn=_noop_sync,
        _post_sync_wiring_fn=_noop_post_sync,
    )

    artifacts_data = _read_beacon_artifacts(beacon_yaml)
    assert "contexts/old.md" not in artifacts_data["contexts"]


# ─────────────────────────────────────────────────────────────
# Mixed flows
# ─────────────────────────────────────────────────────────────


def test_mixed_flows_apply_atomically(tmp_path):
    """Warehouse adopt + pending accept + pending reject in one commit."""
    wh = _make_warehouse(tmp_path)
    (wh / "contexts" / "from-pending.md").write_text("# pending\n")
    (wh / "contexts" / "from-warehouse.md").write_text("# warehouse\n")
    _git_commit(wh, "add files")

    project, beacon_yaml, artifacts, ab = _make_project(tmp_path)

    pending_entries = [
        _pending_entry("contexts/from-pending.md", "context"),
        _pending_entry("contexts/to-reject.md", "context"),
    ]
    _write_pending(project, pending_entries)

    commit_session(
        to_adopt=["contexts/from-warehouse.md"],
        to_unadopt=[],
        pending_accept=["contexts/from-pending.md"],
        pending_reject=["contexts/to-reject.md"],
        candidates=[_candidate("contexts/from-warehouse.md", "contexts")],
        pending_entries=pending_entries,
        project_root=project,
        warehouse_path=wh,
        artifacts_path=artifacts,
        beacon_yaml_path=beacon_yaml,
        _symlink_sync_fn=_noop_sync,
        _post_sync_wiring_fn=_noop_post_sync,
    )

    artifacts_data = _read_beacon_artifacts(beacon_yaml)
    assert "contexts/from-warehouse.md" in artifacts_data["contexts"]
    assert "contexts/from-pending.md" in artifacts_data["contexts"]
    # Rejected pending never goes to beacon.yaml
    assert "contexts/to-reject.md" not in artifacts_data["contexts"]

    # Both pending entries are removed (one accepted, one rejected)
    final_pending = PendingManifest.from_yaml(ab / "pending.yaml")
    assert final_pending.pending == []


# ─────────────────────────────────────────────────────────────
# Rollback
# ─────────────────────────────────────────────────────────────


def test_sync_failure_triggers_rollback(tmp_path):
    """If symlink sync fails, both beacon.yaml and pending.yaml restore to pre state."""
    wh = _make_warehouse(tmp_path)
    project, beacon_yaml, artifacts, ab = _make_project(tmp_path)
    pending_yaml = ab / "pending.yaml"

    pending_entries = [_pending_entry("contexts/foo.md", "context")]
    _write_pending(project, pending_entries)

    pre_beacon = beacon_yaml.read_bytes()
    pre_pending = pending_yaml.read_bytes()

    def _failing_sync(*args, **kwargs) -> None:
        raise RuntimeError("simulated sync error")

    with pytest.raises(CommitError):
        commit_session(
            to_adopt=[],
            to_unadopt=[],
            pending_accept=["contexts/foo.md"],
            pending_reject=[],
            candidates=[],
            pending_entries=pending_entries,
            project_root=project,
            warehouse_path=wh,
            artifacts_path=artifacts,
            beacon_yaml_path=beacon_yaml,
            _symlink_sync_fn=_failing_sync,
            _post_sync_wiring_fn=_noop_post_sync,
        )

    assert beacon_yaml.read_bytes() == pre_beacon
    assert pending_yaml.read_bytes() == pre_pending
