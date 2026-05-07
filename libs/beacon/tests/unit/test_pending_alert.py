"""Unit tests for beacon.domains.adoption.pending_alert (and cli re-export)."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from beacon.cli.pending_alert import maybe_emit_pending_alert
from beacon.core.manifest.pending import PendingEntry, PendingManifest

_UTC = UTC


def _make_project(tmp_path: Path) -> Path:
    """Create a minimal project directory with .agentic-beacon/config.toml."""
    beacon_dir = tmp_path / ".agentic-beacon"
    beacon_dir.mkdir()
    (beacon_dir / "config.toml").write_text(
        '[warehouse]\nlocal_path = "/tmp/fake-warehouse"\n', encoding="utf-8"
    )
    return tmp_path


def _write_pending(project: Path, entries: list[PendingEntry]) -> None:
    manifest = PendingManifest(pending=entries)
    manifest.to_yaml(project / ".agentic-beacon" / "pending.yaml")


def _sample_entry(n: int = 1) -> PendingEntry:
    return PendingEntry(
        path=f"contexts/entry{n}.md",
        type="context",
        action="modified",
        source="record-knowledge",
        created_at=datetime(2026, 5, 6, 14, 22, n, tzinfo=_UTC),
    )


# ---------------------------------------------------------------------------
# Alert fires with correct count
# ---------------------------------------------------------------------------


def test_alert_fires_with_one_entry(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    project = _make_project(tmp_path)
    _write_pending(project, [_sample_entry(1)])

    maybe_emit_pending_alert(project)

    err = capsys.readouterr().err
    assert "⚠ 1 pending artifacts. Run 'abc adopt' to wire them." in err


def test_alert_fires_with_correct_count_multiple(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    project = _make_project(tmp_path)
    _write_pending(project, [_sample_entry(1), _sample_entry(2), _sample_entry(3)])

    maybe_emit_pending_alert(project)

    err = capsys.readouterr().err
    assert "⚠ 3 pending artifacts. Run 'abc adopt' to wire them." in err


# ---------------------------------------------------------------------------
# Alert suppressed when pending.yaml absent or empty
# ---------------------------------------------------------------------------


def test_alert_suppressed_when_pending_yaml_absent(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    project = _make_project(tmp_path)

    maybe_emit_pending_alert(project)

    err = capsys.readouterr().err
    assert "pending" not in err.lower()


def test_alert_suppressed_when_pending_list_empty(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    project = _make_project(tmp_path)
    _write_pending(project, [])

    maybe_emit_pending_alert(project)

    err = capsys.readouterr().err
    assert "pending" not in err.lower()


# ---------------------------------------------------------------------------
# Alert suppressed when no config.toml in cwd-walk chain
# ---------------------------------------------------------------------------


def test_alert_suppressed_outside_project(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    # tmp_path has no .agentic-beacon/config.toml
    maybe_emit_pending_alert(tmp_path)

    err = capsys.readouterr().err
    assert err == ""


def test_alert_suppressed_in_subdirectory_outside_project(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    subdir = tmp_path / "some" / "nested" / "dir"
    subdir.mkdir(parents=True)

    maybe_emit_pending_alert(subdir)

    err = capsys.readouterr().err
    assert err == ""


def test_alert_detected_from_subdirectory_inside_project(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    project = _make_project(tmp_path)
    _write_pending(project, [_sample_entry(1)])

    subdir = project / "src" / "foo"
    subdir.mkdir(parents=True)

    maybe_emit_pending_alert(subdir)

    err = capsys.readouterr().err
    assert "⚠ 1 pending artifacts" in err


# ---------------------------------------------------------------------------
# Alert does not block subcommand execution
# ---------------------------------------------------------------------------


def test_alert_does_not_raise_on_corrupt_pending(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    project = _make_project(tmp_path)
    (project / ".agentic-beacon" / "pending.yaml").write_text(
        "not: valid: yaml: [\n", encoding="utf-8"
    )

    maybe_emit_pending_alert(project)  # must not raise


def test_alert_does_not_raise_on_permission_error(
    tmp_path: Path, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _make_project(tmp_path)
    _write_pending(project, [_sample_entry(1)])

    def _boom(path: Path) -> PendingManifest:
        raise PermissionError("no access")

    monkeypatch.setattr(PendingManifest, "from_yaml", staticmethod(_boom))

    maybe_emit_pending_alert(project)  # must not raise
