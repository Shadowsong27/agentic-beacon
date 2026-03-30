"""Tests for abc delta command.

Following TDD workflow for tasks 9.1-9.7.
"""

import pytest
from beacon.cli import main
from click.testing import CliRunner


@pytest.fixture
def project_with_artifacts(temp_dir, valid_warehouse):
    """Create a project connected to warehouse with synced artifacts."""
    project = temp_dir / "project"
    project.mkdir()

    beacon_dir = project / ".agentic-beacon"
    beacon_dir.mkdir()

    # Create config.toml
    config = beacon_dir / "config.toml"
    config.write_text(f'[warehouse]\nlocal_path = "{valid_warehouse}"\n')

    # Create beacon.yaml
    beacon_yaml = beacon_dir / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge:\n    - knowledge/doc.md\n  skills: []\n  contexts: []\n"
    )

    # Create warehouse file
    (valid_warehouse / "knowledge" / "doc.md").write_text("# Warehouse content")

    # Create synced artifact (identical)
    artifacts_dir = beacon_dir / "artifacts"
    (artifacts_dir / "knowledge").mkdir(parents=True)
    (artifacts_dir / "knowledge" / "doc.md").write_text("# Warehouse content")

    return project


def test_delta_no_differences(project_with_artifacts, monkeypatch):
    """TC2: No changes → "No differences found"."""
    runner = CliRunner()
    monkeypatch.chdir(project_with_artifacts)
    result = runner.invoke(main, ["delta"])
    assert result.exit_code == 0
    assert "No differences found" in result.output


def test_delta_modified_file(project_with_artifacts, monkeypatch):
    """TC1: 1 modified file → Shows summary with modified entry."""
    # Modify local file
    artifacts_dir = project_with_artifacts / ".agentic-beacon" / "artifacts"
    (artifacts_dir / "knowledge" / "doc.md").write_text("# Modified locally")

    runner = CliRunner()
    monkeypatch.chdir(project_with_artifacts)
    result = runner.invoke(main, ["delta"])
    assert result.exit_code == 0
    assert "Modified" in result.output


def test_delta_no_warehouse_connected(temp_dir, monkeypatch):
    """TC8: No warehouse connected → Error."""
    project = temp_dir / "project"
    project.mkdir()
    (project / ".agentic-beacon").mkdir()

    runner = CliRunner()
    monkeypatch.chdir(project)
    result = runner.invoke(main, ["delta"])
    assert result.exit_code == 1
    assert "No warehouse connected" in result.output


def test_delta_no_beacon_yaml(temp_dir, valid_warehouse, monkeypatch):
    """TC9: No beacon.yaml → Error."""
    project = temp_dir / "project"
    project.mkdir()
    beacon_dir = project / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "config.toml").write_text(
        f'[warehouse]\nlocal_path = "{valid_warehouse}"\n'
    )

    runner = CliRunner()
    monkeypatch.chdir(project)
    result = runner.invoke(main, ["delta"])
    assert result.exit_code == 1
    assert "No beacon.yaml found" in result.output


def test_delta_shows_untracked_local_skill(temp_dir, valid_warehouse, monkeypatch):
    """abc delta shows a locally-present skill not registered in beacon.yaml as Added."""
    project = temp_dir / "project"
    project.mkdir()
    beacon_dir = project / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "config.toml").write_text(
        f'[warehouse]\nlocal_path = "{valid_warehouse}"\n'
    )
    # beacon.yaml has NO skills entries
    (beacon_dir / "beacon.yaml").write_text(
        "artifacts:\n  knowledge: []\n  skills: []\n  contexts: []\n"
    )

    # Create opsx-handoff skill locally (untracked — not in beacon.yaml, not in warehouse)
    skill_dir = beacon_dir / "artifacts" / "skills" / "opsx-handoff"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# opsx-handoff\n")

    runner = CliRunner()
    monkeypatch.chdir(project)
    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 0
    assert "opsx-handoff" in result.output
    assert "Added" in result.output


def test_delta_no_beacon_dir(temp_dir, monkeypatch):
    """No .agentic-beacon directory → Error."""
    project = temp_dir / "project"
    project.mkdir()

    runner = CliRunner()
    monkeypatch.chdir(project)
    result = runner.invoke(main, ["delta"])
    assert result.exit_code == 1
    assert "No .agentic-beacon" in result.output


