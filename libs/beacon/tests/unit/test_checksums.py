"""Unit tests for checksums.py utilities and checksum writing on warehouse init."""

import hashlib
import json

from beacon.data.historical_hashes import (
    KNOWN_TEMPLATE_HASHES,
    is_known_hash,
    normalise_path,
)
from beacon.domains.artifact.checksums import (
    compute_sha256,
    compute_sha256_bytes,
    read_checksums,
    write_checksums,
)
from beacon.initializer import TEMPLATE_FILES, WarehouseInitializer

# ---------------------------------------------------------------------------
# compute_sha256
# ---------------------------------------------------------------------------


def test_compute_sha256_known_string():
    # "hello" SHA256 is well-known
    assert (
        compute_sha256("hello")
        == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    )


def test_compute_sha256_empty_string():
    assert (
        compute_sha256("")
        == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )


def test_compute_sha256_unicode():
    content = "héllo wörld"
    expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
    assert compute_sha256(content) == expected


def test_compute_sha256_bytes_known():
    assert (
        compute_sha256_bytes(b"hello")
        == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    )


# ---------------------------------------------------------------------------
# write_checksums / read_checksums
# ---------------------------------------------------------------------------


def test_write_and_read_checksums(tmp_path):
    hashes = {"README.md": "abc123", "docs/architecture.md": "def456"}
    write_checksums(tmp_path, hashes)

    checksums_file = tmp_path / ".beacon" / "template-checksums.json"
    assert checksums_file.exists()

    read_back = read_checksums(tmp_path)
    assert read_back == hashes


def test_read_checksums_returns_none_when_missing(tmp_path):
    assert read_checksums(tmp_path) is None


def test_write_checksums_creates_beacon_dir(tmp_path):
    write_checksums(tmp_path, {"README.md": "abc"})
    assert (tmp_path / ".beacon").is_dir()


def test_checksums_json_contains_beacon_version(tmp_path):
    write_checksums(tmp_path, {"README.md": "abc"})
    data = json.loads((tmp_path / ".beacon" / "template-checksums.json").read_text())
    assert "beacon_version" in data
    assert isinstance(data["beacon_version"], str)


# ---------------------------------------------------------------------------
# historical_hashes helpers
# ---------------------------------------------------------------------------


def test_normalise_path_forward_slash():
    assert normalise_path("docs/architecture.md") == "docs/architecture.md"


def test_normalise_path_backslash():
    assert normalise_path("docs\\architecture.md") == "docs/architecture.md"


def test_is_known_hash_match():
    key = list(KNOWN_TEMPLATE_HASHES.keys())[0]
    sha = KNOWN_TEMPLATE_HASHES[key][0]
    assert is_known_hash(key, sha) is True


def test_is_known_hash_no_match():
    assert is_known_hash("README.md", "deadbeef" * 8) is False


def test_is_known_hash_unknown_file():
    assert is_known_hash("nonexistent.md", "abc123") is False


def test_is_known_hash_backslash_path():
    key = list(KNOWN_TEMPLATE_HASHES.keys())[0]
    sha = KNOWN_TEMPLATE_HASHES[key][0]
    backslash_key = key.replace("/", "\\")
    assert is_known_hash(backslash_key, sha) is True


# ---------------------------------------------------------------------------
# WarehouseInitializer writes checksum file
# ---------------------------------------------------------------------------


def test_init_writes_checksum_file(tmp_path):
    initializer = WarehouseInitializer(warehouse_path=tmp_path / "wh")
    initializer.init(org_name="Test Org", init_git=False)

    checksums_path = tmp_path / "wh" / ".beacon" / "template-checksums.json"
    assert checksums_path.exists()


def test_init_checksum_keys_match_template_files(tmp_path):
    wh = tmp_path / "wh"
    initializer = WarehouseInitializer(warehouse_path=wh)
    initializer.init(org_name="Test Org", init_git=False)

    hashes = read_checksums(wh)
    assert hashes is not None
    for rel in TEMPLATE_FILES:
        assert rel in hashes, f"Missing checksum for {rel}"


def test_init_checksum_values_are_correct_sha256(tmp_path):
    wh = tmp_path / "wh"
    initializer = WarehouseInitializer(warehouse_path=wh)
    initializer.init(org_name="Test Org", init_git=False)

    hashes = read_checksums(wh)
    assert hashes is not None
    for rel, stored_sha in hashes.items():
        file_path = wh / rel
        actual_sha = compute_sha256(file_path.read_text(encoding="utf-8"))
        assert stored_sha == actual_sha, f"Hash mismatch for {rel}"


def test_init_beacon_version_in_checksum_file(tmp_path):
    wh = tmp_path / "wh"
    initializer = WarehouseInitializer(warehouse_path=wh)
    initializer.init(org_name="Test Org", init_git=False)

    data = json.loads(
        (wh / ".beacon" / "template-checksums.json").read_text(encoding="utf-8")
    )
    assert "beacon_version" in data


def test_init_no_git_flag_does_not_affect_checksums(tmp_path):
    wh = tmp_path / "wh"
    initializer = WarehouseInitializer(warehouse_path=wh)
    initializer.init(org_name="Test Org", init_git=False)
    assert (wh / ".beacon" / "template-checksums.json").exists()


def test_gitignore_does_not_exclude_beacon_dir(tmp_path):
    wh = tmp_path / "wh"
    initializer = WarehouseInitializer(warehouse_path=wh)
    initializer.init(org_name="Test Org", init_git=False)

    gitignore_content = (wh / ".gitignore").read_text(encoding="utf-8")
    assert ".beacon" not in gitignore_content
    assert ".beacon/" not in gitignore_content
