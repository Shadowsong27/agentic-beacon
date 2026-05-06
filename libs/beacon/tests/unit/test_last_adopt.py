"""Unit tests for beacon.domains.adoption.last_adopt."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from beacon.core.exceptions import ValidationError
from beacon.domains.adoption.last_adopt import read_last_adopt, write_last_adopt

_UTC = timezone.utc


# ---------------------------------------------------------------------------
# read_last_adopt
# ---------------------------------------------------------------------------


def test_read_absent_returns_none(tmp_path: Path) -> None:
    assert read_last_adopt(tmp_path) is None


def test_read_empty_file_returns_none(tmp_path: Path) -> None:
    (tmp_path / ".agentic-beacon").mkdir()
    (tmp_path / ".agentic-beacon" / ".last-adopt").write_text("", encoding="utf-8")
    assert read_last_adopt(tmp_path) is None


def test_read_malformed_raises(tmp_path: Path) -> None:
    (tmp_path / ".agentic-beacon").mkdir()
    (tmp_path / ".agentic-beacon" / ".last-adopt").write_text(
        "not-a-timestamp\n", encoding="utf-8"
    )
    with pytest.raises(ValidationError) as exc_info:
        read_last_adopt(tmp_path)
    assert "not-a-timestamp" in str(exc_info.value)


# ---------------------------------------------------------------------------
# write_last_adopt
# ---------------------------------------------------------------------------


def test_write_creates_parent_dirs(tmp_path: Path) -> None:
    when = datetime(2026, 5, 6, 15, 0, 0, tzinfo=_UTC)
    write_last_adopt(tmp_path, when)
    marker = tmp_path / ".agentic-beacon" / ".last-adopt"
    assert marker.exists()


def test_write_then_read_round_trips(tmp_path: Path) -> None:
    when = datetime(2026, 5, 6, 15, 0, 0, tzinfo=_UTC)
    write_last_adopt(tmp_path, when)
    result = read_last_adopt(tmp_path)
    assert result == when


def test_write_produces_z_suffix(tmp_path: Path) -> None:
    when = datetime(2026, 5, 6, 15, 0, 0, tzinfo=_UTC)
    write_last_adopt(tmp_path, when)
    content = (tmp_path / ".agentic-beacon" / ".last-adopt").read_text(encoding="utf-8")
    assert content.strip() == "2026-05-06T15:00:00Z"


def test_write_trailing_newline(tmp_path: Path) -> None:
    when = datetime(2026, 5, 6, 15, 0, 0, tzinfo=_UTC)
    write_last_adopt(tmp_path, when)
    content = (tmp_path / ".agentic-beacon" / ".last-adopt").read_text(encoding="utf-8")
    assert content.endswith("\n")


def test_write_overwrites_existing(tmp_path: Path) -> None:
    first = datetime(2026, 5, 6, 10, 0, 0, tzinfo=_UTC)
    second = datetime(2026, 5, 6, 15, 0, 0, tzinfo=_UTC)
    write_last_adopt(tmp_path, first)
    write_last_adopt(tmp_path, second)
    assert read_last_adopt(tmp_path) == second
