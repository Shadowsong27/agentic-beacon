# Implementation Tasks — global-agent-artifact-type

## Repositories & Branches

| Repo | Path | Branch | Role |
|------|------|--------|------|
| `agentic-beacon` | `~/Code/agentic-beacon` | `global-agent-artifact-type` | Code changes — all implementation, tests, and templates |

---

## 🔴 TDD WORKFLOW - MANDATORY FOR ALL TASKS

**CRITICAL**: This project follows strict Test-Driven Development (TDD). Before implementing ANY task:

### RED-GREEN-REFACTOR Cycle

1. **🔴 RED Phase - Write Failing Tests FIRST**
   - Read the task's TDD Test Cases (TC1-TCN)
   - Create test file in `tests/` directory
   - Write ALL test cases from the task BEFORE any implementation
   - Run tests - they MUST fail (import errors, missing functions, etc.)
   - If tests pass without implementation, you wrote the tests wrong!

2. **🟢 GREEN Phase - Implement Minimal Code**
   - Write ONLY enough code to make tests pass
   - Run tests after each implementation
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
- ✅ Test results documented in tasks.md

### Test Organization

```
tests/
├── core/           # Core module tests (delta.py, sync.py, settings.py)
├── test_cli.py     # CLI command tests
└── conftest.py     # Shared fixtures
```

### Running Tests

```bash
uv sync --group dev
pytest tests/ -v --tb=short
```

---

## Phase Dependency Order

Phases must be implemented in order — each phase builds on the previous:

```
1. Template and Scaffold        — foundation: files and initializer
2. Warehouse Validator          — foundation: validation + CLI surfacing
3. Global Agent Detection       — foundation: _detect_agents_global()
4. Global Agent Sync State      — foundation: sync-state.json helpers (needed by phases 5 and 7)
5. Sync/Install Soft Block      — core infrastructure: classify_conflicts() (needed by phase 6)
6. Global Agent Install         — uses phases 3, 4, 5
7. Delta: Global Agent          — uses phases 3, 4 (STALE enrichment reads sync-state)
8. abc reset Command            — independent
9. Contribute No-op Detection   — independent verification
10. Install Flags               — uses phase 5 infrastructure
11. Tests and Docs              — final validation
```

---

## 1. Template and Scaffold

**Goal**: Create the `agents/` warehouse directory scaffold so `abc warehouse init` produces a complete, documented agents directory.
**Input**: Existing `initializer.py` with `_create_structure()`, `_create_skills()` patterns; existing `data/templates/` directory.
**Output**: `abc warehouse init` creates `agents/README.md`; `examples/sample-warehouse/agents/README.md` exists and matches the template; `TEMPLATE_FILES` tracks `agents/README.md`.
**Validation**: Run `abc warehouse init` in a temp directory; confirm `agents/README.md` is present with frontmatter format docs and install workflow instructions.

- [ ] 1.1 Create `libs/beacon/src/beacon/data/templates/agents/README.md` with frontmatter format explanation and `abc install agents/<name>.md` workflow
- [ ] 1.2 Add `_create_agents()` method to `WarehouseInitializer` in `initializer.py` (write `agents/README.md` from template, skip if exists)
- [ ] 1.3 Call `_create_agents()` from `_create_structure()` so `agents/` is scaffolded by `abc warehouse init`
- [ ] 1.4 Add `"agents/README.md"` to `TEMPLATE_FILES` list in `initializer.py` so `abc warehouse template-upgrade` tracks the file and the parity test in Phase 11 covers it
- [ ] 1.5 Create `examples/sample-warehouse/agents/README.md` matching the new template

## 2. Warehouse Validator and Agent Surfacing

**Goal**: Add `agents` as a validated warehouse directory and surface agent artifacts in `abc warehouse list`, `abc list`, and `abc setup`.
**Input**: `WarehouseValidator.REQUIRED_DIRECTORIES`; existing `warehouse_list()`, `list_cmd()`, and `setup()` handlers in `cli.py`.
**Output**: `abc warehouse connect` validates `agents/` directory exists; `abc warehouse list` shows warehouse-side agent files; `abc list agents` shows globally installed agents (other `abc list` filters remain project-scoped); `abc setup` guides user to `abc install agents/<name>`.
**Validation**: `pytest tests/ -v -k agent_surfacing` passes; manual `abc warehouse list` shows agents section.

