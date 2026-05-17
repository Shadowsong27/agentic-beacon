# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Atomic push wrapper for the contribute-warehouse skill.

On success: exits 0 with a quiet success message on stdout.
On failure: prints a structured error to stderr, prints the exact recovery
            command to stdout, and exits non-zero.

Recovery command format:
    git -C <warehouse> push origin <branch>

Safety guarantees:
  - The only git operations performed are:
      1. git rev-parse --abbrev-ref HEAD   (to capture branch name)
      2. git push                           (no extra flags)
  - No destructive git operations are ever invoked.

Usage:
    uv run push_warehouse.py --warehouse <path>
"""

import argparse
import shlex
import subprocess
import sys
from pathlib import Path


def get_current_branch(warehouse: Path) -> str:
    """Return the current branch name in the warehouse.

    Returns 'HEAD' if in detached-HEAD state.
    Exits non-zero on subprocess failure.
    """
    result = subprocess.run(
        ["git", "-C", str(warehouse), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        print(
            f"Error: could not determine current branch: {result.stderr.strip()}",
            file=sys.stderr,
        )
        sys.exit(1)
    return result.stdout.strip()


def push(warehouse: Path) -> None:
    """Push the warehouse to origin.

    On success: prints a success message and returns.
    On failure: prints structured error to stderr, prints recovery command
                to stdout, and raises SystemExit with non-zero code.
    """
    branch = get_current_branch(warehouse)

    result = subprocess.run(
        ["git", "-C", str(warehouse), "push"],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode == 0:
        print(f"Push succeeded (branch: {branch})")
        return

    # Push failed — structured error to stderr
    print(
        "Push failed.\n"
        "---\n"
        f"Branch: {branch}\n"
        f"git stderr:\n{result.stderr.strip()}\n"
        "---\n"
        "Your local commits are intact. Resolve the issue above and re-push.",
        file=sys.stderr,
    )

    # Recovery command to stdout (copy-pasteable)
    print(f"git -C {shlex.quote(str(warehouse))} push origin {shlex.quote(branch)}")
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Atomic push wrapper — push warehouse to origin with recovery output on failure."
    )
    parser.add_argument(
        "--warehouse",
        required=True,
        help="Absolute path to the warehouse root.",
    )
    args = parser.parse_args()

    warehouse = Path(args.warehouse)
    if not warehouse.is_dir():
        print(f"Error: warehouse path does not exist: {warehouse}", file=sys.stderr)
        sys.exit(1)

    push(warehouse)
    sys.exit(0)


if __name__ == "__main__":
    main()
