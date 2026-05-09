"""Custom exceptions for Agentic Beacon."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AgentWireConflict:
    """Describes a single regular-file conflict blocking agent wiring."""

    dest: Path
    agent_name: str
    tool: str


class BeaconError(Exception):
    """Base class for all Beacon errors."""

    pass


class ConfigurationError(BeaconError):
    """Base class for configuration errors."""

    pass


class YAMLParseError(ConfigurationError):
    """Raised when YAML parsing fails."""

    pass


class TOMLParseError(ConfigurationError):
    """Raised when TOML parsing fails."""

    pass


class ValidationError(ConfigurationError):
    """Raised when validation fails."""

    pass


class DirectoryNotFoundError(ConfigurationError):
    """Raised when .agentic-beacon directory not found."""

    pass


class WarehouseValidationError(ConfigurationError):
    """Raised when warehouse structure validation fails."""

    pass


class ResetError(ConfigurationError):
    """Raised when artifact reset cannot proceed due to configuration issues."""

    pass


class BeaconSyncError(BeaconError):
    """Raised when the sync pipeline cannot proceed."""

    def __init__(self, message: str, hint: str | None = None) -> None:
        super().__init__(message)
        self.hint = hint


class RegularFileConflictError(BeaconSyncError):
    """Raised when one or more agent destinations are regular (non-symlink) files."""

    def __init__(self, conflicts: Sequence[AgentWireConflict]) -> None:
        if not conflicts:
            raise ValueError("RegularFileConflictError requires at least one conflict")
        self.conflicts = tuple(conflicts)
        n = len(self.conflicts)
        s = "s" if n != 1 else ""
        message = f"Cannot wire {n} agent{s}: regular file conflict."
        hint = (
            f"{n} regular file{s} block agent wiring. "
            "Run abc sync or abc adopt to see a structured remediation guide."
        )
        super().__init__(message, hint=hint)


class ContributeError(BeaconError):
    """Raised when a contribute operation cannot proceed."""

    pass


class AgentManifestError(ConfigurationError):
    """Raised when the agent manifest (agents/agents.yaml) is invalid or malformed."""

    pass


class DependencyError(ConfigurationError):
    """Raised when a declared agent's required skill is missing from the project."""

    pass
