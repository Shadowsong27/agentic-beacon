"""Tests for abc delta STALE enrichment (Phase 7, task 7.10).

TDD Test Cases (7.7):
- TC1: Agent file IDENTICAL, sync-state HEAD matches warehouse HEAD → displayed as IN SYNC
- TC2: Agent file IDENTICAL, sync-state HEAD differs from warehouse HEAD → enriched to STALE
- TC3: No sync-state entry for this agent file → no STALE enrichment, displayed as IN SYNC
- TC4: Agent file MODIFIED, no comparator passed → stays MODIFIED (can't distinguish)
- TC5: Agent file MISSING → displayed as MISSING
- TC6: Agent file IDENTICAL, HEAD differs but content_hash unchanged → stays IDENTICAL (not STALE)
- TC7: Agent file MODIFIED, user hasn't changed it locally, warehouse updated → enriched to STALE
- TC8: Agent file MODIFIED, user locally edited it → stays MODIFIED (real local change)
- TC9: Mixed per-agent: opencode IDENTICAL, claudecode user-unchanged MODIFIED → claudecode STALE
"""

import hashlib
import json
from pathlib import Path

import pytest
from beacon.core.delta import ComparisonResult, DeltaComparator, DeltaStatus
from beacon.domains.artifact.agent import enrich_agent_stale


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


AGENT_CONTENT = "---\nname: code-reviewer\ndescription: Reviews code\n---\n# Agent\n"


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    return home


def _write_sync_state(
    fake_home: Path, warehouse_path: Path, agent_path: str, head: str
) -> None:
    """Write a sync-state entry for testing."""
    state_file = fake_home / ".config" / "agentic-beacon" / "sync-state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "version": 1,
        "warehouses": {
            str(warehouse_path): {
                agent_path: {
                    "content_hash": "abc123",
                    "warehouse_head": head,
                    "installed_at": "2026-01-01T00:00:00+00:00",
                }
            }
        },
    }
    state_file.write_text(json.dumps(state))


def test_tc1_identical_with_matching_head_stays_in_sync(tmp_path, fake_home):
    """TC1: Agent file IDENTICAL, sync-state HEAD matches warehouse HEAD → IN SYNC (IDENTICAL)."""
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()

    result = ComparisonResult(
        path="agents/code-reviewer.md",
        status=DeltaStatus.IDENTICAL,
        agent_statuses={"opencode": DeltaStatus.IDENTICAL},
    )

    _write_sync_state(fake_home, warehouse, "agents/code-reviewer.md", "abc123sha")

    enriched = enrich_agent_stale(
        result, warehouse_path=warehouse, current_head="abc123sha"
    )

    assert enriched.status == DeltaStatus.IDENTICAL
    assert enriched.agent_statuses.get("opencode") == DeltaStatus.IDENTICAL


def test_tc2_identical_with_different_head_becomes_stale(tmp_path, fake_home):
    """TC2: Agent file IDENTICAL, sync-state HEAD differs → enriched to STALE."""
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()

    result = ComparisonResult(
        path="agents/code-reviewer.md",
        status=DeltaStatus.IDENTICAL,
        agent_statuses={"opencode": DeltaStatus.IDENTICAL},
    )

    _write_sync_state(fake_home, warehouse, "agents/code-reviewer.md", "old_head_sha")

    enriched = enrich_agent_stale(
        result, warehouse_path=warehouse, current_head="new_head_sha"
    )

    assert enriched.status == DeltaStatus.STALE
    assert enriched.agent_statuses.get("opencode") == DeltaStatus.STALE


def test_tc3_no_sync_state_entry_stays_in_sync(tmp_path, fake_home):
    """TC3: No sync-state entry for this agent file → no STALE enrichment, stays IDENTICAL."""
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()

    result = ComparisonResult(
        path="agents/code-reviewer.md",
        status=DeltaStatus.IDENTICAL,
        agent_statuses={"opencode": DeltaStatus.IDENTICAL},
    )
    # No sync-state file exists

    enriched = enrich_agent_stale(
        result, warehouse_path=warehouse, current_head="some_sha"
    )

    assert enriched.status == DeltaStatus.IDENTICAL


def test_tc4_modified_without_comparator_stays_modified(tmp_path, fake_home):
    """TC4: MODIFIED result with no comparator → stays MODIFIED (can't hash live files)."""
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()

    result = ComparisonResult(
        path="agents/code-reviewer.md",
        status=DeltaStatus.MODIFIED,
        agent_statuses={"opencode": DeltaStatus.MODIFIED},
    )

    _write_sync_state(fake_home, warehouse, "agents/code-reviewer.md", "old_sha")

    enriched = enrich_agent_stale(
        result, warehouse_path=warehouse, current_head="new_sha"
    )

    assert enriched.status == DeltaStatus.MODIFIED


