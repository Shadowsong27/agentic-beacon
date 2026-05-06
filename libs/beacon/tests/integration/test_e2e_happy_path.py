"""End-to-end integration test: full CLI happy path.

Runs the complete user workflow in a single chained test:
  warehouse init → list → warehouse connect → setup → sync →
  status → warehouse status → sync → sync --prune → update → clean

This test is the automated equivalent of the manual e2e walkthrough done
before each release. If this test passes, the core user journey works.

All tests are marked `integration` so they can be run independently of the
unit tests:

    pytest -m integration          # only e2e tests
    pytest -m "not integration"    # only unit tests (default CI run)
    pytest                         # everything
"""

import os
import subprocess

import pytest
import yaml
from beacon.cli.main import main
from click.testing import CliRunner


def _git_env():
    return {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "t@t.local",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "t@t.local",
    }


pytestmark = pytest.mark.integration


@pytest.fixture
def e2e_warehouse(tmp_path):
    """
    A warehouse initialised via 'abc warehouse init', then populated with
    a small set of real artifacts so every sync/delta scenario has content.
    """
    runner = CliRunner()

    # --- init ---
    result = runner.invoke(
        main,
        [
            "warehouse",
            "init",
            "my-warehouse",
            "--path",
            str(tmp_path),
            "--org",
            "Test Org",
            "--languages",
            "python",
            "--no-interactive",
            "--no-git",
        ],
    )
    assert result.exit_code == 0, f"warehouse init failed:\n{result.output}"

    wh = tmp_path / "my-warehouse"

    # Add real artifacts so sync has something to copy
    (wh / "contexts" / "team.md").write_text(
        "# Team Context\nStandards for the team.\n"
    )
    (wh / "contexts" / "python").mkdir(parents=True, exist_ok=True)
    (wh / "contexts" / "python" / "standards.md").write_text(
        "# Python Standards\n- Use type annotations\n"
    )
    (wh / "contexts" / "decisions").mkdir(parents=True, exist_ok=True)
    (wh / "contexts" / "decisions" / "use-uv.md").write_text(
        "# Decision: Use uv\nWe use uv for package management.\n"
    )
    skill_dir = wh / "skills" / "code-review"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nrequires:\n  contexts: []\n---\n# Skill: Code Review\n"
    )

    # Init git and commit files (required by symlink-based sync)
    env = _git_env()
    subprocess.run(["git", "init"], cwd=wh, env=env, check=True, capture_output=True)
    subprocess.run(
        ["git", "add", "."], cwd=wh, env=env, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Add test artifacts"],
        cwd=wh,
        env=env,
        check=True,
        capture_output=True,
    )

    return wh


@pytest.fixture
def e2e_project(tmp_path, e2e_warehouse, monkeypatch, isolated_home):
    """A project directory wired up to e2e_warehouse, ready for workflow steps."""
    project_dir = tmp_path / "my-project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)
    return project_dir, e2e_warehouse, CliRunner()


# ---------------------------------------------------------------------------
# Step 1 — warehouse init creates the expected structure
# ---------------------------------------------------------------------------


def test_e2e_warehouse_init_creates_structure(e2e_warehouse):
    """warehouse init produces contexts/, knowledge/, skills/, docs/, README.md."""
    assert (e2e_warehouse / "contexts").is_dir()
    assert (e2e_warehouse / "contexts").is_dir()
    assert (e2e_warehouse / "skills").is_dir()
    assert (e2e_warehouse / "docs").is_dir()
    assert (e2e_warehouse / "README.md").exists()
    assert (e2e_warehouse / "contexts" / "README.md").exists()


def test_e2e_warehouse_init_installs_record_knowledge(e2e_warehouse):
    """warehouse init bundles record-knowledge as a distributable warehouse skill."""
    assert (e2e_warehouse / "skills" / "record-knowledge" / "SKILL.md").exists()


def test_e2e_warehouse_init_installs_record_skill(e2e_warehouse):
    """warehouse init bundles record-skill as a distributable warehouse skill."""
    assert (e2e_warehouse / "skills" / "record-skill" / "SKILL.md").exists()
    assert (
        e2e_warehouse / "skills" / "record-skill" / "scripts" / "resolve_warehouse.py"
    ).exists()
    assert (
        e2e_warehouse / "skills" / "record-skill" / "scripts" / "append_pending.py"
    ).exists()


