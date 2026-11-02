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
| `agentic-beacon` | `~/Code/oss/agentic-beacon` | `feat/agents-md-native-wiring` | Code changes — wiring, doctor, setup/sync CLI, tests, docs |
<!-- opsx:repos-table:end -->

## 1. Reconcile into AGENTS.md with CLAUDE.md migration

<!-- opsx:phase-summary:1:begin -->
**Goal**: Make the root AGENTS.md the reconcile target and migrate beacon-owned imports out of CLAUDE.md (D1-D7).
**Input**: origin/main @ 85b875a; wiring.py reconciles CLAUDE.md.
**Output**: reconcile_context_references writes AGENTS.md, migrates and deletes thin CLAUDE.md files, and reports deleted/left paths.
**Validation**: pytest libs/beacon/tests/unit/test_context_reference_reconcile.py passes.
<!-- opsx:phase-summary:1:end -->


- [ ] 1.1 In `domains/setup/wiring.py`, add two fields with empty-tuple defaults to
      `ReferenceReconcileResult`: `claude_md_deleted` and `claude_md_left` (D7). Keep `__bool__`
      as `added or removed`.
- [ ] 1.2 Rename `_reconcile_claude_md` to `_reconcile_agents_md` and target the root `AGENTS.md`
      (D1, D2). Remove `_resolve_claude_md`. Keep the ownership, blank-collapse and sorted-append
      logic unchanged.
- [ ] 1.3 Add the migration step inside `_reconcile_agents_md` for `./CLAUDE.md` and
      `./.claude/CLAUDE.md` (D4): strip owned lines, apply the delete test (D5), delete or write
      back, record deleted/left paths. Skip a `CLAUDE.md` that resolves to the same file as
      `AGENTS.md` (D6). Create `AGENTS.md` when it is missing and owned lines were found (D3).
      Write and delete nothing under `dry_run`.
<!-- opsx:tdd:1.3:begin -->
  - **Input**: pytest libs/beacon/tests/unit/test_context_reference_reconcile.py -v
  - **Expected Output**: All migration cases pass; AGENTS.md holds the sorted desired @-imports; thin CLAUDE.md files are gone
  - **Validation**: Zero failed tests; a mutant that skips the delete test (D5) makes at least one test fail
  - **TDD Test Cases (write these first):**
    - TC1: ./CLAUDE.md = '@AGENTS.md\n@.agentic-beacon/artifacts/contexts/a.md\n', AGENTS.md exists → CLAUDE.md deleted, AGENTS.md ends with '@.agentic-beacon/artifacts/contexts/a.md', claude_md_deleted == ('CLAUDE.md',)
    - TC2: CLAUDE.md = '<!-- note -->\n\n@./AGENTS.md\n<!--\nmulti\n-->\n' + owned line → deleted (HTML comments, blanks and @./AGENTS.md are trivial, D5)
    - TC3: CLAUDE.md = '# Title\n@AGENTS.md\n' + owned line → kept, owned line stripped, '# Title' and '@AGENTS.md' preserved, claude_md_left == ('CLAUDE.md',)
    - TC4: .claude/CLAUDE.md holds only owned lines and @AGENTS.md → deleted; ./CLAUDE.md absent is fine
    - TC5: AGENTS.md missing, CLAUDE.md holds an owned line → AGENTS.md created with the desired set (D3)
    - TC6: AGENTS.md missing, no CLAUDE.md → no AGENTS.md created, result empty (D3)
    - TC7: CLAUDE.md is a symlink to AGENTS.md → symlink untouched, AGENTS.md reconciled once, no owned line lost (D6)
    - TC8: dry_run=True with a thin CLAUDE.md → no file written or deleted; result reports the pending change
    - TC9: second run after migration → result empty and AGENTS.md byte-identical (idempotent)
    - TC10: CLAUDE.md with no owned lines and other content → file byte-identical, reported as left
