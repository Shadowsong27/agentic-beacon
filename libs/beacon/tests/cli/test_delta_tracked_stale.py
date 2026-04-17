"""Tests for _enrich_tracked_stale — MODIFIED→STALE enrichment for tracked artifacts.

Covers:
- TC1: Knowledge file MODIFIED, local == synced content → enriched to STALE
- TC2: Knowledge file MODIFIED, local != synced content (user edit) → stays MODIFIED
- TC3: No git in warehouse → no enrichment (falls back silently)
- TC4: No sync SHA recorded → no enrichment
- TC5: Snapshot current (sync SHA == HEAD) → no enrichment
- TC6: Skill file MODIFIED per-agent, live skill == synced → per-agent STALE
- TC7: Skill file MODIFIED per-agent, live skill != synced (user edit) → stays MODIFIED
"""

import hashlib
import subprocess
from pathlib import Path

import pytest
from beacon.cli import _enrich_tracked_stale
from beacon.core.delta import (
    ComparisonResult,
    DeltaComparator,
    DeltaStatus,
    DeltaSummary,
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_sync_state_sha(artifacts_path: Path, sha: str) -> None:
    state_file = artifacts_path / ".sync-state"
    artifacts_path.mkdir(parents=True, exist_ok=True)
    state_file.write_text(sha + "\n")


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init", str(path)], capture_output=True, check=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "test@test.com"],
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "Test"],
        capture_output=True,
        check=True,
    )


