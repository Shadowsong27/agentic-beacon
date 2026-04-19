"""Unit tests for WarehouseUpgrader (TDD — written before implementation)."""

import hashlib
import json
from pathlib import Path

import pytest
from beacon.domains.artifact.checksums import compute_sha256
from beacon.domains.distribution.upgrader import FileState, WarehouseUpgrader
from beacon.initializer import WarehouseInitializer

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_warehouse(tmp_path: Path, org_name: str = "Test") -> Path:
    """Create a fresh initialised warehouse and return its path."""
    wh = tmp_path / "warehouse"
    WarehouseInitializer(warehouse_path=wh).init(org_name=org_name, init_git=False)
    return wh


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# classify_file — TC1-TC6
# ---------------------------------------------------------------------------


def test_classify_file_unmodified(tmp_path):
    """TC1: on-disk hash == stored checksum → unmodified."""
    wh = _make_warehouse(tmp_path)
    upgrader = WarehouseUpgrader(warehouse_path=wh)
    state = upgrader.classify_file("README.md")
    assert state == FileState.UNMODIFIED


def test_classify_file_user_modified(tmp_path):
    """TC2: on-disk hash != stored checksum → user-modified."""
    wh = _make_warehouse(tmp_path)
    # Tamper with README
    (wh / "README.md").write_text("# My custom README\n", encoding="utf-8")
    upgrader = WarehouseUpgrader(warehouse_path=wh)
    state = upgrader.classify_file("README.md")
    assert state == FileState.USER_MODIFIED


def test_classify_file_legacy_unmodified(tmp_path):
    """TC3: no checksum file; on-disk hash in KNOWN_TEMPLATE_HASHES → legacy-unmodified."""
    wh = _make_warehouse(tmp_path)
    # Remove checksum file to simulate legacy warehouse
    (wh / ".beacon" / "template-checksums.json").unlink()
    upgrader = WarehouseUpgrader(warehouse_path=wh)
    # README.md was written from template, hash should be in registry
    # (only if sample-warehouse README matches template — use a template file instead)
    state = upgrader.classify_file("skills/README.md")
    # skills/README.md has no org_name substitution so hash matches template exactly
    assert state == FileState.LEGACY_UNMODIFIED


def test_classify_file_legacy_unknown(tmp_path):
    """TC4: no checksum file; on-disk hash not in registry → legacy-unknown."""
    wh = _make_warehouse(tmp_path)
    (wh / ".beacon" / "template-checksums.json").unlink()
    (wh / "README.md").write_text("# Totally custom\n", encoding="utf-8")
    upgrader = WarehouseUpgrader(warehouse_path=wh)
    state = upgrader.classify_file("README.md")
    assert state == FileState.LEGACY_UNKNOWN


def test_classify_file_missing_raises(tmp_path):
    """TC5: file doesn't exist → FileNotFoundError."""
    wh = _make_warehouse(tmp_path)
    upgrader = WarehouseUpgrader(warehouse_path=wh)
    with pytest.raises(FileNotFoundError):
        upgrader.classify_file("nonexistent.md")


def test_classify_file_key_missing_from_checksums(tmp_path):
    """TC6: checksum file exists but key missing for this file → user-modified."""
    wh = _make_warehouse(tmp_path)
    # Remove README.md from stored checksums
    cs_path = wh / ".beacon" / "template-checksums.json"
    data = json.loads(cs_path.read_text())
    del data["files"]["README.md"]
    cs_path.write_text(json.dumps(data))
    upgrader = WarehouseUpgrader(warehouse_path=wh)
    state = upgrader.classify_file("README.md")
    assert state == FileState.USER_MODIFIED


# ---------------------------------------------------------------------------
# Upgrade loop — default mode (TC1-TC4)
# ---------------------------------------------------------------------------


def test_upgrade_unmodified_file_is_overwritten(tmp_path):
    """TC1: unmodified file → overwritten with new template content."""
    wh = _make_warehouse(tmp_path)
    upgrader = WarehouseUpgrader(warehouse_path=wh)
    new_templates = {"skills/README.md": "# New Skills Content\n"}
    result = upgrader.run(template_overrides=new_templates)
    assert (wh / "skills" / "README.md").read_text(
        encoding="utf-8"
    ) == "# New Skills Content\n"
    assert result["upgraded"] >= 1


def test_upgrade_user_modified_file_writes_sidecar(tmp_path):
    """TC2: user-modified file → .new sidecar written; original untouched."""
    wh = _make_warehouse(tmp_path)
    (wh / "README.md").write_text("# My Custom README\n", encoding="utf-8")
    upgrader = WarehouseUpgrader(warehouse_path=wh)
    new_templates = {"README.md": "# Updated Template\n"}
    upgrader.run(template_overrides=new_templates)
    # Original untouched
    assert (wh / "README.md").read_text(encoding="utf-8") == "# My Custom README\n"
    # Sidecar written
    assert (wh / "README.md.new").exists()
    assert (wh / "README.md.new").read_text(encoding="utf-8") == "# Updated Template\n"


