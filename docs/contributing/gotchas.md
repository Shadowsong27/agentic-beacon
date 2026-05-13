# Gotchas and Common Pitfalls

Things that have bitten contributors before. Read this before debugging a confusing failure.

---

## `cd libs/beacon` Before Running Tests

**Do not.** Tests must be run from the repo root:

```bash
# correct
pytest

# wrong — testpaths are configured in the root pyproject.toml
cd libs/beacon && pytest
```

`pytest.ini` / `pyproject.toml` at the repo root sets `testpaths = ["libs/beacon/tests"]`.
Running pytest inside `libs/beacon/` uses a different configuration file and may miss options
or discover tests differently.

---

## Creating a venv Inside `libs/beacon/`

**Do not.** This is a uv workspace project. The single virtualenv lives at the repo root:

```bash
# correct — run from repo root
uv sync --group dev
.venv/bin/abc --version

# wrong — never create a nested venv
cd libs/beacon && python -m venv .venv
```

A nested venv under `libs/beacon/` will shadow the workspace venv and break cross-workspace
dependency resolution.

---

## Running on Windows

Windows is explicitly rejected at runtime. Beacon relies on filesystem symlinks for artifact
distribution. If you attempt to run `abc` on Windows or Cygwin, you will see an
`UnsupportedPlatformError` immediately.

For Windows contributors: use WSL2.

---

## Relative Imports

Relative imports are banned and enforced by TC4/TC6 in `test_architecture.py`:

```python
# wrong — will fail test_architecture.py
from ..core.manifest import BeaconManifest
```

Always use absolute imports:

```python
# correct
from beacon.core.manifest.beacon import BeaconManifest
```

---

## Importing from `__init__.py`

`__init__.py` files are empty markers. Importing from them is banned (TC7):

```python
# wrong — __init__.py is empty; this import will fail at import time
from beacon.core.manifest import BeaconManifest

# correct — import from the defining module
from beacon.core.manifest.beacon import BeaconManifest
```

If you see an `ImportError` about a name not existing in `beacon.core.manifest`, this is why.

---

## Adding Logic to a Domain but Importing It from Another Domain

Cross-domain imports must stay within depth 4 (TC5):

```python
# allowed (depth 4: beacon.domains.artifact.skill)
from beacon.domains.artifact.skill import wire_single_skill

# NOT allowed (depth 5: beacon.domains.artifact.skill.helpers)
from beacon.domains.artifact.skill.helpers import some_util
```

If you need to share logic between two domains, either:
1. Move it to `core/` (only if multiple domains genuinely need it), or
2. Keep it in one domain and accept that the other domain imports at depth 4.

---

## Adding I/O to a CLI Handler

CLI handlers must not perform I/O (TC8). These are banned in `cli/` handler bodies:

```
open(), subprocess.run(), os.walk(), glob.glob(), shutil.copy(),
Path.read_text(), Path.write_text(), Path.unlink(), Path.mkdir(),
Path.rglob(), Path.glob(), yaml.load(), tomllib.load()
```

Put I/O in the domain layer. The CLI handler calls the domain and formats the result.

---

## Adding `click`, `rich`, or `sys.exit()` to Domain Code

Domains must not import `click`, `rich`, or call `sys.exit()` (TC10). These belong in `cli/`.

Known waivers exist (`_TC10_WAIVERS`) but adding new ones requires an explicit discussion and
a TODO tracking the cleanup.

---

## Stale Waivers in `test_architecture.py`

If you remove a file or rename a handler that is listed in `_TC9B_WAIVERS` or `_TC10_WAIVERS`,
the architecture test will fail with a "stale waiver" error. Update the waiver dictionary
(or remove the entry if the waiver is no longer needed) alongside the code change.

---

## Pre-commit Hook Removes Trailing Whitespace

The `trailing-whitespace` hook strips trailing spaces from all files on commit. If your editor
adds trailing whitespace, your commit will be amended automatically. After the hook runs,
re-stage the modified files:

```bash
git add -u
git commit  # try again
```

---

## Git Identity Not Configured

Integration tests that create git commits will fail with:

```
Author identity unknown
*** Please tell me who you are.
```

Set your git identity globally:

```bash
git config --global user.email "you@example.com"
git config --global user.name "Your Name"
```

---

## Warehouse Not Connected When Running `abc sync`

`abc sync` requires a connected warehouse (`.agentic-beacon/config.toml` must exist). If you
see `WorkspaceConfigError: no warehouse connected`, run:

```bash
abc warehouse connect /path/to/your/warehouse
```

or for testing, create the config manually:

```bash
mkdir -p .agentic-beacon
cat > .agentic-beacon/config.toml <<'EOF'
[warehouse]
local_path = "/absolute/path/to/warehouse"
main_branch = "main"
EOF
```

---

## `pending.yaml` Growing Without Being Adopted

If `record-knowledge` or `record-skill` writes entries to `.agentic-beacon/pending.yaml` and
you never run `abc adopt`, every subsequent `abc` invocation prints a pending alert on stderr.
This is by design — run `abc adopt` to review and accept/reject/defer the pending items.
