"""Historical SHA256 hashes of all known pristine warehouse template versions.

This registry is used to classify legacy warehouses (created before checksum
tracking was introduced) without a ``.beacon/template-checksums.json`` file.

If an on-disk file's hash matches any entry in ``KNOWN_TEMPLATE_HASHES``, the
file is treated as an unmodified template and is safe to upgrade.

Maintenance rule: whenever a template under ``data/templates/`` changes, add
the new file's SHA256 to the corresponding list here before releasing. The CI
regression test ``test_template_commands.py`` will fail if current hashes are
missing, ensuring this dict stays in sync.
"""

KNOWN_TEMPLATE_HASHES: dict[str, list[str]] = {
    ".gitignore": [
        # v2.x (current)
        "2a2ea65bc817582bf992ebc0ffe919774635173f138ab35dc6c68f237ec2c15e",
    ],
    "README.md": [
        # v2.x (current)
        "3c1c02ce7df7161a4f6286638b9d4b12fb462c08e8bba12aa2d1b720de6d5856",
    ],
    "contexts/README.md": [
        # v2.2+ (current)
        "90dfeb30f5844e16596302291d9f9770e2f714a35733d525ab7fe913be49912b",
    ],
    "docs/architecture.md": [
        # v2.x (current)
        "965c303c69da4de6774677c84eff345287414a5937c196ad14f3404867791f4f",
    ],
    "docs/contribution-guide.md": [
        # v2.x (current)
        "62d8af6eecb71ff0c29d5179fe59637ad18aff71455ba149cff3f3aea3d12945",
    ],
    "knowledge/README.md": [
        # v2.x (current)
        "fb2fa6a609bc234b37f87268c2322b66b529aabd5cdf41b5ccd88dab5ed026fc",
    ],
    "skills/README.md": [
        # v2.x (current)
        "abbf8a13d85ec87c77cc164673ab7924de6b44ead33482bedcf9765c88837179",
    ],
}


def normalise_path(path: str) -> str:
    """Normalise a file path to use forward slashes (cross-platform lookup)."""
    return path.replace("\\", "/")


def is_known_hash(rel_path: str, sha256: str) -> bool:
    """Return True if *sha256* is a known pristine hash for *rel_path*."""
    key = normalise_path(rel_path)
    return sha256 in KNOWN_TEMPLATE_HASHES.get(key, [])
