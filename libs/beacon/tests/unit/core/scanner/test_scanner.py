"""Tests for the knowledge reference scanner (tasks 5.1–5.10).

Covers all TDD test cases listed under each task in the auto-pull-artifact-dependencies
OpenSpec change.
"""

from pathlib import Path

from beacon.core.manifest.beacon import BeaconManifest
from beacon.core.scanner.scanner import (
    LinkRef,
    classify_knowledge_ref,
    extract_markdown_links,
    is_absolute_url,
    normalize_link_target,
    resolve_link,
    scan_adopted_artifacts,
    scan_file_for_knowledge,
)


class TestExtractMarkdownLinks:
    """Task 5.2: extract_markdown_links — TDD test cases."""

    def test_tc1_basic_link(self):
        """TC1: [foo](bar.md) → one LinkRef."""
        result = extract_markdown_links("[foo](bar.md)")
        assert result == [LinkRef(text="foo", target="bar.md")]

    def test_tc2_no_links(self):
        """TC2: Text with no links → empty list."""
        result = extract_markdown_links("Just plain text.")
        assert result == []

    def test_tc3_spaces_in_text(self):
        """TC3: Link with spaces in text → correctly extracted."""
        result = extract_markdown_links("[foo bar](baz.md)")
        assert result == [LinkRef(text="foo bar", target="baz.md")]

    def test_tc4_parens_in_target(self):
        """TC4: Link with parens in target → stops at first unescaped )."""
        result = extract_markdown_links("[x](foo(y).md)")
        # First ) closes the link target
        assert result == [LinkRef(text="x", target="foo(y")]

    def test_tc5_image_skipped(self):
        """TC5: Image link ![alt](img.png) → skipped."""
        result = extract_markdown_links("![alt](img.png)")
        assert result == []

    def test_tc6_link_in_code_fence(self):
        """TC6: Link inside code fence → NOT extracted."""
        text = "```\n[x](y)\n```"
        result = extract_markdown_links(text)
        assert result == []

    def test_tc7_link_in_inline_code(self):
        """TC7: Link inside inline code → NOT extracted."""
        result = extract_markdown_links("`[x](y)`")
        assert result == []

    def test_tc8_reference_style_skipped(self):
        """TC8: Reference-style [x][ref] → skipped (no inline target)."""
        result = extract_markdown_links("[x][ref] and [ref]: url")
        assert result == []

    def test_tc9_escaped_brackets(self):
        """TC9: Escaped brackets \\[x\\](y) → NOT extracted."""
        result = extract_markdown_links(r"\[x\](y)")
        assert result == []

    def test_tc10_multiple_links(self):
        """TC10: Multiple links on one line → all extracted in order."""
        result = extract_markdown_links("[a](1.md) [b](2.md)")
        assert result == [
            LinkRef(text="a", target="1.md"),
            LinkRef(text="b", target="2.md"),
        ]


class TestNormalizeLinkTarget:
    """Task 5.3: normalize_link_target — TDD test cases."""

    def test_tc1_fragment_stripped(self):
        """TC1: foo.md#anchor → foo.md."""
        assert normalize_link_target("foo.md#anchor") == "foo.md"

    def test_tc2_url_decode(self):
        """TC2: foo%20bar.md → foo bar.md."""
        assert normalize_link_target("foo%20bar.md") == "foo bar.md"

    def test_tc3_no_change(self):
        """TC3: foo.md (no fragment, no encoding) → unchanged."""
        assert normalize_link_target("foo.md") == "foo.md"

    def test_tc4_fragment_only(self):
        """TC4: #just-a-fragment → empty string."""
        assert normalize_link_target("#just-a-fragment") == ""

    def test_tc5_multiple_hashes(self):
        """TC5: foo.md#anchor#another → foo.md (first # splits)."""
        assert normalize_link_target("foo.md#anchor#another") == "foo.md"


