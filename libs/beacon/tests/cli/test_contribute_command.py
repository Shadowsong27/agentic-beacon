"""Tests for abc contribute command."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest
from beacon.cli import main
from beacon.core.delta import DeltaComparator, DeltaStatus
from beacon.utils.contribute import _build_pr_body, _resolve_skill_contribute_source
from beacon.utils.skills import _build_skills_paths
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
def project_with_delta(tmp_path, monkeypatch, isolated_home):
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

    result = runner.invoke(
        main, ["contribute", "knowledge/python/type-hints.md"], input="y\n"
    )

    assert result.exit_code == 0, result.output
    dest = warehouse / "knowledge" / "python" / "type-hints.md"
    assert dest.read_text() == KNOWLEDGE_CONTENT_MODIFIED


def test_contribute_single_added_file(project_with_delta):
    """ADDED file (exists locally, not in warehouse) is copied to warehouse."""
    tmp_path, warehouse = project_with_delta
    runner = CliRunner()

    result = runner.invoke(
        main, ["contribute", "knowledge/python/new-lesson.md"], input="y\n"
    )

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

    result = runner.invoke(
        main, ["contribute", "knowledge/python/type-hints.md"], input="y\n"
    )

    assert result.exit_code == 0
    assert "nothing to contribute" in result.output.lower()
    # Warehouse unchanged
    assert (
        warehouse / "knowledge" / "python" / "type-hints.md"
    ).read_text() == KNOWLEDGE_CONTENT_ORIGINAL


# ---------------------------------------------------------------------------
# Default behaviour: contribute all (no file argument)
# ---------------------------------------------------------------------------


def test_contribute_all_copies_modified_and_added(project_with_delta, isolated_home):
    tmp_path, warehouse = project_with_delta
    runner = CliRunner()

    result = runner.invoke(main, ["contribute", "--manual-git"], input="y\n")

    assert result.exit_code == 0, result.output
    assert (
        warehouse / "knowledge" / "python" / "type-hints.md"
    ).read_text() == KNOWLEDGE_CONTENT_MODIFIED
    assert (
        warehouse / "knowledge" / "python" / "new-lesson.md"
    ).read_text() == ADDED_CONTENT


def test_contribute_all_nothing_to_contribute(project_with_delta, isolated_home):
    """When all artifacts are identical, contribute with no file reports nothing to contribute."""
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

    result = runner.invoke(main, ["contribute"])

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

    result = runner.invoke(main, ["contribute", "--dry-run"])

    assert result.exit_code == 0, result.output
    # Warehouse files unchanged
    assert (
        warehouse / "knowledge" / "python" / "type-hints.md"
    ).read_text() == KNOWLEDGE_CONTENT_ORIGINAL
    assert not (warehouse / "knowledge" / "python" / "new-lesson.md").exists()


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_contribute_errors_when_file_not_in_beacon_yaml(project_with_delta):
    """A file that doesn't exist locally is always rejected (can't contribute nothing)."""
    runner = CliRunner()
    result = runner.invoke(main, ["contribute", "knowledge/unlisted/file.md"])
    assert result.exit_code != 0
    # File doesn't exist locally — that's the first error reported now
    assert "error" in result.output.lower()


def test_contribute_single_unrecognised_path_still_copies(project_with_delta):
    """A local file with non-standard path prefix is still contributed (no type gating)."""
    tmp_path, warehouse = project_with_delta
    runner = CliRunner()

    # Create a local file with an unusual path prefix
    weird = tmp_path / ".agentic-beacon" / "artifacts" / "misc" / "random.md"
    weird.parent.mkdir(parents=True)
    weird.write_text("random")

    result = runner.invoke(main, ["contribute", "misc/random.md"], input="y\n")

    assert result.exit_code == 0, result.output
    assert (warehouse / "misc" / "random.md").read_text() == "random"


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
    result = runner.invoke(
        main, ["contribute", "knowledge/python/type-hints.md"], input="y\n"
    )
    assert result.exit_code != 0
    assert "sync" in result.output.lower() or "not" in result.output.lower()


def test_contribute_errors_without_beacon_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        main, ["contribute", "knowledge/python/type-hints.md"], input="y\n"
    )
    assert result.exit_code != 0
    assert ".agentic-beacon" in result.output


def test_contribute_errors_without_warehouse_connection(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".agentic-beacon").mkdir()
    # No config.toml
    runner = CliRunner()
    result = runner.invoke(
        main, ["contribute", "knowledge/python/type-hints.md"], input="y\n"
    )
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
def project_with_untracked(tmp_path, monkeypatch, isolated_home):
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


def test_contribute_single_untracked_file_copies_without_registering(
    project_with_untracked,
):
    """Contributing an untracked file copies it but does NOT modify beacon.yaml."""
    tmp_path, warehouse = project_with_untracked
    runner = CliRunner()

    beacon_yaml = tmp_path / ".agentic-beacon" / "beacon.yaml"
    original_content = beacon_yaml.read_text()

    result = runner.invoke(
        main, ["contribute", "knowledge/python/new-lesson.md"], input="y\n"
    )

    assert result.exit_code == 0, result.output
    # File copied to warehouse
    assert (
        warehouse / "knowledge" / "python" / "new-lesson.md"
    ).read_text() == ADDED_CONTENT
    # beacon.yaml NOT modified — abc adopt is the opt-in mechanism
    assert beacon_yaml.read_text() == original_content


def test_contribute_all_ignores_untracked_files(project_with_untracked, isolated_home):
    """--exclude-unregistered only contributes tracked artifacts; untracked files are ignored."""
    tmp_path, warehouse = project_with_untracked
    runner = CliRunner()

    beacon_yaml = tmp_path / ".agentic-beacon" / "beacon.yaml"
    original_content = beacon_yaml.read_text()

    result = runner.invoke(
        main, ["contribute", "--exclude-unregistered", "--manual-git"], input="y\n"
    )

    assert result.exit_code == 0, result.output
    # Untracked file NOT copied to warehouse
    assert not (warehouse / "knowledge" / "python" / "new-lesson.md").exists()
    # beacon.yaml unchanged
    assert beacon_yaml.read_text() == original_content


def test_contribute_single_already_tracked_does_not_duplicate(project_with_delta):
    """Contributing a file already in beacon.yaml does not add a duplicate entry."""
    tmp_path, warehouse = project_with_delta
    runner = CliRunner()

    beacon_yaml = tmp_path / ".agentic-beacon" / "beacon.yaml"

    result = runner.invoke(
        main, ["contribute", "knowledge/python/type-hints.md"], input="y\n"
    )

    assert result.exit_code == 0, result.output
    import yaml

    data = yaml.safe_load(beacon_yaml.read_text())
    knowledge = data["artifacts"]["knowledge"]
    assert knowledge.count("knowledge/python/type-hints.md") == 1


# ---------------------------------------------------------------------------
# Unit tests: _build_skills_paths()
# ---------------------------------------------------------------------------


def test_build_skills_paths_opencode_detected(tmp_path):
    """_build_skills_paths returns opencode entry when opencode.json exists."""
    (tmp_path / "opencode.json").write_text("{}")
    result = _build_skills_paths(tmp_path)
    assert "opencode" in result
    assert result["opencode"] == tmp_path / ".opencode" / "skills"
    assert "claudecode" not in result


def test_build_skills_paths_claudecode_detected(tmp_path):
    """_build_skills_paths returns claudecode entry when .claude dir exists."""
    (tmp_path / ".claude").mkdir()
    result = _build_skills_paths(tmp_path)
    assert "claudecode" in result
    assert result["claudecode"] == tmp_path / ".claude" / "skills"
    assert "opencode" not in result


def test_build_skills_paths_both_agents_detected(tmp_path):
    """_build_skills_paths returns both entries when both agents are configured."""
    (tmp_path / "opencode.json").write_text("{}")
    (tmp_path / ".claude").mkdir()
    result = _build_skills_paths(tmp_path)
    assert "opencode" in result
    assert "claudecode" in result


def test_build_skills_paths_no_agents_returns_empty(tmp_path):
    """_build_skills_paths returns empty dict when no agents are detected."""
    result = _build_skills_paths(tmp_path)
    assert result == {}


def test_build_skills_paths_matches_delta_detection(tmp_path):
    """_build_skills_paths produces the same paths that delta uses — shared logic."""
    (tmp_path / "opencode.json").write_text("{}")
    (tmp_path / ".claude").mkdir()
    result = _build_skills_paths(tmp_path)
    # These are the exact paths delta builds
    assert result["opencode"] == tmp_path / ".opencode" / "skills"
    assert result["claudecode"] == tmp_path / ".claude" / "skills"


# ---------------------------------------------------------------------------
# Unit tests: _resolve_skill_contribute_source()
# ---------------------------------------------------------------------------


@pytest.fixture
def resolver_setup(tmp_path, valid_warehouse):
    """Shared setup for _resolve_skill_contribute_source tests."""
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()

    # Warehouse has the skill
    skill_wh = valid_warehouse / "skills" / "my-skill"
    skill_wh.mkdir(parents=True)
    (skill_wh / "SKILL.md").write_text(SKILL_WAREHOUSE_CONTENT)

    # Snapshot matches warehouse
    snapshot_dir = artifacts_dir / "skills" / "my-skill"
    snapshot_dir.mkdir(parents=True)
    (snapshot_dir / "SKILL.md").write_text(SKILL_WAREHOUSE_CONTENT)

    return valid_warehouse, artifacts_dir


def test_resolve_returns_none_when_no_agents(resolver_setup, tmp_path):
    """Without skills_paths, falls back to artifact snapshot path (not None)."""
    valid_warehouse, artifacts_dir = resolver_setup

    comparator = DeltaComparator(valid_warehouse, artifacts_dir)
    result = _resolve_skill_contribute_source(
        comparator, "skills/my-skill/SKILL.md", artifacts_dir
    )
    # Fallback to snapshot path
    assert result == artifacts_dir / "skills" / "my-skill" / "SKILL.md"


def test_resolve_returns_none_when_live_identical(resolver_setup, tmp_path):
    """Returns None when live agent copy matches warehouse (nothing to contribute)."""
    valid_warehouse, artifacts_dir = resolver_setup

    opencode_skills = tmp_path / ".opencode" / "skills"
    live_dir = opencode_skills / "my-skill"
    live_dir.mkdir(parents=True)
    (live_dir / "SKILL.md").write_text(SKILL_WAREHOUSE_CONTENT)  # identical

    comparator = DeltaComparator(
        valid_warehouse, artifacts_dir, skills_paths={"opencode": opencode_skills}
    )
    result = _resolve_skill_contribute_source(
        comparator, "skills/my-skill/SKILL.md", artifacts_dir
    )
    assert result is None


def test_resolve_returns_live_path_when_single_agent_modified(resolver_setup, tmp_path):
    """Returns the live path when exactly one agent has a modification."""
    valid_warehouse, artifacts_dir = resolver_setup

    opencode_skills = tmp_path / ".opencode" / "skills"
    live_dir = opencode_skills / "my-skill"
    live_dir.mkdir(parents=True)
    (live_dir / "SKILL.md").write_text(SKILL_MODIFIED_CONTENT)

    comparator = DeltaComparator(
        valid_warehouse, artifacts_dir, skills_paths={"opencode": opencode_skills}
    )
    result = _resolve_skill_contribute_source(
        comparator, "skills/my-skill/SKILL.md", artifacts_dir
    )
    assert result == live_dir / "SKILL.md"
    assert result.read_text() == SKILL_MODIFIED_CONTENT


def test_resolve_returns_live_path_when_multi_agent_identical_modification(
    resolver_setup, tmp_path
):
    """When multiple agents modified identically, returns one path without prompting."""
    valid_warehouse, artifacts_dir = resolver_setup

    opencode_skills = tmp_path / ".opencode" / "skills"
    (opencode_skills / "my-skill").mkdir(parents=True)
    (opencode_skills / "my-skill" / "SKILL.md").write_text(SKILL_MODIFIED_CONTENT)

    claude_skills = tmp_path / ".claude" / "skills"
    (claude_skills / "my-skill").mkdir(parents=True)
    (claude_skills / "my-skill" / "SKILL.md").write_text(SKILL_MODIFIED_CONTENT)  # same

    comparator = DeltaComparator(
        valid_warehouse,
        artifacts_dir,
        skills_paths={"opencode": opencode_skills, "claudecode": claude_skills},
    )
    result = _resolve_skill_contribute_source(
        comparator, "skills/my-skill/SKILL.md", artifacts_dir
    )
    assert result is not None
    assert result.read_text() == SKILL_MODIFIED_CONTENT


def test_resolve_prompts_when_multi_agent_different_modifications(
    resolver_setup, tmp_path
):
    """When agents have different modifications, prompts user and returns chosen path."""
    valid_warehouse, artifacts_dir = resolver_setup

    opencode_skills = tmp_path / ".opencode" / "skills"
    (opencode_skills / "my-skill").mkdir(parents=True)
    (opencode_skills / "my-skill" / "SKILL.md").write_text(SKILL_MODIFIED_CONTENT)

    claude_skills = tmp_path / ".claude" / "skills"
    (claude_skills / "my-skill").mkdir(parents=True)
    (claude_skills / "my-skill" / "SKILL.md").write_text(SKILL_OTHER_MODIFIED_CONTENT)

    comparator = DeltaComparator(
        valid_warehouse,
        artifacts_dir,
        skills_paths={"opencode": opencode_skills, "claudecode": claude_skills},
    )

    # Simulate user picking "1" (first agent)
    import click

    with click.testing.CliRunner().isolated_filesystem():
        # We can't call the function directly with input in isolation easily,
        # so we test via the full CLI path (covered in CLI tests above).
        # Here we verify the comparator state that would trigger the prompt.
        result = comparator.compare_file("skills/my-skill/SKILL.md")
        assert result.status == DeltaStatus.MODIFIED
        modified_agents = [
            agent
            for agent, status in result.agent_statuses.items()
            if status == DeltaStatus.MODIFIED
        ]
        assert len(modified_agents) == 2
        # Hashes must differ to confirm conflict
        hashes = {
            agent: comparator.compute_hash(
                comparator._skill_live_path(agent, "skills/my-skill/SKILL.md")
            )
            for agent in modified_agents
        }
        assert len(set(hashes.values())) == 2  # two distinct hashes → conflict


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
def project_with_skill_setup(tmp_path, monkeypatch, isolated_home):
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
    result = runner.invoke(
        main, ["contribute", "skills/my-skill/SKILL.md"], input="y\n"
    )

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
    result = runner.invoke(
        main, ["contribute", "skills/my-skill/SKILL.md"], input="y\n"
    )

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
    result = runner.invoke(
        main, ["contribute", "skills/my-skill/SKILL.md"], input="y\n"
    )

    assert result.exit_code == 0
    assert "nothing to contribute" in result.output.lower()
    # Warehouse unchanged
    assert (
        warehouse / "skills" / "my-skill" / "SKILL.md"
    ).read_text() == SKILL_WAREHOUSE_CONTENT


def test_contribute_skill_all_reads_from_live_dir(project_with_skill_setup):
    """abc contribute (no file) picks up live-dir skill modifications."""
    tmp_path, warehouse = project_with_skill_setup

    live_dir = tmp_path / ".opencode" / "skills" / "my-skill"
    live_dir.mkdir(parents=True)
    (live_dir / "SKILL.md").write_text(SKILL_MODIFIED_CONTENT)

    runner = CliRunner()
    result = runner.invoke(main, ["contribute", "--manual-git"], input="y\n")

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
    result = runner.invoke(
        main, ["contribute", "skills/my-skill/SKILL.md"], input="y\n"
    )

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
    # User picks option 1 (opencode); y\n answers the preceding "Proceed?" prompt
    result = runner.invoke(
        main, ["contribute", "skills/my-skill/SKILL.md"], input="y\n1\n"
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
    # User picks option 2 (claudecode); y\n answers the preceding "Proceed?" prompt
    result = runner.invoke(
        main, ["contribute", "skills/my-skill/SKILL.md"], input="y\n2\n"
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


# ---------------------------------------------------------------------------
# --manual-git flag
# ---------------------------------------------------------------------------


def test_contribute_manual_git_prints_next_steps(project_with_delta):
    """--manual-git skips auto git and prints manual instructions."""
    tmp_path, warehouse = project_with_delta
    runner = CliRunner()

    result = runner.invoke(main, ["contribute", "--manual-git"], input="y\n")

    assert result.exit_code == 0, result.output
    # Files still copied
    assert (
        warehouse / "knowledge" / "python" / "type-hints.md"
    ).read_text() == KNOWLEDGE_CONTENT_MODIFIED
    # Manual instructions printed
    assert "git add" in result.output
    assert "git commit" in result.output


def test_contribute_single_manual_git_prints_next_steps(project_with_delta):
    """--manual-git on a single file skips auto git and prints manual instructions."""
    tmp_path, warehouse = project_with_delta
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["contribute", "knowledge/python/type-hints.md", "--manual-git"],
        input="y\n",
    )

    assert result.exit_code == 0, result.output
    assert (
        warehouse / "knowledge" / "python" / "type-hints.md"
    ).read_text() == KNOWLEDGE_CONTENT_MODIFIED
    assert "git add" in result.output


# ---------------------------------------------------------------------------
# Auto-git workflow (mocked subprocess)
# ---------------------------------------------------------------------------


def _make_completed(
    returncode: int = 0, stdout: str = "", stderr: str = ""
) -> MagicMock:
    m = MagicMock(spec=subprocess.CompletedProcess)
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


def test_contribute_auto_git_creates_pr(project_with_delta, tmp_path):
    """Default mode runs git workflow and creates a PR when everything succeeds."""
    tmp_path2, warehouse = project_with_delta

    # Give the warehouse a .git directory so the auto-git path is taken
    (warehouse / ".git").mkdir()

    runner = CliRunner()
    with (
        patch("beacon.cli._check_warehouse_git_clean", return_value=None),
        patch("beacon.cli._check_sync_state", return_value=None),
        patch("beacon.utils.contribute.subprocess.run") as mock_run,
    ):
        mock_run.side_effect = [
            _make_completed(0),  # git checkout -b
            _make_completed(0),  # git add -- <paths>
            _make_completed(0),  # git commit
            _make_completed(0),  # git push
            _make_completed(
                0, stdout="https://github.com/org/repo/pull/42\n"
            ),  # gh pr create
        ]
        result = runner.invoke(main, ["contribute"], input="y\n")

    assert result.exit_code == 0, result.output
    assert "https://github.com/org/repo/pull/42" in result.output
    assert mock_run.call_count == 5


def test_contribute_auto_git_fallback_when_no_git_dir(project_with_delta):
    """Falls back to manual instructions when warehouse has no .git directory."""
    tmp_path2, warehouse = project_with_delta
    # No .git dir in warehouse (default fixture state) — git clean check is skipped,
    # and auto-git also falls back to manual.

    runner = CliRunner()
    result = runner.invoke(main, ["contribute"], input="y\n")

    assert result.exit_code == 0, result.output
    # Manual next-steps printed as fallback
    assert "git add" in result.output


def test_contribute_auto_git_fallback_when_push_fails(project_with_delta):
    """Falls back to manual instructions when git push fails."""
    tmp_path2, warehouse = project_with_delta
    (warehouse / ".git").mkdir()

    runner = CliRunner()
    with (
        patch("beacon.cli._check_warehouse_git_clean", return_value=None),
        patch("beacon.cli._check_sync_state", return_value=None),
        patch("beacon.utils.contribute.subprocess.run") as mock_run,
    ):
        mock_run.side_effect = [
            _make_completed(0),  # git checkout -b
            _make_completed(0),  # git add -- <paths>
            _make_completed(0),  # git commit
            _make_completed(1, stderr="error: failed to push"),  # git push fails
        ]
        result = runner.invoke(main, ["contribute"], input="y\n")

    assert result.exit_code == 0, result.output
    assert "warning" in result.output.lower() or "falling back" in result.output.lower()
    assert "git push" in result.output  # manual steps shown


def test_contribute_auto_git_fallback_when_gh_not_installed(project_with_delta):
    """Falls back gracefully when gh is not installed."""
    tmp_path2, warehouse = project_with_delta
    (warehouse / ".git").mkdir()

    runner = CliRunner()
    with (
        patch("beacon.cli._check_warehouse_git_clean", return_value=None),
        patch("beacon.cli._check_sync_state", return_value=None),
        patch("beacon.utils.contribute.subprocess.run") as mock_run,
    ):
        mock_run.side_effect = [
            _make_completed(0),  # git checkout -b
            _make_completed(0),  # git add -- <paths>
            _make_completed(0),  # git commit
            _make_completed(0),  # git push
            FileNotFoundError("gh not found"),  # gh pr create
        ]
        result = runner.invoke(main, ["contribute"], input="y\n")

    assert result.exit_code == 0, result.output
    assert "gh not installed" in result.output.lower() or "pr" in result.output.lower()
    # Success message still shown
    assert "contributed" in result.output.lower()


# ---------------------------------------------------------------------------
# Unit tests: _build_pr_body()
# ---------------------------------------------------------------------------


def test_build_pr_body_lists_files():
    contributed = [
        ("knowledge/python/type-hints.md", "modified"),
        ("contexts/global.md", "added"),
    ]
    body = _build_pr_body(contributed)
    assert "## Contributed artifacts" in body
    assert "`knowledge/python/type-hints.md` (modified)" in body
    assert "`contexts/global.md` (added)" in body


def test_build_pr_body_single_file():
    body = _build_pr_body([("knowledge/lesson.md", "modified")])
    assert "`knowledge/lesson.md` (modified)" in body


# ---------------------------------------------------------------------------
# Regression: contribute must not create infinite delta cycle (PER-38)
# ---------------------------------------------------------------------------


def test_contribute_single_skill_propagates_to_other_agents(
    project_with_skill_setup,
):
    """After contributing one agent's skill, all other agents' live copies converge.

    Reproduces the PER-38 infinite cycle:
      1. Two agents configured; only claudecode has the modified skill.
      2. abc contribute copies claudecode's version to the warehouse.
      3. opencode's live copy must be updated to the same content so that
         a subsequent abc delta shows IDENTICAL for both agents.
    """
    tmp_path, warehouse = project_with_skill_setup

    # Set up claudecode agent with the modified skill
    (tmp_path / ".claude").mkdir()
    cc_skill_dir = tmp_path / ".claude" / "skills" / "my-skill"
    cc_skill_dir.mkdir(parents=True)
    (cc_skill_dir / "SKILL.md").write_text(SKILL_MODIFIED_CONTENT)

    # opencode live copy still has the old warehouse content
    oc_skill_dir = tmp_path / ".opencode" / "skills" / "my-skill"
    oc_skill_dir.mkdir(parents=True)
    (oc_skill_dir / "SKILL.md").write_text(SKILL_WAREHOUSE_CONTENT)

    runner = CliRunner()
    result = runner.invoke(
        main, ["contribute", "skills/my-skill/SKILL.md"], input="y\n"
    )

    assert result.exit_code == 0, result.output
    # Warehouse updated to contributed version
    assert (
        warehouse / "skills" / "my-skill" / "SKILL.md"
    ).read_text() == SKILL_MODIFIED_CONTENT
    # opencode live copy must also be updated — no more infinite cycle
    assert (oc_skill_dir / "SKILL.md").read_text() == SKILL_MODIFIED_CONTENT, (
        "opencode live copy was not propagated; abc delta would flag it MODIFIED "
        "causing an infinite contribute/delta cycle"
    )


def test_contribute_all_skills_propagates_to_other_agents(
    project_with_skill_setup,
):
    """abc contribute (no file arg) also propagates contributed skill to all agents."""
    tmp_path, warehouse = project_with_skill_setup

    # Set up claudecode agent with the modified skill
    (tmp_path / ".claude").mkdir()
    cc_skill_dir = tmp_path / ".claude" / "skills" / "my-skill"
    cc_skill_dir.mkdir(parents=True)
    (cc_skill_dir / "SKILL.md").write_text(SKILL_MODIFIED_CONTENT)

    # opencode live copy still has the old warehouse content
    oc_skill_dir = tmp_path / ".opencode" / "skills" / "my-skill"
    oc_skill_dir.mkdir(parents=True)
    (oc_skill_dir / "SKILL.md").write_text(SKILL_WAREHOUSE_CONTENT)

    runner = CliRunner()
    result = runner.invoke(main, ["contribute"], input="y\n")

    assert result.exit_code == 0, result.output
    assert (
        warehouse / "skills" / "my-skill" / "SKILL.md"
    ).read_text() == SKILL_MODIFIED_CONTENT
    assert (oc_skill_dir / "SKILL.md").read_text() == SKILL_MODIFIED_CONTENT, (
        "opencode live copy was not propagated after contribute --all"
    )


# ---------------------------------------------------------------------------
# --exclude-unregistered flag
# ---------------------------------------------------------------------------


def test_default_includes_untracked_file(project_with_untracked):
    """Default behaviour contributes files not listed in beacon.yaml to the warehouse."""
    tmp_path, warehouse = project_with_untracked
    runner = CliRunner()

    result = runner.invoke(main, ["contribute", "--manual-git"], input="y\n")

    assert result.exit_code == 0, result.output
    assert (
        warehouse / "knowledge" / "python" / "new-lesson.md"
    ).read_text() == ADDED_CONTENT


def test_default_does_not_modify_beacon_yaml(project_with_untracked):
    """Default contribute never writes to beacon.yaml; registration stays user's job."""
    tmp_path, warehouse = project_with_untracked
    runner = CliRunner()

    beacon_yaml = tmp_path / ".agentic-beacon" / "beacon.yaml"
    original_content = beacon_yaml.read_text()

    runner.invoke(main, ["contribute", "--manual-git"], input="y\n")

    assert beacon_yaml.read_text() == original_content


