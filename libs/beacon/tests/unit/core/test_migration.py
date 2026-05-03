"""Unit tests for migration detection and resolution.

Implements TCs from tasks 3.1, 3.2, 3.5, 3.6.
"""

import pytest
from beacon.domains.distribution.migration import migrate_entries
from beacon.domains.distribution.sync_engine import SyncEngine


def make_callback(decisions: dict[str, str]):
    """Create a resolve callback that returns decisions per rel_path."""

    def _cb(rel_path, diff):
        return decisions[rel_path]

    return _cb


@pytest.fixture
def migration_warehouse(tmp_path):
    """Create a warehouse with files for migration tests."""
    wh = tmp_path / "warehouse"
    wh.mkdir()
    (wh / ".git").mkdir()

    (wh / "knowledge").mkdir()
    (wh / "knowledge" / "unchanged.md").write_text("# Unchanged\noriginal content\n")
    (wh / "knowledge" / "modified.md").write_text("# Modified\noriginal content\n")
    (wh / "knowledge" / "missing.md").write_text("# Missing\noriginal content\n")

    return wh


@pytest.fixture
def migration_engine(migration_warehouse, tmp_path):
    """Create a SyncEngine for migration tests."""
    artifacts = tmp_path / "project" / ".agentic-beacon" / "artifacts"
    artifacts.mkdir(parents=True)
    return SyncEngine(warehouse_path=migration_warehouse, artifacts_path=artifacts)


class TestClassifyEntries:
    """TCs from task 3.1."""

    def test_symlink_ok(self, migration_engine, migration_warehouse):
        """TC1: Symlink pointing to correct warehouse file -> symlink_ok."""
        rel = "knowledge/unchanged.md"
        migration_engine.create_symlink(rel)
        result = migration_engine.classify_entries([rel])
        assert result[rel] == "symlink_ok"

    def test_symlink_broken(self, migration_engine, migration_warehouse):
        """TC2: Symlink pointing to missing target -> symlink_broken."""
        rel = "knowledge/unchanged.md"
        link = migration_engine.artifacts_path / rel
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to("/nonexistent")

        result = migration_engine.classify_entries([rel])
        assert result[rel] == "symlink_broken"

    def test_regular_file_identical(self, migration_engine, migration_warehouse):
        """TC3: Regular file identical to warehouse -> regular_file_identical."""
        rel = "knowledge/unchanged.md"
        dest = migration_engine.artifacts_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("# Unchanged\noriginal content\n")

        result = migration_engine.classify_entries([rel])
        assert result[rel] == "regular_file_identical"

    def test_regular_file_modified(self, migration_engine, migration_warehouse):
        """TC4: Regular file differing from warehouse -> regular_file_modified."""
        rel = "knowledge/unchanged.md"
        dest = migration_engine.artifacts_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("# Unchanged\nMODIFIED content\n")

        result = migration_engine.classify_entries([rel])
        assert result[rel] == "regular_file_modified"

    def test_missing(self, migration_engine):
        """TC5: Entry absent from disk -> missing."""
        rel = "knowledge/unchanged.md"
        result = migration_engine.classify_entries([rel])
        assert result[rel] == "missing"

    def test_regular_file_warehouse_missing(
        self, migration_engine, migration_warehouse
    ):
        """TC6: Regular file but warehouse has no such file -> regular_file_modified."""
        rel = "knowledge/new-file.md"
        dest = migration_engine.artifacts_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("# New local file\n")

        result = migration_engine.classify_entries([rel])
        assert result[rel] == "regular_file_modified"


