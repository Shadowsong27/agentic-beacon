# Tasks — Context-reference reconciliation (AB-96)

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
| `agentic-beacon` | `~/Code/oss/agentic-beacon` | `openspec/reconcile-context-references` | Code changes — context-reference reconciler in domains/setup/wiring.py, rewiring sync + adopt through it, retiring the append-only wiring / prune-gated context unwire, doctor --fix reference repair, and full unit/integration coverage + docs |
<!-- opsx:repos-table:end -->


## 1. The reconciler (`domains/setup/wiring.py`)

<!-- opsx:phase-summary:1:begin -->
**Goal**: Build the single wholesale reconciler that brings CLAUDE.md @-includes and opencode.json instructions to exactly the desired context-reference set, scoped to the .agentic-beacon/artifacts/ namespace, idempotent and dry-run-aware.
**Input**: Existing append-only wire_contexts_opencode / wire_contexts_claudecode and the prune-gated unwire_pruned_artifacts in domains/setup/wiring.py.
**Output**: wiring.py exposes ARTIFACT_REF_PREFIX, desired_context_refs, _reconcile_opencode_json, _reconcile_claude_md, and reconcile_context_references -> ReferenceReconcileResult; the context branch of unwire_pruned_artifacts is removed.
**Validation**: pytest tests/unit/test_context_reference_reconcile.py passes; non-artifact lines/keys always preserved; idempotent re-run is a no-op.
<!-- opsx:phase-summary:1:end -->


- [x] 1.1 Add `ARTIFACT_REF_PREFIX = ".agentic-beacon/artifacts/"` and `desired_context_refs(effective_contexts)` returning the sorted desired reference paths for the effective context set.
<!-- opsx:tdd:1.1:begin -->
  - **Input**: pytest tests/unit/test_context_reference_reconcile.py -k desired_refs -v
  - **Expected Output**: desired_context_refs({'python-standards','beacon-ops'}) == ['.agentic-beacon/artifacts/contexts/beacon-ops.md', '.agentic-beacon/artifacts/contexts/python-standards.md'] (sorted).
  - **Validation**: Prefix and .md suffix correct; sorted; empty set -> [].
  - **TDD Test Cases (write these first):**
    - TC1: two context names -> two sorted `.agentic-beacon/artifacts/contexts/<name>.md` paths
    - TC2: empty effective set -> empty list
    - TC3: names already containing dots/hyphens map to `<name>.md` unchanged
<!-- opsx:tdd:1.1:end -->
- [x] 1.2 Implement `_reconcile_opencode_json(project_root, desired_refs)`: partition `instructions` into Beacon-owned (prefix match) vs kept; add missing desired refs, remove departed owned refs, preserve `$schema`, user entries, and order; re-serialize as `json.dumps(data, indent=2) + "\n"`; write only on change. Return added/removed.
<!-- opsx:tdd:1.2:begin -->
  - **Input**: pytest tests/unit/test_context_reference_reconcile.py -k opencode -v
  - **Expected Output**: instructions equals kept-entries + desired context refs; $schema and user entries preserved; removed = owned-not-desired, added = desired-not-owned; re-serialized with indent=2 + trailing newline; no write when unchanged.
  - **Validation**: Only `.agentic-beacon/artifacts/`-prefixed entries are managed; order of kept entries stable; JSON stays valid.
  - **TDD Test Cases (write these first):**
    - TC1: instructions has an owned ref not in desired -> removed; returned removed lists it
    - TC2: desired ref missing from instructions -> appended; returned added lists it
    - TC3: $schema key + user entry 'docs/house-style.md' present -> both preserved, order stable
    - TC4: instructions already == kept + desired -> file bytes unchanged (no write)
    - TC5: empty desired set -> all owned refs removed, non-owned entries + $schema preserved
    - TC6: output re-serialized with 2-space indent and a single trailing newline
    - TC7: no opencode.json present -> no-op, empty result
