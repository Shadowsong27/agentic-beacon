"""ABC tool behaviour settings.

Environment-variable driven settings that control how the abc CLI operates —
distinct from project-level manifest files (beacon.yaml, config.toml).

All settings can be overridden via environment variables with the ABC_ prefix:
    ABC_GLOBAL_AGENTS_DIR=/custom/path
    ABC_MAX_COMMITS_LOOKBACK=200
    ABC_DEBUG=true
"""

import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .exceptions import DirectoryNotFoundError


class AbcSettings(BaseSettings):
    """Runtime settings for the abc CLI tool."""

    model_config = SettingsConfigDict(
        env_prefix="ABC_",
        env_nested_delimiter="__",
    )

    global_agents_dir: Path = Field(
        default=Path.home() / ".abc" / "agents",
        description="Directory to search for global agent context files.",
    )
    max_commits_lookback: int = Field(
        default=100,
        description="Maximum number of git commits to scan when computing delta.",
        ge=1,
    )
    debug: bool = Field(
        default=False,
        description="Enable verbose debug output.",
    )


abc_settings = AbcSettings()


def validate_beacon_directory(base_dir: str | Path = ".") -> Path:
    """Validate that .agentic-beacon directory exists.

    Returns:
        Path to .agentic-beacon directory

    Raises:
        DirectoryNotFoundError: If directory doesn't exist
        NotADirectoryError: If path exists but is not a directory
        PermissionError: If directory is unreadable
    """
    config_dir = Path(base_dir).resolve() / ".agentic-beacon"

    if not config_dir.exists():
        raise DirectoryNotFoundError(
            f"Project not initialized. .agentic-beacon directory not found at {config_dir}. "
            "Run 'abc setup' first."
        )

    if not config_dir.is_dir():
        raise NotADirectoryError(f"Expected directory, found file: {config_dir}")

    if not os.access(config_dir, os.R_OK):
        raise PermissionError(
            f"Cannot read .agentic-beacon directory at {config_dir}: insufficient permissions"
        )

    return config_dir