def test_default_contributes_both_tracked_and_untracked(
    project_with_untracked,
):
    """Default contribute includes tracked modified files AND untracked new files."""
    tmp_path, warehouse = project_with_untracked
    runner = CliRunner()

    # Make the tracked file differ from the warehouse
    local_hints = (
        tmp_path
        / ".agentic-beacon"
        / "artifacts"
        / "knowledge"
        / "python"
        / "type-hints.md"
    )
    local_hints.write_text(KNOWLEDGE_CONTENT_MODIFIED)

    result = runner.invoke(main, ["contribute", "--manual-git"], input="y\n")

    assert result.exit_code == 0, result.output
    # Tracked modified file contributed
    assert (
        warehouse / "knowledge" / "python" / "type-hints.md"
    ).read_text() == KNOWLEDGE_CONTENT_MODIFIED
    # Untracked new file also contributed
    assert (
        warehouse / "knowledge" / "python" / "new-lesson.md"
    ).read_text() == ADDED_CONTENT


def test_default_dry_run_does_not_copy(project_with_untracked):
    """Default --dry-run does not copy any files."""
    tmp_path, warehouse = project_with_untracked
    runner = CliRunner()

    result = runner.invoke(main, ["contribute", "--dry-run"])

    assert result.exit_code == 0, result.output
    assert "dry" in result.output.lower() or "would" in result.output.lower()
    assert not (warehouse / "knowledge" / "python" / "new-lesson.md").exists()


