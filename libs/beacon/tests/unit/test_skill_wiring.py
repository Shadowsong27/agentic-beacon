"""Unit tests for skill wiring: per-file symlinks to the warehouse and
dynamic OpenCode command stub generation.

Covers the fix for the bug where project-level skills under .opencode/skills/
and .claude/skills/ were copies of the warehouse content instead of symlinks,
which caused edits made in the warehouse to be invisible to agents until the
next abc sync.
"""

import os
from pathlib import Path

from beacon.domains.artifact.skill import (
    _resolve_skill_source,
    _write_skill_file,
    wire_single_skill,
    wire_skills_post_sync,
)

# ---------------------------------------------------------------------------
# Helpers — build a fake warehouse + artifacts layout on disk
# ---------------------------------------------------------------------------


def _make_warehouse_skill(
    warehouse: Path, skill_name: str, *, extra_files: dict[str, str] | None = None
) -> Path:
    """Create a warehouse-side skill directory with SKILL.md and optional extras."""
    skill_dir = warehouse / "skills" / skill_name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\ndescription: Test skill {skill_name}\n---\n\n# {skill_name}\n",
        encoding="utf-8",
    )
    for rel, content in (extra_files or {}).items():
        dest = skill_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
    return skill_dir


def _make_artifact_skill(artifacts_dir: Path, warehouse_skill_dir: Path) -> Path:
    """Symlink each file in warehouse_skill_dir into .agentic-beacon/artifacts/skills/
    matching how SyncEngine.create_symlink lays things out (per-file absolute symlinks,
    real intermediate directories)."""
    skill_name = warehouse_skill_dir.name
    artifact_skill_dir = artifacts_dir / "skills" / skill_name
    artifact_skill_dir.mkdir(parents=True)
    for warehouse_file in sorted(warehouse_skill_dir.rglob("*")):
        if not warehouse_file.is_file():
            continue
        rel = warehouse_file.relative_to(warehouse_skill_dir)
        dest = artifact_skill_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.symlink_to(str(warehouse_file.resolve()))
    return artifact_skill_dir


# ---------------------------------------------------------------------------
# _resolve_skill_source
# ---------------------------------------------------------------------------


class TestResolveSkillSource:
    def test_symlink_source_returns_warehouse_path_and_true(self, tmp_path):
        warehouse_file = tmp_path / "warehouse" / "SKILL.md"
        warehouse_file.parent.mkdir()
        warehouse_file.write_text("hi", encoding="utf-8")
        artifact_file = tmp_path / "artifact" / "SKILL.md"
        artifact_file.parent.mkdir()
        artifact_file.symlink_to(str(warehouse_file))

        target, use_symlink = _resolve_skill_source(artifact_file)

        assert use_symlink is True
        assert target == Path(str(warehouse_file))

    def test_regular_file_source_returns_self_and_false(self, tmp_path):
        regular = tmp_path / "SKILL.md"
        regular.write_text("hi", encoding="utf-8")

        target, use_symlink = _resolve_skill_source(regular)

        assert use_symlink is False
        assert target == regular


# ---------------------------------------------------------------------------
# _write_skill_file
# ---------------------------------------------------------------------------


