"""Subprocess-level regression tests for the record-* enforcement scripts.

The original bug was: record-knowledge wrote a real file into the project's
symlink-mirror at .agentic-beacon/artifacts/knowledge/ instead of the warehouse.
These tests pin that the new write_*.py scripts, when launched as a fresh
process from inside a project's CWD, only write under the resolved warehouse --
never under the project's .agentic-beacon/artifacts/.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_SKILLS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "src" / "beacon" / "data" / "skills"
)
WRITE_KNOWLEDGE = _SKILLS_DIR / "record-knowledge" / "scripts" / "write_knowledge.py"
WRITE_SKILL = _SKILLS_DIR / "record-skill" / "scripts" / "write_skill.py"


def _setup(tmp_path: Path) -> tuple[Path, Path]:
    """Project at tmp_path/project, warehouse at tmp_path/warehouse, wired."""
    project = tmp_path / "project"
    project.mkdir()
    (project / ".agentic-beacon").mkdir()
    artifacts = project / ".agentic-beacon" / "artifacts"
    artifacts.mkdir()

    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    (warehouse / "knowledge").mkdir()
    (warehouse / "skills").mkdir()

    (project / ".agentic-beacon" / "config.toml").write_text(
        f'[warehouse]\nlocal_path = "{warehouse}"\n'
    )
    return project, warehouse


def test_write_knowledge_subprocess_lands_in_warehouse(tmp_path: Path) -> None:
    """Running write_knowledge.py from the project CWD writes into the warehouse only."""
    project, warehouse = _setup(tmp_path)
    artifacts = project / ".agentic-beacon" / "artifacts"

    result = subprocess.run(
        [
            sys.executable,
            str(WRITE_KNOWLEDGE),
            "--type",
            "lesson",
            "--topic",
            "infrastructure",
            "--name",
            "deploy-via-git",
        ],
        cwd=project,
        input="# Deploy via git\n\nUse git push, not rsync.\n",
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    target = (
        warehouse / "knowledge" / "infrastructure" / "lessons" / "deploy-via-git.md"
    )
    assert target.is_file()
    assert target.read_text().startswith("# Deploy via git")
    assert result.stdout.strip() == "knowledge/infrastructure/lessons/deploy-via-git.md"

    # Crucial regression guard: nothing under the project's artifact mirror.
    knowledge_mirror = artifacts / "knowledge"
    if knowledge_mirror.exists():
        assert list(knowledge_mirror.rglob("*")) == [], (
            f"write_knowledge.py leaked files into the project mirror: "
            f"{list(knowledge_mirror.rglob('*'))}"
        )


def test_write_skill_subprocess_lands_in_warehouse(tmp_path: Path) -> None:
    """Running write_skill.py from the project CWD writes into the warehouse only."""
    project, warehouse = _setup(tmp_path)
    artifacts = project / ".agentic-beacon" / "artifacts"

    result = subprocess.run(
        [
            sys.executable,
            str(WRITE_SKILL),
            "--name",
            "deploy-check",
            "--description",
            "Validate deployment readiness",
            "--include-script",
        ],
        cwd=project,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    skill_md = warehouse / "skills" / "deploy-check" / "SKILL.md"
    script = warehouse / "skills" / "deploy-check" / "scripts" / "deploy-check.py"
    assert skill_md.is_file()
    assert script.is_file()
    assert "name: deploy-check" in skill_md.read_text()
    assert script.read_text().startswith("# /// script")
    assert result.stdout.strip() == "skills/deploy-check/"

    # Regression guard: nothing under the project's artifact mirror.
    skills_mirror = artifacts / "skills"
    if skills_mirror.exists():
        assert list(skills_mirror.rglob("*")) == [], (
            f"write_skill.py leaked files into the project mirror: "
            f"{list(skills_mirror.rglob('*'))}"
        )


def test_write_knowledge_no_warehouse_exits_nonzero(tmp_path: Path) -> None:
    """Run from a directory with no .agentic-beacon/config.toml -- hard error."""
    result = subprocess.run(
        [
            sys.executable,
            str(WRITE_KNOWLEDGE),
            "--type",
            "lesson",
            "--name",
            "x",
        ],
        cwd=tmp_path,
        input="# X\n",
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "no warehouse connected" in result.stderr
    assert list(tmp_path.iterdir()) == []


def test_write_skill_no_warehouse_exits_nonzero(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(WRITE_SKILL),
            "--name",
            "x",
            "--description",
            "x",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "no warehouse connected" in result.stderr
    assert list(tmp_path.iterdir()) == []


# ----
# E2E smoke: full record-skill flow (PER-150 regression guard)
# ----

_APPEND_PENDING_SKILL = _SKILLS_DIR / "record-skill" / "scripts" / "append_pending.py"


@pytest.mark.integration
def test_record_skill_e2e_write_then_append_pending(tmp_path: Path) -> None:
    """Full record-skill flow: write_skill.py then append_pending.py via uv run.

    Without the PER-150 fix, append_pending.py fails with:
        ModuleNotFoundError: No module named 'beacon'
    """
    project, warehouse = _setup(tmp_path)

    # Step 1: write_skill.py -- stdlib-only, no uv run needed
    write_result = subprocess.run(
        [
            sys.executable,
            str(WRITE_SKILL),
            "--name",
            "e2e-skill",
            "--description",
            "End-to-end test skill",
        ],
        cwd=project,
        capture_output=True,
        text=True,
    )
    assert write_result.returncode == 0, write_result.stderr
    skill_path_out = write_result.stdout.strip()  # e.g. "skills/e2e-skill/"
    assert skill_path_out == "skills/e2e-skill/"

    # Step 2: append_pending.py -- requires pyyaml; use uv run --isolated to
    # prove it works in a fresh environment where beacon is NOT importable.
    clean_env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("PYTHONPATH", "VIRTUAL_ENV") and not k.startswith("BEACON_")
    }
    append_result = subprocess.run(
        [
            "uv",
            "run",
            "--no-project",
            "--isolated",
            str(_APPEND_PENDING_SKILL),
            "--path",
            skill_path_out,
            "--type",
            "skill",
            "--action",
            "created",
            "--source",
            "record-skill",
        ],
        cwd=project,
        env=clean_env,
        capture_output=True,
        text=True,
    )
    assert append_result.returncode == 0, (
        f"append_pending.py failed: {append_result.stderr}"
    )

    # Verify pending.yaml exists and round-trips through PendingManifest
    from beacon.core.manifest.pending import PendingManifest

    pending_path = project / ".agentic-beacon" / "pending.yaml"
    assert pending_path.exists()
    manifest = PendingManifest.from_yaml(pending_path)
    assert len(manifest.pending) == 1
    entry = manifest.pending[0]
    assert entry.path == skill_path_out
    assert entry.type == "skill"
    assert entry.source == "record-skill"
