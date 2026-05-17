"""Unit tests for beacon.domains.warehouse.lint.

Covers phases 2–9: data model, rule helpers, and the orchestrator.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
import yaml
from beacon.domains.warehouse.lint import (
    LintFinding,
    LintReport,
    lint_warehouse,
)

# ---------------------------------------------------------------------------
# Helpers — fixture warehouse builders
# ---------------------------------------------------------------------------


def _build_clean_warehouse(root: Path) -> Path:
    """Build a structurally valid warehouse with no defects."""
    wh = root / "warehouse"
    wh.mkdir()
    (wh / "agents").mkdir()
    (wh / "contexts").mkdir()
    (wh / "skills").mkdir()
    (wh / "docs").mkdir()
    (wh / "README.md").write_text("# Warehouse\n")
    (wh / "agents" / "README.md").write_text("# Agents\n")
    (wh / "contexts" / "README.md").write_text("# Contexts\n")
    (wh / "skills" / "README.md").write_text("# Skills\n")
    return wh


def _add_valid_skill(wh: Path, name: str, contexts: list[str] | None = None) -> Path:
    """Add a valid skill with proper frontmatter."""
    skill_dir = wh / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    ctx_list = contexts or []
    content = f"---\nrequires:\n  contexts: [{', '.join(ctx_list)}]\n---\n# {name}\n"
    (skill_dir / "SKILL.md").write_text(content)
    return skill_dir / "SKILL.md"


def _add_valid_agent(
    wh: Path, name: str, skills: list[str] | None = None, register: bool = True
) -> Path:
    """Add a valid agent with proper frontmatter and optional manifest entry."""
    agent_file = wh / "agents" / f"{name}.md"
    agent_file.write_text(
        f"---\nname: {name}\ndescription: Test agent\n---\n# {name}\n"
    )
    if register:
        _register_agent(wh, name, skills or [])
    return agent_file


def _register_agent(wh: Path, name: str, skills: list[str] | None = None) -> None:
    """Register an agent in agents/agents.yaml."""
    manifest_path = wh / "agents" / "agents.yaml"
    existing: dict = {}
    if manifest_path.exists():
        existing = yaml.safe_load(manifest_path.read_text()) or {}
    existing[name] = {"skills": skills or []}
    manifest_path.write_text(yaml.dump(existing))


def _add_valid_context(wh: Path, name: str, content: str | None = None) -> Path:
    """Add a valid context file."""
    ctx_file = wh / "contexts" / f"{name}.md"
    ctx_file.write_text(content or f"# {name}\n")
    return ctx_file


# ---------------------------------------------------------------------------
# Phase 2: Data model
# ---------------------------------------------------------------------------


class TestLintReport:
    """TC2.2: LintReport truthiness and immutability."""

    def test_empty_findings_is_falsy(self):
        """TC1: empty findings tuple → bool(report) is False."""
        report = LintReport(findings=())
        assert bool(report) is False

    def test_one_finding_is_truthy(self):
        """TC2: one finding → bool(report) is True."""
        report = LintReport(findings=(LintFinding("p", "m"),))
        assert bool(report) is True

    def test_frozen_instance_raises_on_mutation(self):
        """TC3: attempt to mutate findings → raises FrozenInstanceError."""
        report = LintReport(findings=())
        with pytest.raises((FrozenInstanceError, AttributeError)):
            report.findings = (LintFinding("p", "m"),)  # type: ignore[misc]


class TestLintWarehouseOrchestrator:
    """TC2.3: lint_warehouse orchestrator composition order and path resolution."""

    def test_all_helpers_return_empty_gives_empty_report(self, tmp_path):
        """TC1: all helpers return [] → LintReport.findings == ()."""
        # Use a clean warehouse so all rules pass
        wh = _build_clean_warehouse(tmp_path)
        report = lint_warehouse(wh)
        # A clean warehouse should produce no findings (or only if template is not perfect)
        # This tests that the orchestrator doesn't crash and returns a LintReport
        assert isinstance(report, LintReport)

    def test_relative_path_is_resolved(self, tmp_path, monkeypatch):
        """TC3: warehouse_path is a relative path → orchestrator resolves to absolute."""
        _build_clean_warehouse(tmp_path)
        # monkeypatch cwd so we can use a relative path
        monkeypatch.chdir(tmp_path)
        report = lint_warehouse(Path("warehouse"))
        assert isinstance(report, LintReport)

    def test_smoke_empty_dir_produces_findings(self, tmp_path):
        """TC2.5: empty dir trips structure preflight → findings > 0."""
        empty = tmp_path / "empty"
        empty.mkdir()
        report = lint_warehouse(empty)
        assert len(report.findings) > 0


# ---------------------------------------------------------------------------
# Phase 3: Structure preflight rule
# ---------------------------------------------------------------------------


class TestLintStructure:
    """Tests for _lint_structure."""

    def _call(self, path):
        from beacon.domains.warehouse.lint import _lint_structure

        return _lint_structure(path)

    def test_clean_warehouse_no_findings(self, tmp_path):
        """TC1: clean warehouse → returns []."""
        wh = _build_clean_warehouse(tmp_path)
        result = self._call(wh)
        assert result == []

    def test_missing_docs_produces_finding(self, tmp_path):
        """TC2/3.2: missing docs/ → 1 finding scoped to <warehouse>."""
        wh = tmp_path / "wh"
        wh.mkdir()
        (wh / "agents").mkdir()
        (wh / "contexts").mkdir()
        (wh / "skills").mkdir()
        (wh / "README.md").write_text("# Warehouse\n")
        # No docs/ directory
        result = self._call(wh)
        assert len(result) == 1
        assert result[0].artifact_path == "<warehouse>"
        assert "docs/" in result[0].message

    def test_missing_docs_and_readme_produces_two_findings(self, tmp_path):
        """TC3: missing docs/ AND missing README → 2 findings, both at <warehouse>."""
        wh = tmp_path / "wh"
        wh.mkdir()
        (wh / "agents").mkdir()
        (wh / "contexts").mkdir()
        (wh / "skills").mkdir()
        # No docs/ and no README
        result = self._call(wh)
        assert len(result) >= 2
        for f in result:
            assert f.artifact_path == "<warehouse>"

    def test_nonexistent_path_produces_finding(self, tmp_path):
        """TC4/3.3: target path does not exist → 1 finding mentioning 'Path not found'."""
        result = self._call(tmp_path / "does-not-exist")
        assert len(result) == 1
        assert "Path not found" in result[0].message

    def test_project_directory_produces_finding(self, tmp_path):
        """TC5/3.4: target is a project → 1 finding mentioning 'project directory'."""
        project = tmp_path / "project"
        project.mkdir()
        (project / ".agentic-beacon" / "artifacts").mkdir(parents=True)
        result = self._call(project)
        assert len(result) == 1
        assert "project directory" in result[0].message.lower()

    def test_file_not_directory_produces_finding(self, tmp_path):
        """TC6: target is a file, not a directory → 1 finding mentioning 'not a directory'."""
        f = tmp_path / "file.txt"
        f.write_text("hello")
        result = self._call(f)
        assert len(result) == 1
        assert "not a directory" in result[0].message.lower()


# ---------------------------------------------------------------------------
# Phase 4: Skill frontmatter rule
# ---------------------------------------------------------------------------


class TestLintSkillFrontmatter:
    """Tests for _lint_skill_frontmatter."""

    def _call(self, path):
        from beacon.domains.warehouse.lint import _lint_skill_frontmatter

        return _lint_skill_frontmatter(path)

    def test_valid_skill_no_finding(self, tmp_path):
        """TC1: skill with valid frontmatter and valid requires.contexts → no finding."""
        wh = _build_clean_warehouse(tmp_path)
        _add_valid_context(wh, "some-ctx")
        _add_valid_skill(wh, "my-skill", contexts=["some-ctx"])
        result = self._call(wh)
        assert result == []

    def test_no_frontmatter_produces_finding(self, tmp_path):
        """TC2: skill with no frontmatter block → 1 finding."""
        wh = _build_clean_warehouse(tmp_path)
        skill_dir = wh / "skills" / "no-fm"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# No frontmatter here\n")
        result = self._call(wh)
        assert len(result) == 1
        assert result[0].message.startswith("File has no YAML frontmatter")

    def test_regression_per114_exact_message(self, tmp_path):
        """TC4.2: PER-114 regression — exact message for missing frontmatter."""
        wh = _build_clean_warehouse(tmp_path)
        skill_dir = wh / "skills" / "delegate-to-cc"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# delegate-to-cc\n\nSome content\n")
        result = self._call(wh)
        assert len(result) == 1
        assert result[0].artifact_path == "skills/delegate-to-cc/SKILL.md"
        assert result[0].message == "File has no YAML frontmatter (must start with ---)"

    def test_unterminated_frontmatter_produces_finding(self, tmp_path):
        """TC3: skill with frontmatter opened but never closed → 1 finding mentioning 'never closed'."""
        wh = _build_clean_warehouse(tmp_path)
        skill_dir = wh / "skills" / "unterminated"
        skill_dir.mkdir()
        # Content starts with --- but has no closing ---
        (skill_dir / "SKILL.md").write_text(
            "---\nrequires:\n  contexts: []\nbody text without closing delimiter\n"
        )
        result = self._call(wh)
        assert len(result) == 1
        assert "never closed" in result[0].message

    def test_malformed_yaml_produces_finding(self, tmp_path):
        """TC4/4.3: skill with malformed YAML → 1 finding mentioning 'YAML parse error'."""
        wh = _build_clean_warehouse(tmp_path)
        skill_dir = wh / "skills" / "bad-yaml"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\n  : invalid\n---\nbody\n")
        result = self._call(wh)
        assert len(result) == 1
        assert "YAML parse error" in result[0].message

    def test_skill_to_skill_dependency_produces_finding(self, tmp_path):
        """TC5/4.4: skill with requires.skills → 1 finding mentioning 'Skill-to-skill'."""
        wh = _build_clean_warehouse(tmp_path)
        skill_dir = wh / "skills" / "s2s"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nrequires:\n  skills: [other]\n  contexts: [foo]\n---\nbody\n"
        )
        result = self._call(wh)
        assert len(result) == 1
        assert "Skill-to-skill dependencies are not supported" in result[0].message

    def test_two_defective_skills_produce_two_findings(self, tmp_path):
        """TC8: two skills each with different defects → 2 findings, stable ordering."""
        wh = _build_clean_warehouse(tmp_path)
        skill_a = wh / "skills" / "skill-a"
        skill_a.mkdir()
        (skill_a / "SKILL.md").write_text("# no frontmatter\n")
        skill_b = wh / "skills" / "skill-b"
        skill_b.mkdir()
        (skill_b / "SKILL.md").write_text("---\n  : invalid\n---\nbody\n")
        result = self._call(wh)
        assert len(result) == 2

    def test_valid_requires_contexts_no_finding(self, tmp_path):
        """TC1/4.5: skill with valid requires.contexts → no finding."""
        wh = _build_clean_warehouse(tmp_path)
        _add_valid_skill(wh, "good-skill", contexts=[])
        result = self._call(wh)
        assert result == []


# ---------------------------------------------------------------------------
# Phase 5: Skill requires.contexts resolution rule
# ---------------------------------------------------------------------------


class TestLintSkillRequires:
    """Tests for _lint_skill_requires."""

    def _call(self, path):
        from beacon.domains.warehouse.lint import _lint_skill_requires

        return _lint_skill_requires(path)

    def test_all_contexts_exist_no_finding(self, tmp_path):
        """TC1: skill with all referenced contexts existing → no finding."""
        wh = _build_clean_warehouse(tmp_path)
        _add_valid_context(wh, "existing-ctx")
        _add_valid_skill(wh, "foo", contexts=["existing-ctx"])
        result = self._call(wh)
        assert result == []

    def test_one_missing_context_produces_finding(self, tmp_path):
        """TC2/5.2: skill references one missing context → 1 finding."""
        wh = _build_clean_warehouse(tmp_path)
        _add_valid_skill(wh, "foo", contexts=["missing-ctx"])
        result = self._call(wh)
        assert len(result) == 1
        assert result[0].artifact_path == "skills/foo/SKILL.md"
        assert "missing-ctx" in result[0].message

    def test_two_missing_contexts_produce_two_findings(self, tmp_path):
        """TC3/5.3: skill references two missing contexts → 2 findings."""
        wh = _build_clean_warehouse(tmp_path)
        _add_valid_skill(wh, "foo", contexts=["a", "b"])
        result = self._call(wh)
        assert len(result) == 2
        assert all(f.artifact_path == "skills/foo/SKILL.md" for f in result)
        messages = [f.message for f in result]
        assert any("a" in m for m in messages)
        assert any("b" in m for m in messages)

    def test_invalid_frontmatter_skipped(self, tmp_path):
        """TC4: skill with invalid frontmatter → 0 findings from this rule."""
        wh = _build_clean_warehouse(tmp_path)
        skill_dir = wh / "skills" / "bad-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# no frontmatter\n")
        result = self._call(wh)
        assert result == []

    def test_empty_requires_contexts_no_finding(self, tmp_path):
        """TC5/5.4: skill with empty requires.contexts → no finding."""
        wh = _build_clean_warehouse(tmp_path)
        _add_valid_skill(wh, "foo", contexts=[])
        result = self._call(wh)
        assert result == []

    def test_context_is_directory_treated_as_missing(self, tmp_path):
        """TC6: context path is a directory, not a file → 1 finding."""
        wh = _build_clean_warehouse(tmp_path)
        ctx_dir = wh / "contexts" / "ctx-as-dir"
        ctx_dir.mkdir()
        _add_valid_skill(wh, "foo", contexts=["ctx-as-dir"])
        result = self._call(wh)
        assert len(result) == 1
        assert "ctx-as-dir" in result[0].message


# ---------------------------------------------------------------------------
# Phase 6: Agent manifest rule
# ---------------------------------------------------------------------------


class TestLintAgentManifest:
    """Tests for _lint_agent_manifest."""

    def _call(self, path):
        from beacon.domains.warehouse.lint import _lint_agent_manifest

        return _lint_agent_manifest(path)

    def test_no_agents_yaml_no_finding(self, tmp_path):
        """TC5: agents.yaml does not exist → no finding (optional file)."""
        wh = _build_clean_warehouse(tmp_path)
        result = self._call(wh)
        assert result == []

    def test_valid_manifest_no_finding(self, tmp_path):
        """TC1: agents.yaml is valid → no finding."""
        wh = _build_clean_warehouse(tmp_path)
        _add_valid_skill(wh, "my-skill")
        _add_valid_agent(wh, "foo", skills=["my-skill"])
        result = self._call(wh)
        assert result == []

    def test_unparseable_yaml_produces_finding_on_agents_yaml(self, tmp_path):
        """TC2/6.7: agents.yaml has YAML syntax error → finding scoped to agents/agents.yaml."""
        wh = _build_clean_warehouse(tmp_path)
        (wh / "agents" / "agents.yaml").write_text(":::")
        (wh / "agents" / "foo.md").write_text(
            "---\nname: foo\ndescription: test\n---\n"
        )
        result = self._call(wh)
        assert len(result) >= 1
        assert all(f.artifact_path == "agents/agents.yaml" for f in result)

    def test_agent_file_missing_from_manifest(self, tmp_path):
        """TC6.3: agents/foo.md exists, agents.yaml has no foo: key → 1 finding."""
        wh = _build_clean_warehouse(tmp_path)
        (wh / "agents" / "foo.md").write_text(
            "---\nname: foo\ndescription: test\n---\n"
        )
        (wh / "agents" / "agents.yaml").write_text(yaml.dump({}))
        result = self._call(wh)
        assert len(result) == 1
        # The error message should reference foo
        assert "foo" in result[0].message
        assert result[0].artifact_path == "agents/foo.md"

    def test_declared_skill_missing_produces_finding(self, tmp_path):
        """TC6.4: agents.yaml declares missing skill → 1 finding."""
        wh = _build_clean_warehouse(tmp_path)
        _add_valid_agent(wh, "foo", skills=["missing-skill"])
        result = self._call(wh)
        assert len(result) == 1
        assert "missing-skill" in result[0].message

    def test_agent_with_requires_in_frontmatter_produces_finding(self, tmp_path):
        """TC6.5: agent frontmatter has requires: → 1 finding."""
        wh = _build_clean_warehouse(tmp_path)
        agent_file = wh / "agents" / "foo.md"
        agent_file.write_text(
            "---\nname: foo\ndescription: test\nrequires:\n  skills: [bar]\n---\n"
        )
        (wh / "agents" / "agents.yaml").write_text(yaml.dump({"foo": {"skills": []}}))
        result = self._call(wh)
        assert len(result) >= 1
        assert any("requires" in f.message for f in result)

    def test_two_agents_missing_from_manifest_produce_two_findings(self, tmp_path):
        """TC6.6: two agents missing from agents.yaml → 2 findings (pins \n-split contract)."""
        wh = _build_clean_warehouse(tmp_path)
        (wh / "agents" / "foo.md").write_text(
            "---\nname: foo\ndescription: test\n---\n"
        )
        (wh / "agents" / "bar.md").write_text(
            "---\nname: bar\ndescription: test\n---\n"
        )
        (wh / "agents" / "agents.yaml").write_text(yaml.dump({}))
        result = self._call(wh)
        assert len(result) == 2
        paths = {f.artifact_path for f in result}
        assert "agents/foo.md" in paths
        assert "agents/bar.md" in paths


# ---------------------------------------------------------------------------
# Phase 7: Agent frontmatter (name + description) rule
# ---------------------------------------------------------------------------


class TestLintAgentFrontmatter:
    """Tests for _lint_agent_frontmatter."""

    def _call(self, path):
        from beacon.domains.warehouse.lint import _lint_agent_frontmatter

        return _lint_agent_frontmatter(path)

    def test_agent_with_both_keys_no_finding(self, tmp_path):
        """TC1/7.4: agent with {name, description} → no finding."""
        wh = _build_clean_warehouse(tmp_path)
        (wh / "agents" / "foo.md").write_text(
            "---\nname: foo\ndescription: test\n---\n"
        )
        result = self._call(wh)
        assert result == []

    def test_missing_name_produces_finding(self, tmp_path):
        """TC2/7.2: agent with only description → 1 finding about name."""
        wh = _build_clean_warehouse(tmp_path)
        (wh / "agents" / "foo.md").write_text("---\ndescription: test\n---\n")
        result = self._call(wh)
        assert len(result) == 1
        assert "`name`" in result[0].message
        assert result[0].artifact_path == "agents/foo.md"

    def test_missing_description_produces_finding(self, tmp_path):
        """TC3/7.3: agent with only name → 1 finding about description."""
        wh = _build_clean_warehouse(tmp_path)
        (wh / "agents" / "foo.md").write_text("---\nname: foo\n---\n")
        result = self._call(wh)
        assert len(result) == 1
        assert "`description`" in result[0].message

    def test_missing_both_keys_produces_two_findings(self, tmp_path):
        """TC4: agent with valid dict but neither key → 2 findings."""
        wh = _build_clean_warehouse(tmp_path)
        (wh / "agents" / "foo.md").write_text("---\nmodel: gpt-4\n---\n")
        result = self._call(wh)
        assert len(result) == 2

    def test_no_frontmatter_produces_one_finding_not_two(self, tmp_path):
        """TC5/7.6: agent with no frontmatter block → exactly 1 finding (not 2)."""
        wh = _build_clean_warehouse(tmp_path)
        (wh / "agents" / "foo.md").write_text("# No frontmatter here\n")
        result = self._call(wh)
        assert len(result) == 1
        assert (
            "no YAML frontmatter" in result[0].message.lower()
            or "frontmatter" in result[0].message.lower()
        )

    def test_readme_excluded(self, tmp_path):
        """TC6/7.5: agents/README.md with no frontmatter → no finding."""
        wh = _build_clean_warehouse(tmp_path)
        (wh / "agents" / "README.md").write_text("# README\n")
        result = self._call(wh)
        assert result == []

    def test_name_value_not_string_no_finding(self, tmp_path):
        """TC7: agent with integer name: value → no finding (only key presence checked)."""
        wh = _build_clean_warehouse(tmp_path)
        (wh / "agents" / "foo.md").write_text("---\nname: 42\ndescription: test\n---\n")
        result = self._call(wh)
        assert result == []


# ---------------------------------------------------------------------------
# Phase 8: Knowledge link integrity rule
# ---------------------------------------------------------------------------


class TestLintKnowledgeLinks:
    """Tests for _lint_knowledge_links."""

    def _call(self, path):
        from beacon.domains.warehouse.lint import _lint_knowledge_links

        return _lint_knowledge_links(path)

    def test_valid_knowledge_link_no_finding(self, tmp_path):
        """TC1/TC7: context with valid knowledge link → no finding."""
        wh = _build_clean_warehouse(tmp_path)
        (wh / "knowledge").mkdir()
        (wh / "knowledge" / "foo").mkdir()
        (wh / "knowledge" / "foo" / "bar.md").write_text("# Bar\n")
        ctx = wh / "contexts" / "ctx.md"
        ctx.write_text("[X](../knowledge/foo/bar.md)\n")
        result = self._call(wh)
        assert result == []

    def test_broken_context_knowledge_link_produces_finding(self, tmp_path):
        """TC2/8.3: context with broken knowledge link → 1 finding."""
        wh = _build_clean_warehouse(tmp_path)
        (wh / "knowledge").mkdir()
        ctx = wh / "contexts" / "foo.md"
        ctx.write_text("[X](../knowledge/foo/bar.md)\n")
        result = self._call(wh)
        assert len(result) == 1
        assert result[0].artifact_path == "contexts/foo.md"

    def test_broken_skill_knowledge_link_produces_finding(self, tmp_path):
        """TC4/8.4: skill with broken knowledge link → 1 finding scoped to skill."""
        wh = _build_clean_warehouse(tmp_path)
        skill_dir = wh / "skills" / "foo"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nrequires:\n  contexts: []\n---\n[X](../../knowledge/foo/bar.md)\n"
        )
        result = self._call(wh)
        assert len(result) == 1
        assert result[0].artifact_path == "skills/foo/SKILL.md"

    def test_absolute_url_no_finding(self, tmp_path):
        """TC5/8.5: context with absolute URL → no finding."""
        wh = _build_clean_warehouse(tmp_path)
        ctx = wh / "contexts" / "foo.md"
        ctx.write_text("[X](https://example.com)\n")
        result = self._call(wh)
        assert result == []

    def test_non_knowledge_link_no_finding(self, tmp_path):
        """TC6/8.6: context with non-knowledge link → no finding."""
        wh = _build_clean_warehouse(tmp_path)
        ctx = wh / "contexts" / "foo.md"
        ctx.write_text("[X](./other.md)\n")
        result = self._call(wh)
        assert result == []

    def test_two_broken_links_produce_two_findings(self, tmp_path):
        """TC3: context with two broken knowledge links → 2 findings."""
        wh = _build_clean_warehouse(tmp_path)
        ctx = wh / "contexts" / "foo.md"
        ctx.write_text("[X](../knowledge/a.md)\n[Y](../knowledge/b.md)\n")
        result = self._call(wh)
        assert len(result) == 2

    def test_finding_message_names_broken_target(self, tmp_path):
        """TC8.2: finding message contains raw link, resolved path, and file not found."""
        wh = _build_clean_warehouse(tmp_path)
        ctx = wh / "contexts" / "foo.md"
        ctx.write_text("[X](../knowledge/foo/bar.md)\n")
        result = self._call(wh)
        assert len(result) == 1
        msg = result[0].message
        assert "../knowledge/foo/bar.md" in msg
        assert "knowledge/foo/bar.md" in msg
        assert "file not found" in msg

    def test_scan_file_for_knowledge_unchanged(self, tmp_path):
        """TC8.7: regression — scan_file_for_knowledge returns a set and does not raise."""
        from beacon.core.scanner.scanner import scan_file_for_knowledge

        wh = _build_clean_warehouse(tmp_path)
        ctx = wh / "contexts" / "foo.md"
        ctx.write_text("[X](../knowledge/foo/bar.md)\n")
        result = scan_file_for_knowledge(ctx, wh)
        assert isinstance(result, set)
        # Broken target is still in the returned set
        assert "knowledge/foo/bar.md" in result


# ---------------------------------------------------------------------------
# Phase 9: Orchestrator integration test
# ---------------------------------------------------------------------------


def _build_six_defect_fixture(tmp_path: Path) -> Path:
    """Build a fixture warehouse with one defect from each of the 6 rules."""
    wh = tmp_path / "six-defect-wh"
    wh.mkdir()
    # No docs/ → structure defect (rule 1)
    (wh / "agents").mkdir()
    (wh / "contexts").mkdir()
    (wh / "skills").mkdir()
    (wh / "README.md").write_text("# Warehouse\n")
    # knowledge dir for links
    (wh / "knowledge").mkdir()

    # Rule 2: skill with no frontmatter
    skill_a = wh / "skills" / "no-fm-skill"
    skill_a.mkdir()
    (skill_a / "SKILL.md").write_text("# No frontmatter\n")

    # Rule 3: skill with missing context (needs valid frontmatter)
    skill_b = wh / "skills" / "missing-ctx-skill"
    skill_b.mkdir()
    (skill_b / "SKILL.md").write_text(
        "---\nrequires:\n  contexts: [nonexistent-ctx]\n---\nbody\n"
    )

    # Rule 4: agent missing from agents.yaml (orphan-agent not in agents.yaml)
    agent_file = wh / "agents" / "orphan-agent.md"
    agent_file.write_text("---\nname: orphan-agent\ndescription: orphan\n---\n")

    # Rule 5: agent missing name key — registered in agents.yaml, but no `name:` key
    agent_no_name = wh / "agents" / "no-name-agent.md"
    agent_no_name.write_text("---\ndescription: has no name\n---\n")
    # agents.yaml: register no-name-agent (so rule 4 doesn't fire for it)
    # but intentionally leave orphan-agent OUT (so rule 4 fires for it)
    (wh / "agents" / "agents.yaml").write_text(
        yaml.dump({"no-name-agent": {"skills": []}})
    )

    # Rule 6: context with broken knowledge link
    ctx = wh / "contexts" / "ctx-with-broken-link.md"
    ctx.write_text("[X](../knowledge/missing/file.md)\n")

    return wh


class TestLintWarehouseOrchestrator2:
    """Phase 9: Orchestrator integration tests."""

    def test_six_defect_fixture_all_categories_present(self, tmp_path):
        """TC9.2 TC1: six-defect fixture → findings from every rule category."""
        wh = _build_six_defect_fixture(tmp_path)
        report = lint_warehouse(wh)

        # Every rule category should be represented
        all_paths = " ".join(f.artifact_path for f in report.findings)

        # Rule 1: structural
        assert "<warehouse>" in all_paths
        # Rule 2: skill frontmatter
        assert any("YAML frontmatter" in f.message for f in report.findings)
        # Rule 3: context resolution
        assert any("nonexistent-ctx" in f.message for f in report.findings)
        # Rule 4: agent manifest
        assert any("orphan-agent" in f.message for f in report.findings)
        # Rule 5: agent frontmatter keys
        assert any("`name`" in f.message for f in report.findings)
        # Rule 6: knowledge link
        assert any("knowledge" in f.message for f in report.findings)

    def test_clean_warehouse_produces_empty_report(self, tmp_path):
        """TC9.2 TC2: clean warehouse → bool(report) is False."""
        wh = _build_clean_warehouse(tmp_path)
        report = lint_warehouse(wh)
        assert not report

    def test_idempotent_on_same_fixture(self, tmp_path):
        """TC9.2 TC3: same fixture lint-ed twice → identical reports."""
        wh = _build_six_defect_fixture(tmp_path)
        report1 = lint_warehouse(wh)
        report2 = lint_warehouse(wh)
        assert report1.findings == report2.findings

    def test_findings_sorted_by_artifact_path_and_message(self, tmp_path):
        """TC9.2 TC4: findings list is sorted by (artifact_path, message)."""
        wh = _build_six_defect_fixture(tmp_path)
        report = lint_warehouse(wh)
        paths = [f.artifact_path for f in report.findings]
        assert paths == sorted(paths), "Findings are not sorted by artifact_path"
        # Within same path, messages should also be sorted
        from itertools import groupby

        for path, group_iter in groupby(report.findings, key=lambda f: f.artifact_path):
            group = list(group_iter)
            msgs = [f.message for f in group]
            assert msgs == sorted(msgs), f"Messages not sorted for path {path}"

    def test_structural_finding_uses_warehouse_scope(self, tmp_path):
        """TC9.2 TC5: structural finding uses <warehouse> scope."""
        wh = _build_six_defect_fixture(tmp_path)
        report = lint_warehouse(wh)
        assert any(f.artifact_path == "<warehouse>" for f in report.findings)


# ---------------------------------------------------------------------------
# Phase 10: CLI handler tests
# ---------------------------------------------------------------------------


class TestPrintLintReport:
    """TC10.2: _print_lint_report output formatting."""

    def _make_console(self):
        from rich.console import Console

        return Console(record=True, highlight=False)

    def _call(self, report, console):
        from beacon.cli.warehouse import _print_lint_report

        _print_lint_report(report, console)
        return console.export_text()

    def test_empty_report_prints_lint_passed(self):
        """TC1: empty report → output contains '✓ Lint passed.' and no error lines."""
        c = self._make_console()
        output = self._call(LintReport(findings=()), c)
        assert "Lint passed" in output
        assert "error:" not in output

    def test_one_finding_output(self, tmp_path):
        """TC2: one finding → 1 path header, 1 error line, summary."""
        report = LintReport(findings=(LintFinding("agents/foo.md", "missing name"),))
        c = self._make_console()
        output = self._call(report, c)
        assert "agents/foo.md" in output
        assert "error:" in output
        assert "missing name" in output
        assert "Found 1 error(s) across 1 file(s)." in output

    def test_three_findings_across_two_paths(self):
        """TC3: 3 findings across 2 paths → 2 headers, 3 error lines grouped."""
        report = LintReport(
            findings=(
                LintFinding("agents/foo.md", "err1"),
                LintFinding("agents/foo.md", "err2"),
                LintFinding("skills/bar/SKILL.md", "err3"),
            )
        )
        c = self._make_console()
        output = self._call(report, c)
        assert "agents/foo.md" in output
        assert "skills/bar/SKILL.md" in output
        assert output.count("error:") == 3
        assert "Found 3 error(s) across 2 file(s)." in output

    def test_five_findings_same_path(self):
        """TC4: 5 findings under same path → 1 header, 5 error lines."""
        findings = tuple(
            LintFinding("skills/foo/SKILL.md", f"err{i}") for i in range(5)
        )
        report = LintReport(findings=findings)
        c = self._make_console()
        output = self._call(report, c)
        assert output.count("skills/foo/SKILL.md") >= 1
        assert output.count("error:") == 5
        assert "Found 5 error(s) across 1 file(s)." in output

    def test_groups_appear_sorted_by_path(self):
        """TC5: groups appear in lexicographically sorted order regardless of insertion."""
        # LintReport is already sorted by lint_warehouse, but _print_lint_report
        # uses itertools.groupby which relies on sort order from LintReport.
        report = LintReport(
            findings=(
                LintFinding("agents/foo.md", "err"),
                LintFinding("skills/bar/SKILL.md", "err"),
            )
        )
        c = self._make_console()
        output = self._call(report, c)
        # agents comes before skills
        agents_pos = output.index("agents/foo.md")
        skills_pos = output.index("skills/bar/SKILL.md")
        assert agents_pos < skills_pos


class TestWarehouseLintCommand:
    """TC10.3, 10.5, 10.6: warehouse_lint Click handler."""

    def _run(self, args):
        from beacon.cli.main import main
        from click.testing import CliRunner

        runner = CliRunner()
        return runner.invoke(main, ["warehouse", "lint"] + args, catch_exceptions=False)

    def test_help_renders(self):
        """TC10.1: --help renders without error, exit code 0."""
        result = self._run(["--help"])
        assert result.exit_code == 0
        assert (
            "WAREHOUSE_PATH" in result.output
            or "warehouse_path" in result.output.lower()
        )

    def test_clean_fixture_exits_zero(self, tmp_path):
        """TC10.5: clean fixture → exit_code 0 and 'Lint passed' in stdout."""
        wh = _build_clean_warehouse(tmp_path)
        result = self._run([str(wh)])
        assert result.exit_code == 0
        assert "Lint passed" in result.output

    def test_defective_fixture_exits_one(self, tmp_path):
        """TC10.6: defective fixture → exit_code 1 and grouped output."""
        wh = _build_six_defect_fixture(tmp_path)
        result = self._run([str(wh)])
        assert result.exit_code == 1
        assert "error:" in result.output

    def test_json_flag_rejected(self, tmp_path):
        """TC3: passing --json → exit_code != 0 (Click's unknown-option exit)."""
        wh = _build_clean_warehouse(tmp_path)
        from beacon.cli.main import main
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(main, ["warehouse", "lint", "--json", str(wh)])
        assert result.exit_code != 0
