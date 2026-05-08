"""Integration tests for agent sync lifecycle (PER-113, task 9.3).

Covers the full add-and-wire / remove-and-unwire lifecycle for declared agents:

- Declaring an agent in beacon.yaml and running abc sync creates:
  - .agentic-beacon/artifacts/agents/<name>.md  (artifact symlink)
  - .claude/agents/<name>.md                    (project-local tool symlink)
- Removing the agent from beacon.yaml and re-running abc sync removes
  all three paths.
"""

import os
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
    (wh / "agents" / "spec-planner.md").write_text(
        "---\nname: spec-planner\ndescription: Plans specs\n---\n# Spec Planner\n"
    )
    (wh / "agents" / "agents.yaml").write_text(
        yaml.safe_dump({"spec-planner": {"skills": []}})
    )
    _git_init(wh)
    _git_add_commit(wh, "init")
    return wh


@pytest.fixture
def project_dir(tmp_path: Path, warehouse: Path, monkeypatch) -> Path:
    """A project connected to the warehouse, with .claude/ present."""
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)

    runner = CliRunner()
    r = runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])
    assert r.exit_code == 0, f"connect failed: {r.output}"
    r = runner.invoke(main, ["setup"])
    assert r.exit_code == 0, f"setup failed: {r.output}"

    # Create .claude/ so detect_agents() returns 'claudecode'
    (project / ".claude").mkdir(exist_ok=True)

    return project


# ---------------------------------------------------------------------------
# TC1 / Phase-add: declare agent → abc sync → artifact + tool symlinks appear
# ---------------------------------------------------------------------------


def test_sync_wires_declared_agent_artifact_and_tool_symlinks(
    project_dir: Path, warehouse: Path, monkeypatch
):
    """Declaring an agent in beacon.yaml and running abc sync creates three paths.

    1. .agentic-beacon/artifacts/agents/spec-planner.md  (artifact symlink)
    2. .claude/agents/spec-planner.md                    (project-local tool symlink)
    """
    runner = CliRunner()
    monkeypatch.chdir(project_dir)

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  contexts: []\n"
        "  skills: []\n"
        "  agents:\n"
        "    - agents/spec-planner.md\n"
    )

    r = runner.invoke(main, ["sync", "--skip-git-check"])
    assert r.exit_code == 0, f"sync failed: {r.output}"

    # Artifact symlink
    artifact = (
        project_dir / ".agentic-beacon" / "artifacts" / "agents" / "spec-planner.md"
    )
    assert artifact.is_symlink(), f"Expected artifact symlink at {artifact}"
    assert artifact.exists(), f"Artifact symlink is broken: {artifact}"

    # Project-local tool symlink
    claude_link = project_dir / ".claude" / "agents" / "spec-planner.md"
    assert claude_link.is_symlink(), (
        f"Expected .claude/agents/spec-planner.md symlink, not found. "
        f"sync output: {r.output}"
    )
    assert claude_link.exists(), f".claude/agents symlink is broken: {claude_link}"


# ---------------------------------------------------------------------------
# TC2: sync with only .claude/ present → only .claude/agents/ wired
# ---------------------------------------------------------------------------


def test_sync_wires_only_claude_when_no_opencode_dir(
    project_dir: Path, warehouse: Path, monkeypatch
):
    """When only .claude/ exists, only .claude/agents/ is wired; no .opencode/ error."""
    runner = CliRunner()
    monkeypatch.chdir(project_dir)

    # Ensure no .opencode/ dir exists
    opencode_dir = project_dir / ".opencode"
    if opencode_dir.exists():
        import shutil

        shutil.rmtree(opencode_dir)

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  contexts: []\n"
        "  skills: []\n"
        "  agents:\n"
        "    - agents/spec-planner.md\n"
    )

    r = runner.invoke(main, ["sync", "--skip-git-check"])
    assert r.exit_code == 0, f"sync failed: {r.output}"

    # .claude/agents/ symlink present
    claude_link = project_dir / ".claude" / "agents" / "spec-planner.md"
    assert claude_link.is_symlink(), "Expected .claude/agents/spec-planner.md"

    # No .opencode/ wiring (dir doesn't exist)
    opencode_link = project_dir / ".opencode" / "agents" / "spec-planner.md"
    assert not opencode_link.exists(), (
        "Expected no .opencode/agents/ wiring when .opencode/ dir is absent"
    )


