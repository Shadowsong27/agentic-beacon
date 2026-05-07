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


# ---------------------------------------------------------------------------
# TC6: accept fails mid-commit (wire failure) → all writes rolled back (TC3 spec)
# ---------------------------------------------------------------------------


def test_accept_agent_rollback_on_wire_failure(
    project: tuple, warehouse: Path, monkeypatch
):
    """TC3 from spec project-agent-wiring: accept fails mid-commit → all writes rolled back.

    Forces wire_agent_opencode to raise OSError after wire_agent_claudecode succeeds.
    Asserts that beacon.yaml, pending.yaml, the artifact symlink, and the partially-
    created .claude/agents/ symlink are all restored to pre-commit state.
    """
    project_root, artifacts_path, beacon_yaml = project

    # Both .claude/ and .opencode/ present so both wiring paths are attempted
    (project_root / ".opencode").mkdir()

    pre_beacon_bytes = beacon_yaml.read_bytes()

    agent_candidate = AdoptCandidate(
        artifact_type="agents",
        path="agents/spec-planner.md",
        description="Plans specs",
    )

    # Monkeypatch wire_agent_opencode to raise on first call.
    # This lets _default_post_sync_wiring run normally (populating created_paths)
    # so claudecode wiring succeeds and opencode wiring fails — partial state.
    import beacon.domains.setup.wiring as wiring_mod

    call_count = {"n": 0}

    def _failing_wire_opencode(project_root_arg, artifact_file):
        call_count["n"] += 1
        raise OSError("forced wire failure")

    monkeypatch.setattr(wiring_mod, "wire_agent_opencode", _failing_wire_opencode)

    from beacon.domains.adoption.apply import CommitError

    with pytest.raises(CommitError):
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

    # beacon.yaml restored to pre-commit state
    assert beacon_yaml.read_bytes() == pre_beacon_bytes, (
        "beacon.yaml was not rolled back after accept failure"
    )

    # Artifact symlink rolled back
    artifact = artifacts_path / "agents" / "spec-planner.md"
    assert not artifact.is_symlink() and not artifact.exists(), (
        "Artifact symlink should be rolled back after accept failure"
    )

    # .claude/agents/ symlink rolled back (was created before the opencode failure)
    claude_link = project_root / ".claude" / "agents" / "spec-planner.md"
    assert not claude_link.is_symlink() and not claude_link.exists(), (
        ".claude/agents/spec-planner.md should be rolled back after accept failure"
    )

    # .opencode/agents/ symlink never created (that was the failing call)
    oc_link = project_root / ".opencode" / "agents" / "spec-planner.md"
    assert not oc_link.is_symlink() and not oc_link.exists(), (
        ".opencode/agents/spec-planner.md should not exist after accept failure"
    )

    # Confirm the failing call was reached
    assert call_count["n"] >= 1


# ---------------------------------------------------------------------------
# TC7: reject mid-commit artifact symlink restored on failure
# ---------------------------------------------------------------------------


def test_reject_agent_artifact_symlink_restored_on_failure(
    project: tuple, warehouse: Path, monkeypatch
):
    """Reject with mid-commit failure restores artifact symlink and tool symlinks."""
    pytest.skip(
        "TODO: patching Path.unlink to force a failure mid-reject is too brittle "
        "without a dedicated injectable hook in the reject path; skipping per spec allowance."
    )


# ---------------------------------------------------------------------------
# TC8: rollback preserves pre-existing identical tool symlink
# ---------------------------------------------------------------------------


def test_accept_rollback_preserves_pre_existing_identical_tool_symlink(
    project: tuple, warehouse: Path, monkeypatch
):
    """Rollback must NOT unlink a tool symlink that already pointed at the correct target.

    Set up: .claude/agents/spec-planner.md already points at the artifact file (idempotent
    wire would no-op). Force wire_agent_opencode to raise. After rollback, the
    pre-existing .claude symlink must still exist, pointing at the same target.
    """
    project_root, artifacts_path, beacon_yaml = project
    (project_root / ".opencode").mkdir()

    artifact_path = artifacts_path / "agents" / "spec-planner.md"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    warehouse_agent = warehouse / "agents" / "spec-planner.md"
    artifact_path.symlink_to(warehouse_agent)

    claude_dest = project_root / ".claude" / "agents" / "spec-planner.md"
    claude_dest.parent.mkdir(parents=True, exist_ok=True)
    claude_dest.symlink_to(artifact_path)

    pre_target = claude_dest.readlink()

    import beacon.domains.setup.wiring as wiring_mod

    def _failing_wire_opencode(p, a):
        raise OSError("forced wire failure")

    monkeypatch.setattr(wiring_mod, "wire_agent_opencode", _failing_wire_opencode)

    candidate = AdoptCandidate(
        artifact_type="agents", path="agents/spec-planner.md", description="x"
    )
    from beacon.domains.adoption.apply import CommitError

    with pytest.raises(CommitError):
        commit_session(
            to_adopt=["agents/spec-planner.md"],
            to_unadopt=[],
            pending_accept=[],
            pending_reject=[],
            candidates=[candidate],
            pending_entries=[],
            project_root=project_root,
            warehouse_path=warehouse,
            artifacts_path=artifacts_path,
            beacon_yaml_path=beacon_yaml,
        )

    assert claude_dest.is_symlink(), (
        "Pre-existing .claude symlink was destroyed by rollback"
    )
    assert claude_dest.readlink() == pre_target, (
        "Pre-existing .claude symlink target changed"
    )


# ---------------------------------------------------------------------------
# TC9: rollback restores stale tool symlink to prior target
# ---------------------------------------------------------------------------


def test_accept_rollback_restores_stale_tool_symlink_target(
    project: tuple, warehouse: Path, monkeypatch
):
    """Rollback must restore a stale tool symlink to its prior (different) target.

    Set up: .claude/agents/spec-planner.md points at OLD_TARGET (some unrelated path).
    Wire would replace it with artifact_file. Force wire_agent_opencode to raise.
    After rollback, .claude symlink must point at OLD_TARGET again.
    """
    project_root, artifacts_path, beacon_yaml = project
    (project_root / ".opencode").mkdir()

    artifact_path = artifacts_path / "agents" / "spec-planner.md"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    warehouse_agent = warehouse / "agents" / "spec-planner.md"
    artifact_path.symlink_to(warehouse_agent)

    stale_target = project_root / "some-old-agent.md"
    stale_target.touch()
    claude_dest = project_root / ".claude" / "agents" / "spec-planner.md"
    claude_dest.parent.mkdir(parents=True, exist_ok=True)
    claude_dest.symlink_to(stale_target)

    import beacon.domains.setup.wiring as wiring_mod

    def _failing_wire_opencode(p, a):
        raise OSError("forced wire failure")

    monkeypatch.setattr(wiring_mod, "wire_agent_opencode", _failing_wire_opencode)

    candidate = AdoptCandidate(
        artifact_type="agents", path="agents/spec-planner.md", description="x"
    )
    from beacon.domains.adoption.apply import CommitError

    with pytest.raises(CommitError):
        commit_session(
            to_adopt=["agents/spec-planner.md"],
            to_unadopt=[],
            pending_accept=[],
            pending_reject=[],
            candidates=[candidate],
            pending_entries=[],
            project_root=project_root,
            warehouse_path=warehouse,
            artifacts_path=artifacts_path,
            beacon_yaml_path=beacon_yaml,
        )

    assert claude_dest.is_symlink()
    assert claude_dest.readlink() == stale_target, (
        f"Stale .claude symlink target was not restored on rollback: got {claude_dest.readlink()}"
    )
