"""Tests for abc delta STALE enrichment (Phase 7, task 7.10).

TDD Test Cases (7.7):
- TC1: Agent file IDENTICAL, sync-state HEAD matches warehouse HEAD → displayed as IN SYNC
- TC2: Agent file IDENTICAL, sync-state HEAD differs from warehouse HEAD → enriched to STALE
- TC3: No sync-state entry for this agent file → no STALE enrichment, displayed as IN SYNC
- TC4: Agent file MODIFIED → displayed as MODIFIED (sync-state not consulted)
- TC5: Agent file MISSING → displayed as MISSING
"""

import json
from pathlib import Path

import pytest
from beacon.cli import _enrich_agent_stale
from beacon.core.delta import ComparisonResult, DeltaStatus

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

    enriched = _enrich_agent_stale(
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

    enriched = _enrich_agent_stale(
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

    enriched = _enrich_agent_stale(
        result, warehouse_path=warehouse, current_head="some_sha"
    )

    assert enriched.status == DeltaStatus.IDENTICAL


def test_tc4_modified_not_consulted(tmp_path, fake_home):
    """TC4: Agent file MODIFIED → displayed as MODIFIED (sync-state not consulted)."""
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()

    result = ComparisonResult(
        path="agents/code-reviewer.md",
        status=DeltaStatus.MODIFIED,
        agent_statuses={"opencode": DeltaStatus.MODIFIED},
    )

    _write_sync_state(fake_home, warehouse, "agents/code-reviewer.md", "old_sha")

    enriched = _enrich_agent_stale(
        result, warehouse_path=warehouse, current_head="new_sha"
    )

    assert enriched.status == DeltaStatus.MODIFIED


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

    enriched = _enrich_agent_stale(
        result, warehouse_path=warehouse, current_head="new_sha"
    )

    assert enriched.status == DeltaStatus.MISSING