# ---------------------------------------------------------------------------
# Step 2 — abc warehouse list shows all three sections including Contexts
# ---------------------------------------------------------------------------


def test_e2e_warehouse_list_shows_contexts(e2e_project):
    project_dir, warehouse, runner = e2e_project

    # Connect first so warehouse list can read config.toml
    connect = runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])
    assert connect.exit_code == 0, f"connect failed:\n{connect.output}"

    result = runner.invoke(main, ["warehouse", "list"])

    assert result.exit_code == 0
    assert "Contexts" in result.output
    assert "contexts/team.md" in result.output
    assert "contexts/README.md" not in result.output
    assert "Skills" in result.output


# ---------------------------------------------------------------------------
# Step 3 — warehouse connect
# ---------------------------------------------------------------------------


def test_e2e_warehouse_connect(e2e_project):
    project_dir, warehouse, runner = e2e_project

    result = runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    assert result.exit_code == 0
    assert "Connected" in result.output

    config = project_dir / ".agentic-beacon" / "config.toml"
    assert config.exists()
    assert str(warehouse) in config.read_text()


# ---------------------------------------------------------------------------
# Step 4 — setup produces clean beacon.yaml template
# ---------------------------------------------------------------------------


def test_e2e_setup_manual_template(e2e_project):
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    result = runner.invoke(main, ["setup"])

    assert result.exit_code == 0
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    assert beacon_yaml.exists()

    # Must be valid YAML with exactly one of each artifact key
    parsed = yaml.safe_load(beacon_yaml.read_text())
    assert "skills" in parsed["artifacts"]
    assert parsed["artifacts"]["skills"] == []
    assert parsed["artifacts"]["contexts"] == []

    raw = beacon_yaml.read_text()
    # No duplicate keys (Bug #1 regression)
    import re

    assert len(re.findall(r"^\s{2}skills:", raw, re.MULTILINE)) == 1
    # Context comments use current path format (Bug #1/#4 regression)
    assert "AGENTS.global.md" not in raw
    assert "contexts/README.md" in raw

    # ---------------------------------------------------------------------------
    # Step 5 — sync copies all declared artifacts
    # ---------------------------------------------------------------------------

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  contexts:\n"
        "    - contexts/python/standards.md\n"
        "    - contexts/decisions/use-uv.md\n"
        "    - contexts/README.md\n"
        ""
        "  skills:\n"
        "    - skills/code-review/\n"
    )

    result = runner.invoke(main, ["sync"])

    assert result.exit_code == 0
    # Copy-based output changed to symlink-based

    artifacts = project_dir / ".agentic-beacon" / "artifacts"
    assert (artifacts / "contexts" / "python" / "standards.md").exists()
    assert (artifacts / "contexts" / "decisions" / "use-uv.md").exists()
    assert (artifacts / "skills" / "code-review" / "SKILL.md").exists()
    assert (artifacts / "contexts" / "README.md").exists()


def test_e2e_sync_is_idempotent(e2e_project):
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  contexts:\n    - contexts/python/standards.md\n  skills: []\n"
    )

    runner.invoke(main, ["sync"])
    result = runner.invoke(main, ["sync"])

    assert result.exit_code == 0
    assert "Up to date" in result.output or "symlink" in result.output.lower()
    assert "Created: 0" in result.output or "Up to date" in result.output

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  contexts:\n    - contexts/**/*.md\n  skills: []\n"
    )

    result = runner.invoke(main, ["sync"])

    assert result.exit_code == 0
    artifacts = project_dir / ".agentic-beacon" / "artifacts"
    assert (artifacts / "contexts" / "python" / "standards.md").exists()
    assert (artifacts / "contexts" / "decisions" / "use-uv.md").exists()


# ---------------------------------------------------------------------------
# Step 6 — status shows ✓ for synced contexts and skills
# ---------------------------------------------------------------------------


def test_e2e_status_shows_check_marks_for_synced(e2e_project):
    """status correctly shows ✓ for synced items (Bug #2 regression)."""
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "\n"
        "  skills:\n"
        "    - skills/code-review/\n"
        "  contexts:\n"
        "    - contexts/README.md\n"
    )
    runner.invoke(main, ["sync"])

    result = runner.invoke(main, ["status"])

    assert result.exit_code == 0
    assert "✗ contexts/README.md" not in result.output
    assert "✗ skills/code-review/SKILL.md" not in result.output
    assert "✓" in result.output


