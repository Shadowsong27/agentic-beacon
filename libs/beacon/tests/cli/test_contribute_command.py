"""Tests for abc contribute command."""

import pytest
from beacon.cli import main
from click.testing import CliRunner

KNOWLEDGE_CONTENT_ORIGINAL = "# Type Hints\n\nUse type hints.\n"
KNOWLEDGE_CONTENT_MODIFIED = (
    "# Type Hints\n\nUse type hints.\nPrefer `str | None` over `Optional[str]`.\n"
)
ADDED_CONTENT = "# New Lesson\n\nSomething new discovered locally.\n"

BEACON_YAML = """\
artifacts:
  knowledge:
    - knowledge/python/type-hints.md
    - knowledge/python/new-lesson.md
  skills: []
  contexts: []
"""


@pytest.fixture
def project_with_delta(tmp_path, monkeypatch):
    """Project with a warehouse, beacon config, and local artifact changes."""
    monkeypatch.chdir(tmp_path)

    # Warehouse structure
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    (warehouse / "contexts").mkdir()
    (warehouse / "knowledge").mkdir()
    (warehouse / "skills").mkdir()
    (warehouse / "docs").mkdir()
    (warehouse / "README.md").write_text("# Warehouse")

    knowledge_dir = warehouse / "knowledge" / "python"
    knowledge_dir.mkdir(parents=True)
    (knowledge_dir / "type-hints.md").write_text(KNOWLEDGE_CONTENT_ORIGINAL)
    # new-lesson.md does NOT exist in warehouse (ADDED case)

    # Project .agentic-beacon
    beacon_dir = tmp_path / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "config.toml").write_text(
        f'[warehouse]\nlocal_path = "{warehouse}"\n'
    )
    (beacon_dir / "beacon.yaml").write_text(BEACON_YAML)

    # Local artifacts (modified + added)
    artifacts_knowledge = beacon_dir / "artifacts" / "knowledge" / "python"
    artifacts_knowledge.mkdir(parents=True)
    (artifacts_knowledge / "type-hints.md").write_text(KNOWLEDGE_CONTENT_MODIFIED)
    (artifacts_knowledge / "new-lesson.md").write_text(ADDED_CONTENT)

    return tmp_path, warehouse


# ---------------------------------------------------------------------------
# Single file contribution
# ---------------------------------------------------------------------------


def test_contribute_single_modified_file(project_with_delta):
    tmp_path, warehouse = project_with_delta
    runner = CliRunner()

    result = runner.invoke(main, ["contribute", "knowledge/python/type-hints.md"])

    assert result.exit_code == 0, result.output
    dest = warehouse / "knowledge" / "python" / "type-hints.md"
    assert dest.read_text() == KNOWLEDGE_CONTENT_MODIFIED


def test_contribute_single_added_file(project_with_delta):
    """ADDED file (exists locally, not in warehouse) is copied to warehouse."""
    tmp_path, warehouse = project_with_delta
    runner = CliRunner()

    result = runner.invoke(main, ["contribute", "knowledge/python/new-lesson.md"])

    assert result.exit_code == 0, result.output
    dest = warehouse / "knowledge" / "python" / "new-lesson.md"
    assert dest.exists()
    assert dest.read_text() == ADDED_CONTENT


def test_contribute_identical_file_is_noop(project_with_delta):
    """IDENTICAL file produces a friendly message and exit 0."""
    tmp_path, warehouse = project_with_delta
    runner = CliRunner()

    # Make local match warehouse
    local = (
        tmp_path
        / ".agentic-beacon"
        / "artifacts"
        / "knowledge"
        / "python"
        / "type-hints.md"
    )
    local.write_text(KNOWLEDGE_CONTENT_ORIGINAL)

    result = runner.invoke(main, ["contribute", "knowledge/python/type-hints.md"])

    assert result.exit_code == 0
    assert "nothing to contribute" in result.output.lower()
    # Warehouse unchanged
    assert (
        warehouse / "knowledge" / "python" / "type-hints.md"
    ).read_text() == KNOWLEDGE_CONTENT_ORIGINAL