class TestIsAbsoluteUrl:
    """Task 5.4: is_absolute_url — TDD test cases."""

    def test_tc1_https(self):
        assert is_absolute_url("https://example.com/foo") is True

    def test_tc2_http(self):
        assert is_absolute_url("http://example.com") is True

    def test_tc3_mailto(self):
        assert is_absolute_url("mailto:x@y.com") is True

    def test_tc4_ftp(self):
        assert is_absolute_url("ftp://host/path") is True

    def test_tc5_file_uri(self):
        assert is_absolute_url("file:///local/path") is True

    def test_tc6_relative(self):
        assert is_absolute_url("../foo.md") is False

    def test_tc7_absolute_path(self):
        """TC7: /absolute/path.md → not skipped at this layer."""
        assert is_absolute_url("/absolute/path.md") is False


class TestResolveLink:
    """Task 5.5: resolve_link — TDD test cases."""

    def _wh(self, tmp_path: Path) -> Path:
        wh = tmp_path / "warehouse"
        wh.mkdir()
        return wh

    def test_tc1_context_to_knowledge(self, tmp_path):
        """TC1: scanned=contexts/python-standards.md, link=../knowledge/foo/bar.md."""
        wh = self._wh(tmp_path)
        scanned = wh / "contexts" / "python-standards.md"
        scanned.parent.mkdir(parents=True)
        scanned.write_text("# Context")
        result = resolve_link(scanned, "../knowledge/foo/bar.md", wh)
        assert result is not None
        assert result.warehouse_relative == "knowledge/foo/bar.md"

    def test_tc2_skill_to_knowledge(self, tmp_path):
        """TC2: scanned=skills/s/SKILL.md, link=../../knowledge/foo/bar.md."""
        wh = self._wh(tmp_path)
        scanned = wh / "skills" / "s" / "SKILL.md"
        scanned.parent.mkdir(parents=True)
        scanned.write_text("# Skill")
        result = resolve_link(scanned, "../../knowledge/foo/bar.md", wh)
        assert result is not None
        assert result.warehouse_relative == "knowledge/foo/bar.md"

    def test_tc3_out_of_warehouse(self, tmp_path):
        """TC3: ../../../other/repo/x.md → None (out of warehouse)."""
        wh = self._wh(tmp_path)
        scanned = wh / "contexts" / "a.md"
        scanned.parent.mkdir(parents=True)
        scanned.write_text("# Context")
        result = resolve_link(scanned, "../../../other/repo/x.md", wh)
        assert result is None

    def test_tc4_absolute_url(self, tmp_path):
        """TC4: https://example.com → None (absolute URL)."""
        wh = self._wh(tmp_path)
        scanned = wh / "contexts" / "a.md"
        scanned.parent.mkdir(parents=True)
        scanned.write_text("# Context")
        result = resolve_link(scanned, "https://example.com", wh)
        assert result is None

    def test_tc5_same_dir_sibling(self, tmp_path):
        """TC5: ./b.md → contexts/b.md."""
        wh = self._wh(tmp_path)
        scanned = wh / "contexts" / "a.md"
        scanned.parent.mkdir(parents=True)
        scanned.write_text("# Context")
        result = resolve_link(scanned, "./b.md", wh)
        assert result is not None
        assert result.warehouse_relative == "contexts/b.md"

    def test_tc6_deep_nesting(self, tmp_path):
        """TC6: ../../knowledge/x.md from nested context → knowledge/x.md."""
        wh = self._wh(tmp_path)
        scanned = wh / "contexts" / "nested" / "a.md"
        scanned.parent.mkdir(parents=True)
        scanned.write_text("# Context")
        result = resolve_link(scanned, "../../knowledge/x.md", wh)
        assert result is not None
        assert result.warehouse_relative == "knowledge/x.md"

    def test_tc7_directory_link(self, tmp_path):
        """TC7: ../knowledge/ → ResolvedLink(knowledge/) or None.

        Our implementation resolves it; classifier will reject it later (not .md).
        """
        wh = self._wh(tmp_path)
        scanned = wh / "contexts" / "a.md"
        scanned.parent.mkdir(parents=True)
        scanned.write_text("# Context")
        result = resolve_link(scanned, "../knowledge/", wh)
        # pathlib resolves "../knowledge/" to a directory path, still inside warehouse
        assert result is not None
        assert result.warehouse_relative == "knowledge"


