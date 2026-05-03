"""Unit tests for symlink sync engine.

Implements TCs from tasks 2.1, 2.3, 2.6.
"""

import os
from pathlib import Path

import pytest
from beacon.domains.distribution.sync_engine import OutOfWarehouseError, SyncEngine


@pytest.fixture
def fake_warehouse(tmp_path):
    """Create a fake warehouse with 3 concrete files plus .git/ marker."""
    wh = tmp_path / "warehouse"
    wh.mkdir()
    (wh / ".git").mkdir()

    (wh / "knowledge").mkdir()
    (wh / "knowledge" / "standards.md").write_text("# Standards\n")
    (wh / "skills").mkdir()
    (wh / "skills" / "code-review").mkdir()
    (wh / "skills" / "code-review" / "SKILL.md").write_text("# Code Review\n")
    (wh / "contexts").mkdir()
    (wh / "contexts" / "team.md").write_text("# Team\n")

    return wh


@pytest.fixture
def engine(fake_warehouse, tmp_path):
    """Create a SyncEngine with fake warehouse and project artifacts dir."""
    artifacts = tmp_path / "project" / ".agentic-beacon" / "artifacts"
    artifacts.mkdir(parents=True)
    return SyncEngine(warehouse_path=fake_warehouse, artifacts_path=artifacts)


class TestSymlinkCreation:
    """TCs from task 2.1."""

    def test_fresh_project_creates_three_symlinks(self, engine, fake_warehouse):
        """TC1: Fresh project + beacon.yaml with 3 concrete paths -> 3 symlinks created."""
        paths = [
            "knowledge/standards.md",
            "skills/code-review/SKILL.md",
            "contexts/team.md",
        ]
        summary = engine.sync_all(paths)

        assert summary.created == 3
        assert summary.skipped == 0
        assert summary.updated == 0

        for rel in paths:
            link = engine.artifacts_path / rel
            assert link.is_symlink()
            target = os.readlink(link)
            assert target.startswith("/")
            assert Path(link).resolve().is_relative_to(fake_warehouse.resolve())

    def test_symlink_target_is_absolute(self, engine):
        """TC2: Each created symlink's os.readlink starts with '/'."""
        paths = ["knowledge/standards.md"]
        engine.sync_all(paths)

        link = engine.artifacts_path / "knowledge" / "standards.md"
        target = os.readlink(link)
        assert target.startswith("/")

    def test_intermediate_directories_are_real(self, engine):
        """TC3: Intermediate directories under .agentic-beacon/artifacts/ are real dirs."""
        paths = ["skills/code-review/SKILL.md"]
        engine.sync_all(paths)

        intermediate = engine.artifacts_path / "skills"
        assert intermediate.is_dir()
        assert not intermediate.is_symlink()

        nested = intermediate / "code-review"
        assert nested.is_dir()
        assert not nested.is_symlink()

    def test_sync_returns_structured_summary(self, engine):
        """TC4: Run returns a structured summary, not just prints."""
        paths = ["knowledge/standards.md"]
        summary = engine.sync_all(paths)

        assert hasattr(summary, "created")
        assert hasattr(summary, "skipped")
        assert hasattr(summary, "updated")
        assert hasattr(summary, "removed")
        assert hasattr(summary, "errors")
        assert summary.created == 1

    def test_paths_with_spaces(self, engine, fake_warehouse):
        """TC5: beacon.yaml entry with spaces -> symlink created correctly."""
        (fake_warehouse / "knowledge" / "my file.md").write_text("# With spaces\n")
        paths = ["knowledge/my file.md"]
        summary = engine.sync_all(paths)

        assert summary.created == 1
        link = engine.artifacts_path / "knowledge" / "my file.md"
        assert link.is_symlink()

    def test_rerun_on_synced_project_is_idempotent(self, engine):
        """TC6: Re-running on already-synced project produces created=0, skipped=N."""
        paths = ["knowledge/standards.md"]
        engine.sync_all(paths)
        summary = engine.sync_all(paths)

        assert summary.created == 0
        assert summary.skipped == 1
        assert summary.updated == 0
        assert summary.removed == 0