# ---------------------------------------------------------------------------
# --all flag
# ---------------------------------------------------------------------------


def test_contribute_all_copies_modified_and_added(project_with_delta):
    tmp_path, warehouse = project_with_delta
    runner = CliRunner()

    result = runner.invoke(main, ["contribute", "--all"])

    assert result.exit_code == 0, result.output
    assert (
        warehouse / "knowledge" / "python" / "type-hints.md"
    ).read_text() == KNOWLEDGE_CONTENT_MODIFIED
    assert (
        warehouse / "knowledge" / "python" / "new-lesson.md"
    ).read_text() == ADDED_CONTENT


def test_contribute_all_nothing_to_contribute(project_with_delta):
    """When all artifacts are identical, --all reports nothing to contribute."""
    tmp_path, warehouse = project_with_delta
    runner = CliRunner()

    # Sync local back to original so nothing differs
    local_hints = (
        tmp_path
        / ".agentic-beacon"
        / "artifacts"
        / "knowledge"
        / "python"
        / "type-hints.md"
    )
    local_hints.write_text(KNOWLEDGE_CONTENT_ORIGINAL)
    # Remove added file to make both identical
    local_new = (
        tmp_path
        / ".agentic-beacon"
        / "artifacts"
        / "knowledge"
        / "python"
        / "new-lesson.md"
    )
    local_new.unlink()
    # Add new-lesson to warehouse so it's also "identical" (both absent from local)
    # Actually MISSING means it's in beacon.yaml but not local — we just remove it

    result = runner.invoke(main, ["contribute", "--all"])

    assert result.exit_code == 0
    assert "nothing to contribute" in result.output.lower()


# ---------------------------------------------------------------------------
# --dry-run flag
# ---------------------------------------------------------------------------


def test_contribute_dry_run_does_not_copy(project_with_delta):
    tmp_path, warehouse = project_with_delta
    runner = CliRunner()

    result = runner.invoke(
        main, ["contribute", "knowledge/python/type-hints.md", "--dry-run"]
    )

    assert result.exit_code == 0, result.output
    assert "dry" in result.output.lower() or "would" in result.output.lower()
    # Warehouse NOT modified
    assert (
        warehouse / "knowledge" / "python" / "type-hints.md"
    ).read_text() == KNOWLEDGE_CONTENT_ORIGINAL


def test_contribute_all_dry_run_does_not_copy(project_with_delta):
    tmp_path, warehouse = project_with_delta
    runner = CliRunner()

    result = runner.invoke(main, ["contribute", "--all", "--dry-run"])

    assert result.exit_code == 0, result.output
    # Warehouse files unchanged
    assert (
        warehouse / "knowledge" / "python" / "type-hints.md"
    ).read_text() == KNOWLEDGE_CONTENT_ORIGINAL
    assert not (warehouse / "knowledge" / "python" / "new-lesson.md").exists()


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_contribute_errors_without_file_or_all(project_with_delta):
    runner = CliRunner()
    result = runner.invoke(main, ["contribute"])
    assert result.exit_code != 0


def test_contribute_errors_with_file_and_all(project_with_delta):
    runner = CliRunner()
    result = runner.invoke(
        main, ["contribute", "knowledge/python/type-hints.md", "--all"]
    )
    assert result.exit_code != 0


def test_contribute_errors_when_file_not_in_beacon_yaml(project_with_delta):
    """A file that doesn't exist locally is always rejected (can't contribute nothing)."""
    runner = CliRunner()
    result = runner.invoke(main, ["contribute", "knowledge/unlisted/file.md"])
    assert result.exit_code != 0
    # File doesn't exist locally — that's the first error reported now
    assert "error" in result.output.lower()


