"""Tests for abc agents sync command.

abc agents sync reads the connected warehouse, finds every agent definition
under agents/, and installs them into global tool directories. It operates
at the user level (global agent dirs), not the project level.

Test Cases:
- TC1: Installs agent to opencode global dir
- TC2: Installs agent to claudecode global dir
- TC3: Both tools present → both get the agent
- TC4: No agents/ dir in warehouse → silent no-op
- TC5: Already up-to-date → idempotent
- TC6: --force overwrites conflicting agent without prompting
- TC7: --preserve skips conflicting agent
- TC8: Non-interactive mode with conflict → skipped automatically
- TC9: No .agentic-beacon → error
- TC10: --force and --preserve are mutually exclusive
"""

import pytest
from beacon.cli import main
from click.testing import CliRunner

SAMPLE_AGENT_MD = "You are a helpful assistant specialized in Python.\n"
SAMPLE_AGENT_MD_LOCAL = "You are a local version of the assistant.\n"


@pytest.fixture
def warehouse_with_agents(tmp_path):
    """Warehouse with one agent definition."""
    wh = tmp_path / "warehouse"
    for d in ("agents", "knowledge", "skills", "contexts", "docs"):
        (wh / d).mkdir(parents=True)
    (wh / "README.md").write_text("# WH")
    (wh / "agents" / "code-reviewer.md").write_text(SAMPLE_AGENT_MD)
    return wh


@pytest.fixture
def connected_project(tmp_path, warehouse_with_agents, monkeypatch):
    """Project connected to the warehouse."""
    project = tmp_path / "project"
    project.mkdir()
    beacon_dir = project / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "config.toml").write_text(
        f'[warehouse]\nlocal_path = "{warehouse_with_agents}"\n'
    )
    (beacon_dir / "beacon.yaml").write_text(
        "artifacts:\n  knowledge: []\n  skills: []\n  contexts: []\n"
    )
    monkeypatch.chdir(project)
    return project, warehouse_with_agents


# ---------------------------------------------------------------------------
# TC1: Installs agent to opencode global dir
# ---------------------------------------------------------------------------


def test_agents_sync_installs_to_opencode(connected_project, isolated_home):
    """TC1: abc agents sync writes agent to ~/.config/opencode/agents/."""
    (isolated_home / ".config" / "opencode").mkdir(parents=True)
    project, wh = connected_project

    runner = CliRunner()
    result = runner.invoke(main, ["agents", "sync", "--skip-git-check"])

    assert result.exit_code == 0, result.output
    dest = isolated_home / ".config" / "opencode" / "agents" / "code-reviewer.md"
    assert dest.exists()
    assert dest.read_text() == SAMPLE_AGENT_MD


# ---------------------------------------------------------------------------
# TC2: Installs agent to claudecode global dir
# ---------------------------------------------------------------------------


def test_agents_sync_installs_to_claudecode(connected_project, isolated_home):
    """TC2: abc agents sync writes agent to ~/.claude/agents/."""
    (isolated_home / ".claude").mkdir(parents=True)
    project, wh = connected_project

    runner = CliRunner()
    result = runner.invoke(main, ["agents", "sync", "--skip-git-check"])

    assert result.exit_code == 0, result.output
    dest = isolated_home / ".claude" / "agents" / "code-reviewer.md"
    assert dest.exists()
    assert dest.read_text() == SAMPLE_AGENT_MD


# ---------------------------------------------------------------------------
# TC3: Both tools present → both get the agent
# ---------------------------------------------------------------------------


def test_agents_sync_installs_to_both_tools(connected_project, isolated_home):
    """TC3: When both tools are installed, both get the agent."""
    (isolated_home / ".config" / "opencode").mkdir(parents=True)
    (isolated_home / ".claude").mkdir(parents=True)
    project, wh = connected_project

    runner = CliRunner()
    result = runner.invoke(main, ["agents", "sync", "--skip-git-check"])

    assert result.exit_code == 0, result.output
    assert (
        isolated_home / ".config" / "opencode" / "agents" / "code-reviewer.md"
    ).exists()
    assert (isolated_home / ".claude" / "agents" / "code-reviewer.md").exists()
    assert "code-reviewer" in result.output


# ---------------------------------------------------------------------------
# TC4: No agents/ dir in warehouse → silent no-op
# ---------------------------------------------------------------------------


def test_agents_sync_no_agents_dir_is_noop(tmp_path, monkeypatch, isolated_home):
    """TC4: Warehouse without agents/ dir completes silently without error."""
    (isolated_home / ".config" / "opencode").mkdir(parents=True)

    wh = tmp_path / "warehouse"
    for d in ("knowledge", "skills", "contexts", "docs"):
        (wh / d).mkdir(parents=True)
    (wh / "README.md").write_text("# WH")

    project = tmp_path / "project"
    project.mkdir()
    beacon_dir = project / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "config.toml").write_text(f'[warehouse]\nlocal_path = "{wh}"\n')
    (beacon_dir / "beacon.yaml").write_text(
        "artifacts:\n  knowledge: []\n  skills: []\n  contexts: []\n"
    )
    monkeypatch.chdir(project)

    runner = CliRunner()
    result = runner.invoke(main, ["agents", "sync", "--skip-git-check"])

    assert result.exit_code == 0, result.output
    assert not (isolated_home / ".config" / "opencode" / "agents").exists()


