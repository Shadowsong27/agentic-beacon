"""Integration tests for abc sync soft block behavior.

TDD Test Cases (5.3/5.9):
- TC1: No conflicts → proceeds without prompt
- TC2: Conflicts, interactive, y → proceeds with overwrite
- TC3: Conflicts, interactive, N → exits 0, no files written
- TC4: Conflicts, non-interactive, no flags → exits 1 with conflict list
- TC5: Conflicts, --preserve → skips conflicting files, no prompt
- TC6: Conflicts, --force → overwrites without prompt
- TC7: --force and --preserve together → exits 1 with mutual-exclusion error

TDD Test Cases for skill wiring soft-block (5.10):
- TC1: Skill wiring target does not exist → writes without prompt
- TC2: Skill wiring target identical → skips silently (not a conflict)
- TC3: Skill wiring target differs, interactive, y → overwrites
- TC4: Skill wiring target differs, --preserve → skips silently
- TC5: Skill wiring target differs, --force → overwrites without prompt
"""

import json
from pathlib import Path

import pytest
from beacon.cli import main
from beacon.domains.artifact.skill import wire_skills_post_sync
from click.testing import CliRunner

SAMPLE_SKILL_MD = """\
---
name: my-skill
description: A test skill
---
# Skill: My Skill
"""

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def warehouse_with_conflict(tmp_path):
    """A warehouse with a knowledge file that conflicts with a local artifact."""
    wh = tmp_path / "warehouse"
    wh.mkdir()
    (wh / "README.md").write_text("# Warehouse")
    (wh / "agents").mkdir()
    (wh / "docs").mkdir()
    (wh / "contexts").mkdir()
    (wh / "knowledge").mkdir()
    (wh / "skills").mkdir()
    (wh / "knowledge" / "file.md").write_text("# Warehouse version\n")
    return wh


@pytest.fixture
def connected_project_with_conflict(tmp_path, warehouse_with_conflict, monkeypatch):
    """A project connected to warehouse_with_conflict that has a local conflict."""
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    runner = CliRunner()
    # Connect
    runner.invoke(
        main, ["warehouse", "connect", "--path", str(warehouse_with_conflict)]
    )
    # Write beacon.yaml
    beacon_yaml = project / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge:\n    - knowledge/file.md\n  skills: []\n  contexts: []\n"
    )
    # Sync first
    runner.invoke(main, ["sync", "--skip-git-check"])
    # Modify local artifact (create conflict)
    local_file = project / ".agentic-beacon" / "artifacts" / "knowledge" / "file.md"
    local_file.write_text("# Locally modified\n")
    return project, warehouse_with_conflict, runner


# ---------------------------------------------------------------------------
# abc sync soft-block tests (5.3)
# ---------------------------------------------------------------------------


def test_tc1_no_conflicts_proceeds(tmp_path, monkeypatch):
    """TC1: No conflicts → proceeds without prompt (no blocking)."""
    wh = tmp_path / "warehouse"
    wh.mkdir()
    (wh / "README.md").write_text("# Warehouse")
    (wh / "agents").mkdir()
    (wh / "docs").mkdir()
    (wh / "contexts").mkdir()
    (wh / "knowledge").mkdir()
    (wh / "skills").mkdir()
    (wh / "knowledge" / "file.md").write_text("# Same content\n")

    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    runner = CliRunner()
    runner.invoke(main, ["warehouse", "connect", "--path", str(wh)])
    beacon_yaml = project / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge:\n    - knowledge/file.md\n  skills: []\n  contexts: []\n"
    )
    # First sync (no conflict)
    result = runner.invoke(main, ["sync", "--skip-git-check"])
    assert result.exit_code == 0

    # Second sync — artifact now identical to warehouse, no conflict
    result2 = runner.invoke(main, ["sync", "--skip-git-check"])
    assert result2.exit_code == 0
    assert "Warning" not in result2.output


def test_tc4_conflicts_noninteractive_exits1(connected_project_with_conflict):
    """TC4: Conflicts, non-interactive, no flags → exits 1 with conflict list."""
    project, warehouse, runner = connected_project_with_conflict

    result = runner.invoke(main, ["sync", "--skip-git-check"])
    assert result.exit_code == 1
    assert "Warning" in result.output or "Non-interactive" in result.output


