"""TDD Test Cases for Task 1.2: Create config.toml schema and settings model for warehouse connection

Test Coverage:
- TC1: Valid config.toml with warehouse section → Returns WarehouseSettings with local_path set
- TC2: Valid config with absolute path → local_path is absolute
- TC3: Valid config with relative path → Raises ValidationError "local_path must be absolute"
- TC4: Missing warehouse section → Raises ValidationError "Missing [warehouse] section"
- TC5: Missing local_path key → Raises ValidationError "Missing local_path in [warehouse]"
- TC6: Invalid TOML syntax → Pydantic raises validation error
- TC7: local_path is empty string → Raises ValidationError "local_path cannot be empty"
- TC8: File not found → Pydantic raises validation error (no graceful handling for BaseSettings)
- TC9: local_path is not a string → Raises ValidationError "local_path must be string"
- TC10: Extra unknown keys in config → Ignored gracefully (extra="ignore" in model_config)
"""
import pytest
import os
from pathlib import Path
from beacon.core.settings import WarehouseSettings
from pydantic import ValidationError


class TestConfigTomlParser:
    """Test suite for WarehouseSettings - Task 1.2"""

    def test_tc1_valid_config_with_warehouse_section(self, temp_dir, sample_config_toml_valid):
        """TC1: Valid config.toml with warehouse section → Returns WarehouseSettings with local_path set"""
        config_file = temp_dir / ".agentic-beacon" / "config.toml"
        config_file.parent.mkdir(exist_ok=True)
        config_file.write_text(sample_config_toml_valid)

        # Change to temp_dir to make Pydantic Settings find config.toml
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            settings = WarehouseSettings()
            
            assert isinstance(settings, WarehouseSettings)
            assert settings.warehouse.local_path == "/absolute/path/to/warehouse"
        finally:
            os.chdir(original_cwd)

    def test_tc2_valid_config_absolute_path(self, temp_dir):
        """TC2: Valid config with absolute path → local_path is absolute"""
        config_file = temp_dir / ".agentic-beacon" / "config.toml"
        config_file.parent.mkdir(exist_ok=True)
        config_file.write_text("""
[warehouse]
local_path = "/usr/local/warehouse"
""")

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            settings = WarehouseSettings()
            
            assert settings.warehouse.local_path == "/usr/local/warehouse"
            assert Path(settings.warehouse.local_path).is_absolute()
        finally:
            os.chdir(original_cwd)

    def test_tc3_relative_path_raises_error(self, temp_dir, sample_config_toml_relative):
        """TC3: Valid config with relative path → Raises ValidationError "local_path must be absolute" """
        config_file = temp_dir / ".agentic-beacon" / "config.toml"
        config_file.parent.mkdir(exist_ok=True)
        config_file.write_text(sample_config_toml_relative)

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            
            with pytest.raises(ValidationError) as exc_info:
                WarehouseSettings()
            
            error_str = str(exc_info.value).lower()
            assert "absolute" in error_str or "path" in error_str
        finally:
            os.chdir(original_cwd)

    def test_tc4_missing_warehouse_section(self, temp_dir):
        """TC4: Missing warehouse section → Raises ValidationError "Missing [warehouse] section" """
        config_file = temp_dir / ".agentic-beacon" / "config.toml"
        config_file.parent.mkdir(exist_ok=True)
        config_file.write_text("""
[other_section]
key = "value"
""")

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            
            with pytest.raises(ValidationError) as exc_info:
                WarehouseSettings()
            
            # Pydantic should complain about missing required field
            assert "local_path" in str(exc_info.value).lower() or "required" in str(exc_info.value).lower()
        finally:
            os.chdir(original_cwd)

    def test_tc5_missing_local_path_key(self, temp_dir):
        """TC5: Missing local_path key → Raises ValidationError "Missing local_path in [warehouse]" """
        config_file = temp_dir / ".agentic-beacon" / "config.toml"
        config_file.parent.mkdir(exist_ok=True)
        config_file.write_text("""
[warehouse]
other_key = "value"
""")

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            
            with pytest.raises(ValidationError) as exc_info:
                WarehouseSettings()
            
            assert "local_path" in str(exc_info.value).lower()
        finally:
            os.chdir(original_cwd)

    def test_tc6_invalid_toml_syntax(self, temp_dir):
        """TC6: Invalid TOML syntax → Pydantic raises validation error"""
        config_file = temp_dir / ".agentic-beacon" / "config.toml"
        config_file.parent.mkdir(exist_ok=True)
        config_file.write_text("""
[warehouse
invalid syntax here
""")

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            
            with pytest.raises(Exception):  # Pydantic or TOML parsing error
                WarehouseSettings()
        finally:
            os.chdir(original_cwd)

    def test_tc7_empty_local_path(self, temp_dir):
        """TC7: local_path is empty string → Raises ValidationError "local_path cannot be empty" """
        config_file = temp_dir / ".agentic-beacon" / "config.toml"
        config_file.parent.mkdir(exist_ok=True)
        config_file.write_text("""
[warehouse]
local_path = ""
""")

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            
            with pytest.raises(ValidationError) as exc_info:
                WarehouseSettings()
            
            error_str = str(exc_info.value).lower()
            assert "empty" in error_str or "path" in error_str
        finally:
            os.chdir(original_cwd)

    def test_tc8_config_file_not_found(self, temp_dir):
        """TC8: File not found → Pydantic raises validation error (no graceful handling for BaseSettings)"""
        # No config.toml created
        
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            
            with pytest.raises(ValidationError):
                WarehouseSettings()
        finally:
            os.chdir(original_cwd)

    def test_tc9_local_path_not_string(self, temp_dir):
        """TC9: local_path is not a string → Raises ValidationError "local_path must be string" """
        config_file = temp_dir / ".agentic-beacon" / "config.toml"
        config_file.parent.mkdir(exist_ok=True)
        config_file.write_text("""
[warehouse]
local_path = 12345
""")

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            
            with pytest.raises(ValidationError) as exc_info:
                WarehouseSettings()
            
            error_str = str(exc_info.value).lower()
            assert "string" in error_str or "str" in error_str or "type" in error_str
        finally:
            os.chdir(original_cwd)

    def test_tc10_extra_keys_ignored(self, temp_dir):
        """TC10: Extra unknown keys in config → Ignored gracefully (extra="ignore" in model_config)"""
        config_file = temp_dir / ".agentic-beacon" / "config.toml"
        config_file.parent.mkdir(exist_ok=True)
        config_file.write_text("""
[warehouse]
local_path = "/absolute/path/warehouse"
unknown_key = "should be ignored"
another_unknown = 123
""")

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            settings = WarehouseSettings()
            
            # Should succeed without errors
            assert settings.warehouse.local_path == "/absolute/path/warehouse"
            # Unknown keys should not be accessible
            assert not hasattr(settings, 'unknown_key')
        finally:
            os.chdir(original_cwd)
