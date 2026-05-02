"""Shared file filters for skill/knowledge distribution and contribution.

Filters out OS-generated litter files (macOS .DS_Store, Windows Thumbs.db)
that should never be distributed or contributed alongside skill artifacts.
"""

from pathlib import Path

SKILL_IGNORE_NAMES: frozenset[str] = frozenset({".DS_Store", "Thumbs.db"})

SKILL_IGNORE_PATTERNS: tuple[str, ...] = (".DS_Store", "Thumbs.db")


def is_skill_file(path: Path) -> bool:
    """Return True if path is a file that should be included in skill operations."""
    return path.is_file() and path.name not in SKILL_IGNORE_NAMES
