# Implementation Tasks — warehouse-template-upgrade

## Repositories & Branches

| Repo | Path | Branch | Role |
|------|------|--------|------|
| `agentic-beacon` | `~/Code/oss/agentic-beacon` | `feat/warehouse-template-upgrade` | Code changes — all implementation |

---

## 🔴 TDD WORKFLOW - MANDATORY FOR ALL TASKS

**CRITICAL**: This project follows strict Test-Driven Development (TDD). Before implementing ANY task:

### RED-GREEN-REFACTOR Cycle

1. **🔴 RED Phase - Write Failing Tests FIRST**
   - Read the task's TDD Test Cases (TC1-TCN)
   - Create test file in `libs/beacon/tests/` directory
   - Write ALL test cases from the task BEFORE any implementation
   - Run tests — they MUST fail (import errors, missing functions, etc.)
   - If tests pass without implementation, you wrote the tests wrong!

2. **🟢 GREEN Phase - Implement Minimal Code**
   - Write ONLY enough code to make tests pass
   - Run tests after each implementation step
   - All tests must pass before marking task complete

3. **🔵 REFACTOR Phase - Improve Code Quality**
   - Clean up implementation
   - Remove duplication
   - Improve naming
   - Tests must still pass after refactoring

### Task Completion Criteria

**A task is NOT complete until:**
- ✅ All TDD test cases are written
- ✅ All tests pass (or are justifiably skipped with documentation)
- ✅ Implementation matches the Expected Output
- ✅ Test results verified

### Running Tests

```bash
# From repo root
uv sync --group dev
pytest -v --tb=short
```

**See Also:** `AGENTS.md` → Unit Testing Workflow

---

## 1. Historical Hashes Registry

**Goal**: Ship a lookup table of all known pristine template hashes inside the CLI package so legacy warehouses can be classified without a checksum file.
**Input**: Current template files under `libs/beacon/src/beacon/data/templates/`
**Output**: `historical_hashes.py` importable module; existing regression test extended to guard against future drift
**Validation**: `from beacon.data.historical_hashes import KNOWN_TEMPLATE_HASHES` succeeds; `pytest libs/beacon/tests/test_template_commands.py` passes

- [x] 1.1 Create `libs/beacon/src/beacon/data/historical_hashes.py` with `KNOWN_TEMPLATE_HASHES: dict[str, list[str]]` populated with SHA256 hashes of all current templates
  - **Input**: `from beacon.data.historical_hashes import KNOWN_TEMPLATE_HASHES`
  - **Expected Output**: Non-empty dict with one key per template file (e.g., `"docs/architecture.md"`)
  - **Validation**: Module importable; every key in dict corresponds to a real template file
  - **TDD Test Cases (write these first):**
    - TC1: Module imports without error → `KNOWN_TEMPLATE_HASHES` is a dict
    - TC2: Every key in registry matches a file that exists under `data/templates/` → no phantom entries
    - TC3: Every value is a non-empty list of 64-char hex strings → valid SHA256 format
    - TC4: All current template files have at least one entry in the registry → no missing files

- [x] 1.2 Add cross-platform path normalisation helper (forward-slash canonicalisation) to the registry module
  - **TDD Test Cases (write these first):**
    - TC1: `normalise_path("docs\\architecture.md")` → `"docs/architecture.md"` on any platform
    - TC2: `normalise_path("docs/architecture.md")` → `"docs/architecture.md"` unchanged
    - TC3: Lookup via Windows-style path matches same entry as forward-slash path

- [x] 1.3 Add test: assert every current template file's hash is present in `KNOWN_TEMPLATE_HASHES` (CI regression guard)
  - **Input**: `pytest libs/beacon/tests/test_template_commands.py -v`
  - **Expected Output**: All assertions pass; descriptive failure message if a template file hash is missing
  - **Validation**: Test fails when a template file is changed but registry is not updated

## 2. Checksum Tracking on Init

**Goal**: Ensure every fresh `abc warehouse init` writes a `.beacon/template-checksums.json` so future upgrades have a baseline.
**Input**: `initializer.py` with existing template-write logic
**Output**: `.beacon/template-checksums.json` written atomically after all template files; unit tests covering creation and atomicity
**Validation**: `abc warehouse init /tmp/test-cs && cat /tmp/test-cs/.beacon/template-checksums.json` shows valid JSON with all template keys