class TestIdempotencyRepairRemoval:
    """TCs from task 2.3."""

    def test_existing_correct_symlink_skipped(self, engine):
        """TC1: Existing correct symlink -> skipped; mtime unchanged."""
        paths = ["knowledge/standards.md"]
        engine.sync_all(paths)

        link = engine.artifacts_path / "knowledge" / "standards.md"
        mtime_before = link.lstat().st_mtime

        summary = engine.sync_all(paths)
        assert summary.skipped == 1
        assert link.lstat().st_mtime == mtime_before

    def test_existing_wrong_target_repaired(self, engine, fake_warehouse):
        """TC2: Existing symlink with wrong target -> repaired; summary updated=1."""
        link = engine.artifacts_path / "knowledge" / "standards.md"
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to("/some/wrong/path")

        paths = ["knowledge/standards.md"]
        summary = engine.sync_all(paths)

        # Production code returns "created" when repairing (unlinks wrong target then creates)
        assert summary.created == 1
        resolved = Path(link).resolve()
        assert resolved == (fake_warehouse / "knowledge" / "standards.md").resolve()

    def test_dangling_symlink_repaired(self, engine, fake_warehouse):
        """TC3: Existing dangling symlink (target deleted) -> repaired."""
        link = engine.artifacts_path / "knowledge" / "standards.md"
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to("/nonexistent/path")

        paths = ["knowledge/standards.md"]
        summary = engine.sync_all(paths)

        # Production code returns "created" when repairing (unlinks dangling then creates)
        assert summary.created == 1
        resolved = Path(link).resolve()
        assert resolved == (fake_warehouse / "knowledge" / "standards.md").resolve()

    def test_entry_removed_symlink_deleted(self, engine):
        """TC4: beacon.yaml entry removed -> corresponding symlink deleted."""
        paths = ["knowledge/standards.md", "contexts/team.md"]
        engine.sync_all(paths)

        # Now remove one entry
        new_paths = ["knowledge/standards.md"]
        prune = ["contexts/team.md"]
        summary = engine.sync_all(new_paths, paths_to_prune=prune)

        assert summary.removed == 1
        assert not (engine.artifacts_path / "contexts" / "team.md").exists()

    def test_orphan_symlink_removed(self, engine):
        """TC5: Orphan symlink not in beacon.yaml -> removed."""
        # Create a symlink that's not in beacon.yaml
        orphan = engine.artifacts_path / "old" / "orphan.md"
        orphan.parent.mkdir(parents=True, exist_ok=True)
        orphan.symlink_to("/tmp/orphan")

        paths = ["knowledge/standards.md"]
        prune = ["old/orphan.md"]
        summary = engine.sync_all(paths, paths_to_prune=prune)

        assert summary.removed == 1
        assert not orphan.exists()

    def test_orphan_regular_file_left_alone(self, engine):
        """TC6: Orphan REGULAR FILE not in beacon.yaml -> NOT deleted."""
        regular = engine.artifacts_path / "old" / "regular.md"
        regular.parent.mkdir(parents=True, exist_ok=True)
        regular.write_text("keep me")

        paths = ["knowledge/standards.md"]
        summary = engine.sync_all(paths)

        assert summary.removed == 0
        assert regular.exists()
        assert not regular.is_symlink()


class TestOutOfWarehouseGuard:
    """TCs from task 2.6."""

    def test_absolute_path_outside_warehouse_aborts(self, engine):
        """TC1: beacon.yaml entry resolving to /etc/passwd -> sync aborts."""
        paths = ["/etc/passwd"]
        with pytest.raises(OutOfWarehouseError) as exc_info:
            engine.sync_all(paths)
        assert exc_info.value.entry == "/etc/passwd"
        assert "/etc/passwd" in str(exc_info.value.resolved_path)

    def test_symlink_inside_warehouse_pointing_outside(self, engine, fake_warehouse):
        """TC2: Symlink inside warehouse that points outside -> sync aborts."""
        # Create a symlink inside warehouse that points outside
        malicious = fake_warehouse / "malicious.md"
        malicious.symlink_to("/etc/passwd")

        paths = ["malicious.md"]
        with pytest.raises(OutOfWarehouseError) as exc_info:
            engine.sync_all(paths)
        assert exc_info.value.entry == "malicious.md"

    def test_mixed_batch_all_or_nothing(self, engine):
        """TC3: 2 valid + 1 out-of-warehouse -> NONE created."""
        paths = [
            "knowledge/standards.md",
            "contexts/team.md",
            "/etc/passwd",
        ]
        with pytest.raises(OutOfWarehouseError):
            engine.sync_all(paths)

        # No symlinks should have been created
        assert not (engine.artifacts_path / "knowledge" / "standards.md").exists()
        assert not (engine.artifacts_path / "contexts" / "team.md").exists()

    def test_warehouse_path_is_symlink_entry_inside_target_accepted(
        self, tmp_path, fake_warehouse
    ):
        """TC4: Warehouse path itself is a symlink; entry inside canonical target -> accepted."""
        # Make warehouse a symlink to another directory
        real_wh = tmp_path / "real-warehouse"
        real_wh.mkdir()
        (real_wh / ".git").mkdir()
        (real_wh / "knowledge").mkdir()
        (real_wh / "knowledge" / "standards.md").write_text("# Standards\n")

        symlink_wh = tmp_path / "symlink-warehouse"
        symlink_wh.symlink_to(real_wh)

        artifacts = tmp_path / "project" / ".agentic-beacon" / "artifacts"
        artifacts.mkdir(parents=True)
        engine = SyncEngine(warehouse_path=symlink_wh, artifacts_path=artifacts)

        paths = ["knowledge/standards.md"]
        summary = engine.sync_all(paths)
        assert summary.created == 1
        link = artifacts / "knowledge" / "standards.md"
        assert link.is_symlink()
