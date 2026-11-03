"""Frontmatter parsing and validation for skill artifacts.

Implements the dependency-resolution contract from the auto-pull-artifact-dependencies
OpenSpec change.

Note: Agent frontmatter parsing was removed in PER-117. Agent dependencies now
live in <warehouse>/agents/agents.yaml (see core/dependencies/manifest.py).
This module only handles SKILL frontmatter.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, model_validator


class SkillRequires(BaseModel):
    """Skill-specific requires block (forbids skill-to-skill deps)."""

    contexts: list[str]

    @model_validator(mode="before")
    @classmethod
    def reject_skills_key(cls, data: dict) -> dict:
        if isinstance(data, dict) and "skills" in data:
            msg = (
                "Skill-to-skill dependencies are not supported. "
                "Remove 'skills' from the requires block. See "
                "docs/archive/migrations/artifact-dependencies-frontmatter.md"
            )
            raise ValueError(msg)
        return data


class SkillFrontmatter(BaseModel):
    """Validated frontmatter for a skill SKILL.md file."""

    requires: SkillRequires


@dataclass
class FrontmatterResult:
    """Result of parsing a markdown file's YAML frontmatter."""

    success: bool
    data: dict | None = None
    error: str | None = None
    message: str = ""


def parse_frontmatter(path: Path) -> FrontmatterResult:
    """Parse YAML frontmatter from a markdown file.

    Args:
        path: Path to the markdown file.

    Returns:
        FrontmatterResult with parsed dict on success, or structured error on failure.
    """
    if not path.exists():
        return FrontmatterResult(
            success=False,
            error="file-not-found",
            message=f"File not found: {path}",
        )

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        return FrontmatterResult(
            success=False,
            error="read-error",
            message=f"Could not read {path}: {exc}",
        )

    return parse_frontmatter_text(content)


def parse_frontmatter_text(content: str) -> FrontmatterResult:
    """Parse YAML frontmatter from markdown text already in memory.

    Args:
        content: Full text of the markdown file.

    Returns:
        FrontmatterResult with parsed dict on success, or structured error on failure.
    """
    # Strip leading whitespace / BOM
    content = content.lstrip("\ufeff").lstrip()

    if not content.startswith("---"):
        return FrontmatterResult(
            success=False,
            error="missing-frontmatter",
            message="File has no YAML frontmatter (must start with ---)",
        )

    # Find closing ---
    remainder = content[3:]
    end_idx = remainder.find("---")
    if end_idx == -1:
        return FrontmatterResult(
            success=False,
            error="unterminated-frontmatter",
            message="Frontmatter opened with --- but never closed",
        )

    yaml_block = remainder[:end_idx].strip()

    try:
        data = yaml.safe_load(yaml_block)
    except yaml.YAMLError as exc:
        return FrontmatterResult(
            success=False,
            error="yaml-parse-error",
            message=f"YAML parse error: {exc}",
        )

    if not isinstance(data, dict):
        return FrontmatterResult(
            success=False,
            error="invalid-frontmatter",
            message="Frontmatter did not parse to a YAML object (dict)",
        )

    return FrontmatterResult(success=True, data=data)


@dataclass
class FrontmatterSplit:
    """A markdown file split into its frontmatter data and its body.

    ``frontmatter`` is None when there is no usable block. ``warning`` holds the
    reason a block was present but unusable; it is None otherwise.
    """

    frontmatter: dict | None
    body: str
    warning: str | None


_FENCE = "---"


def split_frontmatter(text: str) -> FrontmatterSplit:
    """Split markdown text into frontmatter data and body, line by line.

    The block opens on a first line (after an optional BOM) that is ``---``, and
    closes on the next line that is ``---`` once stripped. Only a full line closes
    the block, so a ``---`` inside a value does not. Values that YAML parses to a
    non-JSON type (dates) are converted with ``str()``.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].lstrip("\ufeff").strip() != _FENCE:
        return FrontmatterSplit(frontmatter=None, body=text, warning=None)

    close = next((i for i in range(1, len(lines)) if lines[i].strip() == _FENCE), None)
    if close is None:
        return FrontmatterSplit(frontmatter=None, body=text, warning=None)

    body = "".join(lines[close + 1 :])
    try:
        data = yaml.safe_load("".join(lines[1:close]))
    except yaml.YAMLError as exc:
        return FrontmatterSplit(
            frontmatter=None, body=body, warning=f"YAML parse error: {exc}"
        )
    if not isinstance(data, dict):
        return FrontmatterSplit(
            frontmatter=None,
            body=body,
            warning="frontmatter did not parse to a YAML object (dict)",
        )
    return FrontmatterSplit(frontmatter=_json_native(data), body=body, warning=None)


def _json_native(value: object) -> object:
    """Return ``value`` with every non-JSON scalar converted to ``str``."""
    if isinstance(value, dict):
        return {str(key): _json_native(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_native(item) for item in value]
    if value is None or isinstance(value, str | bool | int | float):
        return value
    return str(value)