<!-- opsx:tdd:1.2:end -->
- [x] 1.3 Implement `_reconcile_claude_md(project_root, desired_refs)`: manage only `@<path>` lines under the artifact prefix; add missing desired refs (existing blank-line separator convention), remove departed owned lines (and any orphaned blank pair), preserve all other lines verbatim; write only on change. Return added/removed.
<!-- opsx:tdd:1.3:begin -->
  - **Input**: pytest tests/unit/test_context_reference_reconcile.py -k claude_md -v
  - **Expected Output**: @-include lines under the artifact prefix reconciled to desired; @AGENTS.md and other non-artifact lines preserved byte-for-byte; missing desired refs appended with existing separator convention; departed owned lines removed; no write when unchanged.
  - **Validation**: A line is owned iff stripped form is `@<path>` with path under `.agentic-beacon/artifacts/`; blank-line structure preserved.
  - **TDD Test Cases (write these first):**
    - TC1: owned @-include not in desired -> line removed; @AGENTS.md untouched
    - TC2: desired ref absent -> appended as `@.agentic-beacon/artifacts/contexts/<name>.md` with blank-line separator
    - TC3: file with @AGENTS.md + @docs/x.md + artifact includes -> only artifact includes change, others in place
    - TC4: already-matching file -> bytes unchanged (no write)
    - TC5: empty desired set -> all owned includes removed, non-artifact lines preserved
    - TC6: `.claude/CLAUDE.md` preferred over root CLAUDE.md when both exist
    - TC7: no CLAUDE.md present -> no-op, empty result
<!-- opsx:tdd:1.3:end -->
- [x] 1.4 Implement `reconcile_context_references(project_root, desired_refs, *, dry_run=False)` aggregating both file reconcilers into a `ReferenceReconcileResult(added, removed)`; under `dry_run`, compute the delta but perform no writes.
<!-- opsx:tdd:1.4:begin -->
  - **Input**: pytest tests/unit/test_context_reference_reconcile.py -k reconcile_context_references -v
  - **Expected Output**: Returns ReferenceReconcileResult with aggregated added/removed across both files; dry_run=True computes the delta but writes nothing; second run is a no-op (added and removed empty).
  - **Validation**: Idempotent; dry-run makes no filesystem writes (assert bytes/mtime unchanged).
  - **TDD Test Cases (write these first):**
    - TC1: both files drift -> aggregated added/removed spans both; both files written
    - TC2: dry_run=True -> result reports the delta but neither file is written (bytes unchanged)
    - TC3: idempotent -> second call returns empty added/removed and writes nothing
    - TC4: only one of the two files exists -> the other reconciler is a silent no-op
<!-- opsx:tdd:1.4:end -->
- [x] 1.5 Reduce `wire_contexts_opencode` / `wire_contexts_claudecode` to add-only helpers driven by the desired set (or fold into the reconciler); remove the **context branch** of `unwire_pruned_artifacts`, leaving its skill/agent branches intact.
<!-- opsx:tdd:1.5:begin -->
  - **Input**: pytest tests/unit -k 'unwire and (skill or agent)' -v ; grep -rn 'unwire_pruned_artifacts' src/
  - **Expected Output**: wire_contexts_* no longer scan the contexts/ directory to drive wiring; the context branch of unwire_pruned_artifacts is gone; its skill and agent branches still remove the right dirs/symlinks on prune.
  - **Validation**: No remaining code path wires contexts by rglob of the directory; skill/agent prune unwiring unchanged (regression).
  - **TDD Test Cases (write these first):**
    - TC1: unwire_pruned_artifacts on a pruned skill still removes .claude/.opencode skill dirs
    - TC2: unwire_pruned_artifacts on a pruned agent still removes the agent symlinks
    - TC3: unwire_pruned_artifacts on a pruned context is now a no-op there (reconcile owns it)
<!-- opsx:tdd:1.5:end -->

## 2. Wire every path to the reconciler

<!-- opsx:phase-summary:2:begin -->
**Goal**: Route abc sync and abc adopt through reconcile_context_references so add and remove are both handled without a prune confirmation.
**Input**: Phase 1 reconciler; current call sites in orchestrator.py (run_sync), adoption/apply.py, cli/sync.py.
**Output**: run_sync and the adopt accept/reject path call the reconciler; the prune-triggered context unwire is gone; cli/sync.py guidance stays coherent.
**Validation**: Integration tests: de-adopt + sync removes the reference; adopt accept adds / reject removes; dry-run writes nothing.
<!-- opsx:phase-summary:2:end -->


