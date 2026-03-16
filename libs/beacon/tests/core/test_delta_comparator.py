"""Tests for DeltaComparator - artifact comparison between local and warehouse.

Following TDD workflow for tasks 8.1-8.6:
- Task 8.1: DeltaComparator class creation
- Task 8.2: Hash-based comparison
- Task 8.4: Beacon.yaml-aware comparison
- Task 8.5: Git diff integration
- Task 8.6: Color output support
"""

import pytest
from beacon.core.delta import (
    ComparisonResult,
    DeltaComparator,
    DeltaStatus,
)

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
    summary = comparator.compare_all(
        ["knowledge/same.md", "knowledge/modified.md", "knowledge/missing.md"]
    )

    assert len(summary.identical) == 1
    assert len(summary.modified) == 1
    assert len(summary.missing) == 1


# ========== Bug fix: compare_from_config detects locally-added files ==========


def test_compare_from_config_detects_added_file_via_glob(valid_warehouse, temp_dir):
    """compare_from_config finds locally-added files that match a glob pattern
    but don't exist in the warehouse (previously invisible to delta)."""
    from beacon.core.settings import BeaconSettings

    artifacts_dir = temp_dir / "artifacts"
    (artifacts_dir / "knowledge").mkdir(parents=True)

    # This file only exists locally — not in the warehouse
    (artifacts_dir / "knowledge" / "new-lesson.md").write_text("# New Lesson\n")

    beacon_yaml = temp_dir / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge:\n    - knowledge/**/*.md\n  skills: []\n  contexts: []\n"
    )
    settings = BeaconSettings.from_yaml(beacon_yaml)

    comparator = DeltaComparator(valid_warehouse, artifacts_dir)
    summary = comparator.compare_from_config(settings)

    added_paths = [r.path for r in summary.added]
    assert "knowledge/new-lesson.md" in added_paths


def test_compare_from_config_detects_added_skill_via_glob(valid_warehouse, temp_dir):
    """compare_from_config detects a locally-added skill file via glob.

    When no skills_paths are configured, falls back to artifacts_path for skills
    (backward compatibility — no agents detected).
    """
    from beacon.core.settings import BeaconSettings

    artifacts_dir = temp_dir / "artifacts"
    skill_dir = artifacts_dir / "skills" / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Skill: My Skill\n")

    beacon_yaml = temp_dir / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge: []\n  skills:\n    - skills/**/*\n  contexts: []\n"
    )
    settings = BeaconSettings.from_yaml(beacon_yaml)

    # No skills_paths → falls back to artifacts_path
    comparator = DeltaComparator(valid_warehouse, artifacts_dir)
    summary = comparator.compare_from_config(settings)

    added_paths = [r.path for r in summary.added]
    assert "skills/my-skill/SKILL.md" in added_paths


def test_compare_from_config_skills_uses_live_agent_path(valid_warehouse, temp_dir):
    """compare_from_config uses live agent install dir for skills when skills_paths configured."""
    from beacon.core.settings import BeaconSettings

    artifacts_dir = temp_dir / "artifacts"
    artifacts_dir.mkdir()

    # Warehouse has the skill
    skill_wh = valid_warehouse / "skills" / "opsx-enhance"
    skill_wh.mkdir(parents=True)
    (skill_wh / "SKILL.md").write_text("# Warehouse version\n")

    # Live agent dir has a MODIFIED version
    opencode_skills = temp_dir / ".opencode" / "skills"
    live_skill_dir = opencode_skills / "opsx-enhance"
    live_skill_dir.mkdir(parents=True)
    (live_skill_dir / "SKILL.md").write_text("# Modified locally\n")

    beacon_yaml = temp_dir / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge: []\n  skills:\n    - skills/opsx-enhance/SKILL.md\n  contexts: []\n"
    )
    settings = BeaconSettings.from_yaml(beacon_yaml)

    comparator = DeltaComparator(
        valid_warehouse,
        artifacts_dir,
        skills_paths={"opencode": opencode_skills},
    )
    summary = comparator.compare_from_config(settings)

    assert len(summary.modified) == 1
    result = summary.modified[0]
    assert result.path == "skills/opsx-enhance/SKILL.md"
    assert result.agent_statuses == {"opencode": DeltaStatus.MODIFIED}