def test_contribute_errors_when_unrecognisable_path(project_with_delta):
    """A local file whose path doesn't start with knowledge/skills/contexts is rejected."""
    tmp_path, warehouse = project_with_delta
    runner = CliRunner()

    # Create a local file with an unrecognisable path prefix
    weird = tmp_path / ".agentic-beacon" / "artifacts" / "misc" / "random.md"
    weird.parent.mkdir(parents=True)
    weird.write_text("random")

    result = runner.invoke(main, ["contribute", "misc/random.md"])
    assert result.exit_code != 0
    assert (
        "type" in result.output.lower()
        or "infer" in result.output.lower()
        or "not tracked" in result.output.lower()
    )


def test_contribute_errors_when_file_not_synced_locally(project_with_delta):
    """File is in beacon.yaml but not downloaded yet."""
    tmp_path, warehouse = project_with_delta
    # Remove local artifact
    local = (
        tmp_path
        / ".agentic-beacon"
        / "artifacts"
        / "knowledge"
        / "python"
        / "type-hints.md"
    )
    local.unlink()

    runner = CliRunner()
    result = runner.invoke(main, ["contribute", "knowledge/python/type-hints.md"])
    assert result.exit_code != 0
    assert "sync" in result.output.lower() or "not" in result.output.lower()


def test_contribute_errors_without_beacon_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["contribute", "knowledge/python/type-hints.md"])
    assert result.exit_code != 0
    assert ".agentic-beacon" in result.output


def test_contribute_errors_without_warehouse_connection(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".agentic-beacon").mkdir()
    # No config.toml
    runner = CliRunner()
    result = runner.invoke(main, ["contribute", "knowledge/python/type-hints.md"])
    assert result.exit_code != 0
    assert "warehouse" in result.output.lower()


# ---------------------------------------------------------------------------
# beacon.yaml auto-registration for untracked files
# ---------------------------------------------------------------------------


BEACON_YAML_NO_NEW_LESSON = """\
artifacts:
  knowledge:
    - knowledge/python/type-hints.md
  skills: []
  contexts: []
"""


@pytest.fixture
def project_with_untracked(tmp_path, monkeypatch):
    """Project where a local artifact is NOT listed in beacon.yaml."""
    monkeypatch.chdir(tmp_path)

    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    (warehouse / "contexts").mkdir()
    (warehouse / "knowledge").mkdir()
    (warehouse / "skills").mkdir()
    (warehouse / "docs").mkdir()
    (warehouse / "README.md").write_text("# Warehouse")

    knowledge_dir = warehouse / "knowledge" / "python"
    knowledge_dir.mkdir(parents=True)
    (knowledge_dir / "type-hints.md").write_text(KNOWLEDGE_CONTENT_ORIGINAL)

    beacon_dir = tmp_path / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "config.toml").write_text(
        f'[warehouse]\nlocal_path = "{warehouse}"\n'
    )
    (beacon_dir / "beacon.yaml").write_text(BEACON_YAML_NO_NEW_LESSON)

    # Local artifacts: known file + an untracked brand-new file
    artifacts_knowledge = beacon_dir / "artifacts" / "knowledge" / "python"
    artifacts_knowledge.mkdir(parents=True)
    (artifacts_knowledge / "type-hints.md").write_text(KNOWLEDGE_CONTENT_ORIGINAL)
    (artifacts_knowledge / "new-lesson.md").write_text(ADDED_CONTENT)

    return tmp_path, warehouse


def test_contribute_single_untracked_file_copies_and_registers(project_with_untracked):
    """Contributing a file not in beacon.yaml copies it and adds it to beacon.yaml."""
    tmp_path, warehouse = project_with_untracked
    runner = CliRunner()

    result = runner.invoke(main, ["contribute", "knowledge/python/new-lesson.md"])

    assert result.exit_code == 0, result.output
    # File copied to warehouse
    assert (
        warehouse / "knowledge" / "python" / "new-lesson.md"
    ).read_text() == ADDED_CONTENT
    # beacon.yaml updated
    import yaml

    beacon_yaml = tmp_path / ".agentic-beacon" / "beacon.yaml"
    data = yaml.safe_load(beacon_yaml.read_text())
    assert "knowledge/python/new-lesson.md" in data["artifacts"]["knowledge"]