class TestWriteSkillFile:
    def test_creates_symlink_when_use_symlink_true(self, tmp_path):
        warehouse_file = tmp_path / "warehouse" / "SKILL.md"
        warehouse_file.parent.mkdir()
        warehouse_file.write_text("content", encoding="utf-8")
        dest = tmp_path / "dest" / "SKILL.md"

        changed = _write_skill_file(dest, warehouse_file, use_symlink=True)

        assert changed is True
        assert dest.is_symlink()
        assert os.readlink(dest) == str(warehouse_file)

    def test_returns_false_when_symlink_already_correct(self, tmp_path):
        warehouse_file = tmp_path / "warehouse" / "SKILL.md"
        warehouse_file.parent.mkdir()
        warehouse_file.write_text("content", encoding="utf-8")
        dest = tmp_path / "dest" / "SKILL.md"
        dest.parent.mkdir()
        dest.symlink_to(str(warehouse_file))

        changed = _write_skill_file(dest, warehouse_file, use_symlink=True)

        assert changed is False

    def test_replaces_regular_file_with_symlink(self, tmp_path):
        """Migration case: project was set up before the symlink fix."""
        warehouse_file = tmp_path / "warehouse" / "SKILL.md"
        warehouse_file.parent.mkdir()
        warehouse_file.write_text("warehouse content", encoding="utf-8")
        dest = tmp_path / "dest" / "SKILL.md"
        dest.parent.mkdir()
        dest.write_text("stale copy", encoding="utf-8")
        assert not dest.is_symlink()

        changed = _write_skill_file(dest, warehouse_file, use_symlink=True)

        assert changed is True
        assert dest.is_symlink()
        assert os.readlink(dest) == str(warehouse_file)

    def test_repairs_wrong_target_symlink(self, tmp_path):
        warehouse_file = tmp_path / "warehouse" / "SKILL.md"
        warehouse_file.parent.mkdir()
        warehouse_file.write_text("new", encoding="utf-8")
        old_target = tmp_path / "old" / "SKILL.md"
        old_target.parent.mkdir()
        old_target.write_text("old", encoding="utf-8")
        dest = tmp_path / "dest" / "SKILL.md"
        dest.parent.mkdir()
        dest.symlink_to(str(old_target))

        changed = _write_skill_file(dest, warehouse_file, use_symlink=True)

        assert changed is True
        assert os.readlink(dest) == str(warehouse_file)

    def test_copies_when_use_symlink_false(self, tmp_path):
        """Bundled skill case: source is a regular file, dest gets a content copy."""
        source = tmp_path / "source" / "SKILL.md"
        source.parent.mkdir()
        source.write_text("content", encoding="utf-8")
        dest = tmp_path / "dest" / "SKILL.md"

        changed = _write_skill_file(dest, source, use_symlink=False)

        assert changed is True
        assert not dest.is_symlink()
        assert dest.read_text(encoding="utf-8") == "content"

    def test_copy_is_noop_when_content_matches(self, tmp_path):
        source = tmp_path / "source" / "SKILL.md"
        source.parent.mkdir()
        source.write_text("content", encoding="utf-8")
        dest = tmp_path / "dest" / "SKILL.md"
        dest.parent.mkdir()
        dest.write_text("content", encoding="utf-8")

        changed = _write_skill_file(dest, source, use_symlink=False)

        assert changed is False


# ---------------------------------------------------------------------------
# wire_single_skill — warehouse-backed skills produce symlinks
# ---------------------------------------------------------------------------


