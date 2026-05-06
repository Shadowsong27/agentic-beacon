"""Tests for discover_candidates() — pending.yaml + warehouse-diff merge.

Covers tasks 4.1–4.4:
- TC1: pending-only, no warehouse changes
- TC2: warehouse-only, no pending
- TC3: both empty
- TC4: .last-adopt absent → all warehouse files are candidates
- TC5: existing discover_adoptable still works (regression)
- Dedup TCs: same path → pending.yaml metadata wins
- Annotation TCs: warehouse-only → source='warehouse-modified'
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from beacon.core.manifest.pending import PendingEntry, PendingManifest
from beacon.domains.adoption.discovery import discover_candidates
from beacon.domains.adoption.last_adopt import write_last_adopt


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────


def _git_init(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=path, check=True, capture_output=True,
    )


def _git_commit(warehouse: Path, message: str = "add files") -> None:
    subprocess.run(["git", "add", "-A"], cwd=warehouse, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=warehouse, check=True, capture_output=True,
    )


def _make_warehouse(tmp_path: Path) -> Path:
    """Create a minimal git-initialized warehouse."""
    wh = tmp_path / "warehouse"
    wh.mkdir()
    _git_init(wh)
    (wh / "contexts").mkdir()
    (wh / "skills").mkdir()
    (wh / "knowledge").mkdir()
    (wh / ".gitkeep").write_text("")
    _git_commit(wh, "initial")
    return wh


def _make_project(tmp_path: Path) -> Path:
    """Create a minimal project root with .agentic-beacon/."""
    project = tmp_path / "project"
    project.mkdir()
    (project / ".agentic-beacon").mkdir()
    return project


def _pending_entry(
    path: str,
    entry_type: str = "knowledge",
    action: str = "created",
    source: str = "record-knowledge",
) -> PendingEntry:
    return PendingEntry(
        path=path,
        type=entry_type,  # type: ignore[arg-type]
        action=action,  # type: ignore[arg-type]
        source=source,
        created_at=datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc),
    )


def _write_pending(project: Path, entries: list[PendingEntry]) -> None:
    manifest = PendingManifest(pending=entries)
    manifest.to_yaml(project / ".agentic-beacon" / "pending.yaml")


# ─────────────────────────────────────────────────────────────
# Task 4.1: Merge two sources
# ─────────────────────────────────────────────────────────────


def test_tc1_pending_only_no_warehouse_changes(tmp_path):
    """TC1: pending.yaml has 2 entries, no warehouse changes → returns 2 candidates."""
    wh = _make_warehouse(tmp_path)
    project = _make_project(tmp_path)

    # Set .last-adopt to AFTER the last warehouse commit (no new changes)
    write_last_adopt(project, datetime.now(tz=timezone.utc))

    entries = [
        _pending_entry("knowledge/lessons/foo.md"),
        _pending_entry("skills/bar/", entry_type="skill"),
    ]
    _write_pending(project, entries)

    candidates = discover_candidates(project, wh)

    assert len(candidates) == 2
    paths = {c.path for c in candidates}
    assert "knowledge/lessons/foo.md" in paths
    assert "skills/bar/" in paths


def test_tc2_warehouse_only_no_pending(tmp_path):
    """TC2: pending.yaml empty, warehouse has 1 modified file post-.last-adopt → 1 candidate."""
    wh = _make_warehouse(tmp_path)
    project = _make_project(tmp_path)

    # Set .last-adopt BEFORE adding the new file
    write_last_adopt(project, datetime(2020, 1, 1, tzinfo=timezone.utc))

    # Add a file to warehouse AFTER .last-adopt
    ctx_file = wh / "contexts" / "python-standards.md"
    ctx_file.write_text("# Python Standards\n")
    _git_commit(wh, "add context file")

    candidates = discover_candidates(project, wh)

    assert len(candidates) == 1
    assert candidates[0].path == "contexts/python-standards.md"
    assert candidates[0].source == "warehouse-modified"


def test_tc3_both_empty(tmp_path):
    """TC3: Both pending.yaml empty and no warehouse changes → returns []."""
    wh = _make_warehouse(tmp_path)
    project = _make_project(tmp_path)

    # Set .last-adopt to now (no new warehouse changes expected)
    write_last_adopt(project, datetime.now(tz=timezone.utc))
    _write_pending(project, [])

    candidates = discover_candidates(project, wh)

    assert candidates == []


def test_tc4_last_adopt_absent_returns_all_warehouse_files(tmp_path):
    """TC4: .last-adopt absent → all warehouse tracked files are candidates."""
    wh = _make_warehouse(tmp_path)
    project = _make_project(tmp_path)

    # Add a context and a knowledge file
    (wh / "contexts" / "agent-practices.md").write_text("# Agent Practices\n")
    (wh / "knowledge" / "lesson.md").write_text("# Lesson\n")
    _git_commit(wh, "add files")

    # No .last-adopt and no pending.yaml
    candidates = discover_candidates(project, wh)

    paths = {c.path for c in candidates}
    assert "contexts/agent-practices.md" in paths
    assert "knowledge/lesson.md" in paths


def test_tc5_existing_discover_adoptable_regression(tmp_path):
    """TC5: existing discover_adoptable still works (regression check)."""
    from beacon.core.manifest.beacon import BeaconManifest
    from beacon.domains.adoption.discovery import discover_adoptable

    wh = _make_warehouse(tmp_path)
    (wh / "contexts" / "cicd-flow.md").write_text("# CICD Flow\n")
    _git_commit(wh, "add context")

    beacon = BeaconManifest()
    candidates, _ = discover_adoptable(wh, beacon)

    paths = {c.path for c in candidates}
    assert "contexts/cicd-flow.md" in paths


# ─────────────────────────────────────────────────────────────
# Task 4.2: Dedup by path — pending.yaml wins
# ─────────────────────────────────────────────────────────────


def test_dedup_same_path_pending_metadata_wins(tmp_path):
    """TC1 for 4.2: Same path in both sources → 1 row, source=pending's source."""
    wh = _make_warehouse(tmp_path)
    project = _make_project(tmp_path)

    # .last-adopt BEFORE commit so warehouse diff also picks up the file
    write_last_adopt(project, datetime(2020, 1, 1, tzinfo=timezone.utc))

    # Commit the file to warehouse
    (wh / "knowledge" / "foo.md").write_text("# Foo\n")
    _git_commit(wh, "add foo.md")

    # Pending.yaml also has this path with a distinct source
    _write_pending(project, [
        _pending_entry("knowledge/foo.md", source="record-knowledge"),
    ])

    candidates = discover_candidates(project, wh)

    foo_candidates = [c for c in candidates if c.path == "knowledge/foo.md"]
    assert len(foo_candidates) == 1
    assert foo_candidates[0].source == "record-knowledge"


