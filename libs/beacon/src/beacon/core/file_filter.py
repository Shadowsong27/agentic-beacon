"""Shared file filters for skill/knowledge distribution and contribution.

Filters out OS-generated litter files (macOS .DS_Store, Windows Thumbs.db)
and Python build artifacts (__pycache__, *.pyc) that should never be
distributed or contributed alongside skill artifacts.
"""

from pathlib import Path

SKILL_IGNORE_NAMES: frozenset[str] = frozenset({".DS_Store", "Thumbs.db"})

SKILL_IGNORE_DIR_NAMES: frozenset[str] = frozenset({"__pycache__"})

SKILL_IGNORE_SUFFIXES: frozenset[str] = frozenset({".pyc", ".pyo"})

SKILL_IGNORE_PATTERNS: tuple[str, ...] = (
    ".DS_Store",
    "Thumbs.db",
    "__pycache__",
    "*.pyc",
    "*.pyo",
)


def is_skill_file(path: Path) -> bool:
    """Return True if path is a file that should be included in skill operations.

    Excludes OS litter (.DS_Store, Thumbs.db), Python bytecode (*.pyc, *.pyo),
    and any file inside a __pycache__ directory. These are generated artifacts
    that must never be synced, contributed, or wired into agent skill dirs.
    """
    if not path.is_file():
        return False
    if path.name in SKILL_IGNORE_NAMES:
        return False
    if path.suffix in SKILL_IGNORE_SUFFIXES:
        return False
    if any(part in SKILL_IGNORE_DIR_NAMES for part in path.parts):
        return False
    return True
