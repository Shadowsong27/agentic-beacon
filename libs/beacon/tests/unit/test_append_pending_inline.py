"""Unit tests for the inlined YAML logic in both append_pending.py copies.

Validates the self-contained read-merge-write behaviour introduced in PER-150.
Parametrised over both copies to enforce the byte-identity invariant.
"""

from __future__ import annotations

import hashlib
import importlib.util
import re
import sys
from pathlib import Path

import pytest
import yaml

_SKILLS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "src" / "beacon" / "data" / "skills"
)

_SKILL_NAMES = ["record-skill", "record-knowledge"]


def _load_module(skill_name: str):
    script_path = _SKILLS_DIR / skill_name / "scripts" / "append_pending.py"
    spec = importlib.util.spec_from_file_location(
        f"{skill_name.replace('-', '_')}_append_pending_inline",
        script_path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_project(tmp_path: Path) -> Path:
    beacon_dir = tmp_path / ".agentic-beacon"
    beacon_dir.mkdir(parents=True)
    (beacon_dir / "config.toml").write_text(f'[warehouse]\nlocal_path = "{tmp_path}"\n')
    return tmp_path


@pytest.fixture(params=_SKILL_NAMES)
def mod(request):
    return _load_module(request.param)


# ----
# 1. Creates file when pending.yaml doesn't exist
# ----


def test_appends_to_empty_dir_creates_file(mod, tmp_path):
    # Arrange
    root = _make_project(tmp_path)
    pending_path = root / ".agentic-beacon" / "pending.yaml"
    assert not pending_path.exists()

    # Act
    mod.append_pending_entry(root, "skills/test/", "skill", "created", "record-skill")

    # Assert
    assert pending_path.exists()
    data = yaml.safe_load(pending_path.read_text())
    assert isinstance(data, dict)
    assert isinstance(data["pending"], list)
    assert len(data["pending"]) == 1


# ----
# 2. Appends to existing entries preserving insertion order
# ----


def test_appends_to_existing_entries_preserves_order(mod, tmp_path):
    # Arrange
    root = _make_project(tmp_path)
    pending_path = root / ".agentic-beacon" / "pending.yaml"
    existing = {
        "pending": [
            {
                "path": "skills/first/",
                "type": "skill",
                "action": "created",
                "source": "s",
                "created_at": "2026-01-01T00:00:00Z",
            },
            {
                "path": "contexts/second.md",
                "type": "context",
                "action": "modified",
                "source": "s",
                "created_at": "2026-01-02T00:00:00Z",
            },
        ]
    }
    pending_path.write_text(
        yaml.dump(existing, default_flow_style=False, sort_keys=False)
    )

    # Act
    mod.append_pending_entry(root, "agents/third/", "agent", "created", "record-skill")

    # Assert
    data = yaml.safe_load(pending_path.read_text())
    paths = [e["path"] for e in data["pending"]]
    assert paths == ["skills/first/", "contexts/second.md", "agents/third/"]


# ----
# 3. pending: null treated as empty list
# ----


def test_appends_when_pending_is_null(mod, tmp_path):
    # Arrange
    root = _make_project(tmp_path)
    pending_path = root / ".agentic-beacon" / "pending.yaml"
    pending_path.write_text("pending: null\n")

    # Act
    mod.append_pending_entry(root, "skills/x/", "skill", "created", "s")

    # Assert
    data = yaml.safe_load(pending_path.read_text())
    assert len(data["pending"]) == 1
    assert data["pending"][0]["path"] == "skills/x/"


# ----
# 4. pending key missing from dict treated as empty list
# ----


def test_appends_when_pending_is_missing_key(mod, tmp_path):
    # Arrange
    root = _make_project(tmp_path)
    pending_path = root / ".agentic-beacon" / "pending.yaml"
    pending_path.write_text("{}\n")

    # Act
    mod.append_pending_entry(root, "contexts/x.md", "context", "created", "s")

    # Assert
    data = yaml.safe_load(pending_path.read_text())
    assert len(data["pending"]) == 1
    assert data["pending"][0]["path"] == "contexts/x.md"


# ----
# 5. Rejects YAML that is a list at root (not a dict)
# ----


def test_rejects_malformed_yaml_not_a_dict(mod, tmp_path, capsys):
    # Arrange
    root = _make_project(tmp_path)
    pending_path = root / ".agentic-beacon" / "pending.yaml"
    pending_path.write_text("- foo\n- bar\n")
    original_content = pending_path.read_text()

    # Act
    with pytest.raises(SystemExit) as exc:
        mod.append_pending_entry(root, "x", "skill", "created", "s")

    # Assert
    assert exc.value.code != 0
    assert "Error" in capsys.readouterr().err
    assert pending_path.read_text() == original_content


# ----
# 6. Rejects pending field that is a string (not a list)
# ----


def test_rejects_pending_not_a_list(mod, tmp_path, capsys):
    # Arrange
    root = _make_project(tmp_path)
    pending_path = root / ".agentic-beacon" / "pending.yaml"
    pending_path.write_text("pending: 'not-a-list'\n")
    original_content = pending_path.read_text()

    # Act
    with pytest.raises(SystemExit) as exc:
        mod.append_pending_entry(root, "x", "skill", "created", "s")

    # Assert
    assert exc.value.code != 0
    assert "Error" in capsys.readouterr().err
    assert pending_path.read_text() == original_content


# ----
# 7. created_at format is UTC ISO 8601 with Z suffix
# ----


def test_datetime_format_is_utc_iso_z(mod, tmp_path):
    # Arrange
    root = _make_project(tmp_path)

    # Act
    mod.append_pending_entry(root, "skills/x/", "skill", "created", "s")

    # Assert
    content = (root / ".agentic-beacon" / "pending.yaml").read_text()
    data = yaml.safe_load(content)
    created_at = data["pending"][0]["created_at"]
    # Pydantic/yaml may return datetime or string; normalise to string
    if not isinstance(created_at, str):
        created_at = created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", created_at)


# ----
# 8. Field order is canonical: path / type / action / source / created_at
# ----


def test_field_order_is_canonical(mod, tmp_path):
    # Arrange
    root = _make_project(tmp_path)

    # Act
    mod.append_pending_entry(root, "skills/test/", "skill", "created", "test-source")

    # Assert -- check key appearance order in raw YAML text
    lines = (root / ".agentic-beacon" / "pending.yaml").read_text().splitlines()
    key_order = ["path:", "type:", "action:", "source:", "created_at:"]

    def _find_line(key: str) -> int:
        for i, line in enumerate(lines):
            s = line.strip()
            if s.startswith(key) or s.startswith(f"- {key}"):
                return i
        return -1

    positions = [_find_line(k) for k in key_order]
    assert all(p >= 0 for p in positions), (
        f"Some keys not found in YAML output: {list(zip(key_order, positions, strict=False))}"
    )
    assert positions == sorted(positions), (
        f"Keys are out of canonical order: {list(zip(key_order, positions, strict=False))}"
    )


# ----
# 9. Written file ends with a trailing newline
# ----


def test_trailing_newline_present(mod, tmp_path):
    # Arrange
    root = _make_project(tmp_path)

    # Act
    mod.append_pending_entry(root, "skills/x/", "skill", "created", "s")

    # Assert
    raw = (root / ".agentic-beacon" / "pending.yaml").read_bytes()
    assert raw.endswith(b"\n")


# ----
# 10. Multibyte (Unicode) path roundtrips correctly
# ----


def test_unicode_path_roundtrip(mod, tmp_path):
    # Arrange
    root = _make_project(tmp_path)
    unicode_path = "skills/测试/"

    # Act
    mod.append_pending_entry(root, unicode_path, "skill", "created", "s")

    # Assert
    data = yaml.safe_load(
        (root / ".agentic-beacon" / "pending.yaml").read_text(encoding="utf-8")
    )
    assert data["pending"][0]["path"] == unicode_path


# ----
# 11. Output round-trips through canonical PendingManifest
# ----


def test_round_trips_through_canonical_pending_manifest(mod, tmp_path):
    # Arrange
    root = _make_project(tmp_path)

    # Act
    mod.append_pending_entry(
        root, "skills/myskill/", "skill", "created", "record-skill"
    )

    # Assert -- import the canonical Pydantic model and verify it parses the output
    from beacon.core.manifest.pending import PendingManifest

    manifest = PendingManifest.from_yaml(root / ".agentic-beacon" / "pending.yaml")
    assert len(manifest.pending) == 1
    entry = manifest.pending[0]
    assert entry.path == "skills/myskill/"
    assert entry.type == "skill"
    assert entry.action == "created"
    assert entry.source == "record-skill"


# ----
# 12. Invalid --type rejected by argparse (exits 2)
# ----


def test_invalid_type_rejected_by_argparse(mod, monkeypatch, tmp_path):
    # Arrange
    root = _make_project(tmp_path)
    pending_path = root / ".agentic-beacon" / "pending.yaml"
    monkeypatch.chdir(root)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "append_pending.py",
            "--path",
            "x",
            "--type",
            "bogus",
            "--action",
            "created",
            "--source",
            "s",
        ],
    )

    # Act
    with pytest.raises(SystemExit) as exc:
        mod.main()

    # Assert
    assert exc.value.code == 2
    assert not pending_path.exists()