<!-- opsx:tdd:1.3:end -->
- [ ] 1.4 Make `reconcile_context_references` call `_reconcile_agents_md` and carry
      `claude_md_deleted` / `claude_md_left` through to its result.
- [ ] 1.5 Update `tests/unit/test_context_reference_reconcile.py`: retarget the existing
      `_reconcile_claude_md` cases to `_reconcile_agents_md`, and cover: a thin `CLAUDE.md`
      (`@AGENTS.md`, blanks, an HTML comment) is deleted and its imports land in `AGENTS.md`; a
      `CLAUDE.md` with a heading is kept, stripped and reported as left; `.claude/CLAUDE.md` is
      migrated; a missing `AGENTS.md` is created only when a `CLAUDE.md` held owned lines; a
      `CLAUDE.md` symlinked to `AGENTS.md` is untouched; `dry_run` writes and deletes nothing;
      a second run is a no-op.
<!-- opsx:tdd:1.5:begin -->
  - **Input**: pytest libs/beacon/tests/unit/test_context_reference_reconcile.py -v
  - **Expected Output**: No test references _reconcile_claude_md; all cases pass
  - **Validation**: grep -c _reconcile_claude_md libs/beacon/tests prints 0; zero failed tests
<!-- opsx:tdd:1.5:end -->

## 2. Setup, sync and orchestrator retarget

<!-- opsx:phase-summary:2:begin -->
**Goal**: Stop every command from creating CLAUDE.md and surface a left CLAUDE.md in sync output (D7, D10, D11, D14).
**Input**: Phase 1 reconcile in place.
**Output**: abc setup and first-time sync create AGENTS.md; dead Claude helpers removed.
**Validation**: Setup, sync and e2e tests pass; git grep init_claude_md returns nothing.
<!-- opsx:phase-summary:2:end -->


- [ ] 2.1 Replace `init_claude_md` with `init_agents_md` and rename `SetupResult.claude_created`
      to `agents_md_created` (D10). Update `setup_project`.
- [ ] 2.2 Update `cli/setup.py` to print "Initialized AGENTS.md" and `cli/sync.py` to import and
      call `init_agents_md` (D10).
- [ ] 2.3 In `domains/distribution/orchestrator.py`, base `has_claude` on the root `AGENTS.md`,
      change both wiring hints to name `AGENTS.md` (D11), append a `wiring_notes` entry for each
      `claude_md_left` path and log each `claude_md_deleted` path (D7).
- [ ] 2.4 Delete `wire_contexts_claudecode` and `unwire_context_claudecode` and their tests in
      `tests/integration/test_sync_wiring.py` (D14). Update the `unwire_pruned_artifacts`
      docstring and the comment at `domains/adoption/apply.py` L401 to say `AGENTS.md`.
- [ ] 2.5 Update `tests/unit/domains/setup/test_setup_opencode_init.py` and the sync/e2e
      integration tests that assert on `CLAUDE.md`: `abc setup` creates `AGENTS.md` and no
      `CLAUDE.md`; `abc sync` wires imports into `AGENTS.md`; de-adopting a context removes its
      import from `AGENTS.md` and keeps non-owned lines; a left `CLAUDE.md` produces the sync note.
<!-- opsx:tdd:2.5:begin -->
  - **Input**: pytest libs/beacon/tests/unit/domains/setup/test_setup_opencode_init.py pytest libs/beacon/tests/integration -v
  - **Expected Output**: Setup and sync tests assert AGENTS.md wiring; no test expects a created CLAUDE.md
  - **Validation**: Zero failed tests
  - **TDD Test Cases (write these first):**
    - TC1: abc setup in an empty project → AGENTS.md exists, CLAUDE.md does not, output says 'Initialized AGENTS.md'
    - TC2: abc setup when AGENTS.md exists with content → content unchanged, no 'Initialized' line
    - TC3: abc sync with one adopted context and an existing AGENTS.md → '@.agentic-beacon/artifacts/contexts/<name>.md' appended
    - TC4: de-adopt that context and sync → import removed, user-authored lines in AGENTS.md preserved
    - TC5: sync with a CLAUDE.md holding a heading → sync output contains the manual-wiring note naming CLAUDE.md
