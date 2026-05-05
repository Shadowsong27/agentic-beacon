"""TDD Test Cases for Task 1.5: Add validation for beacon.yaml structure (artifacts grouped by type)

Test Coverage:
- TC1: All two valid artifact types → ValidationResult(valid=True)
- TC2: Only skills type → ValidationResult(valid=True)
- TC3: Unknown artifact type "agents" → ValidationError
- TC4: Artifact type with non-string item → ValidationError
- TC5: Artifact type with nested list → ValidationError
- TC6: Artifact type with dict instead of list → ValidationError
- TC7: Empty lists for all types → ValidationResult(valid=True)
- TC8: Multiple unknown types → ValidationError
- TC9: Mixed valid and invalid types → ValidationError
- TC10: Artifact paths with valid characters → ValidationResult(valid=True)
"""

import pytest
from beacon.core.exceptions import ValidationError
from beacon.core.manifest.beacon import BeaconManifest, BeaconManifestValidator

validator = BeaconManifestValidator()


class TestBeaconStructureValidation:
    """Test suite for beacon.yaml structure validation - Task 1.5"""

    def test_tc1_all_valid_artifact_types(self, temp_dir):
        """TC1: All valid artifact types → ValidationResult(valid=True)"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  skills:
    - skills/review/
  contexts:
    - context1.md
""")

        settings = BeaconManifest.from_yaml(str(beacon_file))
        result = validator.validate_structure(settings)

        assert result.valid is True
        assert len(result.errors) == 0

    def test_tc2_only_skills_type(self, temp_dir):
        """TC2: Only skills type → ValidationResult(valid=True)"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  skills:
    - skills/review/
""")

        settings = BeaconManifest.from_yaml(str(beacon_file))
        result = validator.validate_structure(settings)

        assert result.valid is True

    def test_tc3_unknown_artifact_type(self, temp_dir):
        """TC3: Unknown artifact type "plugins" → ValidationError"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  skills:
    - skills/review/
  plugins:
    - plugin1.md
""")

        with pytest.raises(ValidationError) as exc_info:
            BeaconManifest.from_yaml(str(beacon_file))

        assert "plugins" in str(exc_info.value).lower()

    def test_tc4_non_string_item(self, temp_dir):
        """TC4: Artifact type with non-string item → ValidationError"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  skills:
    - 12345
""")

        with pytest.raises(ValidationError) as exc_info:
            BeaconManifest.from_yaml(str(beacon_file))

        assert (
            "str" in str(exc_info.value).lower()
            or "string" in str(exc_info.value).lower()
        )

    def test_tc5_nested_list(self, temp_dir):
        """TC5: Artifact type with nested list → ValidationError"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  skills:
    -
      - nested.md
""")

        with pytest.raises(ValidationError):
            BeaconManifest.from_yaml(str(beacon_file))

    def test_tc6_dict_instead_of_list(self, temp_dir):
        """TC6: Artifact type with dict instead of list → ValidationError"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  skills:
    key: value
""")

        with pytest.raises(ValidationError) as exc_info:
            BeaconManifest.from_yaml(str(beacon_file))

        assert (
            "list" in str(exc_info.value).lower()
            or "array" in str(exc_info.value).lower()
        )

    def test_tc7_empty_lists(self, temp_dir, sample_beacon_yaml_empty):
        """TC7: Empty lists for all types → ValidationResult(valid=True)"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text(sample_beacon_yaml_empty)

        settings = BeaconManifest.from_yaml(str(beacon_file))
        result = validator.validate_structure(settings)

        assert result.valid is True

    def test_tc8_multiple_unknown_types(self, temp_dir):
        """TC8: Multiple unknown types → ValidationError"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  plugins:
    - plugin1.md
  extensions:
    - ext1.md
""")

        with pytest.raises(ValidationError) as exc_info:
            BeaconManifest.from_yaml(str(beacon_file))

        error_str = str(exc_info.value).lower()
        assert "plugins" in error_str or "extensions" in error_str

    def test_tc9_mixed_valid_and_invalid(self, temp_dir):
        """TC9: Mixed valid and invalid types → ValidationError"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  skills:
    - skills/review/
  invalid_type:
    - invalid.md
""")

        with pytest.raises(ValidationError) as exc_info:
            BeaconManifest.from_yaml(str(beacon_file))

        assert "invalid_type" in str(exc_info.value).lower()

    def test_tc10_invalid_path_characters(self, temp_dir):
        """TC10: Artifact paths with valid characters → ValidationResult(valid=True)"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  skills:
    - skills/valid-path/
    - skills/also_valid/
""")

        settings = BeaconManifest.from_yaml(str(beacon_file))
        result = validator.validate_structure(settings)
        assert result.valid is True