# ----
# 13. Invalid --action rejected by argparse (exits 2)
# ----


def test_invalid_action_rejected_by_argparse(mod, monkeypatch, tmp_path):
    # Arrange
    root = _make_project(tmp_path)
    pending_path = root / ".agentic-beacon" / "pending.yaml"
    monkeypatch.chdir(root)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "append_pending.py",
            "--path",
            "x",
            "--type",
            "skill",
            "--action",
            "bogus",
            "--source",
            "s",
        ],
    )

    # Act
    with pytest.raises(SystemExit) as exc:
        mod.main()

    # Assert
    assert exc.value.code == 2
    assert not pending_path.exists()


# ----
# 14. No project root -> exits 1 with ERROR_NO_WAREHOUSE on stderr
# ----


def test_no_project_root_exits_with_error(mod, monkeypatch, tmp_path, capsys):
    # Arrange -- tmp_path has no .agentic-beacon/config.toml
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "append_pending.py",
            "--path",
            "x",
            "--type",
            "skill",
            "--action",
            "created",
            "--source",
            "s",
        ],
    )

    # Act
    with pytest.raises(SystemExit) as exc:
        mod.main()

    # Assert
    assert exc.value.code == 1
    assert "Error: no warehouse connected" in capsys.readouterr().err


# ----
# Extra coverage: yaml.YAMLError branch (line 53-55)
# ----


