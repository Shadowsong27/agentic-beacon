# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Draft a deterministic Conventional Commits message from a list of paths and a subject.

Outputs: <type>(<scope>): <subject>

Mapping table (documented inline):
  Type prefix rules:
    - All paths under skills/  AND at least one new file (status
      first or second column is A, ?, R, or C)                       → feat
    - All paths under skills/  AND only modifications (status M, D,
      or space in both columns)                                      → fix
    - All paths under contexts/ or knowledge/                        → docs
    - All paths under agents/  AND new file                          → feat
    - All paths under agents/  AND modification                      → fix
    - Mixed top-level dirs or unclassifiable                         → chore

  Scope derivation rules:
    1. Find the longest common path prefix across all paths.
    2. If all paths are under knowledge/<topic>/ (same topic) → scope = <topic>
    3. If all paths are under knowledge/ (mixed topics)       → scope = knowledge
    4. If all paths are under contexts/                       → scope = contexts
    5. If all paths are under skills/                         → scope = skills
    6. If all paths are under agents/                         → scope = agents
    7. Mixed top-level dirs or root-level files               → scope = general

Usage:
    uv run draft_commit_message.py --paths <p1> [<p2> ...] --subject <text>
"""

import argparse
import sys
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Scope derivation
# ─────────────────────────────────────────────────────────────────────────────


def derive_scope(paths: list[str]) -> str:
    """Derive the commit scope deterministically from a list of warehouse-relative paths.

    Rules (from design.md Decision 9):
      - knowledge/<same-topic>/... → <topic>
      - knowledge/ mixed topics    → knowledge
      - contexts/...               → contexts
      - skills/...                 → skills
      - agents/...                 → agents
      - mixed or root-level        → general

    Args:
        paths: List of warehouse-relative path strings.

    Returns:
        A non-empty scope string.

    Raises:
        ValueError: If paths is empty.
    """
    if not paths:
        raise ValueError("paths must not be empty")

    # Normalise to forward-slash strings
    norm = [p.replace("\\", "/") for p in paths]

    # Determine top-level directories
    top_dirs = set()
    for p in norm:
        parts = Path(p).parts
        top_dirs.add(parts[0] if parts else "")

    if len(top_dirs) > 1:
        # Mixed top-level — fallback to general
        return "general"

    top = top_dirs.pop()

    if top == "knowledge":
        # Check if all paths share the same <topic>
        topics = set()
        for p in norm:
            parts = Path(p).parts
            # knowledge/<topic>/... → parts[1] if available
            if len(parts) >= 2:
                topics.add(parts[1])
            else:
                topics.add("")

        if len(topics) == 1:
            topic = topics.pop()
            return topic if topic else "knowledge"
        else:
            return "knowledge"

    if top in ("contexts", "skills", "agents"):
        return top

    # Root-level file or unknown → use stem of first path as scope, or 'general'
    first_stem = Path(norm[0]).stem
    return first_stem if first_stem else "general"


# ─────────────────────────────────────────────────────────────────────────────
# Type derivation
# ─────────────────────────────────────────────────────────────────────────────


def derive_type(paths: list[str], git_statuses: list[str] | None = None) -> str:
    """Derive the commit type prefix deterministically.

    Type mapping table (see module docstring for full table):
      skills/ + new files       → feat
      skills/ + modifications   → fix
      contexts/ or knowledge/   → docs
      agents/ + new             → feat
      agents/ + mod             → fix
      mixed or unclassifiable   → chore

    Args:
        paths: List of warehouse-relative path strings.
    git_statuses: Optional list of two-character git porcelain status
        codes per path (index column + worktree column).  A file is
        treated as "new" when either column is A, ?, R, or C.

    Returns:
        One of: 'feat', 'fix', 'docs', 'chore', 'refactor', 'test'.
    """
    if not paths:
        raise ValueError("paths must not be empty")

    norm = [p.replace("\\", "/") for p in paths]

    top_dirs = set()
    for p in norm:
        parts = Path(p).parts
        top_dirs.add(parts[0] if parts else "")

    if len(top_dirs) > 1:
        return "chore"

    top = top_dirs.pop()

    if top in ("contexts", "knowledge"):
        return "docs"

    if top in ("skills", "agents"):
        # Check statuses to distinguish feat vs fix.
        # Porcelain is two chars: index column + worktree column.
        # Treat as "new" when either column is A, ?, R, or C.
        if git_statuses:
            has_new = any(
                any(ch in "A?RC" for ch in status[:2]) for status in git_statuses
            )
        else:
            # Without status information, assume new files (feat)
            has_new = True

        return "feat" if has_new else "fix"

    return "chore"


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


def build_message(
    paths: list[str], subject: str, git_statuses: list[str] | None = None
) -> str:
    """Build the Conventional Commits message string."""
    scope = derive_scope(paths)
    type_prefix = derive_type(paths, git_statuses)
    return f"{type_prefix}({scope}): {subject}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Draft a deterministic Conventional Commits message."
    )
    parser.add_argument(
        "--paths",
        nargs="+",
        required=True,
        help="Warehouse-relative paths included in this commit.",
    )
    parser.add_argument(
        "--subject",
        required=True,
        help="Free-text commit subject (supplied by the LLM or user).",
    )
    parser.add_argument(
        "--git-statuses",
        nargs="*",
        default=None,
        help="Git status codes (A/M/??) per path, in the same order as --paths.",
    )
    args = parser.parse_args()

    subject = args.subject.rstrip()
    try:
        message = build_message(args.paths, subject, args.git_statuses)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(message)
    sys.exit(0)


if __name__ == "__main__":
    main()
