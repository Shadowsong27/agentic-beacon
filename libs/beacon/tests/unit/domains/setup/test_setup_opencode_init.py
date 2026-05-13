"""Unit tests for auto-init of opencode.json + CLAUDE.md during abc setup (PER-151).

Tests 1-2 cover the setup CLI handler invoking init_opencode_json + init_claude_md.
"""

from __future__ import annotations

import json
from pathlib import Path

from beacon.cli.main import main
from click.testing import CliRunner


def _connected_project(tmp_path: Path, monkeypatch) -> tuple[Path, CliRunner]:
    """Create a project connected to a minimal warehouse stub with CWD set."""
    project = tmp_path / "project"
    project.mkdir()
    warehouse = tmp_path / "warehouse"
    warehouse.mkdir()
    (warehouse / "contexts").mkdir()
    (warehouse / "skills").mkdir()
    (warehouse / "README.md").write_text("# Warehouse\n")

    ab = project / ".agentic-beacon"
    ab.mkdir()
    (ab / "config.toml").write_text(f'[warehouse]\nlocal_path = "{warehouse}"\n')

    monkeypatch.chdir(project)
    runner = CliRunner()
    return project, runner


def test_setup_creates_opencode_json_and_claude_md(tmp_path, monkeypatch):
    """abc setup creates opencode.json and CLAUDE.md at project root."""
    project, runner = _connected_project(tmp_path, monkeypatch)

    result = runner.invoke(main, ["setup"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    assert (project / "opencode.json").exists()
    assert (project / "CLAUDE.md").exists()

    data = json.loads((project / "opencode.json").read_text())
    assert "$schema" in data
    assert "instructions" in data


def test_setup_idempotent_does_not_overwrite_existing_files(tmp_path, monkeypatch):
    """abc setup does not overwrite existing opencode.json or CLAUDE.md."""
    project, runner = _connected_project(tmp_path, monkeypatch)

    custom_opencode = (
        '{"$schema": "https://opencode.ai/config.json", "instructions": ["custom"]}\n'
    )
    custom_claude = "# My Custom CLAUDE.md\nDo not overwrite me.\n"
    (project / "opencode.json").write_text(custom_opencode)
    (project / "CLAUDE.md").write_text(custom_claude)

    # Run setup (beacon.yaml doesn't exist yet, so it will create it)
    result = runner.invoke(main, ["setup"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    assert (project / "opencode.json").read_text() == custom_opencode
    assert (project / "CLAUDE.md").read_text() == custom_claude


def test_setup_does_not_claim_initialization_when_files_preexisted(
    tmp_path, monkeypatch
):
    """abc setup must not print 'Initialized' for files that already existed."""
    project, runner = _connected_project(tmp_path, monkeypatch)

    (project / "opencode.json").write_text('{"custom": true}\n')
    (project / "CLAUDE.md").write_text("# Mine\n")

    result = runner.invoke(main, ["setup"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    assert "Initialized opencode.json" not in result.output
    assert "Initialized CLAUDE.md" not in result.output
    # Files must remain unchanged
    assert (project / "opencode.json").read_text() == '{"custom": true}\n'
    assert (project / "CLAUDE.md").read_text() == "# Mine\n"
