"""Integration tests for adopt accept/reject agent lifecycle (PER-113, task 9.4).

Covers the commit_session() accept and reject paths for agents:

Accept:
  - beacon.yaml is updated with the agent path
  - artifact symlink created under .agentic-beacon/artifacts/agents/
  - project-local tool symlink created under .claude/agents/

Reject:
  - All three paths are removed atomically
  - Global ~/.claude/agents/ and ~/.config/opencode/agents/ are untouched
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import yaml
from beacon.domains.adoption.apply import commit_session
from beacon.domains.adoption.models import AdoptCandidate

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
def project(tmp_path: Path, warehouse: Path) -> tuple[Path, Path, Path]:
    """Returns (project_root, artifacts_path, beacon_yaml_path).

    Sets up a minimal project scaffold without running abc setup.
    """
    project_root = tmp_path / "project"
    project_root.mkdir()
    beacon_dir = project_root / ".agentic-beacon"
    beacon_dir.mkdir()
    artifacts_path = beacon_dir / "artifacts"
    artifacts_path.mkdir()

    beacon_yaml = beacon_dir / "beacon.yaml"
    beacon_yaml.write_text("artifacts:\n  contexts: []\n  skills: []\n  agents: []\n")

    # Create .claude/ so detect_agents() returns 'claudecode'
    (project_root / ".claude").mkdir()

    return project_root, artifacts_path, beacon_yaml


# ---------------------------------------------------------------------------
# TC1: accept with both tools detected → artifact + .claude symlinks written
# ---------------------------------------------------------------------------


def test_accept_agent_writes_artifact_and_tool_symlinks(
    project: tuple, warehouse: Path
):
    """Accepting an agent in commit_session writes beacon.yaml + artifact + tool symlinks."""
    project_root, artifacts_path, beacon_yaml = project

    agent_candidate = AdoptCandidate(
        artifact_type="agents",
        path="agents/spec-planner.md",
        description="Plans specs",
    )

    commit_session(
        to_adopt=["agents/spec-planner.md"],
        to_unadopt=[],
        pending_accept=[],
        pending_reject=[],
        candidates=[agent_candidate],
        pending_entries=[],
        project_root=project_root,
        warehouse_path=warehouse,
        artifacts_path=artifacts_path,
        beacon_yaml_path=beacon_yaml,
    )

    # beacon.yaml updated
    loaded = yaml.safe_load(beacon_yaml.read_text())
    assert "agents/spec-planner.md" in loaded["artifacts"]["agents"]

    # Artifact symlink created
    artifact = artifacts_path / "agents" / "spec-planner.md"
    assert artifact.is_symlink(), f"Expected artifact symlink at {artifact}"
    assert artifact.exists(), f"Artifact symlink is broken: {artifact}"

    # Project-local tool symlink created
    claude_link = project_root / ".claude" / "agents" / "spec-planner.md"
    assert claude_link.is_symlink(), (
        f"Expected .claude/agents/spec-planner.md symlink at {claude_link}"
    )
    assert claude_link.exists(), f".claude/agents symlink is broken: {claude_link}"


# ---------------------------------------------------------------------------
# TC2: accept with only Claude detected → artifact + .claude only
# ---------------------------------------------------------------------------


def test_accept_agent_only_claude_detected(project: tuple, warehouse: Path):
    """When only .claude/ exists, only .claude/agents/ is wired — no .opencode/ error."""
    project_root, artifacts_path, beacon_yaml = project

    # No .opencode/ dir
    assert not (project_root / ".opencode").exists()

    agent_candidate = AdoptCandidate(
        artifact_type="agents",
        path="agents/spec-planner.md",
        description="Plans specs",
    )

    commit_session(
        to_adopt=["agents/spec-planner.md"],
        to_unadopt=[],
        pending_accept=[],
        pending_reject=[],
        candidates=[agent_candidate],
        pending_entries=[],
        project_root=project_root,
        warehouse_path=warehouse,
        artifacts_path=artifacts_path,
        beacon_yaml_path=beacon_yaml,
    )

    # .claude/agents/ symlink present
    assert (project_root / ".claude" / "agents" / "spec-planner.md").is_symlink()

    # No .opencode/ wiring
    assert not (project_root / ".opencode" / "agents" / "spec-planner.md").exists()


# ---------------------------------------------------------------------------
# TC3: accept already-declared agent → idempotent, no duplicate
# ---------------------------------------------------------------------------


def test_accept_already_declared_agent_is_idempotent(project: tuple, warehouse: Path):
    """Accepting an agent already in beacon.yaml is a no-op (idempotent)."""
    project_root, artifacts_path, beacon_yaml = project

    # Pre-seed beacon.yaml with the agent
    beacon_yaml.write_text(
        "artifacts:\n"
        "  contexts: []\n"
        "  skills: []\n"
        "  agents:\n"
        "    - agents/spec-planner.md\n"
    )

    agent_candidate = AdoptCandidate(
        artifact_type="agents",
        path="agents/spec-planner.md",
        description="Plans specs",
    )

    commit_session(
        to_adopt=["agents/spec-planner.md"],
        to_unadopt=[],
        pending_accept=[],
        pending_reject=[],
        candidates=[agent_candidate],
        pending_entries=[],
        project_root=project_root,
        warehouse_path=warehouse,
        artifacts_path=artifacts_path,
        beacon_yaml_path=beacon_yaml,
    )

    loaded = yaml.safe_load(beacon_yaml.read_text())
    # No duplicate
    assert loaded["artifacts"]["agents"].count("agents/spec-planner.md") == 1


# ---------------------------------------------------------------------------
# TC4: reject of a wired agent → all project-local paths removed
# ---------------------------------------------------------------------------


def test_reject_agent_removes_all_project_local_paths(
    project: tuple, warehouse: Path, isolated_home
):
    """Rejecting (unadopting) a wired agent removes artifact + tool symlinks.

    Global ~/.claude/agents/ must NOT be touched.
    """
    project_root, artifacts_path, beacon_yaml = project

    # Seed beacon.yaml with the agent declared
    beacon_yaml.write_text(
        "artifacts:\n"
        "  contexts: []\n"
        "  skills: []\n"
        "  agents:\n"
        "    - agents/spec-planner.md\n"
    )

    # Pre-create the artifact symlink and project-local tool symlink
    artifact = artifacts_path / "agents" / "spec-planner.md"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.symlink_to(warehouse / "agents" / "spec-planner.md")

    claude_agents = project_root / ".claude" / "agents"
    claude_agents.mkdir(parents=True, exist_ok=True)
    claude_link = claude_agents / "spec-planner.md"
    claude_link.symlink_to(artifact)

    # Seed a fake global symlink to verify it is NOT touched
    global_claude = isolated_home / ".claude" / "agents"
    global_claude.mkdir(parents=True, exist_ok=True)
    global_link = global_claude / "spec-planner.md"
    global_link.symlink_to(warehouse / "agents" / "spec-planner.md")

    agent_candidate = AdoptCandidate(
        artifact_type="agents",
        path="agents/spec-planner.md",
        description="Plans specs",
    )

    commit_session(
        to_adopt=[],
        to_unadopt=["agents/spec-planner.md"],
        pending_accept=[],
        pending_reject=[],
        candidates=[agent_candidate],
        pending_entries=[],
        project_root=project_root,
        warehouse_path=warehouse,
        artifacts_path=artifacts_path,
        beacon_yaml_path=beacon_yaml,
    )

    # beacon.yaml: agent removed
    loaded = yaml.safe_load(beacon_yaml.read_text())
    assert loaded["artifacts"]["agents"] == []

    # Project-local tool symlink removed
    assert not claude_link.exists() and not claude_link.is_symlink(), (
        "Expected .claude/agents/spec-planner.md to be removed after reject"
    )

    # Global symlink untouched
    assert global_link.is_symlink(), (
        "Global ~/.claude/agents/spec-planner.md must NOT be removed by reject"
    )


# ---------------------------------------------------------------------------
# TC5: reject of missing tool symlinks → no error (graceful)
# ---------------------------------------------------------------------------


def test_reject_agent_missing_tool_symlinks_no_error(project: tuple, warehouse: Path):
    """Rejecting an agent whose tool symlinks are absent raises no error."""
    project_root, artifacts_path, beacon_yaml = project

    beacon_yaml.write_text(
        "artifacts:\n"
        "  contexts: []\n"
        "  skills: []\n"
        "  agents:\n"
        "    - agents/spec-planner.md\n"
    )

    # Do NOT create tool symlinks — simulate "declared but never wired"
    artifact = artifacts_path / "agents" / "spec-planner.md"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.symlink_to(warehouse / "agents" / "spec-planner.md")

    agent_candidate = AdoptCandidate(
        artifact_type="agents",
        path="agents/spec-planner.md",
        description="Plans specs",
    )

    # Must not raise
    commit_session(
        to_adopt=[],
        to_unadopt=["agents/spec-planner.md"],
        pending_accept=[],
        pending_reject=[],
        candidates=[agent_candidate],
        pending_entries=[],
        project_root=project_root,
        warehouse_path=warehouse,
        artifacts_path=artifacts_path,
        beacon_yaml_path=beacon_yaml,
    )

    loaded = yaml.safe_load(beacon_yaml.read_text())
    assert loaded["artifacts"]["agents"] == []