class TestWireSingleSkillSymlinks:
    def test_creates_symlinks_to_warehouse_for_opencode(self, tmp_path):
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()
        warehouse_skill = _make_warehouse_skill(
            warehouse, "review", extra_files={"scripts/helper.py": "print('hi')\n"}
        )
        artifacts_dir = tmp_path / "project" / ".agentic-beacon" / "artifacts"
        artifact_skill = _make_artifact_skill(artifacts_dir, warehouse_skill)
        project_root = tmp_path / "project"

        wire_single_skill(project_root, "review", artifact_skill, "opencode")

        live_skill = project_root / ".opencode" / "skills" / "review" / "SKILL.md"
        live_helper = (
            project_root / ".opencode" / "skills" / "review" / "scripts" / "helper.py"
        )
        assert live_skill.is_symlink()
        assert os.readlink(live_skill) == str(
            (warehouse / "skills" / "review" / "SKILL.md").resolve()
        )
        assert live_helper.is_symlink()
        assert os.readlink(live_helper) == str(
            (warehouse / "skills" / "review" / "scripts" / "helper.py").resolve()
        )

    def test_creates_symlinks_for_claudecode(self, tmp_path):
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()
        warehouse_skill = _make_warehouse_skill(warehouse, "review")
        artifacts_dir = tmp_path / "project" / ".agentic-beacon" / "artifacts"
        artifact_skill = _make_artifact_skill(artifacts_dir, warehouse_skill)
        project_root = tmp_path / "project"

        wire_single_skill(project_root, "review", artifact_skill, "claudecode")

        live_skill = project_root / ".claude" / "skills" / "review" / "SKILL.md"
        assert live_skill.is_symlink()
        assert os.readlink(live_skill) == str(
            (warehouse / "skills" / "review" / "SKILL.md").resolve()
        )

    def test_warehouse_edit_visible_without_resync(self, tmp_path):
        """Key regression test: after wiring, edits in the warehouse must be
        visible through .opencode/skills/ immediately, without re-running sync."""
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()
        warehouse_skill = _make_warehouse_skill(warehouse, "review")
        artifacts_dir = tmp_path / "project" / ".agentic-beacon" / "artifacts"
        artifact_skill = _make_artifact_skill(artifacts_dir, warehouse_skill)
        project_root = tmp_path / "project"
        wire_single_skill(project_root, "review", artifact_skill, "opencode")

        # Mutate warehouse directly — simulates editing via another project.
        warehouse_file = warehouse / "skills" / "review" / "SKILL.md"
        warehouse_file.write_text(
            "---\ndescription: UPDATED\n---\n\n# Updated content\n",
            encoding="utf-8",
        )

        # Read through the live symlink — must reflect the warehouse edit.
        live_skill = project_root / ".opencode" / "skills" / "review" / "SKILL.md"
        assert "UPDATED" in live_skill.read_text(encoding="utf-8")

    def test_idempotent_second_call_returns_false(self, tmp_path):
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()
        warehouse_skill = _make_warehouse_skill(warehouse, "review")
        artifacts_dir = tmp_path / "project" / ".agentic-beacon" / "artifacts"
        artifact_skill = _make_artifact_skill(artifacts_dir, warehouse_skill)
        project_root = tmp_path / "project"

        first = wire_single_skill(project_root, "review", artifact_skill, "opencode")
        second = wire_single_skill(project_root, "review", artifact_skill, "opencode")

        assert first is True
        assert second is False

    def test_replaces_pre_existing_regular_files_from_old_behavior(self, tmp_path):
        """Projects set up before the symlink fix have .opencode/skills/<name>/SKILL.md
        as a regular file copy. Sync must replace it with a symlink to warehouse."""
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()
        warehouse_skill = _make_warehouse_skill(warehouse, "review")
        artifacts_dir = tmp_path / "project" / ".agentic-beacon" / "artifacts"
        artifact_skill = _make_artifact_skill(artifacts_dir, warehouse_skill)
        project_root = tmp_path / "project"
        # Simulate old copy-based install
        stale_dir = project_root / ".opencode" / "skills" / "review"
        stale_dir.mkdir(parents=True)
        stale_file = stale_dir / "SKILL.md"
        stale_file.write_text("stale content", encoding="utf-8")
        assert not stale_file.is_symlink()

        wire_single_skill(project_root, "review", artifact_skill, "opencode")

        assert stale_file.is_symlink()
        assert os.readlink(stale_file) == str(
            (warehouse / "skills" / "review" / "SKILL.md").resolve()
        )


# ---------------------------------------------------------------------------
# wire_single_skill — bundled skills still get copies
# ---------------------------------------------------------------------------


class TestWireSingleSkillBundled:
    def test_bundled_skill_source_produces_regular_file_copy(self, tmp_path):
        """Bundled skills live inside the installed agentic-beacon package as
        regular files. Symlinking to site-packages is fragile across pip upgrades,
        so we keep copy behavior in that path."""
        bundled_skill = tmp_path / "package_data" / "skills" / "record-knowledge"
        bundled_skill.mkdir(parents=True)
        (bundled_skill / "SKILL.md").write_text(
            "---\ndescription: Record knowledge\n---\n# Skill\n",
            encoding="utf-8",
        )
        project_root = tmp_path / "project"

        wire_single_skill(project_root, "record-knowledge", bundled_skill, "opencode")

        live = project_root / ".opencode" / "skills" / "record-knowledge" / "SKILL.md"
        assert live.exists()
        assert not live.is_symlink()
        assert "Record knowledge" in live.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Command stub generation
# ---------------------------------------------------------------------------


