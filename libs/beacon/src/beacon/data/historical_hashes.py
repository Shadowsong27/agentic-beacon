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
        # v2.x
        "2a2ea65bc817582bf992ebc0ffe919774635173f138ab35dc6c68f237ec2c15e",
        # v2.2+ (agent skill dirs added)
        "84eeaf600db2a2b5aaa963c05e4ea13af92dc973a6b63740554212fec1701cb7",
    ],
    "agents/README.md": [
        # v2.3+ (agents artifact type introduced)
        "5ffded083242776b0016aabbfe66baa01798892ea17c0a7da1bf551707df4b1c",
        # v3.0 — symlink-based sync migration: `abc install agents/` → `abc agents sync`
        "db6db08eef486e4dbf5713474262ff2f1caa6d3680df053b17c4b695d2274122",
        # v3.0 — global agents switched from copies to symlinks
        "6b99ed582044fab280e9a6ae6fd72fa48d05a15c4c53446337fc1c92f2274e4c",
        # v3.x — move-agent-requires-to-warehouse-manifest
        "5ee9768984c954f7ef8a3157018f283828f3ac10ea45b3b3a56053e13c7d4b42",
        # project-scoped-agents — dual agent semantics
        "6f05be87226b2892c20d1a75bee24b682590506ee22dbdc2c911f959ff625590",
    ],
    "agents/agents.yaml": [
        # v3.x — move-agent-requires-to-warehouse-manifest
        "9f03ec77cf08ad3296d640d70a65038e0cdf46a3335e887f6ee130ce314077e2",
    ],
    "README.md": [
        # v2.x
        "3c1c02ce7df7161a4f6286638b9d4b12fb462c08e8bba12aa2d1b720de6d5856",
        # v3.0 — symlink-based sync migration: rewritten around symlinks + warehouse subcommands
        "ec91ea5f824620bd4b8c8f0aba84758bcf8af61738aae6af5c032f2ae6cdf020",
        # v3.0 — global agents switched from copies to symlinks
        "7d819ebc3f73c2380b128edf888dc47bb44ca8a767cff7c2621fca4b6979a430",
        # v3.0 — setup simplified around abc adopt
        "e7d52b2e8fc6725079fc11afd3a7ee9435229d399eeb71b0bf9ebf74e1284aaa",
        # project-scoped-agents — dual agent semantics
        "052846a397d19d160ab86287a7bc211e92c4943bcea72ca34909155aa78ebf1a",
    ],
    "contexts/README.md": [
        # v2.2+ (current)
        "90dfeb30f5844e16596302291d9f9770e2f714a35733d525ab7fe913be49912b",
    ],
    "docs/architecture.md": [
        # v2.x
        "965c303c69da4de6774677c84eff345287414a5937c196ad14f3404867791f4f",
        # v3.0 — symlink-based sync migration: updated contribution flow
        "73e93f5e3cd19dcf692a4e2b5465bdcdbc40f0677362e16bf6805bd9beb2c8ba",
        # v3.0 — setup simplified around abc adopt
        "d92c1da4c0d7647b70add95aba1dfeb49513ce18035116b9346f11b406bdc391",
    ],
    "docs/contribution-guide.md": [
        # v2.x
        "62d8af6eecb71ff0c29d5179fe59637ad18aff71455ba149cff3f3aea3d12945",
        # v3.0 — symlink-based sync migration: `abc status` → `abc warehouse status`
        "a5f8e97d09c4b114d099ffef569c2f0d9a37cc9efad8b6704a4f7ec550057a18",
        # v3.0 — setup simplified around abc adopt
        "68f697984db7052f5179f495d6349fcd38452b8924269bd0a3337449b1f8fa58",
    ],
    "knowledge/README.md": [
        # v2.x (current)
        "fb2fa6a609bc234b37f87268c2322b66b529aabd5cdf41b5ccd88dab5ed026fc",
    ],
    "skills/README.md": [
        # v2.x
        "abbf8a13d85ec87c77cc164673ab7924de6b44ead33482bedcf9765c88837179",
        # v3.0 — symlink-based sync migration: `abc install skills/` → declare in beacon.yaml + `abc sync`
        "be570d20bec7563e77762095c45af6aff2367bcf122cc46514ead6265b0af6fb",
        # project-scoped-agents — added agents: to beacon.yaml snippet
        "91759e4e3657b1aaa570b0d2bcb09c2a12b46f34f19147ca2b288e9cfd4ed39f",
    ],
}


def normalise_path(path: str) -> str:
    """Normalise a file path to use forward slashes (cross-platform lookup)."""
    return path.replace("\\", "/")


def is_known_hash(rel_path: str, sha256: str) -> bool:
    """Return True if *sha256* is a known pristine hash for *rel_path*."""
    key = normalise_path(rel_path)
    return sha256 in KNOWN_TEMPLATE_HASHES.get(key, [])
