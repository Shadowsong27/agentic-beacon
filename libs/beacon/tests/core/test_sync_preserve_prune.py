"""Tests for SyncEngine --preserve, --prune, and verbose flags.

Following TDD workflow for tasks 6.6-6.8.
"""

import pytest
from pathlib import Path
from beacon.core.sync import SyncEngine, SyncSummary


# ========== Task 6.6: --preserve flag ==========


def test_preserve_skips_modified_local(valid_warehouse, temp_dir):
    """TC: preserve=True → Modified local file not overwritten."""
    artifacts_dir = temp_dir / "artifacts"
    (artifacts_dir / "knowledge").mkdir(parents=True)

    # Create warehouse version
    (valid_warehouse / "knowledge" / "doc.md").write_text("warehouse version")
    # Create different local version
    (artifacts_dir / "knowledge" / "doc.md").write_text("local modified version")

    engine = SyncEngine(valid_warehouse, artifacts_dir)
    result = engine.copy_file("knowledge/doc.md", preserve=True)

    assert result.success
    assert result.action == "preserved"
    # Local content should be unchanged
    assert (artifacts_dir / "knowledge" / "doc.md").read_text() == "local modified version"


def test_preserve_copies_new_files(valid_warehouse, temp_dir):
    """TC: preserve=True → New files still copied."""
    artifacts_dir = temp_dir / "artifacts"
    artifacts_dir.mkdir()

    (valid_warehouse / "knowledge" / "new.md").write_text("new content")

    engine = SyncEngine(valid_warehouse, artifacts_dir)
    result = engine.copy_file("knowledge/new.md", preserve=True)

    assert result.success
    assert result.action == "copied"


def test_preserve_skips_identical(valid_warehouse, temp_dir):
    """TC: preserve=True → Identical files still skipped."""
    artifacts_dir = temp_dir / "artifacts"
    (artifacts_dir / "knowledge").mkdir(parents=True)

    (valid_warehouse / "knowledge" / "doc.md").write_text("same content")
    (artifacts_dir / "knowledge" / "doc.md").write_text("same content")

    engine = SyncEngine(valid_warehouse, artifacts_dir)
    result = engine.copy_file("knowledge/doc.md", preserve=True)

    assert result.success
    assert result.action == "skipped"


# ========== Task 6.7: --prune flag ==========


def test_prune_removes_unlisted_artifacts(valid_warehouse, temp_dir):
    """TC: prune=True → Artifacts not in list are removed."""
    artifacts_dir = temp_dir / "artifacts"
    (artifacts_dir / "knowledge").mkdir(parents=True)

    # Create files in artifacts dir
    (valid_warehouse / "knowledge" / "keep.md").write_text("keep")
    (artifacts_dir / "knowledge" / "keep.md").write_text("keep")
    (artifacts_dir / "knowledge" / "remove-me.md").write_text("should be removed")

    engine = SyncEngine(valid_warehouse, artifacts_dir)
    summary = engine.sync_all(
        artifact_paths=["knowledge/keep.md"],
        prune=True,
    )

    assert summary.pruned == 1
    assert (artifacts_dir / "knowledge" / "keep.md").exists()
    assert not (artifacts_dir / "knowledge" / "remove-me.md").exists()


def test_prune_false_keeps_extra_files(valid_warehouse, temp_dir):
    """TC: prune=False → Extra files in artifacts/ remain."""
    artifacts_dir = temp_dir / "artifacts"
    (artifacts_dir / "knowledge").mkdir(parents=True)

    (valid_warehouse / "knowledge" / "listed.md").write_text("listed")
    (artifacts_dir / "knowledge" / "listed.md").write_text("listed")
    (artifacts_dir / "knowledge" / "extra.md").write_text("extra file")

    engine = SyncEngine(valid_warehouse, artifacts_dir)
    summary = engine.sync_all(
        artifact_paths=["knowledge/listed.md"],
        prune=False,
    )

    assert summary.pruned == 0
    assert (artifacts_dir / "knowledge" / "extra.md").exists()


def test_prune_cleans_empty_dirs(valid_warehouse, temp_dir):
    """TC: prune removes empty directories after cleanup."""
    artifacts_dir = temp_dir / "artifacts"
    (artifacts_dir / "knowledge" / "subdir").mkdir(parents=True)

    (valid_warehouse / "knowledge" / "keep.md").write_text("keep")
    (artifacts_dir / "knowledge" / "keep.md").write_text("keep")
    (artifacts_dir / "knowledge" / "subdir" / "orphan.md").write_text("orphan")

    engine = SyncEngine(valid_warehouse, artifacts_dir)
    engine.sync_all(
        artifact_paths=["knowledge/keep.md"],
        prune=True,
    )

    assert not (artifacts_dir / "knowledge" / "subdir").exists()


# ========== Task 6.8: Verbose Logging ==========


def test_verbose_logs_operations(valid_warehouse, temp_dir):
    """TC: verbose=True → Detailed log messages generated."""
    artifacts_dir = temp_dir / "artifacts"
    artifacts_dir.mkdir()

    (valid_warehouse / "knowledge" / "doc.md").write_text("content")

    engine = SyncEngine(valid_warehouse, artifacts_dir)
    log_messages = []
    summary = engine.sync_all(
        artifact_paths=["knowledge/doc.md"],
        verbose=True,
        log_fn=lambda msg: log_messages.append(msg),
    )

    assert len(log_messages) > 0
    assert any("Syncing" in msg or "Copied" in msg for msg in log_messages)


def test_verbose_false_minimal_logs(valid_warehouse, temp_dir):
    """TC: verbose=False → Minimal log messages."""
    artifacts_dir = temp_dir / "artifacts"
    artifacts_dir.mkdir()

    (valid_warehouse / "knowledge" / "doc.md").write_text("content")

    engine = SyncEngine(valid_warehouse, artifacts_dir)
    summary = engine.sync_all(
        artifact_paths=["knowledge/doc.md"],
        verbose=False,
    )

    # Only error messages in log
    assert all("Error" in msg for msg in summary.log_messages) or len(summary.log_messages) == 0


# ========== sync_all Summary ==========


def test_sync_all_counts(valid_warehouse, temp_dir):
    """sync_all returns correct counts in summary."""
    artifacts_dir = temp_dir / "artifacts"
    (artifacts_dir / "knowledge").mkdir(parents=True)

    # New file (will be copied)
    (valid_warehouse / "knowledge" / "new.md").write_text("new")

    # Identical file (will be skipped)
    (valid_warehouse / "knowledge" / "same.md").write_text("same")
    (artifacts_dir / "knowledge" / "same.md").write_text("same")

    # Missing source (will error)
    # knowledge/missing.md doesn't exist in warehouse

    engine = SyncEngine(valid_warehouse, artifacts_dir)
    summary = engine.sync_all(
        artifact_paths=["knowledge/new.md", "knowledge/same.md", "knowledge/missing.md"],
    )

    assert summary.copied == 1
    assert summary.skipped == 1
    assert summary.errors == 1