def test_upgrade_legacy_unmodified_is_upgraded(tmp_path):
    """TC3: legacy-unmodified → overwritten."""
    wh = _make_warehouse(tmp_path)
    (wh / ".beacon" / "template-checksums.json").unlink()
    upgrader = WarehouseUpgrader(warehouse_path=wh)
    new_templates = {"skills/README.md": "# New Skills\n"}
    upgrader.run(template_overrides=new_templates)
    assert (wh / "skills" / "README.md").read_text(encoding="utf-8") == "# New Skills\n"


def test_upgrade_legacy_unknown_writes_sidecar(tmp_path):
    """TC4: legacy-unknown → .new sidecar written."""
    wh = _make_warehouse(tmp_path)
    (wh / ".beacon" / "template-checksums.json").unlink()
    (wh / "README.md").write_text("# Custom legacy content\n", encoding="utf-8")
    upgrader = WarehouseUpgrader(warehouse_path=wh)
    new_templates = {"README.md": "# New Template\n"}
    upgrader.run(template_overrides=new_templates)
    assert (wh / "README.md.new").exists()
    assert (wh / "README.md").read_text(encoding="utf-8") == "# Custom legacy content\n"


# ---------------------------------------------------------------------------
# .new sidecar — TC1-TC2
# ---------------------------------------------------------------------------


def test_sidecar_not_overwritten_if_exists(tmp_path):
    """TC1: .new file already present → second run skips, prints warning."""
    wh = _make_warehouse(tmp_path)
    (wh / "README.md").write_text("# Custom\n", encoding="utf-8")
    (wh / "README.md.new").write_text("# Pre-existing sidecar\n", encoding="utf-8")
    upgrader = WarehouseUpgrader(warehouse_path=wh)
    new_templates = {"README.md": "# New Template\n"}
    result = upgrader.run(template_overrides=new_templates)
    # Sidecar must not be overwritten
    assert (wh / "README.md.new").read_text(
        encoding="utf-8"
    ) == "# Pre-existing sidecar\n"
    assert result["sidecar_skipped"] >= 1


# ---------------------------------------------------------------------------
# --dry-run — TC1-TC3
# ---------------------------------------------------------------------------


def test_dry_run_does_not_write_files(tmp_path):
    """TC1-TC2: dry-run prints plans but writes nothing."""
    wh = _make_warehouse(tmp_path)
    original_readme = (wh / "README.md").read_text(encoding="utf-8")
    upgrader = WarehouseUpgrader(warehouse_path=wh)
    new_templates = {"README.md": "# Dry Run Template\n"}
    upgrader.run(template_overrides=new_templates, dry_run=True)
    assert (wh / "README.md").read_text(encoding="utf-8") == original_readme
    assert not (wh / "README.md.new").exists()


def test_dry_run_does_not_update_checksums(tmp_path):
    """TC3: checksum file NOT updated after dry run."""
    wh = _make_warehouse(tmp_path)
    cs_before = (wh / ".beacon" / "template-checksums.json").read_text()
    upgrader = WarehouseUpgrader(warehouse_path=wh)
    upgrader.run(template_overrides={"README.md": "# Changed\n"}, dry_run=True)
    assert (wh / ".beacon" / "template-checksums.json").read_text() == cs_before


# ---------------------------------------------------------------------------
# --force — TC1-TC2
# ---------------------------------------------------------------------------


def test_force_overwrites_user_modified_file(tmp_path):
    """TC1: force on user-modified file → file overwritten; no sidecar."""
    wh = _make_warehouse(tmp_path)
    (wh / "README.md").write_text("# Custom\n", encoding="utf-8")
    upgrader = WarehouseUpgrader(warehouse_path=wh)
    new_templates = {"README.md": "# Force Template\n"}
    upgrader.run(template_overrides=new_templates, force=True)
    assert (wh / "README.md").read_text(encoding="utf-8") == "# Force Template\n"
    assert not (wh / "README.md.new").exists()


def test_force_overwrites_unmodified_file(tmp_path):
    """TC2: force on unmodified file → also overwritten."""
    wh = _make_warehouse(tmp_path)
    upgrader = WarehouseUpgrader(warehouse_path=wh)
    new_templates = {"skills/README.md": "# Force Skills\n"}
    upgrader.run(template_overrides=new_templates, force=True)
    assert (wh / "skills" / "README.md").read_text(
        encoding="utf-8"
    ) == "# Force Skills\n"


# ---------------------------------------------------------------------------
# Checksum refresh after upgrade
# ---------------------------------------------------------------------------