class TestCommandStubGeneration:
    def test_stub_generated_for_opencode(self, tmp_path):
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()
        warehouse_skill = _make_warehouse_skill(warehouse, "review")
        artifacts_dir = tmp_path / "project" / ".agentic-beacon" / "artifacts"
        artifact_skill = _make_artifact_skill(artifacts_dir, warehouse_skill)
        project_root = tmp_path / "project"

        wire_single_skill(project_root, "review", artifact_skill, "opencode")

        stub = project_root / ".opencode" / "command" / "review.md"
        assert stub.exists()
        content = stub.read_text(encoding="utf-8")
        assert "description: Test skill review" in content
        assert "Use the **skill** tool" in content
        assert "`review`" in content

    def test_no_command_dir_for_claudecode(self, tmp_path):
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()
        warehouse_skill = _make_warehouse_skill(warehouse, "review")
        artifacts_dir = tmp_path / "project" / ".agentic-beacon" / "artifacts"
        artifact_skill = _make_artifact_skill(artifacts_dir, warehouse_skill)
        project_root = tmp_path / "project"

        wire_single_skill(project_root, "review", artifact_skill, "claudecode")

        # claudecode must NOT create .opencode/command/
        assert not (project_root / ".opencode" / "command").exists()

    def test_stub_regenerated_when_description_changes(self, tmp_path):
        """Command stubs are generated unconditionally each call so the stub
        description stays current with the warehouse SKILL.md frontmatter."""
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()
        warehouse_skill = _make_warehouse_skill(warehouse, "review")
        artifacts_dir = tmp_path / "project" / ".agentic-beacon" / "artifacts"
        artifact_skill = _make_artifact_skill(artifacts_dir, warehouse_skill)
        project_root = tmp_path / "project"

        wire_single_skill(project_root, "review", artifact_skill, "opencode")
        stub = project_root / ".opencode" / "command" / "review.md"
        assert "Test skill review" in stub.read_text(encoding="utf-8")

        # Edit warehouse description.
        (warehouse / "skills" / "review" / "SKILL.md").write_text(
            "---\ndescription: Brand new description\n---\n\n# Review\n",
            encoding="utf-8",
        )

        wire_single_skill(project_root, "review", artifact_skill, "opencode")

        assert "Brand new description" in stub.read_text(encoding="utf-8")
        assert "Test skill review" not in stub.read_text(encoding="utf-8")

    def test_stub_falls_back_to_skill_name_when_description_missing(self, tmp_path):
        warehouse = tmp_path / "warehouse"
        skill_dir = warehouse / "skills" / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# No frontmatter here\n", encoding="utf-8")
        artifacts_dir = tmp_path / "project" / ".agentic-beacon" / "artifacts"
        artifact_skill = _make_artifact_skill(artifacts_dir, skill_dir)
        project_root = tmp_path / "project"

        wire_single_skill(project_root, "my-skill", artifact_skill, "opencode")

        stub = project_root / ".opencode" / "command" / "my-skill.md"
        assert "description: Use the my-skill skill" in stub.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# wire_skills_post_sync — end-to-end over artifacts/skills/
# ---------------------------------------------------------------------------


