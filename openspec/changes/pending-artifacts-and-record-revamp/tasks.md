<!-- opsx:tdd-header:begin -->
## TDD WORKFLOW - MANDATORY FOR ALL TASKS

**CRITICAL**: This project follows strict Test-Driven Development (TDD). Before implementing ANY task:

### RED-GREEN-REFACTOR Cycle

1. **RED Phase - Write Failing Tests FIRST**
   - Read the task's TDD Test Cases (TC1-TCN)
   - Create test file in `tests/` directory
   - Write ALL test cases from the task BEFORE any implementation
   - Run tests - they MUST fail (import errors, missing functions, etc.)
   - If tests pass without implementation, you wrote the tests wrong!

2. **GREEN Phase - Implement Minimal Code**
   - Write ONLY enough code to make tests pass
   - Run tests after each implementation
   - All tests must pass before marking task complete

3. **REFACTOR Phase - Improve Code Quality**
   - Clean up implementation
   - Remove duplication
   - Improve naming
   - Tests must still pass after refactoring

### Task Completion Criteria

**A task is NOT complete until:**
- All TDD test cases are written
- All tests pass (or are justifiably skipped with documentation)
- Implementation matches the Expected Output
- Test results documented in tasks.md

**For skipped tests:**
- Add `@pytest.mark.skip(reason="...")` with clear justification
- Document in tasks.md under "Skipped Test Cases" section
- Explain why feature is deferred and when it will be implemented

### Test Organization

```
tests/
├── core/           # Core module tests
├── <module>/       # Module-specific tests
└── conftest.py     # Shared fixtures
```

### Running Tests

```bash
# Activate venv, install dev deps, run tests
source .venv/bin/activate
uv sync --extra dev
pytest tests/ -v --tb=short
```

**See Also:**
- Check project AGENTS.md for unit testing workflow
- Check knowledge base for TDD lessons and standards
<!-- opsx:tdd-header:end -->

<!-- opsx:repos-table:begin -->
## Repositories & Branches

| Repo | Path | Branch | Role |
|------|------|--------|------|
| `agentic-beacon` | `~/Documents/oss/agentic-beacon` | `implement-pending-artifacts-and-record-revamp` | Code changes — pending.yaml schema, .last-adopt marker, CLI alert hook, abc adopt three-way actions + rollback, record-knowledge / record-skill rewrites, docs/migrations, sample-warehouse regen, CHANGELOG. |
| `hl-knowledge-market` | `~/Documents/oss/hl-knowledge-market` | `main` | Operational only — warehouse target where record-knowledge / record-skill write authored artifacts (knowledge/, skills/, contexts/). No code edits in this repo as part of this change; touched indirectly via `record-*` happy-path tests. |
<!-- opsx:repos-table:end -->

## 1. Core manifest & gitignore

<!-- opsx:phase-summary:1:begin -->
**Goal**: Define the `pending.yaml` data model and ensure new project-local files are gitignored by default.
**Input**: Existing `core/manifest/{beacon,workspace}.py` patterns; existing `core/gitignore.py` template; sample warehouse fixture.
**Output**: `PendingEntry` + `PendingManifest` Pydantic models with YAML round-trip. `GITIGNORE_ENTRIES` includes `.agentic-beacon/pending.yaml` and `.agentic-beacon/.last-adopt`. Sample warehouse `.gitignore` regenerated.
**Validation**: `pytest libs/beacon/tests/unit/test_pending.py -q` green. `diff <(abc warehouse init <tmp>; cat <tmp>/.gitignore) examples/sample-warehouse/.gitignore` is empty.
<!-- opsx:phase-summary:1:end -->


- [x] 1.1 Create `libs/beacon/src/beacon/core/manifest/pending.py` with `PendingEntry` Pydantic model (fields: `path: str`, `type: Literal["knowledge", "skill", "context", "agent"]`, `action: Literal["created", "modified"]`, `source: str`, `created_at: datetime`) and `PendingManifest` (wraps `pending: list[PendingEntry]`).
<!-- opsx:tdd:1.1:begin -->
  - **Input**: from beacon.core.manifest.pending import PendingEntry, PendingManifest; PendingEntry(path='knowledge/lessons/x.md', type='knowledge', action='created', source='record-knowledge', created_at=datetime.now(timezone.utc))
  - **Expected Output**: Constructs without error. All five fields required (no defaults except where the spec explicitly allows). `type` and `action` reject values outside their Literal set. `PendingManifest(pending=[entry]).pending == [entry]`.
  - **Validation**: `pytest libs/beacon/tests/unit/test_pending.py::test_well_formed_entry_constructs_round_trip -q` green.
  - **TDD Test Cases (write these first):**
    - TC1: All five fields supplied, valid types → entry constructs
    - TC2: Missing `type` → ValidationError citing field name
    - TC3: Missing `created_at` → ValidationError
    - TC4: `action='deleted'` → ValidationError listing allowed values
    - TC5: `type='unknown'` → ValidationError
    - TC6: `source='my-custom-skill'` (free-form string) → entry constructs
    - TC7: `created_at` as naive datetime vs UTC-aware → behaviour documented (UTC required)
    - TC8: `PendingManifest(pending=[])` → empty manifest constructs
<!-- opsx:tdd:1.1:end -->
- [x] 1.2 Implement `PendingManifest.from_yaml(path: Path) -> PendingManifest` that tolerates absent file (returns empty manifest) and raises clear validation errors on schema violations.
<!-- opsx:tdd:1.2:begin -->
  - **Input**: PendingManifest.from_yaml(Path('/tmp/nonexistent.yaml')) and PendingManifest.from_yaml(Path('/tmp/malformed.yaml'))
  - **Expected Output**: Absent path → `PendingManifest(pending=[])`. Malformed YAML or schema violation → ValidationError identifying the offending entry index and field.
  - **Validation**: `pytest libs/beacon/tests/unit/test_pending.py -q -k from_yaml` green.
  - **TDD Test Cases (write these first):**
    - TC1: Path does not exist → empty manifest, no exception
    - TC2: Path is empty file → empty manifest, no exception
    - TC3: Valid YAML with `pending: []` → empty manifest
    - TC4: Valid YAML with one entry → manifest with one entry, fields preserved
    - TC5: YAML missing required field on entry 0 → ValidationError citing entry index 0 + field
    - TC6: YAML with `action: deleted` on entry 1 → ValidationError citing entry index 1 + allowed values
    - TC7: YAML at top level missing `pending` key → ValidationError
    - TC8: Non-YAML garbage in file → parse error surfaced clearly