# ---------------------------------------------------------------------------
# Skills: live agent path comparison (bug fix)
# abc delta must compare skills against the live agent dirs, not the snapshot.
# ---------------------------------------------------------------------------


@pytest.fixture
def project_with_skill(temp_dir, valid_warehouse):
    """Project with a synced skill and an opencode.json agent config."""
    project = temp_dir / "project"
    project.mkdir()

    beacon_dir = project / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "config.toml").write_text(
        f'[warehouse]\nlocal_path = "{valid_warehouse}"\n'
    )
    (beacon_dir / "beacon.yaml").write_text(
        "artifacts:\n"
        "  knowledge: []\n"
        "  skills:\n"
        "    - skills/my-skill/SKILL.md\n"
        "  contexts: []\n"
    )

    # Add skill to warehouse
    skill_wh = valid_warehouse / "skills" / "my-skill"
    skill_wh.mkdir(parents=True)
    (skill_wh / "SKILL.md").write_text("# Warehouse version\n")

    # Artifact snapshot (identical to warehouse)
    (beacon_dir / "artifacts" / "skills" / "my-skill").mkdir(parents=True)
    (beacon_dir / "artifacts" / "skills" / "my-skill" / "SKILL.md").write_text(
        "# Warehouse version\n"
    )

    # opencode.json marks this as an opencode project
    (project / "opencode.json").write_text("{}")

    return project


def test_delta_skill_identical_live_shows_no_differences(
    project_with_skill, valid_warehouse, monkeypatch
):
    """abc delta reports no differences when live skill matches warehouse."""
    project = project_with_skill

    # Install the live skill (identical to warehouse)
    live_dir = project / ".opencode" / "skills" / "my-skill"
    live_dir.mkdir(parents=True)
    (live_dir / "SKILL.md").write_text("# Warehouse version\n")

    runner = CliRunner()
    monkeypatch.chdir(project)
    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 0
    assert "No differences" in result.output


def test_delta_skill_modified_live_shows_modified(
    project_with_skill, valid_warehouse, monkeypatch
):
    """abc delta reports Modified when live skill differs from warehouse."""
    project = project_with_skill

    # Install a MODIFIED version in the live dir
    live_dir = project / ".opencode" / "skills" / "my-skill"
    live_dir.mkdir(parents=True)
    (live_dir / "SKILL.md").write_text("# Locally edited version\n")

    runner = CliRunner()
    monkeypatch.chdir(project)
    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 0
    assert "Modified" in result.output
    assert "skills/my-skill/SKILL.md" in result.output


def test_delta_skill_snapshot_identical_but_live_modified_shows_modified(
    project_with_skill, valid_warehouse, monkeypatch
):
    """Regression: delta reports Modified even when artifact snapshot is identical.

    This is the core bug scenario — the snapshot matches warehouse but the live
    agent copy has been edited. Without the fix, delta would silently show
    'No differences'.
    """
    project = project_with_skill

    # Snapshot is identical to warehouse (no drift there)
    # but live dir has a different version
    live_dir = project / ".opencode" / "skills" / "my-skill"
    live_dir.mkdir(parents=True)
    (live_dir / "SKILL.md").write_text("# Added a new guardrail\n")

    runner = CliRunner()
    monkeypatch.chdir(project)
    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 0
    assert "Modified" in result.output
    assert "skills/my-skill/SKILL.md" in result.output


