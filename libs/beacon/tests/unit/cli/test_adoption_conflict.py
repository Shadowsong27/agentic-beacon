"""Unit test for CommitError → RegularFileConflictError unwrap path in adopt CLI."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from beacon.core.exceptions import AgentWireConflict, RegularFileConflictError
from beacon.domains.adoption.apply import CommitError
from click.testing import CliRunner


def _make_commit_error_wrapping_conflict(dest: Path) -> CommitError:
    conflict = AgentWireConflict(
        dest=dest, agent_name="spec-planner", tool="claudecode"
    )
    cause = RegularFileConflictError(conflicts=[conflict])
    err = CommitError("commit failed")
    err.__cause__ = cause
    return err


def test_adopt_commit_error_with_regular_file_conflict_cause(tmp_path):
    """adopt exits 1 and renders the conflict path when CommitError wraps RegularFileConflictError."""
    from beacon.cli.adoption import adopt

    dest = tmp_path / ".claude" / "agents" / "spec-planner.md"
    commit_err = _make_commit_error_wrapping_conflict(dest)

    # Create required dirs so the early existence checks pass
    beacon_dir = tmp_path / ".agentic-beacon"
    beacon_dir.mkdir(parents=True)
    (beacon_dir / "beacon.yaml").write_text("")

    # Build a fake candidate so the code doesn't short-circuit at "Nothing to adopt"
    fake_candidate = MagicMock()
    fake_candidate.artifact_type = "agent"
    fake_candidate.path = "agents/spec-planner.md"
    fake_candidate.description = "spec-planner agent"
    fake_candidate.commits_ago = None

    mock_result = MagicMock()
    mock_result.to_adopt = ["agents/spec-planner.md"]
    mock_result.to_unadopt = []
    mock_result.pending_accept = []
    mock_result.pending_reject = []

    runner = CliRunner()
    with (
        patch("beacon.cli.adoption.find_project_root", return_value=tmp_path),
        patch("beacon.cli.adoption.WorkspaceConfig") as mock_ws_cfg,
        patch("beacon.cli.adoption.BeaconManifest.from_yaml") as mock_manifest,
        patch("beacon.cli.adoption.discover_pending", return_value=[]),
        patch(
            "beacon.cli.adoption.discover_adoptable",
            return_value=([fake_candidate], []),
        ),
        patch("beacon.cli.adoption.is_interactive", return_value=True),
        patch("beacon.cli.adoption.AdoptApp") as mock_app_cls,
        patch("beacon.cli.adoption.commit_session", side_effect=commit_err),
    ):
        mock_ws_cfg.return_value.warehouse.local_path = str(tmp_path / "warehouse")

        mock_bm = mock_manifest.return_value
        mock_bm.artifacts.contexts = []
        mock_bm.artifacts.skills = []
        mock_bm.artifacts.agents = []

        mock_app_cls.return_value.run.return_value = mock_result

        result = runner.invoke(adopt)

    assert result.exit_code == 1
    assert str(dest) in result.output or "spec-planner" in result.output
    assert "Cannot wire 1 agent" in result.output
