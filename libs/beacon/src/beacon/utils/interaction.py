"""Pure interaction logic — no Click, no Rich, no sys.exit.

Callers (CLI handlers) own the interactive UX.
"""

from __future__ import annotations

from enum import StrEnum


class OverwriteDecision(StrEnum):
    """Result of resolving a file-overwrite conflict."""

    PROCEED = "proceed"
    SKIP = "skip"
    NEEDS_CONFIRMATION = "needs_confirmation"


def resolve_conflict(
    *,
    force: bool = False,
    preserve: bool = False,
    has_conflicts: bool = False,
) -> OverwriteDecision:
    """Determine what to do when local files conflict with warehouse copies.

    Args:
        force: Overwrite all conflicts without prompting.
        preserve: Skip all conflicts without prompting.
        has_conflicts: Whether any conflicting files exist.

    Returns:
        OverwriteDecision.PROCEED if safe to overwrite.
        OverwriteDecision.SKIP if caller should skip conflicts.
        OverwriteDecision.NEEDS_CONFIRMATION if user input is required.
    """
    if not has_conflicts:
        return OverwriteDecision.PROCEED
    if preserve:
        return OverwriteDecision.SKIP
    if force:
        return OverwriteDecision.PROCEED
    return OverwriteDecision.NEEDS_CONFIRMATION