<!-- opsx:tdd:2.5:end -->

## 3. Doctor checks

<!-- opsx:phase-summary:3:begin -->
**Goal**: Check AGENTS.md imports and report every CLAUDE.md that hides AGENTS.md (D8, D9).
**Input**: Phases 1-2 done.
**Output**: abc doctor checks AGENTS.md and reports shadowing files in the project and ancestors.
**Validation**: test_diagnostics.py and test_doctor_command.py pass.
<!-- opsx:phase-summary:3:end -->


- [ ] 3.1 In `domains/setup/diagnostics.py`, rename `_check_claude_md` to `_check_atpath_file` and
      make `_check_path_references` check the root `AGENTS.md` instead of the `CLAUDE.md` files
      (D9). Update the module docstring and the `repair_reference_drift` docstring.
- [ ] 3.2 Add `_check_claude_md_shadowing(project_root, home=None)` and call it from
      `run_project_health_checks` (D8). Report each `CLAUDE.md`, `CLAUDE.local.md` and
      `.claude/CLAUDE.md` in the project root and every ancestor as an error naming the path,
      skipping candidates under `home / ".claude"`.
<!-- opsx:tdd:3.2:begin -->
  - **Input**: pytest libs/beacon/tests/unit/domains/setup/test_diagnostics.py -v
  - **Expected Output**: Each shadowing file yields one error DoctorIssue whose message names its path
  - **Validation**: Zero failed tests; files under home/.claude are never reported
  - **TDD Test Cases (write these first):**
    - TC1: project_root/CLAUDE.md exists → one error naming it
    - TC2: parent/CLAUDE.local.md exists above project_root → one error naming it
    - TC3: grandparent/.claude/CLAUDE.md exists → one error naming it
    - TC4: home=tmp/home, tmp/home/.claude/CLAUDE.md exists and project is under tmp/home → not reported
    - TC5: tmp/home/CLAUDE.md exists (home dir itself, not .claude) → reported (D8)
    - TC6: no shadowing files in the tree → empty list
<!-- opsx:tdd:3.2:end -->
- [ ] 3.3 Update `tests/unit/domains/setup/test_diagnostics.py` and
      `tests/integration/test_doctor_command.py`: move the `@` import cases from `CLAUDE.md` to
      `AGENTS.md`; cover a project `CLAUDE.md`, an ancestor `CLAUDE.local.md`, an ancestor
      `.claude/CLAUDE.md`, and a `home/.claude/CLAUDE.md` that is not reported. Keep clean-run
      tests independent of the host's ancestors (R2).
<!-- opsx:tdd:3.3:begin -->
  - **Input**: pytest libs/beacon/tests/unit/domains/setup/test_diagnostics.py pytest libs/beacon/tests/integration/test_doctor_command.py -v
  - **Expected Output**: Import-integrity cases run against AGENTS.md; clean-run tests pass regardless of host ancestors
  - **Validation**: Zero failed tests
<!-- opsx:tdd:3.3:end -->

## 4. Remaining references

<!-- opsx:phase-summary:4:begin -->
**Goal**: Retarget the last CLAUDE.md references in code and docs (D12, D13, D15).
**Input**: Phases 1-3 done.
**Output**: Only migration, delete-test and doctor code still name CLAUDE.md; docs describe AGENTS.md wiring.
**Validation**: git grep -n 'CLAUDE.md' -- libs/beacon/src matches only D4/D5/D8 code.
<!-- opsx:phase-summary:4:end -->


- [ ] 4.1 Replace `"CLAUDE.md"` with `"AGENTS.md"` in `TRACKED_ON_PURPOSE` in `core/gitignore.py`
      (D13) and update any gitignore test that names it.
