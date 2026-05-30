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

    # Wiring note must explain the skip and the remediation
    assert "no tool directories found" in r.output, (
        f"Expected wiring note in sync output; got:\n{r.output}"
    )
    assert "mkdir .claude" in r.output, (
        f"Expected remediation hint in sync output; got:\n{r.output}"
    )


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

    Regression guard for the round-5 over-correction where ensure_agent_dirs_gitignored
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
    # weren't added, since ensure_agent_dirs_gitignored is the gated function.
    assert ".claude/agents/" not in post_state, (
        f"sync with agents=[] must not add .claude/agents/ to .gitignore: {post_state!r}"
    )
    assert ".opencode/agents/" not in post_state, (
        f"sync with agents=[] must not add .opencode/agents/ to .gitignore: {post_state!r}"
    )


def test_sync_with_emptied_agents_prunes_gitignore_entries(
    project_dir: Path, warehouse: Path, monkeypatch
):
    """When agents are removed from beacon.yaml, the prior .gitignore entries are pruned.

    Regression guard for PER-135: previously the .claude/agents/ and
    .opencode/agents/ entries were never removed once added. Now the
    orchestrator's prune-on-empty path removes them when artifacts.agents
    becomes empty.
    """
    runner = CliRunner()
    monkeypatch.chdir(project_dir)

    # Pre-populate the .gitignore with the agent-dir entries (as if a prior
    # sync with agents declared had added them).
    gitignore_path = project_dir / ".gitignore"
    gitignore_path.write_text(
        "# Existing project content\n__pycache__/\n.claude/agents/\n.opencode/agents/\n"
    )

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text("artifacts:\n  contexts: []\n  skills: []\n  agents: []\n")

    r = runner.invoke(main, ["sync", "--skip-git-check"])
    assert r.exit_code == 0, f"sync failed: {r.output}"

    post = gitignore_path.read_text()
    assert ".claude/agents/" not in post, (
        f"sync with agents=[] must prune .claude/agents/: {post!r}"
    )
    assert ".opencode/agents/" not in post, (
        f"sync with agents=[] must prune .opencode/agents/: {post!r}"
    )
    # User's other content must be preserved.
    assert "__pycache__/" in post, "pre-existing user entries must survive prune"


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
    claude_lines = set(claude_gitignore.read_text().splitlines())
    for entry in ("skills/", "scheduled_tasks.lock", "worktrees/"):
        assert entry in claude_lines, (
            f".claude/.gitignore must contain {entry!r}: {claude_lines!r}"
        )
    assert opencode_gitignore.exists(), ".opencode/.gitignore must be created by sync"
    opencode_lines = set(opencode_gitignore.read_text().splitlines())
    for entry in (
        "skills/",
        "command/",
        "bun.lock",
        "package.json",
        "package-lock.json",
        "node_modules/",
    ):
        assert entry in opencode_lines, (
            f".opencode/.gitignore must contain {entry!r}: {opencode_lines!r}"
        )


def test_sync_appends_missing_entries_to_existing_per_tool_gitignore(
    project_dir: Path, warehouse: Path, monkeypatch
):
    """Sync must extend an existing per-tool .gitignore without duplicating lines.

    Projects upgrading from an older Beacon may already have `.opencode/.gitignore`
    with the original `skills/` + `command/` entries. Re-syncing must:
      - leave the existing entries untouched (no duplicates)
      - preserve any user-added lines
      - append the newly-tracked entries (bun.lock, node_modules/, …)
    """
    runner = CliRunner()
    monkeypatch.chdir(project_dir)

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text("artifacts:\n  contexts: []\n  skills: []\n  agents: []\n")

    opencode_dir = project_dir / ".opencode"
    opencode_dir.mkdir(exist_ok=True)
    opencode_gitignore = opencode_dir / ".gitignore"
    opencode_gitignore.write_text(
        "# Agentic Beacon\nskills/\ncommand/\n# user-added\nmy-local-notes.md\n"
    )

    r = runner.invoke(main, ["sync", "--skip-git-check"])
    assert r.exit_code == 0, f"sync failed: {r.output}"

    lines = opencode_gitignore.read_text().splitlines()
    # No duplicates of pre-existing entries.
    assert lines.count("skills/") == 1, f"duplicate 'skills/': {lines!r}"
    assert lines.count("command/") == 1, f"duplicate 'command/': {lines!r}"
    assert lines.count("# Agentic Beacon") == 1, f"duplicate section header: {lines!r}"
    # User content preserved.
    assert "my-local-notes.md" in lines, f"user entry dropped: {lines!r}"
    # New entries appended.
    for entry in ("bun.lock", "package.json", "package-lock.json", "node_modules/"):
        assert entry in lines, f"missing newly-tracked entry {entry!r}: {lines!r}"