<!-- opsx:tdd:1.2:end -->
- [x] 1.3 Implement `PendingManifest.to_yaml(path: Path) -> None` preserving field order (path / type / action / source / created_at) and pretty-printing with trailing newline.
<!-- opsx:tdd:1.3:begin -->
  - **Input**: manifest.to_yaml(tmp_path/'pending.yaml'); content = (tmp_path/'pending.yaml').read_text()
  - **Expected Output**: File ends with `\n`. Field order on each entry: `path` then `type` then `action` then `source` then `created_at`. `PendingManifest.from_yaml(path)` returns a manifest equal to the source.
  - **Validation**: `pytest libs/beacon/tests/unit/test_pending.py -q -k to_yaml or round_trip` green.
  - **TDD Test Cases (write these first):**
    - TC1: Empty manifest → `pending: []\n` (or canonical empty form), trailing newline
    - TC2: One entry → field order exactly path/type/action/source/created_at
    - TC3: Multiple entries → entry order preserved
    - TC4: Round-trip from_yaml(to_yaml(m)) == m for non-trivial manifest
    - TC5: ISO-8601 UTC timestamp serialises in canonical format (no float, no naive)
<!-- opsx:tdd:1.3:end -->
- [x] 1.4 Implement `PendingManifest.append(entry: PendingEntry) -> None` with in-memory mutation (persistence via `to_yaml`).
<!-- opsx:tdd:1.4:begin -->
  - **Input**: manifest.append(entry); manifest.to_yaml(path); reloaded = PendingManifest.from_yaml(path)
  - **Expected Output**: After append: `manifest.pending[-1] == entry`. After to_yaml + from_yaml: reloaded manifest contains the appended entry at the end. Append does NOT touch disk.
  - **Validation**: `pytest libs/beacon/tests/unit/test_pending.py -q -k append` green.
  - **TDD Test Cases (write these first):**
    - TC1: Append to empty manifest → length 1
    - TC2: Append twice → length 2, order preserved
    - TC3: Append then to_yaml then from_yaml → reloaded has same entries in same order
    - TC4: Append does not call write/open (verify via mock or `tmp_path` non-existence post-append)
<!-- opsx:tdd:1.4:end -->
- [x] 1.5 Unit tests: round-trip serialization, missing-field validation, invalid-enum validation, append-then-dump ordering, empty-file handling.
<!-- opsx:tdd:1.5:begin -->
  - **Input**: pytest libs/beacon/tests/unit/test_pending.py -q
  - **Expected Output**: All test scenarios listed in 1.5 covered (round-trip, missing-field, invalid-enum, append-then-dump ordering, empty-file). Zero failed tests, zero skipped tests.
  - **Validation**: Coverage of `core/manifest/pending.py` ≥ 90% (`pytest --cov=beacon.core.manifest.pending`).
<!-- opsx:tdd:1.5:end -->
- [x] 1.6 Update `libs/beacon/src/beacon/core/gitignore.py` template to include `.agentic-beacon/pending.yaml` and `.agentic-beacon/.last-adopt` alongside the existing `config.toml` entry.
<!-- opsx:tdd:1.6:begin -->
  - **Input**: Inspect `libs/beacon/src/beacon/core/gitignore.py` and any test that asserts on the entries.
  - **Expected Output**: `GITIGNORE_ENTRIES` (or the equivalent project-level template) contains `.agentic-beacon/pending.yaml` and `.agentic-beacon/.last-adopt` alongside the existing `.agentic-beacon/config.toml` entry. Order: existing entries first, new entries appended.
  - **Validation**: `grep -n 'pending.yaml' libs/beacon/src/beacon/core/gitignore.py` returns the new entry. Existing gitignore tests still pass.
  - **Note**: Design ambiguity resolved during D1: the new entries belong in project-level `GITIGNORE_ENTRIES`, NOT the warehouse-template gitignore. The two surfaces are different — see design.md §1 (config.toml as warehouse pointer) and §10 (alert suppressed outside a project).
<!-- opsx:tdd:1.6:end -->
- [x] 1.7 Regenerate `examples/sample-warehouse/` gitignore output to reflect 1.6.
<!-- opsx:tdd:1.7:begin -->
  - **Input**: abc warehouse init /tmp/sample-warehouse-regen-test && diff /tmp/sample-warehouse-regen-test/.gitignore examples/sample-warehouse/.gitignore
  - **Expected Output**: Diff is empty. The committed sample exactly matches a fresh `abc warehouse init` output.
  - **Validation**: `diff` exits 0. If interactive prompts block `abc warehouse init`, fall back to `diff libs/beacon/src/beacon/data/templates/.gitignore examples/sample-warehouse/.gitignore` — also empty.
  - **Note**: 1.6's entries (`pending.yaml`, `.last-adopt`) are project-level, NOT warehouse-template — so 1.7 does NOT add them to the sample warehouse gitignore. 1.7 only catches any pre-existing template/sample drift.
<!-- opsx:tdd:1.7:end -->

## 2. `.last-adopt` marker

<!-- opsx:phase-summary:2:begin -->
**Goal**: Persist the timestamp of the last successful adopt commit so warehouse-diff discovery has a cursor.
**Input**: Phase 1 complete (gitignore entry exists). Empty `<project>/.agentic-beacon/`.
**Output**: `domains/adoption/last_adopt.py` with `read_last_adopt` / `write_last_adopt`. ISO-8601 UTC single-line file.
**Validation**: `pytest libs/beacon/tests/unit/test_last_adopt.py -q` green. Round-trip: write → read returns equal datetime.
<!-- opsx:phase-summary:2:end -->


- [x] 2.1 Add helper `libs/beacon/src/beacon/domains/adoption/last_adopt.py` with `read_last_adopt(project_root: Path) -> datetime | None` and `write_last_adopt(project_root: Path, when: datetime) -> None`. Format: single ISO-8601 UTC line.
<!-- opsx:tdd:2.1:begin -->
  - **Input**: from beacon.domains.adoption.last_adopt import read_last_adopt, write_last_adopt; write_last_adopt(tmp_path, datetime(2026,5,6,15,0,0,tzinfo=timezone.utc)); read_last_adopt(tmp_path)
  - **Expected Output**: After write: `<tmp_path>/.agentic-beacon/.last-adopt` exists with content `2026-05-06T15:00:00+00:00\n` (or canonical ISO-8601 UTC equivalent). After read: returns equal aware datetime. If file absent: returns None. If malformed: raises with clear message.
  - **Validation**: `pytest libs/beacon/tests/unit/test_last_adopt.py -q` green.
  - **TDD Test Cases (write these first):**
    - TC1: Write then read → returned datetime equals input (timezone-aware)
    - TC2: Read absent file → returns None, no exception
    - TC3: Read empty file → returns None or raises clearly (consistent with spec)
    - TC4: Read malformed line (`not-a-date`) → raises with clear message
    - TC5: Write to non-existent project_root → creates `.agentic-beacon/` dir then file
    - TC6: Write same path twice → second write overwrites (not appended)