- [ ] 4.2 Change `detect_agents` in `domains/artifact/agent.py` to detect `claudecode` from
      `.claude/` or `AGENTS.md` (D12), and update the docstring of `detect_agent_targets` and
      `tests/unit/test_detect_agent_targets.py` where they name `CLAUDE.md`.
- [ ] 4.3 Run `git grep -n 'CLAUDE.md' -- libs/beacon/src` and confirm every remaining match is
      the migration (D4), the delete test (D5) or the doctor check (D8).
- [ ] 4.4 Update `README.md` and the `site-docs/` pages that describe beacon wiring `CLAUDE.md`
      (D15).

## 5. Verification

<!-- opsx:phase-summary:5:begin -->
**Goal**: Prove the change with the full suite and a real CLI run.
**Input**: Phases 1-4 done.
**Output**: Green suite and a verified happy path.
**Validation**: pytest and pre-commit exit 0; happy-path run matches 5.2.
<!-- opsx:phase-summary:5:end -->


- [ ] 5.1 Run `pytest` from the repo root and `pre-commit run --all-files`; both pass.
<!-- opsx:tdd:5.1:begin -->
  - **Input**: pytest && pre-commit run --all-files (from repo root)
  - **Expected Output**: Exit 0 for both; no files modified by hooks
  - **Validation**: Zero failed tests; pre-commit reports all hooks Passed
<!-- opsx:tdd:5.1:end -->
- [ ] 5.2 Happy path in a scratch project: `abc setup` creates `AGENTS.md` and no `CLAUDE.md`;
      `abc sync` with one context writes its import into `AGENTS.md`; a pre-existing thin
      `CLAUDE.md` is deleted; `abc doctor` reports a `CLAUDE.md` placed in a parent directory.
<!-- opsx:tdd:5.2:begin -->
  - **Input**: Scratch dir with a connected test warehouse: .venv/bin/abc setup; add one context to beacon.yaml; .venv/bin/abc sync; then write a thin CLAUDE.md, sync again; then write ../CLAUDE.md and run .venv/bin/abc doctor
  - **Expected Output**: AGENTS.md holds the context import; thin CLAUDE.md removed; doctor prints an error naming ../CLAUDE.md
  - **Validation**: ls shows no CLAUDE.md in the project; doctor exits non-zero with the shadowing error
<!-- opsx:tdd:5.2:end -->

## 6. Ops follow-up

<!-- opsx:phase-summary:6:begin -->
**Goal**: Keep the declared ops follow-up ticket accurate against what merged.
**Input**: PR merged.
**Output**: Ops ticket left, corrected, or closed with a reason.
**Validation**: The ops ticket's steps match design.md Migration Plan and the merged code.
<!-- opsx:phase-summary:6:end -->


- [ ] 6.1 **[OPS]** Verify the ops follow-up ticket declared by the plan run ("Upgrade abc on the hosts
      and remove CLAUDE.md from beacon projects after AB-106") still matches what was built and
      merged, then take exactly one of: leave it as filed; correct its steps in place; or close it
      with a reason if implementation made it unnecessary.

<!-- opsx:metadata:begin -->
---

## Enhancement Metadata

**Enhanced**: 2026-11-02
**Methodology**: Spec-Driven Development + TDD
**Enhancements Applied**:
- TDD Workflow Header
- Repositories & Branches table
- Phase summaries (Goal/Input/Output/Validation)
- Task-level TDD criteria on 7 task(s)
- 21 test case(s) across complex tasks
- 0 task(s) flagged [MANUAL] (blocking pause)
- 0 task(s) flagged [MANUAL-DEFER] (non-blocking)
- 1 task(s) flagged [OPS]
- 0 task(s) routed to Cross-Repo Follow-ups

**Status**: Ready for implementation.
<!-- opsx:metadata:end -->
