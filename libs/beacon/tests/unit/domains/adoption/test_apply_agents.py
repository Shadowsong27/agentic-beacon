"""Tests for adoption apply flow with agents (tasks 4.1–4.5)."""

from beacon.core.manifest.beacon import BeaconManifest
from beacon.domains.adoption.apply import apply_adoption, cleanup_unadopted_artifacts
from beacon.domains.adoption.discovery import is_adopted
from beacon.domains.adoption.models import AdoptCandidate


class TestApplyAdoptionAgents:
    """Task 4.1: apply_adoption records agent selections."""

    def test_tc1_first_time_adopt_agent(self, tmp_path):
        """TC1: First-time adopt of one agent → entry appears exactly once."""
        beacon_file = tmp_path / "beacon.yaml"
        beacon_file.write_text(
            "artifacts:\n  contexts: []\n  skills: []\n  agents: []\n"
        )

        selections = [
            AdoptCandidate(artifact_type="agents", path="agents/spec-planner.md")
        ]
        apply_adoption(beacon_file, selections)

        manifest = BeaconManifest.from_yaml(beacon_file)
        assert manifest.artifacts.agents == ["agents/spec-planner.md"]

    def test_tc2_re_adopt_same_agent_no_duplicate(self, tmp_path):
        """TC2: Re-adopt same agent → no duplicate appended."""
        beacon_file = tmp_path / "beacon.yaml"
        beacon_file.write_text(
            "artifacts:\n  contexts: []\n  skills: []\n  agents:\n    - agents/spec-planner.md\n"
        )

        selections = [
            AdoptCandidate(artifact_type="agents", path="agents/spec-planner.md")
        ]
        apply_adoption(beacon_file, selections)

        manifest = BeaconManifest.from_yaml(beacon_file)
        assert manifest.artifacts.agents == ["agents/spec-planner.md"]

    def test_tc3_adopt_mixed_artifacts(self, tmp_path):
        """TC3: Adopt agent + context + skill in same run → all three appear."""
        beacon_file = tmp_path / "beacon.yaml"
        beacon_file.write_text(
            "artifacts:\n  contexts: []\n  skills: []\n  agents: []\n"
        )

        selections = [
            AdoptCandidate(artifact_type="agents", path="agents/planner.md"),
            AdoptCandidate(artifact_type="contexts", path="contexts/team.md"),
            AdoptCandidate(artifact_type="skills", path="skills/review/"),
        ]
        apply_adoption(beacon_file, selections)

        manifest = BeaconManifest.from_yaml(beacon_file)
        assert manifest.artifacts.agents == ["agents/planner.md"]
        assert manifest.artifacts.contexts == ["contexts/team.md"]
        assert manifest.artifacts.skills == ["skills/review/"]


class TestIsAdoptedAgents:
    """Task 4.3: is_adopted checks artifacts.agents."""

    def test_agent_in_artifacts_agents_returns_true(self, tmp_path):
        """Agent path returns True when in artifacts.agents."""
        beacon_file = tmp_path / "beacon.yaml"
        beacon_file.write_text(
            "artifacts:\n  contexts: []\n  skills: []\n  agents:\n    - agents/planner.md\n"
        )
        manifest = BeaconManifest.from_yaml(beacon_file)
        assert is_adopted("agents/planner.md", manifest) is True

    def test_agent_not_in_artifacts_agents_returns_false(self, tmp_path):
        """Agent path returns False when not in artifacts.agents."""
        beacon_file = tmp_path / "beacon.yaml"
        beacon_file.write_text(
            "artifacts:\n  contexts: []\n  skills: []\n  agents: []\n"
        )
        manifest = BeaconManifest.from_yaml(beacon_file)
        assert is_adopted("agents/missing.md", manifest) is False


class TestCleanupUnadoptedAgents:
    """Task 4.4: cleanup does NOT uninstall global agent symlinks."""

    def test_agent_unadopt_does_not_remove_global_symlink(self, tmp_path):
        """TC1: Remove agent from beacon.yaml, run cleanup → global symlinks persist."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        warehouse = tmp_path / "warehouse"
        warehouse.mkdir()

        # Create a fake global agent symlink
        agent_file = warehouse / "agents" / "planner.md"
        agent_file.parent.mkdir(parents=True)
        agent_file.write_text("# Agent\n")
        global_dir = tmp_path / ".config" / "opencode" / "agents"
        global_dir.mkdir(parents=True)
        global_link = global_dir / "planner.md"
        global_link.symlink_to(agent_file)

        cleanup_unadopted_artifacts(
            ["agents/planner.md"],
            artifacts_dir,
            warehouse,
        )

        # Global symlink should still exist
        assert global_link.exists()