- [x] 2.1 `domains/distribution/orchestrator.py::run_sync` — build `desired_refs` from `effective_set.contexts` and call `reconcile_context_references` instead of the append-only `wire_contexts_*`; remove the `if summary.pruned_paths: unwire_pruned_artifacts(...)` context handling (skill/agent prune unwiring stays). Respect `dry_run`.
<!-- opsx:tdd:2.1:begin -->
  - **Input**: pytest tests/integration/test_sync_wiring.py -k 'reconcile or deadopt' -v
  - **Expected Output**: run_sync builds desired_refs from effective_set.contexts and calls reconcile_context_references; the `if summary.pruned_paths: unwire_pruned_artifacts` context handling is removed; dry_run path performs no writes.
  - **Validation**: After sync, references in both files == effective context set; de-adopt + sync removes the reference with no prune confirmation.
  - **TDD Test Cases (write these first):**
    - TC1: sync with a context removed from beacon.yaml -> its reference gone from both files (no prompt)
    - TC2: sync adding a new context -> its reference present in both files
    - TC3: sync --dry-run -> reports would-add/would-remove but writes neither file
<!-- opsx:tdd:2.1:end -->
- [x] 2.2 `domains/adoption/apply.py` — replace the append-only `wire_contexts_*` calls on the accept/reject path with `reconcile_context_references` so un-adopt/reject removes references.
<!-- opsx:tdd:2.2:begin -->
  - **Input**: pytest tests/integration/test_adopt_apply.py -k reconcile -v
  - **Expected Output**: adopt accept adds the reference; reject / un-adopt removes it — both via reconcile_context_references, not append-only wiring.
  - **Validation**: No append-only wire_contexts_* remains on the adopt path; reject removes references.
  - **TDD Test Cases (write these first):**
    - TC1: adopt-accept a context -> reference present in both files
    - TC2: un-adopt (remove from beacon.yaml) + adopt-sync -> reference removed from both files
<!-- opsx:tdd:2.2:end -->
- [x] 2.3 `cli/sync.py` — update the post-sync wiring init calls to the reconciler (keep the "wire them into your agent config" guidance path coherent).

## 3. Doctor `--fix` reference repair

<!-- opsx:phase-summary:3:begin -->
**Goal**: Make abc doctor --fix repair reference drift via the same reconciler, recording repairs in fixes_applied.
**Input**: Phase 1 reconciler; existing run_project_diagnostics + repair_gitignore_drift and the --fix plumbing in cli/diagnostics.py.
**Output**: repair_reference_drift added and called from run_project_diagnostics when --fix is set, alongside repair_gitignore_drift; repairs surfaced in the applied-fixes summary.
**Validation**: Doctor tests: broken + unmanaged references repaired by --fix; re-run clean; healthy repo not written.
<!-- opsx:phase-summary:3:end -->


- [x] 3.1 `domains/setup/diagnostics.py` — add `repair_reference_drift(project_root, beacon_manifest, warehouse_path)` that computes the effective set, builds `desired_refs`, and calls `reconcile_context_references`; return a human-readable fix line per changed file.
<!-- opsx:tdd:3.1:begin -->
  - **Input**: pytest tests/unit -k repair_reference_drift -v
  - **Expected Output**: repair_reference_drift computes the effective set, builds desired_refs, calls the reconciler, and returns a fix line per changed file; healthy repo returns [].
  - **Validation**: Reuses the same reconciler as sync; no divergent logic.
  - **TDD Test Cases (write these first):**
    - TC1: repo with a broken + an unmanaged reference -> both reconciled away, one-or-two fix lines returned
    - TC2: healthy repo -> returns [] and writes nothing
<!-- opsx:tdd:3.1:end -->
- [x] 3.2 `domains/setup/diagnostics.py::run_project_diagnostics` — when `fix` is set, call `repair_reference_drift` alongside `repair_gitignore_drift` and merge into `applied_fixes` (runs before the checks so the returned issues reflect the repaired state).
<!-- opsx:tdd:3.2:begin -->
  - **Input**: pytest tests/unit -k 'run_project_diagnostics and fix' -v
  - **Expected Output**: When fix=True, run_project_diagnostics calls repair_reference_drift alongside repair_gitignore_drift and merges both into applied_fixes; repair runs before the checks so returned issues reflect the repaired state.
  - **Validation**: applied_fixes contains both gitignore and reference repairs when both drifted; check ordering (repair-then-check) preserved.
  - **TDD Test Cases (write these first):**
    - TC1: fix=True with reference drift -> applied_fixes includes the reference repair and the re-run checks report no reference drift
    - TC2: fix=False -> no repair invoked, references untouched
