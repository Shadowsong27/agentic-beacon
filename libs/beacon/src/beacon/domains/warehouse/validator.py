"""Warehouse structure validation for the warehouse domain."""

from pathlib import Path

from beacon.core.dependencies.manifest import (
    AgentManifestError,
    load_agent_manifest,
    validate_agent_frontmatter_clean,
    validate_agents_directory,
    validate_declared_skills,
)
from beacon.core.manifest.beacon import ValidationResult


class WarehouseValidator:
    """Validates warehouse directory structure.

    A valid warehouse must contain:
    - Required directories: agents/, contexts/, skills/, docs/
    - Required file: README.md
    """

    REQUIRED_DIRECTORIES = [
        "agents",
        "contexts",
        "skills",
        "docs",
    ]

    REQUIRED_FILES: list[str] = []

    OPTIONAL_FILES = [
        "README.md",
        "README",
        "README.txt",
    ]

    def validate(
        self, path: str | Path, *, validate_manifest: bool = True
    ) -> ValidationResult:
        """Validate a warehouse directory structure.

        Args:
            path: Path to the warehouse directory
            validate_manifest: When True (default), also runs agent manifest
                validators (load_agent_manifest, validate_agents_directory,
                validate_agent_frontmatter_clean, validate_declared_skills) and
                rolls any failures into the result. When False, runs only the
                structural checks (required directories, README, project-vs-
                warehouse detection). Callers that have their own dedicated
                manifest-validation pass — notably `abc warehouse lint` —
                should pass False to avoid duplicate findings.

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

        # Agent manifest validation (only when agents/ has content).
        # Skipped when validate_manifest=False — callers like `abc warehouse
        # lint` run their own per-defect manifest validation pass and would
        # otherwise see duplicate findings (one combined here + N per-defect).
        if validate_manifest:
            agents_dir = warehouse_path / "agents"
            if agents_dir.exists() and agents_dir.is_dir():
                has_agent_files = any(
                    f.is_file() and f.suffix == ".md" and f.name != "README.md"
                    for f in agents_dir.iterdir()
                )
                if has_agent_files:
                    try:
                        manifest = load_agent_manifest(warehouse_path)
                        validate_agents_directory(warehouse_path, manifest)
                        validate_agent_frontmatter_clean(warehouse_path)
                        if manifest is not None:
                            validate_declared_skills(warehouse_path, manifest)
                    except AgentManifestError as exc:
                        errors.append(str(exc))

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
