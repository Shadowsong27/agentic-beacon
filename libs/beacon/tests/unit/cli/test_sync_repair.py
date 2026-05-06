"""Tests for abc sync interactive repair prompt (tasks 3.1–3.7)."""

from pathlib import Path

import pytest
import yaml
from beacon.core.exceptions import DependencyError
from beacon.core.manifest.beacon import BeaconManifest
from beacon.domains.distribution.orchestrator import run_sync


class TestSyncRepairPrompt:
    """Task 3.2–3.5: Sync repair prompt behaviour."""

    def _make_project(self, tmp_path: Path) -> tuple[Path, Path]:
        """Create a minimal project with beacon.yaml and warehouse."""
        project = tmp_path / "project"
        project.mkdir()
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()
        (warehouse / ".git").mkdir()
        (warehouse / "contexts").mkdir()
        (warehouse / "skills").mkdir()
        (warehouse / "agents").mkdir()
        (warehouse / "docs").mkdir()

        # Create beacon.yaml
        beacon_dir = project / ".agentic-beacon"
        beacon_dir.mkdir()
        beacon_yaml = beacon_dir / "beacon.yaml"
        beacon_yaml.write_text(
            "artifacts:\n  contexts: []\n  skills: []\n  agents: []\n"
        )

        # Create config.toml pointing to warehouse
        config_toml = beacon_dir / "config.toml"
        config_toml.write_text(f'[warehouse]\nlocal_path = "{warehouse}"\n')

        return project, warehouse

    def _write_skill(self, wh: Path, name: str) -> None:
        skill_dir = wh / "skills" / name
        skill_dir.mkdir(exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nrequires:\n  contexts: []\n---\n# Skill\n"
        )

    def _write_agent_manifest(self, wh: Path, agents: dict) -> None:
        (wh / "agents" / "agents.yaml").write_text(yaml.dump(agents))

    def test_tc1_auto_accept_gaps_updates_beacon(self, tmp_path, monkeypatch):
        """TC1: auto_accept_gaps=True → beacon.yaml updated, sync proceeds."""
        project, warehouse = self._make_project(tmp_path)
        self._write_skill(warehouse, "missing-skill")
        self._write_agent_manifest(
            warehouse, {"planner": {"skills": ["missing-skill"]}}
        )

        # Update beacon.yaml to declare the agent
        beacon_yaml = project / ".agentic-beacon" / "beacon.yaml"
        beacon = BeaconManifest.from_yaml(beacon_yaml)
        beacon.artifacts.agents = ["agents/planner.md"]
        beacon.to_yaml(beacon_yaml)

        monkeypatch.chdir(project)

        run_sync(
            project_root=project,
            dry_run=False,
            auto_accept_gaps=True,
            skip_git_check=True,
        )
        # After accepting gaps, beacon.yaml should have the skill
        updated = BeaconManifest.from_yaml(beacon_yaml)
        assert "skills/missing-skill/" in updated.artifacts.skills

    def test_tc2_reject_gaps_raises_error(self, tmp_path, monkeypatch):
        """TC2: Rejecting gaps → DependencyError, beacon.yaml untouched."""
        project, warehouse = self._make_project(tmp_path)
        self._write_agent_manifest(
            warehouse, {"planner": {"skills": ["missing-skill"]}}
        )

        beacon_yaml = project / ".agentic-beacon" / "beacon.yaml"
        beacon = BeaconManifest.from_yaml(beacon_yaml)
        beacon.artifacts.agents = ["agents/planner.md"]
        beacon.to_yaml(beacon_yaml)

        # Capture original content
        original_content = beacon_yaml.read_text()

        def reject_all(gap):
            return False

        monkeypatch.chdir(project)

        with pytest.raises(DependencyError):
            run_sync(
                project_root=project,
                dry_run=True,
                gap_prompt_callback=reject_all,
                skip_git_check=True,
            )

        # beacon.yaml should be unchanged
        assert beacon_yaml.read_text() == original_content

    def test_tc3_non_interactive_no_auto_accept_raises(self, tmp_path, monkeypatch):
        """TC3: Non-interactive without --yes → DependencyError."""
        project, warehouse = self._make_project(tmp_path)
        self._write_agent_manifest(
            warehouse, {"planner": {"skills": ["missing-skill"]}}
        )

        beacon_yaml = project / ".agentic-beacon" / "beacon.yaml"
        beacon = BeaconManifest.from_yaml(beacon_yaml)
        beacon.artifacts.agents = ["agents/planner.md"]
        beacon.to_yaml(beacon_yaml)

        monkeypatch.chdir(project)

        with pytest.raises(DependencyError):
            run_sync(
                project_root=project,
                dry_run=True,
                skip_git_check=True,
            )

    def test_tc4_no_gaps_sync_proceeds_normally(self, tmp_path, monkeypatch):
        """TC4: No gaps → sync proceeds normally."""
        project, warehouse = self._make_project(tmp_path)
        self._write_skill(warehouse, "existing-skill")

        beacon_yaml = project / ".agentic-beacon" / "beacon.yaml"
        beacon = BeaconManifest.from_yaml(beacon_yaml)
        beacon.artifacts.skills = ["existing-skill"]
        beacon.to_yaml(beacon_yaml)

        monkeypatch.chdir(project)

        result = run_sync(
            project_root=project,
            dry_run=True,
            skip_git_check=True,
        )
        assert result is not None

    def test_tc5_atomic_rejection(self, tmp_path, monkeypatch):
        """TC5: Two gaps, first Y second N → beacon.yaml untouched."""
        project, warehouse = self._make_project(tmp_path)
        self._write_agent_manifest(
            warehouse,
            {
                "planner": {"skills": ["skill-a"]},
                "reviewer": {"skills": ["skill-b"]},
            },
        )

        beacon_yaml = project / ".agentic-beacon" / "beacon.yaml"
        beacon = BeaconManifest.from_yaml(beacon_yaml)
        beacon.artifacts.agents = [
            "agents/planner.md",
            "agents/reviewer.md",
        ]
        beacon.to_yaml(beacon_yaml)

        original_content = beacon_yaml.read_text()
        call_count = 0

        def mixed_response(gap):
            nonlocal call_count
            call_count += 1
            return call_count == 1  # First Y, second N

        monkeypatch.chdir(project)

        with pytest.raises(DependencyError):
            run_sync(
                project_root=project,
                dry_run=True,
                gap_prompt_callback=mixed_response,
                skip_git_check=True,
            )

        assert beacon_yaml.read_text() == original_content