# ---------------------------------------------------------------------------
# TC3: sync with no tool dirs → only artifact symlink; no error
# ---------------------------------------------------------------------------


def test_sync_creates_only_artifact_symlink_when_no_tool_dirs(
    project_dir: Path, warehouse: Path, monkeypatch
):
    """When neither .claude/ nor .opencode/ exists, sync creates only the artifact symlink."""
    runner = CliRunner()
    monkeypatch.chdir(project_dir)

    # Remove .claude/ if setup created it
    claude_dir = project_dir / ".claude"
    if claude_dir.exists():
        import shutil

        shutil.rmtree(claude_dir)

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  contexts: []\n"
        "  skills: []\n"
        "  agents:\n"
        "    - agents/spec-planner.md\n"
    )

    r = runner.invoke(main, ["sync", "--skip-git-check"])
    assert r.exit_code == 0, f"sync failed: {r.output}"

    # Artifact symlink still created
    artifact = (
        project_dir / ".agentic-beacon" / "artifacts" / "agents" / "spec-planner.md"
    )
    assert artifact.is_symlink(), "Artifact symlink must exist even with no tool dirs"

    # No tool symlinks
    assert not (project_dir / ".claude" / "agents" / "spec-planner.md").exists()
    assert not (project_dir / ".opencode" / "agents" / "spec-planner.md").exists()


# ---------------------------------------------------------------------------
# TC4: empty agents list → sync still succeeds
# ---------------------------------------------------------------------------


def test_sync_with_empty_agents_list_succeeds(
    project_dir: Path, warehouse: Path, monkeypatch
):
    """An empty agents list does not prevent sync from completing."""
    runner = CliRunner()
    monkeypatch.chdir(project_dir)

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text("artifacts:\n  contexts: []\n  skills: []\n  agents: []\n")

    r = runner.invoke(main, ["sync", "--skip-git-check"])
    assert r.exit_code == 0, f"sync failed: {r.output}"

    # No agents dir created
    artifact_dir = project_dir / ".agentic-beacon" / "artifacts" / "agents"
    if artifact_dir.exists():
        assert not any(artifact_dir.rglob("*.md")), (
            "No agent artifacts should exist when agents list is empty"
        )


# ---------------------------------------------------------------------------
# Phase-remove: remove agent from beacon.yaml → abc sync → all three paths gone
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Finding 2: agents-only sync still updates project-root .gitignore
# ---------------------------------------------------------------------------


def test_sync_with_only_agents_updates_gitignore(
    project_dir: Path, warehouse: Path, monkeypatch
):
    """A project with agents but no skills must still get .claude/agents/ + .opencode/agents/ in .gitignore."""
    runner = CliRunner()
    monkeypatch.chdir(project_dir)

    # Ensure both tool dirs exist so detect_agent_targets returns both
    (project_dir / ".opencode").mkdir(exist_ok=True)

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  contexts: []\n"
        "  skills: []\n"
        "  agents:\n"
        "    - agents/spec-planner.md\n"
    )

    r = runner.invoke(main, ["sync", "--skip-git-check"])
    assert r.exit_code == 0, f"sync failed: {r.output}"

    gitignore = (project_dir / ".gitignore").read_text()
    assert ".claude/agents/" in gitignore, (
        f".gitignore missing .claude/agents/ entry: {gitignore!r}"
    )
    assert ".opencode/agents/" in gitignore, (
        f".gitignore missing .opencode/agents/ entry: {gitignore!r}"
    )


def test_sync_with_no_agents_declared_does_not_mutate_gitignore(
    project_dir: Path, warehouse: Path, monkeypatch
):
    """A sync with zero declared agents must NOT add agent entries to .gitignore.

    Regression guard for the round-5 over-correction where update_agent_gitignores
    was hoisted to run on every real sync, dirtying contexts-only and skills-only
    repos with unused .claude/agents/ / .opencode/agents/ entries.
    """
    runner = CliRunner()
    monkeypatch.chdir(project_dir)

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text("artifacts:\n  contexts: []\n  skills: []\n  agents: []\n")

    # Reset .gitignore to a clean state with no agent dir entries so we can
    # detect whether sync mutates it. (The fixture's default .gitignore may
    # already contain agent entries from a prior setup step.)
    gitignore_path = project_dir / ".gitignore"
    clean_content = "# Test fixture — clean gitignore for regression check\n"
    gitignore_path.write_text(clean_content)

    r = runner.invoke(main, ["sync", "--skip-git-check"])
    assert r.exit_code == 0, f"sync failed: {r.output}"

    post_state = gitignore_path.read_text()
    # The orchestrator's broader gitignore manager may append unrelated
    # .agentic-beacon/* entries; we only assert that THE AGENT-DIR entries
    # weren't added, since update_agent_gitignores is the gated function.
    assert ".claude/agents/" not in post_state, (
        f"sync with agents=[] must not add .claude/agents/ to .gitignore: {post_state!r}"
    )
    assert ".opencode/agents/" not in post_state, (
        f"sync with agents=[] must not add .opencode/agents/ to .gitignore: {post_state!r}"
    )


