"""Tests for DeltaComparator - artifact comparison between local and warehouse.

Following TDD workflow for tasks 8.1-8.6:
- Task 8.1: DeltaComparator class creation
- Task 8.2: Hash-based comparison
- Task 8.4: Beacon.yaml-aware comparison
- Task 8.5: Git diff integration
- Task 8.6: Color output support
"""

import os
import pytest
from pathlib import Path
from beacon.core.delta import DeltaComparator, DeltaStatus, ComparisonResult, DeltaSummary


# ========== Task 8.1: DeltaComparator Class Creation ==========


def test_comparator_instantiates_with_valid_paths(valid_warehouse, temp_dir):
    """TC1: Both paths valid → Class instantiates successfully."""
    artifacts_dir = temp_dir / "artifacts"
    artifacts_dir.mkdir()
    comparator = DeltaComparator(valid_warehouse, artifacts_dir)
    assert comparator.warehouse_path == valid_warehouse.resolve()
    assert comparator.artifacts_path == artifacts_dir.resolve()


def test_comparator_invalid_warehouse_path(temp_dir):
    """TC2: Warehouse path invalid → Raises ValueError."""
    artifacts_dir = temp_dir / "artifacts"
    artifacts_dir.mkdir()
    with pytest.raises(ValueError, match="not a valid directory"):
        DeltaComparator(temp_dir / "nonexistent", artifacts_dir)


def test_comparator_empty_artifacts_returns_empty(valid_warehouse, temp_dir):
    """TC4: Empty artifacts directory → Returns empty results list."""
    artifacts_dir = temp_dir / "artifacts"
    artifacts_dir.mkdir()
    comparator = DeltaComparator(valid_warehouse, artifacts_dir)
    summary = comparator.compare_all()
    assert len(summary.results) == 0


def test_comparator_compare_all_returns_structured_data(valid_warehouse, temp_dir):
    """TC6: compare_all() returns structured data → Each result has path, status, hashes."""
    artifacts_dir = temp_dir / "artifacts"
    artifacts_dir.mkdir()

    # Create matching file in both locations
    (valid_warehouse / "knowledge" / "test.md").write_text("content")
    (artifacts_dir / "knowledge").mkdir(parents=True)
    (artifacts_dir / "knowledge" / "test.md").write_text("content")

    comparator = DeltaComparator(valid_warehouse, artifacts_dir)
    summary = comparator.compare_all()

    assert len(summary.results) == 1
    result = summary.results[0]
    assert isinstance(result, ComparisonResult)
    assert result.path == "knowledge/test.md"
    assert result.status == DeltaStatus.IDENTICAL
    assert result.local_hash is not None
    assert result.warehouse_hash is not None


def test_comparator_multiple_files(valid_warehouse, temp_dir):
    """TC7: Multiple comparisons → Results list contains all artifacts."""
    artifacts_dir = temp_dir / "artifacts"
    (artifacts_dir / "knowledge").mkdir(parents=True)

    for i in range(3):
        (valid_warehouse / "knowledge" / f"file{i}.md").write_text(f"content {i}")
        (artifacts_dir / "knowledge" / f"file{i}.md").write_text(f"content {i}")

    comparator = DeltaComparator(valid_warehouse, artifacts_dir)
    summary = comparator.compare_all()
    assert len(summary.results) == 3


def test_comparator_idempotent(valid_warehouse, temp_dir):
    """TC10: Call compare_all() multiple times → Consistent results."""
    artifacts_dir = temp_dir / "artifacts"
    (artifacts_dir / "knowledge").mkdir(parents=True)
    (valid_warehouse / "knowledge" / "test.md").write_text("content")
    (artifacts_dir / "knowledge" / "test.md").write_text("content")

    comparator = DeltaComparator(valid_warehouse, artifacts_dir)
    summary1 = comparator.compare_all()
    summary2 = comparator.compare_all()
    assert len(summary1.results) == len(summary2.results)
    assert summary1.results[0].status == summary2.results[0].status


# ========== Task 8.2: Hash-based Comparison ==========


def test_hash_same_content(valid_warehouse, temp_dir):
    """TC1: Same content → Identical hashes."""
    file1 = temp_dir / "file1.md"
    file2 = temp_dir / "file2.md"
    file1.write_text("identical content")
    file2.write_text("identical content")

    artifacts_dir = temp_dir / "artifacts"
    artifacts_dir.mkdir()
    comparator = DeltaComparator(valid_warehouse, artifacts_dir)
    assert comparator.compute_hash(file1) == comparator.compute_hash(file2)


