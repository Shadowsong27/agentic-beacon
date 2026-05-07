"""Integration tests for the full pending → adopt → wired pipeline.

Covers:
- knowledge files are auto-managed (do not appear in adopt)
- accepting a pending context entry creates a symlink and updates beacon.yaml
- accepting a pending skill entry wires it correctly
- abc adopt CLI orchestrates accept/reject/defer end-to-end
- pending alert visibility
- record-knowledge resolve_warehouse hard error when no warehouse is connected
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
from beacon.core.manifest.beacon import BeaconManifest
from beacon.core.manifest.pending import PendingEntry, PendingManifest
from beacon.domains.adoption.apply import commit_session
from beacon.domains.adoption.discovery import discover_adoptable, discover_pending
from beacon.domains.adoption.models import AdoptResult

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
) -> dict:
    """Set up a minimal project connected to *warehouse*."""
    ab = root / ".agentic-beacon"
    ab.mkdir(parents=True, exist_ok=True)
    artifacts = ab / "artifacts"
    artifacts.mkdir(exist_ok=True)

    (ab / "config.toml").write_text(f'[warehouse]\nlocal_path = "{warehouse}"\n')

    beacon_yaml = ab / "beacon.yaml"
    if beacon_content is None:
        beacon_content = "artifacts:\n  contexts: []\n  skills: []\n  agents: []\n"
    beacon_yaml.write_text(beacon_content)

    return {
        "root": root,
        "ab": ab,
        "beacon_yaml": beacon_yaml,
        "artifacts": artifacts,
        "pending_yaml": ab / "pending.yaml",
    }


# ─────────────────────────────────────────────────────────────
# Knowledge files are auto-managed (don't appear in adopt)
# ─────────────────────────────────────────────────────────────


def test_knowledge_files_are_not_adoptable(tmp_path: Path) -> None:
    """Knowledge files live in knowledge/ and are auto-derived; they don't appear in adopt."""
    wh = tmp_path / "wh"
    _init_warehouse(wh)
    (wh / "knowledge" / "lesson.md").write_text("# Lesson\n")
    _commit_all(wh, "add lesson")

    proj = tmp_path / "proj"
    proj.mkdir()
    _make_project(proj, wh)

    beacon = BeaconManifest()
    candidates, _ = discover_adoptable(wh, beacon)

    assert "knowledge/lesson.md" not in {c.path for c in candidates}
    assert discover_pending(proj) == []


# ─────────────────────────────────────────────────────────────
# Pending context: accept creates a symlink and updates beacon.yaml
# ─────────────────────────────────────────────────────────────


def test_pending_context_accept_creates_symlink(tmp_path: Path) -> None:
    """Pending context entry → on accept, symlink resolves and beacon.yaml updates."""
    wh = tmp_path / "wh"
    _init_warehouse(wh)
    (wh / "contexts" / "guide.md").write_text("# Guide\n")
    _commit_all(wh, "add guide")

    proj = tmp_path / "proj"
    proj.mkdir()
    p = _make_project(proj, wh)

    entries = [
        PendingEntry(
            path="contexts/guide.md",
            type="context",
            action="created",
            source="record-knowledge",
            created_at=datetime(2026, 5, 6, 12, 0, tzinfo=UTC),
        ),
    ]
    PendingManifest(pending=entries).to_yaml(p["pending_yaml"])

    commit_session(
        to_adopt=[],
        to_unadopt=[],
        pending_accept=["contexts/guide.md"],
        pending_reject=[],
        candidates=[],
        pending_entries=entries,
        project_root=proj,
        warehouse_path=wh,
        artifacts_path=p["artifacts"],
        beacon_yaml_path=p["beacon_yaml"],
    )

    # Symlink resolves to the warehouse file
    symlink = p["artifacts"] / "contexts" / "guide.md"
    assert symlink.is_symlink()
    assert symlink.read_text() == "# Guide\n"

    # beacon.yaml has the context
    data = yaml.safe_load(p["beacon_yaml"].read_text())
    assert "contexts/guide.md" in data["artifacts"]["contexts"]

    # pending.yaml empty
    assert PendingManifest.from_yaml(p["pending_yaml"]).pending == []


