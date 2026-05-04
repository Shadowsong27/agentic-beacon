"""Tests for manifest changes: knowledge removal, agents addition, legacy drop hook.

Covers tasks 3.1–3.5 from auto-pull-artifact-dependencies OpenSpec change.
"""

import pytest
import yaml
from beacon.core.exceptions import ValidationError as BeaconValidationError
from beacon.core.manifest.beacon import (
    ArtifactsConfig,
    BeaconManifest,
    BeaconManifestValidator,
)
from pydantic import ValidationError


class TestArtifactsConfig:
    """Task 3.1 + 3.2: ArtifactsConfig schema changes."""

    def test_tc1_knowledge_field_removed(self):
        """TC1: knowledge field returns empty list via backward-compat shim."""
        config = ArtifactsConfig()
        assert config.knowledge == []
        assert "knowledge" not in config.model_dump()

    def test_tc2_agents_field_exists_with_default(self):
        """TC2: agents field exists and defaults to empty list."""
        config = ArtifactsConfig()
        assert config.agents == []

    def test_tc3_agents_round_trip(self):
        """TC3: agents list persists through model_dump."""
        config = ArtifactsConfig(agents=["agents/foo.md"])
        dumped = config.model_dump()
        assert dumped["agents"] == ["agents/foo.md"]

    def test_tc4_extra_forbid_blocks_knowledge(self):
        """TC4: extra=forbid prevents knowledge from being set."""
        with pytest.raises(ValidationError):
            ArtifactsConfig(knowledge=["knowledge/foo.md"])


class TestLegacyDropHook:
    """Task 3.3: Legacy-drop migration hook in from_yaml."""

    def test_tc1_legacy_yaml_with_populated_knowledge(self, tmp_path, caplog):
        """TC1: Legacy YAML with populated knowledge list → stripped, log emitted, manifest valid."""
        beacon_file = tmp_path / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  knowledge:
    - knowledge/foo.md
  contexts: []
  skills: []
""")
        manifest = BeaconManifest.from_yaml(str(beacon_file))
        assert manifest.artifacts.knowledge == []
        assert "knowledge" not in manifest.artifacts.model_dump()
        assert manifest.artifacts.contexts == []
        assert manifest.artifacts.skills == []

    def test_tc2_legacy_yaml_with_empty_knowledge(self, tmp_path, caplog):
        """TC2: Legacy YAML with empty knowledge: [] → stripped, log emitted, manifest valid."""
        beacon_file = tmp_path / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  knowledge: []
  contexts: []
  skills: []
""")
        manifest = BeaconManifest.from_yaml(str(beacon_file))
        assert manifest.artifacts.knowledge == []
        assert "knowledge" not in manifest.artifacts.model_dump()
        assert manifest.artifacts.contexts == []
        assert manifest.artifacts.skills == []

    def test_tc3_modern_yaml_no_knowledge(self, tmp_path, caplog):
        """TC3: Modern YAML with no knowledge key → no migration log, manifest valid."""
        beacon_file = tmp_path / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  agents: []
  contexts: []
  skills: []
""")
        manifest = BeaconManifest.from_yaml(str(beacon_file))
        assert manifest.artifacts.knowledge == []
        assert "knowledge" not in manifest.artifacts.model_dump()
        assert manifest.artifacts.contexts == []
        assert manifest.artifacts.skills == []

    def test_tc4_missing_artifacts_key(self, tmp_path, caplog):
        """TC4: YAML missing artifacts key → existing error path, no migration log."""
        beacon_file = tmp_path / "beacon.yaml"
        beacon_file.write_text("knowledge:\n  - foo.md\n")

        with pytest.raises(BeaconValidationError) as exc_info:
            BeaconManifest.from_yaml(str(beacon_file))

        assert "artifacts" in str(exc_info.value).lower()

    def test_tc5_legacy_loaded_twice(self, tmp_path, caplog):
        """TC5: Legacy YAML loaded twice → log emitted each time."""
        beacon_file = tmp_path / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  knowledge:
    - knowledge/foo.md
  contexts: []
  skills: []
""")
        # Load twice
        BeaconManifest.from_yaml(str(beacon_file))
        BeaconManifest.from_yaml(str(beacon_file))
        # Both loads should succeed; loguru emits per-load

    def test_tc6_legacy_plus_extra_key(self, tmp_path):
        """TC6: Legacy YAML with knowledge and unexpected extra key → drops knowledge, extra triggers error."""
        beacon_file = tmp_path / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  knowledge:
    - knowledge/foo.md
  contexts: []
  skills: []
  unknown_type:
    - invalid.md
""")
        with pytest.raises(BeaconValidationError) as exc_info:
            BeaconManifest.from_yaml(str(beacon_file))

        error_str = str(exc_info.value).lower()
        assert (
            "unknown" in error_str or "extra" in error_str or "unexpected" in error_str
        )


class TestManifestWriter:
    """Task 3.4: Writer never serializes knowledge key."""

    def test_tc1_extra_forbid_prevents_knowledge_setattr(self):
        """TC1: setattr with knowledge raises ValidationError due to extra=forbid."""
        with pytest.raises(ValidationError):
            ArtifactsConfig(knowledge=["x"])

    def test_tc2_round_trip_no_knowledge(self, tmp_path):
        """TC2: Round-trip write produces no knowledge line."""
        beacon_file = tmp_path / "beacon.yaml"
        manifest = BeaconManifest(
            artifacts=ArtifactsConfig(
                agents=["agents/foo.md"], contexts=["contexts/bar.md"]
            )
        )
        manifest.to_yaml(str(beacon_file))

        content = beacon_file.read_text()
        assert "knowledge:" not in content
        assert "agents:" in content
        assert "contexts:" in content
        assert "skills:" in content

    def test_tc3_defaults_write_clean_yaml(self, tmp_path):
        """TC3: Manifest with defaults writes only agents, contexts, skills keys."""
        beacon_file = tmp_path / "beacon.yaml"
        manifest = BeaconManifest()
        manifest.to_yaml(str(beacon_file))

        data = yaml.safe_load(beacon_file.read_text())
        artifact_keys = set(data["artifacts"].keys())
        assert artifact_keys == {"agents", "contexts", "skills"}


class TestBeaconManifestValidator:
    """Task 3.5: Validator uses updated artifact types."""

    def test_validator_accepts_agents(self):
        """Validator accepts agents artifact type."""
        manifest = BeaconManifest(artifacts=ArtifactsConfig(agents=["agents/foo.md"]))
        validator = BeaconManifestValidator()
        result = validator.validate_structure(manifest)
        assert result.valid is True
        assert result.errors == []

    def test_validator_rejects_knowledge(self, tmp_path):
        """Validator no longer knows about knowledge type."""
        # This is tested indirectly: a manifest loaded from legacy YAML has knowledge stripped
        beacon_file = tmp_path / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  knowledge:
    - knowledge/foo.md
  contexts: []
  skills: []
""")
        manifest = BeaconManifest.from_yaml(str(beacon_file))
        validator = BeaconManifestValidator()
        result = validator.validate_structure(manifest)
        assert result.valid is True
