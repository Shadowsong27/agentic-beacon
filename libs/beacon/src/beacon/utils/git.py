"""Git utility functions for Beacon CLI."""

import hashlib
import subprocess
from pathlib import Path


def find_project_root() -> Path:
    """
    Find project root (current directory or first parent with .git).

    Returns:
        Path to project root
    """
    current = Path.cwd()

    # Check for .git directory
    for path in [current, *current.parents]:
        if (path / ".git").exists():
            return path

    # Fallback to current directory
    return current


def get_warehouse_head_sha(warehouse_path: Path) -> str | None:
    """Return the current HEAD commit SHA of the warehouse git repo, or None."""
    if not (warehouse_path / ".git").exists():
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(warehouse_path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def get_file_hash_at_sha(
    warehouse_path: Path, relative_path: str, sha: str
) -> str | None:
    """Return SHA-256 of a file in the warehouse repo at a specific commit, or None.

    Uses ``git show <sha>:<relative_path>`` so no working-tree checkout is needed.
    Returns None if git is unavailable, the commit is missing, or the file did not
    exist at that commit.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(warehouse_path), "show", f"{sha}:{relative_path}"],
            capture_output=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return hashlib.sha256(result.stdout).hexdigest()


def hash_content(content: str) -> str:
    """Return SHA-256 hex digest of UTF-8 encoded content string."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
