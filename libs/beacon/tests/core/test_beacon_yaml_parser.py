"""TDD Test Cases for Task 1.1: Create beacon.yaml schema and parser for artifact dependencies

Test Coverage:
- TC1: Valid complete beacon.yaml → Returns BeaconSettings with all artifact types populated
- TC2: Valid partial beacon.yaml (only knowledge) → Returns BeaconSettings with empty lists for skills/contexts
- TC3: Empty artifacts section → Returns BeaconSettings with all types as empty lists
- TC4: Invalid YAML syntax → Raises YAMLParseError with syntax message
- TC5: Missing artifacts root key → Raises ValidationError "Missing required 'artifacts' section"
- TC6: Artifact type not a list (string) → Raises ValidationError "Artifact types must be lists"
- TC7: Unknown artifact type → Raises ValidationError listing unknown type
- TC8: File not found → Raises FileNotFoundError with helpful message
- TC9: File is directory not file → Raises IsADirectoryError
- TC10: Permission denied reading file → Raises PermissionError with clear message
"""

from pathlib import Path

import pytest
from beacon.core.exceptions import ValidationError, YAMLParseError
from beacon.core.settings import BeaconSettings


class TestBeaconYAMLParser:
    """Test suite for BeaconSettings.from_yaml() - Task 1.1"""

    def test_tc1_valid_complete_beacon_yaml(
        self, temp_dir, sample_beacon_yaml_complete
    ):
        """TC1: Valid complete beacon.yaml → Returns BeaconSettings with all artifact types populated"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text(sample_beacon_yaml_complete)

        settings = BeaconSettings.from_yaml(str(beacon_file))

        assert isinstance(settings, BeaconSettings)
        assert len(settings.artifacts.knowledge) == 2
        assert "languages/python/type-hints.md" in settings.artifacts.knowledge
        assert "languages/python/async-patterns.md" in settings.artifacts.knowledge
        assert len(settings.artifacts.skills) == 2
        assert "development/tdd-workflow.md" in settings.artifacts.skills
        assert len(settings.artifacts.contexts) == 1
        assert "teams/backend/AGENTS.md" in settings.artifacts.contexts

    def test_tc2_valid_partial_beacon_yaml(self, temp_dir, sample_beacon_yaml_partial):
        """TC2: Valid partial beacon.yaml (only knowledge) → Returns BeaconSettings with empty lists for skills/contexts"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text(sample_beacon_yaml_partial)

        settings = BeaconSettings.from_yaml(str(beacon_file))

        assert isinstance(settings, BeaconSettings)
        assert len(settings.artifacts.knowledge) == 1
        assert settings.artifacts.knowledge[0] == "languages/python/basics.md"
        assert len(settings.artifacts.skills) == 0
        assert len(settings.artifacts.contexts) == 0

    def test_tc3_empty_artifacts_section(self, temp_dir, sample_beacon_yaml_empty):
        """TC3: Empty artifacts section → Returns BeaconSettings with all types as empty lists"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text(sample_beacon_yaml_empty)

        settings = BeaconSettings.from_yaml(str(beacon_file))

        assert isinstance(settings, BeaconSettings)
        assert len(settings.artifacts.knowledge) == 0
        assert len(settings.artifacts.skills) == 0
        assert len(settings.artifacts.contexts) == 0

    def test_tc4_invalid_yaml_syntax(self, temp_dir):
        """TC4: Invalid YAML syntax → Raises YAMLParseError with syntax message"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  knowledge:
    - item1
  - invalid indentation
""")

        with pytest.raises(YAMLParseError) as exc_info:
            BeaconSettings.from_yaml(str(beacon_file))

        assert (
            "syntax" in str(exc_info.value).lower()
            or "parse" in str(exc_info.value).lower()
        )

    def test_tc5_missing_artifacts_root_key(self, temp_dir):
        """TC5: Missing artifacts root key → Raises ValidationError "Missing required 'artifacts' section" """
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text("""
knowledge:
  - some-file.md
""")

        with pytest.raises(ValidationError) as exc_info:
            BeaconSettings.from_yaml(str(beacon_file))

        assert "artifacts" in str(exc_info.value).lower()

    def test_tc6_artifact_type_not_a_list(self, temp_dir):
        """TC6: Artifact type not a list (string) → Raises ValidationError "Artifact types must be lists" """
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  knowledge: "not-a-list"
""")

        with pytest.raises(ValidationError) as exc_info:
            BeaconSettings.from_yaml(str(beacon_file))

        # Pydantic should complain about type mismatch
        assert (
            "list" in str(exc_info.value).lower()
            or "type" in str(exc_info.value).lower()
        )

    def test_tc7_unknown_artifact_type(self, temp_dir):
        """TC7: Unknown artifact type → Raises ValidationError listing unknown type"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  knowledge:
    - valid.md
  unknown_type:
    - invalid.md
""")

        with pytest.raises(ValidationError) as exc_info:
            BeaconSettings.from_yaml(str(beacon_file))

        error_str = str(exc_info.value).lower()
        # Should mention the unknown field
        assert (
            "unknown" in error_str or "extra" in error_str or "unexpected" in error_str
        )

    def test_tc8_file_not_found(self, temp_dir):
        """TC8: File not found → Raises FileNotFoundError with helpful message"""
        non_existent_file = temp_dir / "non_existent.yaml"

        with pytest.raises(FileNotFoundError) as exc_info:
            BeaconSettings.from_yaml(str(non_existent_file))

        assert "non_existent.yaml" in str(exc_info.value) or str(
            non_existent_file
        ) in str(exc_info.value)

    def test_tc9_file_is_directory(self, temp_dir):
        """TC9: File is directory not file → Raises IsADirectoryError"""
        dir_path = temp_dir / "beacon_dir"
        dir_path.mkdir()

        with pytest.raises(IsADirectoryError):
            BeaconSettings.from_yaml(str(dir_path))

    @pytest.mark.skipif(
        not hasattr(Path, "chmod"), reason="chmod not available on this platform"
    )
    def test_tc10_permission_denied(self, temp_dir, sample_beacon_yaml_complete):
        """TC10: Permission denied reading file → Raises PermissionError with clear message"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text(sample_beacon_yaml_complete)

        # Remove read permissions
        beacon_file.chmod(0o000)

        try:
            with pytest.raises(PermissionError) as exc_info:
                BeaconSettings.from_yaml(str(beacon_file))

            assert (
                "permission" in str(exc_info.value).lower()
                or "denied" in str(exc_info.value).lower()
            )
        finally:
            # Restore permissions for cleanup
            beacon_file.chmod(0o644)