def test_contribute_all_untracked_file_copies_and_registers(project_with_untracked):
    """--all also contributes untracked local files and registers them in beacon.yaml."""
    tmp_path, warehouse = project_with_untracked
    runner = CliRunner()

    result = runner.invoke(main, ["contribute", "--all"])

    assert result.exit_code == 0, result.output
    # Untracked file copied
    assert (
        warehouse / "knowledge" / "python" / "new-lesson.md"
    ).read_text() == ADDED_CONTENT
    # Registered in beacon.yaml
    import yaml

    beacon_yaml = tmp_path / ".agentic-beacon" / "beacon.yaml"
    data = yaml.safe_load(beacon_yaml.read_text())
    assert "knowledge/python/new-lesson.md" in data["artifacts"]["knowledge"]


def test_contribute_all_dry_run_does_not_register(project_with_untracked):
    """--all --dry-run does not modify beacon.yaml."""
    tmp_path, warehouse = project_with_untracked
    runner = CliRunner()

    beacon_yaml = tmp_path / ".agentic-beacon" / "beacon.yaml"
    original_content = beacon_yaml.read_text()

    result = runner.invoke(main, ["contribute", "--all", "--dry-run"])

    assert result.exit_code == 0, result.output
    # beacon.yaml unchanged
    assert beacon_yaml.read_text() == original_content
    # File not copied to warehouse
    assert not (warehouse / "knowledge" / "python" / "new-lesson.md").exists()


def test_contribute_single_already_tracked_does_not_duplicate(project_with_delta):
    """Contributing a file already in beacon.yaml does not add a duplicate entry."""
    tmp_path, warehouse = project_with_delta
    runner = CliRunner()

    beacon_yaml = tmp_path / ".agentic-beacon" / "beacon.yaml"

    result = runner.invoke(main, ["contribute", "knowledge/python/type-hints.md"])

    assert result.exit_code == 0, result.output
    import yaml

    data = yaml.safe_load(beacon_yaml.read_text())
    knowledge = data["artifacts"]["knowledge"]
    assert knowledge.count("knowledge/python/type-hints.md") == 1


# ---------------------------------------------------------------------------
# Skills: contribute from live agent directories (bug fix)
# abc contribute must read from the live agent path, not the artifact snapshot.
# ---------------------------------------------------------------------------

SKILL_WAREHOUSE_CONTENT = "# Skill: My Skill\n\n## Purpose\nDoes something.\n"
SKILL_MODIFIED_CONTENT = (
    "# Skill: My Skill\n\n## Purpose\nDoes something.\n\n## Guardrail\nNo foo.\n"
)
SKILL_OTHER_MODIFIED_CONTENT = (
    "# Skill: My Skill\n\n## Purpose\nDoes something.\n\n## Guardrail\nNo bar.\n"
)


@pytest.fixture
def project_with_skill_setup(tmp_path, monkeypatch):
    """Project connected to warehouse with a skill installed in the live agent dir."""
    monkeypatch.chdir(tmp_path)

    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    (warehouse / "contexts").mkdir()
    (warehouse / "knowledge").mkdir()
    (warehouse / "skills").mkdir()
    (warehouse / "docs").mkdir()
    (warehouse / "README.md").write_text("# Warehouse")

    skill_wh = warehouse / "skills" / "my-skill"
    skill_wh.mkdir(parents=True)
    (skill_wh / "SKILL.md").write_text(SKILL_WAREHOUSE_CONTENT)

    beacon_dir = tmp_path / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "config.toml").write_text(
        f'[warehouse]\nlocal_path = "{warehouse}"\n'
    )
    (beacon_dir / "beacon.yaml").write_text(
        "artifacts:\n  knowledge: []\n  skills:\n    - skills/my-skill/SKILL.md\n  contexts: []\n"
    )

    # Artifact snapshot (identical to warehouse — unchanged by sync)
    snapshot_dir = beacon_dir / "artifacts" / "skills" / "my-skill"
    snapshot_dir.mkdir(parents=True)
    (snapshot_dir / "SKILL.md").write_text(SKILL_WAREHOUSE_CONTENT)

    # opencode agent configured
    (tmp_path / "opencode.json").write_text("{}")

    return tmp_path, warehouse


