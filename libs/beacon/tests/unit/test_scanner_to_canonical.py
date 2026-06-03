from pathlib import Path

from beacon.core.scanner.scanner import (
    classify_link,
    resolve_canonical_link,
    to_canonical,
)


def test_to_canonical_rewrites_cross_artifact_relative_skill_link(
    tmp_path: Path,
) -> None:
    source = tmp_path / "skills" / "foo" / "SKILL.md"

    assert (
        to_canonical("../../contexts/bar.md", source, tmp_path)
        == ".agentic-beacon/artifacts/contexts/bar.md"
    )


def test_to_canonical_preserves_anchor(tmp_path: Path) -> None:
    source = tmp_path / "skills" / "foo" / "SKILL.md"

    assert (
        to_canonical("../../contexts/bar.md#multi-repo", source, tmp_path)
        == ".agentic-beacon/artifacts/contexts/bar.md#multi-repo"
    )


def test_to_canonical_rewrites_legacy_partials_to_top_level_agent_partials(
    tmp_path: Path,
) -> None:
    """Legacy ``agents/_partials/`` references rewrite to ``agent-partials/``.

    The Phase 4 layout moves partials out of ``agents/_partials/`` to a
    top-level ``agent-partials/`` directory and the distribution glob only
    mirrors the new location. ``to_canonical()`` therefore canonicalises
    a legacy relative reference straight to the new location so a
    rewritten link resolves in synced projects after the warehouse
    migration. Tests both the agent-relative form (``_partials/...``)
    and a same-tree absolute form (resolving to ``agents/_partials/...``).
    """
    warehouse_root = tmp_path
    source = warehouse_root / "agents" / "sup.md"
    rewritten = to_canonical(
        "_partials/deep-review-checklist.md", source, warehouse_root
    )

    assert (
        rewritten == ".agentic-beacon/artifacts/agent-partials/deep-review-checklist.md"
    )
    assert classify_link(rewritten, source, warehouse_root) == "canonical"
    # Build the agent-partials/ tree so resolve_canonical_link can verify
    # the rewritten target lives under the warehouse root.
    (warehouse_root / "agent-partials").mkdir()
    (warehouse_root / "agent-partials" / "deep-review-checklist.md").write_text("x\n")
    assert resolve_canonical_link(rewritten, warehouse_root) == (
        (warehouse_root / "agent-partials" / "deep-review-checklist.md").resolve(),
        None,
    )


def test_to_canonical_is_idempotent_for_canonical_input(tmp_path: Path) -> None:
    source = tmp_path / "skills" / "foo" / "SKILL.md"
    link = ".agentic-beacon/artifacts/contexts/bar.md#multi-repo"

    assert to_canonical(link, source, tmp_path) == link