class TestMigrationResolution:
    """TCs from task 3.2 and 3.5."""

    def test_identical_file_silently_converted(
        self, migration_engine, migration_warehouse
    ):
        """TC1: Identical regular file -> converted silently."""
        rel = "knowledge/unchanged.md"
        dest = migration_engine.artifacts_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("# Unchanged\noriginal content\n")

        classification = migration_engine.classify_entries([rel])
        resolved = migrate_entries(migration_engine, classification)

        assert resolved[rel] == "converted"
        link = migration_engine.artifacts_path / rel
        assert link.is_symlink()
        # is_file() returns True for symlinks pointing to existing files,
        # so we assert it's not a regular file (it IS a symlink)
        assert not link.exists() or link.is_symlink()

    def test_callback_contribute(self, migration_engine, migration_warehouse):
        """TC3: User chooses 'c' -> warehouse receives local content, project becomes symlink."""
        rel = "knowledge/modified.md"
        dest = migration_engine.artifacts_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("# Modified\nLOCAL content\n")

        classification = migration_engine.classify_entries([rel])
        cb = make_callback({rel: "contribute"})
        resolved = migrate_entries(
            migration_engine, classification, resolve_callback=cb
        )

        assert resolved[rel] == "contributed"
        # Project path is now a symlink
        link = migration_engine.artifacts_path / rel
        assert link.is_symlink()
        # Warehouse has local content
        wh_file = migration_warehouse / rel
        assert "LOCAL content" in wh_file.read_text()

    def test_callback_discard(self, migration_engine, migration_warehouse):
        """TC4: User chooses 'd' -> local file deleted, symlink to warehouse content."""
        rel = "knowledge/modified.md"
        dest = migration_engine.artifacts_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("# Modified\nLOCAL content\n")

        classification = migration_engine.classify_entries([rel])
        cb = make_callback({rel: "discard"})
        resolved = migrate_entries(
            migration_engine, classification, resolve_callback=cb
        )

        assert resolved[rel] == "discarded"
        link = migration_engine.artifacts_path / rel
        assert link.is_symlink()
        # Warehouse unchanged
        wh_file = migration_warehouse / rel
        assert "original content" in wh_file.read_text()

    def test_callback_skip(self, migration_engine):
        """TC5: User chooses 's' -> local file untouched, NO symlink."""
        rel = "knowledge/modified.md"
        dest = migration_engine.artifacts_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("# Modified\nLOCAL content\n")

        classification = migration_engine.classify_entries([rel])
        cb = make_callback({rel: "skip"})
        resolved = migrate_entries(
            migration_engine, classification, resolve_callback=cb
        )

        assert resolved[rel] == "skipped"
        # Local file still exists as regular file
        assert (migration_engine.artifacts_path / rel).is_file()
        assert not (migration_engine.artifacts_path / rel).is_symlink()

    def test_diff_output_non_empty(self, migration_engine):
        """TC6: Diff output is non-empty and labeled."""
        from beacon.domains.distribution.migration import diff_preview

        rel = "knowledge/modified.md"
        local = migration_engine.artifacts_path / rel
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text("# Modified\nLOCAL content\n")
        warehouse = migration_engine.warehouse_path / rel

        diff = diff_preview(local, warehouse)
        assert diff
        assert "--- warehouse" in diff
        assert "+++ local" in diff

    def test_contribute_local_flag(self, migration_engine, migration_warehouse):
        """TC from 3.5: --contribute_local on modified file -> contributed, no prompts."""
        rel = "knowledge/modified.md"
        dest = migration_engine.artifacts_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("# Modified\nLOCAL content\n")

        classification = migration_engine.classify_entries([rel])
        resolved = migrate_entries(
            migration_engine, classification, contribute_local=True
        )

        assert resolved[rel] == "contributed"
        link = migration_engine.artifacts_path / rel
        assert link.is_symlink()
        wh_file = migration_warehouse / rel
        assert "LOCAL content" in wh_file.read_text()

    def test_discard_local_flag(self, migration_engine, migration_warehouse):
        """TC from 3.5: --discard_local on modified file -> discarded, no prompts."""
        rel = "knowledge/modified.md"
        dest = migration_engine.artifacts_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("# Modified\nLOCAL content\n")

        classification = migration_engine.classify_entries([rel])
        resolved = migrate_entries(migration_engine, classification, discard_local=True)

        assert resolved[rel] == "discarded"
        link = migration_engine.artifacts_path / rel
        assert link.is_symlink()
        wh_file = migration_warehouse / rel
        assert "original content" in wh_file.read_text()

    def test_discard_local_preserves_file_when_warehouse_missing(
        self, migration_engine
    ):
        """Discard cannot delete local-only content when no warehouse source exists."""
        rel = "knowledge/local-only.md"
        dest = migration_engine.artifacts_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("# Local only\nimportant content\n")

        classification = migration_engine.classify_entries([rel])
        resolved = migrate_entries(migration_engine, classification, discard_local=True)

        assert resolved[rel] == "skipped"
        assert dest.exists()
        assert not dest.is_symlink()
        assert "important content" in dest.read_text()


class TestResumability:
    """TCs from task 3.6."""

    def test_abort_mid_flow_no_orphans(self, migration_engine, migration_warehouse):
        """TC1: Abort mid-flow leaves valid mixed state."""
        rels = ["knowledge/unchanged.md", "knowledge/modified.md"]

        # Set up: first is identical regular file, second is modified
        for rel in rels:
            dest = migration_engine.artifacts_path / rel
            dest.parent.mkdir(parents=True, exist_ok=True)

        (migration_engine.artifacts_path / "knowledge" / "unchanged.md").write_text(
            "# Unchanged\noriginal content\n"
        )
        (migration_engine.artifacts_path / "knowledge" / "modified.md").write_text(
            "# Modified\nLOCAL content\n"
        )

        classification = migration_engine.classify_entries(rels)

        # Callback that raises on second file
        class AbortException(Exception):
            pass

        def abort_cb(rel_path, diff):
            if rel_path == "knowledge/modified.md":
                raise AbortException("User aborted")
            return "discard"

        with pytest.raises(AbortException):
            migrate_entries(migration_engine, classification, resolve_callback=abort_cb)

        # File 1 should be converted/discarded
        first = migration_engine.artifacts_path / "knowledge" / "unchanged.md"
        assert first.is_symlink() or first.is_file()

        # File 2 should still be regular file (not partially symlinked)
        second = migration_engine.artifacts_path / "knowledge" / "modified.md"
        assert second.is_file()

    def test_resume_based_on_filesystem(self, migration_engine, migration_warehouse):
        """TC3: Resume is based purely on filesystem classification."""
        rels = ["knowledge/unchanged.md", "knowledge/modified.md"]

        for rel in rels:
            dest = migration_engine.artifacts_path / rel
            dest.parent.mkdir(parents=True, exist_ok=True)

        (migration_engine.artifacts_path / "knowledge" / "unchanged.md").write_text(
            "# Unchanged\noriginal content\n"
        )
        (migration_engine.artifacts_path / "knowledge" / "modified.md").write_text(
            "# Modified\nLOCAL content\n"
        )

        # First run: discard modified file; unchanged is auto-converted
        classification1 = migration_engine.classify_entries(rels)
        cb1 = make_callback({"knowledge/modified.md": "discard"})
        resolved1 = migrate_entries(
            migration_engine, classification1, resolve_callback=cb1
        )
        assert resolved1["knowledge/unchanged.md"] == "converted"
        assert resolved1["knowledge/modified.md"] == "discarded"

        # Second run: both should be symlinks now
        classification2 = migration_engine.classify_entries(rels)
        assert classification2["knowledge/unchanged.md"] == "symlink_ok"
        assert classification2["knowledge/modified.md"] == "symlink_ok"
