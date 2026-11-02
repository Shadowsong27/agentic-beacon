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


def resolve_commit(repo: Path, ref: str) -> str | None:
    """Return the full 40-hex SHA a commit-ish resolves to, or None.

    Uses ``git rev-parse --verify --quiet <ref>^{commit}``. Returns None if git is
    unavailable, the ref does not name a commit, or the call times out.
    """
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "rev-parse",
                "--verify",
                "--quiet",
                f"{ref}^{{commit}}",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def list_tree_paths(repo: Path, sha: str, prefix: str) -> list[str] | None:
    """Return every file path under *prefix* at *sha*, or None on git failure.

    Uses ``git ls-tree -r -z --name-only`` and splits on NUL, so non-ASCII file
    names are returned unquoted. An empty list means git succeeded and found no entries.
    """
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "ls-tree",
                "-r",
                "-z",
                "--name-only",
                sha,
                "--",
                prefix,
            ],
            capture_output=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return [entry for entry in result.stdout.decode("utf-8").split("\0") if entry]


def read_blob(repo: Path, sha: str, relative_path: str) -> bytes | None:
    """Return the raw bytes of a file at a commit, or None if git fails.

    Uses ``git show <sha>:<relative_path>`` so no working-tree checkout is needed.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "show", f"{sha}:{relative_path}"],
            capture_output=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def hash_content(content: str) -> str:
    """Return SHA-256 hex digest of UTF-8 encoded content string."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