def test_sync_with_no_skills_declared_writes_skill_gitignore_entries(
    project_dir: Path, warehouse: Path, monkeypatch
):
    """A sync with zero declared skills MUST still write skills/ gitignore entries.

    Regression guard for PER-136: the per-tool .gitignore writes for skills/
    and command/ were gated inside `if has_skills:` after PR #109, meaning
    projects with no declared skills never got those entries even when .claude/
    or .opencode/ directories existed. This test confirms the fix — entries
    are written on directory existence alone.
    """
    runner = CliRunner()
    monkeypatch.chdir(project_dir)

    # Arrange
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text("artifacts:\n  contexts: []\n  skills: []\n  agents: []\n")

    claude_dir = project_dir / ".claude"
    claude_dir.mkdir(exist_ok=True)
    opencode_dir = project_dir / ".opencode"
    opencode_dir.mkdir(exist_ok=True)

    # Remove any pre-existing per-tool .gitignore files so the assertion detects
    # that sync wrote them rather than that they already existed.
    claude_gitignore = claude_dir / ".gitignore"
    opencode_gitignore = opencode_dir / ".gitignore"
    claude_gitignore.unlink(missing_ok=True)
    opencode_gitignore.unlink(missing_ok=True)

    # Act
    r = runner.invoke(main, ["sync", "--skip-git-check"])
    assert r.exit_code == 0, f"sync failed: {r.output}"

    # Assert
    assert claude_gitignore.exists(), ".claude/.gitignore must be created by sync"
    assert "skills/" in claude_gitignore.read_text(), (
        f".claude/.gitignore must contain 'skills/' entry: {claude_gitignore.read_text()!r}"
    )
    assert opencode_gitignore.exists(), ".opencode/.gitignore must be created by sync"
    opencode_content = opencode_gitignore.read_text()
    assert "skills/" in opencode_content, (
        f".opencode/.gitignore must contain 'skills/' entry: {opencode_content!r}"
    )
    assert "command/" in opencode_content, (
        f".opencode/.gitignore must contain 'command/' entry: {opencode_content!r}"
    )


def test_sync_unwires_removed_agent(project_dir: Path, warehouse: Path, monkeypatch):
    """Removing an agent from beacon.yaml and re-syncing removes all three paths.

    Covers task 9.3 phase-remove and task 3.2 (unwire_pruned_artifacts for agents).
    """
    runner = CliRunner()
    monkeypatch.chdir(project_dir)

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"

    # First sync: declare the agent
    beacon_yaml.write_text(
        "artifacts:\n"
        "  contexts: []\n"
        "  skills: []\n"
        "  agents:\n"
        "    - agents/spec-planner.md\n"
    )
    r = runner.invoke(main, ["sync", "--skip-git-check"])
    assert r.exit_code == 0, f"first sync failed: {r.output}"

    artifact = (
        project_dir / ".agentic-beacon" / "artifacts" / "agents" / "spec-planner.md"
    )
    claude_link = project_dir / ".claude" / "agents" / "spec-planner.md"
    assert artifact.is_symlink(), "Artifact symlink must exist after first sync"
    assert claude_link.is_symlink(), (
        ".claude/agents symlink must exist after first sync"
    )

    # Second sync: remove the agent
    beacon_yaml.write_text("artifacts:\n  contexts: []\n  skills: []\n  agents: []\n")
    # Pass "y\n" to confirm artifact symlink removal
    r = runner.invoke(main, ["sync", "--skip-git-check"], input="y\n")
    assert r.exit_code == 0, f"second sync failed: {r.output}"

    # All three paths must be absent
    assert not artifact.exists() and not artifact.is_symlink(), (
        "Artifact symlink must be removed after sync with empty agents list"
    )
    assert not claude_link.exists() and not claude_link.is_symlink(), (
        ".claude/agents symlink must be removed when agent is pruned"
    )
