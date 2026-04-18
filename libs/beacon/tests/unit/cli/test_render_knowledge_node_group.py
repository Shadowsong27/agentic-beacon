"""Unit tests for _render_knowledge_node_group — fraction badge display.

When a knowledge node has missing files, the header badge should show the count
as a fraction of the total files in the warehouse node (e.g. "2/5 missing")
rather than a plain count.  Other statuses show plain counts.

Test Cases:
- TC1: all files missing → shows "N/N missing" (full fraction)
- TC2: some files missing → shows "2/5 missing" (partial fraction)
- TC3: modified files → shows plain "1 modified" (no fraction)
- TC4: mixed statuses → missing is fractional, modified is plain
- TC5: warehouse node dir is empty → falls back to plain missing count
"""

from io import StringIO
from pathlib import Path

# We capture Rich output by redirecting the module-level console.
# _render_knowledge_node_group uses the module-level `console` from utils/delta,
# so we monkey-patch it.
import beacon.utils.delta as delta_module
from beacon.core.delta import DeltaStatus
from beacon.utils.delta import _render_knowledge_node_group
from rich.console import Console

_STATUS_MARKUP = {
    DeltaStatus.MODIFIED: "[yellow]modified[/yellow]",
    DeltaStatus.MISSING: "[red]missing[/red]",
    DeltaStatus.ADDED: "[green]added[/green]",
    DeltaStatus.STALE: "[dim cyan]stale[/dim cyan]",
}


def _capture(node_path: str, results, warehouse_path: Path) -> str:
    buf = StringIO()
    patched = Console(file=buf, highlight=False, markup=True)
    original = delta_module.console
    delta_module.console = patched
    try:
        _render_knowledge_node_group(node_path, results, _STATUS_MARKUP, warehouse_path)
    finally:
        delta_module.console = original
    return buf.getvalue()


def _make_result(path: str, status: DeltaStatus):
    from beacon.core.delta import ComparisonResult

    return ComparisonResult(path=path, status=status)


class TestRenderKnowledgeNodeGroupFraction:
    def test_tc1_all_missing_shows_full_fraction(self, tmp_path):
        """TC1: 3 warehouse files, all missing → '3/3 missing'."""
        node = tmp_path / "knowledge" / "python"
        (node / "decisions").mkdir(parents=True)
        for name in ("a.md", "b.md", "c.md"):
            (node / "decisions" / name).write_text("# x")

        results = [
            _make_result("knowledge/python/decisions/a.md", DeltaStatus.MISSING),
            _make_result("knowledge/python/decisions/b.md", DeltaStatus.MISSING),
            _make_result("knowledge/python/decisions/c.md", DeltaStatus.MISSING),
        ]
        output = _capture("knowledge/python", results, tmp_path)
        assert "3/3 missing" in output

    def test_tc2_partial_missing_shows_fraction(self, tmp_path):
        """TC2: 5 warehouse files, 2 missing → '2/5 missing'."""
        node = tmp_path / "knowledge" / "python"
        node.mkdir(parents=True)
        for i in range(5):
            (node / f"file{i}.md").write_text("# x")

        results = [
            _make_result("knowledge/python/file0.md", DeltaStatus.MISSING),
            _make_result("knowledge/python/file1.md", DeltaStatus.MISSING),
        ]
        output = _capture("knowledge/python", results, tmp_path)
        assert "2/5 missing" in output

    def test_tc3_modified_shows_plain_count(self, tmp_path):
        """TC3: modified files use plain count, not a fraction."""
        node = tmp_path / "knowledge" / "python"
        node.mkdir(parents=True)
        (node / "doc.md").write_text("# x")

        results = [_make_result("knowledge/python/doc.md", DeltaStatus.MODIFIED)]
        output = _capture("knowledge/python", results, tmp_path)
        assert "1 modified" in output
        assert "/" not in output.split("modified")[0].split("[")[-1]

    def test_tc4_mixed_missing_fractional_modified_plain(self, tmp_path):
        """TC4: 3 warehouse files, 1 missing + 1 modified → '1/3 missing' and '1 modified'."""
        node = tmp_path / "knowledge" / "python"
        node.mkdir(parents=True)
        for name in ("a.md", "b.md", "c.md"):
            (node / name).write_text("# x")

        results = [
            _make_result("knowledge/python/a.md", DeltaStatus.MISSING),
            _make_result("knowledge/python/b.md", DeltaStatus.MODIFIED),
        ]
        output = _capture("knowledge/python", results, tmp_path)
        assert "1/3 missing" in output
        assert "1 modified" in output

    def test_tc5_empty_warehouse_node_falls_back_to_plain_count(self, tmp_path):
        """TC5: warehouse node dir has no .md files → plain '2 missing' (no fraction)."""
        node = tmp_path / "knowledge" / "python"
        node.mkdir(parents=True)
        # No .md files in warehouse node

        results = [
            _make_result("knowledge/python/a.md", DeltaStatus.MISSING),
            _make_result("knowledge/python/b.md", DeltaStatus.MISSING),
        ]
        output = _capture("knowledge/python", results, tmp_path)
        # total_in_node == 0, so fraction is skipped → plain count
        assert "2 missing" in output
        assert "2/0" not in output
