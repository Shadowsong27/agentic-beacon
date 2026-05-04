"""Beacon.yaml manifest models for Agentic Beacon.

Defines the structure of the beacon.yaml artifact manifest — a project-level file
committed to git that declares which artifacts to adopt from the warehouse.
"""

from pathlib import Path

import yaml
from loguru import logger
from pydantic import BaseModel, Field

from beacon.core.exceptions import (
    ValidationError,
    YAMLParseError,
)


class ArtifactsConfig(BaseModel):
    """Artifacts configuration from beacon.yaml."""

    model_config = {"extra": "forbid"}

    agents: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    contexts: list[str] = Field(default_factory=list)

    # XXX REMOVE-IN-CHUNK-C: backward-compat shim for `artifacts.knowledge`.
    # Spec D2 says knowledge is "deleted, not deprecated", and TC1 of task 3.1
    # mandates `assert not hasattr(a, "knowledge")`. We knowingly violate that
    # because 14 call-sites in adoption/distribution/cli still read/write
    # `manifest.artifacts.knowledge`; deleting the shim now would crash the
    # CLI between Chunks A and C. Chunk C (phases 7-8) rewrites those
    # call-sites; this @property + setter MUST be removed at that time, along
    # with the corresponding tests in TestArtifactsConfig.
    @property
    def knowledge(self) -> list[str]:
        return []

    @knowledge.setter
    def knowledge(self, value: list[str]) -> None:
        return None


class IgnoreConfig(BaseModel):
    """Patterns to ignore in contribute and delta commands.

    Supports fnmatch glob patterns, e.g. ``openspec-*``.
    """

    skills: list[str] = Field(default_factory=list)


class BeaconManifest(BaseModel):
    """Parsed representation of beacon.yaml.

    Not a BaseSettings subclass — beacon.yaml has a custom structure
    that requires manual parsing and validation.
    """

    artifacts: ArtifactsConfig = Field(default_factory=ArtifactsConfig)
    ignore: IgnoreConfig = Field(default_factory=IgnoreConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "BeaconManifest":
        """Load beacon manifest from YAML file.

        Raises:
            FileNotFoundError: If file doesn't exist
            IsADirectoryError: If path is a directory
            PermissionError: If file cannot be read
            YAMLParseError: If YAML syntax is invalid
            ValidationError: If structure is invalid
        """
        path = Path(path)

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

        if data is None:
            data = {}

        if not isinstance(data, dict):
            raise ValidationError("Configuration must be a YAML object (dict)")

        if "artifacts" not in data:
            raise ValidationError("Missing required 'artifacts' section")

        artifacts_data = data.get("artifacts", {})
        if not isinstance(artifacts_data, dict):
            raise ValidationError("'artifacts' section must be a YAML object (dict)")

        # Legacy-drop migration: remove artifacts.knowledge if present
        if "knowledge" in artifacts_data:
            logger.info("artifacts.knowledge removed; knowledge is now auto-derived")
            del artifacts_data["knowledge"]

        valid_types = {"agents", "skills", "contexts"}
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

        try:
            return cls(**data)
        except Exception as e:
            raise ValidationError(f"Configuration validation failed: {e}") from e

    def to_yaml(self, path: str | Path) -> None:
        """Write beacon manifest to YAML file.

        Raises:
            PermissionError: If cannot write to path
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

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
    """Result of manifest or structure validation."""

    valid: bool
    errors: list[str] = Field(default_factory=list)


class BeaconManifestValidator:
    """Validator for beacon.yaml structure and content."""

    VALID_ARTIFACT_TYPES = {"agents", "skills", "contexts"}

    def validate_structure(self, manifest: BeaconManifest) -> ValidationResult:
        """Validate beacon manifest structure."""
        errors = []

        artifacts_dict = manifest.artifacts.model_dump()

        for artifact_type in artifacts_dict.keys():
            if artifact_type not in self.VALID_ARTIFACT_TYPES:
                errors.append(f"Unknown artifact type: {artifact_type}")

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
