"""Tests for SyncEngine - snapshot-based artifact syncing.

Following TDD workflow for tasks 6.1-6.8:
- Task 6.1: SyncEngine class creation
- Task 6.2: Pure copy sync (no symlinks)
- Task 6.3: Glob pattern expansion
- Task 6.4: Directory structure preservation
- Task 6.5: Idempotent sync logic
- Task 6.6-6.8: Flags (--preserve, --prune, --verbose)
"""
import pytest
import os
import hashlib
from pathlib import Path
from beacon.core.sync import SyncEngine


# ========== Task 6.1 & 6.2: SyncEngine Creation and Pure Copy ==========


def test_sync_engine_copies_single_file(valid_warehouse, temp_dir):
    """TC1: Copy single file → File exists in artifacts/, is regular file not symlink."""
    project_dir = temp_dir / "project"
    project_dir.mkdir()
    artifacts_dir = project_dir / ".agentic-beacon" / "artifacts"
    
    # Create test file in warehouse
    test_file = valid_warehouse / "knowledge" / "test.md"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("# Test content")
    
    engine = SyncEngine(
        warehouse_path=valid_warehouse,
        artifacts_path=artifacts_dir
    )
    
    result = engine.copy_file("knowledge/test.md")
    
    assert result.success
    copied_file = artifacts_dir / "knowledge" / "test.md"
    assert copied_file.exists()
    assert copied_file.is_file()
    assert not os.path.islink(copied_file)  # Must be regular file, not symlink
    assert copied_file.read_text() == "# Test content"


def test_sync_engine_preserves_directory_structure(valid_warehouse, temp_dir):
    """TC2: Copy with nested directories → Directory structure preserved exactly."""
    project_dir = temp_dir / "project"
    project_dir.mkdir()
    artifacts_dir = project_dir / ".agentic-beacon" / "artifacts"
    
    # Create nested file in warehouse
    nested_file = valid_warehouse / "knowledge" / "languages" / "python" / "types.md"
    nested_file.parent.mkdir(parents=True, exist_ok=True)
    nested_file.write_text("# Python types")
    
    engine = SyncEngine(
        warehouse_path=valid_warehouse,
        artifacts_path=artifacts_dir
    )
    
    result = engine.copy_file("knowledge/languages/python/types.md")
    
    assert result.success
    copied_file = artifacts_dir / "knowledge" / "languages" / "python" / "types.md"
    assert copied_file.exists()
    assert copied_file.read_text() == "# Python types"


def test_sync_engine_overwrites_existing_file(valid_warehouse, temp_dir):
    """TC3: Copy overwrites existing file → Existing file replaced with warehouse version."""
    project_dir = temp_dir / "project"
    project_dir.mkdir()
    artifacts_dir = project_dir / ".agentic-beacon" / "artifacts"
    
    # Create file in both warehouse and artifacts
    warehouse_file = valid_warehouse / "knowledge" / "doc.md"
    warehouse_file.parent.mkdir(parents=True, exist_ok=True)
    warehouse_file.write_text("# Warehouse version")
    
    local_file = artifacts_dir / "knowledge" / "doc.md"
    local_file.parent.mkdir(parents=True, exist_ok=True)
    local_file.write_text("# Old version")
    
    engine = SyncEngine(
        warehouse_path=valid_warehouse,
        artifacts_path=artifacts_dir
    )
    
    result = engine.copy_file("knowledge/doc.md")
    
    assert result.success
    assert local_file.read_text() == "# Warehouse version"


def test_sync_engine_no_symlinks_created(valid_warehouse, temp_dir):
    """TC12: Verify no symlinks created → All files are regular copies."""
    project_dir = temp_dir / "project"
    project_dir.mkdir()
    artifacts_dir = project_dir / ".agentic-beacon" / "artifacts"
    
    # Create multiple files
    for i in range(3):
        test_file = valid_warehouse / "knowledge" / f"file{i}.md"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text(f"Content {i}")
    
    engine = SyncEngine(
        warehouse_path=valid_warehouse,
        artifacts_path=artifacts_dir
    )
    
    for i in range(3):
        engine.copy_file(f"knowledge/file{i}.md")
    
    # Verify none are symlinks
    for i in range(3):
        copied = artifacts_dir / "knowledge" / f"file{i}.md"
        assert not os.path.islink(copied)


