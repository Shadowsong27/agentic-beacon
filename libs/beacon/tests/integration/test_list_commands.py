"""Tests for abc list and abc warehouse list commands."""

import os
import subprocess

import pytest
from beacon.cli.main import main
from click.testing import CliRunner


def _git_env():
    return {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "t@t.local",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "t@t.local",
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def warehouse_with_artifacts(tmp_path):
    """A valid warehouse with contexts, knowledge, and skills."""
    wh = tmp_path / "warehouse"
    wh.mkdir()
    (wh / "README.md").write_text("# Warehouse")
    (wh / "agents").mkdir()
    (wh / "docs").mkdir()

    (wh / "contexts").mkdir()
    (wh / "contexts" / "AGENTS.md").write_text("# Context")
    (wh / "contexts" / "python").mkdir()
    (wh / "contexts" / "python" / "standards.md").write_text("# Python Standards")

    (wh / "skills").mkdir()
    skill_dir = wh / "skills" / "code-review"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nrequires:\n  contexts: []\n---\n# Skill: Code Review"
    )

    # Init git and commit files (required by sync)
    env = _git_env()
    subprocess.run(["git", "init"], cwd=wh, env=env, check=True, capture_output=True)
    subprocess.run(
        ["git", "add", "."], cwd=wh, env=env, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=wh,
        env=env,
        check=True,
        capture_output=True,
    )

    return wh


@pytest.fixture
def connected_project(tmp_path, warehouse_with_artifacts, monkeypatch):
    """A project connected to warehouse_with_artifacts."""
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    runner = CliRunner()
    result = runner.invoke(
        main, ["warehouse", "connect", "--path", str(warehouse_with_artifacts)]
    )
    assert result.exit_code == 0, f"connect failed:\n{result.output}"

    return project, warehouse_with_artifacts, runner


@pytest.fixture
def synced_project(connected_project):
    """A connected project with artifacts synced from the warehouse."""
    project, warehouse, runner = connected_project

    # Write beacon.yaml
    beacon_yaml = project / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  contexts:\n"
        "    - contexts/AGENTS.md\n"
        "    - contexts/python/standards.md\n"
        "  skills:\n"
        "    - skills/code-review/\n"
        "\n"
    )

    result = runner.invoke(main, ["sync"])
    assert result.exit_code == 0, f"sync failed:\n{result.output}"

    return project, warehouse, runner


# ---------------------------------------------------------------------------
# abc warehouse list — unit / isolated tests
# ---------------------------------------------------------------------------


def test_warehouse_list_requires_connected_project(runner, tmp_path, monkeypatch):
    """abc warehouse list exits non-zero when no config.toml exists."""
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    result = runner.invoke(main, ["warehouse", "list"])

    assert result.exit_code != 0
    assert "No warehouse connected" in result.output


def test_warehouse_list_all_types(connected_project):
    """abc warehouse list shows all sections."""
    project, warehouse, runner = connected_project

    result = runner.invoke(main, ["warehouse", "list"])

    assert result.exit_code == 0
    assert "Contexts" in result.output
    assert "Skills" in result.output


def test_warehouse_list_filter_contexts_second(connected_project):
    """abc warehouse list contexts shows only contexts section."""
    project, warehouse, runner = connected_project

    result = runner.invoke(main, ["warehouse", "list", "contexts"])

    assert result.exit_code == 0
    assert "Contexts" in result.output
    assert "Skills" not in result.output


def test_warehouse_list_filter_skills(connected_project):
    """abc warehouse list skills shows only skills section."""
    project, warehouse, runner = connected_project

    result = runner.invoke(main, ["warehouse", "list", "skills"])

    assert result.exit_code == 0
    assert "Skills" in result.output
    assert "Contexts" not in result.output


def test_warehouse_list_filter_contexts(connected_project):
    """abc warehouse list contexts shows only contexts section."""
    project, warehouse, runner = connected_project

    result = runner.invoke(main, ["warehouse", "list", "contexts"])

    assert result.exit_code == 0
    assert "Contexts" in result.output
    assert "Skills" not in result.output


def test_warehouse_list_shows_artifact_paths(connected_project):
    """abc warehouse list shows actual artifact paths from the warehouse."""
    project, warehouse, runner = connected_project

    result = runner.invoke(main, ["warehouse", "list"])

    assert result.exit_code == 0
    assert "contexts/AGENTS.md" in result.output


def test_warehouse_list_empty_warehouse(runner, tmp_path, monkeypatch):
    """abc warehouse list handles empty warehouse sections gracefully."""
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    # Create an empty but valid warehouse
    wh = tmp_path / "empty-warehouse"
    wh.mkdir()
    (wh / "README.md").write_text("# Empty Warehouse")
    (wh / "agents").mkdir()
    (wh / "docs").mkdir()
    (wh / "contexts").mkdir()
    (wh / "skills").mkdir()

    connect_result = runner.invoke(main, ["warehouse", "connect", "--path", str(wh)])
    assert connect_result.exit_code == 0

    result = runner.invoke(main, ["warehouse", "list"])

    assert result.exit_code == 0
    assert "No artifacts found" in result.output or result.output.strip() != ""


