"""Unit tests for _collect_artifact_paths — knowledge node expansion.

Bug: When beacon.yaml contains a node-level knowledge entry (directory path like
``knowledge/python``), _collect_artifact_paths was adding the raw directory string
to the tracked set instead of expanding it to individual .md file paths.

This caused _find_untracked_local_files to report every synced knowledge file as
a new untracked artifact, making abc delta show all knowledge files as contributions.

TDD Test Cases:
- TC1: knowledge entry is a warehouse directory → expands to individual .md paths
- TC2: knowledge entry with trailing slash → strips slash and expands correctly
- TC3: knowledge entry is a regular file (not a dir) → added as-is
- TC4: locally-added .md file in node dir (not yet in warehouse) → included in tracked
- TC5: nested knowledge node (knowledge/data-platform/clickhouse) → expands correctly
"""

from pathlib import Path

from beacon.core.manifest.beacon import BeaconManifest
from beacon.domains.distribution.delta import DeltaComparator
from beacon.utils.delta import _collect_artifact_paths


def _make_manifest(knowledge: list[str]) -> BeaconManifest:
    return _build_manifest(knowledge)


def _build_manifest(knowledge: list[str]) -> BeaconManifest:
    from beacon.core.manifest.beacon import ArtifactsConfig

    m = BeaconManifest()
    m.artifacts = ArtifactsConfig(knowledge=knowledge, skills=[], contexts=[])
    return m


def _make_comparator(warehouse_path: Path, artifacts_path: Path) -> DeltaComparator:
    return DeltaComparator(
        warehouse_path=warehouse_path,
        artifacts_path=artifacts_path,
        skills_paths={},
    )


class TestCollectArtifactPathsKnowledgeNodes:
    def test_tc1_knowledge_dir_entry_expands_to_md_files(self, tmp_path):
        """TC1: knowledge/python is a warehouse dir → expands to its .md files."""
        warehouse = tmp_path / "warehouse"
        artifacts = tmp_path / "artifacts"

        node = warehouse / "knowledge" / "python"
        (node / "decisions").mkdir(parents=True)
        (node / "decisions" / "typing.md").write_text("# Typing")
        (node / "lessons").mkdir()
        (node / "lessons" / "async.md").write_text("# Async")

        comparator = _make_comparator(warehouse, artifacts)
        manifest = _build_manifest(["knowledge/python"])

        paths = _collect_artifact_paths(comparator, manifest)

        assert "knowledge/python/decisions/typing.md" in paths
        assert "knowledge/python/lessons/async.md" in paths
        # The raw directory string must NOT be in paths
        assert "knowledge/python" not in paths

    def test_tc2_trailing_slash_entry_expands(self, tmp_path):
        """TC2: knowledge/python/ with trailing slash → expands to .md files."""
        warehouse = tmp_path / "warehouse"
        artifacts = tmp_path / "artifacts"

        node = warehouse / "knowledge" / "python"
        (node / "facts").mkdir(parents=True)
        (node / "facts" / "basics.md").write_text("# Basics")

        comparator = _make_comparator(warehouse, artifacts)
        manifest = _build_manifest(["knowledge/python/"])

        paths = _collect_artifact_paths(comparator, manifest)

        assert "knowledge/python/facts/basics.md" in paths
        assert "knowledge/python/" not in paths
        assert "knowledge/python" not in paths

    def test_tc3_file_entry_added_as_is(self, tmp_path):
        """TC3: knowledge/doc.md is a regular file entry → kept as-is."""
        warehouse = tmp_path / "warehouse"
        artifacts = tmp_path / "artifacts"

        (warehouse / "knowledge").mkdir(parents=True)
        (warehouse / "knowledge" / "doc.md").write_text("# Doc")

        comparator = _make_comparator(warehouse, artifacts)
        manifest = _build_manifest(["knowledge/doc.md"])

        paths = _collect_artifact_paths(comparator, manifest)

        assert "knowledge/doc.md" in paths

    def test_tc4_locally_added_file_in_node_included(self, tmp_path):
        """TC4: .md file added locally under a node dir (not yet in warehouse) is tracked."""
        warehouse = tmp_path / "warehouse"
        artifacts = tmp_path / "artifacts"

        # Warehouse has one file
        node = warehouse / "knowledge" / "python"
        (node / "decisions").mkdir(parents=True)
        (node / "decisions" / "existing.md").write_text("# Existing")

        # Local artifacts has an extra file not in warehouse yet
        local_node = artifacts / "knowledge" / "python" / "decisions"
        local_node.mkdir(parents=True)
        (local_node / "existing.md").write_text("# Existing")
        (local_node / "new-local.md").write_text("# New local file")

        comparator = _make_comparator(warehouse, artifacts)
        manifest = _build_manifest(["knowledge/python"])

        paths = _collect_artifact_paths(comparator, manifest)

        assert "knowledge/python/decisions/existing.md" in paths
        assert "knowledge/python/decisions/new-local.md" in paths

    def test_tc5_nested_node_path_expands(self, tmp_path):
        """TC5: knowledge/data-platform/clickhouse deep node → expands to .md files."""
        warehouse = tmp_path / "warehouse"
        artifacts = tmp_path / "artifacts"

        node = warehouse / "knowledge" / "data-platform" / "clickhouse"
        (node / "facts").mkdir(parents=True)
        (node / "facts" / "schema.md").write_text("# Schema")

        comparator = _make_comparator(warehouse, artifacts)
        manifest = _build_manifest(["knowledge/data-platform/clickhouse"])

        paths = _collect_artifact_paths(comparator, manifest)

        assert "knowledge/data-platform/clickhouse/facts/schema.md" in paths
        assert "knowledge/data-platform/clickhouse" not in paths
