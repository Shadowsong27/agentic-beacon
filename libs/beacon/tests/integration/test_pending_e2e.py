"""Integration tests for the full pending → adopt → wired pipeline.

Covers tasks 9.1–9.6:
- test_knowledge_no_pointer: knowledge entry accepted → beacon.yaml unchanged
- test_knowledge_with_pointer: knowledge + context entries → context symlink created
- test_skill_create: skill pending entry → beacon.yaml entry + symlink
- test_warehouse_modified_via_last_adopt: hand-edited file surfaces via .last-adopt diff
- test_alert_visibility: pending.yaml non-empty → alert on stderr before status output
- test_missing_warehouse_hard_error: no config.toml → hard error, no file writes
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from beacon.core.manifest.pending import PendingEntry, PendingManifest
from beacon.domains.adoption.apply import commit_pending_session
from beacon.domains.adoption.discovery import discover_candidates
from beacon.domains.adoption.last_adopt import read_last_adopt, write_last_adopt
from beacon.domains.adoption.models import AdoptCandidate, AdoptResult

# ─────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────

_GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "t@t.local",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "t@t.local",
}


def _git(path: Path, *args: str, date: str | None = None) -> None:
    env = {**_GIT_ENV}
    if date:
        env = {**env, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
    subprocess.run(["git", *args], cwd=path, check=True, capture_output=True, env=env)


def _init_warehouse(path: Path, *, date: str = "2026-01-01T00:00:00+00:00") -> None:
    """Create a git-initialized warehouse with empty subdirectories."""
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init")
    _git(path, "config", "user.email", "t@t.local")
    _git(path, "config", "user.name", "Test")
    for d in ("contexts", "skills", "knowledge", "agents"):
        (path / d).mkdir(exist_ok=True)
        (path / d / ".gitkeep").write_text("")
    _git(path, "add", "-A")
    _git(path, "commit", "-m", "init", date=date)


def _commit_all(path: Path, msg: str = "add files", *, date: str | None = None) -> None:
    _git(path, "add", "-A")
    _git(path, "commit", "-m", msg, date=date)


def _make_project(
    root: Path,
    warehouse: Path,
    *,
    beacon_content: str | None = None,
    last_adopt_dt: datetime | None = None,
) -> dict:
    """Set up a minimal project connected to *warehouse*. Returns a dict of key paths."""
    ab = root / ".agentic-beacon"
    ab.mkdir(parents=True, exist_ok=True)
    artifacts = ab / "artifacts"
    artifacts.mkdir(exist_ok=True)

    (ab / "config.toml").write_text(f'[warehouse]\nlocal_path = "{warehouse}"\n')

    beacon_yaml = ab / "beacon.yaml"
    if beacon_content is None:
        beacon_content = "artifacts:\n  contexts: []\n  skills: []\n  agents: []\n"
    beacon_yaml.write_text(beacon_content)

    if last_adopt_dt is not None:
        write_last_adopt(root, last_adopt_dt)

    return {
        "root": root,
        "ab": ab,
        "beacon_yaml": beacon_yaml,
        "artifacts": artifacts,
        "pending_yaml": ab / "pending.yaml",
    }


# ─────────────────────────────────────────────────────────────
# 9.1 — Knowledge (no pointer): beacon.yaml unchanged after accept
# ─────────────────────────────────────────────────────────────


def test_knowledge_no_pointer(tmp_path: Path) -> None:
    """9.1: knowledge entry accepted → beacon.yaml unchanged, pending.yaml empty, .last-adopt advanced."""
    wh = tmp_path / "wh"
    _init_warehouse(wh)
    (wh / "knowledge" / "lesson.md").write_text("# Lesson\n")
    _commit_all(wh, "add lesson")

    proj = tmp_path / "proj"
    proj.mkdir()
    p = _make_project(proj, wh, last_adopt_dt=datetime(2026, 5, 1, tzinfo=UTC))

    entry = PendingEntry(
        path="knowledge/lesson.md",
        type="knowledge",
        action="created",
        source="record-knowledge",
        created_at=datetime(2026, 5, 6, 12, 0, tzinfo=UTC),
    )
    PendingManifest(pending=[entry]).to_yaml(p["pending_yaml"])
    pre_beacon = p["beacon_yaml"].read_bytes()

    commit_time = datetime(2026, 5, 7, 12, 0, tzinfo=UTC)
    commit_pending_session(
        {"knowledge/lesson.md": "accept"},
        [AdoptCandidate(artifact_type="knowledge", path="knowledge/lesson.md")],
        proj,
        wh,
        p["artifacts"],
        p["beacon_yaml"],
        commit_time=commit_time,
    )

    # beacon.yaml must be byte-identical — knowledge is not a beacon.yaml artifact
    assert p["beacon_yaml"].read_bytes() == pre_beacon, (
        "beacon.yaml must not change when accepting a knowledge entry"
    )

    # pending.yaml is now empty
    assert PendingManifest.from_yaml(p["pending_yaml"]).pending == []

    # .last-adopt advanced to commit_time
    assert read_last_adopt(proj) == commit_time


# ─────────────────────────────────────────────────────────────
# 9.2 — Knowledge (with pointer): context symlink created
# ─────────────────────────────────────────────────────────────


def test_knowledge_with_pointer(tmp_path: Path) -> None:
    """9.2: knowledge + context pending entries accepted → context symlink resolves in project."""
    wh = tmp_path / "wh"
    _init_warehouse(wh)
    (wh / "knowledge" / "lesson.md").write_text("# Lesson\n")
    (wh / "contexts" / "guide.md").write_text("# Guide\n")
    _commit_all(wh, "add files")

    proj = tmp_path / "proj"
    proj.mkdir()
    p = _make_project(proj, wh, last_adopt_dt=datetime(2026, 5, 1, tzinfo=UTC))

    entries = [
        PendingEntry(
            path="knowledge/lesson.md",
            type="knowledge",
            action="created",
            source="record-knowledge",
            created_at=datetime(2026, 5, 6, 12, 0, tzinfo=UTC),
        ),
        PendingEntry(
            path="contexts/guide.md",
            type="context",
            action="modified",
            source="record-knowledge",
            created_at=datetime(2026, 5, 6, 12, 0, tzinfo=UTC),
        ),
    ]
    PendingManifest(pending=entries).to_yaml(p["pending_yaml"])

    commit_pending_session(
        {"knowledge/lesson.md": "accept", "contexts/guide.md": "accept"},
        [
            AdoptCandidate(artifact_type="knowledge", path="knowledge/lesson.md"),
            AdoptCandidate(artifact_type="contexts", path="contexts/guide.md"),
        ],
        proj,
        wh,
        p["artifacts"],
        p["beacon_yaml"],
        commit_time=datetime(2026, 5, 7, 12, 0, tzinfo=UTC),
    )

    # Context symlink exists and reads through to the warehouse file
    symlink = p["artifacts"] / "contexts" / "guide.md"
    assert symlink.is_symlink(), "contexts/guide.md must be a symlink"
    assert symlink.read_text() == "# Guide\n"

    # beacon.yaml has the context entry
    data = yaml.safe_load(p["beacon_yaml"].read_text())
    assert "contexts/guide.md" in data["artifacts"]["contexts"]

    # knowledge NOT in any beacon.yaml artifact list
    all_beacon_paths = (
        data["artifacts"].get("contexts", [])
        + data["artifacts"].get("skills", [])
        + data["artifacts"].get("agents", [])
    )
    assert "knowledge/lesson.md" not in all_beacon_paths

    # pending.yaml empty
    assert PendingManifest.from_yaml(p["pending_yaml"]).pending == []


# ─────────────────────────────────────────────────────────────
# 9.3 — Skill create: beacon.yaml entry + symlink created
# ─────────────────────────────────────────────────────────────


def test_skill_create(tmp_path: Path) -> None:
    """9.3: skill pending entry accepted → beacon.yaml entry + symlink created, pending.yaml empty."""
    wh = tmp_path / "wh"
    _init_warehouse(wh)
    skill_dir = wh / "skills" / "new-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nrequires:\n  contexts: []\n---\n# New Skill\n"
    )
    _commit_all(wh, "add skill")

    proj = tmp_path / "proj"
    proj.mkdir()
    p = _make_project(proj, wh, last_adopt_dt=datetime(2026, 5, 1, tzinfo=UTC))

    entry = PendingEntry(
        path="skills/new-skill/",
        type="skill",
        action="created",
        source="record-skill",
        created_at=datetime(2026, 5, 6, 12, 0, tzinfo=UTC),
    )
    PendingManifest(pending=[entry]).to_yaml(p["pending_yaml"])

    commit_pending_session(
        {"skills/new-skill/": "accept"},
        [AdoptCandidate(artifact_type="skills", path="skills/new-skill/")],
        proj,
        wh,
        p["artifacts"],
        p["beacon_yaml"],
        commit_time=datetime(2026, 5, 7, 12, 0, tzinfo=UTC),
    )

    # beacon.yaml has the skill entry
    data = yaml.safe_load(p["beacon_yaml"].read_text())
    assert "skills/new-skill/" in data["artifacts"]["skills"]

    # SKILL.md symlink exists under artifacts
    skill_symlink = p["artifacts"] / "skills" / "new-skill" / "SKILL.md"
    assert skill_symlink.is_symlink(), "skills/new-skill/SKILL.md must be a symlink"

    # pending.yaml empty
    assert PendingManifest.from_yaml(p["pending_yaml"]).pending == []


# ─────────────────────────────────────────────────────────────
# 9.4 — Warehouse-modified entry via .last-adopt diff
# ─────────────────────────────────────────────────────────────


def test_warehouse_modified_via_last_adopt(tmp_path: Path) -> None:
    """9.4: hand-edit warehouse context surfaces via .last-adopt diff; second run is empty."""
    # Two fixed dates bracket the .last-adopt value
    initial_date = "2026-01-01T00:00:00+00:00"
    modification_date = "2026-02-01T00:00:00+00:00"

    wh = tmp_path / "wh"
    _init_warehouse(wh, date=initial_date)
    # Add context file in initial commit (before .last-adopt)
    (wh / "contexts" / "guide.md").write_text("# Original\n")
    _commit_all(wh, "add guide", date=initial_date)

    proj = tmp_path / "proj"
    proj.mkdir()
    # .last-adopt set between initial commit and modification
    last_adopt_dt = datetime(2026, 1, 15, tzinfo=UTC)
    p = _make_project(proj, wh, last_adopt_dt=last_adopt_dt)
    # No pending.yaml entries — only warehouse diff path matters

    # Hand-edit the context file and commit AFTER .last-adopt
    (wh / "contexts" / "guide.md").write_text("# Modified\n")
    _commit_all(wh, "edit guide", date=modification_date)

    # discover_candidates should surface the warehouse-modified entry
    candidates = discover_candidates(proj, wh)
    guide_candidates = [c for c in candidates if c.path == "contexts/guide.md"]
    assert guide_candidates, (
        f"contexts/guide.md not in candidates: {[c.path for c in candidates]}"
    )
    guide = guide_candidates[0]
    assert guide.source == "warehouse-modified"

    # Accept the entry via commit_pending_session
    commit_time = datetime(2026, 3, 1, tzinfo=UTC)
    commit_pending_session(
        {"contexts/guide.md": "accept"},
        [
            AdoptCandidate(
                artifact_type="contexts",
                path="contexts/guide.md",
                source="warehouse-modified",
            )
        ],
        proj,
        wh,
        p["artifacts"],
        p["beacon_yaml"],
        commit_time=commit_time,
    )

    # .last-adopt advanced to commit_time
    assert read_last_adopt(proj) == commit_time

    # Subsequent discover: no commits after commit_time (2026-03-01), no pending entries → empty
    second_candidates = discover_candidates(proj, wh)
    assert not any(c.path == "contexts/guide.md" for c in second_candidates), (
        f"contexts/guide.md must not reappear after .last-adopt advance: "
        f"{[c.path for c in second_candidates]}"
    )


def test_uncommitted_warehouse_edit_surfaces_via_discovery(tmp_path: Path) -> None:
    """Uncommitted warehouse working-tree edits are discoverable by abc adopt."""
    wh = tmp_path / "wh"
    _init_warehouse(wh)
    (wh / "contexts" / "draft.md").write_text("# Original\n")
    _commit_all(wh, "add draft", date="2026-01-01T00:00:00+00:00")

    proj = tmp_path / "proj"
    proj.mkdir()
    _make_project(proj, wh, last_adopt_dt=datetime(2026, 2, 1, tzinfo=UTC))

    (wh / "contexts" / "draft.md").write_text("# Uncommitted edit\n")

    candidates = discover_candidates(proj, wh)

    draft = [c for c in candidates if c.path == "contexts/draft.md"]
    assert draft, f"contexts/draft.md not in candidates: {[c.path for c in candidates]}"
    assert draft[0].source == "warehouse-modified"


def test_cli_adopt_commits_pending_three_way_actions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """abc adopt uses the pending-aware commit path, including reject/defer choices."""
    import beacon.cli.adoption as adoption_cli
    from beacon.cli.main import main
    from click.testing import CliRunner

    wh = tmp_path / "wh"
    _init_warehouse(wh)
    (wh / "contexts" / "accept.md").write_text("# Accept\n")
    (wh / "contexts" / "reject.md").write_text("# Reject\n")
    (wh / "contexts" / "defer.md").write_text("# Defer\n")
    _commit_all(wh, "add pending candidates")

    proj = tmp_path / "proj"
    proj.mkdir()
    p = _make_project(proj, wh, last_adopt_dt=datetime(2026, 5, 1, tzinfo=UTC))
    PendingManifest(
        pending=[
            PendingEntry(
                path="contexts/accept.md",
                type="context",
                action="created",
                source="test",
                created_at=datetime(2026, 5, 6, 12, 0, tzinfo=UTC),
            ),
            PendingEntry(
                path="contexts/reject.md",
                type="context",
                action="created",
                source="test",
                created_at=datetime(2026, 5, 6, 12, 0, tzinfo=UTC),
            ),
            PendingEntry(
                path="contexts/defer.md",
                type="context",
                action="created",
                source="test",
                created_at=datetime(2026, 5, 6, 12, 0, tzinfo=UTC),
            ),
        ]
    ).to_yaml(p["pending_yaml"])

    class FakeAdoptApp:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def run(self) -> AdoptResult:
            return AdoptResult(
                to_adopt=["contexts/accept.md"],
                to_reject=["contexts/reject.md"],
                to_defer=["contexts/defer.md"],
            )

    monkeypatch.setattr(adoption_cli, "AdoptApp", FakeAdoptApp)
    monkeypatch.setattr(adoption_cli, "is_interactive", lambda: True)
    monkeypatch.chdir(proj)

    result = CliRunner().invoke(main, ["adopt"])

    assert result.exit_code == 0, result.output
    data = yaml.safe_load(p["beacon_yaml"].read_text())
    assert "contexts/accept.md" in data["artifacts"]["contexts"]

    remaining = PendingManifest.from_yaml(p["pending_yaml"]).pending
    assert [e.path for e in remaining] == ["contexts/defer.md"]
    assert read_last_adopt(proj) is not None


# ─────────────────────────────────────────────────────────────
# 9.5 — Alert visibility: pending alert precedes warehouse status
# ─────────────────────────────────────────────────────────────


def test_alert_visibility(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """9.5: non-empty pending.yaml → alert on stderr, then warehouse status runs normally."""
    from beacon.cli.main import main
    from click.testing import CliRunner

    wh = tmp_path / "wh"
    _init_warehouse(wh)

    proj = tmp_path / "proj"
    proj.mkdir()
    p = _make_project(proj, wh)

    # Populate pending.yaml with 3 entries
    entries = [
        PendingEntry(
            path=f"contexts/ctx-{i}.md",
            type="context",
            action="created",
            source="test",
            created_at=datetime(2026, 5, 6, 12, 0, tzinfo=UTC),
        )
        for i in range(3)
    ]
    PendingManifest(pending=entries).to_yaml(p["pending_yaml"])

    monkeypatch.chdir(proj)
    runner = CliRunner()
    result = runner.invoke(main, ["warehouse", "status"])

    # Alert must appear in stderr
    assert "⚠ 3 pending artifacts. Run 'abc adopt' to wire them." in result.stderr, (
        f"Alert not found in stderr: {result.stderr!r}"
    )

    # First line of stderr is the alert
    first_stderr_line = result.stderr.splitlines()[0] if result.stderr else ""
    assert re.match(
        r"^⚠ \d+ pending artifacts\. Run 'abc adopt' to wire them\.$",
        first_stderr_line,
    ), f"First stderr line does not match alert pattern: {first_stderr_line!r}"

    # Alert does not force exit code to a specific non-zero value;
    # exit_code is whatever warehouse status would give
    assert result.exit_code is not None, "Command must produce an exit code"


# ─────────────────────────────────────────────────────────────
# 9.6 — Missing warehouse: resolve_warehouse hard-errors
# ─────────────────────────────────────────────────────────────


def test_missing_warehouse_hard_error(tmp_path: Path) -> None:
    """9.6: no .agentic-beacon/config.toml → resolve_warehouse exits non-zero, no file writes."""
    script_path = (
        Path(__file__).parent.parent.parent
        / "src"
        / "beacon"
        / "data"
        / "skills"
        / "record-knowledge"
        / "scripts"
        / "resolve_warehouse.py"
    )
    assert script_path.exists(), f"resolve_warehouse.py not found at {script_path}"

    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )

    # Must exit non-zero
    assert result.returncode != 0, (
        f"Expected non-zero exit; got {result.returncode}. stderr: {result.stderr!r}"
    )

    # Stderr must contain the documented error text
    assert "Error: no warehouse connected" in result.stderr, (
        f"Documented error text not in stderr: {result.stderr!r}"
    )
    assert "abc warehouse connect" in result.stderr, (
        f"Connect instructions not in stderr: {result.stderr!r}"
    )

    # No files created in tmp_path (the only entry is the dir itself)
    contents = list(tmp_path.iterdir())
    assert contents == [], (
        f"Script must not create files; found: {[str(f) for f in contents]}"
    )
