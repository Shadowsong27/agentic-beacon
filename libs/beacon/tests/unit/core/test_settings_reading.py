"""TDD Test Cases for Task 1.3: Settings objects read themselves (no separate reader needed)

Test Coverage:
- TC1: WorkspaceConfig() → Pydantic loads from config.toml automatically
- TC2: BeaconManifest.from_yaml() → Manually parses YAML with validation
- TC3: config.toml missing → Pydantic raises validation error
- TC4: beacon.yaml missing → FileNotFoundError from from_yaml()
- TC5: Invalid TOML → Pydantic validation error
- TC6: Invalid YAML → YAMLParseError from from_yaml()
- TC7: .agentic-beacon directory doesn't exist → DirectoryNotFoundError from validate_beacon_directory()
- TC8: Files exist but unreadable → PermissionError
- TC9: Load called multiple times → Idempotent behavior
- TC10: Settings objects are independent → Can load one without the other
"""

import os

import pytest
from beacon.core.exceptions import ValidationError as BeaconValidationError
from beacon.core.exceptions import YAMLParseError
from beacon.core.manifest.beacon import BeaconManifest
from beacon.core.manifest.workspace import WorkspaceConfig
from pydantic_core import ValidationError as PydanticValidationError


class TestSettingsSelfReading:
    """Test suite for settings self-reading capabilities - Task 1.3"""

    def test_tc1_warehouse_settings_auto_loads_toml(
        self, temp_dir, sample_config_toml_valid
    ):
        """TC1: WorkspaceConfig() → Pydantic loads from config.toml automatically"""
        config_file = temp_dir / ".agentic-beacon" / "config.toml"
        config_file.parent.mkdir(exist_ok=True)
        config_file.write_text(sample_config_toml_valid)

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            settings = WorkspaceConfig()

            assert isinstance(settings, WorkspaceConfig)
            assert settings.warehouse.local_path == "/absolute/path/to/warehouse"
        finally:
            os.chdir(original_cwd)

    def test_tc2_beacon_settings_manually_parses_yaml(
        self, temp_dir, sample_beacon_yaml_complete
    ):
        """TC2: BeaconManifest.from_yaml() → Manually parses YAML with validation"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text(sample_beacon_yaml_complete)

        settings = BeaconManifest.from_yaml(str(beacon_file))

        assert isinstance(settings, BeaconManifest)
        assert len(settings.artifacts.knowledge) > 0

    def test_tc3_config_missing_raises_error(self, temp_dir):
        """TC3: config.toml missing → Pydantic raises validation error"""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            with pytest.raises((BeaconValidationError, PydanticValidationError)):
                WorkspaceConfig()
        finally:
            os.chdir(original_cwd)

    def test_tc4_beacon_yaml_missing_raises_error(self, temp_dir):
        """TC4: beacon.yaml missing → FileNotFoundError from from_yaml()"""
        non_existent = temp_dir / "missing.yaml"

        with pytest.raises(FileNotFoundError):
            BeaconManifest.from_yaml(str(non_existent))

    def test_tc5_invalid_toml_raises_error(self, temp_dir):
        """TC5: Invalid TOML → Pydantic validation error"""
        config_file = temp_dir / ".agentic-beacon" / "config.toml"
        config_file.parent.mkdir(exist_ok=True)
        config_file.write_text("[warehouse\ninvalid")

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            with pytest.raises(Exception):  # noqa: B017  # TOML parse or validation error
                WorkspaceConfig()
        finally:
            os.chdir(original_cwd)

    def test_tc6_invalid_yaml_raises_error(self, temp_dir):
        """TC6: Invalid YAML → YAMLParseError from from_yaml()"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text("artifacts:\n  - invalid:\nbroken")

        with pytest.raises((YAMLParseError, BeaconValidationError)):
            BeaconManifest.from_yaml(str(beacon_file))

    def test_tc7_beacon_directory_missing(self, temp_dir):
        """TC7: .agentic-beacon directory doesn't exist → Appropriate error"""
        # This will be tested more thoroughly in test_directory_validation.py
        # Here we just verify the behavior when directory is missing
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            # Should not be able to create WarehouseSettings without .agentic-beacon/
            with pytest.raises((BeaconValidationError, PydanticValidationError)):
                WorkspaceConfig()
        finally:
            os.chdir(original_cwd)

    def test_tc8_files_unreadable(self, temp_dir, sample_beacon_yaml_complete):
        """TC8: Files exist but unreadable → PermissionError"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text(sample_beacon_yaml_complete)
        beacon_file.chmod(0o000)

        try:
            with pytest.raises(PermissionError):
                BeaconManifest.from_yaml(str(beacon_file))
        finally:
            beacon_file.chmod(0o644)

    def test_tc9_idempotent_loading(self, temp_dir, sample_beacon_yaml_complete):
        """TC9: Load called multiple times → Idempotent behavior"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text(sample_beacon_yaml_complete)

        settings1 = BeaconManifest.from_yaml(str(beacon_file))
        settings2 = BeaconManifest.from_yaml(str(beacon_file))

        # Should produce identical results
        assert settings1.artifacts.knowledge == settings2.artifacts.knowledge
        assert settings1.artifacts.skills == settings2.artifacts.skills
        assert settings1.artifacts.contexts == settings2.artifacts.contexts

    def test_tc10_settings_are_independent(
        self, temp_dir, sample_beacon_yaml_complete, sample_config_toml_valid
    ):
        """TC10: Settings objects are independent → Can load one without the other"""
        # Create only beacon.yaml
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text(sample_beacon_yaml_complete)

        # Should be able to load beacon without config
        beacon_settings = BeaconManifest.from_yaml(str(beacon_file))
        assert isinstance(beacon_settings, BeaconManifest)

        # Create config.toml
        config_file = temp_dir / ".agentic-beacon" / "config.toml"
        config_file.parent.mkdir(exist_ok=True)
        config_file.write_text(sample_config_toml_valid)

        # Should be able to load warehouse settings independently
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            warehouse_settings = WorkspaceConfig()
            assert isinstance(warehouse_settings, WorkspaceConfig)
        finally:
            os.chdir(original_cwd)
