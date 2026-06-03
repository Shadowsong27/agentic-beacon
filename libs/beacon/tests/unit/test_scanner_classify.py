from pathlib import Path

from beacon.core.scanner.scanner import classify_link


def test_classify_link_absolute_urls(tmp_path: Path) -> None:
    source = tmp_path / "contexts" / "foo.md"

    assert classify_link("https://x.com", source, tmp_path) == "absolute-url"
    assert classify_link("mailto:a@b.com", source, tmp_path) == "absolute-url"


def test_classify_link_canonical(tmp_path: Path) -> None:
    source = tmp_path / "contexts" / "foo.md"

    assert (
        classify_link(".agentic-beacon/artifacts/contexts/a.md", source, tmp_path)
        == "canonical"
    )


def test_classify_link_own_skill_folder(tmp_path: Path) -> None:
    source = tmp_path / "skills" / "foo" / "SKILL.md"
    (tmp_path / "skills" / "foo" / "references").mkdir(parents=True)
    (tmp_path / "skills" / "foo" / "references" / "api.md").write_text(
        "# API\n", encoding="utf-8"
    )

    assert classify_link("references/api.md", source, tmp_path) == "own-skill-folder"


def test_classify_link_cross_artifact_relative_from_skill(tmp_path: Path) -> None:
    source = tmp_path / "skills" / "foo" / "SKILL.md"

    assert (
        classify_link("../../contexts/bar.md", source, tmp_path)
        == "cross-artifact-relative"
    )


def test_classify_link_cross_artifact_relative_from_agent(tmp_path: Path) -> None:
    source = tmp_path / "agents" / "sup.md"

    assert (
        classify_link("_partials/x.md", source, tmp_path) == "cross-artifact-relative"
    )


def test_classify_link_warehouse_escape(tmp_path: Path) -> None:
    source = tmp_path / "skills" / "foo" / "SKILL.md"

    assert (
        classify_link("../../../apps/backtest/docs/schema.md", source, tmp_path)
        == "warehouse-escape"
    )


def test_classify_link_context_relative_is_not_own_folder(tmp_path: Path) -> None:
    source = tmp_path / "contexts" / "foo.md"
    (tmp_path / "contexts" / "references").mkdir(parents=True)
    (tmp_path / "contexts" / "references" / "api.md").write_text(
        "# API\n", encoding="utf-8"
    )

    assert (
        classify_link("references/api.md", source, tmp_path)
        == "cross-artifact-relative"
    )


def test_classify_link_canonical_with_traversal_escape_is_warehouse_escape(
    tmp_path: Path,
) -> None:
    """A canonical-shaped link that .. -escapes the warehouse classifies as
    warehouse-escape, not canonical. PR #159 round-3 review (HIGH severity).
    """
    source = tmp_path / "contexts" / "foo.md"
    source.parent.mkdir(parents=True, exist_ok=True)

    assert (
        classify_link(".agentic-beacon/artifacts/../../outside.md", source, tmp_path)
        == "warehouse-escape"
    )
