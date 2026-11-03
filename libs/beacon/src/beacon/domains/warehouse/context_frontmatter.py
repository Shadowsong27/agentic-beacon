"""Frontmatter schema for warehouse context files (AB-109).

A context must open with a YAML frontmatter block. The only allowed key is
``description``: one or two sentences on when an agent needs the context.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, StrictStr, field_validator


class ContextFrontmatter(BaseModel):
    """Validated frontmatter for a warehouse context file."""

    model_config = ConfigDict(extra="forbid")

    description: StrictStr | None = None

    @field_validator("description")
    @classmethod
    def _reject_blank_description(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            msg = "description must not be empty"
            raise ValueError(msg)
        return value