def test_hash_different_content(valid_warehouse, temp_dir):
    """TC2: Different content → Different hashes."""
    file1 = temp_dir / "file1.md"
    file2 = temp_dir / "file2.md"
    file1.write_text("content A")
    file2.write_text("content B")

    artifacts_dir = temp_dir / "artifacts"
    artifacts_dir.mkdir()
    comparator = DeltaComparator(valid_warehouse, artifacts_dir)
    assert comparator.compute_hash(file1) != comparator.compute_hash(file2)


def test_hash_empty_file(valid_warehouse, temp_dir):
    """TC6: Empty file → Returns valid hash."""
    empty_file = temp_dir / "empty.md"
    empty_file.write_text("")

    artifacts_dir = temp_dir / "artifacts"
    artifacts_dir.mkdir()
    comparator = DeltaComparator(valid_warehouse, artifacts_dir)
    hash_value = comparator.compute_hash(empty_file)
    assert isinstance(hash_value, str)
    assert len(hash_value) == 64  # SHA256 hex digest


def test_hash_unicode_file(valid_warehouse, temp_dir):
    """TC7: File with Unicode characters → Handles correctly."""
    unicode_file = temp_dir / "unicode.md"
    unicode_file.write_text("Hello 世界 🌍 мир", encoding="utf-8")

    artifacts_dir = temp_dir / "artifacts"
    artifacts_dir.mkdir()
    comparator = DeltaComparator(valid_warehouse, artifacts_dir)
    hash_value = comparator.compute_hash(unicode_file)
    assert isinstance(hash_value, str)
    assert len(hash_value) == 64


def test_hash_file_not_found(valid_warehouse, temp_dir):
    """TC9: File not found → Raises FileNotFoundError."""
    artifacts_dir = temp_dir / "artifacts"
    artifacts_dir.mkdir()
    comparator = DeltaComparator(valid_warehouse, artifacts_dir)
    with pytest.raises(FileNotFoundError):
        comparator.compute_hash(temp_dir / "nonexistent.md")


def test_hash_file_is_directory(valid_warehouse, temp_dir):
    """TC10: File is directory → Raises IsADirectoryError."""
    artifacts_dir = temp_dir / "artifacts"
    artifacts_dir.mkdir()
    comparator = DeltaComparator(valid_warehouse, artifacts_dir)
    with pytest.raises(IsADirectoryError):
        comparator.compute_hash(temp_dir)


def test_hash_is_sha256(valid_warehouse, temp_dir):
    """TC11: Hash algorithm is SHA256 → Verify specific algorithm used."""
    import hashlib
    test_file = temp_dir / "test.md"
    test_file.write_text("test content")

    artifacts_dir = temp_dir / "artifacts"
    artifacts_dir.mkdir()
    comparator = DeltaComparator(valid_warehouse, artifacts_dir)
    computed = comparator.compute_hash(test_file)

    expected = hashlib.sha256(b"test content").hexdigest()
    assert computed == expected


# ========== Compare File Statuses ==========


def test_compare_identical_files(valid_warehouse, temp_dir):
    """Files with same content → IDENTICAL status."""
    artifacts_dir = temp_dir / "artifacts"
    (artifacts_dir / "knowledge").mkdir(parents=True)
    (valid_warehouse / "knowledge" / "doc.md").write_text("same")
    (artifacts_dir / "knowledge" / "doc.md").write_text("same")

    comparator = DeltaComparator(valid_warehouse, artifacts_dir)
    result = comparator.compare_file("knowledge/doc.md")
    assert result.status == DeltaStatus.IDENTICAL


def test_compare_modified_file(valid_warehouse, temp_dir):
    """Files with different content → MODIFIED status."""
    artifacts_dir = temp_dir / "artifacts"
    (artifacts_dir / "knowledge").mkdir(parents=True)
    (valid_warehouse / "knowledge" / "doc.md").write_text("warehouse version")
    (artifacts_dir / "knowledge" / "doc.md").write_text("local version")

    comparator = DeltaComparator(valid_warehouse, artifacts_dir)
    result = comparator.compare_file("knowledge/doc.md")
    assert result.status == DeltaStatus.MODIFIED


def test_compare_missing_local(valid_warehouse, temp_dir):
    """File in warehouse but not local → MISSING status."""
    artifacts_dir = temp_dir / "artifacts"
    artifacts_dir.mkdir()
    (valid_warehouse / "knowledge" / "doc.md").write_text("warehouse only")

    comparator = DeltaComparator(valid_warehouse, artifacts_dir)
    result = comparator.compare_file("knowledge/doc.md")
    assert result.status == DeltaStatus.MISSING