def test_warehouse_list_shown_in_warehouse_help(runner):
    """abc warehouse --help lists the list subcommand."""
    result = runner.invoke(main, ["warehouse", "--help"])

    assert result.exit_code == 0
    assert "list" in result.output


# ---------------------------------------------------------------------------
# abc list — unit / isolated tests
# ---------------------------------------------------------------------------


def test_list_project_no_artifacts_dir(runner, tmp_path, monkeypatch):
    """abc list exits non-zero when .agentic-beacon/artifacts/ does not exist."""
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    result = runner.invoke(main, ["list"])

    assert result.exit_code != 0
    assert "No synced artifacts" in result.output


def test_list_project_all_types(synced_project):
    """abc list shows all synced artifact sections."""
    project, warehouse, runner = synced_project

    result = runner.invoke(main, ["list"])

    assert result.exit_code == 0
    assert "Contexts" in result.output
    assert "Skills" in result.output


def test_list_project_filter_contexts_second(synced_project):
    """abc list contexts shows only synced contexts."""
    project, warehouse, runner = synced_project

    result = runner.invoke(main, ["list", "contexts"])

    assert result.exit_code == 0
    assert "Contexts" in result.output
    assert "Skills" not in result.output


def test_list_project_filter_skills(synced_project):
    """abc list skills shows only synced skills."""
    project, warehouse, runner = synced_project

    result = runner.invoke(main, ["list", "skills"])

    assert result.exit_code == 0
    assert "Skills" in result.output
    assert "Contexts" not in result.output


def test_list_project_filter_contexts(synced_project):
    """abc list contexts shows only synced contexts."""
    project, warehouse, runner = synced_project

    result = runner.invoke(main, ["list", "contexts"])

    assert result.exit_code == 0
    assert "Contexts" in result.output
    assert "Skills" not in result.output


def test_list_project_shows_artifact_paths(synced_project):
    """abc list shows actual relative file paths under each section."""
    project, warehouse, runner = synced_project

    result = runner.invoke(main, ["list"])

    assert result.exit_code == 0
    assert "contexts/python/standards.md" in result.output
    assert "skills/code-review/SKILL.md" in result.output
    assert "contexts/AGENTS.md" in result.output


def test_list_project_empty_artifacts_dir(runner, tmp_path, monkeypatch):
    """abc list shows helpful message when artifacts dir exists but is empty."""
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    # Create empty artifacts dir
    (project / ".agentic-beacon" / "artifacts").mkdir(parents=True)

    result = runner.invoke(main, ["list"])

    assert result.exit_code == 0
    assert "No artifacts found" in result.output


# ---------------------------------------------------------------------------
# Integration: warehouse list end-to-end
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_integration_warehouse_list_skills_filter(connected_project):
    """Integration: abc warehouse list skills returns only skills after connection."""
    project, warehouse, runner = connected_project

    result = runner.invoke(main, ["warehouse", "list", "skills"])

    assert result.exit_code == 0
    assert "Skills" in result.output
    assert "code-review" in result.output


@pytest.mark.integration
def test_integration_list_after_sync(synced_project):
    """Integration: abc list shows all synced artifacts after abc sync."""
    project, warehouse, runner = synced_project

    result = runner.invoke(main, ["list"])

    assert result.exit_code == 0
    assert "contexts/python/standards.md" in result.output
    assert "skills/code-review/SKILL.md" in result.output
    assert "contexts/AGENTS.md" in result.output


# ---------------------------------------------------------------------------
# agents surfacing — Phase 2 tasks 2.2 and 2.3
# ---------------------------------------------------------------------------


def test_warehouse_list_agents_section(tmp_path, monkeypatch):
    """TC1: abc warehouse list → agents section shown alongside other types."""
    from click.testing import CliRunner

    runner = CliRunner()
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    wh = tmp_path / "warehouse"
    wh.mkdir()
    (wh / "README.md").write_text("# Warehouse")
    (wh / "agents").mkdir()
    (wh / "agents" / "code-reviewer.md").write_text(
        "---\nname: code-reviewer\n---\n# Agent"
    )
    (wh / "agents" / "agents.yaml").write_text("code-reviewer:\n  skills: []\n")
    (wh / "docs").mkdir()
    (wh / "contexts").mkdir()
    (wh / "skills").mkdir()

    connect = runner.invoke(main, ["warehouse", "connect", "--path", str(wh)])
    assert connect.exit_code == 0

    result = runner.invoke(main, ["warehouse", "list"])
    assert result.exit_code == 0
    assert "Agent" in result.output or "agent" in result.output.lower()


