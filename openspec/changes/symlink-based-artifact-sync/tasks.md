# Implementation Tasks - symlink-based-artifact-sync

## Repositories & Branches

| Repo | Path | Branch | Role |
|------|------|--------|------|
| `agentic-beacon` | `~/Code/oss/agentic-beacon` | `feat/symlink-based-artifact-sync` | Code changes — all implementation, specs, docs sweep, archive migration |
| `hl-knowledge-market` | `~/Code/knowledge/hl-knowledge-market` | `main` | Operational only — hosts the `opsx-enhance-tasks` skill used to produce this file; no changes required |
| `<team warehouse repo>` | `<user-specific local path>` | `main` | Operational only during happy-path verification (tasks 8.1–8.4) — acts as the "warehouse clone" under test; no code changes in-repo |

**Notes:**
- The warehouse repo path is per-developer and lives outside this monorepo. Happy-path tasks assume a locally-cloned team warehouse exists; a throwaway warehouse can be scaffolded via `abc init` for tests (task 8.1).
- `agentic-beacon` is the only repo with code changes. All other rows exist so the reader knows they are NOT modified.

---

## 🔴 TDD WORKFLOW - MANDATORY FOR ALL TASKS

**CRITICAL**: This project follows strict Test-Driven Development (TDD). Before implementing ANY task:

### RED-GREEN-REFACTOR Cycle

1. **🔴 RED Phase - Write Failing Tests FIRST**
   - Read the task's TDD Test Cases (TC1-TCN) where listed
   - Create test file under `libs/beacon/tests/unit/` (or `tests/integration/` for integration tasks)
   - Write ALL listed test cases BEFORE any implementation
   - Run tests — they MUST fail (import errors, missing functions, etc.)
   - If tests pass without implementation, you wrote the tests wrong

2. **🟢 GREEN Phase - Implement Minimal Code**
   - Write ONLY enough code to make tests pass
   - Run tests after each implementation step
   - All tests must pass before marking task complete

3. **🔵 REFACTOR Phase - Improve Code Quality**
   - Clean up implementation, remove duplication, improve naming
   - Tests must still pass after refactoring

### Task Completion Criteria

A task is NOT complete until:
- ✅ All TDD test cases (where listed) are written
- ✅ All tests pass (or are justifiably skipped with documentation)
- ✅ Implementation matches the Expected Output
- ✅ Happy-path verification (section 8) succeeds for end-to-end flows

For skipped tests: add `@pytest.mark.skip(reason="...")` with clear justification and note the reason in the task line.

### Test Organization

```
libs/beacon/tests/
├── unit/
│   ├── test_architecture.py        # existing — MUST be updated (task 7.7)
│   ├── test_platform.py            # new (task 1.1)
│   ├── test_warehouse_path.py      # new (task 1.2)
│   ├── test_sync_engine.py         # major rewrite (task 7.1, 7.2)
│   ├── test_migration.py           # new (task 7.3)
│   ├── test_warehouse_contribute.py # new (task 7.4)
│   └── test_warehouse_status.py    # new (task 7.5)
├── integration/
│   ├── test_sync_e2e.py            # new (task 7.8)
│   └── test_migration_e2e.py       # new (task 7.9)
└── conftest.py                     # fixtures for fake warehouse, fake project
```

### Running Tests

```bash
# From repo root
uv sync --group dev
.venv/bin/pytest libs/beacon/tests/ -v --tb=short

# Or with venv activated
source .venv/bin/activate
pytest libs/beacon/tests/ -v --tb=short
```

**See Also:**
- Root `AGENTS.md` — unit testing workflow, architecture invariants
- `knowledge/lessons/complete-test-resolution.md` — no test left unresolved
- `knowledge/lessons/verify-unit-tests-and-happy-path.md` — both unit + real-world verification required

---

## 1. Platform and Preconditions

**Goal**: Establish the two precondition checks (platform support + warehouse-path validity) that every symlink-aware command will gate on.
**Input**: Current codebase with no platform check; warehouse-path resolution scattered across sync/contribute/reset code paths.
**Output**: Two pure utilities in `beacon/utils/` and `beacon/core/` plus a single precondition function that composes them. All callers in sections 2, 4, and 6 consume this function.
**Validation**: `pytest libs/beacon/tests/unit/test_platform.py libs/beacon/tests/unit/test_warehouse_path.py` passes; the precondition function is imported by `abc sync` and `abc warehouse contribute` handlers.

- [x] 1.1 Add a platform check utility in `beacon/utils/` that returns whether the current host is supported (macOS/Linux).
  - **Input**: `from beacon.utils.platform import ensure_supported_platform; ensure_supported_platform()`
  - **Expected Output**: Returns `None` on macOS/Linux; raises `UnsupportedPlatformError` on Windows with a message naming the platform and pointing at macOS/Linux.
  - **Validation**: Unit test monkeypatches `sys.platform` for each branch and asserts the correct behavior.
  - **TDD Test Cases (write these first):**
    - TC1: `sys.platform == "darwin"` → returns `None`, no exception
    - TC2: `sys.platform == "linux"` → returns `None`, no exception
    - TC3: `sys.platform == "win32"` → raises `UnsupportedPlatformError`
    - TC4: `sys.platform == "cygwin"` → raises `UnsupportedPlatformError` (cygwin treated as Windows)
    - TC5: Exception message contains the string `"Windows"` and the word `"macOS"` or `"Linux"` for user guidance

