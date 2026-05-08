"""Frontmatter parsing and validation for agent and skill artifacts.

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
                "docs/migrations/artifact-dependencies-frontmatter.md"
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

    # Strip leading whitespace / BOM
    content = content.lstrip("﻿").lstrip()

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


def validate_requires_against_warehouse(
    frontmatter: SkillFrontmatter, warehouse_path: Path
) -> list[str]:
    """Validate that every name in frontmatter.requires resolves to an existing warehouse file.

    Args:
        frontmatter: Parsed and validated skill frontmatter.
        warehouse_path: Root of the warehouse clone.

    Returns:
        List of human-readable error strings; empty on success.
    """
    errors: list[str] = []
    req = frontmatter.requires

    for ctx_name in req.contexts:
        expected = warehouse_path / "contexts" / f"{ctx_name}.md"
        if not expected.exists():
            errors.append(f"Missing context '{ctx_name}': expected {expected}")

    return errors
