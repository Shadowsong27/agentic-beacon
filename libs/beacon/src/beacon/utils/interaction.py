"""Pure interaction logic — no Click, no Rich, no sys.exit.

Callers (CLI handlers) own the interactive UX.
"""

from __future__ import annotations

from enum import StrEnum


class ConflictResolution(StrEnum):
    """Result of resolving a file-overwrite conflict."""

    PROCEED = "proceed"
    SKIP = "skip"
    NEEDS_CONFIRMATION = "needs_confirmation"


def resolve_conflict(
    *,
    force: bool = False,
    preserve: bool = False,
    has_conflicts: bool = False,
) -> ConflictResolution:
    """Determine what to do when local files conflict with warehouse copies.

    Args:
        force: Overwrite all conflicts without prompting.
        preserve: Skip all conflicts without prompting.
        has_conflicts: Whether any conflicting files exist.

    Returns:
        ConflictResolution.PROCEED if safe to overwrite.
        ConflictResolution.SKIP if caller should skip conflicts.
        ConflictResolution.NEEDS_CONFIRMATION if user input is required.
    """
    if not has_conflicts:
        return ConflictResolution.PROCEED
    if preserve:
        return ConflictResolution.SKIP
    if force:
        return ConflictResolution.PROCEED
    return ConflictResolution.NEEDS_CONFIRMATION