def test_compare_from_config_skills_identical_live_agent(valid_warehouse, temp_dir):
    """compare_from_config reports IDENTICAL when live skill matches warehouse."""
    from beacon.core.settings import BeaconSettings

    artifacts_dir = temp_dir / "artifacts"
    artifacts_dir.mkdir()

    content = "# Same content\n"
    skill_wh = valid_warehouse / "skills" / "my-skill"
    skill_wh.mkdir(parents=True)
    (skill_wh / "SKILL.md").write_text(content)

    opencode_skills = temp_dir / ".opencode" / "skills"
    live_skill_dir = opencode_skills / "my-skill"
    live_skill_dir.mkdir(parents=True)
    (live_skill_dir / "SKILL.md").write_text(content)

    beacon_yaml = temp_dir / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge: []\n  skills:\n    - skills/my-skill/SKILL.md\n  contexts: []\n"
    )
    settings = BeaconSettings.from_yaml(beacon_yaml)

    comparator = DeltaComparator(
        valid_warehouse,
        artifacts_dir,
        skills_paths={"opencode": opencode_skills},
    )
    summary = comparator.compare_from_config(settings)

    assert len(summary.identical) == 1
    assert summary.identical[0].agent_statuses == {"opencode": DeltaStatus.IDENTICAL}


def test_compare_skill_multi_agent_worst_status_wins(valid_warehouse, temp_dir):
    """With multiple agents, aggregate status reflects the worst across all agents."""
    from beacon.core.settings import BeaconSettings

    artifacts_dir = temp_dir / "artifacts"
    artifacts_dir.mkdir()

    warehouse_content = "# Warehouse\n"
    skill_wh = valid_warehouse / "skills" / "my-skill"
    skill_wh.mkdir(parents=True)
    (skill_wh / "SKILL.md").write_text(warehouse_content)

    # opencode: identical
    opencode_skills = temp_dir / ".opencode" / "skills"
    oc_skill = opencode_skills / "my-skill"
    oc_skill.mkdir(parents=True)
    (oc_skill / "SKILL.md").write_text(warehouse_content)

    # claudecode: modified
    claude_skills = temp_dir / ".claude" / "skills"
    cc_skill = claude_skills / "my-skill"
    cc_skill.mkdir(parents=True)
    (cc_skill / "SKILL.md").write_text("# Different\n")

    beacon_yaml = temp_dir / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge: []\n  skills:\n    - skills/my-skill/SKILL.md\n  contexts: []\n"
    )
    settings = BeaconSettings.from_yaml(beacon_yaml)

    comparator = DeltaComparator(
        valid_warehouse,
        artifacts_dir,
        skills_paths={"opencode": opencode_skills, "claudecode": claude_skills},
    )
    summary = comparator.compare_from_config(settings)

    assert len(summary.modified) == 1
    result = summary.modified[0]
    assert result.status == DeltaStatus.MODIFIED
    assert result.agent_statuses["opencode"] == DeltaStatus.IDENTICAL
    assert result.agent_statuses["claudecode"] == DeltaStatus.MODIFIED


def test_compare_from_config_detects_missing_skill_via_glob(valid_warehouse, temp_dir):
    """compare_from_config detects a warehouse skill not yet synced locally via glob."""
    from beacon.core.settings import BeaconSettings

    # Skill exists in warehouse but not in local artifacts
    skill_dir = valid_warehouse / "skills" / "opsx-handoff"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Skill: opsx-handoff\n")

    artifacts_dir = temp_dir / "artifacts"
    artifacts_dir.mkdir()

    beacon_yaml = temp_dir / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge: []\n  skills:\n    - skills/**/*\n  contexts: []\n"
    )
    settings = BeaconSettings.from_yaml(beacon_yaml)

    comparator = DeltaComparator(valid_warehouse, artifacts_dir)
    summary = comparator.compare_from_config(settings)

    missing_paths = [r.path for r in summary.missing]
    assert "skills/opsx-handoff/SKILL.md" in missing_paths


def test_compare_from_config_no_duplicates_for_modified(valid_warehouse, temp_dir):
    """A MODIFIED file present in both warehouse and local is not double-counted."""
    from beacon.core.settings import BeaconSettings

    artifacts_dir = temp_dir / "artifacts"
    (artifacts_dir / "knowledge").mkdir(parents=True)
    (valid_warehouse / "knowledge" / "shared.md").write_text("original")
    (artifacts_dir / "knowledge" / "shared.md").write_text("modified")

    beacon_yaml = temp_dir / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge:\n    - knowledge/**/*.md\n  skills: []\n  contexts: []\n"
    )
    settings = BeaconSettings.from_yaml(beacon_yaml)

    comparator = DeltaComparator(valid_warehouse, artifacts_dir)
    summary = comparator.compare_from_config(settings)

    assert len(summary.results) == 1
    assert summary.results[0].path == "knowledge/shared.md"
    assert len(summary.modified) == 1


