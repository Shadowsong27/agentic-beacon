"""Stateless path helpers with no domain knowledge."""

import os
from pathlib import Path


def normalize_relative_path(path: str) -> str:
    """Normalize a user-supplied relative path for membership checking.

    * Converts to POSIX-style forward slashes.
    * Removes leading './' segments.
    * Collapses redundant separators (e.g. 'skills//foo' -> 'skills/foo').
    * Rejects absolute paths and parent-directory traversal.

    Raises:
        ValueError: if the path is absolute or contains a '..' component.
    """
    p = Path(path)
    if p.is_absolute():
        raise ValueError(f"Absolute paths are not allowed: {path!r}")
    parts = p.parts
    if ".." in parts:
        raise ValueError(f"Parent-directory traversal is not allowed: {path!r}")
    # normpath removes './' and collapses redundant separators
    normalized = os.path.normpath(path)
    # Ensure POSIX-style forward slashes for cross-platform consistency
    normalized = normalized.replace(os.sep, "/")
    return normalized
