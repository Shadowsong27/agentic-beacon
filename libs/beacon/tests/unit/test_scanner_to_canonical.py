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


def test_to_canonical_round_trips_agent_partial_link(tmp_path: Path) -> None:
    warehouse_root = tmp_path
    source = warehouse_root / "agents" / "sup.md"
    rewritten = to_canonical(
        "_partials/deep-review-checklist.md", source, warehouse_root
    )

    assert (
        rewritten
        == ".agentic-beacon/artifacts/agents/_partials/deep-review-checklist.md"
    )
    assert classify_link(rewritten, source, warehouse_root) == "canonical"
    assert resolve_canonical_link(rewritten, warehouse_root) == (
        warehouse_root / "agents" / "_partials" / "deep-review-checklist.md",
        None,
    )


def test_to_canonical_is_idempotent_for_canonical_input(tmp_path: Path) -> None:
    source = tmp_path / "skills" / "foo" / "SKILL.md"
    link = ".agentic-beacon/artifacts/contexts/bar.md#multi-repo"

    assert to_canonical(link, source, tmp_path) == link
