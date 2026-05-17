"""Unit tests for contribute-warehouse SKILL.md frontmatter (Task 9.4).

TDD test cases per tasks.md TC table for 2.3 and 9.4.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from beacon.core.dependencies.frontmatter import parse_frontmatter

_SKILL_MD = (
    Path(__file__).resolve().parents[5]
    / "src"
    / "beacon"
    / "data"
    / "skills"
    / "contribute-warehouse"
    / "SKILL.md"
)


@pytest.fixture
def frontmatter_result():
    return parse_frontmatter(_SKILL_MD)


class TestFrontmatterParsing:
    """TC1-TC8 from tasks.md 2.3 TDD spec."""

    def test_tc1_parses_cleanly(self, frontmatter_result):
        """TC1: Frontmatter parses cleanly via parse_frontmatter."""
        assert frontmatter_result.success is True, frontmatter_result.message

    def test_tc2_name_is_contribute_warehouse(self, frontmatter_result):
        """TC2: name field equals 'contribute-warehouse' exactly."""
        assert frontmatter_result.data["name"] == "contribute-warehouse"

    def test_tc3_description_non_empty_and_short(self, frontmatter_result):
        """TC3: description is non-empty and ≤200 chars."""
        desc = frontmatter_result.data.get("description", "")
        assert desc, "description must not be empty"
        assert len(desc) <= 200, f"description too long ({len(desc)} chars)"

    def test_tc4_compatibility_is_opencode(self, frontmatter_result):
        """TC4: compatibility field equals 'opencode'."""
        assert frontmatter_result.data.get("compatibility") == "opencode"

    def test_tc5_requires_contexts_is_empty_list(self, frontmatter_result):
        """TC5: requires.contexts is an empty list."""
        requires = frontmatter_result.data.get("requires", {})
        assert requires.get("contexts") == []

    def test_tc6_body_references_all_four_scripts(self):
        """TC6: Body references all four helper scripts by name."""
        content = _SKILL_MD.read_text()
        for script in [
            "resolve_warehouse.py",
            "summarize_changes.py",
            "draft_commit_message.py",
            "push_warehouse.py",
        ]:
            assert script in content, f"Body must reference {script}"

    def test_tc7_body_documents_slash_invocation(self):
        """TC7: Body documents /contribute-warehouse as the slash invocation."""
        content = _SKILL_MD.read_text()
        assert "/contribute-warehouse" in content

    def test_tc8_body_length_in_range(self):
        """TC8: Body length (non-frontmatter lines) is between 100 and 400 lines."""
        content = _SKILL_MD.read_text()
        # Strip frontmatter block
        lines = content.split("\n")
        # Find the second ---
        fm_end = 0
        count = 0
        for i, line in enumerate(lines):
            if line.strip() == "---":
                count += 1
                if count == 2:
                    fm_end = i + 1
                    break
        body_lines = lines[fm_end:]
        assert 100 <= len(body_lines) <= 400, (
            f"Body length {len(body_lines)} not in [100, 400]"
        )