class TestWireSkillsPostSync:
    def _setup(
        self,
        tmp_path: Path,
        skill_names: list[str],
        *,
        create_opencode_config: bool = True,
    ) -> tuple[Path, Path, Path]:
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()
        project_root = tmp_path / "project"
        project_root.mkdir()
        if create_opencode_config:
            (project_root / "opencode.json").write_text("{}", encoding="utf-8")
        artifacts_dir = project_root / ".agentic-beacon" / "artifacts"

        for name in skill_names:
            warehouse_skill = _make_warehouse_skill(warehouse, name)
            _make_artifact_skill(artifacts_dir, warehouse_skill)

        return warehouse, artifacts_dir, project_root

    def test_wires_all_skills_as_symlinks_and_generates_stubs(self, tmp_path):
        warehouse, artifacts_dir, project_root = self._setup(
            tmp_path, ["review", "plan"]
        )

        installed, errors = wire_skills_post_sync(project_root, artifacts_dir)

        assert not errors
        assert any("review" in e for e in installed)
        assert any("plan" in e for e in installed)

        for name in ["review", "plan"]:
            live = project_root / ".opencode" / "skills" / name / "SKILL.md"
            assert live.is_symlink()
            assert os.readlink(live) == str(
                (warehouse / "skills" / name / "SKILL.md").resolve()
            )
            stub = project_root / ".opencode" / "command" / f"{name}.md"
            assert stub.exists()

    def test_conflict_only_flagged_for_regular_file_differences(
        self, tmp_path, monkeypatch
    ):
        """Symlinks pointing to the wrong target must not be flagged as conflicts;
        they are repaired silently. Only regular files with divergent content
        count as conflicts needing user resolution."""
        warehouse, artifacts_dir, project_root = self._setup(tmp_path, ["review"])
        # Plant a divergent regular file in the live dir (old copy-based install).
        live_dir = project_root / ".opencode" / "skills" / "review"
        live_dir.mkdir(parents=True)
        (live_dir / "SKILL.md").write_text("user-edited content", encoding="utf-8")

        captured: dict[str, bool] = {}

        def fake_resolve_conflict(*, force, preserve, has_conflicts):
            captured["has_conflicts"] = has_conflicts
            from beacon.utils.interaction import OverwriteDecision

            return OverwriteDecision.PROCEED

        monkeypatch.setattr(
            "beacon.domains.artifact.skill.resolve_conflict",
            fake_resolve_conflict,
        )

        wire_skills_post_sync(project_root, artifacts_dir, force=True)

        assert captured.get("has_conflicts") is True

    def test_no_conflict_when_only_wrong_target_symlinks(self, tmp_path, monkeypatch):
        warehouse, artifacts_dir, project_root = self._setup(tmp_path, ["review"])
        # Plant a symlink pointing to the wrong target (simulating a stale repair case).
        live_dir = project_root / ".opencode" / "skills" / "review"
        live_dir.mkdir(parents=True)
        old_target = tmp_path / "old.md"
        old_target.write_text("old", encoding="utf-8")
        (live_dir / "SKILL.md").symlink_to(str(old_target))

        captured: dict[str, bool] = {}

        def fake_resolve_conflict(*, force, preserve, has_conflicts):
            captured["has_conflicts"] = has_conflicts
            from beacon.utils.interaction import OverwriteDecision

            return OverwriteDecision.PROCEED

        monkeypatch.setattr(
            "beacon.domains.artifact.skill.resolve_conflict",
            fake_resolve_conflict,
        )

        wire_skills_post_sync(project_root, artifacts_dir)

        # resolve_conflict should NOT have been called because symlinks aren't conflicts.
        assert "has_conflicts" not in captured
        # And the symlink should now point at the warehouse.
        live = live_dir / "SKILL.md"
        assert os.readlink(live) == str(
            (warehouse / "skills" / "review" / "SKILL.md").resolve()
        )

    def test_returns_empty_when_no_skills_synced(self, tmp_path):
        project_root = tmp_path / "project"
        artifacts_dir = project_root / ".agentic-beacon" / "artifacts"
        artifacts_dir.mkdir(parents=True)

        installed, errors = wire_skills_post_sync(project_root, artifacts_dir)

        assert installed == []
        assert errors == []


# ---------------------------------------------------------------------------
# Migration from pre-symlink copy-based installs
# ---------------------------------------------------------------------------