- [x] 2.1 Add `_compute_sha256(content: str) -> str` utility (to `initializer.py` or a new `checksums.py` module)
  - **TDD Test Cases (write these first):**
    - TC1: Known string → correct SHA256 hex digest (verify against `hashlib` reference)
    - TC2: Empty string → SHA256 of empty string (`e3b0c44...`)
    - TC3: Unicode content → stable digest (UTF-8 encoded)

- [x] 2.2 After all template files are written in `abc warehouse init`, compute SHA256 of each and write `.beacon/template-checksums.json`

- [x] 2.3 Ensure `.beacon/template-checksums.json` is NOT written if init fails mid-way (build dict first, then write once)
  - **TDD Test Cases (write these first):**
    - TC1: Successful init → checksum file exists with correct content
    - TC2: Simulated failure mid-write → checksum file does NOT exist (no partial state)

- [x] 2.4 Verify `.beacon/` is absent from generated `.gitignore` patterns

- [x] 2.5 Add `.beacon/template-checksums.json` example to `examples/sample-warehouse/`

- [x] 2.6 Add unit tests for checksum file creation on init (file exists, correct keys, correct SHA256 values)
  - **Input**: `pytest libs/beacon/tests/test_initializer.py -v`
  - **Expected Output**: All assertions pass; checksum file keys match template file set; SHA256 values are valid
  - **TDD Test Cases (write these first):**
    - TC1: Init completes → `.beacon/template-checksums.json` exists
    - TC2: Keys in checksum file match exactly the set of template-generated files
    - TC3: SHA256 values in file match re-computed hashes of the written files
    - TC4: `beacon_version` field matches current CLI version
    - TC5: `--no-git` flag has no effect on checksum file creation

## 3. Upgrade Command — Core Logic

**Goal**: Implement the `WarehouseUpgrader` class with full classification and upgrade loop.
**Input**: A warehouse directory (with or without `.beacon/template-checksums.json`)
**Output**: `upgrader.py` with all classification states and action logic; unit tests covering all paths
**Validation**: `pytest libs/beacon/tests/test_upgrader.py -v` — all tests pass

- [x] 3.1 Create `libs/beacon/src/beacon/upgrader.py` with a `WarehouseUpgrader` class encapsulating all upgrade logic

- [x] 3.2 Implement `classify_file(path, warehouse_root, checksums_path) -> Literal["unmodified", "user-modified", "legacy-unmodified", "legacy-unknown"]` method
  - **TDD Test Cases (write these first):**
    - TC1: On-disk hash == stored checksum → `"unmodified"`
    - TC2: On-disk hash != stored checksum → `"user-modified"`
    - TC3: No checksum file; on-disk hash in `KNOWN_TEMPLATE_HASHES` → `"legacy-unmodified"`
    - TC4: No checksum file; on-disk hash not in registry → `"legacy-unknown"`
    - TC5: File doesn't exist on disk → raises `FileNotFoundError`
    - TC6: Checksum file exists but key missing for this file → treated as `"user-modified"`

- [x] 3.3 Implement upgrade loop: iterate all tracked template files, classify each, apply the correct action
  - **TDD Test Cases (write these first):**
    - TC1: Unmodified file → overwritten with new template; success message printed
    - TC2: User-modified file (default mode) → `.new` sidecar written; original untouched; warning printed
    - TC3: Legacy-unmodified → overwritten; `(legacy warehouse)` note in message
    - TC4: Legacy-unknown → `.new` sidecar written; warning printed

- [x] 3.4 Implement `.new` sidecar logic: skip write if `<path>.new` already exists, print warning
  - **TDD Test Cases (write these first):**
    - TC1: No existing `.new` file → sidecar written with new template content
    - TC2: `.new` file already exists → sidecar NOT overwritten; warning printed

- [x] 3.5 Implement `--dry-run`: collect and print planned actions, write nothing
  - **TDD Test Cases (write these first):**
    - TC1: Dry run on unmodified file → prints `[would upgrade]`; file unchanged
    - TC2: Dry run on user-modified file → prints `[would write .new sidecar]`; no `.new` created
    - TC3: Checksum file NOT updated after dry run

- [x] 3.6 Implement `--force`: overwrite all files regardless of classification, no `.new` sidecars
  - **TDD Test Cases (write these first):**
    - TC1: Force on user-modified file → file overwritten; no `.new` sidecar created
    - TC2: Force on unmodified file → file overwritten (same behaviour as default)