<!-- opsx:tdd:2.1:end -->
- [x] 2.2 Unit tests: absent file returns `None`, write-then-read round-trips exactly, malformed file raises a clear error.
<!-- opsx:tdd:2.2:begin -->
  - **Input**: pytest libs/beacon/tests/unit/test_last_adopt.py -q
  - **Expected Output**: All 2.1 scenarios covered. Zero failed.
  - **Validation**: Coverage of `last_adopt.py` ≥ 90%.
<!-- opsx:tdd:2.2:end -->

## 3. Pending alert hook

<!-- opsx:phase-summary:3:begin -->
**Goal**: Surface non-empty `pending.yaml` to the user on every `abc` invocation inside a project.
**Input**: Phase 1 complete (`PendingManifest` available). Click group entry at `cli/main.py`.
**Output**: `cli/pending_alert.py` (or domain-layer impl + cli re-export) with `maybe_emit_pending_alert(cwd)`. Wired into the root `main()` Click group before subcommand dispatch.
**Validation**: `abc warehouse status` in a project with non-empty `pending.yaml` prints `⚠ N pending artifacts. Run 'abc adopt' to wire them.` on stderr; subcommand still runs. Outside a project (no config.toml in cwd-walk), no alert.
<!-- opsx:phase-summary:3:end -->


- [x] 3.1 Add helper `libs/beacon/src/beacon/cli/pending_alert.py` with `maybe_emit_pending_alert(cwd: Path) -> None` that walks up for `.agentic-beacon/config.toml`, reads `pending.yaml` if present, and emits the one-line stderr notice when entries exist.
<!-- opsx:tdd:3.1:begin -->
  - **Input**: maybe_emit_pending_alert(tmp_path) with various states of `.agentic-beacon/config.toml` and `pending.yaml` present/absent under tmp_path. Capture stderr via pytest `capsys`.
  - **Expected Output**: Stderr contains `⚠ N pending artifacts. Run 'abc adopt' to wire them.` (with N matching count) when both files exist and pending.yaml is non-empty. Stderr empty in suppression cases (no config.toml, or pending.yaml absent/empty).
  - **Validation**: `pytest libs/beacon/tests/unit/test_pending_alert.py -q` green. Architecture test (TC9) still green if function lives in domain layer with cli re-export.
  - **TDD Test Cases (write these first):**
    - TC1: config.toml at cwd, pending.yaml has 3 entries → stderr line printed with count=3
    - TC2: config.toml at cwd-walk parent, pending.yaml has 1 entry → alert prints, walking finds config
    - TC3: No config.toml in cwd-walk chain → no alert, no exception
    - TC4: config.toml present, pending.yaml absent → no alert
    - TC5: config.toml present, pending.yaml `pending: []` → no alert
    - TC6: pending.yaml malformed → does NOT raise; degrades gracefully (silent or warning, never blocking)
    - TC7: Function returns None and never raises (verified: invoking before subcommand must not abort)
<!-- opsx:tdd:3.1:end -->
- [x] 3.2 Wire the helper into the Click group entry in `libs/beacon/src/beacon/cli/main.py` (or root command decorator) so it runs before every `abc` subcommand.
<!-- opsx:tdd:3.2:begin -->
  - **Input**: Inspect `cli/main.py`; run `abc --help` from within a project that has non-empty pending.yaml.
  - **Expected Output**: `maybe_emit_pending_alert(Path.cwd())` is called inside the root `@click.group` `main()` function before any subcommand-specific logic. `abc --help` and `abc warehouse status` both show the alert (stderr) followed by their normal output (stdout).
  - **Validation**: `grep -n 'maybe_emit_pending_alert' libs/beacon/src/beacon/cli/main.py` returns one match in the group entry. Manual run: `abc --help 2>&1 >/dev/null` shows the alert when applicable.
<!-- opsx:tdd:3.2:end -->
- [x] 3.3 Unit tests: alert fires with correct count, alert suppressed when `pending.yaml` absent or empty, alert suppressed when no `config.toml` in cwd-walk chain, alert does not block subcommand execution.
<!-- opsx:tdd:3.3:begin -->
  - **Input**: pytest libs/beacon/tests/unit/test_pending_alert.py -q
  - **Expected Output**: All four scenarios covered. Zero failed.
  - **Validation**: Coverage of `cli/pending_alert.py` (or its domain counterpart) ≥ 90%.
<!-- opsx:tdd:3.3:end -->

## 4. Adopt discovery merge

<!-- opsx:phase-summary:4:begin -->
**Goal**: Unify `pending.yaml` entries and warehouse-modified-since-`.last-adopt` files into one TUI candidate list with `path`-level dedup.
**Input**: Phases 1+2 complete. Existing `domains/adoption/discovery.py` and warehouse git-diff machinery.
**Output**: Discovery returns deduplicated candidate list. `pending.yaml` source-of-truth wins on metadata (source/created_at/action). Warehouse-only entries annotated `source="warehouse-modified"` (display-only).
**Validation**: `pytest libs/beacon/tests/unit/` discovery tests green. Manual: stage one entry in pending.yaml + edit one warehouse file → exactly two TUI rows, one annotated `warehouse-modified`. Both sources for same `path` → one row.
<!-- opsx:phase-summary:4:end -->


- [x] 4.1 Extend `libs/beacon/src/beacon/domains/adoption/discovery.py` to merge two sources into one candidate list: entries from `pending.yaml`, and warehouse files modified since `.last-adopt` (via existing git-diff machinery).
<!-- opsx:tdd:4.1:begin -->
  - **Input**: discovery.discover_candidates(project_root) with a fixture project containing 2 pending.yaml entries + 1 warehouse-modified file (since `.last-adopt`).
  - **Expected Output**: Returns 3 candidates (no dedup needed for this case). Each carries enough metadata for the TUI to render (path, type, action, source, created_at when available).
  - **Validation**: `pytest libs/beacon/tests/unit/test_discovery.py -q -k merge` green.
  - **TDD Test Cases (write these first):**
    - TC1: pending.yaml has 2 entries, no warehouse changes → returns 2 candidates
    - TC2: pending.yaml empty, warehouse has 1 modified file post-`.last-adopt` → returns 1 candidate
    - TC3: Both empty → returns []
    - TC4: `.last-adopt` absent → all warehouse files post-baseline are candidates (per spec)
    - TC5: Existing discovery callers still work (regression check)
