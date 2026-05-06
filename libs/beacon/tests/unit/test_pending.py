"""Unit tests for beacon.core.manifest.pending."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from beacon.core.exceptions import ValidationError
from beacon.core.manifest.pending import PendingEntry, PendingManifest

_UTC = timezone.utc

_SAMPLE_ENTRY = PendingEntry(
    path="knowledge/lessons/foo.md",
    type="knowledge",
    action="created",
    source="record-knowledge",
    created_at=datetime(2026, 5, 6, 14, 22, 0, tzinfo=_UTC),
)


# ---------------------------------------------------------------------------
# from_yaml: absent file
# ---------------------------------------------------------------------------


def test_from_yaml_absent_returns_empty(tmp_path: Path) -> None:
    result = PendingManifest.from_yaml(tmp_path / "pending.yaml")
    assert result.pending == []


def test_from_yaml_empty_file_returns_empty(tmp_path: Path) -> None:
    p = tmp_path / "pending.yaml"
    p.write_text("", encoding="utf-8")
    result = PendingManifest.from_yaml(p)
    assert result.pending == []


def test_from_yaml_null_pending_returns_empty(tmp_path: Path) -> None:
    p = tmp_path / "pending.yaml"
    p.write_text("pending: null\n", encoding="utf-8")
    result = PendingManifest.from_yaml(p)
    assert result.pending == []


def test_from_yaml_empty_list_returns_empty(tmp_path: Path) -> None:
    p = tmp_path / "pending.yaml"
    p.write_text("pending: []\n", encoding="utf-8")
    result = PendingManifest.from_yaml(p)
    assert result.pending == []


# ---------------------------------------------------------------------------
# from_yaml: valid data
# ---------------------------------------------------------------------------


def test_from_yaml_parses_valid_entry(tmp_path: Path) -> None:
    p = tmp_path / "pending.yaml"
    p.write_text(
        "pending:\n"
        "- path: knowledge/lessons/x.md\n"
        "  type: knowledge\n"
        "  action: created\n"
        "  source: record-knowledge\n"
        "  created_at: '2026-05-06T14:22:00Z'\n",
        encoding="utf-8",
    )
    result = PendingManifest.from_yaml(p)
    assert len(result.pending) == 1
    entry = result.pending[0]
    assert entry.path == "knowledge/lessons/x.md"
    assert entry.type == "knowledge"
    assert entry.action == "created"
    assert entry.source == "record-knowledge"
    assert entry.created_at == datetime(2026, 5, 6, 14, 22, 0, tzinfo=_UTC)


def test_from_yaml_accepts_free_form_source(tmp_path: Path) -> None:
    p = tmp_path / "pending.yaml"
    p.write_text(
        "pending:\n"
        "- path: skills/foo/\n"
        "  type: skill\n"
        "  action: created\n"
        "  source: my-custom-authoring-skill\n"
        "  created_at: '2026-05-06T10:00:00Z'\n",
        encoding="utf-8",
    )
    result = PendingManifest.from_yaml(p)
    assert result.pending[0].source == "my-custom-authoring-skill"


# ---------------------------------------------------------------------------
# from_yaml: validation errors
# ---------------------------------------------------------------------------


def test_from_yaml_missing_field_raises(tmp_path: Path) -> None:
    p = tmp_path / "pending.yaml"
    p.write_text(
        "pending:\n"
        "- path: knowledge/lessons/x.md\n"
        "  action: created\n"
        "  source: record-knowledge\n"
        "  created_at: '2026-05-06T14:22:00Z'\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError) as exc_info:
        PendingManifest.from_yaml(p)
    assert "index 0" in str(exc_info.value)
    assert "type" in str(exc_info.value)


def test_from_yaml_invalid_type_enum_raises(tmp_path: Path) -> None:
    p = tmp_path / "pending.yaml"
    p.write_text(
        "pending:\n"
        "- path: knowledge/lessons/x.md\n"
        "  type: invalid-type\n"
        "  action: created\n"
        "  source: record-knowledge\n"
        "  created_at: '2026-05-06T14:22:00Z'\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError) as exc_info:
        PendingManifest.from_yaml(p)
    assert "index 0" in str(exc_info.value)


def test_from_yaml_invalid_action_enum_raises(tmp_path: Path) -> None:
    p = tmp_path / "pending.yaml"
    p.write_text(
        "pending:\n"
        "- path: knowledge/lessons/x.md\n"
        "  type: knowledge\n"
        "  action: deleted\n"
        "  source: record-knowledge\n"
        "  created_at: '2026-05-06T14:22:00Z'\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError) as exc_info:
        PendingManifest.from_yaml(p)
    assert "index 0" in str(exc_info.value)


def test_from_yaml_error_identifies_index(tmp_path: Path) -> None:
    p = tmp_path / "pending.yaml"
    # Second entry is bad
    p.write_text(
        "pending:\n"
        "- path: knowledge/lessons/x.md\n"
        "  type: knowledge\n"
        "  action: created\n"
        "  source: record-knowledge\n"
        "  created_at: '2026-05-06T14:22:00Z'\n"
        "- path: skills/foo/\n"
        "  type: invalid\n"
        "  action: created\n"
        "  source: record-skill\n"
        "  created_at: '2026-05-06T14:23:00Z'\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError) as exc_info:
        PendingManifest.from_yaml(p)
    assert "index 1" in str(exc_info.value)


# ---------------------------------------------------------------------------
# to_yaml: round-trip and field order
# ---------------------------------------------------------------------------


def test_to_yaml_round_trip(tmp_path: Path) -> None:
    manifest = PendingManifest(pending=[_SAMPLE_ENTRY])
    p = tmp_path / "pending.yaml"
    manifest.to_yaml(p)

    loaded = PendingManifest.from_yaml(p)
    assert len(loaded.pending) == 1
    e = loaded.pending[0]
    assert e.path == _SAMPLE_ENTRY.path
    assert e.type == _SAMPLE_ENTRY.type
    assert e.action == _SAMPLE_ENTRY.action
    assert e.source == _SAMPLE_ENTRY.source
    assert e.created_at == _SAMPLE_ENTRY.created_at


def test_to_yaml_field_order(tmp_path: Path) -> None:
    manifest = PendingManifest(pending=[_SAMPLE_ENTRY])
    p = tmp_path / "pending.yaml"
    manifest.to_yaml(p)

    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    entry_keys = list(raw["pending"][0].keys())
    assert entry_keys == ["path", "type", "action", "source", "created_at"]


def test_to_yaml_trailing_newline(tmp_path: Path) -> None:
    manifest = PendingManifest(pending=[_SAMPLE_ENTRY])
    p = tmp_path / "pending.yaml"
    manifest.to_yaml(p)
    assert p.read_text(encoding="utf-8").endswith("\n")


def test_to_yaml_creates_parent_dirs(tmp_path: Path) -> None:
    p = tmp_path / "nested" / "dir" / "pending.yaml"
    manifest = PendingManifest(pending=[])
    manifest.to_yaml(p)
    assert p.exists()


def test_to_yaml_empty_list(tmp_path: Path) -> None:
    manifest = PendingManifest(pending=[])
    p = tmp_path / "pending.yaml"
    manifest.to_yaml(p)
    loaded = PendingManifest.from_yaml(p)
    assert loaded.pending == []


# ---------------------------------------------------------------------------
# append
# ---------------------------------------------------------------------------


def test_append_in_memory(tmp_path: Path) -> None:
    manifest = PendingManifest(pending=[])
    manifest.append(_SAMPLE_ENTRY)
    assert len(manifest.pending) == 1
    assert manifest.pending[0] is _SAMPLE_ENTRY


def test_append_then_dump_preserves_order(tmp_path: Path) -> None:
    entry1 = PendingEntry(
        path="knowledge/a.md",
        type="knowledge",
        action="created",
        source="record-knowledge",
        created_at=datetime(2026, 5, 6, 10, 0, 0, tzinfo=_UTC),
    )
    entry2 = PendingEntry(
        path="skills/b/",
        type="skill",
        action="created",
        source="record-skill",
        created_at=datetime(2026, 5, 6, 11, 0, 0, tzinfo=_UTC),
    )
    manifest = PendingManifest(pending=[])
    manifest.append(entry1)
    manifest.append(entry2)

    p = tmp_path / "pending.yaml"
    manifest.to_yaml(p)

    loaded = PendingManifest.from_yaml(p)
    assert len(loaded.pending) == 2
    assert loaded.pending[0].path == "knowledge/a.md"
    assert loaded.pending[1].path == "skills/b/"

    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    for raw_entry in raw["pending"]:
        assert list(raw_entry.keys()) == ["path", "type", "action", "source", "created_at"]
