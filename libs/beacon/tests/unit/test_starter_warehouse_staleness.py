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
    "agents/README.md": "db6db08eef486e4dbf5713474262ff2f1caa6d3680df053b17c4b695d2274122",
    "README.md": "ec91ea5f824620bd4b8c8f0aba84758bcf8af61738aae6af5c032f2ae6cdf020",
    "contexts/README.md": "90dfeb30f5844e16596302291d9f9770e2f714a35733d525ab7fe913be49912b",
    "docs/architecture.md": "73e93f5e3cd19dcf692a4e2b5465bdcdbc40f0677362e16bf6805bd9beb2c8ba",
    "docs/contribution-guide.md": "a5f8e97d09c4b114d099ffef569c2f0d9a37cc9efad8b6704a4f7ec550057a18",
    "knowledge/README.md": "fb2fa6a609bc234b37f87268c2322b66b529aabd5cdf41b5ccd88dab5ed026fc",
    "skills/README.md": "be570d20bec7563e77762095c45af6aff2367bcf122cc46514ead6265b0af6fb",
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
