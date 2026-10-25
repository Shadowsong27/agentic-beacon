# Tasks — Managed-block gitignore engine (AB-94)

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
| `agentic-beacon` | `~/Code/oss/agentic-beacon` | `openspec/ab-94-managed-gitignore` | Code changes — managed-block gitignore engine in core/gitignore.py, rewiring sync/adopt/connect through it, retiring the conditional agent-dir helpers, doctor drift check + real --fix, and full unit/integration coverage + docs |
<!-- opsx:repos-table:end -->


## 1. Core engine (`core/gitignore.py`)

<!-- opsx:phase-summary:1:begin -->
**Goal**: Build the single cross-domain managed-block engine: marker-delimited block, wholesale regeneration, surgical migration, the two-tier entry sets, and a read-only drift diff — the source of truth every path and doctor will call.
**Input**: Existing core/gitignore.py (GitignoreManager with per-line ensure_entries); Tier B constants currently in distribution/orchestrator.py.
**Output**: core/gitignore.py exposes marker constants, TIER_A_ENTRIES / TIER_B_CLAUDE_ENTRIES / TIER_B_OPENCODE_ENTRIES / TRACKED_ON_PURPOSE, apply_managed_block, read_managed_block, apply_all_gitignores, and diff_gitignores. No imports from domains/.
**Validation**: pytest tests/unit covering the engine passes; tests/unit/test_architecture.py confirms core imports no domains.
<!-- opsx:phase-summary:1:end -->


- [x] 1.1 Add managed-block markers and entry-set constants: `TIER_A_ENTRIES` (10 unconditional lines), `TIER_B_CLAUDE_ENTRIES`, `TIER_B_OPENCODE_ENTRIES`, `TRACKED_ON_PURPOSE`.
- [x] 1.2 Implement `apply_managed_block(gitignore_path, entries)`: create/regenerate the marker-delimited block wholesale; idempotent; preserve trailing-newline shape.
<!-- opsx:tdd:1.2:begin -->
  - **Input**: pytest tests/unit/test_gitignore.py -k apply_managed_block -v
  - **Expected Output**: Exit code 0; block written between '# >>> Agentic Beacon (managed) >>>' and '# <<< Agentic Beacon (managed) <<<'; second apply with same entries leaves bytes unchanged.
  - **Validation**: Fresh-file, stale-body-regen, and idempotent-reapply cases all pass; trailing-newline shape preserved.
  - **TDD Test Cases (write these first):**
    - TC1: no .gitignore exists → file created containing exactly one managed block with all supplied entries
    - TC2: managed block present with correct body → re-apply is byte-identical (idempotent)
    - TC3: managed block present with a missing/extra/reordered entry → body regenerated to canonical set, markers unchanged, out-of-block content untouched
    - TC4: file ends without trailing newline → block appended without corrupting the preceding line; newline shape preserved
    - TC5: entries empty list → block contains only the two markers (no orphan lines)
<!-- opsx:tdd:1.2:end -->
- [x] 1.3 Implement surgical migration inside `apply_managed_block`: dedup exact managed lines from a legacy `# Agentic Beacon` region, drop the emptied bare legacy header, preserve all non-managed lines.
<!-- opsx:tdd:1.3:begin -->
  - **Input**: pytest tests/unit/test_gitignore.py -k migration -v
  - **Expected Output**: Legacy loose managed lines removed; bare '# Agentic Beacon' header dropped; non-managed lines (.legacy-migrated, sample-warehouse/, user lines) retained; managed block appended once.
  - **Validation**: No line the engine does not own is deleted; second run is a no-op.
  - **TDD Test Cases (write these first):**
    - TC1: legacy header + managed loose lines + unknown lines → managed lines deduped, unknown lines preserved in place, bare legacy header removed, block appended once
    - TC2: legacy header whose ALL following lines are managed → header removed, no empty region left behind
    - TC3: legacy header with a mix incl. scattered .claude/agents/ → agent-dir loose line deduped into the block, other lines preserved
    - TC4: already-migrated file → second run makes no change (idempotent)
    - TC5: unknown line equals a managed value only as a substring (not exact) → preserved (exact-match only)
<!-- opsx:tdd:1.3:end -->
- [x] 1.4 Implement `read_managed_block(gitignore_path)` and `apply_all_gitignores(project_root)` (Tier A always; Tier B per tool-dir existence).
<!-- opsx:tdd:1.4:begin -->
  - **Input**: pytest tests/unit/test_gitignore.py -k apply_all -v
  - **Expected Output**: Root .gitignore always gets Tier A; .claude/.gitignore written iff .claude/ exists; .opencode/.gitignore written iff .opencode/ exists; read_managed_block returns the parsed entry list or None.
  - **Validation**: Tier A unconditional; Tier B dir-gated by file location; read round-trips the written block.
  - **TDD Test Cases (write these first):**
    - TC1: project with neither tool dir → only root Tier A block written; no nested files created
    - TC2: project with .claude/ only → root Tier A + .claude/.gitignore; no .opencode/.gitignore
    - TC3: project with both tool dirs → root + both nested blocks
    - TC4: read_managed_block on a file with no markers → returns None
