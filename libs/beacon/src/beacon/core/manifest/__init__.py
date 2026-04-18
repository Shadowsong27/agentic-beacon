"""Manifest package for Agentic Beacon project-level configs.

- beacon: beacon.yaml artifact manifest (committed to git)
- workspace: config.toml workspace connection (gitignored)
"""

from .beacon import (
    ArtifactsConfig,
    BeaconManifest,
    BeaconManifestValidator,
    IgnoreConfig,
    ValidationResult,
)
from .workspace import WarehouseConfig, WorkspaceConfig

__all__ = [
    "ArtifactsConfig",
    "BeaconManifest",
    "BeaconManifestValidator",
    "IgnoreConfig",
    "ValidationResult",
    "WarehouseConfig",
    "WorkspaceConfig",
]