def test_yaml_syntax_error_exits_with_message(mod, tmp_path, capsys):
    # Arrange -- write a file with invalid YAML syntax (unclosed brace)
    root = _make_project(tmp_path)
    pending_path = root / ".agentic-beacon" / "pending.yaml"
    pending_path.write_bytes(b"pending: {unclosed\n")
    original_content = pending_path.read_bytes()

    # Act
    with pytest.raises(SystemExit) as exc:
        mod.append_pending_entry(root, "x", "skill", "created", "s")

    # Assert
    assert exc.value.code != 0
    assert "Error" in capsys.readouterr().err
    assert pending_path.read_bytes() == original_content


# ----
# Extra coverage: data is None (empty / null YAML file) -> line 58
# ----


def test_null_yaml_file_treated_as_empty(mod, tmp_path):
    # Arrange -- file contains only "null" (yaml.safe_load returns None)
    root = _make_project(tmp_path)
    pending_path = root / ".agentic-beacon" / "pending.yaml"
    pending_path.write_text("null\n")

    # Act
    mod.append_pending_entry(root, "skills/x/", "skill", "created", "s")

    # Assert -- treated as empty list, one entry written
    data = yaml.safe_load(pending_path.read_text())
    assert len(data["pending"]) == 1


# ----
# Extra coverage: main() success path (lines 31 and 132)
# ----


def test_main_success_path_writes_pending(mod, monkeypatch, tmp_path):
    # Arrange
    root = _make_project(tmp_path)
    pending_path = root / ".agentic-beacon" / "pending.yaml"
    monkeypatch.chdir(root)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "append_pending.py",
            "--path",
            "skills/my-skill/",
            "--type",
            "skill",
            "--action",
            "created",
            "--source",
            "record-skill",
        ],
    )

    # Act
    mod.main()

    # Assert
    assert pending_path.exists()
    data = yaml.safe_load(pending_path.read_text())
    assert data["pending"][0]["path"] == "skills/my-skill/"


# ----
# 15. Both script copies are byte-identical
# ----


