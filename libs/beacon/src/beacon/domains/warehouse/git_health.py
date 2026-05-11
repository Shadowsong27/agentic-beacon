"""Git health checks for warehouse repositories.

Pure functions — no Click, no Rich, no sys.exit.
Return structured data; callers format output.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from loguru import logger


@dataclass(frozen=True)
class GitHealthResult:
    """Result of a git health check."""

    ok: bool
    """True if the check passed (or was skipped)."""

    error_message: str | None = None
    """Human-readable error if ok is False."""

    warning_message: str | None = None
    """Non-fatal warning (e.g. git not available)."""

    hint: str | None = None
    """CLI-specific hint for resolving the issue (e.g. flag to bypass)."""


def check_warehouse_git_clean(warehouse_path: Path) -> GitHealthResult:
    """Check if the warehouse git working tree is clean and up to date with remote.

    Returns GitHealthResult(ok=True) if clean, behind remote, not a git repo,
    or git not installed. Returns GitHealthResult(ok=False) only when there
    are uncommitted changes.
    """
    if not (warehouse_path / ".git").exists():
        return GitHealthResult(ok=True)

    short_path = str(warehouse_path).replace(str(Path.home()), "~")

    def _git(args: list[str], timeout: int = 10) -> subprocess.CompletedProcess | None:
        try:
            return subprocess.run(
                ["git", "-C", str(warehouse_path), *args],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

    result = _git(["status", "--porcelain"])
    if result is None:
        logger.warning("git not available — skipping warehouse clean check")
        return GitHealthResult(ok=True, warning_message="git not available")

    if result.stdout.strip():
        return GitHealthResult(
            ok=False,
            error_message=(
                f"Warehouse has uncommitted changes.\n"
                f"  Warehouse: {short_path}\n\n"
                f"  Commit or stash your warehouse changes before running this command:\n"
                f"    cd {short_path}\n"
                f"    git diff          # review changes\n"
                f'    git add . && git commit -m "..."\n'
                f"    # or: git stash"
            ),
            hint="Use --skip-git-check to bypass this check.",
        )

    fetch_result = _git(["fetch", "--quiet"], timeout=15)
    if fetch_result is None:
        logger.warning("git fetch timed out — skipping remote check")
        return GitHealthResult(ok=True, warning_message="git fetch timed out")

    behind_result = _git(["rev-list", "--count", "HEAD..@{u}"])
    if behind_result is None or behind_result.returncode != 0:
        return GitHealthResult(ok=True)

    behind_count_str = behind_result.stdout.strip()
    try:
        behind_count = int(behind_count_str)
    except ValueError:
        return GitHealthResult(ok=True)

    if behind_count > 0:
        return GitHealthResult(
            ok=False,
            error_message=(
                f"Warehouse is behind its remote by {behind_count} commit(s).\n"
                f"  Warehouse: {short_path}\n\n"
                f"  Pull the latest changes before syncing:\n"
                f"    cd {short_path}\n"
                f"    git pull"
            ),
            hint="Use --skip-git-check to bypass this check.",
        )

    return GitHealthResult(ok=True)


def check_warehouse_on_main_branch(
    warehouse_path: Path,
    main_branch: str | None = None,
) -> GitHealthResult:
    """Check that the warehouse git repo is on the expected main branch.

    When ``main_branch`` is provided, it is the sole allowed branch.
    When ``main_branch`` is None, both 'main' and 'master' are accepted.

    Returns GitHealthResult(ok=True) if on an accepted branch, not a git repo,
    or git not installed. Returns GitHealthResult(ok=False) otherwise.
    """
    if not (warehouse_path / ".git").exists():
        return GitHealthResult(ok=True)

    short_path = str(warehouse_path).replace(str(Path.home()), "~")

    if main_branch:
        allowed_branches = {main_branch}
        expected_label = f"'{main_branch}' (configured in config.toml)"
        recovery_branch = main_branch
    else:
        allowed_branches = {"main", "master"}
        expected_label = "'main'"
        recovery_branch = "main"

    try:
        result = subprocess.run(
            ["git", "-C", str(warehouse_path), "symbolic-ref", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        return GitHealthResult(ok=True)
    except subprocess.TimeoutExpired:
        logger.warning("git timed out — skipping branch check")
        return GitHealthResult(ok=True, warning_message="git timed out")

    if result.returncode != 0:
        return GitHealthResult(
            ok=False,
            error_message=(
                f"Warehouse is in a detached HEAD state (not on any branch).\n"
                f"  Warehouse: {short_path}\n\n"
                f"  Switch to the main branch before syncing:\n"
                f"    cd {short_path}\n"
                f"    git checkout {recovery_branch}"
            ),
            hint="Use --skip-git-check to bypass this check.",
        )

    current_branch = result.stdout.strip()
    if current_branch not in allowed_branches:
        return GitHealthResult(
            ok=False,
            error_message=(
                f"Warehouse is on branch '{current_branch}', not {expected_label}.\n"
                f"  Warehouse: {short_path}\n\n"
                f"  This usually means you have a contribution in progress.\n"
                f"  Before switching branches, make sure your work is published:\n"
                f"    - Open a PR or push your branch so the work isn't lost\n"
                f"    - Or run 'abc warehouse contribute -m \"…\" --push' to commit and push\n\n"
                f"  Then switch to the main branch:\n"
                f"    cd {short_path}\n"
                f"    git checkout {recovery_branch}"
            ),
            hint="Use --skip-git-check to bypass this check.",
        )

    return GitHealthResult(ok=True)