class TestClassifyKnowledgeRef:
    """Task 5.6: classify_knowledge_ref — TDD test cases."""

    def _wh(self, tmp_path: Path) -> Path:
        wh = tmp_path / "warehouse"
        wh.mkdir()
        return wh

    def test_tc1_deep_knowledge_md(self, tmp_path):
        """TC1: knowledge/python-standards/lessons/foo.md → True."""
        wh = self._wh(tmp_path)
        path = wh / "knowledge" / "python-standards" / "lessons" / "foo.md"
        path.parent.mkdir(parents=True)
        path.write_text("# Foo")
        assert classify_knowledge_ref(path, wh) is True

    def test_tc2_context_other_md(self, tmp_path):
        """TC2: contexts/other.md → False (not under knowledge/)."""
        wh = self._wh(tmp_path)
        path = wh / "contexts" / "other.md"
        path.parent.mkdir(parents=True)
        path.write_text("# Other")
        assert classify_knowledge_ref(path, wh) is False

    def test_tc3_png_under_knowledge(self, tmp_path):
        """TC3: knowledge/diagram.png → False (not .md)."""
        wh = self._wh(tmp_path)
        path = wh / "knowledge" / "diagram.png"
        path.parent.mkdir(parents=True)
        path.write_text("")
        assert classify_knowledge_ref(path, wh) is False

    def test_tc4_readme_md(self, tmp_path):
        """TC4: knowledge/README.md → True."""
        wh = self._wh(tmp_path)
        path = wh / "knowledge" / "README.md"
        path.parent.mkdir(parents=True)
        path.write_text("# README")
        assert classify_knowledge_ref(path, wh) is True

    def test_tc5_top_level_knowledge_md(self, tmp_path):
        """TC5: knowledge.md (top-level, not a dir prefix) → False."""
        wh = self._wh(tmp_path)
        path = wh / "knowledge.md"
        path.write_text("# Knowledge")
        assert classify_knowledge_ref(path, wh) is False

    def test_tc6_knowledge_as_subdir(self, tmp_path):
        """TC6: foo/knowledge/x.md → False (knowledge is a subdir, not top-level)."""
        wh = self._wh(tmp_path)
        path = wh / "foo" / "knowledge" / "x.md"
        path.parent.mkdir(parents=True)
        path.write_text("# X")
        assert classify_knowledge_ref(path, wh) is False

    def test_tc7_knowledge_directory(self, tmp_path):
        """TC7: knowledge/ (directory, not a file) → False."""
        wh = self._wh(tmp_path)
        path = wh / "knowledge"
        path.mkdir()
        assert classify_knowledge_ref(path, wh) is False


class TestScanFileForKnowledge:
    """Task 5.7: scan_file_for_knowledge — TDD test cases."""

    def _wh(self, tmp_path: Path) -> Path:
        wh = tmp_path / "warehouse"
        wh.mkdir()
        return wh

    def test_tc1_duplicate_links_deduped(self, tmp_path):
        """TC2 (file-level): Duplicate knowledge links → set has one entry."""
        wh = self._wh(tmp_path)
        ctx = wh / "contexts" / "ctx.md"
        ctx.parent.mkdir(parents=True)
        ctx.write_text("[a](../knowledge/foo.md) [b](../knowledge/foo.md)\n")
        result = scan_file_for_knowledge(ctx, wh)
        assert result == {"knowledge/foo.md"}

    def test_tc2_mixed_links(self, tmp_path):
        """TC3: Mixed knowledge and non-knowledge links → only knowledge in set."""
        wh = self._wh(tmp_path)
        ctx = wh / "contexts" / "ctx.md"
        ctx.parent.mkdir(parents=True)
        ctx.write_text(
            "[k](../knowledge/foo.md) [c](../contexts/other.md) [h](https://example.com)\n"
        )
        result = scan_file_for_knowledge(ctx, wh)
        assert result == {"knowledge/foo.md"}

    def test_tc3_broken_frontmatter_valid_body(self, tmp_path):
        """TC4: Broken YAML frontmatter but valid body → body still scanned."""
        wh = self._wh(tmp_path)
        ctx = wh / "contexts" / "ctx.md"
        ctx.parent.mkdir(parents=True)
        ctx.write_text("---\nbad\n[link](../knowledge/foo.md)\n")
        result = scan_file_for_knowledge(ctx, wh)
        assert result == {"knowledge/foo.md"}

    def test_tc4_empty_file(self, tmp_path):
        """TC5: Empty file → empty set."""
        wh = self._wh(tmp_path)
        ctx = wh / "contexts" / "ctx.md"
        ctx.parent.mkdir(parents=True)
        ctx.write_text("")
        result = scan_file_for_knowledge(ctx, wh)
        assert result == set()