# ─────────────────────────────────────────────────────────────
# Pending skill: accept wires beacon.yaml + symlink
# ─────────────────────────────────────────────────────────────


def test_pending_skill_accept_wires_skill(tmp_path: Path) -> None:
    """Pending skill entry → on accept, beacon.yaml has the skill and SKILL.md is symlinked."""
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
    p = _make_project(proj, wh)

    entry = PendingEntry(
        path="skills/new-skill/",
        type="skill",
        action="created",
        source="record-skill",
        created_at=datetime(2026, 5, 6, 12, 0, tzinfo=UTC),
    )
    PendingManifest(pending=[entry]).to_yaml(p["pending_yaml"])

    commit_session(
        to_adopt=[],
        to_unadopt=[],
        pending_accept=["skills/new-skill/"],
        pending_reject=[],
        candidates=[],
        pending_entries=[entry],
        project_root=proj,
        warehouse_path=wh,
        artifacts_path=p["artifacts"],
        beacon_yaml_path=p["beacon_yaml"],
    )

    data = yaml.safe_load(p["beacon_yaml"].read_text())
    assert "skills/new-skill/" in data["artifacts"]["skills"]

    skill_symlink = p["artifacts"] / "skills" / "new-skill" / "SKILL.md"
    assert skill_symlink.is_symlink()

    assert PendingManifest.from_yaml(p["pending_yaml"]).pending == []


# ─────────────────────────────────────────────────────────────
# CLI orchestrates accept/reject/defer end-to-end
# ─────────────────────────────────────────────────────────────


def test_cli_adopt_commits_pending_actions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """abc adopt: pending accept goes to beacon.yaml, reject is dropped, defer stays."""
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
    p = _make_project(proj, wh)
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
                pending_accept=["contexts/accept.md"],
                pending_reject=["contexts/reject.md"],
            )

    monkeypatch.setattr(adoption_cli, "AdoptApp", FakeAdoptApp)
    monkeypatch.setattr(adoption_cli, "is_interactive", lambda: True)
    monkeypatch.chdir(proj)

    result = CliRunner().invoke(main, ["adopt"])

    assert result.exit_code == 0, result.output
    data = yaml.safe_load(p["beacon_yaml"].read_text())
    assert "contexts/accept.md" in data["artifacts"]["contexts"]
    assert "contexts/reject.md" not in data["artifacts"]["contexts"]

    remaining = PendingManifest.from_yaml(p["pending_yaml"]).pending
    assert [e.path for e in remaining] == ["contexts/defer.md"]


# ─────────────────────────────────────────────────────────────
# Pending alert visibility
# ─────────────────────────────────────────────────────────────


def test_alert_visibility(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-empty pending.yaml → alert on stderr, then warehouse status runs normally."""
    from beacon.cli.main import main
    from click.testing import CliRunner

    wh = tmp_path / "wh"
    _init_warehouse(wh)

    proj = tmp_path / "proj"
    proj.mkdir()
    p = _make_project(proj, wh)

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

    assert "⚠ 3 pending artifacts. Run 'abc adopt' to wire them." in result.stderr, (
        f"Alert not found in stderr: {result.stderr!r}"
    )

    first_stderr_line = result.stderr.splitlines()[0] if result.stderr else ""
    assert re.match(
        r"^⚠ \d+ pending artifacts\. Run 'abc adopt' to wire them\.$",
        first_stderr_line,
    ), f"First stderr line does not match alert pattern: {first_stderr_line!r}"

    assert result.exit_code is not None


# ─────────────────────────────────────────────────────────────
# resolve_warehouse hard error when warehouse is missing
# ─────────────────────────────────────────────────────────────


def test_missing_warehouse_hard_error(tmp_path: Path) -> None:
    """No .agentic-beacon/config.toml → resolve_warehouse exits non-zero, no file writes."""
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

    assert result.returncode != 0, (
        f"Expected non-zero exit; got {result.returncode}. stderr: {result.stderr!r}"
    )
    assert "Error: no warehouse connected" in result.stderr
    assert "abc warehouse connect" in result.stderr

    contents = list(tmp_path.iterdir())
    assert contents == [], (
        f"Script must not create files; found: {[str(f) for f in contents]}"
    )
