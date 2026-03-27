"""End-to-end integration test: full CLI happy path.

Runs the complete user workflow in a single chained test:
  warehouse init → list → warehouse connect → setup → sync →
  status → delta → sync --preserve → sync --prune → update → clean

This test is the automated equivalent of the manual e2e walkthrough done
before each release. If this test passes, the core user journey works.

All tests are marked `integration` so they can be run independently of the
unit tests:

    pytest -m integration          # only e2e tests
    pytest -m "not integration"    # only unit tests (default CI run)
    pytest                         # everything
"""

import pytest
import yaml
from beacon.cli import main
from click.testing import CliRunner

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
    (wh / "knowledge" / "python").mkdir(parents=True, exist_ok=True)
    (wh / "knowledge" / "python" / "standards.md").write_text(
        "# Python Standards\n- Use type annotations\n"
    )
    (wh / "knowledge" / "decisions").mkdir(parents=True, exist_ok=True)
    (wh / "knowledge" / "decisions" / "use-uv.md").write_text(
        "# Decision: Use uv\nWe use uv for package management.\n"
    )
    skill_dir = wh / "skills" / "code-review"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text("# Skill: Code Review\n")

    return wh


@pytest.fixture
def e2e_project(tmp_path, e2e_warehouse, monkeypatch):
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
    assert (e2e_warehouse / "knowledge").is_dir()
    assert (e2e_warehouse / "skills").is_dir()
    assert (e2e_warehouse / "docs").is_dir()
    assert (e2e_warehouse / "README.md").exists()
    assert (e2e_warehouse / "contexts" / "README.md").exists()


def test_e2e_warehouse_init_installs_record_knowledge(e2e_warehouse):
    """warehouse init bundles record-knowledge as a distributable warehouse skill."""
    assert (e2e_warehouse / "skills" / "record-knowledge" / "SKILL.md").exists()


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
    assert "contexts/README.md" in result.output
    assert "Knowledge" in result.output
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
# Step 4 — setup --manual produces clean beacon.yaml template
# ---------------------------------------------------------------------------


def test_e2e_setup_manual_template(e2e_project):
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    result = runner.invoke(main, ["setup", "--manual"])

    assert result.exit_code == 0
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    assert beacon_yaml.exists()

    # Must be valid YAML with exactly one of each artifact key
    parsed = yaml.safe_load(beacon_yaml.read_text())
    assert parsed["artifacts"]["knowledge"] == []
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


def test_e2e_sync_copies_artifacts(e2e_project):
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  knowledge:\n"
        "    - knowledge/python/standards.md\n"
        "    - knowledge/decisions/use-uv.md\n"
        "  skills:\n"
        "    - skills/code-review/SKILL.md\n"
        "  contexts:\n"
        "    - contexts/README.md\n"
    )

    result = runner.invoke(main, ["sync"])

    assert result.exit_code == 0
    assert "Copied: 4" in result.output

    artifacts = project_dir / ".agentic-beacon" / "artifacts"
    assert (artifacts / "knowledge" / "python" / "standards.md").exists()
    assert (artifacts / "knowledge" / "decisions" / "use-uv.md").exists()
    assert (artifacts / "skills" / "code-review" / "SKILL.md").exists()
    assert (artifacts / "contexts" / "README.md").exists()


def test_e2e_sync_is_idempotent(e2e_project):
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  knowledge:\n"
        "    - knowledge/python/standards.md\n"
        "  skills: []\n"
        "  contexts: []\n"
    )

    runner.invoke(main, ["sync"])
    result = runner.invoke(main, ["sync"])

    assert result.exit_code == 0
    assert "Unchanged: 1" in result.output
    assert "Copied: 0" in result.output


def test_e2e_sync_glob_pattern(e2e_project):
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  knowledge:\n"
        "    - knowledge/**/*.md\n"
        "  skills: []\n"
        "  contexts: []\n"
    )

    result = runner.invoke(main, ["sync"])

    assert result.exit_code == 0
    artifacts = project_dir / ".agentic-beacon" / "artifacts"
    assert (artifacts / "knowledge" / "python" / "standards.md").exists()
    assert (artifacts / "knowledge" / "decisions" / "use-uv.md").exists()


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
        "  knowledge: []\n"
        "  skills:\n"
        "    - skills/code-review/SKILL.md\n"
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
# Step 7 — delta detects no changes, then detects a local modification
# ---------------------------------------------------------------------------


