"""Unit tests for beacon.domains.artifact.skill helpers."""

from beacon.domains.artifact.skill import _extract_skill_description


class TestExtractSkillDescription:
    """Tests for _extract_skill_description with skill_name fallback."""

    def test_extracts_description_from_frontmatter(self):
        content = "---\ndescription: Generate tests\n---\n\n# Skill"
        assert _extract_skill_description(content) == "Generate tests"

    def test_empty_description_with_skill_name_fallback(self):
        """Empty description field falls back to skill_name."""
        content = "---\nname: foo\ndescription:\n---\n# Skill"
        assert _extract_skill_description(content, "foo") == "Use the foo skill"

    def test_missing_description_with_skill_name_fallback(self):
        """Missing description field falls back to skill_name."""
        content = "---\nname: foo\n---\n# Skill"
        assert _extract_skill_description(content, "foo") == "Use the foo skill"

    def test_no_frontmatter_no_skill_name(self):
        """No frontmatter and no skill_name returns empty string."""
        content = "# My Skill\n\nSome content here.\n"
        assert _extract_skill_description(content) == ""

    def test_no_frontmatter_with_skill_name(self):
        """No frontmatter but skill_name provided returns fallback."""
        content = "# My Skill\n\nSome content here.\n"
        assert (
            _extract_skill_description(content, "my-skill") == "Use the my-skill skill"
        )

    def test_whitespace_only_description_fallback(self):
        """Description with only whitespace falls back to skill_name."""
        content = "---\ndescription:    \n---\n# Skill"
        assert (
            _extract_skill_description(content, "test-skill")
            == "Use the test-skill skill"
        )