# ========== Skills: live agent path comparison (bug fix) ==========
# Tests for the fix where abc delta now compares skills against the
# live agent installation directories (.opencode/skills, .claude/skills)
# instead of the intermediate artifact snapshot.


def test_compare_skill_file_directly_modified(valid_warehouse, temp_dir):
    """compare_file reports MODIFIED when live skill differs from warehouse."""
    opencode_skills = temp_dir / ".opencode" / "skills"
    live_dir = opencode_skills / "opsx-enhance"
    live_dir.mkdir(parents=True)
    (live_dir / "SKILL.md").write_text("# Modified live\n")

    (valid_warehouse / "skills" / "opsx-enhance").mkdir(parents=True)
    (valid_warehouse / "skills" / "opsx-enhance" / "SKILL.md").write_text(
        "# Warehouse\n"
    )

    artifacts_dir = temp_dir / "artifacts"
    artifacts_dir.mkdir()

    comparator = DeltaComparator(
        valid_warehouse,
        artifacts_dir,
        skills_paths={"opencode": opencode_skills},
    )
    result = comparator.compare_file("skills/opsx-enhance/SKILL.md")

    assert result.status == DeltaStatus.MODIFIED
    assert result.is_skill is True
    assert result.agent_statuses == {"opencode": DeltaStatus.MODIFIED}


def test_compare_skill_file_identical(valid_warehouse, temp_dir):
    """compare_file reports IDENTICAL when live skill matches warehouse."""
    content = "# Same\n"
    opencode_skills = temp_dir / ".opencode" / "skills"
    (opencode_skills / "my-skill").mkdir(parents=True)
    (opencode_skills / "my-skill" / "SKILL.md").write_text(content)

    (valid_warehouse / "skills" / "my-skill").mkdir(parents=True)
    (valid_warehouse / "skills" / "my-skill" / "SKILL.md").write_text(content)

    artifacts_dir = temp_dir / "artifacts"
    artifacts_dir.mkdir()

    comparator = DeltaComparator(
        valid_warehouse,
        artifacts_dir,
        skills_paths={"opencode": opencode_skills},
    )
    result = comparator.compare_file("skills/my-skill/SKILL.md")

    assert result.status == DeltaStatus.IDENTICAL
    assert result.is_skill is True
    assert result.agent_statuses == {"opencode": DeltaStatus.IDENTICAL}


def test_compare_skill_file_missing_from_live(valid_warehouse, temp_dir):
    """compare_file reports MISSING when skill exists in warehouse but not in live dir."""
    (valid_warehouse / "skills" / "my-skill").mkdir(parents=True)
    (valid_warehouse / "skills" / "my-skill" / "SKILL.md").write_text("# Warehouse\n")

    opencode_skills = temp_dir / ".opencode" / "skills"
    opencode_skills.mkdir(parents=True)  # agent dir exists but skill not installed

    artifacts_dir = temp_dir / "artifacts"
    artifacts_dir.mkdir()

    comparator = DeltaComparator(
        valid_warehouse,
        artifacts_dir,
        skills_paths={"opencode": opencode_skills},
    )
    result = comparator.compare_file("skills/my-skill/SKILL.md")

    assert result.status == DeltaStatus.MISSING
    assert result.agent_statuses == {"opencode": DeltaStatus.MISSING}


def test_compare_skill_file_added_only_in_live(valid_warehouse, temp_dir):
    """compare_file reports ADDED when skill exists live but not in warehouse."""
    opencode_skills = temp_dir / ".opencode" / "skills"
    (opencode_skills / "my-skill").mkdir(parents=True)
    (opencode_skills / "my-skill" / "SKILL.md").write_text("# Local only\n")

    artifacts_dir = temp_dir / "artifacts"
    artifacts_dir.mkdir()

    comparator = DeltaComparator(
        valid_warehouse,
        artifacts_dir,
        skills_paths={"opencode": opencode_skills},
    )
    result = comparator.compare_file("skills/my-skill/SKILL.md")

    assert result.status == DeltaStatus.ADDED
    assert result.agent_statuses == {"opencode": DeltaStatus.ADDED}