<!-- opsx:tdd:3.2:end -->
- [x] 3.3 `cli/diagnostics.py` — surface reference repairs in the applied-fixes summary (reuse the existing `fixes_applied` plumbing).

## 4. Tests

<!-- opsx:phase-summary:4:begin -->
**Goal**: Lock the reconciler behavior, non-artifact preservation, the dangling/warehouse-rename case, cross-path coverage (sync + adopt), the doctor --fix loop, and the live-repo regression.
**Input**: Phases 1-3 implemented; pytest with tests/unit and tests/integration split.
**Output**: New unit + integration tests covering reconciler, dangling case, path coverage, doctor, and the linear-ops/cicd-flow regression; architecture test still green.
**Validation**: pytest tests/ green from repo root; BEACON_OFFLINE=1 respected for network-gated tests.
<!-- opsx:phase-summary:4:end -->


- [x] 4.1 Reconciler unit tests: add-missing; remove-departed; add+remove in one pass; preserve `@AGENTS.md` / user includes / `$schema` / user instructions and order; idempotent re-run (byte-equal); `opencode.json` re-serialization shape; empty-effective-set clears owned refs only.
<!-- opsx:tdd:4.1:begin -->
  - **Input**: pytest tests/unit/test_context_reference_reconcile.py -v
  - **Expected Output**: All reconciler cases pass: add-missing, remove-departed, add+remove in one pass, preserve @AGENTS.md / user includes / $schema / user instructions and order, idempotent re-run (byte-equal), opencode.json re-serialization shape, empty-effective-set clears owned refs only.
  - **Validation**: Zero failures; non-artifact preservation and idempotency explicitly asserted.
<!-- opsx:tdd:4.1:end -->
- [x] 4.2 Dangling / warehouse-rename case: an owned reference not in the effective set (file gone) is removed from both files.
<!-- opsx:tdd:4.2:begin -->
  - **Input**: pytest tests/unit/test_context_reference_reconcile.py -k dangling -v
  - **Expected Output**: An owned reference whose target no longer resolves (warehouse rename) and is absent from the effective set is removed from both CLAUDE.md and opencode.json.
  - **Validation**: Covers the exact reported broken-reference (linear-ops -> plane-ops) shape.
<!-- opsx:tdd:4.2:end -->
- [x] 4.3 Path coverage: `abc sync` after de-adopting a context removes its reference from both files; `abc adopt` accept adds, reject/un-adopt removes.
<!-- opsx:tdd:4.3:begin -->
  - **Input**: pytest tests/ -k 'reference and (sync or adopt)' -v
  - **Expected Output**: abc sync after de-adopting a context removes its reference from both files; abc adopt accept adds, reject/un-adopt removes.
  - **Validation**: Both directions covered through the real sync and adopt entry points.
<!-- opsx:tdd:4.3:end -->
- [x] 4.4 Doctor: a repo with a broken + an unmanaged reference → both flagged; `abc doctor --fix` repairs both and the re-run is clean; healthy repo → no drift, no spurious write; `fixes_applied` non-empty on repair.
<!-- opsx:tdd:4.4:begin -->
  - **Input**: pytest tests/ -k 'doctor and reference' -v
  - **Expected Output**: A repo with a broken + an unmanaged reference -> both flagged; abc doctor --fix repairs both and the re-run is clean; healthy repo -> no drift, no spurious write; fixes_applied non-empty on repair.
  - **Validation**: Covers detection, the real --fix repair loop, and the no-spurious-write guarantee.
<!-- opsx:tdd:4.4:end -->
- [x] 4.5 Regression fixture reproducing this repo's `linear-ops.md` (broken) + `cicd-flow.md` (unmanaged) condition; assert `--fix` clears both.
<!-- opsx:tdd:4.5:begin -->
  - **Input**: pytest tests/ -k regression_reference_drift -v
  - **Expected Output**: Fixture reproduces linear-ops.md (broken, target absent) + cicd-flow.md (present, undeclared) in CLAUDE.md and opencode.json; abc doctor --fix reconciles both away; a subsequent doctor reports zero broken/unmanaged references.
  - **Validation**: Mirrors the exact live-repo condition that motivated AB-96.
  - **TDD Test Cases (write these first):**
    - TC1: broken reference (linear-ops.md target missing) -> removed by --fix
    - TC2: unmanaged reference (cicd-flow.md not in beacon.yaml, not in effective set) -> removed by --fix
    - TC3: second doctor run after --fix -> no broken or unmanaged reference findings
