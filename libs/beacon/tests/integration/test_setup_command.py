"""Tests for abc setup command.

Following TDD workflow for tasks 4.1-4.6:
- Task 4.1: Setup command for project initialization
- Task 4.2: Beacon.yaml template generation
- Task 4.3: Three workflow support (agent-assisted, manual, skip)
- Task 4.4: Project-setup skill installation
- Task 4.5: Interactive workflow selection
- Task 4.6: Non-interactive flags
"""

import yaml
from beacon.cli.main import main
from click.testing import CliRunner

# ========== Task 4.1: Setup Command Implementation ==========


def test_setup_with_warehouse_connected_shows_prompt(
    valid_warehouse, temp_dir, monkeypatch
):
    """TC1: Setup with warehouse connected → Interactive prompt shown."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    # Connect warehouse first
    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])

    # Run setup with skip option
    result = runner.invoke(main, ["setup"], input="3\n")

    assert result.exit_code == 0
    # Should show workflow options
    assert "workflow" in result.output.lower() or "setup" in result.output.lower()


def test_setup_without_warehouse_connected_shows_error(temp_dir, monkeypatch):
    """TC2: Setup without warehouse connected → Error message."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()

    # Create .agentic-beacon but no config.toml (no warehouse connected)
    beacon_dir = project_dir / ".agentic-beacon"
    beacon_dir.mkdir()

    monkeypatch.chdir(project_dir)

    result = runner.invoke(main, ["setup"])

    assert result.exit_code == 1
    assert "warehouse" in result.output.lower()
    assert "connect" in result.output.lower()


def test_setup_when_beacon_yaml_exists(valid_warehouse, temp_dir, monkeypatch):
    """TC3: Setup when beacon.yaml already exists → Prompt or skip."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    # Connect warehouse
    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])

    # Create existing beacon.yaml
    beacon_dir = project_dir / ".agentic-beacon"
    beacon_yaml = beacon_dir / "beacon.yaml"
    beacon_yaml.write_text("artifacts:\n  knowledge: []\n")

    # Try setup again
    result = runner.invoke(main, ["setup", "--manual"])

    # Should either skip or ask to overwrite
    assert result.exit_code == 0 or "already exists" in result.output.lower()


def test_setup_with_manual_flag(valid_warehouse, temp_dir, monkeypatch):
    """TC4: Setup with --manual flag → Creates template directly."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    # Connect warehouse
    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])

    result = runner.invoke(main, ["setup", "--manual"])

    assert result.exit_code == 0

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    assert beacon_yaml.exists()


def test_setup_without_agentic_beacon_dir_shows_error(temp_dir, monkeypatch):
    """TC7: Setup without .agentic-beacon → Error with actionable message."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    result = runner.invoke(main, ["setup"])

    assert result.exit_code == 1
    # Should mention warehouse connection or setup
    assert "warehouse" in result.output.lower() or "connect" in result.output.lower()


# ========== Task 4.2: Beacon.yaml Template Generation ==========


def test_template_creates_file_with_correct_structure(
    valid_warehouse, temp_dir, monkeypatch
):
    """TC1: Template generation creates file with artifacts structure."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    result = runner.invoke(main, ["setup", "--manual"])

    assert result.exit_code == 0

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    assert beacon_yaml.exists()

    content = yaml.safe_load(beacon_yaml.read_text())
    assert "artifacts" in content


def test_template_is_valid_yaml(valid_warehouse, temp_dir, monkeypatch):
    """TC2: Template is valid YAML that parses without errors."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    runner.invoke(main, ["setup", "--manual"])

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"

    # Should parse without exception
    content = yaml.safe_load(beacon_yaml.read_text())
    assert isinstance(content, dict)


def test_template_has_all_three_artifact_types(valid_warehouse, temp_dir, monkeypatch):
    """TC3: Template has knowledge, skills, contexts."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    runner.invoke(main, ["setup", "--manual"])

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    content = yaml.safe_load(beacon_yaml.read_text())

    assert "knowledge" in content["artifacts"]
    assert "skills" in content["artifacts"]
    assert "contexts" in content["artifacts"]