def _git_commit(warehouse: Path, files: dict[str, str]) -> str:
    """Write files and commit them; return the commit SHA."""
    for rel_path, content in files.items():
        dest = warehouse / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
        subprocess.run(
            ["git", "-C", str(warehouse), "add", rel_path],
            capture_output=True,
            check=True,
        )
    subprocess.run(
        ["git", "-C", str(warehouse), "commit", "-m", "test commit"],
        capture_output=True,
        check=True,
    )
    result = subprocess.run(
        ["git", "-C", str(warehouse), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


@pytest.fixture
def warehouse(tmp_path):
    wh = tmp_path / "warehouse"
    wh.mkdir()
    _init_git_repo(wh)
    return wh


@pytest.fixture
def artifacts(tmp_path):
    art = tmp_path / "artifacts"
    art.mkdir()
    return art


@pytest.fixture
def comparator_factory(warehouse, artifacts):
    def _make(skills_paths=None):
        return DeltaComparator(
            warehouse_path=warehouse,
            artifacts_path=artifacts,
            skills_paths=skills_paths or {},
        )

    return _make


# ---------------------------------------------------------------------------
# TC1: knowledge file — user hasn't changed it, warehouse updated → STALE
# ---------------------------------------------------------------------------


def test_tc1_knowledge_user_unchanged_becomes_stale(
    warehouse, artifacts, comparator_factory
):
    original = b"# Knowledge v1\noriginal content\n"
    updated = b"# Knowledge v2\nupdated by maintainer\n"

    # Commit v1
    sha_v1 = _git_commit(warehouse, {"knowledge/doc.md": original.decode()})

    # User synced at v1
    local_file = artifacts / "knowledge" / "doc.md"
    local_file.parent.mkdir(parents=True, exist_ok=True)
    local_file.write_bytes(original)
    _write_sync_state_sha(artifacts, sha_v1)

    # Warehouse updated to v2
    _git_commit(warehouse, {"knowledge/doc.md": updated.decode()})

    local_hash = _sha256(original)
    warehouse_hash = _sha256(updated)

    summary = DeltaSummary(
        results=[
            ComparisonResult(
                path="knowledge/doc.md",
                status=DeltaStatus.MODIFIED,
                local_hash=local_hash,
                warehouse_hash=warehouse_hash,
            )
        ]
    )

    enriched = _enrich_tracked_stale(
        summary,
        warehouse_path=warehouse,
        artifacts_path=artifacts,
        comparator=comparator_factory(),
    )

    assert enriched.results[0].status == DeltaStatus.STALE
    assert enriched.stale == [enriched.results[0]]


# ---------------------------------------------------------------------------
# TC2: knowledge file — user edited it locally → stays MODIFIED
# ---------------------------------------------------------------------------


def test_tc2_knowledge_user_edited_stays_modified(
    warehouse, artifacts, comparator_factory
):
    original = b"# Knowledge v1\noriginal content\n"
    user_edited = b"# Knowledge v1\noriginal content\nuser added this\n"
    updated = b"# Knowledge v2\nupdated by maintainer\n"

    sha_v1 = _git_commit(warehouse, {"knowledge/doc.md": original.decode()})

    # User synced at v1 then edited locally
    local_file = artifacts / "knowledge" / "doc.md"
    local_file.parent.mkdir(parents=True, exist_ok=True)
    local_file.write_bytes(user_edited)
    _write_sync_state_sha(artifacts, sha_v1)

    _git_commit(warehouse, {"knowledge/doc.md": updated.decode()})

    summary = DeltaSummary(
        results=[
            ComparisonResult(
                path="knowledge/doc.md",
                status=DeltaStatus.MODIFIED,
                local_hash=_sha256(user_edited),
                warehouse_hash=_sha256(updated),
            )
        ]
    )

    enriched = _enrich_tracked_stale(
        summary,
        warehouse_path=warehouse,
        artifacts_path=artifacts,
        comparator=comparator_factory(),
    )

    assert enriched.results[0].status == DeltaStatus.MODIFIED


# ---------------------------------------------------------------------------
# TC3: no git in warehouse → no enrichment
# ---------------------------------------------------------------------------


def test_tc3_no_git_no_enrichment(tmp_path, artifacts):
    plain_warehouse = tmp_path / "plain"
    plain_warehouse.mkdir()
    (plain_warehouse / "knowledge").mkdir()
    (plain_warehouse / "knowledge" / "doc.md").write_text("content")

    _write_sync_state_sha(artifacts, "someshasha")

    comparator = DeltaComparator(
        warehouse_path=plain_warehouse,
        artifacts_path=artifacts,
    )

    summary = DeltaSummary(
        results=[
            ComparisonResult(
                path="knowledge/doc.md",
                status=DeltaStatus.MODIFIED,
            )
        ]
    )

    enriched = _enrich_tracked_stale(
        summary,
        warehouse_path=plain_warehouse,
        artifacts_path=artifacts,
        comparator=comparator,
    )

    assert enriched.results[0].status == DeltaStatus.MODIFIED


# ---------------------------------------------------------------------------
# TC4: no sync SHA recorded → no enrichment
# ---------------------------------------------------------------------------


def test_tc4_no_sync_sha_no_enrichment(warehouse, artifacts, comparator_factory):
    _git_commit(warehouse, {"knowledge/doc.md": "content"})
    # No _write_sync_state_sha call → .sync-state absent

    summary = DeltaSummary(
        results=[ComparisonResult(path="knowledge/doc.md", status=DeltaStatus.MODIFIED)]
    )

    enriched = _enrich_tracked_stale(
        summary,
        warehouse_path=warehouse,
        artifacts_path=artifacts,
        comparator=comparator_factory(),
    )

    assert enriched.results[0].status == DeltaStatus.MODIFIED


# ---------------------------------------------------------------------------
# TC5: snapshot current (sync SHA == HEAD) → no enrichment
# ---------------------------------------------------------------------------


def test_tc5_snapshot_current_no_enrichment(warehouse, artifacts, comparator_factory):
    sha = _git_commit(warehouse, {"knowledge/doc.md": "content"})
    _write_sync_state_sha(artifacts, sha)  # snapshot is up to date

    summary = DeltaSummary(
        results=[ComparisonResult(path="knowledge/doc.md", status=DeltaStatus.MODIFIED)]
    )

    enriched = _enrich_tracked_stale(
        summary,
        warehouse_path=warehouse,
        artifacts_path=artifacts,
        comparator=comparator_factory(),
    )

    assert enriched.results[0].status == DeltaStatus.MODIFIED


# ---------------------------------------------------------------------------
# TC6: skill file — live skill unchanged since sync → per-agent STALE
# ---------------------------------------------------------------------------


def test_tc6_skill_user_unchanged_becomes_stale(tmp_path, warehouse, artifacts):
    original = b"# Skill v1\noriginal\n"
    updated = b"# Skill v2\nupdated\n"

    skill_rel = "skills/my-skill/SKILL.md"

    sha_v1 = _git_commit(warehouse, {skill_rel: original.decode()})

    # Live agent skill dirs
    opencode_skills = tmp_path / ".opencode" / "skills"
    claude_skills = tmp_path / ".claude" / "skills"
    for d in (opencode_skills, claude_skills):
        skill_dir = d / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_bytes(original)  # still at synced version

    _write_sync_state_sha(artifacts, sha_v1)

    _git_commit(warehouse, {skill_rel: updated.decode()})

    comparator = DeltaComparator(
        warehouse_path=warehouse,
        artifacts_path=artifacts,
        skills_paths={"opencode": opencode_skills, "claudecode": claude_skills},
    )

    summary = DeltaSummary(
        results=[
            ComparisonResult(
                path=skill_rel,
                status=DeltaStatus.MODIFIED,
                warehouse_hash=_sha256(updated),
                agent_statuses={
                    "opencode": DeltaStatus.MODIFIED,
                    "claudecode": DeltaStatus.MODIFIED,
                },
            )
        ]
    )

    enriched = _enrich_tracked_stale(
        summary,
        warehouse_path=warehouse,
        artifacts_path=artifacts,
        comparator=comparator,
    )

    result = enriched.results[0]
    assert result.status == DeltaStatus.STALE
    assert result.agent_statuses["opencode"] == DeltaStatus.STALE
    assert result.agent_statuses["claudecode"] == DeltaStatus.STALE


# ---------------------------------------------------------------------------
# TC7: skill file — user edited live skill → stays MODIFIED
# ---------------------------------------------------------------------------


def test_tc7_skill_user_edited_stays_modified(tmp_path, warehouse, artifacts):
    original = b"# Skill v1\noriginal\n"
    user_edit = b"# Skill v1\noriginal\nuser added\n"
    updated = b"# Skill v2\nupdated\n"

    skill_rel = "skills/my-skill/SKILL.md"

    sha_v1 = _git_commit(warehouse, {skill_rel: original.decode()})

    claude_skills = tmp_path / ".claude" / "skills"
    skill_dir = claude_skills / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_bytes(user_edit)  # user edited it

    _write_sync_state_sha(artifacts, sha_v1)

    _git_commit(warehouse, {skill_rel: updated.decode()})

    comparator = DeltaComparator(
        warehouse_path=warehouse,
        artifacts_path=artifacts,
        skills_paths={"claudecode": claude_skills},
    )

    summary = DeltaSummary(
        results=[
            ComparisonResult(
                path=skill_rel,
                status=DeltaStatus.MODIFIED,
                warehouse_hash=_sha256(updated),
                agent_statuses={"claudecode": DeltaStatus.MODIFIED},
            )
        ]
    )

    enriched = _enrich_tracked_stale(
        summary,
        warehouse_path=warehouse,
        artifacts_path=artifacts,
        comparator=comparator,
    )

    assert enriched.results[0].status == DeltaStatus.MODIFIED
    assert enriched.results[0].agent_statuses["claudecode"] == DeltaStatus.MODIFIED