<!-- opsx:tdd:1.4:end -->
- [x] 1.5 Implement `diff_gitignores(project_root)` returning drift records (Tier A missing/incomplete, Tier B missing/incomplete when dir exists, tracked-on-purpose file ignored); extend the tracked-set assertion to `TRACKED_ON_PURPOSE`.
<!-- opsx:tdd:1.5:begin -->
  - **Input**: pytest tests/unit/test_gitignore.py -k diff -v
  - **Expected Output**: Returns [] for a healthy project; returns drift records identifying the specific tier/file for each defect; flags any TRACKED_ON_PURPOSE path that git would ignore.
  - **Validation**: Read-only (no writes); the reported 'Tier B present, Tier A absent' case yields a Tier-A drift record.
  - **TDD Test Cases (write these first):**
    - TC1: healthy project (both tiers correct) → empty list
    - TC2: nested .opencode/.gitignore present but root Tier A block absent → drift record naming missing Tier A
    - TC3: Tier A block present but missing warehouse-catalog.md → incomplete-Tier-A drift record
    - TC4: .claude/ exists but .claude/.gitignore missing → Tier B drift record
    - TC5: .gitignore contains a line ignoring beacon.yaml / opencode.json → tracked-set drift record
    - TC6: diff_gitignores makes no filesystem writes (assert mtime/bytes unchanged)
<!-- opsx:tdd:1.5:end -->

## 2. Wire every path to the engine

<!-- opsx:phase-summary:2:begin -->
**Goal**: Route sync, adopt-accept, and warehouse-connect through apply_all_gitignores so no path can emit one tier without the other, and delete the superseded fragmented mechanisms.
**Input**: Phase 1 engine complete; current call sites in orchestrator.py:462/546/558, adoption/apply.py:294, warehouse/connector.py:47, artifact/agent.py.
**Output**: All three wiring paths call apply_all_gitignores; CLAUDE_DIR_/OPENCODE_DIR_GITIGNORE_ENTRIES and ensure_agent_dirs_gitignored/prune_agent_dirs_gitignore_entries removed with their callers.
**Validation**: grep confirms the deleted symbols have no remaining references; path-coverage tests (Phase 4) green.
<!-- opsx:phase-summary:2:end -->


- [x] 2.1 `domains/distribution/orchestrator.py::run_sync` — replace the `ensure_entries()` + conditional agent-dir + per-tool nested-gitignore blocks with a single `apply_all_gitignores(project_root)` call; delete `CLAUDE_DIR_GITIGNORE_ENTRIES` / `OPENCODE_DIR_GITIGNORE_ENTRIES`.
- [x] 2.2 `domains/adoption/apply.py` — call `apply_all_gitignores(project_root)` on the accept path (fixes the Tier-A-skipped bug); remove the conditional `ensure_agent_dirs_gitignored` call.
<!-- opsx:tdd:2.2:begin -->
  - **Input**: pytest tests/unit -k adopt_gitignore -v (or the integration adopt test)
  - **Expected Output**: After adopt-accept that materializes .claude/ and/or .opencode/, the root .gitignore contains the Tier A managed block AND nested Tier B blocks exist.
  - **Validation**: This is the regression that would have caught the original agentic-conductor bug — Tier A must be present on the adopt path.
  - **TDD Test Cases (write these first):**
    - TC1: adopt-accept on a project with no prior .gitignore → Tier A block present after accept
    - TC2: adopt-accept that creates .opencode/ → both Tier A and .opencode/.gitignore present (no Tier-B-without-Tier-A drift)
<!-- opsx:tdd:2.2:end -->
- [x] 2.3 `domains/warehouse/connector.py` — route `connect` through `apply_all_gitignores`.
- [x] 2.4 `domains/artifact/agent.py` — remove `ensure_agent_dirs_gitignored` and `prune_agent_dirs_gitignore_entries`; update/remove their callers and imports.

## 3. Doctor check + real `--fix`

<!-- opsx:phase-summary:3:begin -->
**Goal**: Surface gitignore drift as a doctor error and make --fix actually repair it via the shared engine — Beacon's first working --fix.
**Input**: Phase 1 diff_gitignores; existing run_project_health_checks + DoctorIssue in setup/diagnostics.py and the --fix stub in cli/diagnostics.py.
**Output**: abc doctor reports Tier A / Tier B / tracked-set drift at error severity; abc doctor --fix calls apply_all_gitignores and records repairs in fixes_applied.
**Validation**: Doctor tests (Phase 4.5): drift flagged, healthy clean, --fix repairs, re-run clean.
<!-- opsx:phase-summary:3:end -->