def test_tc5_conflicts_preserve_skips(connected_project_with_conflict):
    """TC5: Conflicts, --preserve → skips conflicting files, no prompt."""
    project, warehouse, runner = connected_project_with_conflict

    result = runner.invoke(main, ["sync", "--preserve", "--skip-git-check"])
    assert result.exit_code == 0
    # Local file should still be modified (not overwritten)
    local_file = project / ".agentic-beacon" / "artifacts" / "knowledge" / "file.md"
    assert "Locally modified" in local_file.read_text()


def test_tc6_conflicts_force_overwrites(connected_project_with_conflict):
    """TC6: Conflicts, --force → overwrites without prompt."""
    project, warehouse, runner = connected_project_with_conflict

    result = runner.invoke(main, ["sync", "--force", "--skip-git-check"])
    assert result.exit_code == 0
    # Local file should have been overwritten with warehouse content
    local_file = project / ".agentic-beacon" / "artifacts" / "knowledge" / "file.md"
    assert "Warehouse version" in local_file.read_text()


def test_tc7_force_and_preserve_mutual_exclusion(tmp_path, monkeypatch):
    """TC7: --force and --preserve together → exits 1 with mutual-exclusion error."""
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    runner = CliRunner()
    result = runner.invoke(main, ["sync", "--force", "--preserve"])
    assert result.exit_code == 1
    assert "mutually exclusive" in result.output.lower()


# ---------------------------------------------------------------------------
# abc install soft-block tests (10.3 mutual exclusion via 5.4)
# ---------------------------------------------------------------------------


def test_install_force_and_preserve_mutual_exclusion(tmp_path, monkeypatch):
    """--force and --preserve together on install → exits 1."""
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    runner = CliRunner()
    result = runner.invoke(
        main, ["install", "knowledge/test.md", "--force", "--preserve"]
    )
    assert result.exit_code == 1
    assert "mutually exclusive" in result.output.lower()


# ---------------------------------------------------------------------------
# Skill wiring soft-block tests (5.10 / 5.5)
# ---------------------------------------------------------------------------


def _make_project_with_skill(
    tmp_path: Path, live_content: str | None = None
) -> tuple[Path, Path]:
    """Create a project with a synced skill and optionally a live installed version."""
    project = tmp_path / "project"
    project.mkdir()
    artifacts_dir = project / ".agentic-beacon" / "artifacts"
    skill_dir = artifacts_dir / "skills" / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(SAMPLE_SKILL_MD)
    (project / "opencode.json").write_text(json.dumps({}))

    if live_content is not None:
        live_dir = project / ".opencode" / "skills" / "my-skill"
        live_dir.mkdir(parents=True)
        (live_dir / "SKILL.md").write_text(live_content)

    return project, artifacts_dir


def test_tc1_wiring_target_not_exist_writes(tmp_path):
    """TC1: Skill wiring target does not exist → writes without prompt."""
    project, artifacts_dir = _make_project_with_skill(tmp_path, live_content=None)

    installed, errors = wire_skills_post_sync(project, artifacts_dir)

    assert any("my-skill" in s for s in installed)
    assert errors == []
    assert (project / ".opencode" / "skills" / "my-skill" / "SKILL.md").exists()


def test_tc2_wiring_target_identical_skips(tmp_path):
    """TC2: Skill wiring target identical → skips silently (not a conflict)."""
    project, artifacts_dir = _make_project_with_skill(
        tmp_path, live_content=SAMPLE_SKILL_MD
    )

    installed, errors = wire_skills_post_sync(project, artifacts_dir)

    # No change needed — identical content, so nothing installed
    assert not any("my-skill" in s for s in installed)
    assert errors == []


def test_tc4_wiring_target_differs_preserve_skips(tmp_path):
    """TC4: Skill wiring target differs, --preserve → skips silently."""
    project, artifacts_dir = _make_project_with_skill(
        tmp_path, live_content="# User's local version\n"
    )

    installed, errors = wire_skills_post_sync(project, artifacts_dir, preserve=True)

    # Preserve skips conflicting wiring
    assert not any("my-skill" in s for s in installed)
    # Live version should be unchanged
    live = project / ".opencode" / "skills" / "my-skill" / "SKILL.md"
    assert "User's local version" in live.read_text()


def test_tc5_wiring_target_differs_force_overwrites(tmp_path):
    """TC5: Skill wiring target differs, --force → overwrites without prompt."""
    project, artifacts_dir = _make_project_with_skill(
        tmp_path, live_content="# User's local version\n"
    )

    installed, errors = wire_skills_post_sync(project, artifacts_dir, force=True)

    assert any("my-skill" in s for s in installed)
    live = project / ".opencode" / "skills" / "my-skill" / "SKILL.md"
    assert "Skill: My Skill" in live.read_text()
