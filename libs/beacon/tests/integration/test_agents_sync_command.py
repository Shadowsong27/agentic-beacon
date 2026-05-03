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
- TC7: Non-interactive mode with conflict → skipped automatically
- TC8: No .agentic-beacon → error
- TC9: Unknown --preserve flag is rejected
- TC10: Sync updates sync-state HEAD even when agent content is already identical
"""

import json
import subprocess

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
# TC10: Sync updates sync-state HEAD even when agent content is already identical
# ---------------------------------------------------------------------------


def test_agents_sync_updates_sync_state_when_content_unchanged(
    connected_project, isolated_home
):
    """TC10: sync updates sync-state HEAD even when agent file is already up-to-date.

    Regression test for: warehouse advances (e.g. a commit that doesn't touch agents),
    content stays identical, but 'abc delta' keeps reporting agents as stale because
    agents sync skipped writing the file and never bumped the recorded HEAD.
    """

    project, wh = connected_project

    # Make wh a real git repo so we can get a HEAD SHA
    subprocess.run(["git", "init", str(wh)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(wh), "config", "user.email", "test@test.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(wh), "config", "user.name", "Test"],
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "-C", str(wh), "add", "."], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(wh), "commit", "-m", "init"],
        check=True,
        capture_output=True,
    )
    current_head = subprocess.run(
        ["git", "-C", str(wh), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    # Pre-install the agent with the correct content (no write needed on sync)
    opencode_agents = isolated_home / ".config" / "opencode" / "agents"
    opencode_agents.mkdir(parents=True)
    (opencode_agents / "code-reviewer.md").write_text(SAMPLE_AGENT_MD)

    # Pre-populate sync-state with a stale (old) warehouse HEAD
    state_file = isolated_home / ".config" / "agentic-beacon" / "sync-state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(
        json.dumps(
            {
                "version": 1,
                "warehouses": {
                    str(wh): {
                        "agents/code-reviewer.md": {
                            "content_hash": "oldhash",
                            "warehouse_head": "old_sha_before_advance",
                            "installed_at": "2026-01-01T00:00:00+00:00",
                        }
                    }
                },
            }
        )
    )

    runner = CliRunner()
    result = runner.invoke(main, ["agents", "sync", "--skip-git-check"])
    assert result.exit_code == 0, result.output

    # Sync-state HEAD must be updated to the current warehouse HEAD
    updated_state = json.loads(state_file.read_text())
    entry = updated_state["warehouses"][str(wh)]["agents/code-reviewer.md"]
    assert entry["warehouse_head"] == current_head, (
        f"Expected sync-state HEAD to be updated to {current_head!r}, "
        f"got {entry['warehouse_head']!r}. "
        "'abc delta' would still report this agent as stale."
    )
