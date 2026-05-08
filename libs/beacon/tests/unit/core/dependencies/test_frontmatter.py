"""Tests for frontmatter parsing and validation.

Covers tasks 4.1–4.6 from auto-pull-artifact-dependencies OpenSpec change.
"""

from pathlib import Path

import pytest
from beacon.core.dependencies.frontmatter import (
    FrontmatterResult,
    SkillFrontmatter,
    parse_frontmatter,
    validate_requires_against_warehouse,
)
from pydantic import ValidationError


class TestParseFrontmatter:
    """Task 4.2: parse_frontmatter() — TDD test cases."""

    def test_tc1_well_formed_frontmatter(self, tmp_path):
        """TC1: Well-formed frontmatter with scalar keys → returns parsed dict."""
        f = tmp_path / "agent.md"
        f.write_text(
            "---\nname: foo\nrequires:\n  contexts: [bar]\n  skills: [baz]\n---\n# Body\n"
        )
        result = parse_frontmatter(f)
        assert isinstance(result, FrontmatterResult)
        assert result.success is True
        assert result.data == {
            "name": "foo",
            "requires": {"contexts": ["bar"], "skills": ["baz"]},
        }
        assert result.error is None

    def test_tc2_no_frontmatter(self, tmp_path):
        """TC2: No frontmatter at all → returns structured error missing-frontmatter."""
        f = tmp_path / "agent.md"
        f.write_text("# Just a heading\n")
        result = parse_frontmatter(f)
        assert result.success is False
        assert result.error == "missing-frontmatter"
        assert (
            "missing frontmatter" in result.message.lower()
            or "no yaml frontmatter" in result.message.lower()
        )

    def test_tc3_malformed_yaml(self, tmp_path):
        """TC3: Frontmatter present but malformed YAML → returns error with diagnostic."""
        f = tmp_path / "agent.md"
        f.write_text("---\nname: foo\n\tbad_indent: 1\n---\n")
        result = parse_frontmatter(f)
        assert result.success is False
        assert result.error == "yaml-parse-error"
        assert "tab" in result.message.lower() or "parse" in result.message.lower()

    def test_tc4_unterminated_frontmatter(self, tmp_path):
        """TC4: Frontmatter opened with --- but never closed → returns error."""
        f = tmp_path / "agent.md"
        f.write_text("---\nname: foo\n")
        result = parse_frontmatter(f)
        assert result.success is False
        assert result.error == "unterminated-frontmatter"

    def test_tc5_leading_whitespace_and_bom(self, tmp_path):
        """TC5: File starts with BOM or leading whitespace → parser tolerates."""
        f = tmp_path / "agent.md"
        f.write_text("\ufeff---\nname: foo\n---\n# Body\n")
        result = parse_frontmatter(f)
        assert result.success is True
        assert result.data["name"] == "foo"

    def test_tc6_nested_requires_block(self, tmp_path):
        """TC6: Frontmatter with nested requires block → nested structure preserved."""
        f = tmp_path / "agent.md"
        f.write_text("---\nrequires:\n  contexts:\n    - a\n    - b\n---\n")
        result = parse_frontmatter(f)
        assert result.success is True
        assert result.data["requires"]["contexts"] == ["a", "b"]

    def test_tc7_file_not_found(self, tmp_path):
        """TC7: File does not exist → parser returns file-not-found error."""
        f = tmp_path / "missing.md"
        result = parse_frontmatter(f)
        assert result.success is False
        assert result.error == "file-not-found"


class TestSkillFrontmatter:
    """Task 4.3: SkillFrontmatter Pydantic model — TDD test cases."""

    def test_tc5_skill_with_contexts(self):
        """TC5: Skill with requires.contexts → validates."""
        raw = {"requires": {"contexts": ["foo"]}}
        skill = SkillFrontmatter.model_validate(raw)
        assert skill.requires.contexts == ["foo"]

    def test_tc6_skill_with_skills_key(self):
        """TC6: Skill with requires.skills → ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SkillFrontmatter.model_validate(
                {"requires": {"contexts": [], "skills": []}}
            )
        assert "skill" in str(exc_info.value).lower()
        assert (
            "docs/migrations/artifact-dependencies-frontmatter.md"
            in str(exc_info.value).lower()
        )

    def test_tc7_skill_missing_requires(self):
        """TC7: Skill missing requires entirely → ValidationError."""
        with pytest.raises(ValidationError):
            SkillFrontmatter.model_validate({})

    def test_tc7b_skill_missing_contexts_key(self):
        """TC7b: Skill with requires but missing contexts → ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SkillFrontmatter.model_validate({"requires": {}})
        assert "contexts" in str(exc_info.value).lower()


class TestValidateRequiresAgainstWarehouse:
    """Task 4.5: validate_requires_against_warehouse — TDD test cases."""

    def _make_warehouse(self, tmp_path: Path) -> Path:
        wh = tmp_path / "warehouse"
        wh.mkdir()
        (wh / "contexts").mkdir()
        (wh / "skills").mkdir()
        return wh

    def test_tc4_skill_with_missing_context(self, tmp_path):
        """TC4: Skill requires.contexts with one missing → single error."""
        wh = self._make_warehouse(tmp_path)
        (wh / "contexts" / "python-standards.md").write_text("# Context")
        skill = SkillFrontmatter.model_validate(
            {"requires": {"contexts": ["python-standards", "testing"]}}
        )
        errors = validate_requires_against_warehouse(skill, wh)
        assert len(errors) == 1
        assert "testing" in errors[0]
