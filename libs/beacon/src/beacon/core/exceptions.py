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