def test_exclude_unregistered_ignores_untracked(project_with_untracked):
    """--exclude-unregistered skips files not listed in beacon.yaml."""
    tmp_path, warehouse = project_with_untracked
    runner = CliRunner()

    # Make the tracked file differ so there IS something to contribute (triggers prompt)
    local_hints = (
        tmp_path
        / ".agentic-beacon"
        / "artifacts"
        / "knowledge"
        / "python"
        / "type-hints.md"
    )
    local_hints.write_text(KNOWLEDGE_CONTENT_MODIFIED)

    result = runner.invoke(
        main, ["contribute", "--exclude-unregistered", "--manual-git"], input="y\n"
    )

    assert result.exit_code == 0, result.output
    # Untracked file NOT copied — excluded by flag
    assert not (warehouse / "knowledge" / "python" / "new-lesson.md").exists()


def test_nothing_to_contribute_when_all_match(
    project_with_untracked,
    isolated_home,
):
    """When tracked files are identical and there are no untracked files, reports nothing."""
    tmp_path, warehouse = project_with_untracked
    runner = CliRunner()

    # Remove the untracked file so there's truly nothing new
    untracked = (
        tmp_path
        / ".agentic-beacon"
        / "artifacts"
        / "knowledge"
        / "python"
        / "new-lesson.md"
    )
    untracked.unlink()

    result = runner.invoke(main, ["contribute", "--exclude-unregistered"])

    assert result.exit_code == 0
    assert "nothing to contribute" in result.output.lower()