class TestCopyToSymlinkMigration:
    """Regression tests for the upgrade path from the old copy-based skill
    install to the new symlink-based model. Before this fix, divergent regular
    files at skill destinations were silently skipped by wire_skills_post_sync
    because resolve_conflict returned NEEDS_CONFIRMATION in non-interactive
    mode and the code defaulted to preserve=True."""

    def _setup_stale_copy(
        self, tmp_path: Path, stale_content: str = "stale copy from old abc"
    ) -> tuple[Path, Path, Path, Path]:
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()
        warehouse_skill = _make_warehouse_skill(warehouse, "review")
        artifacts_dir = tmp_path / "project" / ".agentic-beacon" / "artifacts"
        _make_artifact_skill(artifacts_dir, warehouse_skill)
        project_root = tmp_path / "project"
        # Plant a divergent regular file at the live destination (simulating an
        # older abc that copied content here instead of symlinking).
        live_dir = project_root / ".opencode" / "skills" / "review"
        live_dir.mkdir(parents=True)
        stale_file = live_dir / "SKILL.md"
        stale_file.write_text(stale_content, encoding="utf-8")
        assert not stale_file.is_symlink()
        return warehouse, artifacts_dir, project_root, stale_file

    def test_non_interactive_default_overwrites_stale_copies(self, tmp_path):
        """When no callback is provided (non-interactive sync, no --force/--preserve),
        stale regular-file copies must be replaced with warehouse symlinks.
        Regression for silent-skip bug."""
        warehouse, artifacts_dir, project_root, stale_file = self._setup_stale_copy(
            tmp_path
        )

        installed, errors = wire_skills_post_sync(project_root, artifacts_dir)

        assert errors == []
        assert stale_file.is_symlink()
        assert os.readlink(stale_file) == str(
            (warehouse / "skills" / "review" / "SKILL.md").resolve()
        )
        assert any("review" in e and "opencode" in e for e in installed)

    def test_interactive_callback_accepting_overwrites(self, tmp_path):
        warehouse, artifacts_dir, project_root, stale_file = self._setup_stale_copy(
            tmp_path
        )
        captured: dict[str, list[str]] = {}

        def callback(paths: list[str]) -> bool:
            captured["paths"] = paths
            return True

        wire_skills_post_sync(
            project_root, artifacts_dir, skill_conflict_callback=callback
        )

        assert captured.get("paths") is not None
        assert any(str(stale_file) in p for p in captured["paths"])
        assert stale_file.is_symlink()

    def test_interactive_callback_rejecting_preserves_local(self, tmp_path):
        warehouse, artifacts_dir, project_root, stale_file = self._setup_stale_copy(
            tmp_path, stale_content="my precious local edit"
        )

        def callback(paths: list[str]) -> bool:
            return False

        wire_skills_post_sync(
            project_root, artifacts_dir, skill_conflict_callback=callback
        )

        # Local file preserved; still a regular file with the user's content.
        assert not stale_file.is_symlink()
        assert stale_file.read_text(encoding="utf-8") == "my precious local edit"

    def test_preserve_flag_skips_without_calling_callback(self, tmp_path):
        warehouse, artifacts_dir, project_root, stale_file = self._setup_stale_copy(
            tmp_path, stale_content="keep me"
        )
        callback_called = False

        def callback(paths: list[str]) -> bool:
            nonlocal callback_called
            callback_called = True
            return True

        wire_skills_post_sync(
            project_root,
            artifacts_dir,
            preserve=True,
            skill_conflict_callback=callback,
        )

        assert callback_called is False
        assert not stale_file.is_symlink()
        assert stale_file.read_text(encoding="utf-8") == "keep me"

    def test_force_overwrites_without_calling_callback(self, tmp_path):
        warehouse, artifacts_dir, project_root, stale_file = self._setup_stale_copy(
            tmp_path
        )
        callback_called = False

        def callback(paths: list[str]) -> bool:
            nonlocal callback_called
            callback_called = True
            return False  # would reject if called

        wire_skills_post_sync(
            project_root,
            artifacts_dir,
            force=True,
            skill_conflict_callback=callback,
        )

        assert callback_called is False
        assert stale_file.is_symlink()

    def test_identical_content_is_not_a_conflict(self, tmp_path):
        """A regular file whose content happens to match the warehouse is not a
        conflict — no callback needed, just silently upgrade to symlink."""
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()
        warehouse_skill = _make_warehouse_skill(warehouse, "review")
        artifacts_dir = tmp_path / "project" / ".agentic-beacon" / "artifacts"
        _make_artifact_skill(artifacts_dir, warehouse_skill)
        project_root = tmp_path / "project"
        live_dir = project_root / ".opencode" / "skills" / "review"
        live_dir.mkdir(parents=True)
        # Copy the warehouse content byte-for-byte.
        warehouse_content = (warehouse / "skills" / "review" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        stale_file = live_dir / "SKILL.md"
        stale_file.write_text(warehouse_content, encoding="utf-8")

        callback_called = False

        def callback(paths: list[str]) -> bool:
            nonlocal callback_called
            callback_called = True
            return True

        wire_skills_post_sync(
            project_root, artifacts_dir, skill_conflict_callback=callback
        )

        assert callback_called is False
        assert stale_file.is_symlink()