# ========== Task 6.3: Glob Pattern Expansion ==========


def test_expand_glob_with_double_star(valid_warehouse):
    """TC1: Pattern with ** → Returns all matching files recursively."""
    # Create nested structure
    (valid_warehouse / "knowledge" / "python").mkdir(parents=True, exist_ok=True)
    (valid_warehouse / "knowledge" / "python" / "file1.md").write_text("test")
    (valid_warehouse / "knowledge" / "python" / "sub").mkdir(exist_ok=True)
    (valid_warehouse / "knowledge" / "python" / "sub" / "file2.md").write_text("test")
    
    engine = SyncEngine(warehouse_path=valid_warehouse, artifacts_path=Path("/tmp"))
    
    matches = engine.expand_glob("knowledge/python/**/*.md")
    
    assert len(matches) == 2
    assert any("file1.md" in str(m) for m in matches)
    assert any("file2.md" in str(m) for m in matches)


def test_expand_glob_with_single_star(valid_warehouse):
    """TC2: Pattern with * → Returns files matching in single directory."""
    (valid_warehouse / "knowledge").mkdir(parents=True, exist_ok=True)
    (valid_warehouse / "knowledge" / "file1.md").write_text("test")
    (valid_warehouse / "knowledge" / "file2.md").write_text("test")
    (valid_warehouse / "knowledge" / "sub").mkdir(exist_ok=True)
    (valid_warehouse / "knowledge" / "sub" / "file3.md").write_text("test")
    
    engine = SyncEngine(warehouse_path=valid_warehouse, artifacts_path=Path("/tmp"))
    
    matches = engine.expand_glob("knowledge/*.md")
    
    assert len(matches) == 2  # Only top-level files, not subdirectory
    assert all("sub" not in str(m) for m in matches)


def test_expand_glob_no_matches(valid_warehouse):
    """TC4: Pattern matching no files → Returns empty list, no error."""
    engine = SyncEngine(warehouse_path=valid_warehouse, artifacts_path=Path("/tmp"))
    
    matches = engine.expand_glob("knowledge/nonexistent/**/*.md")
    
    assert matches == []


def test_expand_glob_only_returns_files(valid_warehouse):
    """TC9: Pattern matches directories → Returns only files, not directories."""
    (valid_warehouse / "knowledge" / "dir1").mkdir(parents=True, exist_ok=True)
    (valid_warehouse / "knowledge" / "dir1" / "file.md").write_text("test")
    (valid_warehouse / "knowledge" / "dir2").mkdir(exist_ok=True)
    
    engine = SyncEngine(warehouse_path=valid_warehouse, artifacts_path=Path("/tmp"))
    
    matches = engine.expand_glob("knowledge/**/*.md")
    
    # Should only return file, not directories
    assert len(matches) == 1
    # Convert back to full paths to check they're files
    assert all((valid_warehouse / m).is_file() for m in matches)


# ========== Task 6.5: Idempotent Sync Logic ==========


def test_sync_skips_unchanged_files(valid_warehouse, temp_dir):
    """TC: Second sync with no changes → Files not copied again (idempotent)."""
    project_dir = temp_dir / "project"
    project_dir.mkdir()
    artifacts_dir = project_dir / ".agentic-beacon" / "artifacts"
    
    # Create test file
    test_file = valid_warehouse / "knowledge" / "doc.md"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("# Content")
    
    engine = SyncEngine(
        warehouse_path=valid_warehouse,
        artifacts_path=artifacts_dir
    )
    
    # First sync
    result1 = engine.copy_file("knowledge/doc.md")
    assert result1.success
    assert result1.action == "copied"
    
    # Get modification time
    copied_file = artifacts_dir / "knowledge" / "doc.md"
    mtime1 = copied_file.stat().st_mtime
    
    # Second sync - should detect no changes
    result2 = engine.copy_file("knowledge/doc.md")
    assert result2.success
    assert result2.action == "skipped"  # File unchanged
    
    # File should not have been re-copied
    mtime2 = copied_file.stat().st_mtime
    assert mtime2 == mtime1