def test_template_has_empty_lists(valid_warehouse, temp_dir, monkeypatch):
    """TC4: All artifact types are empty lists."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    runner.invoke(main, ["setup", "--manual"])

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    content = yaml.safe_load(beacon_yaml.read_text())

    assert content["artifacts"]["knowledge"] == []
    assert content["artifacts"]["skills"] == []
    assert content["artifacts"]["contexts"] == []


def test_template_includes_commented_examples(valid_warehouse, temp_dir, monkeypatch):
    """TC5: Template includes helpful comment examples."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    runner.invoke(main, ["setup", "--manual"])

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    content_text = beacon_yaml.read_text()

    # Should have comments (lines starting with #)
    assert "#" in content_text


def test_template_comments_are_valid(valid_warehouse, temp_dir, monkeypatch):
    """TC6: Comments start with # and don't break YAML parsing."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    runner.invoke(main, ["setup", "--manual"])

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"

    # Should still parse correctly despite comments
    content = yaml.safe_load(beacon_yaml.read_text())
    assert content is not None


# ========== Regression: Bug #1 — duplicate skills key ==========


def test_template_has_no_duplicate_artifact_keys(
    valid_warehouse, temp_dir, monkeypatch
):
    """Regression #1: beacon.yaml template must not have duplicate YAML keys.

    A duplicate 'skills' key caused the first block to be silently discarded
    by YAML parsers, and confused users reading the file.
    """
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    runner.invoke(main, ["setup", "--manual"])

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    raw_text = beacon_yaml.read_text()

    # Count how many times each top-level artifact key appears as a YAML key
    import re

    knowledge_count = len(re.findall(r"^\s{2}knowledge:", raw_text, re.MULTILINE))
    skills_count = len(re.findall(r"^\s{2}skills:", raw_text, re.MULTILINE))
    contexts_count = len(re.findall(r"^\s{2}contexts:", raw_text, re.MULTILINE))

    assert knowledge_count == 1, f"Expected 1 'knowledge:' key, found {knowledge_count}"
    assert skills_count == 1, f"Expected 1 'skills:' key, found {skills_count}"
    assert contexts_count == 1, f"Expected 1 'contexts:' key, found {contexts_count}"


def test_template_context_comments_use_full_path(
    valid_warehouse, temp_dir, monkeypatch
):
    """Regression #1/#4: Context examples in template use full path (contexts/README.md).

    Old stale examples showed 'AGENTS.global.md' (old naming convention, no prefix),
    which would lead users/agents to fill in beacon.yaml incorrectly.
    """
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    runner.invoke(main, ["setup", "--manual"])

    raw_text = (project_dir / ".agentic-beacon" / "beacon.yaml").read_text()

    assert "AGENTS.global.md" not in raw_text, (
        "Template must not reference old 'AGENTS.global.md' naming convention"
    )
    assert "contexts/README.md" in raw_text, (
        "Template should show 'contexts/README.md' as a context example"
    )


def test_template_roundtrip_parses_correctly(valid_warehouse, temp_dir, monkeypatch):
    """TC10: Template can be loaded and re-saved without corruption."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    runner.invoke(main, ["setup", "--manual"])

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"

    # Load and re-save
    content = yaml.safe_load(beacon_yaml.read_text())
    new_yaml = yaml.dump(content)

    # Should parse again
    reparsed = yaml.safe_load(new_yaml)
    assert reparsed["artifacts"]["knowledge"] == []


# ========== Task 4.3: Three Workflow Support ==========


def test_setup_interactive_manual_workflow(valid_warehouse, temp_dir, monkeypatch):
    """TC2: Select manual workflow → Creates empty beacon.yaml."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])

    # Select option 2 (manual)
    result = runner.invoke(main, ["setup"], input="2\n")

    assert result.exit_code == 0

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    assert beacon_yaml.exists()


def test_setup_interactive_skip_workflow(valid_warehouse, temp_dir, monkeypatch):
    """TC3: Select skip → No beacon.yaml created."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])

    # Select option 3 (skip)
    result = runner.invoke(main, ["setup"], input="3\n")

    assert result.exit_code == 0

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    assert not beacon_yaml.exists()


# ========== Task 4.6: Non-interactive Flags ==========


def test_setup_manual_flag_bypasses_prompt(valid_warehouse, temp_dir, monkeypatch):
    """TC: --manual flag skips interactive prompt."""
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])

    result = runner.invoke(main, ["setup", "--manual"])

    assert result.exit_code == 0
    # Should not show interactive prompt
    assert "Select" not in result.output or "workflow" not in result.output.lower()

    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    assert beacon_yaml.exists()
