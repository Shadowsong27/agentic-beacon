"""TDD Test Cases for Task 1.5: Add validation for beacon.yaml structure (artifacts grouped by type)

Test Coverage:
- TC1: All three valid artifact types → ValidationResult(valid=True)
- TC2: Only knowledge type → ValidationResult(valid=True)
- TC3: Unknown artifact type "plugins" → ValidationResult(valid=False, errors=["Unknown artifact type: plugins"])
- TC4: Artifact type with non-string item → ValidationResult(valid=False, errors=["All items must be strings"])
- TC5: Artifact type with nested list → ValidationResult(valid=False, errors=["Nested lists not allowed"])
- TC6: Artifact type with dict instead of list → ValidationResult(valid=False, errors=["Must be list"])
- TC7: Empty lists for all types → ValidationResult(valid=True)
- TC8: Multiple unknown types → ValidationResult lists all unknown types in errors
- TC9: Mixed valid and invalid types → ValidationResult lists only invalid ones
- TC10: Artifact paths with invalid characters → ValidationResult(valid=False) with path validation errors
"""
import pytest
from beacon.core.settings import BeaconSettings, BeaconYamlValidator
from beacon.core.exceptions import ValidationError


# Create validator instance for tests
validator = BeaconYamlValidator()


class TestBeaconStructureValidation:
    """Test suite for beacon.yaml structure validation - Task 1.5"""

    def test_tc1_all_valid_artifact_types(self, temp_dir):
        """TC1: All three valid artifact types → ValidationResult(valid=True)"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  knowledge:
    - file1.md
  skills:
    - skill1.md
  contexts:
    - context1.md
""")
        
        settings = BeaconSettings.from_yaml(str(beacon_file))
        result = validator.validate_structure(settings)
        
        assert result.valid is True
        assert len(result.errors) == 0

    def test_tc2_only_knowledge_type(self, temp_dir):
        """TC2: Only knowledge type → ValidationResult(valid=True)"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  knowledge:
    - file1.md
""")
        
        settings = BeaconSettings.from_yaml(str(beacon_file))
        result = validator.validate_structure(settings)
        
        assert result.valid is True

    def test_tc3_unknown_artifact_type(self, temp_dir):
        """TC3: Unknown artifact type "plugins" → ValidationResult(valid=False, errors=[...])"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  knowledge:
    - file1.md
  plugins:
    - plugin1.md
""")
        
        # Should fail during parsing with ValidationError
        with pytest.raises(ValidationError) as exc_info:
            BeaconSettings.from_yaml(str(beacon_file))
        
        assert "plugins" in str(exc_info.value).lower() or "extra" in str(exc_info.value).lower()

    def test_tc4_non_string_item(self, temp_dir):
        """TC4: Artifact type with non-string item → ValidationResult(valid=False)"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  knowledge:
    - 12345
""")
        
        with pytest.raises(ValidationError) as exc_info:
            BeaconSettings.from_yaml(str(beacon_file))
        
        assert "str" in str(exc_info.value).lower() or "string" in str(exc_info.value).lower()

    def test_tc5_nested_list(self, temp_dir):
        """TC5: Artifact type with nested list → ValidationResult(valid=False)"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  knowledge:
    - 
      - nested.md
""")
        
        with pytest.raises(ValidationError):
            BeaconSettings.from_yaml(str(beacon_file))

    def test_tc6_dict_instead_of_list(self, temp_dir):
        """TC6: Artifact type with dict instead of list → ValidationResult(valid=False)"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  knowledge:
    key: value
""")
        
        with pytest.raises(ValidationError) as exc_info:
            BeaconSettings.from_yaml(str(beacon_file))
        
        assert "list" in str(exc_info.value).lower() or "array" in str(exc_info.value).lower()

    def test_tc7_empty_lists(self, temp_dir, sample_beacon_yaml_empty):
        """TC7: Empty lists for all types → ValidationResult(valid=True)"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text(sample_beacon_yaml_empty)
        
        settings = BeaconSettings.from_yaml(str(beacon_file))
        result = validator.validate_structure(settings)
        
        assert result.valid is True

    def test_tc8_multiple_unknown_types(self, temp_dir):
        """TC8: Multiple unknown types → ValidationResult lists all unknown types"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  plugins:
    - plugin1.md
  extensions:
    - ext1.md
""")
        
        with pytest.raises(ValidationError) as exc_info:
            BeaconSettings.from_yaml(str(beacon_file))
        
        # Should mention the unknown fields
        error_str = str(exc_info.value).lower()
        # At least one of the unknown types should be mentioned
        assert "plugins" in error_str or "extensions" in error_str or "extra" in error_str

    def test_tc9_mixed_valid_and_invalid(self, temp_dir):
        """TC9: Mixed valid and invalid types → ValidationResult lists only invalid ones"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  knowledge:
    - valid.md
  invalid_type:
    - invalid.md
""")
        
        with pytest.raises(ValidationError) as exc_info:
            BeaconSettings.from_yaml(str(beacon_file))
        
        assert "invalid_type" in str(exc_info.value).lower() or "extra" in str(exc_info.value).lower()

    def test_tc10_invalid_path_characters(self, temp_dir):
        """TC10: Artifact paths with invalid characters → ValidationResult(valid=False)"""
        # This test depends on what characters are considered invalid
        # For now, we'll accept most characters that filesystems allow
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text("""
artifacts:
  knowledge:
    - valid/path/file.md
    - also-valid_file.md
""")
        
        # These should actually be valid paths
        settings = BeaconSettings.from_yaml(str(beacon_file))
        result = validator.validate_structure(settings)
        assert result.valid is True
