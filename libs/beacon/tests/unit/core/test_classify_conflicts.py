"""Tests for SyncEngine.classify_conflicts() and files_identical() methods.

TDD Test Cases for files_identical (5.1):
- TC1: Two identical files → returns True
- TC2: Two different files → returns False
- TC3: Public method accessible as engine.files_identical(f1, f2)

TDD Test Cases for classify_conflicts (5.2):
- TC1: All files identical → empty list
- TC2: One file differs → list with that path
- TC3: File missing locally (fresh) → not included (not a conflict)
- TC4: Mixed — some identical, some differ, some missing → only differing returned
"""

from pathlib import Path

from beacon.core.sync import SyncEngine


class TestFilesIdentical:
    """Tests for promoted public files_identical method (TC1-TC3)."""

    def test_tc1_identical_files_return_true(self, tmp_path):
        """TC1: Two identical files → returns True."""
        file1 = tmp_path / "a.md"
        file2 = tmp_path / "b.md"
        content = "# Same content\n"
        file1.write_text(content)
        file2.write_text(content)

        engine = SyncEngine(
            warehouse_path=tmp_path,
            artifacts_path=tmp_path / "artifacts",
        )
        assert engine.files_identical(file1, file2) is True

    def test_tc2_different_files_return_false(self, tmp_path):
        """TC2: Two different files → returns False."""
        file1 = tmp_path / "a.md"
        file2 = tmp_path / "b.md"
        file1.write_text("# Content A\n")
        file2.write_text("# Content B\n")

        engine = SyncEngine(
            warehouse_path=tmp_path,
            artifacts_path=tmp_path / "artifacts",
        )
        assert engine.files_identical(file1, file2) is False

    def test_tc3_public_method_accessible(self, tmp_path):
        """TC3: Public method accessible as engine.files_identical(f1, f2)."""
        engine = SyncEngine(
            warehouse_path=tmp_path,
            artifacts_path=tmp_path / "artifacts",
        )
        # Should be accessible without underscore prefix
        assert hasattr(engine, "files_identical")
        assert callable(engine.files_identical)


class TestClassifyConflicts:
    """Tests for SyncEngine.classify_conflicts() covering TC1-TC4."""

    def _make_engine(self, tmp_path: Path) -> tuple[SyncEngine, Path, Path]:
        warehouse = tmp_path / "warehouse"
        artifacts = tmp_path / "artifacts"
        warehouse.mkdir()
        artifacts.mkdir()
        engine = SyncEngine(warehouse_path=warehouse, artifacts_path=artifacts)
        return engine, warehouse, artifacts

    def test_tc1_all_identical_returns_empty(self, tmp_path):
        """TC1: All files identical → empty list."""
        engine, warehouse, artifacts = self._make_engine(tmp_path)
        content = "# Same content\n"
        for p in ["knowledge/a.md", "knowledge/b.md"]:
            (warehouse / p).parent.mkdir(parents=True, exist_ok=True)
            (warehouse / p).write_text(content)
            (artifacts / p).parent.mkdir(parents=True, exist_ok=True)
            (artifacts / p).write_text(content)

        result = engine.classify_conflicts(["knowledge/a.md", "knowledge/b.md"])
        assert result == []

    def test_tc2_one_file_differs(self, tmp_path):
        """TC2: One file differs → list with that path."""
        engine, warehouse, artifacts = self._make_engine(tmp_path)
        (warehouse / "knowledge").mkdir()
        (artifacts / "knowledge").mkdir()
        (warehouse / "knowledge" / "a.md").write_text("# Original\n")
        (artifacts / "knowledge" / "a.md").write_text("# Modified\n")

        result = engine.classify_conflicts(["knowledge/a.md"])
        assert result == ["knowledge/a.md"]

    def test_tc3_missing_dest_not_a_conflict(self, tmp_path):
        """TC3: File missing locally (fresh) → not included (not a conflict)."""
        engine, warehouse, artifacts = self._make_engine(tmp_path)
        (warehouse / "knowledge").mkdir()
        (warehouse / "knowledge" / "fresh.md").write_text("# New\n")
        # No artifact version exists

        result = engine.classify_conflicts(["knowledge/fresh.md"])
        assert result == []

    def test_tc4_mixed_returns_only_differing(self, tmp_path):
        """TC4: Mixed — some identical, some differ, some missing → only differing returned."""
        engine, warehouse, artifacts = self._make_engine(tmp_path)
        (warehouse / "knowledge").mkdir()
        (artifacts / "knowledge").mkdir()

        # identical
        (warehouse / "knowledge" / "same.md").write_text("# Same\n")
        (artifacts / "knowledge" / "same.md").write_text("# Same\n")

        # differing
        (warehouse / "knowledge" / "different.md").write_text("# Original\n")
        (artifacts / "knowledge" / "different.md").write_text("# Modified\n")

        # fresh (no local)
        (warehouse / "knowledge" / "fresh.md").write_text("# Fresh\n")

        result = engine.classify_conflicts(
            ["knowledge/same.md", "knowledge/different.md", "knowledge/fresh.md"]
        )
        assert result == ["knowledge/different.md"]