def test_dedup_pending_action_wins(tmp_path):
    """TC2 for 4.2: Same path, pending action=modified → result action=modified."""
    wh = _make_warehouse(tmp_path)
    project = _make_project(tmp_path)

    write_last_adopt(project, datetime(2020, 1, 1, tzinfo=timezone.utc))

    (wh / "contexts" / "existing.md").write_text("# Existing\n")
    _git_commit(wh, "add existing.md")

    _write_pending(project, [
        _pending_entry("contexts/existing.md", action="modified", source="my-tool"),
    ])

    candidates = discover_candidates(project, wh)

    existing = [c for c in candidates if c.path == "contexts/existing.md"]
    assert len(existing) == 1
    assert existing[0].action == "modified"
    assert existing[0].source == "my-tool"


def test_no_dedup_different_paths(tmp_path):
    """TC3 for 4.2: Different paths in both sources → 2 rows."""
    wh = _make_warehouse(tmp_path)
    project = _make_project(tmp_path)

    write_last_adopt(project, datetime(2020, 1, 1, tzinfo=timezone.utc))

    (wh / "contexts" / "new-context.md").write_text("# New Context\n")
    _git_commit(wh, "add context")

    _write_pending(project, [
        _pending_entry("knowledge/lesson.md"),
    ])

    candidates = discover_candidates(project, wh)

    assert len(candidates) == 2
    paths = {c.path for c in candidates}
    assert "knowledge/lesson.md" in paths
    assert "contexts/new-context.md" in paths


