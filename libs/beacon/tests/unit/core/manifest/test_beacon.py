"""Tests for beacon.yaml schema extension with agents field (tasks 1.1–1.4)."""

import pytest
import yaml
from beacon.core.exceptions import ValidationError as BeaconValidationError
from beacon.core.manifest.beacon import (
    ArtifactsConfig,
    BeaconManifest,
    BeaconManifestValidator,
)
from pydantic import ValidationError


class TestArtifactsConfigAgentsField:
    """Task 1.1: agents field on ArtifactsConfig — TDD test cases."""

    def test_tc1_agents_empty_list(self):
        """TC1: beacon.yaml with artifacts.agents: [] → parses, agents == []"""
        config = ArtifactsConfig(agents=[])
        assert config.agents == []

    def test_tc2_agents_populated_list(self):
        """TC2: beacon.yaml with artifacts.agents: [agents/spec-planner.md] → parses"""
        config = ArtifactsConfig(agents=["agents/spec-planner.md"])
        assert config.agents == ["agents/spec-planner.md"]

    def test_tc3_agents_default_empty(self):
        """TC3: ArtifactsConfig() with no agents key → agents == [] (default)"""
        config = ArtifactsConfig()
        assert config.agents == []

    def test_tc4_agents_none_raises_validation_error(self):
        """TC4: agents: null → raises ValidationError (documented behaviour)."""
        with pytest.raises(ValidationError) as exc_info:
            ArtifactsConfig(agents=None)
        assert "agents" in str(exc_info.value)

    def test_tc5_agents_not_a_list_raises(self):
        """TC5: artifacts.agents: 'not-a-list' → Pydantic ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            ArtifactsConfig(agents="not-a-list")
        assert "agents" in str(exc_info.value)


class TestBeaconManifestRoundTrip:
    """Tasks 1.2 + 1.3: Round-trip YAML serialisation with agents field."""

    def test_tc1_all_three_lists_populated_ordering(self, tmp_path):
        """TC1: Manifest with all three lists → YAML emits contexts, skills, agents in that order"""
        beacon_file = tmp_path / "beacon.yaml"
        manifest = BeaconManifest(
            artifacts=ArtifactsConfig(
                contexts=["contexts/foo.md"],
                skills=["skills/bar/"],
                agents=["agents/spec-planner.md"],
            )
        )
        manifest.to_yaml(str(beacon_file))
        content = beacon_file.read_text()
        # Check ordering under artifacts:
        artifacts_idx = content.index("artifacts:")
        contexts_idx = content.index("contexts:", artifacts_idx)
        skills_idx = content.index("skills:", artifacts_idx)
        agents_idx = content.index("agents:", artifacts_idx)
        assert contexts_idx < skills_idx < agents_idx

    def test_tc2_only_agents_populated_emits_all(self, tmp_path):
        """TC2: Manifest with only agents → YAML still emits all three keys"""
        beacon_file = tmp_path / "beacon.yaml"
        manifest = BeaconManifest(
            artifacts=ArtifactsConfig(agents=["agents/planner.md"])
        )
        manifest.to_yaml(str(beacon_file))
        content = beacon_file.read_text()
        assert "contexts:" in content
        assert "skills:" in content
        assert "agents:" in content

    def test_tc3_round_trip_mixed_agents(self, tmp_path):
        """TC3: Round-trip preserves agent paths"""
        beacon_file = tmp_path / "beacon.yaml"
        original = BeaconManifest(
            artifacts=ArtifactsConfig(
                contexts=["contexts/a.md"],
                skills=["skills/b/"],
                agents=["agents/x.md", "agents/y.md"],
            )
        )
        original.to_yaml(str(beacon_file))
        loaded = BeaconManifest.from_yaml(str(beacon_file))
        assert loaded.artifacts.agents == ["agents/x.md", "agents/y.md"]

    def test_tc4_existing_manifest_without_agents_adds_empty(self, tmp_path):
        """TC4: Existing manifest without agents → serialises with trailing agents: []"""
        beacon_file = tmp_path / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  contexts:
    - contexts/foo.md
  skills:
    - skills/bar/
""")
        manifest = BeaconManifest.from_yaml(str(beacon_file))
        manifest.to_yaml(str(beacon_file))
        content = beacon_file.read_text()
        assert "agents:" in content
        data = yaml.safe_load(content)
        assert data["artifacts"]["agents"] == []

    def test_tc5_round_trip_after_mutation(self, tmp_path):
        """TC5: Round-trip after mutating agents list → new entry appears"""
        beacon_file = tmp_path / "beacon.yaml"
        manifest = BeaconManifest(artifacts=ArtifactsConfig(agents=["agents/a.md"]))
        manifest.to_yaml(str(beacon_file))
        manifest.artifacts.agents.append("agents/b.md")
        manifest.to_yaml(str(beacon_file))
        loaded = BeaconManifest.from_yaml(str(beacon_file))
        assert loaded.artifacts.agents == ["agents/a.md", "agents/b.md"]

    def test_tc6_from_yaml_without_agents_key_defaults_to_empty(self, tmp_path):
        """TC6: beacon.yaml with no agents key → parses, agents == []"""
        beacon_file = tmp_path / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  contexts: []
  skills: []
""")
        manifest = BeaconManifest.from_yaml(str(beacon_file))
        assert manifest.artifacts.agents == []

    def test_tc7_from_yaml_with_agents_key_parses(self, tmp_path):
        """TC7: beacon.yaml with agents key → parses correctly"""
        beacon_file = tmp_path / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  contexts: []
  skills: []
  agents:
    - agents/spec-planner.md
""")
        manifest = BeaconManifest.from_yaml(str(beacon_file))
        assert manifest.artifacts.agents == ["agents/spec-planner.md"]


class TestBeaconManifestValidatorWithAgents:
    """Task 1.1: Validator accepts agents artifact type."""

    def test_validator_accepts_agents(self):
        """Validator accepts agents artifact type."""
        manifest = BeaconManifest(artifacts=ArtifactsConfig(agents=["agents/foo.md"]))
        validator = BeaconManifestValidator()
        result = validator.validate_structure(manifest)
        assert result.valid is True
        assert result.errors == []

    def test_validator_rejects_non_list_agents(self, tmp_path):
        """Validator rejects non-list agents via from_yaml."""
        pass

    def test_from_yaml_accepts_agents(self, tmp_path):
        """from_yaml accepts agents as a valid artifact type."""
        beacon_file = tmp_path / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  contexts: []
  skills: []
  agents:
    - agents/reviewer.md
""")
        manifest = BeaconManifest.from_yaml(str(beacon_file))
        assert manifest.artifacts.agents == ["agents/reviewer.md"]

    def test_from_yaml_rejects_non_list_agents(self, tmp_path):
        """from_yaml rejects non-list agents value."""
        beacon_file = tmp_path / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  contexts: []
  skills: []
  agents: "not-a-list"
""")
        with pytest.raises(BeaconValidationError) as exc_info:
            BeaconManifest.from_yaml(str(beacon_file))
        assert "agents" in str(exc_info.value).lower()

    def test_from_yaml_rejects_non_string_agents(self, tmp_path):
        """from_yaml rejects non-string items in agents list."""
        beacon_file = tmp_path / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  contexts: []
  skills: []
  agents:
    - 123
""")
        with pytest.raises(BeaconValidationError) as exc_info:
            BeaconManifest.from_yaml(str(beacon_file))
        assert "agents" in str(exc_info.value).lower()
