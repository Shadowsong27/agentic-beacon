"""Tests for WarehouseDistributor.

Regression tests for:
- Bug #3: _list_contexts() only matched AGENTS.*.md (old convention),
  missing plain AGENTS.md files created by 'abc warehouse init'.
- Bug #4: warehouse catalog Usage example showed old AGENTS.global.md format.
"""

import pytest
from beacon.cli import _generate_warehouse_catalog
from beacon.distributor import WarehouseDistributor


@pytest.fixture
def warehouse_with_plain_agents_md(temp_dir):
    """Warehouse whose contexts/ contains AGENTS.md (no dot-name suffix)."""
    wh = temp_dir / "warehouse"
    wh.mkdir()
    (wh / "contexts").mkdir()
    (wh / "knowledge").mkdir()
    (wh / "skills").mkdir()
    (wh / "contexts" / "AGENTS.md").write_text("# Global Context")
    return wh


@pytest.fixture
def warehouse_with_named_agents_md(temp_dir):
    """Warehouse with old-style AGENTS.<name>.md context files."""
    wh = temp_dir / "warehouse"
    wh.mkdir()
    (wh / "contexts").mkdir()
    (wh / "knowledge").mkdir()
    (wh / "skills").mkdir()
    (wh / "contexts" / "AGENTS.global.md").write_text("# Global Context")
    (wh / "contexts" / "AGENTS.python.md").write_text("# Python Context")
    return wh


# ========== Regression: Bug #3 — _list_contexts wrong glob ==========


def test_list_contexts_finds_plain_agents_md(warehouse_with_plain_agents_md, temp_dir):
    """Regression #3: list_available must include AGENTS.md (no dot-name suffix).

    The old glob 'AGENTS.*.md' required a dot-separated name component, so a
    plain 'AGENTS.md' was invisible in 'abc list' output.
    """
    distributor = WarehouseDistributor(
        warehouse_root=warehouse_with_plain_agents_md,
        target_root=temp_dir / "project",
    )

    result = distributor.list_available()

    assert len(result["contexts"]) == 1, f"Expected 1 context, got {result['contexts']}"
    assert "contexts/AGENTS.md" in result["contexts"]


def test_list_contexts_finds_named_agents_md(warehouse_with_named_agents_md, temp_dir):
    """list_available still finds old-style AGENTS.<name>.md files."""
    distributor = WarehouseDistributor(
        warehouse_root=warehouse_with_named_agents_md,
        target_root=temp_dir / "project",
    )

    result = distributor.list_available()

    assert "contexts/AGENTS.global.md" in result["contexts"]
    assert "contexts/AGENTS.python.md" in result["contexts"]


def test_list_contexts_returns_relative_paths(warehouse_with_plain_agents_md, temp_dir):
    """Context entries are relative paths from warehouse root (e.g. contexts/AGENTS.md)."""
    distributor = WarehouseDistributor(
        warehouse_root=warehouse_with_plain_agents_md,
        target_root=temp_dir / "project",
    )

    result = distributor.list_available()

    for ctx in result["contexts"]:
        assert ctx.startswith("contexts/"), (
            f"Context path '{ctx}' should start with 'contexts/'"
        )


def test_list_contexts_empty_when_no_contexts_dir(temp_dir):
    """list_available returns empty contexts list when contexts/ doesn't exist."""
    wh = temp_dir / "warehouse"
    wh.mkdir()
    # No contexts/ dir at all
    (wh / "knowledge").mkdir()
    (wh / "skills").mkdir()

    distributor = WarehouseDistributor(
        warehouse_root=wh,
        target_root=temp_dir / "project",
    )

    result = distributor.list_available()

    assert result["contexts"] == []


def test_list_contexts_ignores_dotfiles(temp_dir):
    """_list_contexts does not return hidden files."""
    wh = temp_dir / "warehouse"
    wh.mkdir()
    (wh / "contexts").mkdir()
    (wh / "knowledge").mkdir()
    (wh / "skills").mkdir()
    (wh / "contexts" / "AGENTS.md").write_text("# Real context")
    (wh / "contexts" / ".hidden.md").write_text("# Hidden")

    distributor = WarehouseDistributor(
        warehouse_root=wh,
        target_root=temp_dir / "project",
    )

    result = distributor.list_available()

    assert "contexts/.hidden.md" not in result["contexts"]
    assert "contexts/AGENTS.md" in result["contexts"]


# ========== Regression: Bug #4 — catalog Usage example stale format ==========


def test_catalog_context_example_uses_full_path(temp_dir):
    """Regression #4: warehouse catalog Usage example must use contexts/ prefix.

    The old hardcoded example showed '- AGENTS.global.md', which is both the
    wrong naming convention and missing the 'contexts/' path prefix.
    """
    wh = temp_dir / "warehouse"
    wh.mkdir()
    (wh / "contexts").mkdir()
    (wh / "knowledge").mkdir()
    (wh / "skills").mkdir()
    (wh / "contexts" / "AGENTS.md").write_text("# Context")

    catalog = _generate_warehouse_catalog(wh)

    assert "AGENTS.global.md" not in catalog, (
        "Catalog must not reference old 'AGENTS.global.md' naming convention"
    )
    assert "contexts/AGENTS.md" in catalog, (
        "Catalog Usage example should show 'contexts/AGENTS.md'"
    )


def test_catalog_knowledge_example_uses_knowledge_prefix(temp_dir):
    """Catalog Usage example shows knowledge/ prefix on paths."""
    wh = temp_dir / "warehouse"
    wh.mkdir()
    (wh / "contexts").mkdir()
    (wh / "knowledge").mkdir()
    (wh / "skills").mkdir()

    catalog = _generate_warehouse_catalog(wh)

    # The Usage block should have knowledge/ prefix on example paths
    assert "knowledge/" in catalog


def test_catalog_skills_example_uses_skills_prefix(temp_dir):
    """Catalog Usage example shows skills/ prefix on paths."""
    wh = temp_dir / "warehouse"
    wh.mkdir()
    (wh / "contexts").mkdir()
    (wh / "knowledge").mkdir()
    (wh / "skills").mkdir()

    catalog = _generate_warehouse_catalog(wh)

    assert "skills/" in catalog
