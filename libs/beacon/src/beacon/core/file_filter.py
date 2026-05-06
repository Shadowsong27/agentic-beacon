"""Shared file filters for artifact distribution and contribution.

Filters out OS-generated litter files (macOS .DS_Store, Windows Thumbs.db)
and Python build artifacts (__pycache__, *.pyc) that should never be
distributed or contributed alongside beacon artifacts.
"""

from pathlib import Path

ARTIFACT_IGNORE_NAMES: frozenset[str] = frozenset({".DS_Store", "Thumbs.db"})

ARTIFACT_IGNORE_DIR_NAMES: frozenset[str] = frozenset({"__pycache__"})

ARTIFACT_IGNORE_SUFFIXES: frozenset[str] = frozenset({".pyc", ".pyo"})

ARTIFACT_IGNORE_PATTERNS: tuple[str, ...] = (
    ".DS_Store",
    "Thumbs.db",
    "__pycache__",
    "*.pyc",
    "*.pyo",
)


def is_artifact_file(path: Path) -> bool:
    """Return True if path is a file that should be included in artifact operations.

    Excludes OS litter (.DS_Store, Thumbs.db), Python bytecode (*.pyc, *.pyo),
    and any file inside a __pycache__ directory. These are generated artifacts
    that must never be synced, contributed, or wired into agent artifact dirs.
    """
    if not path.is_file():
        return False
    if path.name in ARTIFACT_IGNORE_NAMES:
        return False
    if path.suffix in ARTIFACT_IGNORE_SUFFIXES:
        return False
    if any(part in ARTIFACT_IGNORE_DIR_NAMES for part in path.parts):
        return False
    return True