# ---------------------------------------------------------------------------
# TC5: Already up-to-date → idempotent
# ---------------------------------------------------------------------------


def test_agents_sync_idempotent(connected_project, isolated_home):
    """TC5: Running agents sync twice does not re-write already-current agent files."""
    opencode_agents = isolated_home / ".config" / "opencode" / "agents"
    opencode_agents.mkdir(parents=True)
    (opencode_agents / "code-reviewer.md").write_text(SAMPLE_AGENT_MD)
    mtime_before = (opencode_agents / "code-reviewer.md").stat().st_mtime

    project, wh = connected_project
    runner = CliRunner()
    runner.invoke(main, ["agents", "sync", "--skip-git-check"])

    mtime_after = (opencode_agents / "code-reviewer.md").stat().st_mtime
    assert mtime_before == mtime_after


# ---------------------------------------------------------------------------
# TC6: --force overwrites conflicting agent without prompting
# ---------------------------------------------------------------------------


def test_agents_sync_force_overwrites_conflict(connected_project, isolated_home):
    """TC6: --force overwrites a diverged local agent without a prompt."""
    opencode_agents = isolated_home / ".config" / "opencode" / "agents"
    opencode_agents.mkdir(parents=True)
    (opencode_agents / "code-reviewer.md").write_text(SAMPLE_AGENT_MD_LOCAL)

    project, wh = connected_project
    runner = CliRunner()
    result = runner.invoke(main, ["agents", "sync", "--force", "--skip-git-check"])

    assert result.exit_code == 0, result.output
    assert (opencode_agents / "code-reviewer.md").read_text() == SAMPLE_AGENT_MD


# ---------------------------------------------------------------------------
# TC7: --preserve skips conflicting agent
# ---------------------------------------------------------------------------


def test_agents_sync_preserve_skips_conflict(connected_project, isolated_home):
    """TC7: --preserve leaves diverged local agent files untouched."""
    opencode_agents = isolated_home / ".config" / "opencode" / "agents"
    opencode_agents.mkdir(parents=True)
    (opencode_agents / "code-reviewer.md").write_text(SAMPLE_AGENT_MD_LOCAL)

    project, wh = connected_project
    runner = CliRunner()
    result = runner.invoke(main, ["agents", "sync", "--preserve", "--skip-git-check"])

    assert result.exit_code == 0, result.output
    assert (opencode_agents / "code-reviewer.md").read_text() == SAMPLE_AGENT_MD_LOCAL
    assert "Skipped" in result.output


# ---------------------------------------------------------------------------
# TC8: Non-interactive mode with conflict → skipped automatically
# ---------------------------------------------------------------------------


def test_agents_sync_non_interactive_skips_conflict(connected_project, isolated_home):
    """TC8: In non-interactive mode, conflicts are skipped without prompting."""
    opencode_agents = isolated_home / ".config" / "opencode" / "agents"
    opencode_agents.mkdir(parents=True)
    (opencode_agents / "code-reviewer.md").write_text(SAMPLE_AGENT_MD_LOCAL)

    project, wh = connected_project
    runner = CliRunner()
    # CliRunner uses non-interactive stdin by default
    result = runner.invoke(main, ["agents", "sync", "--skip-git-check"])

    assert result.exit_code == 0, result.output
    assert (opencode_agents / "code-reviewer.md").read_text() == SAMPLE_AGENT_MD_LOCAL


# ---------------------------------------------------------------------------
# TC9: No .agentic-beacon → error
# ---------------------------------------------------------------------------


def test_agents_sync_no_beacon_dir_errors(tmp_path, monkeypatch, isolated_home):
    """TC9: Running agents sync outside a connected project exits with an error."""
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    runner = CliRunner()
    result = runner.invoke(main, ["agents", "sync", "--skip-git-check"])

    assert result.exit_code != 0
    assert "No .agentic-beacon directory found" in result.output


# ---------------------------------------------------------------------------
# TC10: --force and --preserve are mutually exclusive
# ---------------------------------------------------------------------------


def test_agents_sync_force_and_preserve_are_exclusive(connected_project, isolated_home):
    """TC10: Passing both --force and --preserve is rejected."""
    project, wh = connected_project
    runner = CliRunner()
    result = runner.invoke(
        main, ["agents", "sync", "--force", "--preserve", "--skip-git-check"]
    )

    assert result.exit_code != 0
    assert "mutually exclusive" in result.output