def test_contribute_skill_single_reads_from_live_dir(project_with_skill_setup):
    """abc contribute <skill> copies the live agent version to the warehouse."""
    tmp_path, warehouse = project_with_skill_setup

    # Live dir has a modified version
    live_dir = tmp_path / ".opencode" / "skills" / "my-skill"
    live_dir.mkdir(parents=True)
    (live_dir / "SKILL.md").write_text(SKILL_MODIFIED_CONTENT)

    runner = CliRunner()
    result = runner.invoke(main, ["contribute", "skills/my-skill/SKILL.md"])

    assert result.exit_code == 0, result.output
    dest = warehouse / "skills" / "my-skill" / "SKILL.md"
    assert dest.read_text() == SKILL_MODIFIED_CONTENT


def test_contribute_skill_single_ignores_stale_snapshot(project_with_skill_setup):
    """Regression: contribute reads live dir even when the snapshot still matches warehouse.

    Old behaviour: snapshot == warehouse → reported "Nothing to contribute" and
    silently skipped the file, losing the live edit.
    """
    tmp_path, warehouse = project_with_skill_setup

    # Snapshot is IDENTICAL to warehouse (unchanged)
    # But live dir has a different version
    live_dir = tmp_path / ".opencode" / "skills" / "my-skill"
    live_dir.mkdir(parents=True)
    (live_dir / "SKILL.md").write_text(SKILL_MODIFIED_CONTENT)

    runner = CliRunner()
    result = runner.invoke(main, ["contribute", "skills/my-skill/SKILL.md"])

    assert result.exit_code == 0, result.output
    dest = warehouse / "skills" / "my-skill" / "SKILL.md"
    assert dest.read_text() == SKILL_MODIFIED_CONTENT, (
        "Warehouse should contain the live-dir version, not the stale snapshot"
    )


def test_contribute_skill_single_identical_live_is_noop(project_with_skill_setup):
    """abc contribute <skill> reports nothing to contribute when live matches warehouse."""
    tmp_path, warehouse = project_with_skill_setup

    # Live dir is identical to warehouse
    live_dir = tmp_path / ".opencode" / "skills" / "my-skill"
    live_dir.mkdir(parents=True)
    (live_dir / "SKILL.md").write_text(SKILL_WAREHOUSE_CONTENT)

    runner = CliRunner()
    result = runner.invoke(main, ["contribute", "skills/my-skill/SKILL.md"])

    assert result.exit_code == 0
    assert "nothing to contribute" in result.output.lower()
    # Warehouse unchanged
    assert (
        warehouse / "skills" / "my-skill" / "SKILL.md"
    ).read_text() == SKILL_WAREHOUSE_CONTENT


def test_contribute_skill_all_reads_from_live_dir(project_with_skill_setup):
    """abc contribute --all picks up live-dir skill modifications."""
    tmp_path, warehouse = project_with_skill_setup

    live_dir = tmp_path / ".opencode" / "skills" / "my-skill"
    live_dir.mkdir(parents=True)
    (live_dir / "SKILL.md").write_text(SKILL_MODIFIED_CONTENT)

    runner = CliRunner()
    result = runner.invoke(main, ["contribute", "--all"])

    assert result.exit_code == 0, result.output
    dest = warehouse / "skills" / "my-skill" / "SKILL.md"
    assert dest.read_text() == SKILL_MODIFIED_CONTENT