- [ ] 2.1 Add `"agents"` to `REQUIRED_DIRECTORIES` in `libs/beacon/src/beacon/warehouse/validator.py`
  - **TDD Test Cases (write these first):**
    - TC1: Warehouse has `agents/` dir → validates successfully
    - TC2: Warehouse missing `agents/` dir → validation error listing `agents/`
    - TC3: Existing warehouses without `agents/` will now fail `abc warehouse connect` — add a note in the error message instructing users to run `mkdir agents/` to upgrade their warehouse

- [ ] 2.2 Add `"agents"` to the type list in `warehouse_list()` in `cli.py`; display warehouse-side `agents/` entries in their own table section
  - **TDD Test Cases (write these first):**
    - TC1: `abc warehouse list` → agents section shown alongside contexts/knowledge/skills
    - TC2: `abc warehouse list agents` → only agents section shown
    - TC3: Warehouse `agents/` dir is empty → "No agents found" message for that section

- [ ] 2.3 Add `"agents"` filter to `list_cmd()` in `cli.py`; when `abc list agents` is invoked, display globally installed agent files from `~/.config/opencode/agents/` and `~/.claude/agents/` (union, deduplicated by filename); all other `abc list` filters remain project-scoped (synced artifacts in `.agentic-beacon/artifacts/`)
  - **TDD Test Cases (write these first):**
    - TC1: `abc list agents` → shows globally installed agent files from both tool dirs
    - TC2: `abc list` (no filter) → agents section not shown (backward compatible; agents are global, not project-scoped)
    - TC3: No global agents installed → "No agents found" message
    - TC4: Same agent installed in both tool dirs → deduplicated, shown once with tool indicators

- [ ] 2.4 Update `abc setup` handler in `cli.py` to describe the `agents/` artifact type and print guidance: "Agent definitions are installed globally — use `abc install agents/<name>` to install them" (agents do NOT appear in `beacon.yaml`)

- [ ] 2.5 Write unit tests covering all TDD test cases for subtasks 2.1–2.4

## 3. Global Agent Detection

**Goal**: Introduce `_detect_agents_global()` cleanly separate from the project-level `_detect_agents(project_root)`.
**Input**: No existing global detection; `~/.config/opencode/` and `~/.claude/` as detection signals.
**Output**: Function in `cli.py` returning correct list based solely on home-dir state.
**Validation**: `pytest tests/ -v -k detect_agents_global` — all test cases pass.

- [ ] 3.1 Add `_detect_agents_global() -> list[str]` to `cli.py`; checks `~/.config/opencode/` for `opencode` and `~/.claude/` for `claudecode` (home-dir paths only)
  - **TDD Test Cases (write these first):**
    - TC1: Both `~/.config/opencode/` and `~/.claude/` exist → `["opencode", "claudecode"]`
    - TC2: Only `~/.config/opencode/` exists → `["opencode"]`
    - TC3: Only `~/.claude/` exists → `["claudecode"]`
    - TC4: Neither exists → `[]`
    - TC5: `~/.config/opencode` is a file (not dir) → not counted

- [ ] 3.2 Write unit tests for `_detect_agents_global()` covering TC1–TC5

## 4. Global Agent Sync State

**Goal**: Track agent installs in `~/.config/agentic-beacon/sync-state.json` (versioned schema) to enable `STALE` detection in `abc delta`; handle warehouse path changes with a relink-prompt TUI.
**Input**: `_get_warehouse_head_sha()` helper already in `cli.py`.
**Output**: `~/.config/agentic-beacon/sync-state.json` read/write helpers available; relink-prompt fires when warehouse path has changed; sync-state updated after each successful agent install.
**Validation**: Unit tests pass; state file created with correct `version: 1` schema; relink-prompt fires on simulated warehouse move.

- [ ] 4.1 Add `_read_global_sync_state() -> dict` and `_write_global_sync_state(state: dict)` helpers in `cli.py`; state file at `~/.config/agentic-beacon/sync-state.json`; create dir lazily; schema includes top-level `"version": 1`
  - **TDD Test Cases (write these first):**
    - TC1: File does not exist → `_read_global_sync_state()` returns `{}`
    - TC2: File exists with valid JSON including `version` field → returns parsed dict
    - TC3: `_write_global_sync_state()` with new data → file created with `"version": 1` at top level
    - TC4: `_write_global_sync_state()` overwrites existing → file updated, `version` preserved
    - TC5: File exists with unknown `version` value → reader warns and returns `{}` (does not crash)
    - TC6: File exists with invalid (non-parseable) JSON → reader warns and returns `{}` (does not crash)

