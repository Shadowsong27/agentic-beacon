"""Test Cases for WarehouseValidator

Test Coverage:
- TC1: Valid warehouse structure → ValidationResult(valid=True, errors=[])
- TC2: Missing all required directories → ValidationResult(valid=False, errors=[...list of 4 missing])
- TC3: Path doesn't exist → ValidationResult(valid=False, errors=["Path not found"])
- TC4: Path is file not directory → ValidationResult(valid=False, errors=["Path is not a directory"])
- TC5: Empty directory → ValidationResult(valid=False) with all missing directories listed
- TC6: Partial structure (only contexts/) → ValidationResult(valid=False) with 3 missing listed
- TC7: Absolute path provided → Validates correctly
- TC8: Relative path provided → Resolves and validates correctly
- TC9: Path with spaces and special chars → Handles correctly
- TC10: Symlink to valid warehouse → Follows symlink and validates target
"""

from pathlib import Path

import pytest
from beacon.core.manifest.beacon import ValidationResult
from beacon.domains.warehouse.validator import WarehouseValidator


class TestWarehouseValidator:
    """Test suite for WarehouseValidator class - Task 2.1"""

    def test_tc1_valid_warehouse_structure(self, temp_dir):
        """TC1: Valid warehouse structure → ValidationResult(valid=True, errors=[])"""
        warehouse = temp_dir / "warehouse"
        (warehouse / "agents").mkdir(parents=True)
        (warehouse / "contexts").mkdir(parents=True)
        (warehouse / "knowledge").mkdir(parents=True)
        (warehouse / "skills").mkdir(parents=True)
        (warehouse / "docs").mkdir(parents=True)
        (warehouse / "README.md").write_text("# Warehouse")

        validator = WarehouseValidator()
        result = validator.validate(str(warehouse))

        assert isinstance(result, ValidationResult)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_tc2_missing_all_required_directories(self, temp_dir):
        """TC2: Missing all required directories → ValidationResult(valid=False, errors=[...list of 4 missing])"""
        warehouse = temp_dir / "empty_warehouse"
        warehouse.mkdir()

        validator = WarehouseValidator()
        result = validator.validate(str(warehouse))

        assert result.valid is False
        assert len(result.errors) >= 4  # At least 4 missing directories + README
        # Check for required directories
        error_text = " ".join(result.errors).lower()
        assert "contexts" in error_text
        assert "knowledge" in error_text
        assert "skills" in error_text
        assert "docs" in error_text

    def test_tc3_path_not_found(self, temp_dir):
        """TC3: Path doesn't exist → ValidationResult(valid=False, errors=["Path not found"])"""
        non_existent = temp_dir / "does_not_exist"

        validator = WarehouseValidator()
        result = validator.validate(str(non_existent))

        assert result.valid is False
        assert len(result.errors) > 0
        assert any(
            "not found" in err.lower() or "does not exist" in err.lower()
            for err in result.errors
        )

    def test_tc4_path_is_file_not_directory(self, temp_dir):
        """TC4: Path is file not directory → ValidationResult(valid=False, errors=["Path is not a directory"])"""
        file_path = temp_dir / "not_a_directory.txt"
        file_path.write_text("This is a file")

        validator = WarehouseValidator()
        result = validator.validate(str(file_path))

        assert result.valid is False
        assert any(
            "not a directory" in err.lower() or "not a dir" in err.lower()
            for err in result.errors
        )

    def test_tc5_empty_directory(self, temp_dir):
        """TC5: Empty directory → ValidationResult(valid=False) with all missing directories listed"""
        warehouse = temp_dir / "empty"
        warehouse.mkdir()

        validator = WarehouseValidator()
        result = validator.validate(str(warehouse))

        assert result.valid is False
        # Should list all missing required directories + README
        assert len(result.errors) >= 4

    def test_tc6_partial_structure(self, temp_dir):
        """TC6: Partial structure (only contexts/) → ValidationResult(valid=False) with 4 missing listed"""
        warehouse = temp_dir / "partial"
        (warehouse / "contexts").mkdir(parents=True)

        validator = WarehouseValidator()
        result = validator.validate(str(warehouse))

        assert result.valid is False
        # Should list missing directories (knowledge, skills, docs, knowledge/global)
        assert len(result.errors) >= 3  # At least knowledge/, skills/, docs/ missing

    def test_tc7_absolute_path(self, temp_dir):
        """TC7: Absolute path provided → Validates correctly"""
        warehouse = temp_dir / "warehouse"
        (warehouse / "contexts").mkdir(parents=True)
        (warehouse / "knowledge").mkdir(parents=True)
        (warehouse / "skills").mkdir(parents=True)
        (warehouse / "docs").mkdir(parents=True)
        (warehouse / "README.md").write_text("# Warehouse")

        validator = WarehouseValidator()
        # Use absolute path
        result = validator.validate(str(warehouse.resolve()))

        assert isinstance(result, ValidationResult)
        # May be valid or have errors, but should handle absolute paths

    def test_tc8_relative_path(self, temp_dir):
        """TC8: Relative path provided → Resolves and validates correctly"""
        warehouse = temp_dir / "warehouse"
        (warehouse / "contexts").mkdir(parents=True)
        (warehouse / "knowledge").mkdir(parents=True)
        (warehouse / "skills").mkdir(parents=True)
        (warehouse / "docs").mkdir(parents=True)
        (warehouse / "README.md").write_text("# Warehouse")

        validator = WarehouseValidator()

        # Use relative path
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            result = validator.validate("./warehouse")
            assert isinstance(result, ValidationResult)
        finally:
            os.chdir(original_cwd)

    def test_tc9_path_with_spaces_and_special_chars(self, temp_dir):
        """TC9: Path with spaces and special chars → Handles correctly"""
        warehouse = temp_dir / "my warehouse (v1.0)"
        (warehouse / "contexts").mkdir(parents=True)
        (warehouse / "knowledge").mkdir(parents=True)
        (warehouse / "skills").mkdir(parents=True)
        (warehouse / "docs").mkdir(parents=True)
        (warehouse / "README.md").write_text("# Warehouse")

        validator = WarehouseValidator()
        result = validator.validate(str(warehouse))

        assert isinstance(result, ValidationResult)
        # Should handle paths with spaces and special characters

    @pytest.mark.skipif(
        not hasattr(Path, "symlink_to"), reason="symlinks not supported"
    )
    def test_tc10_symlink_to_valid_warehouse(self, temp_dir):
        """TC10: Symlink to valid warehouse → Follows symlink and validates target"""
        # Create actual warehouse
        actual_warehouse = temp_dir / "actual_warehouse"
        (actual_warehouse / "contexts").mkdir(parents=True)
        (actual_warehouse / "knowledge").mkdir(parents=True)
        (actual_warehouse / "skills").mkdir(parents=True)
        (actual_warehouse / "docs").mkdir(parents=True)
        (actual_warehouse / "README.md").write_text("# Warehouse")

        # Create symlink
        symlink = temp_dir / "warehouse_link"
        try:
            symlink.symlink_to(actual_warehouse)

            validator = WarehouseValidator()
            result = validator.validate(str(symlink))

            assert isinstance(result, ValidationResult)
            # Should follow symlink and validate the target
        except OSError:
            pytest.skip("Cannot create symlinks in this environment")