<!-- opsx:tdd:4.1:end -->
- [x] 4.2 Implement dedup by `path`: when both sources present, prefer the `pending.yaml` entry's metadata (source, created_at, action).
<!-- opsx:tdd:4.2:begin -->
  - **Input**: discovery.discover_candidates with same `path` in both pending.yaml and warehouse-diff.
  - **Expected Output**: Result has exactly one row for that path. Its `source`, `created_at`, `action` come from the pending.yaml entry — not from warehouse-diff.
  - **Validation**: Test asserts on metadata fields of the deduplicated row. Result length matches expected.
  - **TDD Test Cases (write these first):**
    - TC1: Same path in both sources → 1 row, source=pending entry's source
    - TC2: Same path in both, pending action=`modified` → result action=`modified` (not `created`)
    - TC3: Different paths in both sources → 2 rows, no dedup
    - TC4: Two pending entries with same path (degenerate input) → behaviour defined and tested (last-write-wins or error)
<!-- opsx:tdd:4.2:end -->
- [x] 4.3 Annotate warehouse-diff-only entries with `source = "warehouse-modified"` (display-only; not written back to `pending.yaml`).
<!-- opsx:tdd:4.3:begin -->
  - **Input**: discovery.discover_candidates with one warehouse-only candidate; inspect returned candidate's source field; verify pending.yaml is unchanged after discover.
  - **Expected Output**: Warehouse-only row has `source == 'warehouse-modified'`. `pending.yaml` content is byte-identical before/after `discover_candidates` call.
  - **Validation**: Test asserts source string + asserts no IO write to pending.yaml (mock or filesystem snapshot).
  - **TDD Test Cases (write these first):**
    - TC1: Warehouse-only candidate → source='warehouse-modified'
    - TC2: pending.yaml byte-equal pre/post discover (no write-back)
    - TC3: Mixed sources → only warehouse-only rows get the annotation
<!-- opsx:tdd:4.3:end -->
- [x] 4.4 Unit tests: pending-only entry, warehouse-only entry, both-sources dedup, empty-both case.
<!-- opsx:tdd:4.4:begin -->
  - **Input**: pytest libs/beacon/tests/unit/test_discovery.py -q -k pending or merge or dedup
  - **Expected Output**: All four scenarios covered. Zero failed.
  - **Validation**: Coverage of the new discovery code ≥ 90%.
<!-- opsx:tdd:4.4:end -->

## 5. Adopt TUI three-way actions

<!-- opsx:phase-summary:5:begin -->
**Goal**: Expand the per-entry action set from binary (accept/skip) to three-way (accept/reject/defer), with no filesystem mutation during the mark phase.
**Input**: Phase 4 complete (candidate list available). Existing `domains/adoption/tui.py` (textual-based).
**Output**: Three-way per-entry mark in session state. Visual mark + `source` label rendered. No on-disk mutation during marking.
**Validation**: TUI unit/snapshot tests pass. Manual: mark each of 3 entries with a different action; cancel before Apply; verify `beacon.yaml`, `pending.yaml`, `.last-adopt` are byte-identical to pre-session.
<!-- opsx:phase-summary:5:end -->


- [x] 5.1 Extend `libs/beacon/src/beacon/domains/adoption/tui.py` per-entry action model from binary (accept/skip) to three-way (accept/reject/defer); update key bindings.
<!-- opsx:tdd:5.1:begin -->
  - **Input**: TUI test harness pressing key bindings on each candidate row; inspect resulting session state.
  - **Expected Output**: Three distinct keybindings (a = accept, r = reject, d = defer or per design). Session state records the chosen action per row. Default state for unmarked rows = defer (per spec scenario 'Defer is the no-op default').
  - **Validation**: TUI snapshot/unit tests green.
  - **TDD Test Cases (write these first):**
    - TC1: Press accept on row → state[row]='accept'
    - TC2: Press reject on row → state[row]='reject'
    - TC3: Press defer on row → state[row]='defer'
    - TC4: Toggle accept→reject→defer same row → final state correct, no leakage
    - TC5: Default (no key) state → 'defer'
<!-- opsx:tdd:5.1:end -->
- [x] 5.2 Add visual affordance showing each entry's current mark + its `source` label.
- [x] 5.3 Ensure marking choices only update in-memory session state; no filesystem or config mutation during mark phase.
<!-- opsx:tdd:5.3:begin -->
  - **Input**: Snapshot byte-content of `beacon.yaml`, `pending.yaml`, `.last-adopt` before TUI session; perform 3 marks; cancel before Apply; re-snapshot.
  - **Expected Output**: All three files byte-identical before and after the mark phase.
  - **Validation**: Test using `filecmp.cmp(..., shallow=False)` or sha256 comparison on each of the 3 files.
  - **TDD Test Cases (write these first):**
    - TC1: Mark 3 rows then cancel → 3 files byte-identical
    - TC2: Mark all rows accept then cancel → still byte-identical
    - TC3: No marks then cancel → still byte-identical (defensive baseline)
<!-- opsx:tdd:5.3:end -->
- [x] 5.4 TUI unit/snapshot tests for the three-way mark transitions and display layout.
<!-- opsx:tdd:5.4:begin -->
  - **Input**: pytest libs/beacon/tests/unit/test_tui.py -q (or wherever TUI tests live)
  - **Expected Output**: Tests for transitions (5.1 TC1-TC5), display layout (visible mark + source label per row), and the 5.3 byte-equality invariant — all green.
  - **Validation**: Coverage of new TUI code ≥ 80% (snapshot tests dominate).
<!-- opsx:tdd:5.4:end -->

## 6. Adopt session-atomic Apply + confirm + rollback

<!-- opsx:phase-summary:6:begin -->
**Goal**: Commit a marked session as a single logical transaction with a confirm screen and full rollback on mid-commit failure.
**Input**: Phase 5 complete (marks recorded in session state).
**Output**: Apply binding → confirm screen → atomic commit. Pre-commit snapshot of `beacon.yaml` / `pending.yaml` / `.last-adopt` enables full restore on any failure. Reject removes from `pending.yaml` only; warehouse untouched. `.last-adopt` advances only on successful commit.
**Validation**: Integration tests for happy path (2 accept / 1 reject / 1 defer) and rollback (induced symlink-sync failure mid-commit) both green. Byte-equality of pre/post-state on cancel.
<!-- opsx:phase-summary:6:end -->


- [x] 6.1 Add Apply key binding that transitions to a confirm screen summarising `N accepted / N rejected / N deferred` with projected mutations (beacon.yaml adds, symlink syncs, pending.yaml reductions).
<!-- opsx:tdd:6.1:begin -->
  - **Input**: TUI session with 2 accept / 1 reject / 1 defer; press Apply key; inspect rendered confirm screen.
  - **Expected Output**: Confirm screen displays exact totals `2 accepted / 1 rejected / 1 deferred` and the projected mutations: beacon.yaml additions list, symlink sync paths, pending.yaml reductions. Waits for explicit confirm/cancel input.
  - **Validation**: Snapshot test of confirm screen content; manual interaction confirms wait-for-input behaviour.