- [ ] 4.2 Add `_write_agent_sync_state(warehouse_path: Path, relative_path: str, content_hash: str) -> None` helper; reads current state, upserts the entry keyed by `str(warehouse_path)` and `relative_path`, writes back; entry contains `content_hash`, `warehouse_head` (from `_get_warehouse_head_sha()`), `installed_at` ISO timestamp

- [ ] 4.3 Add `_relink_global_sync_state(current_warehouse_path: Path) -> bool` helper: when no entry exists for `current_warehouse_path` but another entry's warehouse directory name matches, prompt the user to confirm relink; if confirmed, rename the key in sync-state and return `True`; if declined or no match found, return `False`
  - **TDD Test Cases (write these first):**
    - TC1: No state file → no prompt, returns `False`
    - TC2: State file has entry for current path → no prompt, returns `False`
    - TC3: State file has entry for `/old/path/warehouse`, current path is `/new/path/warehouse` (same dir name `warehouse`) → prompt shown
    - TC4: User confirms relink → key renamed in state file, returns `True`
    - TC5: User declines → state file unchanged, returns `False`
    - TC6: Multiple old paths with same dir name → prompt shows all candidates, user picks one

- [ ] 4.4 Write unit tests for sync state read/write covering TC1–TC6 from task 4.1

- [ ] 4.5 Write unit tests for relink-prompt covering TC1–TC6 from task 4.3

## 5. Sync/Install Soft Block

**Goal**: Add warn + y/N soft block to `abc sync` and `abc install` whenever content differs; non-interactive mode fails hard without explicit flags.
**Input**: Existing `SyncEngine.copy_file()` and `install_artifact()` flows; existing `--preserve` on `abc sync`.
**Output**: Any content-differing overwrite preceded by a warning listing all conflicting files and a single y/N prompt; `--force` bypasses; non-interactive exits 1; `beacon.yaml` NOT updated when user responds N.
**Validation**: `pytest tests/ -v -k soft_block` passes; manual test of `abc sync` with modified file shows prompt.

- [ ] 5.1 Promote `SyncEngine._files_identical()` to public: rename to `files_identical()` in `sync.py`; update all internal callers
  - **TDD Test Cases (write these first):**
    - TC1: Two identical files → returns `True`
    - TC2: Two different files → returns `False`
    - TC3: Public method accessible as `engine.files_identical(f1, f2)`

- [ ] 5.2 Add `classify_conflicts(artifact_paths: list[str]) -> list[str]` public method to `SyncEngine`; iterates paths, calls `files_identical()` for paths where both source and dest exist, returns list of conflicting relative paths
  - **TDD Test Cases (write these first):**
    - TC1: All files identical → empty list
    - TC2: One file differs → list with that path
    - TC3: File missing locally (fresh) → not included (not a conflict)
    - TC4: Mixed — some identical, some differ, some missing → only differing returned

- [ ] 5.3 Add soft-block pre-check to `abc sync` CLI handler: call `engine.classify_conflicts()`, if non-empty and interactive → warn + y/N; if non-empty and non-interactive and no `--force`/`--preserve` → exit 1
  - **TDD Test Cases (write these first):**
    - TC1: No conflicts → proceeds without prompt
    - TC2: Conflicts, interactive, `y` → proceeds with overwrite
    - TC3: Conflicts, interactive, `N` → exits 0, no files written
    - TC4: Conflicts, non-interactive, no flags → exits 1 with conflict list
    - TC5: Conflicts, `--preserve` → skips conflicting files, no prompt
    - TC6: Conflicts, `--force` → overwrites without prompt
    - TC7: `--force` and `--preserve` together → exits 1 with mutual-exclusion error

- [ ] 5.4 Apply same soft-block pre-check to `abc install` CLI handler for all artifact types (knowledge, contexts, skills); gate `_update_beacon_yaml()` so it is only called when `copied > 0` (at least one file was successfully written, not skipped or preserved)

- [ ] 5.5 Apply soft-block pre-check to skill live-dir wiring: before `_wire_skills_post_sync()` writes to `.opencode/skills/<name>/SKILL.md` or `.claude/skills/<name>/SKILL.md`, check if content differs from existing file; if it does, include those paths in the same batch soft-block prompt as the artifact copy; if user responds N (or `--preserve`), skip the wiring write as well
  - **TDD Test Cases (write these first):**
    - TC1: Skill wiring target does not exist → writes without prompt
    - TC2: Skill wiring target identical → skips silently (not a conflict)
    - TC3: Skill wiring target differs, interactive, `y` → overwrites
    - TC4: Skill wiring target differs, `--preserve` → skips silently
    - TC5: Skill wiring target differs, `--force` → overwrites without prompt

