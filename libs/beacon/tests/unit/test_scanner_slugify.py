from pathlib import Path

from beacon.core.scanner.scanner import extract_markdown_headings, slugify_heading


def test_slugify_heading_matches_cases() -> None:
    assert slugify_heading("Setup") == "setup"
    assert (
        slugify_heading("✨ ClickhouseS3Ingestor — DLT ingestion design")
        == "-clickhouses3ingestor--dlt-ingestion-design"
    )
    assert (
        slugify_heading("Multi-Repository Workspace - CRITICAL")
        == "multi-repository-workspace---critical"
    )
    assert slugify_heading("  Setup  ") == "setup"
    assert slugify_heading("Use `foo()`") == "use-foo"


def test_extract_markdown_headings_deduplicates_in_document_order(
    tmp_path: Path,
) -> None:
    path = tmp_path / "doc.md"
    path.write_text("## Setup\n\n## Setup\n", encoding="utf-8")

    assert extract_markdown_headings(path) == ["setup", "setup-1"]


def test_extract_markdown_headings_ignores_non_headings_and_fenced_blocks(
    tmp_path: Path,
) -> None:
    path = tmp_path / "doc.md"
    path.write_text(
        """plain text
```md
## Hidden heading
```
# Visible Heading
not a heading
~~~python
## Also hidden
~~~
## Final Heading
""",
        encoding="utf-8",
    )

    assert extract_markdown_headings(path) == ["visible-heading", "final-heading"]


def test_heading_dedup_counter_resets_per_file(tmp_path: Path) -> None:
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    first.write_text("## Setup\n## Setup\n", encoding="utf-8")
    second.write_text("## Setup\n", encoding="utf-8")

    assert extract_markdown_headings(first) == ["setup", "setup-1"]
    assert extract_markdown_headings(second) == ["setup"]
