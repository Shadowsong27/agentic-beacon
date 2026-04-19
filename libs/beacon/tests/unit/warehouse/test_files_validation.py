"""Tests for warehouse file validation.

Test Coverage:
- TC1: All required directories + README present → ValidationResult(valid=True)
- TC2: No markdown file in contexts/ → Still valid (no file naming enforced)
- TC3: contexts/ contains a directory named AGENTS.global.md → Still valid
- TC4: Any markdown file in contexts/ → Passes validation
- TC5: contexts/ file unreadable (permissions) → Validation passes (existence only)
- TC6: README.md present in root → Passes validation
- TC7: README.md missing → ValidationResult includes missing README
- TC8: Multiple README variants (README, README.txt) → At least one present passes
- TC9: All directories present, no README → Lists missing README only
- TC10: Symlink to required file → Follows symlink and validates target exists
"""

from pathlib import Path

import pytest
from beacon.domains.warehouse.validator import WarehouseValidator


def _make_valid_dirs(warehouse: Path) -> None:
    """Create all required directories for a valid warehouse."""
    (warehouse / "agents").mkdir(parents=True, exist_ok=True)
    (warehouse / "contexts").mkdir(parents=True, exist_ok=True)
    (warehouse / "knowledge").mkdir(parents=True, exist_ok=True)
    (warehouse / "skills").mkdir(parents=True, exist_ok=True)
    (warehouse / "docs").mkdir(parents=True, exist_ok=True)


class TestWarehouseFilesValidation:
    """Test suite for warehouse required files validation - Task 2.3"""

    def test_tc1_all_required_files_present(self, temp_dir):
        """TC1: All required files present → ValidationResult(valid=True)"""
        warehouse = temp_dir / "warehouse"
        _make_valid_dirs(warehouse)
        (warehouse / "knowledge" / "global").mkdir(parents=True)
        (warehouse / "contexts" / "AGENTS.global.md").write_text("# Global Context")
        (warehouse / "README.md").write_text("# Warehouse")

        validator = WarehouseValidator()
        result = validator.validate(str(warehouse))

        assert result.valid is True
        assert len(result.errors) == 0

    def test_tc2_no_markdown_in_contexts_still_valid(self, temp_dir):
        """TC2: No markdown file in contexts/ → Still valid (no file naming enforced)"""
        warehouse = temp_dir / "warehouse"
        _make_valid_dirs(warehouse)
        (warehouse / "README.md").write_text("# Warehouse")
        # contexts/ is empty — that's fine

        validator = WarehouseValidator()
        result = validator.validate(str(warehouse))

        assert result.valid is True

    def test_tc3_directory_named_agents_in_contexts_still_valid(self, temp_dir):
        """TC3: contexts/ contains a directory named AGENTS.global.md → Still valid (no naming enforced)"""
        warehouse = temp_dir / "warehouse"
        _make_valid_dirs(warehouse)
        (warehouse / "README.md").write_text("# Warehouse")
        # Create AGENTS.global.md as a directory — should still pass since we don't enforce it
        (warehouse / "contexts" / "AGENTS.global.md").mkdir()

        validator = WarehouseValidator()
        result = validator.validate(str(warehouse))

        assert result.valid is True

    def test_tc4_any_markdown_in_contexts_passes(self, temp_dir):
        """TC4: Any markdown file in contexts/ → Passes validation"""
        warehouse = temp_dir / "warehouse"
        _make_valid_dirs(warehouse)
        (warehouse / "contexts" / "AGENTS.md").write_text("")  # any filename is fine
        (warehouse / "README.md").write_text("# Warehouse")

        validator = WarehouseValidator()
        result = validator.validate(str(warehouse))

        assert result.valid is True

    @pytest.mark.skipif(not hasattr(Path, "chmod"), reason="chmod not available")
    def test_tc5_context_file_unreadable_still_valid(self, temp_dir):
        """TC5: A context file is unreadable → Validation still passes (existence only)"""
        warehouse = temp_dir / "warehouse"
        _make_valid_dirs(warehouse)
        agents_file = warehouse / "contexts" / "AGENTS.md"
        agents_file.write_text("# Context")
        (warehouse / "README.md").write_text("# Warehouse")

        agents_file.chmod(0o000)

        try:
            validator = WarehouseValidator()
            result = validator.validate(str(warehouse))
            # Validation only checks existence of directories and README, not file readability
            assert result.valid is True
        finally:
            agents_file.chmod(0o644)

    def test_tc6_readme_present(self, temp_dir):
        """TC6: README.md present in root → Passes validation"""
        warehouse = temp_dir / "warehouse"
        _make_valid_dirs(warehouse)
        (warehouse / "README.md").write_text("# Warehouse")

        validator = WarehouseValidator()
        result = validator.validate(str(warehouse))

        assert result.valid is True

    def test_tc7_readme_missing(self, temp_dir):
        """TC7: README.md missing → ValidationResult includes missing README"""
        warehouse = temp_dir / "warehouse"
        _make_valid_dirs(warehouse)
        # README deliberately not created

        validator = WarehouseValidator()
        result = validator.validate(str(warehouse))

        assert result.valid is False
        assert any("README" in err.upper() for err in result.errors)

    def test_tc8_multiple_readme_variants(self, temp_dir):
        """TC8: Multiple README variants (README, README.txt) → At least one present passes"""
        warehouse = temp_dir / "warehouse"
        _make_valid_dirs(warehouse)
        # Use README.txt instead of README.md
        (warehouse / "README.txt").write_text("Warehouse")

        validator = WarehouseValidator()
        result = validator.validate(str(warehouse))

        assert result.valid is True

    def test_tc9_all_dirs_present_no_readme(self, temp_dir):
        """TC9: All directories present but no README → Lists only missing README"""
        warehouse = temp_dir / "warehouse"
        _make_valid_dirs(warehouse)
        # No README created

        validator = WarehouseValidator()
        result = validator.validate(str(warehouse))

        assert result.valid is False
        assert any("README" in err.upper() for err in result.errors)
        # No errors about AGENTS.global.md — that is not enforced
        assert not any("AGENTS.global.md" in err for err in result.errors)

    @pytest.mark.skipif(
        not hasattr(Path, "symlink_to"), reason="symlinks not supported"
    )
    def test_tc10_symlink_to_readme(self, temp_dir):
        """TC10: Symlink to README → Follows symlink and validates target exists"""
        warehouse = temp_dir / "warehouse"
        _make_valid_dirs(warehouse)

        # Create actual README elsewhere
        actual_readme = temp_dir / "actual_readme.md"
        actual_readme.write_text("# Warehouse")

        # Create symlink for README
        symlink = warehouse / "README.md"
        try:
            symlink.symlink_to(actual_readme)

            validator = WarehouseValidator()
            result = validator.validate(str(warehouse))

            assert result.valid is True
        except OSError:
            pytest.skip("Cannot create symlinks in this environment")