- [ ] 5.6 Add `--force` flag to `abc sync` Click command

- [ ] 5.7 Confirm `_install_bundled_skills_globally()` has NO soft-block check — always overwrites; add inline comment: `# Bundled skills are abc-package-managed — not user content; exempt from soft block`

- [ ] 5.8 Write unit tests for `classify_conflicts()` covering TC1–TC4

- [ ] 5.9 Write integration tests for `abc sync` soft block covering TC1–TC7

- [ ] 5.10 Write unit tests for skill wiring soft-block covering TC1–TC5

## 6. Global Agent Install

**Goal**: Route `abc install agents/<name>.md` to global agent directories with soft-block conflict detection and sync-state tracking.
**Input**: `_detect_agents_global()` (Phase 3), `_write_agent_sync_state()` (Phase 4), `classify_conflicts()` (Phase 5); warehouse with `agents/` directory.
**Output**: `abc install agents/<name>.md` installs to global dirs with y/N prompt on content conflict; sync-state updated on write; `beacon.yaml` unchanged; `beacon.yaml` NOT updated when user responds N.
**Validation**: Integration tests pass; files in correct global dirs; sync-state populated; no beacon.yaml mutation.

- [ ] 6.1 Add `_install_agent_global(agent: str, agent_name: str, content: str) -> bool` helper in `cli.py`; creates parent dirs, writes file, returns `True` if written, `False` if identical content (skipped) — no conflict logic here; conflict is handled at `install_artifact()` level by the soft-block pre-check
  - **TDD Test Cases (write these first):**
    - TC1: Target file does not exist → writes file, returns `True`
    - TC2: Target file exists with identical content → skips, returns `False`
    - TC3: Target file exists with different content → overwrites (caller already confirmed), returns `True`
    - TC4: Parent dir does not exist → auto-creates, writes file, returns `True`
    - TC5: `agent="opencode"` → resolves to `~/.config/opencode/agents/<name>.md`
    - TC6: `agent="claudecode"` → resolves to `~/.claude/agents/<name>.md`

- [ ] 6.2 Add `agents` branch to `install_artifact()` in `cli.py`:
    - Call `_relink_global_sync_state()` (Phase 4) first
    - Run soft-block pre-check via `classify_conflicts()` against global agent dirs
    - Call `_install_agent_global()` for each detected tool
    - Call `_write_agent_sync_state()` (Phase 4) after each successful write
    - Print per-tool results
    - Do NOT call `_update_beacon_yaml()` (agents are never added to `beacon.yaml`)

- [ ] 6.3 Write unit tests for `_install_agent_global()` covering TC1–TC6

- [ ] 6.4 Write integration test for `abc install agents/<name>.md` end-to-end
  - **TDD Test Cases (write these first):**
    - TC1: Both tools detected, fresh install → files in both global dirs, sync-state populated, exit 0
    - TC2: No tools detected → warning printed, no files written, exit 0
    - TC3: `beacon.yaml` exists → unchanged after install
    - TC4: Content identical → no-op, sync-state NOT updated, exit 0
    - TC5: Content differs, interactive, user confirms `y` → file overwritten, sync-state updated
    - TC6: Content differs, `--force` → file overwritten without prompt, sync-state updated
    - TC7: Content differs, `--preserve` → file skipped without prompt, sync-state NOT updated
    - TC8: Content differs, non-interactive, no flags → exit 1, no files written, sync-state unchanged

## 7. Delta: Global Agent Comparison

**Goal**: Extend `abc delta` to include per-tool MISSING/IN SYNC/MODIFIED/STALE status for all `agents/` warehouse files.
**Input**: `DeltaComparator` with existing `_skill_live_path` / `skills_paths` pattern; sync-state helpers from Phase 4.
**Output**: `abc delta` shows per-tool agent rows alongside existing artifact rows; STALE displayed when installed content is current but warehouse HEAD has since moved on.
**Validation**: Unit tests pass; `abc delta` output correct for all five status scenarios.

- [ ] 7.1 Add `DeltaStatus.STALE` to the `DeltaStatus` enum in `delta.py`; add a comment in the priority map in `_compare_skill_file()` that STALE is not a rollup status — it is enriched post-comparison at the CLI layer and must not be added to the priority map
  - **TDD Test Cases (write these first):**
    - TC1: `DeltaStatus.STALE` is a valid enum member
    - TC2: Priority map in `_compare_skill_file()` does not reference `STALE`