def test_e2e_delta_clean(e2e_project):
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  knowledge:\n"
        "    - knowledge/python/standards.md\n"
        "  skills: []\n"
        "  contexts: []\n"
    )
    runner.invoke(main, ["sync"])

    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 0
    assert "No differences" in result.output


def test_e2e_delta_detects_modification(e2e_project):
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  knowledge:\n"
        "    - knowledge/python/standards.md\n"
        "  skills: []\n"
        "  contexts: []\n"
    )
    runner.invoke(main, ["sync"])

    # Locally modify a synced artifact
    synced = (
        project_dir
        / ".agentic-beacon"
        / "artifacts"
        / "knowledge"
        / "python"
        / "standards.md"
    )
    synced.write_text(synced.read_text() + "- Local addition\n")

    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 0
    assert "Modified" in result.output
    assert "knowledge/python/standards.md" in result.output


# ---------------------------------------------------------------------------
# Steps 7a — delta correctly handles skills via live agent directories
# ---------------------------------------------------------------------------


def test_e2e_delta_skill_clean_after_sync(e2e_project):
    """After abc sync, delta reports skill as identical (live dir matches warehouse)."""
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    # Configure an opencode project
    (project_dir / "opencode.json").write_text("{}")

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  knowledge: []\n"
        "  skills:\n"
        "    - skills/code-review/SKILL.md\n"
        "  contexts: []\n"
    )
    sync_result = runner.invoke(main, ["sync"])
    assert sync_result.exit_code == 0

    # Verify the live skill was installed
    assert (project_dir / ".opencode" / "skills" / "code-review" / "SKILL.md").exists()

    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 0
    assert "No differences" in result.output


def test_e2e_delta_skill_detects_live_modification(e2e_project):
    """abc delta detects a modification made directly to the live agent skill file."""
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    (project_dir / "opencode.json").write_text("{}")

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  knowledge: []\n"
        "  skills:\n"
        "    - skills/code-review/SKILL.md\n"
        "  contexts: []\n"
    )
    runner.invoke(main, ["sync"])

    # Edit the live agent copy (simulates a user adding a guardrail locally)
    live_skill = project_dir / ".opencode" / "skills" / "code-review" / "SKILL.md"
    live_skill.write_text(live_skill.read_text() + "\n## Local Guardrail\nNo foo.\n")

    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 0
    assert "Modified" in result.output
    assert "skills/code-review/SKILL.md" in result.output


def test_e2e_delta_skill_snapshot_identical_but_live_modified(e2e_project):
    """Regression: delta catches live skill drift even when snapshot still matches warehouse.

    This is the exact bug scenario: snapshot == warehouse but live != warehouse.
    The old code would report 'No differences'. The fix makes it report Modified.
    """
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    (project_dir / "opencode.json").write_text("{}")

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  knowledge: []\n"
        "  skills:\n"
        "    - skills/code-review/SKILL.md\n"
        "  contexts: []\n"
    )
    runner.invoke(main, ["sync"])

    # Corrupt the live skill but leave the snapshot untouched
    live_skill = project_dir / ".opencode" / "skills" / "code-review" / "SKILL.md"
    live_skill.write_text("# Completely replaced\n")

    # Confirm snapshot is still identical to warehouse
    snapshot = (
        project_dir
        / ".agentic-beacon"
        / "artifacts"
        / "skills"
        / "code-review"
        / "SKILL.md"
    )
    warehouse_content = (warehouse / "skills" / "code-review" / "SKILL.md").read_text()
    assert snapshot.read_text() == warehouse_content

    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 0
    assert "Modified" in result.output, (
        "Expected 'Modified' — delta should detect live drift, not just snapshot drift"
    )


def test_e2e_delta_skill_per_agent_detail_in_output(e2e_project):
    """With both opencode and claudecode present, delta shows per-agent breakdown."""
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    # Both agents configured
    (project_dir / "opencode.json").write_text("{}")
    (project_dir / ".claude").mkdir()

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  knowledge: []\n"
        "  skills:\n"
        "    - skills/code-review/SKILL.md\n"
        "  contexts: []\n"
    )
    runner.invoke(main, ["sync"])

    # Edit only the opencode live copy
    oc_skill = project_dir / ".opencode" / "skills" / "code-review" / "SKILL.md"
    oc_skill.write_text(oc_skill.read_text() + "\n## Extra\n")

    result = runner.invoke(main, ["delta"])

    assert result.exit_code == 0
    assert "Modified" in result.output
    # Per-agent breakdown should appear
    assert "opencode" in result.output
    assert "claudecode" in result.output


