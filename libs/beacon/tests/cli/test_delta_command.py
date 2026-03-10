"""Tests for abc delta command.

Following TDD workflow for tasks 9.1-9.7.
"""

import pytest
from beacon.cli import main
from click.testing import CliRunner


@pytest.fixture
def project_with_artifacts(temp_dir, valid_warehouse):
    """Create a project connected to warehouse with synced artifacts."""
    project = temp_dir / "project"
    project.mkdir()

    beacon_dir = project / ".agentic-beacon"
    beacon_dir.mkdir()

    # Create config.toml
    config = beacon_dir / "config.toml"
    config.write_text(f'[warehouse]\nlocal_path = "{valid_warehouse}"\n')

    # Create beacon.yaml
    beacon_yaml = beacon_dir / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  knowledge:\n    - knowledge/doc.md\n  skills: []\n  contexts: []\n"
    )

    # Create warehouse file
    (valid_warehouse / "knowledge" / "doc.md").write_text("# Warehouse content")

    # Create synced artifact (identical)
    artifacts_dir = beacon_dir / "artifacts"
    (artifacts_dir / "knowledge").mkdir(parents=True)
    (artifacts_dir / "knowledge" / "doc.md").write_text("# Warehouse content")

    return project


def test_delta_no_differences(project_with_artifacts, monkeypatch):
    """TC2: No changes → "No differences found"."""
    runner = CliRunner()
    monkeypatch.chdir(project_with_artifacts)
    result = runner.invoke(main, ["delta"])
    assert result.exit_code == 0
    assert "No differences found" in result.output


def test_delta_modified_file(project_with_artifacts, monkeypatch):
    """TC1: 1 modified file → Shows summary with modified entry."""
    # Modify local file
    artifacts_dir = project_with_artifacts / ".agentic-beacon" / "artifacts"
    (artifacts_dir / "knowledge" / "doc.md").write_text("# Modified locally")

    runner = CliRunner()
    monkeypatch.chdir(project_with_artifacts)
    result = runner.invoke(main, ["delta"])
    assert result.exit_code == 0
    assert "Modified" in result.output


def test_delta_no_warehouse_connected(temp_dir, monkeypatch):
    """TC8: No warehouse connected → Error."""
    project = temp_dir / "project"
    project.mkdir()
    (project / ".agentic-beacon").mkdir()

    runner = CliRunner()
    monkeypatch.chdir(project)
    result = runner.invoke(main, ["delta"])
    assert result.exit_code == 1
    assert "No warehouse connected" in result.output


def test_delta_no_beacon_yaml(temp_dir, valid_warehouse, monkeypatch):
    """TC9: No beacon.yaml → Error."""
    project = temp_dir / "project"
    project.mkdir()
    beacon_dir = project / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "config.toml").write_text(
        f'[warehouse]\nlocal_path = "{valid_warehouse}"\n'
    )

    runner = CliRunner()
    monkeypatch.chdir(project)
    result = runner.invoke(main, ["delta"])
    assert result.exit_code == 1
    assert "No beacon.yaml found" in result.output


def test_delta_no_beacon_dir(temp_dir, monkeypatch):
    """No .agentic-beacon directory → Error."""
    project = temp_dir / "project"
    project.mkdir()

    runner = CliRunner()
    monkeypatch.chdir(project)
    result = runner.invoke(main, ["delta"])
    assert result.exit_code == 1
    assert "No .agentic-beacon" in result.output
