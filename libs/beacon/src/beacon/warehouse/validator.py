"""Warehouse structure validation for Agentic Beacon.

This module provides validation for warehouse directory structures to ensure they
meet the required format before being connected to a project.
"""

from pathlib import Path

from beacon.core.manifest import ValidationResult


class WarehouseValidator:
    """Validates warehouse directory structure.

    A valid warehouse must contain:
    - Required directories: contexts/, knowledge/, skills/, docs/
    - Required file: README.md
    """

    REQUIRED_DIRECTORIES = [
        "agents",
        "contexts",
        "knowledge",
        "skills",
        "docs",
    ]

    REQUIRED_FILES: list[str] = []

    OPTIONAL_FILES = [
        "README.md",
        "README",
        "README.txt",
    ]

    def validate(self, path: str | Path) -> ValidationResult:
        """Validate a warehouse directory structure.

        Args:
            path: Path to the warehouse directory

        Returns:
            ValidationResult with validation status and any errors
        """
        errors = []

        # Resolve path (handle ~, .., relative paths)
        try:
            warehouse_path = Path(path).expanduser().resolve()
        except Exception as e:
            return ValidationResult(valid=False, errors=[f"Invalid path: {e}"])

        # Check if path exists
        if not warehouse_path.exists():
            return ValidationResult(
                valid=False, errors=[f"Path not found: {warehouse_path}"]
            )

        # Check if path is a directory
        if not warehouse_path.is_dir():
            return ValidationResult(
                valid=False, errors=[f"Path is not a directory: {warehouse_path}"]
            )

        # Check for .agentic-beacon/artifacts/ (indicates this is a project, not a warehouse)
        if (warehouse_path / ".agentic-beacon" / "artifacts").exists():
            return ValidationResult(
                valid=False,
                errors=[
                    "This appears to be a project directory, not a warehouse. "
                    "Warehouse should not contain .agentic-beacon/artifacts/"
                ],
            )

        # Validate required directories
        for required_dir in self.REQUIRED_DIRECTORIES:
            dir_path = warehouse_path / required_dir
            if not dir_path.exists():
                if required_dir == "agents":
                    errors.append(
                        "Missing required directory: agents/ "
                        "(run 'mkdir agents/' in your warehouse to upgrade)"
                    )
                else:
                    errors.append(f"Missing required directory: {required_dir}/")
            elif not dir_path.is_dir():
                errors.append(f"Expected directory, found file: {required_dir}")

        # Validate required files
        for required_file in self.REQUIRED_FILES:
            file_path = warehouse_path / required_file
            if not file_path.exists():
                errors.append(f"Missing required file: {required_file}")
            elif not file_path.is_file():
                errors.append(f"Expected file, found directory: {required_file}")

        # Check for at least one README variant
        has_readme = any(
            (warehouse_path / readme_file).is_file()
            for readme_file in self.OPTIONAL_FILES
        )
        if not has_readme:
            errors.append(
                f"Missing README file (expected one of: {', '.join(self.OPTIONAL_FILES)})"
            )

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    def resolve_path(self, path: str | Path) -> Path:
        """Resolve a path to absolute form, handling ~, .., and symlinks.

        Args:
            path: Path to resolve

        Returns:
            Resolved absolute path

        Raises:
            ValueError: If path is empty
        """
        if not path:
            raise ValueError("Path cannot be empty")

        return Path(path).expanduser().resolve()