<!-- opsx:tdd:6.1:end -->
- [x] 6.2 Implement commit transaction in `libs/beacon/src/beacon/domains/adoption/apply.py`: pre-snapshot `beacon.yaml`, `pending.yaml`, `.last-adopt`; apply accepts (beacon.yaml + symlink sync); apply rejects (drop from pending.yaml only, warehouse untouched); keep defers in pending.yaml; advance `.last-adopt`.
<!-- opsx:tdd:6.2:begin -->
  - **Input**: apply.commit(session_state, project_root) with a fixture project. Pre-record byte-content of beacon.yaml/pending.yaml/.last-adopt + warehouse file content for the rejected entry's path.
  - **Expected Output**: After successful commit: beacon.yaml has new entries for accepted candidates (correct artifact category). Symlinks for accepted entries exist and resolve to warehouse. pending.yaml contains ONLY the deferred entries (rejected entries removed, accepted entries removed). `.last-adopt` set to commit timestamp. Warehouse files for rejected entries are byte-identical to pre-commit.
  - **Validation**: Integration test asserts on each of the 4 invariants. Architecture test still green.
  - **TDD Test Cases (write these first):**
    - TC1: 2 accept / 0 reject / 0 defer → beacon.yaml +2 entries, 2 symlinks, pending empty
    - TC2: 0 accept / 2 reject / 0 defer → pending.yaml empty, warehouse files unchanged, beacon.yaml unchanged
    - TC3: 0 accept / 0 reject / 2 defer → pending.yaml unchanged, beacon.yaml unchanged, .last-adopt advanced
    - TC4: Mixed 2/1/1 → all 4 invariants hold simultaneously
    - TC5: Committing twice in succession (idempotency) — second call is a no-op or handles empty session correctly
    - TC6: `.last-adopt` advances ONLY on successful commit, never on partial state
<!-- opsx:tdd:6.2:end -->
- [x] 6.3 Implement rollback: on any mutation failure mid-commit, restore all three files to their pre-snapshot contents and surface a clear error identifying the failing entry.
<!-- opsx:tdd:6.3:begin -->
  - **Input**: apply.commit with a fixture that monkey-patches symlink_sync to raise on the second accepted entry. Pre-record byte-content of all three files.
  - **Expected Output**: Function raises with a clear error citing the failing entry's path and the underlying cause. After the raise: beacon.yaml, pending.yaml, .last-adopt are byte-identical to pre-commit snapshots.
  - **Validation**: `pytest libs/beacon/tests/integration/test_adopt_apply.py::test_rollback_on_symlink_failure -q` green.
  - **TDD Test Cases (write these first):**
    - TC1: Symlink failure on entry 2 of 3 → raise + 3 files restored
    - TC2: pending.yaml write failure → raise + beacon.yaml + .last-adopt restored
    - TC3: `.last-adopt` write failure → raise + beacon.yaml + pending.yaml restored
    - TC4: Error message includes the failing entry's path
    - TC5: Rollback is idempotent (calling rollback twice on already-restored state is a no-op)
<!-- opsx:tdd:6.3:end -->
- [x] 6.4 Cancel from confirm screen leaves filesystem unchanged; verify by byte-equality of the three files before/after.
<!-- opsx:tdd:6.4:begin -->
  - **Input**: Open TUI, mark some rows, hit Apply, hit Cancel on confirm screen. Snapshot byte-content of the three files before TUI session.
  - **Expected Output**: After cancel: beacon.yaml, pending.yaml, .last-adopt byte-identical to pre-session snapshot.
  - **Validation**: `filecmp.cmp(snapshot, current, shallow=False)` returns True for all three files.
<!-- opsx:tdd:6.4:end -->
- [x] 6.5 Integration test: 2 accept / 1 reject / 1 defer happy path → post-state matches expectations.
<!-- opsx:tdd:6.5:begin -->
  - **Input**: pytest libs/beacon/tests/integration/test_adopt_apply.py::test_happy_path -q
  - **Expected Output**: Test exercises the full TUI → confirm → commit flow against a fixture project. Asserts all 4 invariants from 6.2 TC4.
  - **Validation**: Test green. No flakiness over 3 consecutive runs.
<!-- opsx:tdd:6.5:end -->
- [x] 6.6 Integration test: induced symlink-sync failure mid-commit → all three files restored to pre-state; error message identifies failing entry.
<!-- opsx:tdd:6.6:begin -->
  - **Input**: pytest libs/beacon/tests/integration/test_adopt_apply.py::test_rollback_on_symlink_failure -q
  - **Expected Output**: Test injects symlink failure at entry 2 of 3, asserts raise with entry path in message, asserts all three files restored byte-identically.
  - **Validation**: Test green.
<!-- opsx:tdd:6.6:end -->

## 7. record-knowledge skill revamp

<!-- opsx:phase-summary:7:begin -->
**Goal**: Rebuild `record-knowledge` to write knowledge files to the warehouse working tree, append to `pending.yaml`, and never touch `AGENTS.md`.
**Input**: Phases 1+2+3 complete. Existing `record-knowledge/SKILL.md` + `create_skill.py` (project-side write model).
**Output**: Two PEP 723 helpers (`resolve_warehouse.py`, `append_pending.py`) under `record-knowledge/scripts/`. SKILL.md rewritten for warehouse-target write + warehouse-context-only pointer flow + diff-confirm + pending-append + hard-error on missing warehouse.
**Validation**: Manual happy-path: run `record-knowledge` in agentic-beacon → knowledge file lands at `<warehouse>/knowledge/<type>/<name>.md`, pointer diff displayed and accepted, `pending.yaml` has 2 entries (knowledge created + context modified).
<!-- opsx:phase-summary:7:end -->