def test_tc7_modified_user_unchanged_becomes_stale(tmp_path, fake_home):
    """TC7: MODIFIED because warehouse updated agent, user never touched it → STALE.

    Scenario:
    - User installed agent (hash A) from old warehouse commit
    - Warehouse merged an update (hash B)
    - User's global agent still has hash A (user didn't edit it)
    - delta shows MODIFIED (A != B) but should show STALE (upstream change, not local)
    """
    installed_content = "# Agent v1\noriginal content\n"
    warehouse_content = "# Agent v2\nupdated content by maintainer\n"

    installed_hash = _sha256(installed_content)
    warehouse_hash = _sha256(warehouse_content)

    # Set up warehouse with updated file
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    (warehouse / "agents").mkdir()
    (warehouse / "agents" / "code-reviewer.md").write_text(warehouse_content)

    # Set up live claudecode agent still at the installed version
    claude_agents_dir = fake_home / ".claude" / "agents"
    claude_agents_dir.mkdir(parents=True)
    (claude_agents_dir / "code-reviewer.md").write_text(installed_content)

    # Sync-state: installed with old warehouse HEAD, content_hash = installed_hash
    state_file = fake_home / ".config" / "agentic-beacon" / "sync-state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "version": 1,
        "warehouses": {
            str(warehouse): {
                "agents/code-reviewer.md": {
                    "content_hash": installed_hash,
                    "warehouse_head": "old_head_sha",
                    "installed_at": "2026-01-01T00:00:00+00:00",
                }
            }
        },
    }
    state_file.write_text(json.dumps(state))

    comparator = DeltaComparator(
        warehouse_path=warehouse,
        artifacts_path=tmp_path / "artifacts",
        agents_paths={"claudecode": claude_agents_dir},
    )

    result = ComparisonResult(
        path="agents/code-reviewer.md",
        status=DeltaStatus.MODIFIED,
        warehouse_hash=warehouse_hash,
        agent_statuses={"claudecode": DeltaStatus.MODIFIED},
    )

    enriched = enrich_agent_stale(
        result,
        warehouse_path=warehouse,
        current_head="new_head_sha",
        comparator=comparator,
    )

    assert enriched.status == DeltaStatus.STALE
    assert enriched.agent_statuses["claudecode"] == DeltaStatus.STALE


def test_tc8_modified_user_edited_stays_modified(tmp_path, fake_home):
    """TC8: MODIFIED because user locally edited the agent → stays MODIFIED (real local change).

    Scenario:
    - User installed agent (hash A) from old warehouse commit
    - Warehouse merged an update (hash B)
    - User also locally edited their global agent → hash C
    - Both warehouse and user's copy differ from installed → MODIFIED (user's change wins)
    """
    installed_content = "# Agent v1\noriginal content\n"
    warehouse_content = "# Agent v2\nupdated content by maintainer\n"
    user_content = "# Agent v1\noriginal content\nuser added this line\n"

    installed_hash = _sha256(installed_content)
    warehouse_hash = _sha256(warehouse_content)

    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    (warehouse / "agents").mkdir()
    (warehouse / "agents" / "code-reviewer.md").write_text(warehouse_content)

    claude_agents_dir = fake_home / ".claude" / "agents"
    claude_agents_dir.mkdir(parents=True)
    (claude_agents_dir / "code-reviewer.md").write_text(user_content)  # user edited

    state_file = fake_home / ".config" / "agentic-beacon" / "sync-state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "version": 1,
        "warehouses": {
            str(warehouse): {
                "agents/code-reviewer.md": {
                    "content_hash": installed_hash,
                    "warehouse_head": "old_head_sha",
                    "installed_at": "2026-01-01T00:00:00+00:00",
                }
            }
        },
    }
    state_file.write_text(json.dumps(state))

    comparator = DeltaComparator(
        warehouse_path=warehouse,
        artifacts_path=tmp_path / "artifacts",
        agents_paths={"claudecode": claude_agents_dir},
    )

    result = ComparisonResult(
        path="agents/code-reviewer.md",
        status=DeltaStatus.MODIFIED,
        warehouse_hash=warehouse_hash,
        agent_statuses={"claudecode": DeltaStatus.MODIFIED},
    )

    enriched = enrich_agent_stale(
        result,
        warehouse_path=warehouse,
        current_head="new_head_sha",
        comparator=comparator,
    )

    assert enriched.status == DeltaStatus.MODIFIED
    assert enriched.agent_statuses["claudecode"] == DeltaStatus.MODIFIED


