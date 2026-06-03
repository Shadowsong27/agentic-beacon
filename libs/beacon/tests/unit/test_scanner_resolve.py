from pathlib import Path

from beacon.core.scanner.scanner import resolve_canonical_link


def test_resolve_canonical_link_resolves_existing_target(tmp_path: Path) -> None:
    warehouse_root = tmp_path
    target = warehouse_root / "contexts" / "cicd-flow.md"
    target.parent.mkdir()
    target.write_text("# CI/CD\n", encoding="utf-8")

    resolved = resolve_canonical_link(
        ".agentic-beacon/artifacts/contexts/cicd-flow.md", warehouse_root
    )

    assert resolved == (target, None)


def test_resolve_canonical_link_splits_anchor(tmp_path: Path) -> None:
    warehouse_root = tmp_path

    resolved = resolve_canonical_link(
        ".agentic-beacon/artifacts/contexts/cicd-flow.md#section", warehouse_root
    )

    assert resolved == (warehouse_root / "contexts" / "cicd-flow.md", "section")


def test_resolve_canonical_link_returns_missing_path_for_missing_target(
    tmp_path: Path,
) -> None:
    warehouse_root = tmp_path

    resolved = resolve_canonical_link(
        ".agentic-beacon/artifacts/contexts/missing.md", warehouse_root
    )

    assert resolved == (warehouse_root / "contexts" / "missing.md", None)
    assert not resolved[0].exists()


def test_resolve_canonical_link_rejects_non_canonical_input(tmp_path: Path) -> None:
    assert resolve_canonical_link("contexts/cicd-flow.md", tmp_path) is None


def test_resolve_canonical_link_decodes_url_encoded_anchor(tmp_path: Path) -> None:
    warehouse_root = tmp_path

    resolved = resolve_canonical_link(
        ".agentic-beacon/artifacts/contexts/cicd-flow.md#%EF%B8%8F-clickhouses3ingestor--dlt-ingestion-design",
        warehouse_root,
    )

    assert resolved == (
        warehouse_root / "contexts" / "cicd-flow.md",
        "\ufe0f-clickhouses3ingestor--dlt-ingestion-design",
    )


def test_resolve_canonical_link_rejects_path_traversal_escape(tmp_path: Path) -> None:
    """Canonical-shaped input that escapes the warehouse via .. is rejected.

    PR #159 round-3 review (HIGH severity). Without the relative_to() guard
    a payload like .agentic-beacon/artifacts/../../outside.md would be
    accepted as canonical and joined to a path outside the warehouse,
    silently widening the lint's allowed scope.
    """
    warehouse_root = tmp_path / "warehouse"
    warehouse_root.mkdir()

    assert (
        resolve_canonical_link(
            ".agentic-beacon/artifacts/../../outside.md", warehouse_root
        )
        is None
    )
    assert (
        resolve_canonical_link(
            ".agentic-beacon/artifacts/contexts/../../escape.md", warehouse_root
        )
        is None
    )