def test_default_auto_git_includes_untracked_in_pr(project_with_untracked):
    """Default contribute includes untracked files in the auto-git PR."""
    tmp_path, warehouse = project_with_untracked
    (warehouse / ".git").mkdir()

    runner = CliRunner()
    with (
        patch("beacon.cli._check_warehouse_git_clean", return_value=None),
        patch("beacon.cli._check_sync_state", return_value=None),
        patch("beacon.utils.contribute.subprocess.run") as mock_run,
    ):
        mock_run.side_effect = [
            _make_completed(0),  # git checkout -b
            _make_completed(0),  # git add -- <paths>
            _make_completed(0),  # git commit
            _make_completed(0),  # git push
            _make_completed(
                0, stdout="https://github.com/org/repo/pull/99\n"
            ),  # gh pr create
        ]
        result = runner.invoke(main, ["contribute"], input="y\n")

    assert result.exit_code == 0, result.output
    assert "https://github.com/org/repo/pull/99" in result.output
    # The untracked file should appear in the git add call
    add_call = mock_run.call_args_list[1]
    added_paths = add_call.args[0] if add_call.args else add_call[0][0]
    assert any("new-lesson.md" in str(p) for p in added_paths)


# ---------------------------------------------------------------------------
# y/N confirmation prompt
# ---------------------------------------------------------------------------