<!-- opsx:tdd:4.5:end -->
- [x] 4.6 `tests/unit/test_architecture.py` still passes.
<!-- opsx:tdd:4.6:begin -->
  - **Input**: pytest tests/unit/test_architecture.py -v
  - **Expected Output**: Exit code 0 — the reconciler additions keep core/ importing nothing from domains/ and respect the setup-domain boundary.
  - **Validation**: Architecture boundary intact after the wiring/diagnostics changes.
<!-- opsx:tdd:4.6:end -->

## 5. Docs

<!-- opsx:phase-summary:5:begin -->
**Goal**: Document that the artifact-reference layer of CLAUDE.md / opencode.json is Beacon-managed and reconciled.
**Input**: beacon-ops.md two-tier / ownership sections (delivered via the warehouse per-project model).
**Output**: beacon-ops.md notes the reconciled reference layer and abc doctor --fix repair.
**Validation**: Manual read-through; abc warehouse lint clean on edited warehouse docs if applicable.
<!-- opsx:phase-summary:5:end -->


- [ ] 5.1 Note in `beacon-ops.md` (warehouse per-project model) that the artifact-reference layer of `CLAUDE.md` / `opencode.json` is Beacon-managed and reconciled to the effective set, and repairable via `abc doctor --fix`.

## 6. Validate & verify

<!-- opsx:phase-summary:6:begin -->
**Goal**: Prove the change end-to-end on a real scratch project, not just via unit tests.
**Input**: All prior phases complete; a scratch project + the built abc CLI.
**Output**: Verified happy path: sync reconciles references, de-adopt removes one, doctor detects induced drift, --fix repairs it.
**Validation**: pytest green; documented scratch-project walkthrough succeeds.
<!-- opsx:phase-summary:6:end -->


- [x] 6.1 `pytest` green (unit + integration) from repo root; `BEACON_OFFLINE=1` respected for network-gated integration tests.
<!-- opsx:tdd:6.1:begin -->
  - **Input**: pytest (from repo root); BEACON_OFFLINE=1 pytest -m integration when offline
  - **Expected Output**: All tests pass; no regressions in sync/adopt/doctor suites.
  - **Validation**: Zero failures, zero errors from repo root.
<!-- opsx:tdd:6.1:end -->
- [ ] 6.2 **[OPS]** Happy-path check on a scratch project: adopt/sync yields references == effective set; de-adopt a context + sync removes its reference; introduce a broken/unmanaged reference → `abc doctor` errors → `abc doctor --fix` repairs → re-run clean.
<!-- opsx:tdd:6.2:begin -->
  - **Input**: abc sync in a scratch project; de-adopt a context + sync; then hand-add a broken + unmanaged reference and run abc doctor / abc doctor --fix
  - **Expected Output**: After sync, references == effective set; de-adopt + sync removes the reference; abc doctor errors on the induced broken/unmanaged refs; abc doctor --fix repairs them and the re-run is clean.
  - **Validation**: Real CLI walkthrough matches the unit/integration expectations end-to-end.
<!-- opsx:tdd:6.2:end -->

<!-- opsx:metadata:begin -->
---

## Enhancement Metadata

**Enhanced**: 2026-07-20
**Methodology**: Spec-Driven Development + TDD
**Enhancements Applied**:
- TDD Workflow Header
- Repositories & Branches table
- Phase summaries (Goal/Input/Output/Validation)
- Task-level TDD criteria on 17 task(s)
- 36 test case(s) across complex tasks
- 0 task(s) flagged [MANUAL] (blocking pause)
- 0 task(s) flagged [MANUAL-DEFER] (non-blocking)
- 1 task(s) flagged [OPS]
- 0 task(s) routed to Cross-Repo Follow-ups

**Status**: Ready for implementation via `/opsx-apply <name>`.
<!-- opsx:metadata:end -->