def test_sync_dry_run_does_not_write_skill_gitignore_entries(
    project_dir: Path, warehouse: Path, monkeypatch
):
    """A `sync --dry-run` MUST NOT write per-tool skill .gitignore entries.

    Regression guard for PER-136 review Finding 1: when the per-tool gitignore
    writes were hoisted out of `if has_skills:`, they lost the implicit `not
    dry_run` gate that came from `has_skills = bool(effective_set.skills) and
    not dry_run`. Every other mutation in run_sync is gated on `not dry_run`;
    this test ensures the hoisted block stays consistent with that contract.
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

    # Wipe any pre-existing per-tool .gitignore files so we can detect mutation.
    claude_gitignore = claude_dir / ".gitignore"
    opencode_gitignore = opencode_dir / ".gitignore"
    claude_gitignore.unlink(missing_ok=True)
    opencode_gitignore.unlink(missing_ok=True)

    # Act
    r = runner.invoke(main, ["sync", "--dry-run", "--skip-git-check"])
    assert r.exit_code == 0, f"sync --dry-run failed: {r.output}"

    # Assert — neither file should exist after a dry-run
    assert not claude_gitignore.exists(), (
        f".claude/.gitignore must NOT be created by --dry-run: "
        f"{claude_gitignore.read_text() if claude_gitignore.exists() else ''!r}"
    )
    assert not opencode_gitignore.exists(), (
        f".opencode/.gitignore must NOT be created by --dry-run: "
        f"{opencode_gitignore.read_text() if opencode_gitignore.exists() else ''!r}"
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


# ---------------------------------------------------------------------------
# PER-131: rollback when agent wire fails mid-sync
# ---------------------------------------------------------------------------


def test_sync_rollback_when_agent_wire_fails(
    project_dir: Path, warehouse: Path, monkeypatch
):
    """A wire failure mid-sync rolls back successfully-wired agent symlinks.

    Regression guard for PER-131: wire_agent_claudecode / wire_agent_opencode
    can raise BeaconSyncError (e.g., regular file at destination per the
    round-5 user-owned-content policy). Without rollback, the project ends up
    half-wired. The wire_agents_atomically helper must restore all wired
    destinations to their pre-wire state before re-raising.
    """
    runner = CliRunner()
    monkeypatch.chdir(project_dir)

    # Add a second agent to the warehouse so we have two to wire.
    (warehouse / "agents" / "agent-b.md").write_text(
        "---\nname: agent-b\n---\n# Agent B\n"
    )
    manifest_path = warehouse / "agents" / "agents.yaml"
    manifest = yaml.safe_load(manifest_path.read_text()) or {}
    manifest["agent-b"] = {"skills": []}
    manifest_path.write_text(yaml.safe_dump(manifest))
    _git_add_commit(warehouse, "add agent-b")

    # Plant a regular file at agent-b's .claude destination so the second
    # agent's claudecode wire raises BeaconSyncError (user-owned-content
    # policy). agent-a's .claude wire must have already succeeded by then;
    # rollback must remove it.
    (project_dir / ".claude" / "agents").mkdir(parents=True, exist_ok=True)
    (project_dir / ".claude" / "agents" / "agent-b.md").write_text("user content")

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  contexts: []\n"
        "  skills: []\n"
        "  agents:\n"
        "    - agents/spec-planner.md\n"
        "    - agents/agent-b.md\n"
    )

    # Act: sync must fail due to the regular-file blocker on agent-b.
    r = runner.invoke(main, ["sync", "--skip-git-check"])
    assert r.exit_code != 0, (
        f"sync should have failed but exited {r.exit_code}: {r.output}"
    )

    # Assert: spec-planner's .claude destination was rolled back.
    cc_a = project_dir / ".claude" / "agents" / "spec-planner.md"
    assert not cc_a.exists() and not cc_a.is_symlink(), (
        f".claude/agents/spec-planner.md must be rolled back; "
        f"still present: {cc_a.is_symlink()=}, {cc_a.exists()=}"
    )

    # The user's regular file at agent-b's .claude dest must be UNTOUCHED.
    assert (project_dir / ".claude" / "agents" / "agent-b.md").read_text() == (
        "user content"
    ), "user-owned regular file must be preserved"


def test_sync_rollback_when_agent_wire_fails_dual_tool(
    project_dir: Path, warehouse: Path, monkeypatch
):
    """Dual-tool variant of the rollback regression guard.

    When BOTH .claude/ and .opencode/ exist, wire_agents_atomically takes
    two snapshots per agent (one per tool). The rollback must reverse all
    snapshots, not just one tool's. This test exercises the path where
    spec-planner is fully wired into BOTH tools before agent-b's opencode
    wire fails — both spec-planner destinations must be rolled back.
    """
    runner = CliRunner()
    monkeypatch.chdir(project_dir)

    # Add a second agent to the warehouse.
    (warehouse / "agents" / "agent-b.md").write_text(
        "---\nname: agent-b\n---\n# Agent B\n"
    )
    manifest_path = warehouse / "agents" / "agents.yaml"
    manifest = yaml.safe_load(manifest_path.read_text()) or {}
    manifest["agent-b"] = {"skills": []}
    manifest_path.write_text(yaml.safe_dump(manifest))
    _git_add_commit(warehouse, "add agent-b")

    # Ensure BOTH tool dirs exist so detect_agent_targets returns both.
    (project_dir / ".opencode").mkdir(exist_ok=True)

    # Plant a regular file at agent-b's .opencode destination — this is the
    # LAST wire in the helper's loop (claudecode runs first per agent), so
    # spec-planner is fully wired into BOTH tools AND agent-b's claudecode
    # wire succeeds before the opencode wire on agent-b fails. Rollback
    # must restore three previously-wired destinations.
    (project_dir / ".opencode" / "agents").mkdir(parents=True, exist_ok=True)
    (project_dir / ".opencode" / "agents" / "agent-b.md").write_text("user content")

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  contexts: []\n"
        "  skills: []\n"
        "  agents:\n"
        "    - agents/spec-planner.md\n"
        "    - agents/agent-b.md\n"
    )

    # Act: sync must fail due to the regular-file blocker on agent-b's .opencode.
    r = runner.invoke(main, ["sync", "--skip-git-check"])
    assert r.exit_code != 0, (
        f"sync should have failed but exited {r.exit_code}: {r.output}"
    )

    # Assert: spec-planner's BOTH destinations were rolled back.
    cc_a = project_dir / ".claude" / "agents" / "spec-planner.md"
    oc_a = project_dir / ".opencode" / "agents" / "spec-planner.md"
    assert not cc_a.exists() and not cc_a.is_symlink(), (
        f".claude/agents/spec-planner.md must be rolled back; "
        f"still present: {cc_a.is_symlink()=}, {cc_a.exists()=}"
    )
    assert not oc_a.exists() and not oc_a.is_symlink(), (
        f".opencode/agents/spec-planner.md must be rolled back; "
        f"still present: {oc_a.is_symlink()=}, {oc_a.exists()=}"
    )

    # Assert: agent-b's .claude wire was rolled back (it succeeded before
    # the opencode failure).
    cc_b = project_dir / ".claude" / "agents" / "agent-b.md"
    assert not cc_b.exists() and not cc_b.is_symlink(), (
        f".claude/agents/agent-b.md must be rolled back; "
        f"still present: {cc_b.is_symlink()=}, {cc_b.exists()=}"
    )

    # The user's regular file at agent-b's .opencode dest must be UNTOUCHED.
    assert (project_dir / ".opencode" / "agents" / "agent-b.md").read_text() == (
        "user content"
    ), "user-owned regular file must be preserved"


# ---------------------------------------------------------------------------
# PER-126 additions: cover edge cases from deleted test_agents_sync_command.py
# ---------------------------------------------------------------------------

# Case #1: opencode-only install


def test_sync_wires_only_opencode_when_no_claude_dir(
    project_dir: Path, warehouse: Path, monkeypatch
):
    """When only .opencode/ exists, only .opencode/agents/ is wired; no .claude/ error."""
    import shutil

    runner = CliRunner()
    monkeypatch.chdir(project_dir)

    # Remove .claude/ so only .opencode/ remains
    claude_dir = project_dir / ".claude"
    if claude_dir.exists():
        shutil.rmtree(claude_dir)
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

    # .opencode/agents/ symlink created
    opencode_link = project_dir / ".opencode" / "agents" / "spec-planner.md"
    assert opencode_link.is_symlink(), "Expected .opencode/agents/spec-planner.md"
    assert opencode_link.exists(), ".opencode/agents symlink is broken"

    # No .claude/ wiring (dir does not exist)
    claude_link = project_dir / ".claude" / "agents" / "spec-planner.md"
    assert not claude_link.exists() and not claude_link.is_symlink(), (
        "Expected no .claude/agents/ wiring when .claude/ dir is absent"
    )


# Case #3: both-tools install (happy path)


def test_sync_wires_both_tools_when_both_dirs_present(
    project_dir: Path, warehouse: Path, monkeypatch
):
    """When both .claude/ and .opencode/ exist, both tool dirs get agent symlinks."""
    runner = CliRunner()
    monkeypatch.chdir(project_dir)

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

    claude_link = project_dir / ".claude" / "agents" / "spec-planner.md"
    opencode_link = project_dir / ".opencode" / "agents" / "spec-planner.md"
    assert claude_link.is_symlink(), "Expected .claude/agents/spec-planner.md symlink"
    assert claude_link.exists(), ".claude/agents symlink is broken"
    assert opencode_link.is_symlink(), (
        "Expected .opencode/agents/spec-planner.md symlink"
    )
    assert opencode_link.exists(), ".opencode/agents symlink is broken"


# Case #5: idempotent re-run


def test_sync_is_idempotent(project_dir: Path, warehouse: Path, monkeypatch):
    """Running abc sync twice produces the same symlink state as running it once."""
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

    # First sync
    r = runner.invoke(main, ["sync", "--skip-git-check"])
    assert r.exit_code == 0, f"first sync failed: {r.output}"

    artifact = (
        project_dir / ".agentic-beacon" / "artifacts" / "agents" / "spec-planner.md"
    )
    claude_link = project_dir / ".claude" / "agents" / "spec-planner.md"
    assert artifact.is_symlink()
    assert claude_link.is_symlink()
    first_artifact_target = artifact.readlink()
    first_claude_target = claude_link.readlink()

    # Second sync — must exit 0 and leave symlinks unchanged
    r = runner.invoke(main, ["sync", "--skip-git-check"])
    assert r.exit_code == 0, f"second sync failed: {r.output}"

    assert artifact.is_symlink(), "Artifact symlink must persist after second sync"
    assert claude_link.is_symlink(), ".claude symlink must persist after second sync"
    assert artifact.readlink() == first_artifact_target, (
        "Artifact symlink target must be unchanged after idempotent sync"
    )
    assert claude_link.readlink() == first_claude_target, (
        ".claude symlink target must be unchanged after idempotent sync"
    )


# Case #10: warehouse-edits-visible (cross-project design property)


def test_warehouse_edits_visible_through_symlinks(
    project_dir: Path, warehouse: Path, monkeypatch
):
    """Warehouse edits are immediately visible through project artifact symlinks.

    Core cross-project visibility guarantee: artifact paths are symlinks to the
    warehouse, so any write to the warehouse file is reflected without re-running
    abc sync.
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

    artifact = (
        project_dir / ".agentic-beacon" / "artifacts" / "agents" / "spec-planner.md"
    )
    assert artifact.is_symlink()

    # Edit the warehouse source file directly
    warehouse_agent = warehouse / "agents" / "spec-planner.md"
    original_content = warehouse_agent.read_text()
    warehouse_agent.write_text(original_content + "\n## Cross-Project Edit\n")

    # Change must be immediately visible through the artifact symlink
    assert "Cross-Project Edit" in artifact.read_text(), (
        "Warehouse edit must be visible through the artifact symlink without re-syncing"
    )