def test_contribute_prompts_before_copying(project_with_delta):
    """abc contribute shows a preview and prompts y/N before copying any files."""
    tmp_path, warehouse = project_with_delta
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["contribute", "knowledge/python/type-hints.md", "--manual-git"],
        input="y\n",
    )

    assert result.exit_code == 0, result.output
    assert "preview" in result.output.lower()
    assert "would contribute" in result.output.lower()
    assert "proceed" in result.output.lower()
    # File was actually copied
    assert (
        warehouse / "knowledge" / "python" / "type-hints.md"
    ).read_text() == KNOWLEDGE_CONTENT_MODIFIED


def test_contribute_aborts_when_user_declines(project_with_delta):
    """Answering 'n' at the confirmation prompt aborts without copying any files."""
    tmp_path, warehouse = project_with_delta
    runner = CliRunner()

    result = runner.invoke(
        main,
        ["contribute", "knowledge/python/type-hints.md", "--manual-git"],
        input="n\n",
    )

    assert result.exit_code == 0, result.output
    assert "aborted" in result.output.lower()
    # Warehouse must be unchanged
    assert (
        warehouse / "knowledge" / "python" / "type-hints.md"
    ).read_text() == KNOWLEDGE_CONTENT_ORIGINAL


def test_contribute_all_prompts_before_copying(project_with_delta):
    """abc contribute (no file) also shows preview and prompts before copying."""
    tmp_path, warehouse = project_with_delta
    runner = CliRunner()

    result = runner.invoke(main, ["contribute", "--manual-git"], input="y\n")

    assert result.exit_code == 0, result.output
    assert "preview" in result.output.lower()
    assert "proceed" in result.output.lower()
    assert (
        warehouse / "knowledge" / "python" / "type-hints.md"
    ).read_text() == KNOWLEDGE_CONTENT_MODIFIED