def test_compare_added_local(valid_warehouse, temp_dir):
    """File in local but not warehouse → ADDED status."""
    artifacts_dir = temp_dir / "artifacts"
    (artifacts_dir / "custom").mkdir(parents=True)
    (artifacts_dir / "custom" / "local-only.md").write_text("local only")

    comparator = DeltaComparator(valid_warehouse, artifacts_dir)
    result = comparator.compare_file("custom/local-only.md")
    assert result.status == DeltaStatus.ADDED


# ========== Task 8.4: Beacon.yaml-aware Comparison ==========


def test_compare_from_config_only_listed(valid_warehouse, temp_dir):
    """compare_from_config only compares artifacts in beacon.yaml."""
    from beacon.core.settings import BeaconSettings

    artifacts_dir = temp_dir / "artifacts"
    (artifacts_dir / "knowledge").mkdir(parents=True)
    (valid_warehouse / "knowledge" / "listed.md").write_text("content")
    (artifacts_dir / "knowledge" / "listed.md").write_text("content")
    (artifacts_dir / "knowledge" / "unlisted.md").write_text("extra")

    # Create beacon settings with only listed.md
    beacon_yaml = temp_dir / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge:\n    - knowledge/listed.md\n  skills: []\n  contexts: []\n"
    )
    settings = BeaconSettings.from_yaml(beacon_yaml)

    comparator = DeltaComparator(valid_warehouse, artifacts_dir)
    summary = comparator.compare_from_config(settings)

    # Should only compare listed.md, not unlisted.md
    assert len(summary.results) == 1
    assert summary.results[0].path == "knowledge/listed.md"


# ========== Task 8.5: Git Diff Integration ==========


def test_detailed_diff_returns_string(valid_warehouse, temp_dir):
    """detailed_diff returns diff string for modified file."""
    artifacts_dir = temp_dir / "artifacts"
    (artifacts_dir / "knowledge").mkdir(parents=True)
    (valid_warehouse / "knowledge" / "doc.md").write_text("line 1\nline 2\n")
    (artifacts_dir / "knowledge" / "doc.md").write_text("line 1\nline 2 modified\n")

    comparator = DeltaComparator(valid_warehouse, artifacts_dir)
    diff = comparator.detailed_diff("knowledge/doc.md", color=False)
    assert isinstance(diff, str)
    # Should contain some indication of the change
    assert len(diff) > 0


def test_detailed_diff_missing_local(valid_warehouse, temp_dir):
    """detailed_diff handles missing local file."""
    artifacts_dir = temp_dir / "artifacts"
    artifacts_dir.mkdir()
    (valid_warehouse / "knowledge" / "doc.md").write_text("content")

    comparator = DeltaComparator(valid_warehouse, artifacts_dir)
    diff = comparator.detailed_diff("knowledge/doc.md")
    assert "not found" in diff.lower()


# ========== DeltaSummary Properties ==========


def test_summary_has_differences(valid_warehouse, temp_dir):
    """DeltaSummary.has_differences is True when differences exist."""
    artifacts_dir = temp_dir / "artifacts"
    (artifacts_dir / "knowledge").mkdir(parents=True)
    (valid_warehouse / "knowledge" / "doc.md").write_text("warehouse")
    (artifacts_dir / "knowledge" / "doc.md").write_text("local")

    comparator = DeltaComparator(valid_warehouse, artifacts_dir)
    summary = comparator.compare_all()
    assert summary.has_differences is True


def test_summary_no_differences(valid_warehouse, temp_dir):
    """DeltaSummary.has_differences is False when all identical."""
    artifacts_dir = temp_dir / "artifacts"
    (artifacts_dir / "knowledge").mkdir(parents=True)
    (valid_warehouse / "knowledge" / "doc.md").write_text("same")
    (artifacts_dir / "knowledge" / "doc.md").write_text("same")

    comparator = DeltaComparator(valid_warehouse, artifacts_dir)
    summary = comparator.compare_all()
    assert summary.has_differences is False


def test_summary_filter_properties(valid_warehouse, temp_dir):
    """DeltaSummary filter properties return correct subsets."""
    artifacts_dir = temp_dir / "artifacts"
    (artifacts_dir / "knowledge").mkdir(parents=True)

    # Create various states
    (valid_warehouse / "knowledge" / "same.md").write_text("same")
    (artifacts_dir / "knowledge" / "same.md").write_text("same")

    (valid_warehouse / "knowledge" / "modified.md").write_text("original")
    (artifacts_dir / "knowledge" / "modified.md").write_text("changed")

    (valid_warehouse / "knowledge" / "missing.md").write_text("warehouse only")

    comparator = DeltaComparator(valid_warehouse, artifacts_dir)
    summary = comparator.compare_all(["knowledge/same.md", "knowledge/modified.md", "knowledge/missing.md"])

    assert len(summary.identical) == 1
    assert len(summary.modified) == 1
    assert len(summary.missing) == 1
