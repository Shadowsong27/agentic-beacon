"""Settings management for Agentic Beacon.

This module handles configuration for:
- beacon.yaml: Artifact dependencies (committed to git)
- config.toml: Warehouse connection (gitignored)

Uses Pydantic Settings for type-safe configuration.
"""

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

from .exceptions import (
    DirectoryNotFoundError,
    ValidationError,
    YAMLParseError,
)

# ========== Beacon.yaml Settings Models ==========


class ArtifactsConfig(BaseModel):
    """Artifacts configuration from beacon.yaml."""

    knowledge: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    contexts: list[str] = Field(default_factory=list)


class IgnoreConfig(BaseModel):
    """Patterns to ignore in contribute and delta commands.

    Supports fnmatch glob patterns, e.g. ``openspec-*``.
    """

    skills: list[str] = Field(default_factory=list)


class BeaconSettings(BaseModel):
    """Beacon.yaml settings structure.

    This is not a BaseSettings subclass because beacon.yaml has a custom structure
    that requires manual parsing and validation.
    """

    artifacts: ArtifactsConfig = Field(default_factory=ArtifactsConfig)
    ignore: IgnoreConfig = Field(default_factory=IgnoreConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "BeaconSettings":
        """Load beacon settings from YAML file.

        Args:
            path: Path to beacon.yaml file

        Returns:
            BeaconSettings object with parsed configuration

        Raises:
            FileNotFoundError: If file doesn't exist
            IsADirectoryError: If path is a directory
            PermissionError: If file cannot be read
            YAMLParseError: If YAML syntax is invalid
            ValidationError: If structure is invalid
        """
        path = Path(path)

        # File existence and type checks
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        if path.is_dir():
            raise IsADirectoryError(f"Expected file, found directory: {path}")

        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except PermissionError as e:
            raise PermissionError(f"Cannot read file {path}: {e}") from e
        except yaml.YAMLError as e:
            raise YAMLParseError(f"Invalid YAML syntax in {path}: {e}") from e

        # Handle empty or null file
        if data is None:
            data = {}

        # Validate structure
        if not isinstance(data, dict):
            raise ValidationError("Configuration must be a YAML object (dict)")

        if "artifacts" not in data:
            raise ValidationError("Missing required 'artifacts' section")

        artifacts_data = data.get("artifacts", {})
        if not isinstance(artifacts_data, dict):
            raise ValidationError("'artifacts' section must be a YAML object (dict)")

        # Validate artifact types and structure
        valid_types = {"knowledge", "skills", "contexts"}
        for artifact_type, items in artifacts_data.items():
            if artifact_type not in valid_types:
                raise ValidationError(
                    f"Unknown artifact type: {artifact_type}. "
                    f"Valid types: {', '.join(sorted(valid_types))}"
                )

            if not isinstance(items, list):
                raise ValidationError(
                    f"Artifact type '{artifact_type}' must be a list, got {type(items).__name__}"
                )

            for i, item in enumerate(items):
                if not isinstance(item, str):
                    raise ValidationError(
                        f"All items in '{artifact_type}' must be strings, "
                        f"got {type(item).__name__} at index {i}"
                    )

        # Create settings using Pydantic validation
        try:
            return cls(**data)
        except Exception as e:
            raise ValidationError(f"Configuration validation failed: {e}") from e

    def to_yaml(self, path: str | Path) -> None:
        """Write beacon settings to YAML file.

        Args:
            path: Path to write beacon.yaml

        Raises:
            PermissionError: If cannot write to path
        """
        path = Path(path)

        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Create beacon config structure
        config_dict: dict = {"artifacts": self.artifacts.model_dump()}
        if self.ignore.skills:
            config_dict["ignore"] = self.ignore.model_dump()

        try:
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
        except PermissionError as e:
            raise PermissionError(
                f"Cannot write to {path}: insufficient permissions"
            ) from e


class ValidationResult(BaseModel):
    """Result of configuration validation."""

    valid: bool
    errors: list[str] = Field(default_factory=list)


class BeaconYamlValidator:
    """Validator for beacon.yaml structure and content."""

    VALID_ARTIFACT_TYPES = {"knowledge", "skills", "contexts"}

    def validate_structure(self, beacon_settings: BeaconSettings) -> ValidationResult:
        """Validate beacon.yaml structure.

        Args:
            beacon_settings: Parsed beacon settings

        Returns:
            ValidationResult with validation status and any errors
        """
        errors = []

        artifacts = beacon_settings.artifacts
        artifacts_dict = artifacts.model_dump()

        # Check for unknown artifact types (defensive check, parser already validates this)
        for artifact_type in artifacts_dict.keys():
            if artifact_type not in self.VALID_ARTIFACT_TYPES:
                errors.append(f"Unknown artifact type: {artifact_type}")

        # Validate each artifact type contains list of strings
        for artifact_type, items in artifacts_dict.items():
            if not isinstance(items, list):
                errors.append(f"Artifact type '{artifact_type}' must be a list")
                continue

            for i, item in enumerate(items):
                if not isinstance(item, str):
                    errors.append(
                        f"All items in '{artifact_type}' must be strings, "
                        f"got {type(item).__name__} at index {i}"
                    )
                elif not item.strip():
                    errors.append(
                        f"Empty string found in '{artifact_type}' at index {i}"
                    )

        return ValidationResult(valid=len(errors) == 0, errors=errors)


# ========== Config.toml Settings Models ==========


class WarehouseConfig(BaseModel):
    """Warehouse configuration section."""

    local_path: str = Field(..., description="Absolute path to local warehouse")

    @field_validator("local_path")
    @classmethod
    def validate_local_path(cls, v: str) -> str:
        """Validate local_path is not empty and is absolute."""
        if not v or not v.strip():
            raise ValueError("local_path cannot be empty")

        path = Path(v).expanduser()
        if not path.is_absolute():
            raise ValueError("local_path must be an absolute path")

        return str(path)


class WarehouseSettings(BaseSettings):
    """Warehouse connection settings from config.toml.

    Uses Pydantic Settings with TOML file support for type-safe configuration.
    This class acts as both the settings container and the reader.

    Note: The warehouse field is loaded automatically from config.toml via
    Pydantic Settings. When instantiating without arguments, the TOML file
    is read and the field is populated. Type checkers may show a warning
    about missing required field, but this is expected behavior for BaseSettings.
    """

    model_config = SettingsConfigDict(
        toml_file=".agentic-beacon/config.toml",
        extra="ignore",
    )

    warehouse: WarehouseConfig  # Populated automatically from TOML file

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """
        Customize settings sources to use TOML config file only.

        No environment variables for config.toml settings since this is
        project-specific local configuration.
        """
        return (
            TomlConfigSettingsSource(
                settings_cls,
                toml_file=cls.model_config.get("toml_file"),
            ),
        )

    @classmethod
    def from_path(cls, local_path: str | Path) -> "WarehouseSettings":
        """Create warehouse settings from a warehouse path and write to default location.

        Args:
            local_path: Path to warehouse

        Returns:
            WarehouseSettings instance
        """
        # Validate and normalize path
        config = WarehouseConfig(local_path=str(local_path))

        # Write to default location
        beacon_dir = Path(".agentic-beacon")
        beacon_dir.mkdir(parents=True, exist_ok=True)

        toml_path = beacon_dir / "config.toml"
        toml_content = f"""[warehouse]
local_path = "{config.local_path}"
"""
        with open(toml_path, "w", encoding="utf-8") as f:
            f.write(toml_content)

        # Now load via BaseSettings
        return cls()  # type: ignore[call-arg]  # warehouse populated from TOML file

    def to_toml(self, path: str | Path) -> None:
        """Write warehouse settings to TOML file.

        Args:
            path: Path to write config.toml

        Raises:
            PermissionError: If cannot write to path
        """
        path = Path(path)

        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Create TOML content
        toml_content = f"""[warehouse]
local_path = "{self.warehouse.local_path}"
"""

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(toml_content)
        except PermissionError as e:
            raise PermissionError(
                f"Cannot write to {path}: insufficient permissions"
            ) from e


# ========== Helper Functions ==========


def validate_beacon_directory(base_dir: str | Path = ".") -> Path:
    """Validate that .agentic-beacon directory exists.

    Args:
        base_dir: Base directory containing .agentic-beacon/

    Returns:
        Path to .agentic-beacon directory

    Raises:
        DirectoryNotFoundError: If directory doesn't exist
        NotADirectoryError: If path exists but is not a directory
        PermissionError: If directory exists but is unreadable
    """
    config_dir = Path(base_dir).resolve() / ".agentic-beacon"

    if not config_dir.exists():
        raise DirectoryNotFoundError(
            f"Project not initialized. .agentic-beacon directory not found at {config_dir}. "
            "Run 'abc setup' first."
        )

    if not config_dir.is_dir():
        raise NotADirectoryError(f"Expected directory, found file: {config_dir}")

    # Check if directory is readable
    if not os.access(config_dir, os.R_OK):
        raise PermissionError(
            f"Cannot read .agentic-beacon directory at {config_dir}: insufficient permissions"
        )

    return config_dir
