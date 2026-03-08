"""Tests for abc sync command.

Following TDD workflow for tasks 7.1-7.7:
- Task 7.1: sync command implementation
- Task 7.2: Warehouse connection validation
- Task 7.3: beacon.yaml existence validation
- Task 7.4: Artifact path validation
- Task 7.5: Progress output
- Task 7.6: Empty beacon.yaml handling
- Task 7.7: Invalid glob pattern handling
"""
import pytest
from pathlib import Path
from click.testing import CliRunner
from beacon.cli import main
import yaml


# ========== Task 7.1: ABC Sync Command Implementation ==========


def test_sync_with_valid_configuration(valid_warehouse, temp_dir, monkeypatch):
    """TC1: First sync with empty artifacts dir → All artifacts copied."""
    runner = CliRunner()
    
    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)
    
    # Create test files in warehouse
    (valid_warehouse / "knowledge" / "test.md").write_text("# Test")
    
    # Connect warehouse
    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    
    # Create beacon.yaml
    runner.invoke(main, ["setup", "--manual"])
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text("artifacts:\n  knowledge:\n    - knowledge/test.md\n  skills: []\n  contexts: []\n")
    
    # Run sync
    result = runner.invoke(main, ["sync"])
    
    assert result.exit_code == 0
    assert "sync" in result.output.lower() or "✓" in result.output
    
    # Verify file was copied
    synced_file = project_dir / ".agentic-beacon" / "artifacts" / "knowledge" / "test.md"
    assert synced_file.exists()
    assert synced_file.read_text() == "# Test"


def test_sync_is_idempotent(valid_warehouse, temp_dir, monkeypatch):
    """TC2: Second sync with no changes → No files copied (idempotent)."""
    runner = CliRunner()
    
    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)
    
    # Setup
    (valid_warehouse / "knowledge" / "test.md").write_text("# Test")
    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    runner.invoke(main, ["setup", "--manual"])
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text("artifacts:\n  knowledge:\n    - knowledge/test.md\n  skills: []\n  contexts: []\n")
    
    # First sync
    result1 = runner.invoke(main, ["sync"])
    assert result1.exit_code == 0
    
    synced_file = project_dir / ".agentic-beacon" / "artifacts" / "knowledge" / "test.md"
    mtime1 = synced_file.stat().st_mtime
    
    # Second sync - should be idempotent
    result2 = runner.invoke(main, ["sync"])
    assert result2.exit_code == 0
    
    # File should not have been re-copied
    mtime2 = synced_file.stat().st_mtime
    assert mtime2 == mtime1


def test_sync_with_glob_patterns(valid_warehouse, temp_dir, monkeypatch):
    """TC8: beacon.yaml with globs → All matching files synced."""
    runner = CliRunner()
    
    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)
    
    # Create multiple files matching pattern
    (valid_warehouse / "knowledge" / "python").mkdir(parents=True, exist_ok=True)
    (valid_warehouse / "knowledge" / "python" / "file1.md").write_text("# File 1")
    (valid_warehouse / "knowledge" / "python" / "file2.md").write_text("# File 2")
    
    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    runner.invoke(main, ["setup", "--manual"])
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text("artifacts:\n  knowledge:\n    - knowledge/python/*.md\n  skills: []\n  contexts: []\n")
    
    result = runner.invoke(main, ["sync"])
    
    assert result.exit_code == 0
    
    # Verify both files were copied
    artifacts_dir = project_dir / ".agentic-beacon" / "artifacts"
    assert (artifacts_dir / "knowledge" / "python" / "file1.md").exists()
    assert (artifacts_dir / "knowledge" / "python" / "file2.md").exists()


# ========== Task 7.2: Warehouse Connection Validation ==========


def test_sync_without_warehouse_connection(temp_dir, monkeypatch):
    """TC1: No config.toml exists → Error message about connection."""
    runner = CliRunner()
    
    project_dir = temp_dir / "project"
    project_dir.mkdir()
    
    # Create .agentic-beacon but no config.toml
    beacon_dir = project_dir / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "beacon.yaml").write_text("artifacts:\n  knowledge: []\n  skills: []\n  contexts: []\n")
    
    monkeypatch.chdir(project_dir)
    
    result = runner.invoke(main, ["sync"])
    
    assert result.exit_code == 1
    assert "warehouse" in result.output.lower()
    assert "connect" in result.output.lower()


# ========== Task 7.3: Beacon.yaml Existence Validation ==========


def test_sync_without_beacon_yaml(valid_warehouse, temp_dir, monkeypatch):
    """TC: No beacon.yaml → Error with actionable message."""
    runner = CliRunner()
    
    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)
    
    # Connect warehouse but don't create beacon.yaml
    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    
    result = runner.invoke(main, ["sync"])
    
    assert result.exit_code == 1
    assert "beacon.yaml" in result.output.lower()
    assert "setup" in result.output.lower()


# ========== Task 7.6: Empty Beacon.yaml Handling ==========


def test_sync_with_empty_beacon_yaml(valid_warehouse, temp_dir, monkeypatch):
    """TC: Empty beacon.yaml → No-op, friendly message."""
    runner = CliRunner()
    
    project_dir = temp_dir / "project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)
    
    runner.invoke(main, ["warehouse", "connect", "--path", str(valid_warehouse)])
    runner.invoke(main, ["setup", "--manual"])
    
    # beacon.yaml with empty lists
    beacon_yaml = project_dir / ".agentic-beacon" / "beacon.yaml"
    beacon_yaml.write_text("artifacts:\n  knowledge: []\n  skills: []\n  contexts: []\n")
    
    result = runner.invoke(main, ["sync"])
    
    assert result.exit_code == 0
    assert "no artifacts" in result.output.lower() or "nothing to sync" in result.output.lower()