class TestScanAdoptedArtifacts:
    """Task 5.8: scan_adopted_artifacts — TDD test cases."""

    def _make_warehouse(self, tmp_path: Path) -> Path:
        wh = tmp_path / "warehouse"
        wh.mkdir()
        (wh / "contexts").mkdir()
        (wh / "skills").mkdir()
        (wh / "knowledge").mkdir()
        return wh

    def test_tc1_shared_knowledge_link(self, tmp_path):
        """TC1: Two contexts sharing a knowledge link → set has one entry."""
        wh = self._make_warehouse(tmp_path)

        ctx1 = wh / "contexts" / "a.md"
        ctx1.write_text("[x](../knowledge/shared.md)\n")
        ctx2 = wh / "contexts" / "b.md"
        ctx2.write_text("[x](../knowledge/shared.md)\n")

        beacon = BeaconManifest(artifacts={"contexts": ["a", "b"]})
        result = scan_adopted_artifacts(beacon, wh)
        assert result == {"knowledge/shared.md"}

    def test_tc2_skill_with_knowledge(self, tmp_path):
        """TC2: Skill's SKILL.md with knowledge links → included."""
        wh = self._make_warehouse(tmp_path)

        skill_dir = wh / "skills" / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("[x](../../knowledge/skill-kb.md)\n")

        beacon = BeaconManifest(artifacts={"skills": ["my-skill"]})
        result = scan_adopted_artifacts(beacon, wh)
        assert result == {"knowledge/skill-kb.md"}

    def test_tc4_no_adopted(self, tmp_path):
        """TC4: No adopted contexts or skills → empty set."""
        wh = self._make_warehouse(tmp_path)
        beacon = BeaconManifest(artifacts={})
        result = scan_adopted_artifacts(beacon, wh)
        assert result == set()

    def test_tc5_no_knowledge_links(self, tmp_path):
        """TC5: Adopted context with no knowledge links → contributes zero."""
        wh = self._make_warehouse(tmp_path)

        ctx = wh / "contexts" / "a.md"
        ctx.write_text("# No links here\n")

        beacon = BeaconManifest(artifacts={"contexts": ["a"]})
        result = scan_adopted_artifacts(beacon, wh)
        assert result == set()


class TestMissingTargetWarning:
    """Task 5.9: Emit warning when knowledge ref resolves to missing path."""

    def test_missing_target_warning(self, tmp_path, loguru_caplog):
        """Scanner includes missing ref in set AND emits one loguru WARNING."""
        wh = tmp_path / "warehouse"
        wh.mkdir()
        (wh / "contexts").mkdir()
        (wh / "knowledge").mkdir()

        ctx = wh / "contexts" / "ctx.md"
        ctx.write_text("[x](../knowledge/missing.md)\n")

        result = scan_file_for_knowledge(ctx, wh)
        assert "knowledge/missing.md" in result

        warnings = [r for r in loguru_caplog.records if r.levelname == "WARNING"]
        assert len(warnings) == 1
        assert "missing" in warnings[0].message