- [ ] 7.2 Add `_agent_live_path(agent: str, relative_path: str) -> Path` to `DeltaComparator` in `delta.py`
  - **TDD Test Cases (write these first):**
    - TC1: `agent="opencode"`, `"agents/code-reviewer.md"` → `~/.config/opencode/agents/code-reviewer.md`
    - TC2: `agent="claudecode"`, `"agents/code-reviewer.md"` → `~/.claude/agents/code-reviewer.md`
    - TC3: Nested path `"agents/sub/name.md"` → strips only `agents/` prefix

- [ ] 7.3 Add `agents_paths: dict[str, Path]` attribute to `DeltaComparator` (parallel to `skills_paths`); populated by caller

- [ ] 7.4 Add `_compare_agent_file()` method to `DeltaComparator`; performs content-hash comparison only — returns MISSING/IDENTICAL/MODIFIED per tool; does NOT read sync-state (STALE enrichment is the CLI layer's responsibility)
  - **TDD Test Cases (write these first):**
    - TC1: Global file absent → `MISSING`
    - TC2: Global file identical to warehouse → `IDENTICAL`
    - TC3: Global file differs from warehouse → `MODIFIED`
    - TC4: No tools detected (`agents_paths` empty) → empty result, no error
    - TC5: Warehouse `agents/` dir is empty → no agent rows iterated, no error

- [ ] 7.5 Route `agents/` prefix in `compare_file()` to `_compare_agent_file()`

- [ ] 7.6 Extend delta entry point to iterate `agents/` entries from warehouse dir

- [ ] 7.7 Update `abc delta` CLI handler to:
    - Call `_relink_global_sync_state()` (Phase 4) first
    - Pass `agents_paths` to `DeltaComparator`
    - After `DeltaComparator` produces results, read `~/.config/agentic-beacon/sync-state.json` and enrich any `IDENTICAL` agent result to `STALE` if `warehouse_head` in sync-state differs from the current warehouse HEAD SHA
    - Display per-tool agent rows with `STALE` tip: "Run `abc install agents/<name>` to update"
  - **TDD Test Cases (write these first):**
    - TC1: Agent file IDENTICAL, sync-state HEAD matches warehouse HEAD → displayed as `IN SYNC`
    - TC2: Agent file IDENTICAL, sync-state HEAD differs from warehouse HEAD → enriched to `STALE`
    - TC3: No sync-state entry for this agent file → no STALE enrichment, displayed as `IN SYNC`
    - TC4: Agent file MODIFIED → displayed as `MODIFIED` (sync-state not consulted)
    - TC5: Agent file MISSING → displayed as `MISSING`

- [ ] 7.8 Write unit tests for `_agent_live_path()` covering TC1–TC3

- [ ] 7.9 Write unit tests for `_compare_agent_file()` covering TC1–TC5

- [ ] 7.10 Write unit tests for STALE enrichment logic in CLI handler covering TC1–TC5

## 8. abc reset Command

**Goal**: Introduce `abc reset` as the named replacement for `abc update`; deprecate `abc update` with a hidden alias and warning.
**Input**: Existing `abc update` implementation.
**Output**: `abc reset` works identically to `abc update` plus prints overwrite count; `abc update` hidden with deprecation notice; `abc --help` shows only `abc reset`.
**Validation**: `abc reset` overwrites local modifications; `abc update` prints deprecation warning and behaves identically.

- [ ] 8.1 Add `abc reset` Click command with same force-overwrite logic as current `abc update`; add overwrite-count summary line to output
- [ ] 8.2 Mark `abc update` as `hidden=True` in Click; add deprecation warning print at start of handler; delegate to `abc reset` logic
- [ ] 8.3 Write unit tests for `abc reset`
  - **TDD Test Cases (write these first):**
    - TC1: Files differ → all overwritten, exit 0, overwrite count printed
    - TC2: Files identical → no overwrites, "all up to date" message
    - TC3: `abc update` invoked → deprecation warning printed, same result as `abc reset`
    - TC4: `abc reset` does not prompt even when files differ (exempt from soft block)

## 9. Contribute No-op Detection

**Goal**: Confirm existing no-op contribute detection works correctly and that agents are correctly excluded from contribute scope.
**Input**: Existing `_contribute_all()` and `_contribute_single()` in `cli.py` (no-op exits already present).
**Output**: `abc contribute` exits 0 with "nothing to contribute" when all project artifacts match warehouse; agents (globally installed, not project-synced) are never treated as contributable items even if their warehouse copy has changed.
**Validation**: Unit tests confirm no git operations when nothing differs; agent-scope exclusion verified.

- [ ] 9.1 Verify existing no-op detection in `_contribute_all()` and `_contribute_single()` exits cleanly; add explicit test confirming agents are excluded from contribute scope (agents are globally installed — `abc contribute` must not attempt to contribute them even if warehouse `agents/` files differ from globally installed copies)
  - **TDD Test Cases (write these first):**
    - TC1: All project artifacts identical → "Nothing to contribute" printed, exit 0, no branch created
    - TC2: At least one project artifact differs → proceeds to normal contribute flow
    - TC3: Artifacts dir missing or empty → "Nothing to contribute — run 'abc sync' first", exit 0
    - TC4: Warehouse `agents/` files differ from global installs → `abc contribute` ignores them, exits 0 with "Nothing to contribute" (agents are not in contribute scope)

## 10. Install Flags

**Goal**: Add `--preserve` and `--force` to `abc install` for parity with `abc sync`; ensure mutual exclusion.
**Input**: Existing `abc install` Click command without these flags; soft-block infrastructure from Phase 5.
**Output**: `abc install --preserve` skips conflicts; `abc install --force` overwrites without prompt; both passed together → error.
**Validation**: Unit tests for each flag combination pass.

- [ ] 10.1 Add `--preserve` Click option to `abc install` command
- [ ] 10.2 Add `--force` Click option to `abc install` command
- [ ] 10.3 Add mutual-exclusion guard: if both `--force` and `--preserve` set → exit 1 with error message
- [ ] 10.4 Write unit tests for flag behaviour
  - **TDD Test Cases (write these first):**
    - TC1: `--preserve`, file differs → skipped, no prompt
    - TC2: `--force`, file differs → overwritten, no prompt
    - TC3: `--force` + `--preserve` → exits 1 with mutual-exclusion error
    - TC4: No flags, file differs, interactive → soft block prompt shown (delegates to Phase 5 infrastructure)

## 11. Tests and Docs

**Goal**: Final validation, documentation, and happy-path verification before PR.
**Input**: All implementation complete across phases 1–10.
**Output**: Full `pytest` run exits 0; docs updated; happy path confirmed in real shell.
**Validation**: `pytest` exits 0 with no failures; all commands work correctly end-to-end.

- [ ] 11.1 Add test asserting `examples/sample-warehouse/agents/README.md` content matches `data/templates/agents/README.md`
  - **TDD Test Cases:**
    - TC1: Both files exist, content identical → passes
    - TC2: Content differs → fails with diff (catches template drift)

- [ ] 11.2 Update `abc warehouse init` and `abc install` documentation / guides for `agents/` workflow, new flags, `abc reset`, `abc warehouse list agents`, and `abc list agents`

- [ ] 11.3 Run full test suite: `uv sync --group dev && pytest tests/ -v --tb=short`
  - **Expected Output**: All tests pass, exit code 0, zero failures

- [ ] 11.4 Verify happy path end-to-end (steps marked **[auto]** can be covered by integration tests; steps marked **[manual]** require a real shell):
  - **[manual]** `abc warehouse init` → `agents/` dir created; `TEMPLATE_FILES` checksum covers `agents/README.md`
  - **[manual]** `abc warehouse connect` on warehouse with `agents/` → validates successfully
  - **[manual]** `abc warehouse list` → agents section shown
  - **[auto]** `abc install agents/test-agent.md` → global dirs written; `sync-state.json` created with `"version": 1` and correct keys
  - **[auto]** `abc list agents` → globally installed agent shown
  - **[auto]** `abc delta` → agent row shows `IN SYNC`
  - **[auto]** Simulate warehouse HEAD advance; run `abc delta` → agent row shows `STALE`
  - **[auto]** `abc install agents/test-agent.md` again → state updated; `abc delta` returns to `IN SYNC`
  - **[auto]** Modify local artifact; run `abc sync` → soft block prompt appears
  - **[auto]** `abc sync --force` → overwrites without prompt
  - **[auto]** `abc contribute` with no local changes → "Nothing to contribute" exit 0
  - **[auto]** `abc reset` → force overwrites, prints overwrite count
  - **[auto]** `abc update` → deprecation warning + same result as `abc reset`
  - **[manual]** Simulate warehouse path change (rename dir) → relink-prompt TUI fires on next `abc install` or `abc delta`
