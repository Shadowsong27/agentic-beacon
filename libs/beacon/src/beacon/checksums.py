"""SHA256 checksum utilities for warehouse template tracking."""

import hashlib
import json
from importlib.metadata import version
from pathlib import Path

_CHECKSUMS_FILE = ".beacon/template-checksums.json"


def compute_sha256(content: str) -> str:
    """Return the SHA256 hex digest of *content* (UTF-8 encoded)."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def compute_sha256_bytes(data: bytes) -> str:
    """Return the SHA256 hex digest of raw *data* bytes."""
    return hashlib.sha256(data).hexdigest()


def write_checksums(warehouse_path: Path, file_hashes: dict[str, str]) -> None:
    """Write ``.beacon/template-checksums.json`` to *warehouse_path*.

    Args:
        warehouse_path: Root of the warehouse directory.
        file_hashes: Mapping of relative path (forward-slash) → SHA256 hex digest.
    """
    beacon_dir = warehouse_path / ".beacon"
    beacon_dir.mkdir(exist_ok=True)

    try:
        beacon_version = version("agentic-beacon")
    except Exception:
        beacon_version = "unknown"

    payload = {
        "beacon_version": beacon_version,
        "files": file_hashes,
    }
    (beacon_dir / "template-checksums.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def read_checksums(warehouse_path: Path) -> dict[str, str] | None:
    """Read ``.beacon/template-checksums.json`` from *warehouse_path*.

    Returns:
        Mapping of relative path → SHA256, or ``None`` if the file does not exist.
    """
    checksums_path = warehouse_path / _CHECKSUMS_FILE
    if not checksums_path.exists():
        return None
    data = json.loads(checksums_path.read_text(encoding="utf-8"))
    return data.get("files", {})