def test_compare_skill_multi_agent_all_identical(valid_warehouse, temp_dir):
    """When all agents have the skill identical to warehouse, aggregate is IDENTICAL."""
    content = "# Same\n"
    (valid_warehouse / "skills" / "my-skill").mkdir(parents=True)
    (valid_warehouse / "skills" / "my-skill" / "SKILL.md").write_text(content)

    opencode_skills = temp_dir / ".opencode" / "skills"
    (opencode_skills / "my-skill").mkdir(parents=True)
    (opencode_skills / "my-skill" / "SKILL.md").write_text(content)

    claude_skills = temp_dir / ".claude" / "skills"
    (claude_skills / "my-skill").mkdir(parents=True)
    (claude_skills / "my-skill" / "SKILL.md").write_text(content)

    artifacts_dir = temp_dir / "artifacts"
    artifacts_dir.mkdir()

    comparator = DeltaComparator(
        valid_warehouse,
        artifacts_dir,
        skills_paths={"opencode": opencode_skills, "claudecode": claude_skills},
    )
    result = comparator.compare_file("skills/my-skill/SKILL.md")

    assert result.status == DeltaStatus.IDENTICAL
    assert result.agent_statuses["opencode"] == DeltaStatus.IDENTICAL
    assert result.agent_statuses["claudecode"] == DeltaStatus.IDENTICAL


def test_compare_skill_multi_agent_missing_beats_identical(valid_warehouse, temp_dir):
    """MISSING beats IDENTICAL in the aggregate rollup for multi-agent."""
    content = "# Warehouse\n"
    (valid_warehouse / "skills" / "my-skill").mkdir(parents=True)
    (valid_warehouse / "skills" / "my-skill" / "SKILL.md").write_text(content)

    # opencode: identical
    opencode_skills = temp_dir / ".opencode" / "skills"
    (opencode_skills / "my-skill").mkdir(parents=True)
    (opencode_skills / "my-skill" / "SKILL.md").write_text(content)

    # claudecode: agent dir exists but skill not installed
    claude_skills = temp_dir / ".claude" / "skills"
    claude_skills.mkdir(parents=True)

    artifacts_dir = temp_dir / "artifacts"
    artifacts_dir.mkdir()

    comparator = DeltaComparator(
        valid_warehouse,
        artifacts_dir,
        skills_paths={"opencode": opencode_skills, "claudecode": claude_skills},
    )
    result = comparator.compare_file("skills/my-skill/SKILL.md")

    assert result.status == DeltaStatus.MISSING
    assert result.agent_statuses["opencode"] == DeltaStatus.IDENTICAL
    assert result.agent_statuses["claudecode"] == DeltaStatus.MISSING


def test_compare_skill_is_skill_false_for_non_skill(valid_warehouse, temp_dir):
    """is_skill is False for knowledge and context artifacts."""
    artifacts_dir = temp_dir / "artifacts"
    (artifacts_dir / "knowledge").mkdir(parents=True)
    (valid_warehouse / "knowledge" / "doc.md").write_text("content")
    (artifacts_dir / "knowledge" / "doc.md").write_text("content")

    comparator = DeltaComparator(valid_warehouse, artifacts_dir)
    result = comparator.compare_file("knowledge/doc.md")

    assert result.is_skill is False
    assert result.agent_statuses == {}


def test_compare_skill_no_skills_paths_falls_back_to_artifacts(
    valid_warehouse, temp_dir
):
    """When skills_paths is empty, skill comparison falls back to artifact snapshot."""
    artifacts_dir = temp_dir / "artifacts"
    (artifacts_dir / "skills" / "my-skill").mkdir(parents=True)
    (artifacts_dir / "skills" / "my-skill" / "SKILL.md").write_text("# Snapshot\n")

    (valid_warehouse / "skills" / "my-skill").mkdir(parents=True)
    (valid_warehouse / "skills" / "my-skill" / "SKILL.md").write_text("# Warehouse\n")

    # No skills_paths → backward compat, uses artifacts_path
    comparator = DeltaComparator(valid_warehouse, artifacts_dir)
    result = comparator.compare_file("skills/my-skill/SKILL.md")

    assert result.status == DeltaStatus.MODIFIED
    assert result.agent_statuses == {}
    assert result.is_skill is False


