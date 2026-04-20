"""Git utility functions for Beacon CLI."""

import hashlib
import subprocess
from pathlib import Path

from rich.console import Console

console = Console()


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


def check_warehouse_git_clean(warehouse_path: Path) -> str | None:
    """Check if the warehouse git working tree is clean and up to date with remote.

    Returns an error message string if there are uncommitted changes or if the
    local branch is behind its remote tracking branch, or None if everything is
    clean / not a git repo / git not installed.
    """
    if not (warehouse_path / ".git").exists():
        return None  # Not a git repo — skip silently

    short_path = str(warehouse_path).replace(str(Path.home()), "~")

    def _git(args: list[str], timeout: int = 10) -> subprocess.CompletedProcess | None:
        try:
            return subprocess.run(
                ["git", "-C", str(warehouse_path), *args],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except FileNotFoundError:
            return None
        except subprocess.TimeoutExpired:
            return None

    # Check working tree cleanliness
    result = _git(["status", "--porcelain"])
    if result is None:
        console.print(
            "[yellow]Warning:[/yellow] git not available — skipping warehouse clean check."
        )
        return None

    if result.stdout.strip():
        return (
            f"Warehouse has uncommitted changes.\n"
            f"  Warehouse: {short_path}\n\n"
            f"  Commit or stash your warehouse changes before running this command:\n"
            f"    cd {short_path}\n"
            f"    git diff          # review changes\n"
            f'    git add . && git commit -m "..."\n'
            f"    # or: git stash\n\n"
            f"  Use --skip-git-check to bypass this check."
        )

    # Fetch remote silently to get up-to-date tracking info
    fetch_result = _git(["fetch", "--quiet"], timeout=15)
    if fetch_result is None:
        console.print(
            "[yellow]Warning:[/yellow] git fetch timed out or git not found — skipping remote check."
        )
        return None

    # Check if local branch is behind the remote tracking branch
    behind_result = _git(["rev-list", "--count", "HEAD..@{u}"])
    if behind_result is None or behind_result.returncode != 0:
        # No upstream configured or other error — skip silently
        return None

    behind_count_str = behind_result.stdout.strip()
    try:
        behind_count = int(behind_count_str)
    except ValueError:
        return None

    if behind_count > 0:
        return (
            f"Warehouse is behind its remote by {behind_count} commit(s).\n"
            f"  Warehouse: {short_path}\n\n"
            f"  Pull the latest changes before contributing to avoid creating a\n"
            f"  stale PR or overwriting newer warehouse content:\n"
            f"    cd {short_path}\n"
            f"    git pull\n\n"
            f"  Use --skip-git-check to bypass this check."
        )

    return None


def check_warehouse_on_main_branch(warehouse_path: Path) -> str | None:
    """Check that the warehouse git repo is on the main (or master) branch.

    Returns an error message string if the warehouse is on a non-main branch,
    or None if everything looks good / not a git repo / git not installed.
    """
    if not (warehouse_path / ".git").exists():
        return None  # Not a git repo — skip silently

    short_path = str(warehouse_path).replace(str(Path.home()), "~")

    try:
        result = subprocess.run(
            ["git", "-C", str(warehouse_path), "symbolic-ref", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        return None  # git not available — skip silently
    except subprocess.TimeoutExpired:
        console.print(
            "[yellow]Warning:[/yellow] git timed out — skipping branch check."
        )
        return None

    if result.returncode != 0:
        # Detached HEAD or other error — treat as non-main
        return (
            f"Warehouse is in a detached HEAD state (not on any branch).\n"
            f"  Warehouse: {short_path}\n\n"
            f"  Switch to the main branch before syncing:\n"
            f"    cd {short_path}\n"
            f"    git checkout main\n\n"
            f"  Use --skip-git-check to bypass this check."
        )

    current_branch = result.stdout.strip()
    main_branches = {"main", "master"}
    if current_branch not in main_branches:
        return (
            f"Warehouse is on branch '{current_branch}', not 'main'.\n"
            f"  Warehouse: {short_path}\n\n"
            f"  This usually means you have a contribution in progress.\n"
            f"  Before switching branches, make sure your work is published:\n"
            f"    - Open a PR or push your branch so the work isn't lost\n"
            f"    - Or run 'abc contribute' to package it up first\n\n"
            f"  Then switch to main:\n"
            f"    cd {short_path}\n"
            f"    git checkout main\n\n"
            f"  Use --skip-git-check to bypass this check."
        )

    return None


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