- [x] 7.1 Create `libs/beacon/src/beacon/data/skills/record-knowledge/scripts/resolve_warehouse.py` (PEP 723): walks up from `$PWD` for `.agentic-beacon/config.toml`, parses `[warehouse] local_path`, prints absolute path or errors to stderr and exits non-zero with the documented error text.
<!-- opsx:tdd:7.1:begin -->
  - **Input**: uv run libs/beacon/src/beacon/data/skills/record-knowledge/scripts/resolve_warehouse.py with PWD set to (a) project with config.toml, (b) nested subdir, (c) directory with no config.toml.
  - **Expected Output**: (a)+(b): exit 0, stdout = absolute warehouse path, stderr empty. (c): exit non-zero, stderr = `Error: no warehouse connected. Run 'abc warehouse connect <path>' first.`
  - **Validation**: `pytest libs/beacon/tests/unit/test_record_knowledge_scripts.py -q -k resolve_warehouse` green.
  - **TDD Test Cases (write these first):**
    - TC1: PWD = project root with valid config.toml → exit 0, stdout = absolute path
    - TC2: PWD = nested subdir of project → walks up, exit 0, stdout = absolute path
    - TC3: PWD = directory outside any project → exit non-zero, stderr matches documented text
    - TC4: config.toml exists but missing `[warehouse]` section → exit non-zero, parse error citing missing field
    - TC5: config.toml exists with `[warehouse]` but no `local_path` → exit non-zero, parse error citing missing field
    - TC6: PEP 723 metadata block valid (script runs via `uv run` without manual deps)
<!-- opsx:tdd:7.1:end -->
- [x] 7.2 Create `libs/beacon/src/beacon/data/skills/record-knowledge/scripts/append_pending.py` (PEP 723): CLI flags `--path --type --action --source`; auto-stamps `created_at`; resolves project root via cwd-walk; appends to `.agentic-beacon/pending.yaml`; creates the file if absent.
<!-- opsx:tdd:7.2:begin -->
  - **Input**: uv run append_pending.py --path knowledge/lessons/x.md --type knowledge --action created --source record-knowledge (with PWD inside a project).
  - **Expected Output**: Exit 0. `.agentic-beacon/pending.yaml` exists and contains the new entry at the end. `created_at` is current UTC ISO-8601. Field order on dump is path/type/action/source/created_at.
  - **Validation**: Read pending.yaml after run, parse with `PendingManifest.from_yaml`, assert last entry matches inputs (timestamp ≈ now).
  - **TDD Test Cases (write these first):**
    - TC1: First call (pending.yaml absent) → file created with single entry
    - TC2: Second call → entry appended (length 2), order preserved
    - TC3: Missing `--path` → exit non-zero with usage error
    - TC4: Invalid `--type` value → exit non-zero with allowed values listed
    - TC5: Outside any project → exit non-zero with the same error text as resolve_warehouse
    - TC6: `--source` accepts free-form string (no enum check)
    - TC7: created_at is timezone-aware UTC, not naive
<!-- opsx:tdd:7.2:end -->
- [x] 7.3 Rewrite `record-knowledge/SKILL.md`: warehouse-target write flow, pointer-target prompt restricted to `<warehouse>/contexts/*.md` + "skip", diff-confirm before writing pointer, append-pending for both files (or just knowledge) depending on pointer decision, hard-error path when `resolve_warehouse.py` fails.
- [x] 7.4 Explicitly remove all mention of writing to `.agentic-beacon/artifacts/knowledge/` and of updating `AGENTS.md` from the SKILL.md.
<!-- opsx:tdd:7.4:begin -->
  - **Input**: grep -E '\.agentic-beacon/artifacts/knowledge|AGENTS\.md' libs/beacon/src/beacon/data/skills/record-knowledge/SKILL.md
  - **Expected Output**: Zero matches. (Acceptance grep — must be empty.)
  - **Validation**: Exit code 1 from grep (= no match), or stdout empty.
<!-- opsx:tdd:7.4:end -->
- [ ] 7.5 **[MANUAL]** Manual happy-path test: run `record-knowledge` in this repo; verify knowledge file lands in warehouse, pointer diff is shown, `pending.yaml` receives correct entries.
<!-- opsx:tdd:7.5:begin -->
  - **Input**: [MANUAL] In agentic-beacon repo, invoke `record-knowledge` skill via Claude Code/opencode. Author a lesson knowledge file. Accept warehouse-context pointer prompt.
  - **Expected Output**: Knowledge file written at `<warehouse>/knowledge/<type>/<name>.md`. Pointer diff displayed before context-file write; user confirms. `<project>/.agentic-beacon/pending.yaml` has 2 entries (knowledge created + context modified) with correct field order.
  - **Validation**: Manual inspection of warehouse, pending.yaml, and chosen context file. `git status` in warehouse shows new + modified files. `cat <project>/.agentic-beacon/pending.yaml` matches expectation.
<!-- opsx:tdd:7.5:end -->

## 8. record-skill skill revamp

<!-- opsx:phase-summary:8:begin -->
**Goal**: Rebuild `record-skill` to write skills to the warehouse working tree with `requires.contexts` suggestion, append to `pending.yaml`, and retire `create_skill.py`.
**Input**: Phase 7 complete (helper script pattern proven).
**Output**: Two independent PEP 723 helpers under `record-skill/scripts/`. SKILL.md rewritten for LLM-driven scaffold + warehouse-context scan for `requires.contexts` suggestion. `create_skill.py` and its `__pycache__/*.pyc` deleted.
**Validation**: Manual happy-path: run `record-skill` → skill dir at `<warehouse>/skills/<name>/SKILL.md`, requires.contexts suggestion shown, pending.yaml has 1 entry. `git rev-list HEAD -- libs/beacon/src/beacon/data/skills/record-skill/scripts/create_skill.py` shows deletion.
<!-- opsx:phase-summary:8:end -->


- [x] 8.1 Create `libs/beacon/src/beacon/data/skills/record-skill/scripts/resolve_warehouse.py` (PEP 723): independent copy of the record-knowledge helper.
<!-- opsx:tdd:8.1:begin -->
  - **Input**: Compare `record-knowledge/scripts/resolve_warehouse.py` and `record-skill/scripts/resolve_warehouse.py`.
  - **Expected Output**: Both files exist independently (per design.md decision 7: 'duplication over coupling'). Functional behaviour matches 7.1's contract.
  - **Validation**: `diff record-knowledge/scripts/resolve_warehouse.py record-skill/scripts/resolve_warehouse.py` may show differences (acceptable) but both must satisfy 7.1's TC1–TC6.
  - **TDD Test Cases (write these first):**
    - TC1: Same scenarios as 7.1 (TC1–TC6) — duplicated test module under record-skill/ tests directory or shared parametrised test
<!-- opsx:tdd:8.1:end -->
- [x] 8.2 Create `libs/beacon/src/beacon/data/skills/record-skill/scripts/append_pending.py` (PEP 723): independent copy of the record-knowledge helper.
<!-- opsx:tdd:8.2:begin -->
  - **Input**: Same as 7.2.
  - **Expected Output**: File exists independently from record-knowledge counterpart. Contract matches 7.2.
  - **Validation**: Same TC1–TC7 as 7.2 against this file.
