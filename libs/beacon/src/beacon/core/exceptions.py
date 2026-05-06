"""Custom exceptions for Agentic Beacon."""


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


class ContributeError(BeaconError):
    """Raised when a contribute operation cannot proceed."""

    pass


class AgentManifestError(ConfigurationError):
    """Raised when the agent manifest (agents/agents.yaml) is invalid or malformed."""

    pass


class DependencyError(ConfigurationError):
    """Raised when a declared agent's required skill is missing from the project."""

    pass