def test_tc9_mixed_per_agent_opencode_identical_claudecode_stale(tmp_path, fake_home):
    """TC9: opencode IDENTICAL (already up to date), claudecode MODIFIED (user-unchanged) → claudecode STALE.

    This is the exact scenario from the user report:
    - opencode agent matches the new warehouse version (was separately updated)
    - claudecode agent is still at the old installed version (user never changed it)
    - Should show aggregate STALE, claudecode=STALE, opencode=IDENTICAL
    """
    installed_content = "# Agent v1\noriginal content\n"
    warehouse_content = "# Agent v2\nupdated content\n"

    installed_hash = _sha256(installed_content)
    warehouse_hash = _sha256(warehouse_content)

    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    (warehouse / "agents").mkdir()
    (warehouse / "agents" / "pr-reviewer.md").write_text(warehouse_content)

    # opencode already has the new warehouse version
    opencode_agents_dir = fake_home / ".config" / "opencode" / "agents"
    opencode_agents_dir.mkdir(parents=True)
    (opencode_agents_dir / "pr-reviewer.md").write_text(warehouse_content)

    # claudecode still has the old installed version
    claude_agents_dir = fake_home / ".claude" / "agents"
    claude_agents_dir.mkdir(parents=True)
    (claude_agents_dir / "pr-reviewer.md").write_text(installed_content)

    state_file = fake_home / ".config" / "agentic-beacon" / "sync-state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "version": 1,
        "warehouses": {
            str(warehouse): {
                "agents/pr-reviewer.md": {
                    "content_hash": installed_hash,
                    "warehouse_head": "old_head_sha",
                    "installed_at": "2026-01-01T00:00:00+00:00",
                }
            }
        },
    }
    state_file.write_text(json.dumps(state))

    comparator = DeltaComparator(
        warehouse_path=warehouse,
        artifacts_path=tmp_path / "artifacts",
        agents_paths={
            "opencode": opencode_agents_dir,
            "claudecode": claude_agents_dir,
        },
    )

    # _compare_agent_file would produce: opencode=IDENTICAL (matches warehouse),
    # claudecode=MODIFIED (old installed != new warehouse). Aggregate = MODIFIED.
    result = ComparisonResult(
        path="agents/pr-reviewer.md",
        status=DeltaStatus.MODIFIED,
        warehouse_hash=warehouse_hash,
        agent_statuses={
            "opencode": DeltaStatus.IDENTICAL,
            "claudecode": DeltaStatus.MODIFIED,
        },
    )

    enriched = enrich_agent_stale(
        result,
        warehouse_path=warehouse,
        current_head="new_head_sha",
        comparator=comparator,
    )

    assert enriched.status == DeltaStatus.STALE
    assert enriched.agent_statuses["opencode"] == DeltaStatus.IDENTICAL
    assert enriched.agent_statuses["claudecode"] == DeltaStatus.STALE


def test_tc6_identical_head_differs_but_content_unchanged_stays_identical(
    tmp_path, fake_home
):
    """TC6: HEAD advanced (e.g. after git pull) but agent content unchanged → not STALE.

    This covers the case where the warehouse received commits that did not touch
    the agent file.  The recorded content_hash matches the current warehouse file
    hash, so the agent should remain IDENTICAL even though warehouse_head changed.
    """
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()

    content_hash = "deadbeef1234567890"

    result = ComparisonResult(
        path="agents/code-reviewer.md",
        status=DeltaStatus.IDENTICAL,
        warehouse_hash=content_hash,  # current warehouse file has same hash
        agent_statuses={
            "opencode": DeltaStatus.IDENTICAL,
            "claudecode": DeltaStatus.IDENTICAL,
        },
    )

    # Sync-state records the old HEAD but the same content_hash
    state_file = fake_home / ".config" / "agentic-beacon" / "sync-state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "version": 1,
        "warehouses": {
            str(warehouse): {
                "agents/code-reviewer.md": {
                    "content_hash": content_hash,
                    "warehouse_head": "old_head_sha",
                    "installed_at": "2026-01-01T00:00:00+00:00",
                }
            }
        },
    }
    state_file.write_text(json.dumps(state))

    enriched = enrich_agent_stale(
        result, warehouse_path=warehouse, current_head="new_head_sha_after_pull"
    )

    assert enriched.status == DeltaStatus.IDENTICAL, (
        "Agent should stay IDENTICAL when HEAD advanced but content is unchanged"
    )


def test_tc5_missing_not_enriched(tmp_path, fake_home):
    """TC5: Agent file MISSING → displayed as MISSING."""
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()

    result = ComparisonResult(
        path="agents/code-reviewer.md",
        status=DeltaStatus.MISSING,
        agent_statuses={"opencode": DeltaStatus.MISSING},
    )

    _write_sync_state(fake_home, warehouse, "agents/code-reviewer.md", "old_sha")

    enriched = enrich_agent_stale(
        result, warehouse_path=warehouse, current_head="new_sha"
    )

    assert enriched.status == DeltaStatus.MISSING