# ---------------------------------------------------------------------------
# Step 8 — sync --preserve skips locally modified file
# ---------------------------------------------------------------------------


def test_e2e_sync_preserve(e2e_project):
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  knowledge:\n"
        "    - knowledge/python/standards.md\n"
        "  skills: []\n"
        "  contexts: []\n"
    )
    runner.invoke(main, ["sync"])

    synced = (
        project_dir
        / ".agentic-beacon"
        / "artifacts"
        / "knowledge"
        / "python"
        / "standards.md"
    )
    synced.write_text(synced.read_text() + "- Local addition\n")
    original_content = synced.read_text()

    result = runner.invoke(main, ["sync", "--preserve"])

    assert result.exit_code == 0
    assert "Preserved: 1" in result.output
    assert synced.read_text() == original_content  # unchanged


# ---------------------------------------------------------------------------
# Step 9 — sync --prune removes artifacts dropped from beacon.yaml
# ---------------------------------------------------------------------------


def test_e2e_sync_prune(e2e_project):
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  knowledge:\n"
        "    - knowledge/python/standards.md\n"
        "    - knowledge/decisions/use-uv.md\n"
        "  skills: []\n"
        "  contexts: []\n"
    )
    runner.invoke(main, ["sync"])

    # Drop one artifact
    beacon_yaml.write_text(
        "artifacts:\n"
        "  knowledge:\n"
        "    - knowledge/python/standards.md\n"
        "  skills: []\n"
        "  contexts: []\n"
    )

    result = runner.invoke(main, ["sync", "--prune"])

    assert result.exit_code == 0
    assert "Pruned: 1" in result.output
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
        / "knowledge"
        / "python"
        / "standards.md"
    )
    assert kept.exists()


# ---------------------------------------------------------------------------
# Step 10 — update pulls in an upstream warehouse change
# ---------------------------------------------------------------------------


def test_e2e_update_picks_up_upstream_change(e2e_project):
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  knowledge:\n"
        "    - knowledge/python/standards.md\n"
        "  skills: []\n"
        "  contexts: []\n"
    )
    runner.invoke(main, ["sync"])

    # Simulate an upstream change in the warehouse
    standards = warehouse / "knowledge" / "python" / "standards.md"
    standards.write_text(standards.read_text() + "- No bare excepts\n")

    result = runner.invoke(main, ["update"])

    assert result.exit_code == 0
    assert "Updated: 1" in result.output

    synced = (
        project_dir
        / ".agentic-beacon"
        / "artifacts"
        / "knowledge"
        / "python"
        / "standards.md"
    )
    assert "No bare excepts" in synced.read_text()


# ---------------------------------------------------------------------------
# Step 11 — clean removes the artifacts directory
# ---------------------------------------------------------------------------


def test_e2e_clean(e2e_project):
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  knowledge:\n"
        "    - knowledge/python/standards.md\n"
        "  skills: []\n"
        "  contexts: []\n"
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
    """Full workflow: sync → edit live skill → contribute → warehouse updated.

    This is the core scenario: user syncs, tweaks the installed skill in
    their agent folder, then contributes it back. Without the fix, contribute
    would copy the stale snapshot (identical to warehouse) and silently do nothing.
    """
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    (project_dir / "opencode.json").write_text("{}")

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  knowledge: []\n"
        "  skills:\n"
        "    - skills/code-review/SKILL.md\n"
        "  contexts: []\n"
    )
    runner.invoke(main, ["sync"])

    # Edit the live agent copy
    live_skill = project_dir / ".opencode" / "skills" / "code-review" / "SKILL.md"
    original = live_skill.read_text()
    live_skill.write_text(original + "\n## Local Guardrail\nNo foo.\n")

    result = runner.invoke(main, ["contribute", "skills/code-review/SKILL.md"])

    assert result.exit_code == 0, result.output
    # Warehouse now contains the live version
    warehouse_skill = warehouse / "skills" / "code-review" / "SKILL.md"
    assert "Local Guardrail" in warehouse_skill.read_text()


