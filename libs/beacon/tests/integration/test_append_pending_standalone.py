"""Integration tests: append_pending.py works without beacon installed.

These tests run `uv run --no-project --isolated`, which resolves PEP 723
dependencies (`pyyaml`) from the active package index. On a cache-cold CI
environment the first invocation will hit the network; subsequent calls reuse
uv's local cache. Tests are marked `@pytest.mark.integration` and are expected
to be skipped in offline or pre-commit fast-path runs.

This is the direct regression test for PER-150.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from beacon.core.manifest.pending import PendingManifest

from tests.integration._offline_guard import _is_offline_or_cache_cold

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        _is_offline_or_cache_cold(),
        reason="BEACON_OFFLINE=1 set; skipping uv-network-dependent integration test",
    ),
]

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


# ----
# Smoke test: PEP 723 + ephemeral venv path works end-to-end
# ----


@pytest.mark.parametrize("skill_name", ["record-skill", "record-knowledge"])
def test_uv_run_pep723_executes_script_without_beacon(
    skill_name: str, tmp_path: Path
) -> None:
    """Script runs in an isolated env where beacon is NOT on sys.path and
    pyyaml is resolved from the PEP 723 header — not the workspace venv."""
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
