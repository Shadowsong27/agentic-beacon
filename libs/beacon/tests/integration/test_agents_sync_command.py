"""Tests for abc agents sync command.

abc agents sync reads the connected warehouse, finds every agent definition
under agents/, and links them into global tool directories. It operates at
the user level (global agent dirs), not the project level.

Test Cases:
- TC1: Links agent to opencode global dir
- TC2: Links agent to claudecode global dir
- TC3: Both tools present → both get the agent
- TC4: No agents/ dir in warehouse → silent no-op
- TC5: Already up-to-date → idempotent
- TC6: --force overwrites conflicting agent without prompting
- TC7: Non-interactive mode with conflict → skipped automatically
- TC8: No .agentic-beacon → error
- TC9: Unknown --preserve flag is rejected
- TC10: Warehouse edits are visible through global agent symlink
"""

import pytest
from beacon.cli.main import main
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
    """TC1: abc agents sync links agent to ~/.config/opencode/agents/."""
    (isolated_home / ".config" / "opencode").mkdir(parents=True)
    project, wh = connected_project

    runner = CliRunner()
    result = runner.invoke(main, ["agents", "sync", "--skip-git-check"])

    assert result.exit_code == 0, result.output
    dest = isolated_home / ".config" / "opencode" / "agents" / "code-reviewer.md"
    assert dest.is_symlink()
    assert dest.resolve() == (wh / "agents" / "code-reviewer.md").resolve()
    assert dest.read_text() == SAMPLE_AGENT_MD


# ---------------------------------------------------------------------------
# TC2: Installs agent to claudecode global dir
# ---------------------------------------------------------------------------


def test_agents_sync_installs_to_claudecode(connected_project, isolated_home):
    """TC2: abc agents sync links agent to ~/.claude/agents/."""
    (isolated_home / ".claude").mkdir(parents=True)
    project, wh = connected_project

    runner = CliRunner()
    result = runner.invoke(main, ["agents", "sync", "--skip-git-check"])

    assert result.exit_code == 0, result.output
    dest = isolated_home / ".claude" / "agents" / "code-reviewer.md"
    assert dest.is_symlink()
    assert dest.resolve() == (wh / "agents" / "code-reviewer.md").resolve()
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
    opencode_dest = (
        isolated_home / ".config" / "opencode" / "agents" / "code-reviewer.md"
    )
    claude_dest = isolated_home / ".claude" / "agents" / "code-reviewer.md"
    assert opencode_dest.is_symlink()
    assert claude_dest.is_symlink()
    assert opencode_dest.resolve() == (wh / "agents" / "code-reviewer.md").resolve()
    assert claude_dest.resolve() == (wh / "agents" / "code-reviewer.md").resolve()
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
    """TC5: Running agents sync twice does not re-link already-current agents."""
    opencode_agents = isolated_home / ".config" / "opencode" / "agents"
    opencode_agents.mkdir(parents=True)
    project, wh = connected_project
    dest = opencode_agents / "code-reviewer.md"

    runner = CliRunner()
    result = runner.invoke(main, ["agents", "sync", "--skip-git-check"])
    assert result.exit_code == 0, result.output

    assert dest.is_symlink()
    mtime_before = dest.lstat().st_mtime

    result = runner.invoke(main, ["agents", "sync", "--skip-git-check"])
    assert result.exit_code == 0, result.output

    mtime_after = dest.lstat().st_mtime
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
    dest = opencode_agents / "code-reviewer.md"
    assert dest.is_symlink()
    assert dest.resolve() == (wh / "agents" / "code-reviewer.md").resolve()
    assert dest.read_text() == SAMPLE_AGENT_MD


# ---------------------------------------------------------------------------
# TC7: Non-interactive mode with conflict → skipped automatically
# ---------------------------------------------------------------------------


def test_agents_sync_non_interactive_skips_conflict(connected_project, isolated_home):
    """TC7: In non-interactive mode, conflicts are skipped without prompting."""
    opencode_agents = isolated_home / ".config" / "opencode" / "agents"
    opencode_agents.mkdir(parents=True)
    (opencode_agents / "code-reviewer.md").write_text(SAMPLE_AGENT_MD_LOCAL)

    project, wh = connected_project
    runner = CliRunner()
    result = runner.invoke(main, ["agents", "sync", "--skip-git-check"])

    assert result.exit_code == 0, result.output
    assert (opencode_agents / "code-reviewer.md").read_text() == SAMPLE_AGENT_MD_LOCAL
    assert "Skipped" in result.output