def test_delta_skill_shows_per_agent_breakdown_in_output(
    temp_dir, valid_warehouse, monkeypatch
):
    """abc delta shows per-agent status for modified skills with multiple agents."""
    project = temp_dir / "project"
    project.mkdir()

    beacon_dir = project / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "config.toml").write_text(
        f'[warehouse]\nlocal_path = "{valid_warehouse}"\n'
    )
    (beacon_dir / "beacon.yaml").write_text(
        "artifacts:\n"
        "  knowledge: []\n"
        "  skills:\n"
        "    - skills/my-skill/SKILL.md\n"
        "  contexts: []\n"
    )

    skill_wh = valid_warehouse / "skills" / "my-skill"
    skill_wh.mkdir(parents=True)
    (skill_wh / "SKILL.md").write_text("# Warehouse\n")

    (beacon_dir / "artifacts" / "skills" / "my-skill").mkdir(parents=True)
    (beacon_dir / "artifacts" / "skills" / "my-skill" / "SKILL.md").write_text(
        "# Warehouse\n"
    )

    # Both agents configured
    (project / "opencode.json").write_text("{}")
    (project / ".claude").mkdir()

    # opencode: modified
    oc_live = project / ".opencode" / "skills" / "my-skill"
    oc_live.mkdir(parents=True)
    (oc_live / "SKILL.md").write_text("# OpenCode edit\n")

    # claudecode: identical
    cc_live = project / ".claude" / "skills" / "my-skill"
    cc_live.mkdir(parents=True)
    (cc_live / "SKILL.md").write_text("# Warehouse\n")

    runner = CliRunner()
    monkeypatch.chdir(project)
    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 0
    assert "Modified" in result.output
    assert "opencode" in result.output
    assert "claudecode" in result.output
    # opencode modified, claudecode identical
    assert "modified" in result.output.lower()
    assert "identical" in result.output.lower()


def test_delta_skill_no_live_dir_reports_missing(
    project_with_skill, valid_warehouse, monkeypatch
):
    """abc delta reports Missing when skill is in warehouse but not installed in live dir."""
    project = project_with_skill
    # opencode.json exists (agent detected) but .opencode/skills/ dir is absent

    runner = CliRunner()
    monkeypatch.chdir(project)
    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 0
    assert "Missing" in result.output
    assert "skills/my-skill/SKILL.md" in result.output


def test_delta_skill_detailed_diff_uses_live_path(
    project_with_skill, valid_warehouse, monkeypatch
):
    """abc delta <file> diffs warehouse against the live agent copy, not the snapshot."""
    project = project_with_skill

    # Snapshot identical to warehouse
    # Live has extra content
    live_dir = project / ".opencode" / "skills" / "my-skill"
    live_dir.mkdir(parents=True)
    (live_dir / "SKILL.md").write_text(
        "# Warehouse version\n\n## New Section\nExtra.\n"
    )

    runner = CliRunner()
    monkeypatch.chdir(project)
    result = runner.invoke(main, ["delta", "skills/my-skill/SKILL.md", "--no-color"])

    assert result.exit_code == 0
    assert "New Section" in result.output or "Extra" in result.output


# ---------------------------------------------------------------------------
# Bug #52: per-agent breakdown for MISSING and ADDED (not just MODIFIED)
# ---------------------------------------------------------------------------


def test_delta_summary_shows_per_agent_breakdown_for_missing_skill(
    temp_dir, valid_warehouse, monkeypatch
):
    """abc delta summary shows per-agent detail when rollup status is MISSING."""
    project = temp_dir / "project"
    project.mkdir()
    beacon_dir = project / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "config.toml").write_text(
        f'[warehouse]\nlocal_path = "{valid_warehouse}"\n'
    )
    (beacon_dir / "beacon.yaml").write_text(
        "artifacts:\n"
        "  knowledge: []\n"
        "  skills:\n"
        "    - skills/my-skill/SKILL.md\n"
        "  contexts: []\n"
    )

    # Skill in warehouse
    skill_wh = valid_warehouse / "skills" / "my-skill"
    skill_wh.mkdir(parents=True)
    (skill_wh / "SKILL.md").write_text("# Warehouse\n")

    # Both agents detected but neither has the skill installed
    (project / "opencode.json").write_text("{}")
    (project / ".claude").mkdir()
    # Agent skill dirs exist but are empty (skill not synced)
    (project / ".opencode" / "skills").mkdir(parents=True)
    (project / ".claude" / "skills").mkdir(parents=True)

    runner = CliRunner()
    monkeypatch.chdir(project)
    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 0
    assert "Missing" in result.output
    assert "skills/my-skill/SKILL.md" in result.output
    # Per-agent breakdown should appear
    assert "opencode" in result.output
    assert "claudecode" in result.output