<!-- opsx:tdd:8.2:end -->
- [x] 8.3 Delete `libs/beacon/src/beacon/data/skills/record-skill/scripts/create_skill.py` and its compiled `__pycache__/create_skill.cpython-312.pyc`.
<!-- opsx:tdd:8.3:begin -->
  - **Input**: find libs/beacon/src/beacon/data/skills/record-skill -name 'create_skill.py' -o -name 'create_skill.cpython-312.pyc'
  - **Expected Output**: Empty result (zero matches). `git log -- libs/beacon/src/beacon/data/skills/record-skill/scripts/create_skill.py | head -1` shows the deletion commit.
  - **Validation**: Find returns nothing. The deletion is captured in this change's commit.
<!-- opsx:tdd:8.3:end -->
- [x] 8.4 Rewrite `record-skill/SKILL.md`: LLM-driven flow gathering name / description / invocation / include-script; warehouse context scan for `requires.contexts` suggestion with accept / edit / skip; warehouse-target SKILL.md write (+ optional `scripts/<name>.py` PEP 723 scaffold); append-pending with `type: skill action: created source: record-skill`; hard-error path when `resolve_warehouse.py` fails.
- [ ] 8.5 **[MANUAL]** Manual happy-path test: run `record-skill` in this repo; verify skill directory lands in warehouse, `requires.contexts` suggestion surfaces correctly, `pending.yaml` receives entry.
<!-- opsx:tdd:8.5:begin -->
  - **Input**: [MANUAL] In agentic-beacon repo, invoke `record-skill` via Claude Code/opencode. Describe a new skill purpose (e.g. 'validate deployment readiness checklist').
  - **Expected Output**: Warehouse has `<warehouse>/skills/<name>/SKILL.md` (and optional `scripts/<name>.py` scaffold). `requires.contexts:` suggestion shown with rationale per match (or empty list when nothing matches). `pending.yaml` contains 1 entry: `path: skills/<name>/`, `type: skill`, `action: created`, `source: record-skill`.
  - **Validation**: Manual inspection of warehouse skill dir + pending.yaml entry. `cat pending.yaml` matches expectation byte-for-byte.
<!-- opsx:tdd:8.5:end -->

## 9. End-to-end integration tests

<!-- opsx:phase-summary:9:begin -->
**Goal**: Cover the full author → pending → adopt → wired pipeline plus error paths (missing warehouse, alert visibility) at the integration level.
**Input**: Phases 1–8 complete. Test fixtures for projects with non-empty `pending.yaml` and warehouse with hand-edited contexts.
**Output**: Six integration tests covering knowledge-no-pointer, knowledge-with-pointer, skill-create, hand-edited warehouse via `.last-adopt` diff, alert visibility, missing-warehouse hard-error.
**Validation**: `pytest libs/beacon/tests/integration/ -q -k pending` all green. No flakiness on three consecutive runs.
<!-- opsx:phase-summary:9:end -->


- [ ] 9.1 Integration test: author knowledge (no pointer) → one pending entry → `abc adopt` accept → beacon.yaml unchanged (knowledge is not a beacon.yaml artifact), pending.yaml empty, `.last-adopt` advanced.
<!-- opsx:tdd:9.1:begin -->
  - **Input**: pytest libs/beacon/tests/integration/test_pending_e2e.py::test_knowledge_no_pointer -q
  - **Expected Output**: Test simulates record-knowledge → pending append → abc adopt accept. Asserts: beacon.yaml unchanged, pending.yaml empty, .last-adopt advanced past pre-test value.
  - **Validation**: Test green. No flakiness.
  - **Note**: 9.1's 'beacon.yaml unchanged' invariant only applies because knowledge is not a beacon.yaml artifact. Confirm this with the supervisor before D4 — see review note flagged in D1 design discussion.
<!-- opsx:tdd:9.1:end -->
- [ ] 9.2 Integration test: author knowledge (with pointer) → two pending entries → `abc adopt` accept both → context file symlink reflects the updated body in the project.
<!-- opsx:tdd:9.2:begin -->
  - **Input**: pytest libs/beacon/tests/integration/test_pending_e2e.py::test_knowledge_with_pointer -q
  - **Expected Output**: Test creates context pointer entry + knowledge entry, accepts both, asserts the project's symlinked context file includes the new pointer (transitive update via symlink).
  - **Validation**: Test green.
<!-- opsx:tdd:9.2:end -->
- [ ] 9.3 Integration test: author skill → one pending entry → `abc adopt` accept → beacon.yaml has new `skills/<name>/` entry, symlink created, pending.yaml empty.
<!-- opsx:tdd:9.3:begin -->
  - **Input**: pytest libs/beacon/tests/integration/test_pending_e2e.py::test_skill_create -q
  - **Expected Output**: Test simulates record-skill → pending → adopt accept. Asserts beacon.yaml has new artifact entry, project-side symlink resolves to warehouse skill dir, pending.yaml empty.
  - **Validation**: Test green.
<!-- opsx:tdd:9.3:end -->
- [ ] 9.4 Integration test: hand-edit a warehouse context file → no `pending.yaml` change → `abc adopt` picks up via `.last-adopt` diff → user accepts → handled correctly.
<!-- opsx:tdd:9.4:begin -->
  - **Input**: pytest libs/beacon/tests/integration/test_pending_e2e.py::test_warehouse_modified_via_last_adopt -q
  - **Expected Output**: Test edits warehouse context file directly (skipping pending.yaml), runs adopt, asserts the warehouse-modified entry surfaces in TUI with `source='warehouse-modified'`. After accept, `.last-adopt` advances; subsequent run does not re-show the entry.
  - **Validation**: Test green.
<!-- opsx:tdd:9.4:end -->
- [ ] 9.5 Integration test: run `abc warehouse status` in a project with non-empty `pending.yaml` → alert line appears first on stderr, command output follows, exit code unaffected.
<!-- opsx:tdd:9.5:begin -->
  - **Input**: pytest libs/beacon/tests/integration/test_pending_e2e.py::test_alert_visibility -q
  - **Expected Output**: Subprocess invocation of `abc warehouse status`: first stderr line matches `^⚠ \d+ pending artifacts\. Run 'abc adopt' to wire them\.$`. stdout shows normal `warehouse status` output. Exit code 0 (or whatever status would have been without the alert).
  - **Validation**: Test green.
<!-- opsx:tdd:9.5:end -->
- [ ] 9.6 Integration test: run `record-knowledge` in a project without `.agentic-beacon/config.toml` → hard error with documented text, no file writes.
<!-- opsx:tdd:9.6:begin -->
  - **Input**: pytest libs/beacon/tests/integration/test_pending_e2e.py::test_missing_warehouse_hard_error -q
  - **Expected Output**: Subprocess invocation of resolve_warehouse.py (or equivalent integration entry) from a directory with no config.toml: exit non-zero, stderr matches the documented error text from spec, no files created in cwd or anywhere.
  - **Validation**: Test green. Filesystem snapshot pre/post is byte-identical (modulo test tmp_path).