# Case #12: broken-symlink-repair


def test_sync_repairs_broken_symlink(project_dir: Path, warehouse: Path, monkeypatch):
    """A dangling .claude/agents/<name>.md symlink (target missing) is repaired by sync.

    wire_agent_claudecode replaces any symlink whose resolved target differs from
    the current artifact file, which covers broken (dangling) symlinks as well as
    stale ones.
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

    # First sync to establish the symlink chain
    r = runner.invoke(main, ["sync", "--skip-git-check"])
    assert r.exit_code == 0, f"first sync failed: {r.output}"

    claude_link = project_dir / ".claude" / "agents" / "spec-planner.md"
    assert claude_link.is_symlink()
    assert claude_link.exists()

    # Plant a broken symlink: unlink the correct symlink and replace it with
    # one that points to a non-existent path (dangling).
    ghost_target = project_dir / "ghost-agent.md"  # never created → always missing
    claude_link.unlink()
    claude_link.symlink_to(ghost_target)
    assert claude_link.is_symlink(), "Broken symlink must be recognised as a symlink"
    assert not claude_link.exists(), (
        "Broken symlink must not resolve to an existing file"
    )

    # Second sync must repair the broken symlink
    r = runner.invoke(main, ["sync", "--skip-git-check"])
    assert r.exit_code == 0, (
        f"second sync failed (broken symlink not repaired): {r.output}"
    )

    assert claude_link.is_symlink(), "Repaired path must be a symlink"
    assert claude_link.exists(), "Repaired symlink must resolve to an existing file"

    expected_artifact = (
        project_dir / ".agentic-beacon" / "artifacts" / "agents" / "spec-planner.md"
    )
    assert claude_link.resolve(strict=True) == expected_artifact.resolve(strict=True), (
        f"Repaired symlink resolves to {claude_link.resolve()} "
        f"but expected {expected_artifact.resolve()}"
    )


# Case #13: README-ignored


def test_readme_filtered_from_warehouse_agent_catalog(
    project_dir: Path, warehouse: Path, monkeypatch
):
    """_list_agents() excludes README.md from the agent catalog (discovery filter only).

    WarehouseDistributor._list_agents() excludes files whose uppercase name
    equals "README.MD" (guard: ``file.name.upper() != "README.MD"``), so
    README.md cannot appear in the catalog returned to abc adopt / abc sync.
    This test calls _list_agents() directly to exercise that catalog-discovery
    guard; it does NOT cover the sync wiring path. There is no sync-time guard
    that refuses to wire agents/README.md if a user manually adds it to
    beacon.yaml — sync will attempt to wire whatever is declared there.
    """
    from beacon.domains.distribution.distributor import WarehouseDistributor

    # Plant a README.md alongside a real agent definition in the warehouse.
    readme = warehouse / "agents" / "README.md"
    readme.write_text("# Agents Directory\nContains agent definitions.\n")

    distributor = WarehouseDistributor(
        warehouse_root=warehouse, target_root=project_dir
    )
    agent_list = distributor._list_agents(warehouse / "agents")

    # The real agent must be discoverable …
    assert "agents/spec-planner.md" in agent_list, (
        f"spec-planner.md must appear in agent list; got: {agent_list}"
    )
    # … but README.md must be excluded by the README.MD guard.
    assert "agents/README.md" not in agent_list, (
        f"README.md must be filtered from agent list; got: {agent_list}"
    )


# ---------------------------------------------------------------------------
# PER-164: agent partials co-distribution
# ---------------------------------------------------------------------------


def test_sync_with_agent_partials(project_dir: Path, warehouse: Path, monkeypatch):
    """Warehouse with agents/_partials/ — partials are synced and wired but NOT adoptable.

    Covers PER-164 Layer A (filter partials from agent listings) and
    Layer B (co-distribute partials alongside declared agents).
    """
    # Plant a partial file and an agent that references it.
    (warehouse / "agents" / "_partials").mkdir()
    (warehouse / "agents" / "_partials" / "deep-review-checklist.md").write_text(
        "## Deep Review Checklist\n- [ ] Item 1\n"
    )
    (warehouse / "agents" / "implementation-supervisor.md").write_text(
        "---\nname: implementation-supervisor\n---\n"
        "[`_partials/deep-review-checklist.md`](_partials/deep-review-checklist.md)\n"
    )
    manifest_path = warehouse / "agents" / "agents.yaml"
    manifest = yaml.safe_load(manifest_path.read_text()) or {}
    manifest["implementation-supervisor"] = {"skills": []}
    manifest_path.write_text(yaml.safe_dump(manifest))
    _git_add_commit(warehouse, "add partial and agent")

    runner = CliRunner()
    monkeypatch.chdir(project_dir)

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  contexts: []\n"
        "  skills: []\n"
        "  agents:\n"
        "    - agents/implementation-supervisor.md\n"
    )

    r = runner.invoke(main, ["sync", "--skip-git-check"])
    assert r.exit_code == 0, f"sync failed: {r.output}"

    # Partial must appear under .agentic-beacon/artifacts/agents/_partials/
    artifact_partial = (
        project_dir
        / ".agentic-beacon"
        / "artifacts"
        / "agents"
        / "_partials"
        / "deep-review-checklist.md"
    )
    assert artifact_partial.is_symlink(), (
        f"Expected artifact partial symlink at {artifact_partial}"
    )
    assert artifact_partial.exists(), (
        f"Artifact partial symlink is broken: {artifact_partial}"
    )

    # Partial must be wired into .claude/agents/_partials/ as a wrapper
    # (PER-238: regular file with `disable: true` frontmatter, not a raw
    # symlink — so opencode/Claude Code don't expose it as a callable agent).
    claude_partial = (
        project_dir / ".claude" / "agents" / "_partials" / "deep-review-checklist.md"
    )
    assert claude_partial.is_file() and not claude_partial.is_symlink(), (
        f"Expected .claude partial wrapper file at {claude_partial}"
    )
    wrapper_content = claude_partial.read_text()
    assert wrapper_content.startswith("---\n"), (
        f"Wrapper at {claude_partial} missing frontmatter fence"
    )
    assert "disable: true" in wrapper_content.split("\n---\n", 1)[0], (
        f"Wrapper at {claude_partial} missing disable: true"
    )
    # Original partial body must be inlined for relative-link resolution.
    assert "Deep Review Checklist" in wrapper_content, (
        f"Wrapper at {claude_partial} missing original partial body"
    )

    # Partial must NOT be discoverable as an adoptable agent.
    from beacon.domains.distribution.distributor import WarehouseDistributor

    distributor = WarehouseDistributor(
        warehouse_root=warehouse, target_root=project_dir
    )
    agent_list = distributor._list_agents(warehouse / "agents")
    assert "agents/_partials/deep-review-checklist.md" not in agent_list, (
        f"Partial must not appear in agent list; got: {agent_list}"
    )
    assert "agents/implementation-supervisor.md" in agent_list, (
        f"Real agent must still be listed; got: {agent_list}"
    )