- [x] 3.1 `domains/setup/diagnostics.py` — add a gitignore-drift check (error severity) using `diff_gitignores`; surface Tier A, Tier B, and tracked-set findings via `DoctorIssue`.
<!-- opsx:tdd:3.1:begin -->
  - **Input**: pytest tests/unit -k doctor_gitignore -v
  - **Expected Output**: run_project_health_checks returns DoctorIssue(severity='err', ...) for each drift; none for a healthy project.
  - **Validation**: Severity is error; messages identify the specific tier/file; the reported Tier-A-missing case is flagged.
  - **TDD Test Cases (write these first):**
    - TC1: drifted project → DoctorIssue with severity 'err' and a message naming the missing Tier A block
    - TC2: healthy project → no gitignore DoctorIssue emitted
    - TC3: tracked-set file ignored → error-severity DoctorIssue naming the file
<!-- opsx:tdd:3.1:end -->
- [x] 3.2 `cli/diagnostics.py` — implement real `--fix`: when drift is found and `--fix` is set, call `apply_all_gitignores` and append to `fixes_applied`.
<!-- opsx:tdd:3.2:begin -->
  - **Input**: abc doctor --fix in a drifted scratch project, then abc doctor
  - **Expected Output**: First run reports drift and prints a fix in the applied-fixes summary; second run reports no gitignore drift.
  - **Validation**: fixes_applied is non-empty on repair; repaired blocks match the engine output; re-run is clean.
  - **TDD Test Cases (write these first):**
    - TC1: drifted project + --fix → blocks repaired, fix recorded in fixes_applied, exit reflects repair
    - TC2: healthy project + --fix → no fix recorded, no spurious write
    - TC3: --fix then plain doctor → zero gitignore drift on the second run (idempotent repair)
<!-- opsx:tdd:3.2:end -->

## 4. Tests

<!-- opsx:phase-summary:4:begin -->
**Goal**: Lock the engine's behavior, the migration's non-destructiveness, the Tier B fold-in against regression, cross-path coverage (including the adopt bug), and the doctor flow.
**Input**: Phases 1–3 implemented; pytest with tests/unit and tests/integration split.
**Output**: New unit + integration tests covering engine, migration, Tier B lock, path coverage, doctor; architecture test still green.
**Validation**: pytest tests/ green from repo root; BEACON_OFFLINE=1 respected for network-gated integration tests.
<!-- opsx:phase-summary:4:end -->


- [x] 4.1 Engine unit tests: fresh-file, wholesale regen of stale body, idempotent re-apply (byte-equal), unconditional Tier A set (no tool dirs / no declared agents).
<!-- opsx:tdd:4.1:begin -->
  - **Input**: pytest tests/unit/test_gitignore.py -v
  - **Expected Output**: All engine cases pass; Tier A block contains all 10 entries even with no .claude//.opencode/ and empty agents.
  - **Validation**: Zero failures; unconditional Tier A explicitly asserted.