def test_both_script_copies_byte_identical():
    # Arrange
    skill_path = _SKILLS_DIR / "record-skill" / "scripts" / "append_pending.py"
    knowledge_path = _SKILLS_DIR / "record-knowledge" / "scripts" / "append_pending.py"

    # Act
    def _sha256(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    # Assert
    assert _sha256(skill_path) == _sha256(knowledge_path), (
        "record-skill and record-knowledge append_pending.py copies have diverged"
    )


# ----
# New tests: timestamp canonicalization and entry validation (PER-150 review)
# ----


def test_existing_unquoted_timestamp_canonicalized(mod, tmp_path):
    # Arrange: seed with unquoted timestamp -- yaml.safe_load parses it as datetime
    root = _make_project(tmp_path)
    pending_path = root / ".agentic-beacon" / "pending.yaml"
    pending_path.write_text(
        "pending:\n"
        "- path: skills/preexisting/\n"
        "  type: skill\n"
        "  action: created\n"
        "  source: x\n"
        "  created_at: 2026-01-01T00:00:00Z\n"
    )

    # Act
    mod.append_pending_entry(root, "skills/new/", "skill", "created", "record-skill")

    # Assert: no entry may use the Python-repr drift format (space + +00:00)
    content = pending_path.read_text()
    assert "00:00:00+00:00" not in content, (
        f"Timestamp was rewritten to Python repr style:\n{content}"
    )
    for line in content.splitlines():
        if "created_at:" in line:
            assert re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", line), (
                f"created_at not in canonical Z form: {line!r}"
            )


def test_existing_entry_datetime_created_at_accepted_and_canonicalized(mod, tmp_path):
    # Arrange: seed with unquoted timestamp so yaml.safe_load returns datetime
    root = _make_project(tmp_path)
    pending_path = root / ".agentic-beacon" / "pending.yaml"
    pending_path.write_text(
        "pending:\n"
        "- path: skills/old/\n"
        "  type: skill\n"
        "  action: created\n"
        "  source: s\n"
        "  created_at: 2025-06-15T10:30:00Z\n"
    )

    # Act: should NOT raise SystemExit -- datetime value is valid, just canonicalized
    mod.append_pending_entry(root, "skills/new/", "skill", "created", "s")

    # Assert: both entries present; first entry's created_at is in canonical form
    data = yaml.safe_load(pending_path.read_text())
    assert len(data["pending"]) == 2
    first_created_at = data["pending"][0]["created_at"]
    if not isinstance(first_created_at, str):
        first_created_at = first_created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", first_created_at)


def test_existing_entry_missing_required_field_rejected(mod, tmp_path, capsys):
    # Arrange: entry missing 'source'
    root = _make_project(tmp_path)
    pending_path = root / ".agentic-beacon" / "pending.yaml"
    pending_path.write_text(
        yaml.dump(
            {
                "pending": [
                    {
                        "path": "skills/x/",
                        "type": "skill",
                        "action": "created",
                        # source intentionally omitted
                        "created_at": "2026-01-01T00:00:00Z",
                    }
                ]
            },
            default_flow_style=False,
        )
    )
    original_content = pending_path.read_bytes()

    # Act
    with pytest.raises(SystemExit) as exc:
        mod.append_pending_entry(root, "skills/new/", "skill", "created", "s")

    # Assert
    assert exc.value.code != 0
    assert "source" in capsys.readouterr().err
    assert pending_path.read_bytes() == original_content


def test_existing_entry_invalid_type_rejected(mod, tmp_path, capsys):
    # Arrange: entry with type='bogus'
    root = _make_project(tmp_path)
    pending_path = root / ".agentic-beacon" / "pending.yaml"
    pending_path.write_text(
        yaml.dump(
            {
                "pending": [
                    {
                        "path": "skills/x/",
                        "type": "bogus",
                        "action": "created",
                        "source": "s",
                        "created_at": "2026-01-01T00:00:00Z",
                    }
                ]
            },
            default_flow_style=False,
        )
    )
    original_content = pending_path.read_bytes()

    # Act
    with pytest.raises(SystemExit) as exc:
        mod.append_pending_entry(root, "skills/new/", "skill", "created", "s")

    # Assert
    assert exc.value.code != 0
    assert "type" in capsys.readouterr().err
    assert pending_path.read_bytes() == original_content


