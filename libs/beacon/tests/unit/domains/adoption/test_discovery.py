"""Tests for discover_pending() and discover_adoptable(excluded_paths)."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

from beacon.core.manifest.beacon import BeaconManifest
from beacon.core.manifest.pending import PendingEntry, PendingManifest
from beacon.domains.adoption.discovery import discover_adoptable, discover_pending

# ─────────────────────────────────────────────────────────────
# Helpers
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
        ["git", "config", "user.name", "Test User"],
        cwd=path,
        check=True,
        capture_output=True,
    )


def _git_commit(path: Path, message: str = "add files") -> None:
    subprocess.run(["git", "add", "-A"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=path,
        check=True,
        capture_output=True,
    )


def _make_warehouse(tmp_path: Path) -> Path:
    """Create a minimal git-initialized warehouse with empty artifact dirs."""
    wh = tmp_path / "warehouse"
    wh.mkdir()
    _git_init(wh)
    for d in ["contexts", "skills", "agents", "knowledge"]:
        (wh / d).mkdir()
    (wh / ".gitkeep").write_text("")
    _git_commit(wh, "initial")
    return wh


def _make_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    (project / ".agentic-beacon").mkdir()
    return project


def _pending_entry(
    path: str,
    entry_type: str = "context",
    source: str = "record-knowledge",
) -> PendingEntry:
    return PendingEntry(
        path=path,
        type=entry_type,  # type: ignore[arg-type]
        action="created",
        source=source,
        created_at=datetime(2026, 5, 6, 12, 0, 0, tzinfo=UTC),
    )


def _write_pending(project: Path, entries: list[PendingEntry]) -> None:
    PendingManifest(pending=entries).to_yaml(
        project / ".agentic-beacon" / "pending.yaml"
    )


# ─────────────────────────────────────────────────────────────
# discover_pending
# ─────────────────────────────────────────────────────────────


def test_discover_pending_returns_empty_when_no_pending_yaml(tmp_path):
    project = _make_project(tmp_path)
    assert discover_pending(project) == []


def test_discover_pending_returns_entries_in_yaml_order(tmp_path):
    project = _make_project(tmp_path)
    entries = [
        _pending_entry("contexts/foo.md", "context"),
        _pending_entry("skills/bar/", "skill"),
        _pending_entry("agents/baz.md", "agent"),
    ]
    _write_pending(project, entries)

    result = discover_pending(project)

    assert [e.path for e in result] == [
        "contexts/foo.md",
        "skills/bar/",
        "agents/baz.md",
    ]
    assert [e.type for e in result] == ["context", "skill", "agent"]


def test_discover_pending_returns_empty_when_yaml_has_empty_list(tmp_path):
    project = _make_project(tmp_path)
    _write_pending(project, [])
    assert discover_pending(project) == []


# ─────────────────────────────────────────────────────────────
# discover_adoptable with excluded_paths
# ─────────────────────────────────────────────────────────────


def test_discover_adoptable_returns_unadopted_warehouse_artifacts(tmp_path):
    wh = _make_warehouse(tmp_path)
    (wh / "contexts" / "alpha.md").write_text("# Alpha\n")
    (wh / "contexts" / "beta.md").write_text("# Beta\n")
    _git_commit(wh, "add contexts")

    beacon = BeaconManifest()
    candidates, _ = discover_adoptable(wh, beacon)

    paths = {c.path for c in candidates}
    assert "contexts/alpha.md" in paths
    assert "contexts/beta.md" in paths


def test_discover_adoptable_excludes_already_adopted(tmp_path):
    wh = _make_warehouse(tmp_path)
    (wh / "contexts" / "alpha.md").write_text("# Alpha\n")
    (wh / "contexts" / "beta.md").write_text("# Beta\n")
    _git_commit(wh, "add contexts")

    beacon = BeaconManifest()
    beacon.artifacts.contexts = ["contexts/alpha.md"]

    candidates, _ = discover_adoptable(wh, beacon)
    paths = {c.path for c in candidates}

    assert "contexts/alpha.md" not in paths
    assert "contexts/beta.md" in paths


def test_discover_adoptable_excludes_paths_passed_via_excluded_paths(tmp_path):
    """Paths in pending.yaml should be hidden from the warehouse browser."""
    wh = _make_warehouse(tmp_path)
    (wh / "contexts" / "alpha.md").write_text("# Alpha\n")
    (wh / "contexts" / "beta.md").write_text("# Beta\n")
    _git_commit(wh, "add contexts")

    beacon = BeaconManifest()
    excluded = {"contexts/alpha.md"}
    candidates, _ = discover_adoptable(wh, beacon, excluded_paths=excluded)
    paths = {c.path for c in candidates}

    assert "contexts/alpha.md" not in paths
    assert "contexts/beta.md" in paths


def test_discover_adoptable_with_skill_directory_exclusion(tmp_path):
    wh = _make_warehouse(tmp_path)
    skill_dir = wh / "skills" / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\ndescription: A skill\n---\n")
    _git_commit(wh, "add skill")

    beacon = BeaconManifest()
    candidates, _ = discover_adoptable(wh, beacon, excluded_paths={"skills/my-skill/"})
    paths = {c.path for c in candidates}

    assert "skills/my-skill/" not in paths


def test_discover_adoptable_includes_agents(tmp_path):
    wh = _make_warehouse(tmp_path)
    (wh / "agents" / "code-reviewer.md").write_text("---\nname: code-reviewer\n---\n")
    _git_commit(wh, "add agent")

    beacon = BeaconManifest()
    candidates, _ = discover_adoptable(wh, beacon)
    paths = {c.path for c in candidates}

    assert "agents/code-reviewer.md" in paths


# ─────────────────────────────────────────────────────────────
# discover_pending deduplication (read-side tolerance)
# ─────────────────────────────────────────────────────────────


def test_discover_pending_collapses_duplicate_entries_keeps_earliest_created_at(
    tmp_path,
):
    project = _make_project(tmp_path)
    entries = [
        PendingEntry(
            path="contexts/cicd-flow.md",
            type="context",  # type: ignore[arg-type]
            action="modified",
            source="record-knowledge",
            created_at=datetime(2026, 5, 7, 13, 30, 30, tzinfo=UTC),
        ),
        PendingEntry(
            path="contexts/cicd-flow.md",
            type="context",  # type: ignore[arg-type]
            action="modified",
            source="record-knowledge",
            created_at=datetime(2026, 5, 7, 15, 37, 7, tzinfo=UTC),
        ),
    ]
    _write_pending(project, entries)

    result = discover_pending(project)

    assert len(result) == 1
    assert result[0].path == "contexts/cicd-flow.md"
    assert result[0].created_at == datetime(2026, 5, 7, 13, 30, 30, tzinfo=UTC)


def test_discover_pending_preserves_distinct_source_entries(tmp_path):
    project = _make_project(tmp_path)
    entries = [
        PendingEntry(
            path="contexts/cicd-flow.md",
            type="context",  # type: ignore[arg-type]
            action="modified",
            source="record-knowledge",
            created_at=datetime(2026, 5, 7, 13, 30, 30, tzinfo=UTC),
        ),
        PendingEntry(
            path="contexts/cicd-flow.md",
            type="context",  # type: ignore[arg-type]
            action="modified",
            source="manual-edit",
            created_at=datetime(2026, 5, 7, 15, 37, 7, tzinfo=UTC),
        ),
    ]
    _write_pending(project, entries)

    result = discover_pending(project)

    assert len(result) == 2
    sources = {e.source for e in result}
    assert sources == {"record-knowledge", "manual-edit"}


def test_discover_pending_preserves_distinct_action_entries(tmp_path):
    project = _make_project(tmp_path)
    entries = [
        PendingEntry(
            path="skills/foo/",
            type="skill",  # type: ignore[arg-type]
            action="created",
            source="record-skill",
            created_at=datetime(2026, 5, 7, 13, 30, 30, tzinfo=UTC),
        ),
        PendingEntry(
            path="skills/foo/",
            type="skill",  # type: ignore[arg-type]
            action="modified",
            source="record-skill",
            created_at=datetime(2026, 5, 7, 15, 37, 7, tzinfo=UTC),
        ),
    ]
    _write_pending(project, entries)

    result = discover_pending(project)

    assert len(result) == 2
    actions = {e.action for e in result}
    assert actions == {"created", "modified"}