def test_delta_summary_shows_per_agent_breakdown_for_added_skill(
    temp_dir, valid_warehouse, monkeypatch
):
    """abc delta summary shows per-agent detail when rollup status is ADDED."""
    project = temp_dir / "project"
    project.mkdir()
    beacon_dir = project / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "config.toml").write_text(
        f'[warehouse]\nlocal_path = "{valid_warehouse}"\n'
    )
    (beacon_dir / "beacon.yaml").write_text(
        "artifacts:\n"
        "  knowledge: []\n"
        "  skills:\n"
        "    - skills/my-skill/SKILL.md\n"
        "  contexts: []\n"
    )

    # Skill NOT in warehouse (will be ADDED)
    # Both agents have it installed
    (project / "opencode.json").write_text("{}")
    (project / ".claude").mkdir()
    content = "# Local only\n"
    (project / ".opencode" / "skills" / "my-skill").mkdir(parents=True)
    (project / ".opencode" / "skills" / "my-skill" / "SKILL.md").write_text(content)
    (project / ".claude" / "skills" / "my-skill").mkdir(parents=True)
    (project / ".claude" / "skills" / "my-skill" / "SKILL.md").write_text(content)

    runner = CliRunner()
    monkeypatch.chdir(project)
    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 0
    assert "Added" in result.output
    assert "skills/my-skill/SKILL.md" in result.output
    # Per-agent breakdown should appear
    assert "opencode" in result.output
    assert "claudecode" in result.output


def test_delta_detailed_diff_multi_agent_shows_both_sections(
    temp_dir, valid_warehouse, monkeypatch
):
    """abc delta <file> shows a diff section for each agent with a differing version."""
    project = temp_dir / "project"
    project.mkdir()
    beacon_dir = project / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "config.toml").write_text(
        f'[warehouse]\nlocal_path = "{valid_warehouse}"\n'
    )
    (beacon_dir / "beacon.yaml").write_text(
        "artifacts:\n"
        "  knowledge: []\n"
        "  skills:\n"
        "    - skills/my-skill/SKILL.md\n"
        "  contexts: []\n"
    )

    skill_wh = valid_warehouse / "skills" / "my-skill"
    skill_wh.mkdir(parents=True)
    (skill_wh / "SKILL.md").write_text("# Warehouse\n")

    (beacon_dir / "artifacts" / "skills" / "my-skill").mkdir(parents=True)
    (beacon_dir / "artifacts" / "skills" / "my-skill" / "SKILL.md").write_text(
        "# Warehouse\n"
    )

    # Both agents with different edits
    (project / "opencode.json").write_text("{}")
    (project / ".claude").mkdir()
    (project / ".opencode" / "skills" / "my-skill").mkdir(parents=True)
    (project / ".opencode" / "skills" / "my-skill" / "SKILL.md").write_text(
        "# OpenCode edit\n"
    )
    (project / ".claude" / "skills" / "my-skill").mkdir(parents=True)
    (project / ".claude" / "skills" / "my-skill" / "SKILL.md").write_text(
        "# Claude edit\n"
    )

    runner = CliRunner()
    monkeypatch.chdir(project)
    result = runner.invoke(main, ["delta", "skills/my-skill/SKILL.md", "--no-color"])

    assert result.exit_code == 0
    # Both agent sections should appear
    assert "opencode" in result.output
    assert "claudecode" in result.output
    # Content from both diffs
    assert "OpenCode edit" in result.output
    assert "Claude edit" in result.output


# ---------------------------------------------------------------------------
# Regression: .sync-state must not appear as an untracked artifact
# ---------------------------------------------------------------------------


def test_delta_sync_state_not_shown_as_untracked(project_with_artifacts, monkeypatch):
    """Regression: .sync-state is a framework metadata file and must never appear
    in the delta untracked section, even though it lives inside artifacts_dir."""
    artifacts_dir = project_with_artifacts / ".agentic-beacon" / "artifacts"
    # Simulate what abc sync writes after a successful sync
    (artifacts_dir / ".sync-state").write_text("abc123\n")

    runner = CliRunner()
    monkeypatch.chdir(project_with_artifacts)
    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 0
    assert ".sync-state" not in result.output