# ---------------------------------------------------------------------------
# Step 7 — warehouse status and delta shim behavior
# ---------------------------------------------------------------------------


def test_e2e_delta_shim_redirects_to_warehouse_status(e2e_project):
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 1
    assert "has been removed" in result.output
    assert "warehouse status" in result.output


def test_e2e_warehouse_status_clean(e2e_project):
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  contexts:\n    - contexts/python/standards.md\n  skills: []\n"
    )
    runner.invoke(main, ["sync"])

    result = runner.invoke(main, ["warehouse", "status"])

    assert result.exit_code == 0
    assert "Working tree is clean" in result.output

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  contexts:\n    - contexts/python/standards.md\n  skills: []\n"
    )
    runner.invoke(main, ["sync"])

    # Locally modify a synced artifact
    synced = (
        project_dir
        / ".agentic-beacon"
        / "artifacts"
        / "contexts"
        / "python"
        / "standards.md"
    )
    synced.write_text(synced.read_text() + "- Local addition\n")

    result = runner.invoke(main, ["warehouse", "status"])

    assert result.exit_code == 0
    assert "modified" in result.output.lower()
    assert "contexts/python/standards.md" in result.output


# ---------------------------------------------------------------------------
# Steps 7a — delta correctly handles skills via live agent directories
# ---------------------------------------------------------------------------


def test_e2e_delta_skill_clean_after_sync(e2e_project, isolated_home):
    """After abc sync, warehouse status reports the live skill as clean."""
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    # Configure an opencode project
    (project_dir / "opencode.json").write_text("{}")

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n\n  skills:\n    - skills/code-review/\n  contexts: []\n"
    )
    sync_result = runner.invoke(main, ["sync"])
    assert sync_result.exit_code == 0

    # Verify the live skill was installed
    assert (project_dir / ".opencode" / "skills" / "code-review" / "SKILL.md").exists()

    result = runner.invoke(main, ["warehouse", "status"])

    assert result.exit_code == 0
    assert "Working tree is clean" in result.output


def test_e2e_delta_skill_detects_live_modification(e2e_project):
    """warehouse status detects a modification made directly in the warehouse skill file."""
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    (project_dir / "opencode.json").write_text("{}")

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n\n  skills:\n    - skills/code-review/\n  contexts: []\n"
    )
    runner.invoke(main, ["sync"])

    warehouse_skill = warehouse / "skills" / "code-review" / "SKILL.md"
    warehouse_skill.write_text(
        warehouse_skill.read_text() + "\n## Warehouse Guardrail\nNo foo.\n"
    )

    result = runner.invoke(main, ["warehouse", "status"])

    assert result.exit_code == 0
    assert "modified" in result.output.lower()
    assert "skills/code-review/SKILL.md" in result.output


def test_e2e_delta_skill_snapshot_identical_but_live_modified(e2e_project):
    """abc delta now redirects users to abc warehouse status."""
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 1
    assert "has been removed" in result.output
    assert "warehouse status" in result.output