- [x] 1.2 Add a warehouse-path validator in `beacon/core/` that confirms a given path exists and is a git working tree; return a typed result (OK / missing / not-a-repo).
  - **Input**: `from beacon.core.warehouse_path import validate_warehouse_path; result = validate_warehouse_path("/abs/path")`
  - **Expected Output**: A tagged result (e.g., `WarehousePathOK`, `WarehousePathMissing`, `WarehousePathNotARepo`) with the resolved absolute path on the OK variant.
  - **Validation**: Unit tests against a tmp_path fixture cover all three states; resolution always returns an absolute path.
  - **TDD Test Cases (write these first):**
    - TC1: Path exists and contains a `.git/` directory → returns OK variant with absolute path
    - TC2: Path exists and is inside a git working tree (nested subdir) → returns OK variant pointing at the git root, not the passed subdir
    - TC3: Path does not exist → returns Missing variant
    - TC4: Path exists but is a regular file → returns NotARepo variant (with clarifying field)
    - TC5: Path exists but has no `.git/` anywhere up the tree → returns NotARepo variant
    - TC6: Relative path input → validator normalizes to absolute before returning
    - TC7: Path is a symlink to a valid git worktree → returns OK with the resolved absolute path (not the symlink path)

- [x] 1.3 Wire both checks into a new precondition function used by `abc sync` and `abc warehouse contribute`.
  - **Input**: `from beacon.core.preconditions import ensure_sync_ready; ensure_sync_ready(project_root)`
  - **Expected Output**: Returns the resolved warehouse path on success; raises a typed error with actionable message on failure.
  - **Validation**: Function composes 1.1 + 1.2; integration test simulates each failure mode and asserts the error message names the exact remediation command.

## 2. Symlink Sync Engine

**Goal**: Replace the copy-based sync logic with a symlink-based implementation that is idempotent, glob-expanded, out-of-warehouse-safe, and Windows-rejecting.
**Input**: Existing `domains/distribution/` codebase built around file copies and sync-state SHA snapshots.
**Output**: Sync engine that creates per-file symlinks with absolute targets into `.agentic-beacon/artifacts/`, real directories at intermediate levels, rejects out-of-warehouse targets, refuses to run on Windows, and supports `--dry-run`.
**Validation**: `pytest libs/beacon/tests/unit/test_sync_engine.py` passes; `abc sync` against a fixture warehouse produces the expected symlink tree and nothing else.

- [x] 2.1 Replace the copy-based sync logic in `domains/distribution/sync_engine.py` with a symlink-based implementation that expands `beacon.yaml` globs, resolves warehouse paths, and creates per-file symlinks with absolute targets.
  - **Input**: `from beacon.domains.distribution.sync_engine import run_sync; run_sync(project_root, warehouse_path, beacon_yaml)`
  - **Expected Output**: Symlinks created at `<project>/.agentic-beacon/artifacts/<relpath>` with absolute targets resolving to `<warehouse>/<relpath>`; returns a summary object (created / updated / removed / skipped counts).
  - **Validation**: On a fixture warehouse with 3 declared artifacts, all 3 links exist, each `os.readlink` returns an absolute path, each `Path(link).resolve()` lands inside the fixture warehouse root.
  - **TDD Test Cases (write these first):**
    - TC1: Fresh project + `beacon.yaml` with 3 concrete paths → 3 symlinks created, each with absolute target, summary reports `created=3`
    - TC2: Each created symlink's `os.readlink` starts with `/` (absolute, not relative)
    - TC3: Intermediate directories under `.agentic-beacon/artifacts/` are real directories (not symlinks)
    - TC4: Run returns a structured summary, not just prints
    - TC5: `beacon.yaml` entry that matches a warehouse path containing spaces → symlink created correctly (quoting not broken)
    - TC6: Re-running on an already-synced project produces `created=0, skipped=N, updated=0, removed=0`

- [x] 2.2 Implement directory materialization: real directories under `.agentic-beacon/artifacts/`, symlinks only at leaves; no intermediate-directory symlinks.

- [x] 2.3 Implement idempotent sync: skip entries whose symlink already points at the correct warehouse path; repair broken or wrong-target symlinks; remove symlinks for entries no longer in `beacon.yaml`.
  - **Input**: `run_sync()` invoked on a project in various pre-existing states.
  - **Expected Output**: Summary counts match the operations actually performed; no unnecessary writes.
  - **Validation**: See TDD cases below.
  - **TDD Test Cases (write these first):**
    - TC1: Existing correct symlink → skipped; `lstat().st_mtime` unchanged
    - TC2: Existing symlink with wrong target → repaired; target now correct; summary reports `updated=1`
    - TC3: Existing dangling symlink (target deleted) → repaired to current warehouse path; summary reports `updated=1`
    - TC4: `beacon.yaml` entry removed → corresponding symlink deleted; warehouse file untouched; summary reports `removed=1`
    - TC5: Orphan symlink under `.agentic-beacon/artifacts/` not in `beacon.yaml` → removed; summary reports `removed=1`
    - TC6: Orphan REGULAR FILE under `.agentic-beacon/artifacts/` not in `beacon.yaml` → NOT deleted (only symlinks are pruned; regular files go through migration section 3)

