"""Unit tests for artifact-link autofix in beacon.domains.warehouse.lint."""

from __future__ import annotations

from pathlib import Path

from beacon.domains.warehouse.lint import lint_warehouse
from click.testing import CliRunner


def _build_clean_warehouse(root: Path) -> Path:
    wh = root / "warehouse"
    wh.mkdir()
    (wh / "agents").mkdir()
    (wh / "contexts").mkdir()
    (wh / "skills").mkdir()
    (wh / "docs").mkdir()
    (wh / "knowledge").mkdir()
    (wh / "README.md").write_text("# Warehouse\n")
    (wh / "agents" / "README.md").write_text("# Agents\n")
    (wh / "contexts" / "README.md").write_text("# Contexts\n")
    (wh / "skills" / "README.md").write_text("# Skills\n")
    return wh


def _add_valid_skill(wh: Path, name: str) -> Path:
    skill_dir = wh / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("---\nrequires:\n  contexts: []\n---\n# Skill\n")
    return skill_file


def _run_cli(args: list[str]):
    from beacon.cli.main import main

    return CliRunner().invoke(
        main, ["warehouse", "lint"] + args, catch_exceptions=False
    )


class TestLintFix:
    def test_fix_rewrites_cross_artifact_relative_link(self, tmp_path):
        """TC1: fix rewrites a cross-artifact relative link and preserves anchor."""
        wh = _build_clean_warehouse(tmp_path)
        (wh / "contexts" / "bar.md").write_text("# Multi Repo\n")
        skill_file = _add_valid_skill(wh, "foo")
        skill_file.write_text(
            "---\nrequires:\n  contexts: []\n---\n"
            "[ctx](../../contexts/bar.md#multi-repo)\n"
        )

        report = lint_warehouse(wh, fix=True)

        assert report.rewritten_links == 1
        assert report.files_touched == 1
        assert report.findings == ()
        assert (
            skill_file.read_text() == "---\nrequires:\n  contexts: []\n---\n"
            "[ctx](.agentic-beacon/artifacts/contexts/bar.md#multi-repo)\n"
        )

    def test_fix_leaves_own_folder_link_unchanged(self, tmp_path):
        """TC2: own-folder skill link stays byte-identical."""
        wh = _build_clean_warehouse(tmp_path)
        skill_file = _add_valid_skill(wh, "foo")
        ref_dir = wh / "skills" / "foo" / "references"
        ref_dir.mkdir(parents=True)
        (ref_dir / "api.md").write_text("# API\n")
        original = "---\nrequires:\n  contexts: []\n---\n[api](references/api.md)\n"
        skill_file.write_text(original)

        report = lint_warehouse(wh, fix=True)

        assert report.rewritten_links == 0
        assert report.files_touched == 0
        assert skill_file.read_text() == original

    def test_fix_leaves_absolute_url_unchanged(self, tmp_path):
        """TC3: absolute URL stays untouched."""
        wh = _build_clean_warehouse(tmp_path)
        ctx = wh / "contexts" / "foo.md"
        original = "[site](https://example.com/docs)\n"
        ctx.write_text(original)

        report = lint_warehouse(wh, fix=True)

        assert report.rewritten_links == 0
        assert report.files_touched == 0
        assert ctx.read_text() == original

    def test_fix_leaves_canonical_link_unchanged(self, tmp_path):
        """TC4: already-canonical link stays untouched."""
        wh = _build_clean_warehouse(tmp_path)
        (wh / "contexts" / "bar.md").write_text("# Bar\n")
        ctx = wh / "contexts" / "foo.md"
        original = "[bar](.agentic-beacon/artifacts/contexts/bar.md)\n"
        ctx.write_text(original)

        report = lint_warehouse(wh, fix=True)

        assert report.rewritten_links == 0
        assert report.files_touched == 0
        assert ctx.read_text() == original

    def test_fix_leaves_warehouse_escape_link_unchanged(self, tmp_path):
        """TC5: warehouse-escape link is not rewritten and remains an error."""
        wh = _build_clean_warehouse(tmp_path)
        skill_file = _add_valid_skill(wh, "foo")
        original = (
            "---\nrequires:\n  contexts: []\n---\n"
            "[escape](../../../apps/backtest/docs/schema.md)\n"
        )
        skill_file.write_text(original)

        report = lint_warehouse(wh, fix=True)

        assert report.rewritten_links == 0
        assert report.files_touched == 0
        assert len(report.findings) == 1
        assert "warehouse-escape link" in report.findings[0].message
        assert skill_file.read_text() == original

    def test_fix_rewrites_multiple_links_on_one_line(self, tmp_path):
        """TC6: multiple fixable links on one line each rewrite independently."""
        wh = _build_clean_warehouse(tmp_path)
        (wh / "contexts" / "bar.md").write_text("# Bar\n")
        (wh / "knowledge" / "topic.md").write_text("# Topic\n")
        ctx = wh / "contexts" / "foo.md"
        ctx.write_text(
            "See [bar](../contexts/bar.md) and [topic](../knowledge/topic.md#topic).\n"
        )

        report = lint_warehouse(wh, fix=True)

        assert report.rewritten_links == 2
        assert report.files_touched == 1
        assert (
            ctx.read_text()
            == "See [bar](.agentic-beacon/artifacts/contexts/bar.md) and "
            "[topic](.agentic-beacon/artifacts/knowledge/topic.md#topic).\n"
        )

    def test_fix_is_idempotent_on_second_run(self, tmp_path):
        """TC1: second --fix run is a byte-identical no-op."""
        wh = _build_clean_warehouse(tmp_path)
        (wh / "contexts" / "bar.md").write_text("# Bar\n")
        skill_file = _add_valid_skill(wh, "foo")
        skill_file.write_text(
            "---\nrequires:\n  contexts: []\n---\n[ctx](../../contexts/bar.md)\n"
        )

        first = lint_warehouse(wh, fix=True)
        after_first = skill_file.read_text()
        second = lint_warehouse(wh, fix=True)

        assert first.rewritten_links == 1
        assert second.rewritten_links == 0
        assert second.files_touched == 0
        assert skill_file.read_text() == after_first

    def test_lint_without_fix_is_read_only(self, tmp_path):
        """TC3: lint without --fix reports errors and does not modify files."""
        wh = _build_clean_warehouse(tmp_path)
        (wh / "contexts" / "bar.md").write_text("# Bar\n")
        skill_file = _add_valid_skill(wh, "foo")
        original = "---\nrequires:\n  contexts: []\n---\n[ctx](../../contexts/bar.md)\n"
        skill_file.write_text(original)

        report = lint_warehouse(wh)

        assert report.rewritten_links == 0
        assert report.files_touched == 0
        assert len(report.findings) == 1
        assert "malformed cross-artifact link" in report.findings[0].message
        assert skill_file.read_text() == original

    def test_fix_on_clean_warehouse_is_no_op(self, tmp_path):
        """TC4: --fix on already-clean warehouse makes no edits and exits cleanly."""
        wh = _build_clean_warehouse(tmp_path)
        (wh / "contexts" / "bar.md").write_text("# Bar\n")
        ctx = wh / "contexts" / "foo.md"
        ctx.write_text("[bar](.agentic-beacon/artifacts/contexts/bar.md)\n")

        report = lint_warehouse(wh, fix=True)

        assert report.rewritten_links == 0
        assert report.files_touched == 0
        assert report.findings == ()

    def test_cli_help_includes_fix_flag(self):
        """Task 3.1: warehouse lint help exposes the --fix flag."""
        result = _run_cli(["--help"])
        assert result.exit_code == 0
        assert "--fix" in result.output

    def test_cli_fix_reports_counts_and_exits_zero_when_clean_after_fix(self, tmp_path):
        """Task 3.3: --fix prints rewrite counts and exits 0 when no errors remain."""
        wh = _build_clean_warehouse(tmp_path)
        (wh / "contexts" / "bar.md").write_text("# Bar\n")
        skill_file = _add_valid_skill(wh, "foo")
        skill_file.write_text(
            "---\nrequires:\n  contexts: []\n---\n[ctx](../../contexts/bar.md)\n"
        )

        result = _run_cli(["--fix", str(wh)])

        assert result.exit_code == 0
        assert "Rewrote 1 link(s) across 1 file(s)." in result.output
        assert "Lint passed" in result.output

    def test_cli_fix_leaves_escape_error_and_exits_one(self, tmp_path):
        """Task 3.3: remaining warehouse-escape errors still print and exit 1."""
        wh = _build_clean_warehouse(tmp_path)
        skill_file = _add_valid_skill(wh, "foo")
        skill_file.write_text(
            "---\nrequires:\n  contexts: []\n---\n[escape](../../../apps/backtest/docs/schema.md)\n"
        )

        report = lint_warehouse(wh, fix=True)
        result = _run_cli(["--fix", str(wh)])

        assert result.exit_code == 1
        assert report.rewritten_links == 0
        assert report.files_touched == 0
        assert "warehouse-escape link" in result.output

    def test_fix_does_not_rewrite_label_when_label_matches_target(self, tmp_path):
        """Regression: rewrite must touch the link target only, never the label.

        A naive ``full_text.replace(group(2), ..., 1)`` finds the first
        occurrence anywhere inside ``[label](target)``, so for
        ``[../../contexts/bar.md](../../contexts/bar.md)`` it rewrites the
        label and leaves the target malformed. PR #159 round-2 review
        (medium severity) — fix uses span-based slicing.
        """
        wh = _build_clean_warehouse(tmp_path)
        (wh / "contexts" / "bar.md").write_text("# Bar\n")
        skill_file = _add_valid_skill(wh, "foo")
        skill_file.write_text(
            "---\nrequires:\n  contexts: []\n---\n"
            "[../../contexts/bar.md](../../contexts/bar.md)\n"
        )

        report = lint_warehouse(wh, fix=True)

        assert report.rewritten_links == 1
        assert report.files_touched == 1
        # Label is byte-preserved; only the target is rewritten to canonical.
        assert (
            skill_file.read_text() == "---\nrequires:\n  contexts: []\n---\n"
            "[../../contexts/bar.md](.agentic-beacon/artifacts/contexts/bar.md)\n"
        )
        # Re-lint must be clean — the rewritten link classifies as canonical.
        relint = lint_warehouse(wh)
        assert relint.findings == ()

    def test_lint_scans_agent_partials_directory(self, tmp_path):
        """``agent-partials/**/*.md`` must be covered by the artifact-link rule.

        Phase 4 made ``agent-partials/`` a first-class artifact family
        mirrored into projects. A malformed cross-artifact link inside a
        shared partial would otherwise pass lint and ship to every
        downstream project. PR #159 round-2 review (medium severity).
        """
        wh = _build_clean_warehouse(tmp_path)
        (wh / "contexts" / "bar.md").write_text("# Bar\n")
        partials_dir = wh / "agent-partials"
        partials_dir.mkdir()
        (partials_dir / "shared-checklist.md").write_text(
            "# Shared Checklist\n\n[ctx](../contexts/bar.md)\n"
        )

        report = lint_warehouse(wh)

        relevant = [f for f in report.findings if "agent-partials" in f.artifact_path]
        assert len(relevant) == 1, (
            f"expected one finding scoped to agent-partials/, got {report.findings}"
        )
        assert relevant[0].artifact_path == "agent-partials/shared-checklist.md"
        assert "malformed cross-artifact link" in relevant[0].message

    def test_fix_rewrites_links_inside_agent_partials(self, tmp_path):
        """``--fix`` must rewrite cross-artifact links inside agent-partials/."""
        wh = _build_clean_warehouse(tmp_path)
        (wh / "contexts" / "bar.md").write_text("# Bar\n")
        partials_dir = wh / "agent-partials"
        partials_dir.mkdir()
        partial_file = partials_dir / "shared-checklist.md"
        partial_file.write_text("# Shared Checklist\n\n[ctx](../contexts/bar.md)\n")

        report = lint_warehouse(wh, fix=True)

        assert report.rewritten_links == 1
        assert report.files_touched == 1
        assert (
            partial_file.read_text()
            == "# Shared Checklist\n\n[ctx](.agentic-beacon/artifacts/contexts/bar.md)\n"
        )
