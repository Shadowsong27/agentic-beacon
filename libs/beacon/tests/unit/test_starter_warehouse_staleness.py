"""Staleness guard for the agentic-beacon-starter-warehouse repo.

When warehouse templates change, the starter warehouse at
https://github.com/Shadowsong27/agentic-beacon-starter-warehouse
must be re-generated and its .beacon/template-checksums.json updated.

This test pins the raw template file hashes at the time the starter
warehouse was last synced. If templates drift, this test fails before
release so the maintainer is reminded to update the starter warehouse.

Maintenance rule
----------------
After updating the starter warehouse:
1. Re-run `abc warehouse init` to regenerate `.beacon/template-checksums.json`.
2. Update STARTER_WAREHOUSE_PINNED_TEMPLATE_HASHES below with the new raw
   template hashes (use test output or compute via `sha256sum` on each file
   under libs/beacon/src/beacon/data/templates/).
"""

import hashlib
from pathlib import Path

# Raw template file hashes at the time the starter warehouse was last synced.
# Keys are relative paths matching the template directory structure.
# Update this dict whenever the starter warehouse is re-generated.
STARTER_WAREHOUSE_PINNED_TEMPLATE_HASHES: dict[str, str] = {
    ".gitignore": "84eeaf600db2a2b5aaa963c05e4ea13af92dc973a6b63740554212fec1701cb7",
    "agents/README.md": "5ffded083242776b0016aabbfe66baa01798892ea17c0a7da1bf551707df4b1c",
    "README.md": "3c1c02ce7df7161a4f6286638b9d4b12fb462c08e8bba12aa2d1b720de6d5856",
    "contexts/README.md": "90dfeb30f5844e16596302291d9f9770e2f714a35733d525ab7fe913be49912b",
    "docs/architecture.md": "965c303c69da4de6774677c84eff345287414a5937c196ad14f3404867791f4f",
    "docs/contribution-guide.md": "62d8af6eecb71ff0c29d5179fe59637ad18aff71455ba149cff3f3aea3d12945",
    "knowledge/README.md": "fb2fa6a609bc234b37f87268c2322b66b529aabd5cdf41b5ccd88dab5ed026fc",
    "skills/README.md": "abbf8a13d85ec87c77cc164673ab7924de6b44ead33482bedcf9765c88837179",
}

_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "src/beacon/data/templates"


def test_starter_warehouse_templates_are_current():
    """Fail if warehouse templates have changed since the starter warehouse was last synced.

    If this test fails:
    1. Re-generate the starter warehouse:
         abc warehouse init ~/agentic-beacon-starter-warehouse
    2. Push the updated repo to Shadowsong27/agentic-beacon-starter-warehouse
    3. Update STARTER_WAREHOUSE_PINNED_TEMPLATE_HASHES in this file with the
       new hashes shown in the failure message below.
    """
    drifted = []
    for tmpl in sorted(_TEMPLATES_DIR.rglob("*")):
        if not tmpl.is_file():
            continue
        rel = tmpl.relative_to(_TEMPLATES_DIR).as_posix()
        current_sha = hashlib.sha256(tmpl.read_bytes()).hexdigest()
        pinned_sha = STARTER_WAREHOUSE_PINNED_TEMPLATE_HASHES.get(rel)

        if pinned_sha is None:
            drifted.append(f"  NEW FILE  {rel}: {current_sha}  (add to pinned hashes)")
        elif current_sha != pinned_sha:
            drifted.append(
                f"  CHANGED   {rel}: {current_sha}  (was {pinned_sha[:12]}...)"
            )

    assert not drifted, (
        "Warehouse templates have changed since the starter warehouse was last synced.\n\n"
        "Action required:\n"
        "  1. Re-generate: abc warehouse init ~/tmp-starter && push to "
        "Shadowsong27/agentic-beacon-starter-warehouse\n"
        "  2. Update STARTER_WAREHOUSE_PINNED_TEMPLATE_HASHES in this file.\n\n"
        "Drifted files:\n" + "\n".join(drifted)
    )
