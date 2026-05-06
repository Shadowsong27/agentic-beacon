"""Helpers for reading and writing the .last-adopt timestamp marker.

The marker lives at .agentic-beacon/.last-adopt and records the UTC timestamp
of the most recent successful `abc adopt` session commit. It is gitignored.
"""

from datetime import datetime, timezone
from pathlib import Path

from beacon.core.exceptions import ValidationError

_LAST_ADOPT_FILENAME = ".last-adopt"


def _marker_path(project_root: Path) -> Path:
    return project_root / ".agentic-beacon" / _LAST_ADOPT_FILENAME


def read_last_adopt(project_root: Path) -> datetime | None:
    """Return the timestamp from .last-adopt, or None if absent.

    Raises ValidationError if the file exists but cannot be parsed as
    an ISO-8601 UTC timestamp.
    """
    path = _marker_path(project_root)
    if not path.exists():
        return None

    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return None

    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as e:
        raise ValidationError(
            f".last-adopt contains an unrecognisable timestamp: {raw!r}"
        ) from e

    return dt.astimezone(timezone.utc)


def write_last_adopt(project_root: Path, when: datetime) -> None:
    """Write *when* as an ISO-8601 UTC line to .last-adopt."""
    path = _marker_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)

    dt = when if when.tzinfo is None else when.astimezone(timezone.utc)
    timestamp_str = dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    path.write_text(timestamp_str + "\n", encoding="utf-8")