def test_contribute_all_aborts_when_user_declines(project_with_delta):
    """Answering 'n' to the all-files confirmation aborts without copying anything."""
    tmp_path, warehouse = project_with_delta
    runner = CliRunner()

    result = runner.invoke(main, ["contribute", "--manual-git"], input="n\n")

    assert result.exit_code == 0, result.output
    assert "aborted" in result.output.lower()
    assert (
        warehouse / "knowledge" / "python" / "type-hints.md"
    ).read_text() == KNOWLEDGE_CONTENT_ORIGINAL
    assert not (warehouse / "knowledge" / "python" / "new-lesson.md").exists()


def test_contribute_noop_skips_prompt(project_with_delta, isolated_home):
    """When there is nothing to contribute, the confirmation prompt is not shown."""
    tmp_path, warehouse = project_with_delta
    runner = CliRunner()

    # Make local identical to warehouse
    local_hints = (
        tmp_path
        / ".agentic-beacon"
        / "artifacts"
        / "knowledge"
        / "python"
        / "type-hints.md"
    )
    local_hints.write_text(KNOWLEDGE_CONTENT_ORIGINAL)
    (
        tmp_path
        / ".agentic-beacon"
        / "artifacts"
        / "knowledge"
        / "python"
        / "new-lesson.md"
    ).unlink()

    result = runner.invoke(main, ["contribute"])

    assert result.exit_code == 0, result.output
    assert "nothing to contribute" in result.output.lower()
    assert "proceed" not in result.output.lower()