def test_existing_entry_invalid_action_rejected(mod, tmp_path, capsys):
    # Arrange: entry with action='deleted' (not in VALID_ACTIONS)
    root = _make_project(tmp_path)
    pending_path = root / ".agentic-beacon" / "pending.yaml"
    pending_path.write_text(
        yaml.dump(
            {
                "pending": [
                    {
                        "path": "skills/x/",
                        "type": "skill",
                        "action": "deleted",
                        "source": "s",
                        "created_at": "2026-01-01T00:00:00Z",
                    }
                ]
            },
            default_flow_style=False,
        )
    )
    original_content = pending_path.read_bytes()

    # Act
    with pytest.raises(SystemExit) as exc:
        mod.append_pending_entry(root, "skills/new/", "skill", "created", "s")

    # Assert
    assert exc.value.code != 0
    assert "action" in capsys.readouterr().err
    assert pending_path.read_bytes() == original_content


def test_existing_entry_non_string_path_rejected(mod, tmp_path, capsys):
    # Arrange: entry with path=42 (integer, not string)
    root = _make_project(tmp_path)
    pending_path = root / ".agentic-beacon" / "pending.yaml"
    pending_path.write_text(
        yaml.dump(
            {
                "pending": [
                    {
                        "path": 42,
                        "type": "skill",
                        "action": "created",
                        "source": "s",
                        "created_at": "2026-01-01T00:00:00Z",
                    }
                ]
            },
            default_flow_style=False,
        )
    )
    original_content = pending_path.read_bytes()

    # Act
    with pytest.raises(SystemExit) as exc:
        mod.append_pending_entry(root, "skills/new/", "skill", "created", "s")

    # Assert
    assert exc.value.code != 0
    assert "path" in capsys.readouterr().err
    assert pending_path.read_bytes() == original_content


def test_existing_entry_malformed_created_at_rejected(mod, tmp_path, capsys):
    # Arrange: entry with created_at='not-a-date'
    root = _make_project(tmp_path)
    pending_path = root / ".agentic-beacon" / "pending.yaml"
    pending_path.write_text(
        yaml.dump(
            {
                "pending": [
                    {
                        "path": "skills/x/",
                        "type": "skill",
                        "action": "created",
                        "source": "s",
                        "created_at": "not-a-date",
                    }
                ]
            },
            default_flow_style=False,
        )
    )
    original_content = pending_path.read_bytes()

    # Act
    with pytest.raises(SystemExit) as exc:
        mod.append_pending_entry(root, "skills/new/", "skill", "created", "s")

    # Assert
    assert exc.value.code != 0
    assert "created_at" in capsys.readouterr().err
    assert pending_path.read_bytes() == original_content


# ----
# New tests: impossible date/time values rejected (PER-150 review round 2)
# ----


def test_existing_entry_impossible_month_rejected(mod, tmp_path, capsys):
    # Arrange: month=99 passes shape regex but strptime raises ValueError
    root = _make_project(tmp_path)
    pending_path = root / ".agentic-beacon" / "pending.yaml"
    pending_path.write_text(
        yaml.dump(
            {
                "pending": [
                    {
                        "path": "skills/bad/",
                        "type": "skill",
                        "action": "created",
                        "source": "s",
                        "created_at": "2026-99-01T00:00:00Z",
                    }
                ]
            },
            default_flow_style=False,
        )
    )
    original_content = pending_path.read_bytes()

    # Act
    with pytest.raises(SystemExit) as exc:
        mod.append_pending_entry(root, "skills/new/", "skill", "created", "s")

    # Assert
    assert exc.value.code != 0
    assert "created_at" in capsys.readouterr().err
    assert pending_path.read_bytes() == original_content


def test_existing_entry_impossible_day_rejected(mod, tmp_path, capsys):
    # Arrange: Feb 30 doesn't exist
    root = _make_project(tmp_path)
    pending_path = root / ".agentic-beacon" / "pending.yaml"
    pending_path.write_text(
        yaml.dump(
            {
                "pending": [
                    {
                        "path": "skills/bad/",
                        "type": "skill",
                        "action": "created",
                        "source": "s",
                        "created_at": "2026-02-30T00:00:00Z",
                    }
                ]
            },
            default_flow_style=False,
        )
    )
    original_content = pending_path.read_bytes()

    # Act
    with pytest.raises(SystemExit) as exc:
        mod.append_pending_entry(root, "skills/new/", "skill", "created", "s")

    # Assert
    assert exc.value.code != 0
    assert "created_at" in capsys.readouterr().err
    assert pending_path.read_bytes() == original_content