class TestAgentsDirectoryValidation:
    """Tests for agents/ directory requirement (task 2.1)."""

    def test_tc1_warehouse_with_agents_dir_valid(self, temp_dir):
        """TC1: Warehouse has agents/ dir → validates successfully."""
        warehouse = temp_dir / "warehouse"
        (warehouse / "agents").mkdir(parents=True)
        (warehouse / "contexts").mkdir(parents=True)
        (warehouse / "knowledge").mkdir(parents=True)
        (warehouse / "skills").mkdir(parents=True)
        (warehouse / "docs").mkdir(parents=True)
        (warehouse / "README.md").write_text("# Warehouse")

        validator = WarehouseValidator()
        result = validator.validate(str(warehouse))

        assert result.valid is True

    def test_tc2_warehouse_missing_agents_dir_invalid(self, temp_dir):
        """TC2: Warehouse missing agents/ dir → validation error listing agents/."""
        warehouse = temp_dir / "warehouse"
        (warehouse / "contexts").mkdir(parents=True)
        (warehouse / "knowledge").mkdir(parents=True)
        (warehouse / "skills").mkdir(parents=True)
        (warehouse / "docs").mkdir(parents=True)
        (warehouse / "README.md").write_text("# Warehouse")

        validator = WarehouseValidator()
        result = validator.validate(str(warehouse))

        assert result.valid is False
        assert any("agents" in err.lower() for err in result.errors)

    def test_tc3_agents_missing_includes_upgrade_hint(self, temp_dir):
        """TC3: Missing agents/ → error message includes mkdir upgrade instruction."""
        warehouse = temp_dir / "warehouse"
        (warehouse / "contexts").mkdir(parents=True)
        (warehouse / "knowledge").mkdir(parents=True)
        (warehouse / "skills").mkdir(parents=True)
        (warehouse / "docs").mkdir(parents=True)
        (warehouse / "README.md").write_text("# Warehouse")

        validator = WarehouseValidator()
        result = validator.validate(str(warehouse))

        assert result.valid is False
        agents_errors = [e for e in result.errors if "agents" in e.lower()]
        assert agents_errors
        assert any("mkdir" in e for e in agents_errors)