def test_contribute_skill_multi_agent_identical_versions_no_prompt(
    project_with_skill_setup,
):
    """With two agents having identical modifications, contribute proceeds without prompting."""
    tmp_path, warehouse = project_with_skill_setup

    # Add claudecode agent
    (tmp_path / ".claude").mkdir()

    # Both agents have the same modified version
    oc_dir = tmp_path / ".opencode" / "skills" / "my-skill"
    oc_dir.mkdir(parents=True)
    (oc_dir / "SKILL.md").write_text(SKILL_MODIFIED_CONTENT)

    cc_dir = tmp_path / ".claude" / "skills" / "my-skill"
    cc_dir.mkdir(parents=True)
    (cc_dir / "SKILL.md").write_text(SKILL_MODIFIED_CONTENT)  # same content

    runner = CliRunner()
    result = runner.invoke(main, ["contribute", "skills/my-skill/SKILL.md"])

    assert result.exit_code == 0, result.output
    # No prompt — they agreed
    assert "conflict" not in result.output.lower()
    dest = warehouse / "skills" / "my-skill" / "SKILL.md"
    assert dest.read_text() == SKILL_MODIFIED_CONTENT


def test_contribute_skill_multi_agent_conflict_prompts_user(
    project_with_skill_setup,
):
    """With two agents having different modifications, contribute prompts the user to choose."""
    tmp_path, warehouse = project_with_skill_setup

    # Add claudecode agent
    (tmp_path / ".claude").mkdir()

    oc_dir = tmp_path / ".opencode" / "skills" / "my-skill"
    oc_dir.mkdir(parents=True)
    (oc_dir / "SKILL.md").write_text(SKILL_MODIFIED_CONTENT)

    cc_dir = tmp_path / ".claude" / "skills" / "my-skill"
    cc_dir.mkdir(parents=True)
    (cc_dir / "SKILL.md").write_text(SKILL_OTHER_MODIFIED_CONTENT)

    runner = CliRunner()
    # User picks option 1 (opencode)
    result = runner.invoke(
        main, ["contribute", "skills/my-skill/SKILL.md"], input="1\n"
    )

    assert result.exit_code == 0, result.output
    assert "conflict" in result.output.lower()
    dest = warehouse / "skills" / "my-skill" / "SKILL.md"
    assert dest.read_text() == SKILL_MODIFIED_CONTENT


def test_contribute_skill_multi_agent_conflict_user_picks_second(
    project_with_skill_setup,
):
    """User picks the second agent's version when prompted about a conflict."""
    tmp_path, warehouse = project_with_skill_setup

    (tmp_path / ".claude").mkdir()

    oc_dir = tmp_path / ".opencode" / "skills" / "my-skill"
    oc_dir.mkdir(parents=True)
    (oc_dir / "SKILL.md").write_text(SKILL_MODIFIED_CONTENT)

    cc_dir = tmp_path / ".claude" / "skills" / "my-skill"
    cc_dir.mkdir(parents=True)
    (cc_dir / "SKILL.md").write_text(SKILL_OTHER_MODIFIED_CONTENT)

    runner = CliRunner()
    # User picks option 2 (claudecode)
    result = runner.invoke(
        main, ["contribute", "skills/my-skill/SKILL.md"], input="2\n"
    )

    assert result.exit_code == 0, result.output
    dest = warehouse / "skills" / "my-skill" / "SKILL.md"
    assert dest.read_text() == SKILL_OTHER_MODIFIED_CONTENT


def test_contribute_skill_dry_run_does_not_copy(project_with_skill_setup):
    """--dry-run does not copy the live skill to the warehouse."""
    tmp_path, warehouse = project_with_skill_setup

    live_dir = tmp_path / ".opencode" / "skills" / "my-skill"
    live_dir.mkdir(parents=True)
    (live_dir / "SKILL.md").write_text(SKILL_MODIFIED_CONTENT)

    runner = CliRunner()
    result = runner.invoke(
        main, ["contribute", "skills/my-skill/SKILL.md", "--dry-run"]
    )

    assert result.exit_code == 0, result.output
    assert "would" in result.output.lower() or "dry" in result.output.lower()
    # Warehouse unchanged
    dest = warehouse / "skills" / "my-skill" / "SKILL.md"
    assert dest.read_text() == SKILL_WAREHOUSE_CONTENT