def test_checksum_file_refreshed_after_upgrade(tmp_path):
    """Checksum file is updated after successful (non-dry-run) upgrade."""
    wh = _make_warehouse(tmp_path)
    upgrader = WarehouseUpgrader(warehouse_path=wh)
    new_content = "# Updated Skills\n"
    new_templates = {"skills/README.md": new_content}
    upgrader.run(template_overrides=new_templates)
    hashes = json.loads((wh / ".beacon" / "template-checksums.json").read_text())[
        "files"
    ]
    expected_sha = compute_sha256(new_content)
    assert hashes["skills/README.md"] == expected_sha


# ---------------------------------------------------------------------------
# Legacy warehouse full flow
# ---------------------------------------------------------------------------


def test_legacy_warehouse_historical_match_upgraded(tmp_path):
    """Legacy warehouse: pristine file (historical hash match) → upgraded."""
    wh = _make_warehouse(tmp_path)
    (wh / ".beacon" / "template-checksums.json").unlink()
    upgrader = WarehouseUpgrader(warehouse_path=wh)
    new_templates = {"skills/README.md": "# New Skills\n"}
    upgrader.run(template_overrides=new_templates)
    assert (wh / "skills" / "README.md").read_text(encoding="utf-8") == "# New Skills\n"


def test_legacy_warehouse_unknown_hash_writes_sidecar(tmp_path):
    """Legacy warehouse: modified file (unknown hash) → .new sidecar."""
    wh = _make_warehouse(tmp_path)
    (wh / ".beacon" / "template-checksums.json").unlink()
    (wh / "skills" / "README.md").write_text(
        "# Customised skills doc\n", encoding="utf-8"
    )
    upgrader = WarehouseUpgrader(warehouse_path=wh)
    new_templates = {"skills/README.md": "# New Skills\n"}
    upgrader.run(template_overrides=new_templates)
    assert (wh / "skills" / "README.md").read_text() == "# Customised skills doc\n"
    assert (wh / "skills" / "README.md.new").exists()


# ---------------------------------------------------------------------------
# New template file handling (file absent from warehouse)
# ---------------------------------------------------------------------------


def test_new_template_file_created_when_absent_from_checksums(tmp_path):
    """File not on disk and not in stored checksums → new template → created."""
    wh = _make_warehouse(tmp_path)
    # Remove a file AND its checksum entry to simulate a brand-new template
    (wh / "skills" / "README.md").unlink()
    cs_path = wh / ".beacon" / "template-checksums.json"
    data = json.loads(cs_path.read_text())
    del data["files"]["skills/README.md"]
    cs_path.write_text(json.dumps(data))

    upgrader = WarehouseUpgrader(warehouse_path=wh)
    new_templates = {"skills/README.md": "# Newly Added Template\n"}
    result = upgrader.run(template_overrides=new_templates)

    assert (wh / "skills" / "README.md").read_text(
        encoding="utf-8"
    ) == "# Newly Added Template\n"
    assert result["upgraded"] >= 1


def test_user_deleted_file_is_skipped(tmp_path):
    """File not on disk but present in stored checksums → user deleted it → skip."""
    wh = _make_warehouse(tmp_path)
    # Delete the file but leave its checksum entry intact
    (wh / "skills" / "README.md").unlink()

    upgrader = WarehouseUpgrader(warehouse_path=wh)
    new_templates = {"skills/README.md": "# Would overwrite\n"}
    result = upgrader.run(template_overrides=new_templates)

    assert not (wh / "skills" / "README.md").exists()
    assert result["skipped"] >= 1


def test_new_template_file_dry_run_does_not_create(tmp_path):
    """dry-run for new template → prints [would add] but does not create file."""
    wh = _make_warehouse(tmp_path)
    (wh / "skills" / "README.md").unlink()
    cs_path = wh / ".beacon" / "template-checksums.json"
    data = json.loads(cs_path.read_text())
    del data["files"]["skills/README.md"]
    cs_path.write_text(json.dumps(data))

    upgrader = WarehouseUpgrader(warehouse_path=wh)
    upgrader.run(template_overrides={"skills/README.md": "# New\n"}, dry_run=True)

    assert not (wh / "skills" / "README.md").exists()


def test_new_template_checksum_stored_after_creation(tmp_path):
    """Newly created template file hash is stored in checksums."""
    wh = _make_warehouse(tmp_path)
    (wh / "skills" / "README.md").unlink()
    cs_path = wh / ".beacon" / "template-checksums.json"
    data = json.loads(cs_path.read_text())
    del data["files"]["skills/README.md"]
    cs_path.write_text(json.dumps(data))

    new_content = "# Newly Added Template\n"
    upgrader = WarehouseUpgrader(warehouse_path=wh)
    upgrader.run(template_overrides={"skills/README.md": new_content})

    hashes = json.loads(cs_path.read_text())["files"]
    assert hashes["skills/README.md"] == compute_sha256(new_content)
