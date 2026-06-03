"""Integration tests for abc warehouse lint CLI command (subprocess-level).

Spawns real `abc warehouse lint` subprocess invocations against fixture warehouses.
Marked @pytest.mark.integration; honoured by BEACON_OFFLINE=1 skip guard.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from tests.integration._offline_guard import _is_offline_or_cache_cold

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        _is_offline_or_cache_cold(),
        reason="BEACON_OFFLINE=1 set; skipping uv-network-dependent integration test",
    ),
]

# ---------------------------------------------------------------------------
# Fixture warehouse builders
# ---------------------------------------------------------------------------


def _build_clean_warehouse(root: Path) -> Path:
    """Build a structurally valid warehouse with no defects."""
    wh = root / "clean-warehouse"
    wh.mkdir()
    (wh / "agents").mkdir()
    (wh / "contexts").mkdir()
    (wh / "skills").mkdir()
    (wh / "docs").mkdir()
    (wh / "README.md").write_text("# Warehouse\n")
    (wh / "agents" / "README.md").write_text("# Agents\n")
    (wh / "contexts" / "README.md").write_text("# Contexts\n")
    (wh / "skills" / "README.md").write_text("# Skills\n")
    return wh


def _build_defective_warehouse(root: Path) -> tuple[Path, dict]:
    """Build a warehouse with at least 3 defects across at least 2 artifacts.

    Defects:
      - skills/no-fm/SKILL.md: no frontmatter
      - contexts/ctx-with-broken-link.md: cross-artifact-relative link
        to a missing knowledge target (post-Phase-2 lint classifies the
        link form as malformed regardless of target existence; pre-Phase-2
        this fixture verified the broken-knowledge-link rule)
      - agents/no-name.md: missing `name` key in frontmatter (registered in agents.yaml)

    Returns:
        (warehouse_path, expected_defects) where expected_defects maps
        artifact_path → list of expected error substrings.
    """
    wh = root / "defective-warehouse"
    wh.mkdir()
    (wh / "agents").mkdir()
    (wh / "contexts").mkdir()
    (wh / "skills").mkdir()
    (wh / "docs").mkdir()
    (wh / "README.md").write_text("# Warehouse\n")
    (wh / "knowledge").mkdir()

    # Defect 1: skill with no frontmatter
    (wh / "skills" / "no-fm").mkdir()
    (wh / "skills" / "no-fm" / "SKILL.md").write_text("# No frontmatter\n")

    # Defect 2: context with broken knowledge link
    ctx = wh / "contexts" / "ctx-with-broken-link.md"
    ctx.write_text("[X](../knowledge/missing/file.md)\n")

    # Defect 3: agent missing `name` key
    (wh / "agents" / "no-name.md").write_text(
        "---\ndescription: agent with no name\n---\n"
    )
    (wh / "agents" / "agents.yaml").write_text(yaml.dump({"no-name": {"skills": []}}))

    expected = {
        "skills/no-fm/SKILL.md": ["YAML frontmatter"],
        "contexts/ctx-with-broken-link.md": ["malformed cross-artifact link"],
        "agents/no-name.md": ["`name`"],
    }
    return wh, expected


def _run_lint(fixture_path: Path) -> subprocess.CompletedProcess:
    """Run `abc warehouse lint <fixture_path>` via uv run."""
    return subprocess.run(
        ["uv", "run", "--", "abc", "warehouse", "lint", str(fixture_path)],
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# Test: multi-defect fixture → exit 1
# ---------------------------------------------------------------------------


def test_lint_defective_fixture_exits_one(tmp_path):
    """TC11.2 TC1: three-defect fixture → returncode 1, stdout contains all error lines."""
    wh, expected = _build_defective_warehouse(tmp_path)

    # Smoke-assert fixture exists
    assert (wh / "skills" / "no-fm" / "SKILL.md").is_file()
    assert (wh / "contexts" / "ctx-with-broken-link.md").is_file()
    assert (wh / "agents" / "no-name.md").is_file()

    result = _run_lint(wh)

    assert result.returncode == 1, (
        f"Expected returncode 1, got {result.returncode}\nstdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )

    # Assert every defect's error line is present
    for artifact_path, error_substrings in expected.items():
        assert artifact_path in result.stdout, (
            f"Expected path header '{artifact_path}' in stdout.\n"
            f"stdout:\n{result.stdout}"
        )
        for substr in error_substrings:
            assert substr in result.stdout, (
                f"Expected '{substr}' in stdout for {artifact_path}.\n"
                f"stdout:\n{result.stdout}"
            )


def test_lint_defective_fixture_output_sorted_by_path(tmp_path):
    """TC11.2 TC2: stdout group ordering is alphabetical by path."""
    wh, _ = _build_defective_warehouse(tmp_path)
    result = _run_lint(wh)
    assert result.returncode == 1

    # Extract lines that look like group headers (no leading spaces)
    header_lines = [
        line.strip()
        for line in result.stdout.splitlines()
        if line
        and not line.startswith(" ")
        and "error:" not in line
        and "Found" not in line
    ]
    # Filter to lines that are known artifact paths
    artifact_headers = [
        h
        for h in header_lines
        if h
        in (
            "agents/no-name.md",
            "contexts/ctx-with-broken-link.md",
            "skills/no-fm/SKILL.md",
        )
    ]
    assert artifact_headers == sorted(artifact_headers), (
        f"Group headers not sorted: {artifact_headers}"
    )


def test_lint_defective_fixture_summary_line(tmp_path):
    """TC11.2 TC3: stdout summary line shows correct N and M counts."""
    wh, _ = _build_defective_warehouse(tmp_path)
    result = _run_lint(wh)
    assert result.returncode == 1
    # Should have 3 errors across 3 files
    assert "Found 3 error(s) across 3 file(s)." in result.stdout, (
        f"Expected summary line in stdout.\nstdout:\n{result.stdout}"
    )


# ---------------------------------------------------------------------------
# Test: clean fixture → exit 0
# ---------------------------------------------------------------------------


def test_lint_clean_fixture_exits_zero(tmp_path):
    """TC11.3: clean fixture → returncode 0 and 'Lint passed' in stdout."""
    wh = _build_clean_warehouse(tmp_path)

    result = _run_lint(wh)

    assert result.returncode == 0, (
        f"Expected returncode 0, got {result.returncode}\nstdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    assert "Lint passed" in result.stdout, (
        f"Expected 'Lint passed' in stdout.\nstdout:\n{result.stdout}"
    )