- [x] 3.7 Implement `--interactive` / `-i`: print coloured unified diff, prompt before overwriting
  - **TDD Test Cases (write these first):**
    - TC1: User confirms → file overwritten
    - TC2: User declines → `.new` sidecar written; original untouched
    - TC3: Diff output contains red lines for removed, green for added

- [x] 3.8 Refresh `.beacon/template-checksums.json` at the end of every successful (non-dry-run) upgrade

## 4. CLI Registration

**Goal**: Expose `abc warehouse template-upgrade` as a properly wired Click subcommand.
**Input**: Existing `cli.py` with `warehouse` group
**Output**: Command visible in `abc warehouse --help`; all flags accepted and passed to `WarehouseUpgrader`
**Validation**: `abc warehouse template-upgrade --help` shows all flags; `abc warehouse --help` lists `template-upgrade`

- [x] 4.1 Register `template-upgrade` as a subcommand of `abc warehouse` in `cli.py`
- [x] 4.2 Wire `--dry-run`, `--force`, and `--interactive` / `-i` Click options
- [x] 4.3 Print per-file status lines and final summary (`X upgraded, Y skipped`)
- [x] 4.4 Verify `abc warehouse --help` lists `template-upgrade`

## 5. Unit Tests

**Goal**: Achieve comprehensive unit test coverage for all new modules; all tests must pass in CI.
**Input**: `upgrader.py`, `historical_hashes.py`, and updated `initializer.py`
**Output**: Full test suite passing; `pytest` exit code 0
**Validation**: `pytest -v --tb=short` — zero failures, zero errors

- [x] 5.1 Test `classify_file`: all four states (unmodified, user-modified, legacy-unmodified, legacy-unknown)
- [x] 5.2 Test default upgrade: unmodified files overwritten, user-modified files get `.new` sidecar, original untouched
- [x] 5.3 Test `.new` sidecar already exists: second run skips sidecar write
- [x] 5.4 Test `--force`: overwrites user-modified files, no `.new` sidecars written
- [x] 5.5 Test `--dry-run`: no files written, checksum file not updated
- [x] 5.6 Test checksum file is refreshed after successful upgrade
- [x] 5.7 Test legacy warehouse (no checksum file): historical hash match → upgraded; unknown hash → `.new` sidecar

## 6. Integration / Happy Path

**Goal**: Confirm the full end-to-end flow works correctly with the real CLI binary.
**Input**: Live `.venv` with installed package (`uv sync --group dev`)
**Output**: All manual scenarios produce the expected on-disk state
**Validation**: Each step below passes; no unexpected file modifications

- [x] 6.1 Run `abc warehouse init /tmp/test-upgrade-warehouse` and verify `.beacon/template-checksums.json` is created
  - **Input**: `abc warehouse init /tmp/test-upgrade-warehouse --no-git && cat /tmp/test-upgrade-warehouse/.beacon/template-checksums.json`
  - **Expected Output**: Valid JSON with `beacon_version` and `files` dict

- [x] 6.2 Modify one templated file; run `abc warehouse template-upgrade`; verify unmodified files upgraded, modified file gets `.new` sidecar
  - **Input**: Edit `docs/architecture.md` → run `abc warehouse template-upgrade /tmp/test-upgrade-warehouse`
  - **Expected Output**: Unmodified files show `✓ Upgraded`; `docs/architecture.md` unchanged; `docs/architecture.md.new` created with new content

- [x] 6.3 Run `abc warehouse template-upgrade --dry-run` and verify nothing is written
  - **Input**: `abc warehouse template-upgrade /tmp/test-upgrade-warehouse --dry-run`
  - **Expected Output**: `[would upgrade]` / `[would write .new sidecar]` lines printed; no files changed on disk

- [x] 6.4 Run `abc warehouse template-upgrade --force` and verify all files overwritten
  - **Input**: `abc warehouse template-upgrade /tmp/test-upgrade-warehouse --force`
  - **Expected Output**: All files show `✓ Force-upgraded`; `.new` sidecar NOT written

- [x] 6.5 Delete `.beacon/template-checksums.json` and run upgrade to verify legacy bootstrapping path works
  - **Input**: `rm /tmp/test-upgrade-warehouse/.beacon/template-checksums.json && abc warehouse template-upgrade /tmp/test-upgrade-warehouse`
  - **Expected Output**: Pristine files show `✓ Upgraded (legacy warehouse)`; user-modified file gets `.new` sidecar
