"""Integration tests for legacy global agent symlink cleanup (PER-113, task 9.5).

Covers the abc sync migration path:
- Pre-existing legacy symlinks under ~/.claude/agents/ or ~/.config/opencode/agents/
  that point into the connected warehouse's agents/ dir are removed by abc sync.
- The sync output prints 'Cleaned up N legacy global agent symlinks (PER-113 migration).'
  only when N > 0.
- A second run of abc sync produces no notice (idempotent).
- Non-matching symlinks and regular files in the global dirs are preserved.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml
from beacon.cli.main import main
from click.testing import CliRunner

pytestmark = pytest.mark.integration


def _git_env() -> dict:
    return {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "t@t.local",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "t@t.local",
    }


def _git_init(path: Path) -> None:
    env = _git_env()
    subprocess.run(["git", "init"], cwd=path, env=env, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path,
        env=env,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=path,
        env=env,
        check=True,
        capture_output=True,
    )


def _git_add_commit(path: Path, message: str = "add files") -> None:
    env = _git_env()
    subprocess.run(
        ["git", "add", "-A"], cwd=path, env=env, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=path,
        env=env,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def warehouse(tmp_path: Path) -> Path:
    """Minimal warehouse with one agent."""
    wh = tmp_path / "warehouse"
    wh.mkdir()
    for d in ("agents", "contexts", "knowledge", "skills", "docs"):
        (wh / d).mkdir(parents=True)
    (wh / "README.md").write_text("# Test Warehouse\n")
    (wh / "agents" / "test-agent.md").write_text(
        "---\nname: test-agent\n---\n# Test Agent\n"
    )
    (wh / "agents" / "agents.yaml").write_text(
        yaml.safe_dump({"test-agent": {"skills": []}})
    )
    _git_init(wh)
    _git_add_commit(wh, "init")
    return wh


@pytest.fixture
def project_dir(tmp_path: Path, warehouse: Path, monkeypatch) -> Path:
    """A project connected to the warehouse."""
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    runner = CliRunner()
    r = runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])
    assert r.exit_code == 0, f"connect failed: {r.output}"
    r = runner.invoke(main, ["setup"])
    assert r.exit_code == 0, f"setup failed: {r.output}"

    return project


# ---------------------------------------------------------------------------
# TC1: legacy ~/.claude/agents/ symlink into warehouse → removed, notice printed
# ---------------------------------------------------------------------------


def test_sync_removes_legacy_claude_symlink_and_prints_notice(
    project_dir: Path, warehouse: Path, monkeypatch, isolated_home
):
    """abc sync removes a legacy ~/.claude/agents/ symlink and prints the notice."""
    runner = CliRunner()
    monkeypatch.chdir(project_dir)

    # Seed a legacy symlink in the isolated ~/.claude/agents/
    claude_agents = isolated_home / ".claude" / "agents"
    claude_agents.mkdir(parents=True)
    legacy_link = claude_agents / "test-agent.md"
    legacy_link.symlink_to(warehouse / "agents" / "test-agent.md")
    assert legacy_link.is_symlink()

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text("artifacts:\n  contexts: []\n  skills: []\n  agents: []\n")

    r = runner.invoke(main, ["sync", "--skip-git-check"])
    assert r.exit_code == 0, f"sync failed: {r.output}"

    # Legacy symlink removed
    assert not legacy_link.exists() and not legacy_link.is_symlink(), (
        "Expected legacy symlink to be removed by abc sync"
    )

    # Notice printed exactly once, with exact format
    _notice_re = re.compile(
        r"Cleaned up \d+ legacy global agent symlinks \(PER-113 migration\)\.$"
    )
    notice_lines = [line for line in r.output.splitlines() if _notice_re.search(line)]
    assert len(notice_lines) == 1, (
        f"Expected 1 notice line matching regex, got {len(notice_lines)}. Output:\n{r.output}"
    )
    assert "1" in notice_lines[0], f"Expected count of 1 in notice: {notice_lines[0]}"


# ---------------------------------------------------------------------------
# TC2: second sync produces no notice (idempotent)
# ---------------------------------------------------------------------------


def test_sync_legacy_cleanup_is_idempotent(
    project_dir: Path, warehouse: Path, monkeypatch, isolated_home
):
    """Running abc sync a second time after cleanup produces no legacy notice."""
    runner = CliRunner()
    monkeypatch.chdir(project_dir)

    # Seed a legacy symlink
    claude_agents = isolated_home / ".claude" / "agents"
    claude_agents.mkdir(parents=True)
    (claude_agents / "test-agent.md").symlink_to(warehouse / "agents" / "test-agent.md")

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text("artifacts:\n  contexts: []\n  skills: []\n  agents: []\n")

    _notice_re = re.compile(
        r"Cleaned up \d+ legacy global agent symlinks \(PER-113 migration\)\.$"
    )

    # First sync cleans up and must print the notice
    r1 = runner.invoke(main, ["sync", "--skip-git-check"])
    assert r1.exit_code == 0, f"first sync failed: {r1.output}"
    assert any(_notice_re.search(line) for line in r1.output.splitlines()), (
        f"Expected notice on first sync. Output:\n{r1.output}"
    )

    # Second sync: no legacy symlinks remain → no notice
    r2 = runner.invoke(main, ["sync", "--skip-git-check"])
    assert r2.exit_code == 0, f"second sync failed: {r2.output}"
    assert not any(_notice_re.search(line) for line in r2.output.splitlines()), (
        f"Expected no legacy cleanup notice on second run. Output:\n{r2.output}"
    )


# ---------------------------------------------------------------------------
# TC3: non-matching symlinks and regular files preserved
# ---------------------------------------------------------------------------


def test_sync_preserves_non_warehouse_symlinks_and_regular_files(
    project_dir: Path, warehouse: Path, monkeypatch, isolated_home
):
    """abc sync does NOT touch symlinks pointing outside the warehouse or regular files."""
    runner = CliRunner()
    monkeypatch.chdir(project_dir)

    claude_agents = isolated_home / ".claude" / "agents"
    claude_agents.mkdir(parents=True)

    # Symlink pointing to a file OUTSIDE the warehouse → preserved
    other_target = isolated_home / "some-other-agent.md"
    other_target.write_text("# Other Agent\n")
    non_matching_link = claude_agents / "other-agent.md"
    non_matching_link.symlink_to(other_target)

    # Regular file (not a symlink) → preserved
    regular_file = claude_agents / "handcrafted-agent.md"
    regular_file.write_text("# Handcrafted\n")

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text("artifacts:\n  contexts: []\n  skills: []\n  agents: []\n")

    r = runner.invoke(main, ["sync", "--skip-git-check"])
    assert r.exit_code == 0, f"sync failed: {r.output}"

    # Non-matching symlink preserved
    assert non_matching_link.is_symlink(), (
        "Non-matching symlink (not pointing into warehouse) must NOT be removed"
    )

    # Regular file preserved
    assert regular_file.is_file() and not regular_file.is_symlink(), (
        "Regular file in global agent dir must NOT be removed"
    )

    # No notice (nothing was cleaned up)
    notice_lines = [
        line
        for line in r.output.splitlines()
        if "legacy global agent symlink" in line and "PER-113" in line
    ]
    assert len(notice_lines) == 0, (
        f"Expected no notice when nothing was cleaned up. Output:\n{r.output}"
    )


# ---------------------------------------------------------------------------
# TC4: missing global agent dirs → no error, no notice
# ---------------------------------------------------------------------------


def test_sync_with_no_global_agent_dirs_no_error(
    project_dir: Path, warehouse: Path, monkeypatch, isolated_home
):
    """abc sync is silent and error-free when neither global agent dir exists."""
    runner = CliRunner()
    monkeypatch.chdir(project_dir)

    # isolated_home has no .claude/ or .config/ dirs
    assert not (isolated_home / ".claude").exists()
    assert not (isolated_home / ".config").exists()

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text("artifacts:\n  contexts: []\n  skills: []\n  agents: []\n")

    r = runner.invoke(main, ["sync", "--skip-git-check"])
    assert r.exit_code == 0, f"sync failed: {r.output}"

    notice_lines = [
        line
        for line in r.output.splitlines()
        if "legacy global agent symlink" in line and "PER-113" in line
    ]
    assert len(notice_lines) == 0, (
        f"Expected no legacy cleanup notice when dirs are absent. Output:\n{r.output}"
    )
