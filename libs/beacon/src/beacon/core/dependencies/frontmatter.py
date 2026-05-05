"""Frontmatter parsing and validation for agent and skill artifacts.

Implements the dependency-resolution contract from the auto-pull-artifact-dependencies
OpenSpec change.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, model_validator


class RequiresBlock(BaseModel):
    """Shared requires block for agents and skills."""

    contexts: list[str]


class AgentRequires(RequiresBlock):
    """Agent-specific requires block (allows skills)."""

    skills: list[str]


class SkillRequires(RequiresBlock):
    """Skill-specific requires block (forbids skills)."""

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


class AgentFrontmatter(BaseModel):
    """Validated frontmatter for an agent markdown file."""

    requires: AgentRequires


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


def validate_requires_against_warehouse(
    frontmatter: AgentFrontmatter | SkillFrontmatter, warehouse_path: Path
) -> list[str]:
    """Validate that every name in frontmatter.requires resolves to an existing warehouse file.

    Args:
        frontmatter: Parsed and validated frontmatter.
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

    # Agent frontmatter may have skills; skill frontmatter rejects skills at parse time
    if isinstance(req, AgentRequires):
        for skill_name in req.skills:
            expected = warehouse_path / "skills" / skill_name / "SKILL.md"
            if not expected.exists():
                errors.append(f"Missing skill '{skill_name}': expected {expected}")

    return errors