def test_existing_entry_impossible_hour_rejected(mod, tmp_path, capsys):
    # Arrange: hour=25 is out of range
    root = _make_project(tmp_path)
    pending_path = root / ".agentic-beacon" / "pending.yaml"
    pending_path.write_text(
        yaml.dump(
            {
                "pending": [
                    {
                        "path": "skills/bad/",
                        "type": "skill",
                        "action": "created",
                        "source": "s",
                        "created_at": "2026-01-01T25:00:00Z",
                    }
                ]
            },
            default_flow_style=False,
        )
    )
    original_content = pending_path.read_bytes()

    # Act
    with pytest.raises(SystemExit) as exc:
        mod.append_pending_entry(root, "skills/new/", "skill", "created", "s")

    # Assert
    assert exc.value.code != 0
    assert "created_at" in capsys.readouterr().err
    assert pending_path.read_bytes() == original_content


# ----
# New tests: non-canonical zero-padding rejected (PER-150 review round 3)
# ----


def test_existing_entry_non_canonical_zero_padding_rejected(mod, tmp_path, capsys):
    # Arrange: all components unpadded — strptime accepts but round-trip differs
    root = _make_project(tmp_path)
    pending_path = root / ".agentic-beacon" / "pending.yaml"
    pending_path.write_text(
        "pending:\n"
        "- path: skills/x/\n"
        "  type: skill\n"
        "  action: created\n"
        "  source: x\n"
        "  created_at: '2026-1-1T0:0:0Z'\n"
    )
    original_content = pending_path.read_bytes()

    # Act
    with pytest.raises(SystemExit) as exc:
        mod.append_pending_entry(root, "skills/new/", "skill", "created", "s")

    # Assert
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "canonical" in err
    assert pending_path.read_bytes() == original_content


def test_existing_entry_unpadded_day_rejected(mod, tmp_path, capsys):
    # Arrange: day component unpadded ('1' instead of '01')
    root = _make_project(tmp_path)
    pending_path = root / ".agentic-beacon" / "pending.yaml"
    pending_path.write_text(
        "pending:\n"
        "- path: skills/x/\n"
        "  type: skill\n"
        "  action: created\n"
        "  source: x\n"
        "  created_at: '2026-01-1T07:00:00Z'\n"
    )
    original_content = pending_path.read_bytes()

    # Act
    with pytest.raises(SystemExit) as exc:
        mod.append_pending_entry(root, "skills/new/", "skill", "created", "s")

    # Assert
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "canonical" in err
    assert pending_path.read_bytes() == original_content


def test_existing_entry_unpadded_hour_rejected(mod, tmp_path, capsys):
    # Arrange: hour component unpadded ('7' instead of '07')
    root = _make_project(tmp_path)
    pending_path = root / ".agentic-beacon" / "pending.yaml"
    pending_path.write_text(
        "pending:\n"
        "- path: skills/x/\n"
        "  type: skill\n"
        "  action: created\n"
        "  source: x\n"
        "  created_at: '2026-01-01T7:00:00Z'\n"
    )
    original_content = pending_path.read_bytes()

    # Act
    with pytest.raises(SystemExit) as exc:
        mod.append_pending_entry(root, "skills/new/", "skill", "created", "s")

    # Assert
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "canonical" in err
    assert pending_path.read_bytes() == original_content


def test_existing_entry_valid_canonical_string_accepted(mod, tmp_path):
    # Arrange: well-formed, in-range timestamp as quoted string
    root = _make_project(tmp_path)
    pending_path = root / ".agentic-beacon" / "pending.yaml"
    original_entry = {
        "path": "skills/preexisting/",
        "type": "skill",
        "action": "created",
        "source": "s",
        "created_at": "2026-05-13T07:00:00Z",
    }
    pending_path.write_text(
        yaml.dump(
            {"pending": [original_entry]}, default_flow_style=False, sort_keys=False
        )
    )

    # Act
    mod.append_pending_entry(root, "skills/new/", "skill", "created", "record-skill")

    # Assert: script succeeded, original entry preserved verbatim, new entry appended
    data = yaml.safe_load(pending_path.read_text())
    assert len(data["pending"]) == 2
    first = data["pending"][0]
    assert first["path"] == "skills/preexisting/"
    created_at = first["created_at"]
    if not isinstance(created_at, str):
        created_at = created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert created_at == "2026-05-13T07:00:00Z"
    assert data["pending"][1]["path"] == "skills/new/"
