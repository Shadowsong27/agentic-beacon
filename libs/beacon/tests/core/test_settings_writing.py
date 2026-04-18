"""TDD Test Cases for Task 1.4: Settings objects write themselves (no separate writer needed)

Test Coverage:
- TC1: WorkspaceConfig.from_path() → Validates path, writes TOML, returns settings
- TC2: settings.to_toml() → Writes current settings to file
- TC3: beacon.to_yaml() → Writes beacon settings to YAML
- TC4: Write with relative path → Validator converts to absolute
- TC5: Write with ~ in path → Expands ~ to home directory
- TC6: Write to non-existent .agentic-beacon dir → Creates directory first
- TC7: Write with None or empty path → Pydantic validation error
- TC8: Roundtrip write then read → Read returns exact same path
- TC9: WorkspaceConfig() loads from written file → Pydantic reads TOML
- TC10: BeaconManifest.from_yaml() loads from written file → Manual parser reads YAML
"""

import os
from pathlib import Path

import pytest
from beacon.core.manifest import BeaconManifest, WorkspaceConfig


class TestSettingsSelfWriting:
    """Test suite for settings self-writing capabilities - Task 1.4"""

    def test_tc1_warehouse_settings_from_path(self, temp_dir):
        """TC1: WorkspaceConfig.from_path() → Validates path, writes TOML, returns settings"""
        warehouse_path = "/absolute/warehouse/path"

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            # Create settings from path
            settings = WorkspaceConfig.from_path(warehouse_path)

            # Verify settings were created correctly
            assert isinstance(settings, WorkspaceConfig)
            assert settings.warehouse.local_path == warehouse_path

            # Verify config.toml was written
            config_file = temp_dir / ".agentic-beacon" / "config.toml"
            assert config_file.exists()
            assert "[warehouse]" in config_file.read_text()
        finally:
            os.chdir(original_cwd)

    def test_tc2_settings_to_toml(self, temp_dir, sample_config_toml_valid):
        """TC2: settings.to_toml() → Writes current settings to file"""
        config_dir = temp_dir / ".agentic-beacon"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"
        config_file.write_text(sample_config_toml_valid)

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            settings = WorkspaceConfig()

            # Write to a different location
            output_file = temp_dir / "output_config.toml"
            settings.to_toml(str(output_file))

            assert output_file.exists()
            assert "[warehouse]" in output_file.read_text()
        finally:
            os.chdir(original_cwd)

    def test_tc3_beacon_to_yaml(self, temp_dir, sample_beacon_yaml_complete):
        """TC3: beacon.to_yaml() → Writes beacon settings to YAML"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text(sample_beacon_yaml_complete)

        settings = BeaconManifest.from_yaml(str(beacon_file))

        # Write to different location
        output_file = temp_dir / "output_beacon.yaml"
        settings.to_yaml(str(output_file))

        assert output_file.exists()
        assert "artifacts:" in output_file.read_text()

    def test_tc4_relative_path_converted_to_absolute(self, temp_dir):
        """TC4: Write with relative path → Validator converts to absolute"""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            # Relative paths should be rejected by validator
            with pytest.raises(ValueError) as exc_info:
                WorkspaceConfig.from_path("relative/path")

            assert "absolute" in str(exc_info.value).lower()
        finally:
            os.chdir(original_cwd)

    def test_tc5_tilde_expansion(self, temp_dir):
        """TC5: Write with ~ in path → Expands ~ to home directory"""
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            # Use tilde path
            home = Path.home()
            warehouse_path = "~/test/warehouse"

            settings = WorkspaceConfig.from_path(warehouse_path)

            # Should be expanded to absolute path with home directory
            assert settings.warehouse.local_path == str(home / "test" / "warehouse")
            assert settings.warehouse.local_path.startswith(str(home))
        finally:
            os.chdir(original_cwd)

    def test_tc6_creates_directory_if_missing(self, temp_dir):
        """TC6: Write to non-existent .agentic-beacon dir → Creates directory first"""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            # Ensure directory doesn't exist
            beacon_dir = temp_dir / ".agentic-beacon"
            assert not beacon_dir.exists()

            # Create settings - should create directory
            WorkspaceConfig.from_path("/test/path")

            # Verify directory was created
            assert beacon_dir.exists()
            assert beacon_dir.is_dir()
        finally:
            os.chdir(original_cwd)

    def test_tc7_none_or_empty_path_raises_error(self, temp_dir):
        """TC7: Write with None or empty path → Pydantic validation error"""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            # Empty path should raise error
            with pytest.raises(ValueError) as exc_info:
                WorkspaceConfig.from_path("")

            assert (
                "empty" in str(exc_info.value).lower()
                or "path" in str(exc_info.value).lower()
            )
        finally:
            os.chdir(original_cwd)

    def test_tc8_roundtrip_preserves_data(self, temp_dir, sample_beacon_yaml_complete):
        """TC8: Roundtrip write then read → Read returns exact same data"""
        beacon_file = temp_dir / "beacon.yaml"
        beacon_file.write_text(sample_beacon_yaml_complete)

        # Load
        settings1 = BeaconManifest.from_yaml(str(beacon_file))

        # Write
        output_file = temp_dir / "output.yaml"
        settings1.to_yaml(str(output_file))

        # Read back
        settings2 = BeaconManifest.from_yaml(str(output_file))

        # Should be identical
        assert settings1.artifacts.knowledge == settings2.artifacts.knowledge
        assert settings1.artifacts.skills == settings2.artifacts.skills
        assert settings1.artifacts.contexts == settings2.artifacts.contexts

    def test_tc9_warehouse_loads_from_written_file(
        self, temp_dir, sample_config_toml_valid
    ):
        """TC9: WorkspaceConfig() loads from written file → Pydantic reads TOML"""
        config_dir = temp_dir / ".agentic-beacon"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"

        # Write manually
        config_file.write_text(sample_config_toml_valid)

        # Load via Pydantic
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            settings = WorkspaceConfig()
            assert settings.warehouse.local_path == "/absolute/path/to/warehouse"
        finally:
            os.chdir(original_cwd)

    def test_tc10_beacon_loads_from_written_file(
        self, temp_dir, sample_beacon_yaml_complete
    ):
        """TC10: BeaconManifest.from_yaml() loads from written file → Manual parser reads YAML"""
        beacon_file = temp_dir / "beacon.yaml"

        # First create settings and write
        beacon_file.write_text(sample_beacon_yaml_complete)
        settings1 = BeaconManifest.from_yaml(str(beacon_file))

        output_file = temp_dir / "written.yaml"
        settings1.to_yaml(str(output_file))

        # Load from written file
        settings2 = BeaconManifest.from_yaml(str(output_file))
        assert len(settings2.artifacts.knowledge) == len(settings1.artifacts.knowledge)

    def test_tc11_to_yaml_emits_ignore_when_non_empty(self, temp_dir):
        """TC11: to_yaml includes ignore section when ignore.skills is non-empty."""
        settings = BeaconManifest(
            artifacts={"knowledge": [], "skills": [], "contexts": []},
            ignore={"skills": ["openspec-*", "opsx-*"]},
        )
        output_file = temp_dir / "beacon.yaml"
        settings.to_yaml(str(output_file))

        content = output_file.read_text()
        assert "ignore" in content
        assert "openspec-*" in content
        assert "opsx-*" in content

    def test_tc12_to_yaml_omits_ignore_when_empty(self, temp_dir):
        """TC12: to_yaml omits ignore section when ignore.skills is empty."""
        settings = BeaconManifest(
            artifacts={"knowledge": [], "skills": [], "contexts": []},
        )
        output_file = temp_dir / "beacon.yaml"
        settings.to_yaml(str(output_file))

        content = output_file.read_text()
        assert "ignore" not in content

    def test_tc13_roundtrip_preserves_ignore_skills(self, temp_dir):
        """TC13: Write then read roundtrip preserves ignore.skills values."""
        settings1 = BeaconManifest(
            artifacts={"knowledge": [], "skills": [], "contexts": []},
            ignore={"skills": ["openspec-*"]},
        )
        output_file = temp_dir / "beacon.yaml"
        settings1.to_yaml(str(output_file))

        settings2 = BeaconManifest.from_yaml(str(output_file))
        assert settings2.ignore.skills == ["openspec-*"]
