"""Workspace configuration models for Agentic Beacon.

Defines the structure of config.toml — a local, gitignored file that stores
project-specific connection settings (e.g. which warehouse to use).
"""

import re
from pathlib import Path

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

# Conservative subset of valid git branch name characters. Rejects characters
# that would break naive TOML serialization (quotes, backslashes, whitespace).
_BRANCH_NAME_RE = re.compile(r"[A-Za-z0-9._/-]+")


def _is_valid_git_branch_name(name: str) -> bool:
    """Apply the subset of git-check-ref-format rules relevant for a branch name.

    Rejects inputs that pass the basic charset check but are not legal git refs
    (e.g. '.', '..', '/foo', 'foo/', 'foo.lock', 'foo..bar'). This matters
    because the value is later interpolated into a 'git checkout <branch>'
    recovery hint shown to users; a value like '.' would render a destructive
    'git checkout .' command.
    """
    if not _BRANCH_NAME_RE.fullmatch(name):
        return False
    if name in {".", "..", "@", "HEAD"}:
        return False
    if name.startswith("/") or name.endswith("/"):
        return False
    if ".." in name or "//" in name:
        return False
    for component in name.split("/"):
        if not component:
            return False
        if component.startswith(".") or component.startswith("-"):
            return False
        if component.endswith(".") or component.endswith(".lock"):
            return False
    return True


class WarehouseConfig(BaseModel):
    """Warehouse connection details."""

    local_path: str = Field(..., description="Absolute path to local warehouse")
    main_branch: str | None = Field(
        default=None,
        description=(
            "The branch abc treats as the warehouse's main branch. "
            "Defaults to None, which accepts both 'main' and 'master'. "
            "Override (e.g. 'dev') when the warehouse uses a non-standard default branch."
        ),
    )

    @field_validator("local_path")
    @classmethod
    def validate_local_path(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("local_path cannot be empty")

        path = Path(v).expanduser()
        if not path.is_absolute():
            raise ValueError("local_path must be an absolute path")

        return str(path)

    @field_validator("main_branch")
    @classmethod
    def validate_main_branch(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("main_branch cannot be empty if set")
        if not _is_valid_git_branch_name(v):
            raise ValueError(
                "main_branch must be a valid git branch name "
                "(letters, digits, '.', '_', '/', '-'; no leading '-', '.', or '/', "
                f"no '..', no '.lock' suffix). Got: {v!r}"
            )
        return v


class WorkspaceConfig(BaseSettings):
    """Warehouse connection config loaded from config.toml.

    This is per-project local configuration — not abc behaviour settings.
    The TOML file is gitignored and stores the path to the local warehouse.
    """

    model_config = SettingsConfigDict(
        toml_file=".agentic-beacon/config.toml",
        extra="ignore",
    )

    warehouse: WarehouseConfig

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            TomlConfigSettingsSource(
                settings_cls,
                toml_file=cls.model_config.get("toml_file"),
            ),
        )

    @classmethod
    def from_path(
        cls,
        local_path: str | Path,
        *,
        project_root: Path | None = None,
        main_branch: str | None = None,
    ) -> "WorkspaceConfig":
        """Write warehouse path to config.toml and return loaded config."""
        config = WarehouseConfig(local_path=str(local_path), main_branch=main_branch)

        base = project_root if project_root is not None else Path(".")
        beacon_dir = base / ".agentic-beacon"
        beacon_dir.mkdir(parents=True, exist_ok=True)

        toml_path = beacon_dir / "config.toml"
        with open(toml_path, "w", encoding="utf-8") as f:
            f.write(_render_workspace_toml(config))

        return cls.model_construct(warehouse=config)

    def to_toml(self, path: str | Path) -> None:
        """Write workspace config to TOML file.

        Raises:
            PermissionError: If cannot write to path
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(_render_workspace_toml(self.warehouse))
        except PermissionError as e:
            raise PermissionError(
                f"Cannot write to {path}: insufficient permissions"
            ) from e


def _render_workspace_toml(config: WarehouseConfig) -> str:
    """Serialize a WarehouseConfig to TOML, omitting unset optional fields."""
    lines = ["[warehouse]", f'local_path = "{config.local_path}"']
    if config.main_branch is not None:
        lines.append(f'main_branch = "{config.main_branch}"')
    return "\n".join(lines) + "\n"