def test_warehouse_list_filter_agents(tmp_path, monkeypatch):
    """TC2: abc warehouse list agents → only agents section shown."""
    from click.testing import CliRunner

    runner = CliRunner()
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    wh = tmp_path / "warehouse"
    wh.mkdir()
    (wh / "README.md").write_text("# Warehouse")
    (wh / "agents").mkdir()
    (wh / "agents" / "code-reviewer.md").write_text(
        "---\nname: code-reviewer\n---\n# Agent"
    )
    (wh / "agents" / "agents.yaml").write_text("code-reviewer:\n  skills: []\n")
    (wh / "docs").mkdir()
    (wh / "contexts").mkdir()
    (wh / "skills").mkdir()

    connect = runner.invoke(main, ["warehouse", "connect", "--path", str(wh)])
    assert connect.exit_code == 0

    result = runner.invoke(main, ["warehouse", "list", "agents"])
    assert result.exit_code == 0
    assert "Contexts" not in result.output
    assert "Skills" not in result.output


def test_warehouse_list_agents_empty(tmp_path, monkeypatch):
    """TC3: Warehouse agents/ dir is empty → 'No agents found' message."""
    from click.testing import CliRunner

    runner = CliRunner()
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    wh = tmp_path / "warehouse"
    wh.mkdir()
    (wh / "README.md").write_text("# Warehouse")
    (wh / "agents").mkdir()
    (wh / "docs").mkdir()
    (wh / "contexts").mkdir()
    (wh / "skills").mkdir()

    connect = runner.invoke(main, ["warehouse", "connect", "--path", str(wh)])
    assert connect.exit_code == 0

    result = runner.invoke(main, ["warehouse", "list", "agents"])
    assert result.exit_code == 0
    assert "No agents found" in result.output


def test_list_agents_shows_project_artifacts(tmp_path, monkeypatch):
    """TC1: abc list agents → shows agent files from .agentic-beacon/artifacts/agents/.

    PER-113: agents are project-scoped. abc list agents reads from the project
    artifacts dir, not from global ~/.config/opencode/agents/ or ~/.claude/agents/.
    """
    from click.testing import CliRunner

    runner = CliRunner()
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    # Create a fake warehouse agent file to use as the symlink target
    wh_agent = tmp_path / "warehouse" / "agents" / "code-reviewer.md"
    wh_agent.parent.mkdir(parents=True)
    wh_agent.write_text("---\nname: code-reviewer\n---\n# Code Reviewer\n")

    # Plant an agent artifact symlink (normally created by abc sync)
    agents_artifacts = project / ".agentic-beacon" / "artifacts" / "agents"
    agents_artifacts.mkdir(parents=True)
    (agents_artifacts / "code-reviewer.md").symlink_to(wh_agent)

    result = runner.invoke(main, ["list", "agents"])
    assert result.exit_code == 0
    assert "code-reviewer" in result.output


def test_list_agents_no_artifacts_dir_needed(tmp_path, monkeypatch):
    """TC2: abc list agents exits 0 with 'No agents found' when no artifacts dir exists.

    PER-113: agents are project-scoped. abc list agents reads from
    .agentic-beacon/artifacts/agents/ which may not exist yet (before abc sync).
    """
    from click.testing import CliRunner

    runner = CliRunner()
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    result = runner.invoke(main, ["list", "agents"])
    assert result.exit_code == 0
    # No beacon.yaml at all → "No agents declared" branch
    assert "No agents declared" in result.output
    assert "abc adopt" in result.output


def test_list_fails_with_malformed_config_toml(runner, tmp_path, monkeypatch):
    """abc list exits non-zero with a config.toml hint when the file is malformed.

    Regression for PER-129: decoupling from SyncEngine must NOT silently degrade
    when config.toml is present but invalid. The old code validated WorkspaceConfig
    before listing; this test documents that contract.
    """
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    beacon_dir = project / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "artifacts").mkdir()
    # Plant invalid TOML — missing required [warehouse] section
    (beacon_dir / "config.toml").write_text("not valid toml !!!\n")

    result = runner.invoke(main, ["list"])

    assert result.exit_code != 0
    output_lower = result.output.lower()
    assert "config.toml" in output_lower, (
        f"Expected 'config.toml' in error output; got:\n{result.output}"
    )
    assert "invalid" in output_lower or "validation" in output_lower, (
        f"Expected 'invalid' or 'validation' in error output; got:\n{result.output}"
    )


def test_list_agents_not_shown_in_default_list(synced_project):
    """TC2: abc list (no filter) → agents section not shown (backward compatible).

    PER-113: even with agent artifacts in .agentic-beacon/artifacts/agents/,
    the default abc list (no type arg) only shows contexts and skills.
    """
    project, warehouse, runner = synced_project

    # Plant an agent artifact symlink to verify it does NOT show in the default list.
    # Create a real target file so the symlink is valid (list_artifacts checks is_symlink).
    wh_agent = warehouse / "agents" / "test-agent.md"
    wh_agent.write_text("---\nname: test-agent\n---\n")
    agents_artifacts = project / ".agentic-beacon" / "artifacts" / "agents"
    agents_artifacts.mkdir(parents=True, exist_ok=True)
    (agents_artifacts / "test-agent.md").symlink_to(wh_agent)

    result = runner.invoke(main, ["list"])
    assert result.exit_code == 0
    # Agents should not appear in the default project list
    assert "Installed Agents" not in result.output