# ---------------------------------------------------------------------------
# TC8: No .agentic-beacon → error
# ---------------------------------------------------------------------------


def test_agents_sync_no_beacon_dir_errors(tmp_path, monkeypatch, isolated_home):
    """TC8: Running agents sync outside a connected project exits with an error."""
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    runner = CliRunner()
    result = runner.invoke(main, ["agents", "sync", "--skip-git-check"])

    assert result.exit_code != 0
    assert "No .agentic-beacon directory found" in result.output


# ---------------------------------------------------------------------------
# TC9: Unknown --preserve flag is rejected
# ---------------------------------------------------------------------------


def test_agents_sync_preserve_flag_is_rejected(connected_project, isolated_home):
    """TC9: --preserve is no longer accepted on abc agents sync."""
    project, wh = connected_project
    runner = CliRunner()
    result = runner.invoke(main, ["agents", "sync", "--preserve", "--skip-git-check"])

    assert result.exit_code != 0
    assert "No such option: --preserve" in result.output


# ---------------------------------------------------------------------------
# TC10: Warehouse edits are visible through global agent symlink
# ---------------------------------------------------------------------------


def test_agents_sync_reflects_warehouse_edits(connected_project, isolated_home):
    """TC10: global agent symlink reads the warehouse file directly."""
    project, wh = connected_project
    (isolated_home / ".config" / "opencode").mkdir(parents=True)

    runner = CliRunner()
    result = runner.invoke(main, ["agents", "sync", "--skip-git-check"])
    assert result.exit_code == 0, result.output

    dest = isolated_home / ".config" / "opencode" / "agents" / "code-reviewer.md"
    (wh / "agents" / "code-reviewer.md").write_text("Updated in warehouse.\n")

    assert dest.is_symlink()
    assert dest.read_text() == "Updated in warehouse.\n"


def test_agents_sync_replaces_identical_regular_file_with_symlink(
    connected_project, isolated_home
):
    """Existing copy with matching content is migrated to a warehouse symlink."""
    project, wh = connected_project
    opencode_agents = isolated_home / ".config" / "opencode" / "agents"
    opencode_agents.mkdir(parents=True)
    dest = opencode_agents / "code-reviewer.md"
    dest.write_text(SAMPLE_AGENT_MD)

    runner = CliRunner()
    result = runner.invoke(main, ["agents", "sync", "--skip-git-check"])

    assert result.exit_code == 0, result.output
    assert dest.is_symlink()
    assert dest.resolve() == (wh / "agents" / "code-reviewer.md").resolve()


def test_agents_sync_repairs_broken_symlink(connected_project, isolated_home):
    """Broken global agent symlinks are repaired to the warehouse file."""
    project, wh = connected_project
    opencode_agents = isolated_home / ".config" / "opencode" / "agents"
    opencode_agents.mkdir(parents=True)
    dest = opencode_agents / "code-reviewer.md"
    dest.symlink_to(wh / "agents" / "missing.md")

    runner = CliRunner()
    result = runner.invoke(main, ["agents", "sync", "--skip-git-check"])

    assert result.exit_code == 0, result.output
    assert dest.is_symlink()
    assert dest.resolve() == (wh / "agents" / "code-reviewer.md").resolve()


def test_agents_sync_ignores_agents_readme(connected_project, isolated_home):
    """The warehouse agents/README.md scaffold is not an agent definition."""
    project, wh = connected_project
    (wh / "agents" / "README.md").write_text("# Agents docs\n")
    (isolated_home / ".config" / "opencode").mkdir(parents=True)

    runner = CliRunner()
    result = runner.invoke(main, ["agents", "sync", "--skip-git-check"])

    assert result.exit_code == 0, result.output
    assert not (
        isolated_home / ".config" / "opencode" / "agents" / "README.md"
    ).exists()
