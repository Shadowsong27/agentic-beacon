"""Free-function artifact listing — reads artifacts_path without requiring SyncEngine."""

import tomllib
from pathlib import Path

from pydantic import ValidationError as PydanticValidationError

from beacon.core.exceptions import WorkspaceConfigError


def list_artifacts_with_config_check(
    beacon_dir: Path, artifact_type: str | None = None
) -> dict[str, list[str]]:
    """Validate workspace config at beacon_dir/config.toml (if present) then list artifacts.

    Reads and validates config.toml at the path implied by beacon_dir, not cwd.
    Raises WorkspaceConfigError if config.toml is present but malformed.
    """
    config_path = beacon_dir / "config.toml"
    if config_path.is_file():
        from beacon.core.manifest.workspace import WorkspaceConfig

        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
            WorkspaceConfig.model_validate(data)
        except (PydanticValidationError, tomllib.TOMLDecodeError, OSError) as exc:
            raise WorkspaceConfigError(f"config.toml is invalid: {exc}") from exc
    return list_artifacts(beacon_dir / "artifacts", artifact_type)


def list_artifacts(
    artifacts_path: Path, artifact_type: str | None = None
) -> dict[str, list[str]]:
    """List synced artifacts by type.

    Args:
        artifacts_path: Path to the .agentic-beacon/artifacts/ directory.
        artifact_type: Restrict to this section; omit to list contexts and skills.

    Returns:
        Dict mapping section name to sorted list of relative paths.
    """
    types_to_show = [artifact_type] if artifact_type else ["contexts", "skills"]
    result: dict[str, list[str]] = {}
    for section in types_to_show:
        section_dir = artifacts_path / section
        if not section_dir.exists():
            continue
        files = sorted(
            str(f.relative_to(artifacts_path))
            for f in section_dir.rglob("*")
            if f.is_symlink() and not f.name.startswith(".")
        )
        if files:
            result[section] = files
    return result