def test_duplicate_pending_entries_last_write_wins(tmp_path):
    """TC4 for 4.2: Two pending entries with same path → last-write-wins."""
    wh = _make_warehouse(tmp_path)
    project = _make_project(tmp_path)
    write_last_adopt(project, datetime.now(tz=timezone.utc))

    _write_pending(project, [
        _pending_entry("knowledge/foo.md", source="first-tool"),
        _pending_entry("knowledge/foo.md", source="second-tool"),
    ])

    candidates = discover_candidates(project, wh)

    foo_candidates = [c for c in candidates if c.path == "knowledge/foo.md"]
    assert len(foo_candidates) == 1
    # last entry wins
    assert foo_candidates[0].source == "second-tool"


# ─────────────────────────────────────────────────────────────
# Task 4.3: Warehouse-diff-only annotation
# ─────────────────────────────────────────────────────────────


def test_warehouse_only_source_annotation(tmp_path):
    """TC1 for 4.3: Warehouse-only candidate → source='warehouse-modified'."""
    wh = _make_warehouse(tmp_path)
    project = _make_project(tmp_path)

    write_last_adopt(project, datetime(2020, 1, 1, tzinfo=timezone.utc))

    (wh / "contexts" / "cicd.md").write_text("# CICD\n")
    _git_commit(wh, "add cicd.md")

    candidates = discover_candidates(project, wh)

    cicd = [c for c in candidates if c.path == "contexts/cicd.md"]
    assert len(cicd) == 1
    assert cicd[0].source == "warehouse-modified"


def test_pending_yaml_not_written_during_discover(tmp_path):
    """TC2 for 4.3: pending.yaml byte-equal pre/post discover (no write-back)."""
    wh = _make_warehouse(tmp_path)
    project = _make_project(tmp_path)

    write_last_adopt(project, datetime(2020, 1, 1, tzinfo=timezone.utc))
    (wh / "contexts" / "foo.md").write_text("# Foo\n")
    _git_commit(wh, "add foo.md")

    pending_path = project / ".agentic-beacon" / "pending.yaml"
    _write_pending(project, [_pending_entry("knowledge/lesson.md")])
    original_content = pending_path.read_bytes()

    discover_candidates(project, wh)

    assert pending_path.read_bytes() == original_content


def test_mixed_sources_only_warehouse_only_annotated(tmp_path):
    """TC3 for 4.3: Mixed sources → only warehouse-only rows get the annotation."""
    wh = _make_warehouse(tmp_path)
    project = _make_project(tmp_path)

    write_last_adopt(project, datetime(2020, 1, 1, tzinfo=timezone.utc))

    (wh / "contexts" / "cicd.md").write_text("# CICD\n")
    _git_commit(wh, "add cicd.md")

    # pending.yaml entry for a DIFFERENT path
    _write_pending(project, [
        _pending_entry("knowledge/lesson.md", source="record-knowledge"),
    ])

    candidates = discover_candidates(project, wh)

    pending_entry = next(c for c in candidates if c.path == "knowledge/lesson.md")
    warehouse_entry = next(c for c in candidates if c.path == "contexts/cicd.md")

    assert pending_entry.source == "record-knowledge"  # NOT warehouse-modified
    assert warehouse_entry.source == "warehouse-modified"