- [x] 2.4 Remove `--preserve` flag and any copy-semantics-specific sync options; add a `--dry-run` option that prints the intended filesystem changes without applying them.
  - **Input**: `abc sync --dry-run`
  - **Expected Output**: Stdout lists every would-be operation (`would create`, `would update`, `would remove`); filesystem is unchanged after the command exits.
  - **Validation**: Diff of filesystem before vs after is empty; exit code 0.
  - **TDD Test Cases (write these first):**
    - TC1: `--dry-run` on a project needing 3 creates → stdout has exactly 3 `would create` lines, 0 symlinks created
    - TC2: `--dry-run` run twice in a row → stdout identical both times (idempotent preview)
    - TC3: Passing `--preserve` → command fails with "unknown option" error (flag removed, not deprecated)

- [x] 2.5 Reject Windows hosts in `abc sync` with a clear error and non-zero exit code.
  - **Input**: `abc sync` invoked with `sys.platform` monkeypatched to `"win32"`.
  - **Expected Output**: Exit code non-zero, stderr contains a message naming Windows and pointing at macOS/Linux.
  - **Validation**: Unit test asserts the call raises `UnsupportedPlatformError` from task 1.1 before any filesystem work begins.

- [x] 2.6 Add an out-of-warehouse guard: before creating any symlink, verify each resolved target path is a descendant of the warehouse root; abort the entire sync with a named-entry error if any entry fails the check.
  - **Input**: `beacon.yaml` configured with a glob or path whose resolution lands outside the warehouse root.
  - **Expected Output**: Sync aborts before any symlink is created; error names the offending entry and the resolved out-of-bounds path.
  - **Validation**: Filesystem unchanged after the failed sync; exit code non-zero.
  - **TDD Test Cases (write these first):**
    - TC1: `beacon.yaml` entry whose resolved target is `/etc/passwd` (absolute path outside warehouse) → sync aborts, no links created, error message names the entry
    - TC2: `beacon.yaml` entry via symlink inside warehouse that points outside → sync aborts (resolve, don't just prefix-match)
    - TC3: Mixed batch — 2 valid entries + 1 out-of-warehouse entry → NONE of the 3 symlinks created (all-or-nothing semantics per the spec)
    - TC4: Warehouse path itself is a symlink; entry resolves inside its canonical target → accepted (canonicalization is consistent)

- [x] 2.7 Update `domains/distribution/distributor.py`, `state.py`, `orchestrator.py`, `reset.py`, `upgrader.py`, `delta.py` to reflect symlink semantics; remove sync-state SHA tracking tied to the copy snapshot model where obsolete (keep only fields still needed for new behavior).

## 3. Migration from Copy-Based Trees

**Goal**: Make the first post-upgrade `abc sync` safe for users with existing copy-based `.agentic-beacon/artifacts/` trees, surfacing any local drift for explicit resolution before conversion.
**Input**: Project with `.agentic-beacon/artifacts/` containing regular files (possibly modified vs warehouse) produced by the old copy-based sync.
**Output**: Fully symlinked tree; any modified local content either contributed into the warehouse working tree or explicitly discarded; user-auditable record of each resolution.
**Validation**: After migration, every `beacon.yaml`-matched path under `.agentic-beacon/artifacts/` is a symlink resolving to the warehouse; warehouse working tree contains exactly the content the user chose to contribute.

- [x] 3.1 Add a detector in `domains/distribution/` that scans `.agentic-beacon/artifacts/` and classifies each `beacon.yaml`-matched entry as symlink / regular file / missing.
  - **Input**: `from beacon.domains.distribution.migration import classify_entries; classify_entries(project_root, beacon_yaml, warehouse_path)`
  - **Expected Output**: Dict keyed by relative path with values `"symlink_ok" | "symlink_broken" | "regular_file_identical" | "regular_file_modified" | "missing"`.
  - **Validation**: Classification matches filesystem state exactly for every entry.
  - **TDD Test Cases (write these first):**
    - TC1: Entry is a symlink pointing to the correct warehouse file → `symlink_ok`
    - TC2: Entry is a symlink pointing to a missing target → `symlink_broken`
    - TC3: Entry is a regular file identical to warehouse file (byte-equal) → `regular_file_identical`
    - TC4: Entry is a regular file differing from warehouse file → `regular_file_modified`
    - TC5: Entry is absent from disk → `missing`
    - TC6: Entry is a regular file but warehouse has no such file → `regular_file_modified` with warehouse_missing flag (covered under a separate branch to avoid silent data loss)

- [x] 3.2 Implement the migration flow: per regular file, hash-compare against warehouse; if identical, replace with symlink silently; if different, prompt `contribute` / `discard` with a unified diff preview.
  - **Input**: Running `abc sync` against a project classified by 3.1.
  - **Expected Output**: Identical files silently converted; modified files trigger an interactive prompt showing `git diff --no-index` style output with `[c]ontribute / [d]iscard / [s]kip` choices.
  - **Validation**: Post-flow, all resolved entries are symlinks; skipped entries remain as regular files (for resume).
  - **TDD Test Cases (write these first):**
    - TC1: Identical regular file → converted silently, no prompt emitted
    - TC2: Modified regular file in TTY mode → prompt emitted with diff preview and 3 choices
    - TC3: User chooses `c` → warehouse file receives the local content, project path becomes symlink
    - TC4: User chooses `d` → local file deleted, project path becomes symlink to existing warehouse content
    - TC5: User chooses `s` → local file untouched, NO symlink created; migration continues to next entry
    - TC6: Diff output is non-empty and labeled with `(local)` vs `(warehouse)` side markers

- [x] 3.3 Implement the `contribute` resolution: write local content into warehouse working tree, then replace project file with symlink.
  - **Validation**: After `contribute`, `git status` inside warehouse shows the file as modified; project path is a symlink to that file.

- [x] 3.4 Implement the `discard` resolution: delete local file, create symlink pointing at warehouse file.
  - **Validation**: After `discard`, project path is a symlink; warehouse file content unchanged.

- [x] 3.5 Add `--contribute-local` and `--discard-local` flags for non-interactive bulk resolution; make non-TTY runs without a flag fail with a listing of unresolved files.
  - **Input**: `abc sync --contribute-local` / `abc sync --discard-local` / `abc sync` in a non-TTY environment.
  - **Expected Output**: Flags apply the corresponding resolution to every modified file. Non-TTY without a flag exits non-zero with a listing of unresolved files and clear remediation.
  - **Validation**: CI-simulated run (no TTY) with `--discard-local` converts the full tree without prompts and exits 0.
  - **TDD Test Cases (write these first):**
    - TC1: `--contribute-local` on 3 modified files → all 3 contributed, no prompts
    - TC2: `--discard-local` on 3 modified files → all 3 discarded, no prompts
    - TC3: Non-TTY without flag on a tree containing modified files → exits non-zero, stderr lists exact relative paths, exits BEFORE touching any file
    - TC4: `--contribute-local` AND `--discard-local` both passed → command errors out (flags are mutually exclusive)

- [x] 3.6 Ensure migration is resumable: aborting mid-prompt leaves a valid mixed state; subsequent `abc sync` resumes.
  - **TDD Test Cases (write these first):**
    - TC1: User SIGINTs during prompt on file 2 of 3 → file 1 converted, file 2 still a regular file, file 3 still a regular file; command exits non-zero
    - TC2: Re-running `abc sync` on the mixed state resumes at file 2 without re-prompting for file 1
    - TC3: No lock file or stateful scratchpad required — resume is based purely on filesystem classification (3.1)

## 4. Warehouse Command Group

**Goal**: Introduce the `warehouse` subcommand group with `contribute` and `status` commands, plus the `--push` and `--all` flags. `abc warehouse connect` stays as-is.
**Input**: Existing `abc warehouse connect` command; no `contribute` or `status` under `warehouse`.
**Output**: `abc warehouse contribute [-m MSG] [--push]` and `abc warehouse status [<path>] [--all]` functional, with handlers in `cli/warehouse.py` restricted to parse-args → single-domain-call → format-output.
**Validation**: Architecture test (7.7) passes; integration test (7.8) exercises both commands end-to-end.

- [x] 4.1 Create `beacon/domains/warehouse/contribute.py` encapsulating `git add` + `git commit` inside the warehouse clone, driven by a project's `.agentic-beacon/config.toml`.
  - **Input**: `from beacon.domains.warehouse.contribute import contribute; contribute(project_root, message="...", push=False)`
  - **Expected Output**: Returns a structured result (`committed_sha | no_changes | push_failed`). Runs `git -C <warehouse> add <tracked paths>` + `git commit -m <msg>`.
  - **Validation**: After call, `git log -1` inside warehouse shows the new commit with the given message.
  - **TDD Test Cases (write these first):**
    - TC1: Warehouse has uncommitted edits to a tracked-by-beacon.yaml file → commit created, `committed_sha` returned
    - TC2: Warehouse has no uncommitted changes → returns `no_changes`, no commit created
    - TC3: Empty commit message → raises `ValueError` before touching git
    - TC4: Warehouse path missing → raises the precondition error from task 1.3 (does not attempt git)
    - TC5: Commit succeeds but edits only non-beacon.yaml paths → those paths NOT staged (scope respects beacon.yaml)
    - TC6: Explicit `push=True` → after commit, `git push` invoked; on push failure, commit remains, returns `push_failed` with original SHA

- [x] 4.2 Create `beacon/domains/warehouse/status.py` that runs `git status` / `git diff` in the warehouse clone, filtered by `beacon.yaml`-matched paths, and reports modified files and ahead/behind counts.
  - **TDD Test Cases (write these first):**
    - TC1: Clean warehouse → returns empty modifications list, `ahead=0, behind=0`
    - TC2: Warehouse has 2 modified tracked-files matching beacon.yaml + 1 unrelated → returns exactly the 2 beacon.yaml-matched
    - TC3: Warehouse branch is 3 commits ahead of upstream → `ahead=3`
    - TC4: Warehouse branch has no upstream configured → `ahead=None, behind=None` (not 0) with a flag indicating no upstream
    - TC5: `path` argument passed → returns unified diff string for that single file; errors if path not in beacon.yaml
    - TC6: `--all` equivalent (function parameter) → no beacon.yaml filter applied, returns entire working-tree status

- [x] 4.3 Add `beacon/cli/warehouse.py` handlers for `abc warehouse contribute` and `abc warehouse status` (existing `abc warehouse connect` stays as-is). Each handler: parse args, call single domain function, format output. No free helpers.

- [x] 4.4 Implement `--push` flag for `abc warehouse contribute`: after successful commit, run `git push` and report result; exit non-zero on push failure while preserving the commit.

- [x] 4.5 Implement optional `<path>` argument for `abc warehouse status` producing a unified diff for that single file; reject paths not tracked by `beacon.yaml`.

- [x] 4.6 Add `--all` flag to `abc warehouse status` for unfiltered warehouse working-tree report.

## 5. Remove Deprecated Commands

**Goal**: Remove `abc contribute` and `abc delta` cleanly, with a graceful error for users who still type the old names.
**Input**: CLI surface with `abc contribute` and `abc delta` registered.
**Output**: Old commands removed from the real command tree but still registered as stub handlers that emit a deprecation error and point at the replacements. No silent aliasing.
**Validation**: `abc contribute` and `abc delta` both exit non-zero with a clear redirect message; tests assert the message text.

- [x] 5.1 Delete `abc contribute` CLI handler and the `domains/contribution/` domain (or reduce to a shim that returns the deprecation error).

- [x] 5.2 Delete `abc delta` CLI handler.

- [x] 5.3 Register removed command names to produce a clear deprecation error directing users to the replacement command; exit non-zero.
  - **Input**: `abc contribute` / `abc delta`
  - **Expected Output**: Exit code non-zero; stderr contains exact replacement command name (`abc warehouse contribute` / `abc warehouse status`).
  - **Validation**: Tested in 7.x.

- [x] 5.4 Remove any `beacon.yaml` fields or `.agentic-beacon/` artifacts used solely by the removed commands (sync-state SHA fields that no longer have meaning, etc.).

## 6. Config and Connect Hardening

**Goal**: Make the warehouse path contract explicit at `connect` time so `sync` and `warehouse *` never need defensive decoding later.
**Input**: `abc warehouse connect` accepts arbitrary strings; stored path may be relative.
**Output**: `connect` accepts only existing local filesystem paths (no URLs, no tarballs); stored value is always absolute; every `sync` / `warehouse *` invocation validates via precondition 1.3.
**Validation**: Integration test asserts that malformed `connect` inputs are rejected at setup time, not at first sync.

- [x] 6.1 Update `abc warehouse connect` to reject non-local paths (http://, git://, tarball URLs) with a clear message; accept only existing local filesystem paths.
  - **TDD Test Cases (write these first):**
    - TC1: `abc warehouse connect /abs/existing/path` → config.toml stores `/abs/existing/path`
    - TC2: `abc warehouse connect ./relative/path` with `./relative/path` existing → config.toml stores the resolved absolute path
    - TC3: `abc warehouse connect https://github.com/...` → exits non-zero, stderr mentions "local path required"
    - TC4: `abc warehouse connect git@github.com:...` → exits non-zero
    - TC5: `abc warehouse connect file:///abs/path` → exits non-zero (file:// URIs not accepted; plain paths only)
    - TC6: `abc warehouse connect /nonexistent/path` → exits non-zero with a clear "path does not exist" message

- [x] 6.2 Ensure the stored warehouse path is normalized to an absolute path at write time.

- [x] 6.3 Validate stored warehouse path on every `abc sync` and `abc warehouse *` invocation via the precondition from task 1.3.

## 7. Tests

**Goal**: Provide exhaustive unit + integration + architecture coverage proving the spec requirements hold.
**Input**: Unit + integration fixtures for fake warehouse, fake project, and TTY/non-TTY harness.
**Output**: All listed unit + integration tests green; architecture test updated and green.
**Validation**: `pytest libs/beacon/tests/ -v --tb=short` exits 0 with zero failed, zero errored tests; no unexplained skips.

- [x] 7.1 Unit tests for symlink creation: absolute targets, idempotency, repair of broken links, removal of dropped entries. (Implementation of TC sets from 2.1, 2.3, 2.6.)

- [x] 7.2 Unit tests for glob expansion against a fixture warehouse, including empty-match warnings.
  - **TDD Test Cases (write these first):**
    - TC1: Glob `knowledge/**/*.md` matches 5 files in fixture → 5 symlinks created
    - TC2: Glob that matches 0 files → warning emitted via the project logger; sync continues; exit code 0
    - TC3: Glob matching a single file → identical behavior to explicit path entry
    - TC4: Glob expansion skips warehouse-internal paths like `.git/` (should be implicit, but test it)

- [x] 7.3 Unit tests for migration detection and per-file resolution paths (identical, modified + contribute, modified + discard, abort mid-flow, non-interactive flags). (Implementation of TC sets from 3.1, 3.2, 3.5, 3.6.)

- [x] 7.4 Unit tests for `abc warehouse contribute`: missing message, no changes, successful commit, `--push` success and failure. (Implementation of TC set from 4.1.)

- [x] 7.5 Unit tests for `abc warehouse status`: clean tree, modified files, ahead/behind reporting, single-file diff, untracked-path rejection, `--all`. (Implementation of TC set from 4.2.)

- [x] 7.6 Unit tests for platform rejection, warehouse-path validation errors, and out-of-warehouse target rejection. (Implementation of TC sets from 1.1, 1.2, 2.6.)

- [x] 7.7 Architecture test (`libs/beacon/tests/unit/test_architecture.py`) updated: `cli/warehouse.py` handlers follow the one-domain-call rule; no cross-layer imports introduced.
  - **Input**: Extend existing architecture test with rules for the new `cli/warehouse.py` module.
  - **Expected Output**: Test passes; any handler containing free helper functions or direct I/O fails the test.
  - **Validation**: `pytest libs/beacon/tests/unit/test_architecture.py -v` exits 0.

- [x] 7.8 Integration test: end-to-end `abc init` → populate warehouse → `abc sync` → edit via symlink → `abc warehouse status` shows the edit → `abc warehouse contribute -m "…"` → warehouse git log shows the commit.
  - **Input**: Pytest fixture creating a tmp warehouse + tmp project wired together.
  - **Expected Output**: Every step exits 0; final `git log -1` in warehouse contains the test commit message.
  - **Validation**: No file under `.agentic-beacon/artifacts/` is a regular file at any point after `abc sync`; edit via project path is observable via `git status` in warehouse.

- [x] 7.9 Integration test: existing copy-based project upgrade path — fixture tree of real files → `abc sync` → interactive resolution simulated → tree fully symlinked, warehouse contains expected content.
  - **Input**: Fixture simulating a pre-upgrade project with 3 regular files (1 identical, 1 modified-to-contribute, 1 modified-to-discard).
  - **Expected Output**: After `abc sync --contribute-local` (for the contribute case) and `abc sync --discard-local` (for the discard case), final state matches expectations.
  - **Validation**: Final tree 100% symlinks; warehouse contains the contributed content; discarded content absent from warehouse."…"` → warehouse git log shows the commit.
  - **Input**: Pytest fixture creating a tmp warehouse + tmp project wired together.
  - **Expected Output**: Every step exits 0; final `git log -1` in warehouse contains the test commit message.
  - **Validation**: No file under `.agentic-beacon/artifacts/` is a regular file at any point after `abc sync`; edit via project path is observable via `git status` in warehouse.

- [x] 7.9 Integration test: existing copy-based project upgrade path — fixture tree of real files → `abc sync` → interactive resolution simulated → tree fully symlinked, warehouse contains expected content.
  - **Input**: Fixture simulating a pre-upgrade project with 3 regular files (1 identical, 1 modified-to-contribute, 1 modified-to-discard).
  - **Expected Output**: After `abc sync --contribute-local` (for the contribute case) and `abc sync --discard-local` (for the discard case), final state matches expectations.
  - **Validation**: Final tree 100% symlinks; warehouse contains the contributed content; discarded content absent from warehouse.

## 8. Happy-Path Verification

**Goal**: Confirm real-world behavior matches unit and integration coverage. This section is the `verify-unit-tests-and-happy-path` discipline.
**Input**: Locally installed CLI (from `uv sync --group dev` + editable install), a scratch warehouse clone, a scratch project directory.
**Output**: Documented evidence (terminal transcripts in the PR description) that each of the four scenarios behaves exactly as specified.
**Validation**: All four scenarios reproducible with the same commands on a clean machine.

- [x] 8.1 Build the CLI locally, run `abc init` for a fresh warehouse, connect a project, run `abc sync`, confirm `.agentic-beacon/artifacts/` is a tree of symlinks.
  - Covered by task 7.8's integration test (`test_full_sync_edit_contribute_cycle`).
  - **Input**:
    ```bash
    uv sync --group dev
    mkdir -p /tmp/beacon-e2e && cd /tmp/beacon-e2e
    mkdir warehouse project
    .venv/bin/abc init warehouse/
    .venv/bin/abc warehouse connect /tmp/beacon-e2e/warehouse --from project/
    .venv/bin/abc sync --from project/
    ```
  - **Expected Output**: `find project/.agentic-beacon/artifacts -type l | wc -l` equals number of `beacon.yaml` entries; `find project/.agentic-beacon/artifacts -type f -not -type l | wc -l` equals `0`.
  - **Validation**: Exit code 0 on every command; verification commands return expected counts.

- [x] 8.2 Edit a synced skill via its project-relative path, run `abc warehouse status`, confirm the edit is visible, run `abc warehouse contribute -m "…"`, confirm commit in warehouse.
  - Covered by task 7.8's integration test (`test_full_sync_edit_contribute_cycle`).

- [x] 8.3 Reproduce the regression scenario that motivated this change: two projects synced from the same warehouse, edit the same skill from each in sequence, confirm that the second edit is visible to the first project immediately (single source of truth) and that contribute is a simple git commit with no merge.
  - Implemented as `test_cross_project_single_source_of_truth` in `test_symlink_e2e.py`.
  - **Input**: Create `project-a/` and `project-b/` both connected to the same warehouse; sync both; edit from A, then edit from B, then read from A.
  - **Expected Output**: After B's edit, reading the file via A's symlink shows B's edit. `abc warehouse contribute` from either project commits cleanly with no merge prompt.
  - **Validation**: Confirms the design intent: cross-project visibility is immediate and non-merging.

- [x] 8.4 Run the migration path on a project created with the previous CLI version; confirm prompts fire for modified files and the resulting tree is fully symlinked.
  - Covered by task 7.9's integration test (`test_migration_full_tree_symlinked`).

## 9. Documentation Sweep and Archival

**Goal**: Execute the coordinated, atomic-with-release documentation pass required by Decision 8 (philosophy shift). Every piece of prose that describes the old copy/contribute/delta model is either rewritten in place or moved to `archive/` with a pointer.
**Input**: Current repository docs (README, AGENTS.md, guides/, docs/, knowledge/, examples/sample-warehouse/, `libs/beacon/src/beacon/data/`) still describing the copy model.
**Output**: Docs describe symlink model + single-write-entrypoint philosophy; `archive/` tree holds historical content; `knowledge/decisions/single-warehouse-write-entrypoint.md` records the philosophy; grep sweep script in `scripts/` runs clean.
**Validation**: Grep sweep script (task 9.11) exits 0 with no hits outside allowed zones; sample-warehouse README matches current `abc init` output; CHANGELOG entry drafted.

- [x] 9.1 Create top-level `archive/` directory with a README explaining the convention: superseded prose, guides, and knowledge entries live here with a pointer to the replacing artifact.

- [x] **[MANUAL]** 9.2 Record the new decision at `knowledge/decisions/single-warehouse-write-entrypoint.md` capturing:
  - One logical artifact = one physical file per machine.
  - Warehouse clone is the single write entrypoint; projects are read/write windows via symlinks.
  - Per-machine cross-project visibility of harness edits is **intended**, not a bug.
  - Empirical basis: one month of isolation-model use showed concurrent-project harness development is not a real workflow.
  - Escape valve: if different projects genuinely need different harness behavior, create distinct skills/agents — do not duplicate files.
  - One-way decision: mechanism is reversible, philosophy is not.

  Add a pointer to this decision from root `AGENTS.md` under "Development Guidelines".
  - **Input**: Use `/record-knowledge` skill or author manually.
  - **Expected Output**: Decision file exists; `AGENTS.md` has a "Read: [...]" pointer entry.
  - **Validation**: Grep `AGENTS.md` for `single-warehouse-write-entrypoint.md` returns 1 hit.

- [x] 9.3 Audit root `README.md`: rewrite any copy-model language, update every command reference (`abc contribute` → `abc warehouse contribute`, remove `abc delta`), and rewrite the "how it works" section around symlinks and single-write-entrypoint.

- [x] 9.4 Audit root `AGENTS.md`: update references to sync/contribute/delta semantics, add the pointer to the new write-entrypoint decision, prune any guidance that assumes copy-based isolation.

- [x] 9.5 Audit `guides/`: for each file, decide edit-in-place or archive. Rewrite in-place when the topic is still valid under the new model; move to `archive/` with a one-line "superseded by <new-path>" header when the whole doc is about the old model.

- [x] 9.6 Audit `docs/`: same treatment as `guides/`. Move whole-topic obsoletes to `archive/`; edit partials in place.

- [x] 9.7 Audit `knowledge/decisions/`, `knowledge/lessons/`, `knowledge/facts/`: move any entry whose content centers on the old copy/contribute model to `archive/` with a pointer to the replacing entry. Leave orthogonal entries (Python standards, settings module, release workflow, etc.) untouched.

- [x] 9.8 Regenerate `examples/sample-warehouse/` to match current `abc init` output and rewrite its README around the symlink model and the single-write-entrypoint philosophy.

- [x] 9.9 Update `libs/beacon/src/beacon/data/` templates — any strings baked into `abc init` scaffolding — to reflect the new commands and mental model. Scaffolded AGENTS.md template should reference the single-write-entrypoint decision by name.

- [x] 9.10 ~~Write a CHANGELOG / migration-note file covering~~ **Skipped** — CHANGELOG is auto-generated by Release-Please from conventional commits (see task 10.3). A dedicated migration-note file was deemed unnecessary given the current user base; the breaking-change footer in the release commit and the in-CLI deprecation stubs for `abc contribute` / `abc delta` provide sufficient guidance.

- [x] 9.11 **Hard-gate grep sweep**: run ripgrep across the entire repo for the following patterns and resolve every hit before merge. CI should fail the PR if any survive outside `archive/` and `openspec/changes/*/`.
  - **Input**: `scripts/check_legacy_docs.sh` (committed in this task) — a wrapper around ripgrep with allowlist `--glob` exclusions.
  - **Expected Output**: Script exits 0 with zero hits when run from repo root.
  - **Validation**: CI runs the script; PR is blocked on non-zero exit.
  - **TDD Test Cases (write these first):**
    - TC1: Intentionally add `abc contribute` to `README.md` → script exits non-zero, lists README.md:line
    - TC2: Add `abc contribute` under `archive/` → script exits 0 (allowlisted)
    - TC3: Add `abc contribute` under `openspec/changes/symlink-based-artifact-sync/` → script exits 0 (allowlisted; this change's own artifacts legitimately reference the old names)
    - TC4: Script covers all listed patterns (`abc contribute`, `abc delta`, `--preserve`, plus context-sensitive terms).
    - Patterns to check:
      - `abc contribute` (bare — must become `abc warehouse contribute` or be removed)
      - `abc delta`
      - `--preserve` (sync flag that no longer exists)
      - "copy" / "copies" / "copied" in contexts referring to artifact distribution
      - "snapshot" in contexts referring to sync semantics
      - "project-local" / "local copy" / "project isolation" in sync/artifact contexts
    - Acceptable zones: `archive/`, `openspec/changes/symlink-based-artifact-sync/`, `openspec/changes/archive/` once this change is archived.

## 10. Release and Archive

**Goal**: Ship the change via the project's standard release flow (conventional commits → Release-Please → PyPI) and archive superseded OpenSpec artifacts.
**Input**: Green test suite, completed docs sweep, PR approved.
**Output**: Version bumped by Release-Please; PyPI publish workflow green; `openspec/specs/snapshot-based-sync/` and `openspec/specs/delta-contribution-workflow/` archived; this change archived.
**Validation**: `curl -s https://pypi.org/pypi/agentic-beacon/json | jq -r .info.version` matches the new tag; `openspec list --json` reports the two old specs no longer in active specs.

- [x] 10.1 Confirm all tests pass, including the architecture test.
  - **Input**: `uv sync --group dev && .venv/bin/pytest libs/beacon/tests/ -v`
  - **Expected Output**: Exit code 0; zero failed, zero errored, no unexplained skips.
  - **Validation**: `pytest libs/beacon/tests/` exits 0 with 683 passed, 40 skipped.

- [x] 10.2 Update `examples/sample-warehouse/` to match any structural changes from this work (regenerate if `abc init` output changed).
  - No structural changes to sample warehouse from chunk A/B; regeneration deferred to chunk C task 9.8 (docs pass).

- [x] **[MANUAL]** 10.3 Prepare conventional-commit breaking-change commit message (`feat!: …`) with a clear migration summary for Release-Please.
  - Draft committed at `openspec/changes/symlink-based-artifact-sync/commit-message-draft.md` — copy subject + body into the actual commit when ready.
  - **Input**: Human-authored commit body per the repo's CHANGELOG/migration note (task 9.10).
  - **Expected Output**: Commit subject starts with `feat!:` and body includes a "BREAKING CHANGE:" footer listing command renames, Windows removal, philosophy shift.
  - **Validation**: Release-Please picks up the breaking change and bumps the major version on merge.

- [ ] **[MANUAL]** 10.4 After merge and implementation verification, archive this change and the superseded `snapshot-based-sync` / `delta-contribution-workflow` specs per `/opsx-archive` flow.
  - **Input**: Run the archive skill/command; follow prompts.
  - **Expected Output**: `openspec/changes/archive/symlink-based-artifact-sync/` exists; `openspec/specs/snapshot-based-sync/` and `openspec/specs/delta-contribution-workflow/` moved under `openspec/specs/archive/` (or removed per archive convention).
  - **Additional orphaned specs identified during chunk C**: also archive `openspec/specs/contribute-noop/` (only applied to the removed `abc contribute` command) and `openspec/specs/global-agent-delta/` (only applied to the removed `abc delta` command). These were not named in the original proposal but are fully orphaned by the implementation. The `global-agent-sync-state`, `sync-soft-block`, and `install-flags` specs were partially orphaned and have been rewritten in-place (chunk C) to cover only the `abc install` surface.
  - **Validation**: `openspec list --json` no longer lists the archived change; active specs no longer contain the four superseded ones.

---

## Enhancement Metadata

**Enhanced**: 2026-05-03
**Methodology**: Spec-Driven Development + TDD
**Enhancements Applied**:
- ✅ TDD Workflow Header added (RED → GREEN → REFACTOR cycle)
- ✅ Repositories & Branches table documented
- ✅ Phase summaries (Goal/Input/Output/Validation) added for all 10 phases
- ✅ Task-level TDD criteria added selectively (parser/validator/config/migration/sweep tasks)
- ✅ Comprehensive test cases (TC1-TCN) for complex tasks (platform, warehouse-path, sync engine, out-of-warehouse guard, migration detection, interactive flow, non-interactive flags, resumability, contribute, status, connect hardening, glob expansion, grep sweep)
- ✅ `[MANUAL]` tags on 3 tasks that require human authoring or human-driven CLI (record decision, commit message, archive)

**Status**: Ready for implementation via `/opsx-apply symlink-based-artifact-sync`
