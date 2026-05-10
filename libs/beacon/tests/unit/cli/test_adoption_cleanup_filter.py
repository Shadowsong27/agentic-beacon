"""Unit test: cleanup_unadopted_artifacts must not receive agents/* paths (PER-122)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    beacon_dir = project / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "artifacts").mkdir()
    beacon_yaml = beacon_dir / "beacon.yaml"
    beacon_yaml.write_text(
        "artifacts:\n  contexts: []\n  skills: []\n  agents:\n    - agents/spec-planner.md\n"
    )
    (project / ".claude").mkdir()
    return project


@pytest.fixture
def warehouse(tmp_path: Path) -> Path:
    wh = tmp_path / "warehouse"
    wh.mkdir()
    (wh / "agents").mkdir()
    (wh / "agents" / "spec-planner.md").write_text(
        "---\nname: spec-planner\ndescription: Plans specs\n---\n"
    )
    return wh


def test_cleanup_unadopted_not_called_for_agent_paths(
    project_root: Path, warehouse: Path, monkeypatch
):
    """cleanup_unadopted_artifacts must not receive agents/* paths during adopt.

    Agents are handled atomically inside commit_session() (round-3 atomicity
    contract). The CLI must filter them out before passing to cleanup.
    """
    from beacon.cli.adoption import adopt
    from beacon.domains.adoption.models import AdoptResult

    cleanup_received: list[str] = []

    def spy_cleanup(unadoptions, *args, **kwargs):
        cleanup_received.extend(unadoptions)

    mock_manifest = MagicMock()
    mock_manifest.artifacts.contexts = []
    mock_manifest.artifacts.skills = []
    mock_manifest.artifacts.agents = ["agents/spec-planner.md"]

    mock_result = AdoptResult(
        to_adopt=[],
        to_unadopt=["agents/spec-planner.md"],
        pending_accept=[],
        pending_reject=[],
    )
    mock_app = MagicMock()
    mock_app.run.return_value = mock_result

    monkeypatch.setattr("beacon.cli.adoption.find_project_root", lambda: project_root)
    monkeypatch.setattr(
        "beacon.cli.adoption.WorkspaceConfig",
        lambda: MagicMock(warehouse=MagicMock(local_path=str(warehouse))),
    )
    monkeypatch.setattr(
        "beacon.cli.adoption.BeaconManifest",
        MagicMock(from_yaml=MagicMock(return_value=mock_manifest)),
    )
    monkeypatch.setattr("beacon.cli.adoption.discover_pending", lambda root: [])
    monkeypatch.setattr(
        "beacon.cli.adoption.discover_adoptable", lambda *a, **kw: ([], [])
    )
    monkeypatch.setattr("beacon.cli.adoption.is_interactive", lambda: True)
    monkeypatch.setattr(
        "beacon.cli.adoption.AdoptApp", lambda *args, **kwargs: mock_app
    )
    monkeypatch.setattr("beacon.cli.adoption.commit_session", lambda **kwargs: None)
    monkeypatch.setattr("beacon.cli.adoption.cleanup_unadopted_artifacts", spy_cleanup)

    runner = CliRunner()
    result = runner.invoke(adopt, [])
    assert result.exit_code == 0, (
        f"adopt CLI failed: exit={result.exit_code}\noutput:\n{result.output}\n"
        f"exception: {result.exception!r}"
    )

    agent_paths = [p for p in cleanup_received if p.startswith("agents/")]
    assert not agent_paths, (
        f"cleanup_unadopted_artifacts was called with agent paths: {agent_paths}"
    )
