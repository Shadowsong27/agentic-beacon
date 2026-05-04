"""Markdown knowledge reference scanner for warehouse artifacts.

Extracts and classifies knowledge references from adopted contexts and skill
SKILL.md files by resolving relative markdown links and applying the four-part
classifier from the auto-pull-artifact-dependencies spec.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

from loguru import logger

from beacon.core.manifest.beacon import BeaconManifest


@dataclass(frozen=True)
class LinkRef:
    """A single extracted markdown link."""

    text: str
    target: str


def extract_markdown_links(file_content: str) -> list[LinkRef]:
    r"""Extract every ``[text](target)`` inline link from markdown text.

    Skips:
    - Links inside fenced code blocks (``` or ~~~)
    - Links inside inline code (`` `...` ``)
    - Reference-style links ``[text][ref]``
    - Escaped brackets ``\[text\](target)``
    - Image links ``![alt](target)``

    Args:
        file_content: Raw markdown string.

    Returns:
        Ordered list of LinkRef for each inline link found.
    """
    links: list[LinkRef] = []
    lines = file_content.splitlines(keepends=True)

    in_code_fence = False
    fence_char = None

    for line in lines:
        stripped = line.lstrip()

        # Toggle fenced code block state on ``` or ~~~ at line start
        if not in_code_fence and (
            stripped.startswith("```") or stripped.startswith("~~~")
        ):
            in_code_fence = True
            fence_char = stripped[:3]
            continue
        if in_code_fence and stripped.startswith(fence_char):
            in_code_fence = False
            fence_char = None
            continue

        if in_code_fence:
            continue

        # Extract inline links from this line, respecting inline code backticks
        line_links = _extract_inline_links_from_line(line)
        links.extend(line_links)

    return links


def _extract_inline_links_from_line(line: str) -> list[LinkRef]:
    """Extract inline links from a single line, skipping inline code blocks.

    Splits the line by backtick pairs and only scans outside code spans.
    """
    links: list[LinkRef] = []
    parts = line.split("`")

    # Even indices are outside inline code; odd indices are inside
    for i, part in enumerate(parts):
        if i % 2 == 1:
            continue  # skip inline code
        links.extend(_extract_inline_links_from_text(part))

    return links


# Regex for inline links: not preceded by ! or \, then [text](target)
# Target matching stops at first unescaped ); nested parens are not supported.
_INLINE_LINK_RE = re.compile(r"(?<!\\)(?<!!)\[([^\]]*)\]\(([^)]+)\)")


def _extract_inline_links_from_text(text: str) -> list[LinkRef]:
    """Extract inline [text](target) links from plain text (no code blocks)."""
    links: list[LinkRef] = []
    for match in _INLINE_LINK_RE.finditer(text):
        link_text = match.group(1)
        target = match.group(2)
        links.append(LinkRef(text=link_text, target=target))
    return links


def normalize_link_target(target: str) -> str:
    """Strip URL fragments and URL-decode a link target.

    Args:
        target: Raw link target string (e.g. ``foo%20bar.md#section``).

    Returns:
        Normalized target with fragment removed and percent-encoding decoded.
    """
    # Strip fragment (everything from first #)
    hash_idx = target.find("#")
    if hash_idx != -1:
        target = target[:hash_idx]

    # URL-decode
    target = unquote(target)

    return target


def is_absolute_url(target: str) -> bool:
    """Return True if target is an absolute URL (has a scheme)."""
    return "://" in target or target.startswith("mailto:") or target.startswith("ftp:")


@dataclass(frozen=True)
class ResolvedLink:
    """A link resolved to a warehouse-relative path."""

    warehouse_relative: str


def resolve_link(
    scanned_file: Path, link: str, warehouse_root: Path
) -> ResolvedLink | None:
    """Resolve a markdown link relative to the scanned file.

    Returns None for absolute URLs or links that resolve outside the warehouse.

    Args:
        scanned_file: Absolute path to the file containing the link.
        link: The raw link target (should already be normalized).
        warehouse_root: Absolute path to the warehouse root.

    Returns:
        ResolvedLink with warehouse-relative path, or None.
    """
    if is_absolute_url(link):
        return None

    # Resolve against the scanned file's directory
    scanned_dir = scanned_file.parent
    resolved = (scanned_dir / link).resolve()

    # Check if resolved path is within warehouse
    try:
        rel = resolved.relative_to(warehouse_root.resolve())
    except ValueError:
        return None

    return ResolvedLink(warehouse_relative=str(rel))


def classify_knowledge_ref(resolved: Path, warehouse_root: Path) -> bool:
    """Classify whether a resolved path is a knowledge reference.

    Returns True iff the warehouse-relative path starts with ``knowledge/``
    AND ends with ``.md``.

    Args:
        resolved: Resolved absolute path.
        warehouse_root: Warehouse root path.

    Returns:
        True if this is a knowledge reference.
    """
    wh_root = warehouse_root.resolve()
    resolved_abs = resolved.resolve()

    try:
        rel = resolved_abs.relative_to(wh_root)
    except ValueError:
        return False

    rel_str = str(rel)
    return rel_str.startswith("knowledge/") and rel_str.endswith(".md")


def scan_file_for_knowledge(path: Path, warehouse_root: Path) -> set[str]:
    """Scan a single file for knowledge references.

    Args:
        path: Path to the markdown file (context or SKILL.md).
        warehouse_root: Absolute path to the warehouse root.

    Returns:
        Set of warehouse-relative paths classified as knowledge references.
        Includes broken links (missing targets) in the returned set.
    """
    warehouse_root = warehouse_root.resolve()
    path = path.resolve()

    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return set()

    links = extract_markdown_links(content)
    knowledge_refs: set[str] = set()

    for link in links:
        normalized = normalize_link_target(link.target)
        if not normalized:
            continue

        resolved = resolve_link(path, normalized, warehouse_root)
        if resolved is None:
            continue

        resolved_path = warehouse_root / resolved.warehouse_relative
        if classify_knowledge_ref(resolved_path, warehouse_root):
            knowledge_refs.add(resolved.warehouse_relative)
            if not resolved_path.exists():
                logger.warning(
                    "Knowledge reference '{}' from '{}' resolves to missing file '{}'",
                    link.target,
                    path,
                    resolved_path,
                )

    return knowledge_refs


def scan_adopted_artifacts(beacon: BeaconManifest, warehouse_root: Path) -> set[str]:
    """Scan all adopted contexts and skills for knowledge references.

    Args:
        beacon: Loaded beacon manifest.
        warehouse_root: Absolute path to the warehouse root.

    Returns:
        Union of knowledge refs across every adopted context and skill SKILL.md.
    """
    warehouse_root = warehouse_root.resolve()
    all_refs: set[str] = set()

    for ctx_name in beacon.artifacts.contexts:
        ctx_path = warehouse_root / "contexts" / f"{ctx_name}.md"
        all_refs.update(scan_file_for_knowledge(ctx_path, warehouse_root))

    for skill_name in beacon.artifacts.skills:
        skill_path = warehouse_root / "skills" / skill_name / "SKILL.md"
        all_refs.update(scan_file_for_knowledge(skill_path, warehouse_root))

    return all_refs