def test_e2e_contribute_skill_regression_stale_snapshot(e2e_project):
    """Regression: contribute does not silently skip when snapshot matches warehouse.

    Snapshot == warehouse (unchanged) but live dir has edits.
    Old behaviour: reported 'Nothing to contribute'. Fix: reads live dir.
    """
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    (project_dir / "opencode.json").write_text("{}")

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  knowledge: []\n"
        "  skills:\n"
        "    - skills/code-review/SKILL.md\n"
        "  contexts: []\n"
    )
    runner.invoke(main, ["sync"])

    # Edit only the live dir, leave the snapshot alone
    live_skill = project_dir / ".opencode" / "skills" / "code-review" / "SKILL.md"
    live_skill.write_text("# Completely replaced\n")

    # Confirm snapshot still matches warehouse
    snapshot = (
        project_dir
        / ".agentic-beacon"
        / "artifacts"
        / "skills"
        / "code-review"
        / "SKILL.md"
    )
    warehouse_content = (warehouse / "skills" / "code-review" / "SKILL.md").read_text()
    assert snapshot.read_text() == warehouse_content

    result = runner.invoke(main, ["contribute", "skills/code-review/SKILL.md"])

    assert result.exit_code == 0, result.output
    assert "nothing to contribute" not in result.output.lower(), (
        "Should not skip — live dir has changes"
    )
    assert (warehouse / "skills" / "code-review" / "SKILL.md").read_text() == (
        "# Completely replaced\n"
    )


def test_e2e_contribute_all_skill_live_modification(e2e_project):
    """abc contribute (no file) picks up live-dir skill changes."""
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    (project_dir / "opencode.json").write_text("{}")

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  knowledge:\n"
        "    - knowledge/python/standards.md\n"
        "  skills:\n"
        "    - skills/code-review/SKILL.md\n"
        "  contexts: []\n"
    )
    runner.invoke(main, ["sync"])

    # Edit the live skill only (knowledge snapshot left alone)
    live_skill = project_dir / ".opencode" / "skills" / "code-review" / "SKILL.md"
    live_skill.write_text(live_skill.read_text() + "\n## Extra\n")

    result = runner.invoke(main, ["contribute", "--manual-git"])

    assert result.exit_code == 0, result.output
    assert "code-review" in result.output or "✓" in result.output
    assert "Extra" in (warehouse / "skills" / "code-review" / "SKILL.md").read_text()


def test_e2e_contribute_skill_identical_live_is_noop(e2e_project):
    """abc contribute <skill> reports nothing to contribute when live matches warehouse."""
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    (project_dir / "opencode.json").write_text("{}")

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  knowledge: []\n"
        "  skills:\n"
        "    - skills/code-review/SKILL.md\n"
        "  contexts: []\n"
    )
    runner.invoke(main, ["sync"])
    # Live dir is untouched after sync — identical to warehouse

    result = runner.invoke(main, ["contribute", "skills/code-review/SKILL.md"])

    assert result.exit_code == 0
    assert "nothing to contribute" in result.output.lower()


def test_e2e_contribute_skill_multi_agent_conflict_prompts(e2e_project):
    """With two agents holding different edits, contribute prompts the user."""
    project_dir, warehouse, runner = e2e_project
    runner.invoke(main, ["warehouse", "connect", "--path", str(warehouse)])

    # Both agents configured
    (project_dir / "opencode.json").write_text("{}")
    (project_dir / ".claude").mkdir()

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n"
        "  knowledge: []\n"
        "  skills:\n"
        "    - skills/code-review/SKILL.md\n"
        "  contexts: []\n"
    )
    runner.invoke(main, ["sync"])

    # Each agent has a different edit
    oc_skill = project_dir / ".opencode" / "skills" / "code-review" / "SKILL.md"
    oc_skill.write_text(oc_skill.read_text() + "\n## OpenCode edit\n")

    cc_skill = project_dir / ".claude" / "skills" / "code-review" / "SKILL.md"
    cc_skill.write_text(cc_skill.read_text() + "\n## Claude edit\n")

    # User picks option 1 (opencode)
    result = runner.invoke(
        main, ["contribute", "skills/code-review/SKILL.md"], input="1\n"
    )

    assert result.exit_code == 0, result.output
    assert "conflict" in result.output.lower()
    # Warehouse gets the opencode version
    assert (
        "OpenCode edit"
        in (warehouse / "skills" / "code-review" / "SKILL.md").read_text()
    )
