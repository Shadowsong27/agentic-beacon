"""Integration tests: append_pending.py works without beacon installed.

Invokes scripts via `uv run --no-project --isolated` with a clean environment
that strips PYTHONPATH, VIRTUAL_ENV, and BEACON_* variables. This proves the
PEP 723 pyyaml dependency is resolved in a fresh ephemeral venv, independent
of the workspace venv that has beacon installed.

This is the direct regression test for PER-150.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from beacon.core.manifest.pending import PendingManifest

_SKILLS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "src" / "beacon" / "data" / "skills"
)

_SCRIPT_PATHS = {
    "record-skill": _SKILLS_DIR / "record-skill" / "scripts" / "append_pending.py",
    "record-knowledge": _SKILLS_DIR
    / "record-knowledge"
    / "scripts"
    / "append_pending.py",
}


def _clean_env() -> dict[str, str]:
    """Return os.environ with beacon-exposing vars stripped."""
    env = dict(os.environ)
    for key in list(env.keys()):
        if key in ("PYTHONPATH", "VIRTUAL_ENV") or key.startswith("BEACON_"):
            del env[key]
    return env


def _make_project(root: Path) -> None:
    (root / ".agentic-beacon").mkdir(parents=True)
    (root / ".agentic-beacon" / "config.toml").write_text(
        '[warehouse]\nlocal_path = "/tmp/dummy-warehouse"\n'
    )


# ─────────────────────────────────────────────────────────────
# Core: script resolves pyyaml from PEP 723 header, not workspace venv
# ─────────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.parametrize("skill_name", ["record-skill", "record-knowledge"])
def test_script_works_without_beacon_package(skill_name: str, tmp_path: Path) -> None:
    """Script runs in an isolated env where beacon is NOT on sys.path."""
    _make_project(tmp_path)
    script_path = _SCRIPT_PATHS[skill_name]

    result = subprocess.run(
        [
            "uv",
            "run",
            "--no-project",
            "--isolated",
            str(script_path),
            "--path",
            "skills/test-skill/",
            "--type",
            "skill",
            "--action",
            "created",
            "--source",
            skill_name,
        ],
        cwd=str(tmp_path),
        env=_clean_env(),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        f"Script failed (returncode={result.returncode}):\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )

    pending_path = tmp_path / ".agentic-beacon" / "pending.yaml"
    assert pending_path.exists(), "pending.yaml was not created"

    # Round-trip through canonical PendingManifest to verify format compatibility
    manifest = PendingManifest.from_yaml(pending_path)
    assert len(manifest.pending) == 1
    entry = manifest.pending[0]
    assert entry.path == "skills/test-skill/"
    assert entry.type == "skill"
    assert entry.action == "created"
    assert entry.source == skill_name


# ─────────────────────────────────────────────────────────────
# find_project_root walks up from nested subdirectory
# ─────────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.parametrize("skill_name", ["record-skill", "record-knowledge"])
def test_script_finds_project_root_from_nested_subdir(
    skill_name: str, tmp_path: Path
) -> None:
    """find_project_root walks up correctly when invoked from a nested subdirectory."""
    _make_project(tmp_path)
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)
    script_path = _SCRIPT_PATHS[skill_name]

    result = subprocess.run(
        [
            "uv",
            "run",
            "--no-project",
            "--isolated",
            str(script_path),
            "--path",
            "contexts/test.md",
            "--type",
            "context",
            "--action",
            "created",
            "--source",
            skill_name,
        ],
        cwd=str(nested),
        env=_clean_env(),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        f"Script failed from nested subdir:\nstderr: {result.stderr}"
    )

    pending_path = tmp_path / ".agentic-beacon" / "pending.yaml"
    assert pending_path.exists()
    manifest = PendingManifest.from_yaml(pending_path)
    assert len(manifest.pending) == 1
    assert manifest.pending[0].path == "contexts/test.md"
