"""Tests for abc setup command."""

import re

import yaml
from beacon.cli.main import main
from click.testing import CliRunner


def _connected_project(valid_warehouse, temp_dir, monkeypatch):
    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)
    runner = CliRunner()
    result = runner.invoke(
        main, ["warehouse", "connect", "--path", str(valid_warehouse)]
    )
    assert result.exit_code == 0, result.output
    return project_dir, runner


def test_setup_creates_beacon_yaml_without_workflow_prompt(
    valid_warehouse, temp_dir, monkeypatch
):
    project_dir, runner = _connected_project(valid_warehouse, temp_dir, monkeypatch)

    result = runner.invoke(main, ["setup"])

    assert result.exit_code == 0, result.output
    assert "Select workflow" not in result.output
    assert "Skip" not in result.output
    assert "abc adopt" in result.output
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    assert beacon_yaml.exists()


def test_setup_without_warehouse_connected_shows_error(temp_dir, monkeypatch):
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    beacon_dir = project_dir / ".agentic-beacon"
    beacon_dir.mkdir()
    monkeypatch.chdir(project_dir)

    result = runner.invoke(main, ["setup"])

    assert result.exit_code == 1
    assert "warehouse" in result.output.lower()
    assert "connect" in result.output.lower()


def test_setup_without_agentic_beacon_dir_shows_error(temp_dir, monkeypatch):
    runner = CliRunner()

    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    result = runner.invoke(main, ["setup"])

    assert result.exit_code == 1
    assert "warehouse" in result.output.lower() or "connect" in result.output.lower()


def test_setup_existing_beacon_yaml_decline_preserves_file(
    valid_warehouse, temp_dir, monkeypatch
):
    project_dir, runner = _connected_project(valid_warehouse, temp_dir, monkeypatch)
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    original = "artifacts:\n  contexts:\n    - contexts/existing.md\n"
    beacon_yaml.write_text(original)

    result = runner.invoke(main, ["setup"], input="n\n")

    assert result.exit_code == 0, result.output
    assert "already exists" in result.output
    assert beacon_yaml.read_text() == original


def test_setup_existing_beacon_yaml_confirm_overwrites_file(
    valid_warehouse, temp_dir, monkeypatch
):
    project_dir, runner = _connected_project(valid_warehouse, temp_dir, monkeypatch)
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text("artifacts:\n  contexts:\n    - contexts/existing.md\n")

    result = runner.invoke(main, ["setup"], input="y\n")

    assert result.exit_code == 0, result.output
    content = yaml.safe_load(beacon_yaml.read_text())
    assert "knowledge" not in content["artifacts"]


def test_setup_template_is_valid_empty_artifact_yaml(
    valid_warehouse, temp_dir, monkeypatch
):
    project_dir, runner = _connected_project(valid_warehouse, temp_dir, monkeypatch)

    result = runner.invoke(main, ["setup"])

    assert result.exit_code == 0, result.output
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    content = yaml.safe_load(beacon_yaml.read_text())
    assert content == {
        "artifacts": {"skills": [], "contexts": []},
    }


def test_setup_template_includes_commented_examples(
    valid_warehouse, temp_dir, monkeypatch
):
    project_dir, runner = _connected_project(valid_warehouse, temp_dir, monkeypatch)

    result = runner.invoke(main, ["setup"])

    assert result.exit_code == 0, result.output
    raw_text = (project_dir / ".agentic-beacon" / "beacon.yaml").read_text()
    assert "are machine-level global artifacts" in raw_text
    assert "# - skills/code-review/" in raw_text
    assert "# - contexts/README.md" in raw_text


def test_setup_template_has_no_duplicate_artifact_keys(
    valid_warehouse, temp_dir, monkeypatch
):
    project_dir, runner = _connected_project(valid_warehouse, temp_dir, monkeypatch)

    result = runner.invoke(main, ["setup"])

    assert result.exit_code == 0, result.output
    raw_text = (project_dir / ".agentic-beacon" / "beacon.yaml").read_text()
    assert len(re.findall(r"^\s{2}skills:", raw_text, re.MULTILINE)) == 1
    assert len(re.findall(r"^\s{2}contexts:", raw_text, re.MULTILINE)) == 1


def test_setup_does_not_generate_agent_assisted_catalog(
    valid_warehouse, temp_dir, monkeypatch
):
    project_dir, runner = _connected_project(valid_warehouse, temp_dir, monkeypatch)

    result = runner.invoke(main, ["setup"])

    assert result.exit_code == 0, result.output
    assert not (project_dir / ".agentic-beacon" / "warehouse-catalog.md").exists()


def test_setup_manual_flag_is_removed(valid_warehouse, temp_dir, monkeypatch):
    _project_dir, runner = _connected_project(valid_warehouse, temp_dir, monkeypatch)

    result = runner.invoke(main, ["setup", "--manual"])

    assert result.exit_code != 0
    assert "No such option: --manual" in result.output


def test_setup_agent_assisted_flag_is_removed(valid_warehouse, temp_dir, monkeypatch):
    _project_dir, runner = _connected_project(valid_warehouse, temp_dir, monkeypatch)

    result = runner.invoke(main, ["setup", "--agent-assisted"])

    assert result.exit_code != 0
    assert "No such option: --agent-assisted" in result.output