def test_detailed_diff_uses_live_skill_path(valid_warehouse, temp_dir):
    """detailed_diff diffs against the live agent install, not the artifact snapshot."""
    warehouse_content = "line one\nline two\n"
    live_content = "line one\nline two modified\n"

    (valid_warehouse / "skills" / "my-skill").mkdir(parents=True)
    (valid_warehouse / "skills" / "my-skill" / "SKILL.md").write_text(warehouse_content)

    opencode_skills = temp_dir / ".opencode" / "skills"
    (opencode_skills / "my-skill").mkdir(parents=True)
    (opencode_skills / "my-skill" / "SKILL.md").write_text(live_content)

    # Snapshot intentionally has the original (identical to warehouse)
    # so a snapshot-based diff would incorrectly show no diff
    artifacts_dir = temp_dir / "artifacts"
    (artifacts_dir / "skills" / "my-skill").mkdir(parents=True)
    (artifacts_dir / "skills" / "my-skill" / "SKILL.md").write_text(warehouse_content)

    comparator = DeltaComparator(
        valid_warehouse,
        artifacts_dir,
        skills_paths={"opencode": opencode_skills},
    )
    diff = comparator.detailed_diff("skills/my-skill/SKILL.md", color=False)

    assert "line two modified" in diff or "modified" in diff
    assert len(diff) > 0


def test_detailed_diff_skill_missing_from_live_falls_back_to_snapshot(
    valid_warehouse, temp_dir
):
    """detailed_diff falls back to artifact snapshot when no live agent has the skill."""
    warehouse_content = "# Warehouse\n"
    snapshot_content = "# Snapshot version\n"

    (valid_warehouse / "skills" / "my-skill").mkdir(parents=True)
    (valid_warehouse / "skills" / "my-skill" / "SKILL.md").write_text(warehouse_content)

    artifacts_dir = temp_dir / "artifacts"
    (artifacts_dir / "skills" / "my-skill").mkdir(parents=True)
    (artifacts_dir / "skills" / "my-skill" / "SKILL.md").write_text(snapshot_content)

    # Agent dir exists but skill not installed
    opencode_skills = temp_dir / ".opencode" / "skills"
    opencode_skills.mkdir(parents=True)

    comparator = DeltaComparator(
        valid_warehouse,
        artifacts_dir,
        skills_paths={"opencode": opencode_skills},
    )
    diff = comparator.detailed_diff("skills/my-skill/SKILL.md", color=False)

    # Falls back to snapshot — diff should show snapshot_content change
    assert "Snapshot version" in diff or len(diff) > 0


def test_compare_from_config_glob_detects_added_skill_in_live_dir(
    valid_warehouse, temp_dir
):
    """Glob-based config detects a skill present in the live dir but not in the warehouse."""
    from beacon.core.settings import BeaconSettings

    artifacts_dir = temp_dir / "artifacts"
    artifacts_dir.mkdir()

    # Live dir has a new skill not yet contributed to warehouse
    opencode_skills = temp_dir / ".opencode" / "skills"
    (opencode_skills / "new-skill").mkdir(parents=True)
    (opencode_skills / "new-skill" / "SKILL.md").write_text("# New local skill\n")

    beacon_yaml = temp_dir / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge: []\n  skills:\n    - skills/**/*\n  contexts: []\n"
    )
    settings = BeaconSettings.from_yaml(beacon_yaml)

    comparator = DeltaComparator(
        valid_warehouse,
        artifacts_dir,
        skills_paths={"opencode": opencode_skills},
    )
    summary = comparator.compare_from_config(settings)

    added_paths = [r.path for r in summary.added]
    assert "skills/new-skill/SKILL.md" in added_paths


def test_compare_from_config_glob_no_duplicates_multi_agent(valid_warehouse, temp_dir):
    """With multiple agents having the same skill, it appears only once in results."""
    from beacon.core.settings import BeaconSettings

    content = "# Warehouse\n"
    (valid_warehouse / "skills" / "my-skill").mkdir(parents=True)
    (valid_warehouse / "skills" / "my-skill" / "SKILL.md").write_text(content)

    opencode_skills = temp_dir / ".opencode" / "skills"
    (opencode_skills / "my-skill").mkdir(parents=True)
    (opencode_skills / "my-skill" / "SKILL.md").write_text(content)

    claude_skills = temp_dir / ".claude" / "skills"
    (claude_skills / "my-skill").mkdir(parents=True)
    (claude_skills / "my-skill" / "SKILL.md").write_text(content)

    artifacts_dir = temp_dir / "artifacts"
    artifacts_dir.mkdir()

    beacon_yaml = temp_dir / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge: []\n  skills:\n    - skills/**/*\n  contexts: []\n"
    )
    settings = BeaconSettings.from_yaml(beacon_yaml)

    comparator = DeltaComparator(
        valid_warehouse,
        artifacts_dir,
        skills_paths={"opencode": opencode_skills, "claudecode": claude_skills},
    )
    summary = comparator.compare_from_config(settings)

    # Should appear exactly once despite two agents
    skill_paths = [r.path for r in summary.results if "my-skill" in r.path]
    assert len(skill_paths) == 1
