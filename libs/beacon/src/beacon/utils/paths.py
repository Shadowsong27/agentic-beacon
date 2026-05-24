"""Stateless path helpers with no domain knowledge."""

import os
from pathlib import Path


def normalize_relative_path(path: str) -> str:
    """Normalize a user-supplied relative path for membership checking.

    * Converts to POSIX-style forward slashes.
    * Removes leading './' segments.
    * Collapses redundant separators (e.g. 'skills//foo' -> 'skills/foo').
    * Rejects absolute paths and parent-directory traversal.
    * Rejects empty strings and bare ``.`` / ``./`` so a caller cannot pass
      an empty path that normalizes to ``.`` and is later interpreted as
      "the entire warehouse" by git (PR#156 round 8).

    Raises:
        ValueError: if the path is absolute, contains a '..' component, or
            normalizes to an empty / current-directory reference.
    """
    if not path or not path.strip():
        raise ValueError(f"Empty path is not allowed: {path!r}")
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
    if normalized in ("", "."):
        raise ValueError(
            f"Path normalizes to the warehouse root ({normalized!r}); "
            f"pass a specific file path or omit --paths to commit everything: {path!r}"
        )
    return normalized
