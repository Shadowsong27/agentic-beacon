"""Tests for WarehouseDistributor.

Regression tests for:
- Bug #3: _list_contexts() only matched AGENTS.*.md (old convention),
  missing plain AGENTS.md files created by 'abc warehouse init'.
- Bug #4: warehouse catalog Usage example showed old AGENTS.global.md format.
"""

import pytest
from beacon.domains.distribution.distributor import (
    WarehouseDistributor,
    is_partial_path,
)
from beacon.domains.warehouse.catalog import generate_warehouse_catalog


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

    catalog = generate_warehouse_catalog(wh)

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

    catalog = generate_warehouse_catalog(wh)

    # The Usage block should have knowledge/ prefix on example paths
    assert "knowledge/" in catalog


def test_catalog_skills_example_uses_skills_prefix(temp_dir):
    """Catalog Usage example shows skills/ prefix on paths."""
    wh = temp_dir / "warehouse"
    wh.mkdir()
    (wh / "contexts").mkdir()
    (wh / "knowledge").mkdir()
    (wh / "skills").mkdir()

    catalog = generate_warehouse_catalog(wh)

    assert "skills/" in catalog


# ========== Agent partial filtering ==========


@pytest.fixture
def warehouse_with_partials(temp_dir):
    """Warehouse with agents, partials, and underscore-prefixed dirs."""
    wh = temp_dir / "warehouse"
    wh.mkdir()
    (wh / "agents").mkdir()
    (wh / "agent-partials").mkdir()
    (wh / "contexts").mkdir()
    (wh / "knowledge").mkdir()
    (wh / "skills").mkdir()
    (wh / "agents" / "foo.md").write_text("# Agent Foo")
    (wh / "agents" / "_partials").mkdir()
    (wh / "agents" / "_partials" / "p.md").write_text("# Partial")
    (wh / "agent-partials" / "root.md").write_text("# Root Partial")
    (wh / "agents" / "_internal").mkdir()
    (wh / "agents" / "_internal" / "q.md").write_text("# Internal")
    (wh / "agents" / "some-dir").mkdir()
    (wh / "agents" / "some-dir" / "regular.md").write_text("# Regular")
    return wh


@pytest.mark.parametrize(
    ("rel_path", "expected"),
    [
        ("agent-partials/deep-review-checklist.md", True),
        ("agent-partials/sub/x.md", True),
        ("agents/_partials/x.md", True),
        ("_partials/x.md", True),
        ("agents/spec-planner.md", False),
        ("contexts/foo.md", False),
    ],
)
def test_is_partial_path_cases(rel_path, expected):
    """Recognize canonical and legacy partial locations, but not agents."""
    assert is_partial_path(rel_path) is expected


def test_list_agents_skips_partials_dir(warehouse_with_partials, temp_dir):
    """_list_agents skips legacy agents/_partials/*.md for safety."""
    distributor = WarehouseDistributor(
        warehouse_root=warehouse_with_partials,
        target_root=temp_dir / "project",
    )
    result = distributor._list_agents(warehouse_with_partials / "agents")
    assert "agents/_partials/p.md" not in result
    assert "agents/foo.md" in result
    assert is_partial_path("agent-partials/root.md") is True


def test_list_agents_only_skips_partials_not_other_underscore_dirs(
    warehouse_with_partials, temp_dir
):
    """Filter is scoped to partial paths specifically, not all underscore dirs."""
    distributor = WarehouseDistributor(
        warehouse_root=warehouse_with_partials,
        target_root=temp_dir / "project",
    )
    result = distributor._list_agents(warehouse_with_partials / "agents")
    # Anything under _partials/ is hidden …
    assert "agents/_partials/p.md" not in result
    # … but other leading-underscore dirs are NOT hidden, so they don't get
    # silently swallowed by discovery while never being co-distributed.
    assert "agents/_internal/q.md" in result


def test_list_agents_still_lists_plain_agents(warehouse_with_partials, temp_dir):
    """Plain agents and nested non-underscore dirs are still listed (PER-164)."""
    distributor = WarehouseDistributor(
        warehouse_root=warehouse_with_partials,
        target_root=temp_dir / "project",
    )
    result = distributor._list_agents(warehouse_with_partials / "agents")
    assert "agents/foo.md" in result
    assert "agents/some-dir/regular.md" in result
