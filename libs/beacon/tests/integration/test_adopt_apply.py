"""Integration tests for commit_session() — happy path + rollback."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from beacon.core.manifest.pending import PendingEntry, PendingManifest
from beacon.domains.adoption.apply import CommitError, commit_session
from beacon.domains.adoption.models import AdoptCandidate

# ─────────────────────────────────────────────────────────────
# Fixtures / helpers
# ─────────────────────────────────────────────────────────────


def _git_init(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=path,
        check=True,
        capture_output=True,
    )


def _git_commit(path: Path, msg: str = "add files") -> None:
    subprocess.run(["git", "add", "-A"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", msg],
        cwd=path,
        check=True,
        capture_output=True,
    )


@pytest.fixture()
def warehouse(tmp_path: Path) -> Path:
    wh = tmp_path / "warehouse"
    wh.mkdir()
    _git_init(wh)
    for d in ["contexts", "skills", "knowledge"]:
        (wh / d).mkdir()
    (wh / "contexts" / "ctx-a.md").write_text("# Ctx A\n")
    (wh / "contexts" / "ctx-b.md").write_text("# Ctx B\n")
    (wh / "contexts" / "ctx-c.md").write_text("# Ctx C\n")
    (wh / "knowledge" / "k.md").write_text("# Knowledge\n")
    _git_commit(wh, "initial warehouse")
    return wh


@pytest.fixture()
def project(tmp_path: Path, warehouse: Path) -> dict:
    """Project with 4 pending entries: ctx-a, ctx-b, ctx-reject, ctx-c."""
    p = tmp_path / "project"
    p.mkdir()
    ab = p / ".agentic-beacon"
    ab.mkdir()
    artifacts = ab / "artifacts"
    artifacts.mkdir()

    beacon_yaml = ab / "beacon.yaml"
    beacon_yaml.write_text("artifacts:\n  contexts: []\n  skills: []\n  agents: []\n")

    entries = [
        PendingEntry(
            path="contexts/ctx-a.md",
            type="context",
            action="created",
            source="record-knowledge",
            created_at=datetime(2026, 5, 6, 12, 0, 0, tzinfo=UTC),
        ),
        PendingEntry(
            path="contexts/ctx-b.md",
            type="context",
            action="created",
            source="record-knowledge",
            created_at=datetime(2026, 5, 6, 12, 0, 0, tzinfo=UTC),
        ),
        PendingEntry(
            path="contexts/ctx-reject.md",
            type="context",
            action="created",
            source="record-knowledge",
            created_at=datetime(2026, 5, 6, 12, 0, 0, tzinfo=UTC),
        ),
        PendingEntry(
            path="contexts/ctx-c.md",
            type="context",
            action="created",
            source="record-knowledge",
            created_at=datetime(2026, 5, 6, 12, 0, 0, tzinfo=UTC),
        ),
    ]
    PendingManifest(pending=entries).to_yaml(ab / "pending.yaml")

    return {
        "root": p,
        "ab": ab,
        "beacon_yaml": beacon_yaml,
        "artifacts": artifacts,
        "pending_yaml": ab / "pending.yaml",
        "pending_entries": entries,
    }


def _snapshot(paths: dict) -> tuple[bytes, bytes]:
    return (
        paths["beacon_yaml"].read_bytes(),
        paths["pending_yaml"].read_bytes(),
    )


# ─────────────────────────────────────────────────────────────
# Happy path: pending accept + reject + defer in one commit
# ─────────────────────────────────────────────────────────────


def test_happy_path(project: dict, warehouse: Path):
    """2 pending accept + 1 pending reject + 1 defer → all invariants hold."""
    commit_session(
        to_adopt=[],
        to_unadopt=[],
        pending_accept=["contexts/ctx-a.md", "contexts/ctx-b.md"],
        pending_reject=["contexts/ctx-reject.md"],
        candidates=[],
        pending_entries=project["pending_entries"],
        project_root=project["root"],
        warehouse_path=warehouse,
        artifacts_path=project["artifacts"],
        beacon_yaml_path=project["beacon_yaml"],
    )

    # Invariant 1: beacon.yaml has 2 accepted contexts
    with open(project["beacon_yaml"]) as f:
        data = yaml.safe_load(f)
    assert "contexts/ctx-a.md" in data["artifacts"]["contexts"]
    assert "contexts/ctx-b.md" in data["artifacts"]["contexts"]
    assert "contexts/ctx-reject.md" not in data["artifacts"]["contexts"]
    assert "contexts/ctx-c.md" not in data["artifacts"]["contexts"]

    # Invariant 2: Symlinks for accepted entries
    assert (project["artifacts"] / "contexts" / "ctx-a.md").exists()
    assert (project["artifacts"] / "contexts" / "ctx-b.md").exists()
    assert not (project["artifacts"] / "contexts" / "ctx-c.md").exists()

    # Invariant 3: pending.yaml has only the deferred entry
    manifest = PendingManifest.from_yaml(project["pending_yaml"])
    remaining = [e.path for e in manifest.pending]
    assert remaining == ["contexts/ctx-c.md"]


# ─────────────────────────────────────────────────────────────
# Rollback on symlink failure
# ─────────────────────────────────────────────────────────────


def test_rollback_on_symlink_failure(project: dict, warehouse: Path):
    """Injected symlink failure mid-commit → both files restored, error identifies entry."""
    pre = _snapshot(project)

    call_count = [0]

    def _failing_on_second(artifact_paths: list[str], **kwargs):
        call_count[0] += 1
        if call_count[0] == 2:
            raise RuntimeError("injected failure on ctx-b.md")

    with pytest.raises(CommitError) as exc_info:
        commit_session(
            to_adopt=[],
            to_unadopt=[],
            pending_accept=[
                "contexts/ctx-a.md",
                "contexts/ctx-b.md",
                "contexts/ctx-c.md",
            ],
            pending_reject=[],
            candidates=[],
            pending_entries=project["pending_entries"],
            project_root=project["root"],
            warehouse_path=warehouse,
            artifacts_path=project["artifacts"],
            beacon_yaml_path=project["beacon_yaml"],
            _symlink_sync_fn=_failing_on_second,
        )

    # Both files restored byte-for-byte
    post = _snapshot(project)
    assert pre == post, "Both files must be byte-identical after rollback"

    # Error message identifies the failing entry
    assert "ctx-b.md" in str(exc_info.value)


# ─────────────────────────────────────────────────────────────
# Mixed warehouse + pending in one commit
# ─────────────────────────────────────────────────────────────


def test_mixed_warehouse_and_pending(tmp_path: Path, warehouse: Path):
    """Warehouse adopt + pending accept land atomically in beacon.yaml."""
    p = tmp_path / "mixed-project"
    p.mkdir()
    ab = p / ".agentic-beacon"
    ab.mkdir()
    artifacts = ab / "artifacts"
    artifacts.mkdir()
    beacon_yaml = ab / "beacon.yaml"
    beacon_yaml.write_text("artifacts:\n  contexts: []\n  skills: []\n  agents: []\n")

    # Only ctx-b is pending; ctx-a is a warehouse-only pick.
    pending_entries = [
        PendingEntry(
            path="contexts/ctx-b.md",
            type="context",
            action="created",
            source="record-knowledge",
            created_at=datetime(2026, 5, 6, 12, 0, tzinfo=UTC),
        ),
    ]
    PendingManifest(pending=pending_entries).to_yaml(ab / "pending.yaml")

    commit_session(
        to_adopt=["contexts/ctx-a.md"],  # warehouse browser pick
        to_unadopt=[],
        pending_accept=["contexts/ctx-b.md"],  # pending TODO accept
        pending_reject=[],
        candidates=[AdoptCandidate(artifact_type="contexts", path="contexts/ctx-a.md")],
        pending_entries=pending_entries,
        project_root=p,
        warehouse_path=warehouse,
        artifacts_path=artifacts,
        beacon_yaml_path=beacon_yaml,
    )

    data = yaml.safe_load(beacon_yaml.read_text())
    assert "contexts/ctx-a.md" in data["artifacts"]["contexts"]
    assert "contexts/ctx-b.md" in data["artifacts"]["contexts"]

    manifest = PendingManifest.from_yaml(ab / "pending.yaml")
    assert manifest.pending == []  # ctx-b accepted = removed


# ═════════════════════════════════════════════════════════════
# FIX A: adopt with no tool dirs → bundled-skills wiring creates them
#   → apply_all_gitignores runs LAST and writes Tier B
# ═════════════════════════════════════════════════════════════


def test_adopt_with_no_tool_dirs_creates_tier_b(tmp_path: Path, warehouse: Path):
    """Adopt-accept on a project with NO pre-existing .claude//.opencode/
    must end with BOTH Tier A root block AND Tier B nested .gitignore."""
    # Add a skill to the warehouse
    skill_dir = warehouse / "skills" / "my-test-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: my-test-skill\ndescription: Test skill\n"
        "requires:\n  contexts: []\n---\n# Test\n"
    )
    _git_commit(warehouse, "add skill")

    p = tmp_path / "fix-a-project"
    p.mkdir()
    ab = p / ".agentic-beacon"
    ab.mkdir()
    artifacts = ab / "artifacts"
    artifacts.mkdir()
    beacon_yaml = ab / "beacon.yaml"
    beacon_yaml.write_text("artifacts:\n  contexts: []\n  skills: []\n  agents: []\n")

    commit_session(
        to_adopt=["skills/my-test-skill/"],
        to_unadopt=[],
        pending_accept=[],
        pending_reject=[],
        candidates=[
            AdoptCandidate(artifact_type="skills", path="skills/my-test-skill/")
        ],
        pending_entries=[],
        project_root=p,
        warehouse_path=warehouse,
        artifacts_path=artifacts,
        beacon_yaml_path=beacon_yaml,
    )

    # Tier A root block must be present
    root_gitignore = p / ".gitignore"
    assert root_gitignore.exists(), "Tier A .gitignore must exist"
    root_content = root_gitignore.read_text()
    assert ">>> Agentic Beacon (managed) >>>" in root_content, (
        "Root managed block must exist"
    )

    # Tier B .gitignore must exist for any tool dir that was created
    claude_gitignore = p / ".claude" / ".gitignore"
    opencode_gitignore = p / ".opencode" / ".gitignore"
    assert claude_gitignore.exists(), (
        "Tier B .claude/.gitignore must exist after adopt with skill wiring"
    )
    assert opencode_gitignore.exists(), (
        "Tier B .opencode/.gitignore must exist after adopt with skill wiring"
    )
    for tb in (claude_gitignore, opencode_gitignore):
        tb_content = tb.read_text()
        assert ">>> Agentic Beacon (managed) >>>" in tb_content, (
            f"Tier B managed block must exist in {tb}"
        )


# ═════════════════════════════════════════════════════════════
# FIX L: gitignore rollback
# ═════════════════════════════════════════════════════════════


def test_rollback_restores_gitignore_after_post_sync_failure(
    project: dict, warehouse: Path, monkeypatch
):
    """Injected failure in apply_all_gitignores → gitignore files restored on rollback.

    Uses monkeypatch so that apply_all_gitignores writes its real content (via
    the original implementation) and THEN raises. The snapshots captured by the
    new gitignore_snapshots code in _default_post_sync_writing fire before the
    write, so _rollback() must restore pre-state bytes (or remove files that
    didn't exist before).
    """
    pre = _snapshot(project)

    root_gi = project["root"] / ".gitignore"
    claude_gi = project["root"] / ".claude" / ".gitignore"
    opencode_gi = project["root"] / ".opencode" / ".gitignore"

    def _gi_state(path: Path) -> bytes | None:
        return path.read_bytes() if path.exists() else None

    pre_root_gi = _gi_state(root_gi)
    pre_claude_gi = _gi_state(claude_gi)
    pre_opencode_gi = _gi_state(opencode_gi)

    from beacon.core.gitignore import apply_all_gitignores as _real_apply

    def _failing_apply(project_root):
        _real_apply(project_root)
        raise RuntimeError("forced post-gitignore failure")

    monkeypatch.setattr(
        "beacon.core.gitignore.apply_all_gitignores",
        _failing_apply,
    )

    with pytest.raises(CommitError):
        commit_session(
            to_adopt=[],
            to_unadopt=[],
            pending_accept=["contexts/ctx-a.md", "contexts/ctx-b.md"],
            pending_reject=["contexts/ctx-reject.md"],
            candidates=[],
            pending_entries=project["pending_entries"],
            project_root=project["root"],
            warehouse_path=warehouse,
            artifacts_path=project["artifacts"],
            beacon_yaml_path=project["beacon_yaml"],
        )

    # beacon.yaml and pending.yaml restored
    post = _snapshot(project)
    assert pre == post, (
        "beacon.yaml and pending.yaml must be byte-identical after rollback"
    )

    # gitignore files restored to pre-state
    assert _gi_state(root_gi) == pre_root_gi, "root .gitignore must be restored"
    assert _gi_state(claude_gi) == pre_claude_gi, ".claude/.gitignore must be restored"
    assert _gi_state(opencode_gi) == pre_opencode_gi, (
        ".opencode/.gitignore must be restored"
    )
