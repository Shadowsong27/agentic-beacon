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
    "agents/README.md": "6f05be87226b2892c20d1a75bee24b682590506ee22dbdc2c911f959ff625590",
    "agents/agents.yaml": "9f03ec77cf08ad3296d640d70a65038e0cdf46a3335e887f6ee130ce314077e2",
    "README.md": "052846a397d19d160ab86287a7bc211e92c4943bcea72ca34909155aa78ebf1a",
    "contexts/README.md": "90dfeb30f5844e16596302291d9f9770e2f714a35733d525ab7fe913be49912b",
    "docs/architecture.md": "d92c1da4c0d7647b70add95aba1dfeb49513ce18035116b9346f11b406bdc391",
    "docs/contribution-guide.md": "68f697984db7052f5179f495d6349fcd38452b8924269bd0a3337449b1f8fa58",
    "knowledge/README.md": "fb2fa6a609bc234b37f87268c2322b66b529aabd5cdf41b5ccd88dab5ed026fc",
    "skills/README.md": "91759e4e3657b1aaa570b0d2bcb09c2a12b46f34f19147ca2b288e9cfd4ed39f",
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