<!-- opsx:tdd:9.6:end -->

## 10. Docs & sample warehouse

<!-- opsx:phase-summary:10:begin -->
**Goal**: Capture user-visible behaviour changes in migration doc + AGENTS.md + site-docs, and ensure sample warehouse stays canonical.
**Input**: Phases 1–9 complete. Existing migrations directory and site-docs.
**Output**: `docs/migrations/pending-artifacts-flow-and-record-revamp.md`, updated root `AGENTS.md`, updated site-docs `.agentic-beacon/` layout page, regenerated `examples/sample-warehouse/`.
**Validation**: `mkdocs build` (or equivalent) succeeds. New migration page rendered and links to the relevant requirements in the spec. Sample warehouse byte-matches `abc warehouse init` output.
<!-- opsx:phase-summary:10:end -->


- [ ] 10.1 Add `docs/migrations/pending-artifacts-flow-and-record-revamp.md` covering: what `pending.yaml` is, how authoring skills changed, how `abc adopt` changed, breaking changes for `record-*` users, rollback path.
- [ ] 10.2 Update root `AGENTS.md` to reflect new `abc adopt` three-way actions and the pending alert.
- [ ] 10.3 Update site-docs page describing `.agentic-beacon/` layout to list `pending.yaml` and `.last-adopt`.
- [ ] 10.4 Regenerate `examples/sample-warehouse/` if anything structural changed (verify via `abc warehouse init` fresh-diff).
<!-- opsx:tdd:10.4:begin -->
  - **Input**: abc warehouse init /tmp/regen-check && diff -r /tmp/regen-check examples/sample-warehouse
  - **Expected Output**: Diff is empty (modulo .git/ if present in the temp dir).
  - **Validation**: `diff -r` exits 0 (or only `.git/` differences acceptable).
<!-- opsx:tdd:10.4:end -->

## 11. Release & verification

<!-- opsx:phase-summary:11:begin -->
**Goal**: Confirm install-time smoke tests pass + CHANGELOG records the breaking change before release.
**Input**: Phases 1–10 merged.
**Output**: Full pytest green. `abc --version` reports current. Fresh `abc warehouse init` includes the new gitignore entries. `record-knowledge` / `record-skill` smoke-tested end-to-end. CHANGELOG entry calls out breaking change for record-* users.
**Validation**: `pytest libs/beacon/` green from repo root. `git diff CHANGELOG*` shows the new entry. Release tag readiness checklist clean.
<!-- opsx:phase-summary:11:end -->


- [ ] 11.1 Run full test suite from repo root: `pytest` passes.
<!-- opsx:tdd:11.1:begin -->
  - **Input**: uv run pytest -q (from /Users/ypei/Documents/oss/agentic-beacon)
  - **Expected Output**: All collected tests pass. Skipped tests have justifications. No new regressions vs the base branch baseline.
  - **Validation**: Exit 0. `failed` count = 0 (or matches base-branch pre-existing-failure baseline if those still exist as pre-existing).
<!-- opsx:tdd:11.1:end -->
- [ ] 11.2 **[MANUAL]** Verify `abc --version` and basic commands still work after install.
<!-- opsx:tdd:11.2:begin -->
  - **Input**: [MANUAL] uv pip install -e libs/beacon (or equivalent local install) && abc --version && abc --help
  - **Expected Output**: Version reports current. Help renders without traceback. Pending-alert hook runs without breaking invocation when run inside a project with non-empty pending.yaml.
  - **Validation**: All three commands exit 0; output sanity-checked manually.
<!-- opsx:tdd:11.2:end -->
- [ ] 11.3 **[MANUAL]** Smoke test `abc warehouse init test-warehouse` and confirm `.gitignore` in output includes new entries.
<!-- opsx:tdd:11.3:begin -->
  - **Input**: [MANUAL] cd /tmp && abc warehouse init test-warehouse-$$ && cat test-warehouse-$$/.gitignore
  - **Expected Output**: Command exits 0. Output `.gitignore` does NOT include `pending.yaml` or `.last-adopt` (those are project-level, not warehouse-template). Sample-warehouse `.gitignore` matches the produced output byte-for-byte.
  - **Validation**: diff <(cat /tmp/test-warehouse-*/.gitignore) examples/sample-warehouse/.gitignore is empty.
<!-- opsx:tdd:11.3:end -->
- [ ] 11.4 **[MANUAL]** Smoke test `record-knowledge` and `record-skill` end-to-end in a fresh project connected to the sample warehouse.
<!-- opsx:tdd:11.4:begin -->
  - **Input**: [MANUAL] mkdir /tmp/smoke-project && cd /tmp/smoke-project && abc warehouse connect <sample-warehouse-path>; then invoke record-knowledge and record-skill via Claude Code.
  - **Expected Output**: Both skills execute end-to-end. record-knowledge produces 1–2 pending entries depending on pointer choice. record-skill produces 1 pending entry. abc adopt resolves them. beacon.yaml + pending.yaml + symlinks reflect expected post-adopt state.
  - **Validation**: Manual inspection. No traceback, no orphaned files in /tmp/smoke-project beyond what's committed.
<!-- opsx:tdd:11.4:end -->
- [ ] 11.5 Update CHANGELOG with breaking-change callout for `record-*` skills.
<!-- opsx:tdd:11.5:begin -->
  - **Input**: grep -A3 -B1 'BREAKING' CHANGELOG.md (or whatever changelog the repo uses)
  - **Expected Output**: New entry for the next release contains a `### BREAKING CHANGES` section calling out (a) record-knowledge no longer writes to `.agentic-beacon/artifacts/knowledge/` (warehouse-target only); (b) record-skill no longer invokes create_skill.py; (c) both skills hard-error without a connected warehouse.
  - **Validation**: git diff CHANGELOG* shows the new entries. Conventional Changelog `BREAKING CHANGE:` footer convention followed.
<!-- opsx:tdd:11.5:end -->

<!-- opsx:metadata:begin -->
---

## Enhancement Metadata

**Enhanced**: 2026-05-06
**Methodology**: Spec-Driven Development + TDD
**Enhancements Applied**:
- TDD Workflow Header
- Repositories & Branches table
- Phase summaries (Goal/Input/Output/Validation)
- Task-level TDD criteria on 45 task(s)
- 83 test case(s) across complex tasks
- 5 task(s) flagged [MANUAL]

**Status**: Ready for implementation via `/opsx-apply <name>`.
<!-- opsx:metadata:end -->