<!-- opsx:tdd:4.1:end -->
- [x] 4.2 Migration unit tests: dedup managed + preserve unknowns + drop bare legacy header; no-op on 2nd run; realistic mixed legacy block.
<!-- opsx:tdd:4.2:begin -->
  - **Input**: pytest tests/unit/test_gitignore.py -k migration -v
  - **Expected Output**: Realistic legacy block (like this repo's) migrates: managed lines deduped, .legacy-migrated / sample-warehouse/ preserved, header dropped; second run byte-identical.
  - **Validation**: No non-managed line lost; idempotent.
<!-- opsx:tdd:4.2:end -->
- [x] 4.3 Tier B regression lock: exact `.claude/.gitignore` / `.opencode/.gitignore` entry sets + dir-gating unchanged.
<!-- opsx:tdd:4.3:begin -->
  - **Input**: pytest tests/unit -k tier_b -v
  - **Expected Output**: .claude/.gitignore == {skills/, scheduled_tasks.lock, worktrees/}; .opencode/.gitignore == {skills/, command/, bun.lock, package.json, package-lock.json, node_modules/}; nested files only when dir exists.
  - **Validation**: Entry sets match the pre-change constants exactly (guards the fold-into-engine risk).
<!-- opsx:tdd:4.3:end -->
- [x] 4.4 Path coverage: adopt-accept writes Tier A + Tier B; sync writes both; connect routes through engine.
<!-- opsx:tdd:4.4:begin -->
  - **Input**: pytest tests/ -k 'gitignore and (adopt or sync or connect)' -v
  - **Expected Output**: Each of the three paths produces the correct Tier A + Tier B blocks; no path emits one tier without the other.
  - **Validation**: adopt path asserts Tier A present (the original bug); all three paths converge to identical block output.
<!-- opsx:tdd:4.4:end -->
- [x] 4.5 Doctor tests: Tier-A-missing-while-Tier-B-present flagged; healthy → clean; tracked-set-ignored → error; `--fix` repairs and re-run is clean.
<!-- opsx:tdd:4.5:begin -->
  - **Input**: pytest tests/ -k doctor -v
  - **Expected Output**: Drift detected at error severity for each defect; healthy project clean; --fix repairs and the re-run is clean.
  - **Validation**: Covers detection, severity, tracked-set, and the real --fix repair loop.
<!-- opsx:tdd:4.5:end -->
- [x] 4.6 `tests/unit/test_architecture.py` still passes (core imports no domains).
<!-- opsx:tdd:4.6:begin -->
  - **Input**: pytest tests/unit/test_architecture.py -v
  - **Expected Output**: Exit code 0 — core/gitignore.py (and the rest of core/) import nothing from domains/ or cli/.
  - **Validation**: Architecture boundary intact after promoting the policy into core.
<!-- opsx:tdd:4.6:end -->

## 5. Docs

<!-- opsx:phase-summary:5:begin -->
**Goal**: Bring the two-tier gitignore documentation in line with the managed-block engine and the unconditional / doctor --fix behavior.
**Input**: beacon-ops.md two-tier section and AGENTS.md references to the old per-line / conditional agent-dir behavior.
**Output**: Docs describe the marker-delimited managed block, unconditional Tier A set, and abc doctor --fix.
**Validation**: Manual read-through; abc warehouse lint clean on edited warehouse docs if applicable.
<!-- opsx:phase-summary:5:end -->


- [x] 5.1 Update `beacon-ops.md` two-tier gitignore section: managed-block markers, unconditional Tier A, doctor `--fix`. _(Done post-merge in the warehouse: hl-knowledge-market `contexts/beacon-ops.md` @ 30e3c3a — delivered via the beacon per-project model, so it is not in this repo's diff.)_
- [x] 5.2 Update `AGENTS.md` if it references the old per-line / conditional agent-dir behavior.

## 6. Validate & verify

<!-- opsx:phase-summary:6:begin -->
**Goal**: Prove the change end-to-end on a real scratch project, not just via unit tests.
**Input**: All prior phases complete; a scratch project + the built abc CLI.
**Output**: Verified happy path: adopt/sync produce correct blocks, doctor detects induced drift, --fix repairs it.
**Validation**: pytest green; documented scratch-project walkthrough succeeds.
<!-- opsx:phase-summary:6:end -->


- [x] 6.1 `pytest` green (unit + integration).
<!-- opsx:tdd:6.1:begin -->
  - **Input**: pytest (from repo root); BEACON_OFFLINE=1 pytest -m integration when offline
  - **Expected Output**: All tests pass; no regressions in existing sync/adopt/connect/doctor suites.
  - **Validation**: Zero failures, zero errors from repo root.
<!-- opsx:tdd:6.1:end -->
- [ ] 6.2 **[OPS]** Happy-path check: `abc adopt` / `abc sync` on a scratch project yields correct Tier A + Tier B blocks; `abc doctor` clean; introduce drift → `abc doctor` errors → `abc doctor --fix` repairs. _(Post-merge note: the real code paths are covered by integration tests — `tests/integration/test_adopt_apply.py`, `test_sync_wiring.py`, `tests/unit/test_doctor_gitignore.py` (all green, 1592 tests). Live scratch-CLI walkthrough deferred; shipped in 3.7.0 with the flow documented in the release notes.)_
<!-- opsx:tdd:6.2:begin -->
  - **Input**: abc warehouse init /tmp/ab94-scratch-wh && abc sync in a scratch project; then delete the Tier A block and run abc doctor / abc doctor --fix
  - **Expected Output**: Correct managed blocks after sync; abc doctor reports an error after the block is deleted; abc doctor --fix restores it and the re-run is clean.
  - **Validation**: Real CLI walkthrough matches the unit-test expectations end-to-end.
<!-- opsx:tdd:6.2:end -->

<!-- opsx:metadata:begin -->
---

## Enhancement Metadata

**Enhanced**: 2026-07-19
**Methodology**: Spec-Driven Development + TDD
**Enhancements Applied**:
- TDD Workflow Header
- Repositories & Branches table
- Phase summaries (Goal/Input/Output/Validation)
- Task-level TDD criteria on 15 task(s)
- 28 test case(s) across complex tasks
- 0 task(s) flagged [MANUAL] (blocking pause)
- 0 task(s) flagged [MANUAL-DEFER] (non-blocking)
- 1 task(s) flagged [OPS]
- 0 task(s) routed to Cross-Repo Follow-ups

**Status**: Ready for implementation via `/opsx-apply <name>`.
<!-- opsx:metadata:end -->