def test_e2e_delta_skill_per_agent_detail_in_output(e2e_project):
    """abc delta no longer exposes per-agent live-dir detail and redirects instead."""
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 1
    assert "has been removed" in result.output
    assert "warehouse status" in result.output

    # ---------------------------------------------------------------------------
    # Step 9 — sync auto-prune removes artifacts dropped from beacon.yaml
    # ---------------------------------------------------------------------------

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  contexts:\n"
        "    - contexts/python/standards.md\n"
        "    - contexts/decisions/use-uv.md\n"
        ""
        "  skills: []\n"
    )
    runner.invoke(main, ["sync"])

    # Drop one artifact
    beacon_yaml.write_text(
        "artifacts:\n  contexts:\n    - contexts/python/standards.md\n  skills: []\n"
    )

    # Auto-prune: confirm deletion with "y"
    result = runner.invoke(main, ["sync"], input="y\n")

    assert result.exit_code == 0
    assert "Removed:" in result.output or "removed" in result.output.lower()
    dropped = (
        project_dir
        / ".agentic-beacon"
        / "artifacts"
        / "knowledge"
        / "decisions"
        / "use-uv.md"
    )
    assert not dropped.exists()
    kept = (
        project_dir
        / ".agentic-beacon"
        / "artifacts"
        / "contexts"
        / "python"
        / "standards.md"
    )
    assert kept.exists()

    # ---------------------------------------------------------------------------
    # Step 10 — update pulls in an upstream warehouse change
    # ---------------------------------------------------------------------------

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  contexts:\n    - contexts/python/standards.md\n  skills: []\n"
    )
    runner.invoke(main, ["sync"])

    # Simulate an upstream change in the warehouse
    standards = warehouse / "contexts" / "python" / "standards.md"
    standards.write_text(standards.read_text() + "- No bare excepts\n")

    result = runner.invoke(main, ["update"])

    assert result.exit_code == 0
    assert result.exit_code == 0  # deprecated abc update still works

    synced = (
        project_dir
        / ".agentic-beacon"
        / "artifacts"
        / "contexts"
        / "python"
        / "standards.md"
    )
    assert "No bare excepts" in synced.read_text()

    # ---------------------------------------------------------------------------
    # Step 11 — clean removes the artifacts directory
    # ---------------------------------------------------------------------------

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  contexts:\n    - contexts/python/standards.md\n  skills: []\n"
    )
    runner.invoke(main, ["sync"])
    assert (project_dir / ".agentic-beacon" / "artifacts").exists()

    result = runner.invoke(main, ["clean", "--yes"])

    assert result.exit_code == 0
    assert not (project_dir / ".agentic-beacon" / "artifacts").exists()
    # config.toml and beacon.yaml should remain
    assert (project_dir / ".agentic-beacon" / "config.toml").exists()
    assert (project_dir / ".agentic-beacon" / "beacon.yaml").exists()


# ---------------------------------------------------------------------------
# Steps 7b — contribute correctly pushes skill changes back to warehouse
# from the live agent directory, not the stale artifact snapshot
# ---------------------------------------------------------------------------


def test_e2e_contribute_skill_live_modification_goes_to_warehouse(e2e_project):
    """abc warehouse contribute commits warehouse working-tree changes."""
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n\n  skills:\n    - skills/code-review/\n  contexts: []\n"
    )
    runner.invoke(main, ["sync"])

    warehouse_skill = warehouse / "skills" / "code-review" / "SKILL.md"
    warehouse_skill.write_text(
        warehouse_skill.read_text() + "\n## Local Guardrail\nNo foo.\n"
    )

    result = runner.invoke(main, ["warehouse", "contribute", "-m", "skill update"])

    assert result.exit_code == 0, result.output
    assert "Local Guardrail" in warehouse_skill.read_text()


def test_e2e_contribute_skill_regression_stale_snapshot(e2e_project):
    """Old abc contribute redirects users to abc warehouse contribute."""
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    result = runner.invoke(main, ["contribute"])

    assert result.exit_code == 1
    assert "has been removed" in result.output
    assert "warehouse contribute" in result.output


def test_e2e_contribute_all_skill_live_modification(e2e_project):
    """Old fileless abc contribute also redirects users to abc warehouse contribute."""
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    result = runner.invoke(main, ["contribute"])

    assert result.exit_code == 1
    assert "has been removed" in result.output
    assert "warehouse contribute" in result.output


def test_e2e_contribute_skill_identical_live_is_noop(e2e_project):
    """abc warehouse contribute reports nothing to contribute when live matches warehouse."""
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    (project_dir / "opencode.json").write_text("{}")

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n\n  skills:\n    - skills/code-review/\n  contexts: []\n"
    )
    runner.invoke(main, ["sync"])
    # Live dir is untouched after sync — identical to warehouse

    result = runner.invoke(main, ["warehouse", "contribute", "-m", "noop contribute"])

    assert result.exit_code == 0
    assert "no uncommitted changes to contribute" in result.output.lower()


def test_e2e_contribute_skill_multi_agent_conflict_prompts(e2e_project):
    """Old abc contribute shim redirects users to abc warehouse contribute."""
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])
    result = runner.invoke(main, ["contribute"])

    assert result.exit_code == 1
    assert "has been removed" in result.output
    assert "warehouse contribute" in result.output
