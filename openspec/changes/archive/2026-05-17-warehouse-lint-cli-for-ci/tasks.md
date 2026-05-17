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
| `agentic-beacon` | `~/Code/oss/agentic-beacon` | `warehouse-lint-cli-for-ci` | Code changes — ships the `abc warehouse lint` CLI command, lint orchestrator module, unit + integration tests, and docs. All tasks in phases 1–14 land here. |
| `hl-knowledge-market` | `~/Code/knowledge/hl-knowledge-market` | `warehouse-lint-cli-for-ci` | Operational only — tracked separately in PER-182 (warehouse-side rollout). Migrates agent frontmatter, fixes broken knowledge links, adds the lint workflow. No production code from this OpenSpec change lands here. |
| `hl-sandbox-pipelines` | `~/Code/homelab/common/hl-sandbox-pipelines` | `main` | Not involved — Beacon CLI work; no DAG or registra impact. |
| `hl-sandbox-registra` | `~/Code/homelab/common/hl-sandbox-registra` | `main` | Not involved — Beacon CLI work; no DAG or registra impact. |
<!-- opsx:repos-table:end -->

## 1. Scaffold

<!-- opsx:phase-summary:1:begin -->
**Goal**: Create the feature branch and empty source/test scaffolding so subsequent phases can run incrementally without touching the same files in conflicting commits.
**Input**: Clean `main` of `agentic-beacon` with all tests green; `uv` installed; no existing `lint.py` or `test_lint*.py` in the warehouse domain.
**Output**: Branch `warehouse-lint-cli-for-ci` checked out; empty `lint.py`, `test_lint.py`, `test_lint_cli.py` created; baseline `pytest tests/unit` green.
**Validation**: `git rev-parse --abbrev-ref HEAD` returns `warehouse-lint-cli-for-ci`; `pytest libs/beacon/tests/unit` exits 0; the three new files exist and import cleanly.
<!-- opsx:phase-summary:1:end -->


- [x] 1.1 Create branch `warehouse-lint-cli-for-ci` off `main` in `agentic-beacon`.
<!-- opsx:tdd:1.1:begin -->
  - **Input**: cd ~/Code/oss/agentic-beacon && git fetch origin && git checkout -b warehouse-lint-cli-for-ci origin/main
  - **Expected Output**: Switched to a new branch 'warehouse-lint-cli-for-ci'
  - **Validation**: `git rev-parse --abbrev-ref HEAD` returns `warehouse-lint-cli-for-ci`; `git log -1 --format=%H` matches `origin/main`.
<!-- opsx:tdd:1.1:end -->
- [x] 1.2 Create empty module `libs/beacon/src/beacon/domains/warehouse/lint.py` with module docstring referencing this change name.
- [x] 1.3 Create empty test files `libs/beacon/tests/unit/domains/warehouse/test_lint.py` and `libs/beacon/tests/integration/domains/warehouse/test_lint_cli.py`.
- [x] 1.4 Verify `uv sync --group dev` and `pytest libs/beacon/tests/unit` still pass on the fresh branch (baseline check before any edits).
<!-- opsx:tdd:1.4:begin -->
  - **Input**: cd ~/Code/oss/agentic-beacon && uv sync --group dev && pytest libs/beacon/tests/unit
  - **Expected Output**: uv sync resolves; pytest reports `passed` with `0 failed`
  - **Validation**: Both commands exit 0; no import errors triggered by the new (empty) module.
<!-- opsx:tdd:1.4:end -->

## 2. Lint module — data model and orchestrator skeleton

<!-- opsx:phase-summary:2:begin -->
**Goal**: Lock in the public surface (`LintFinding`, `LintReport`, `lint_warehouse`) and the rule-helper composition order before any rule has logic, so every later phase plugs into a stable shape.
**Input**: Empty `lint.py` from phase 1; design.md §1–§2 (data model + composition order) finalised.
**Output**: `lint_warehouse(path) -> LintReport` callable; six private `_lint_*` helpers declared as stubs returning `[]`; smoke unit test passes.
**Validation**: `pytest libs/beacon/tests/unit/domains/warehouse/test_lint.py::test_smoke` exits 0; orchestrator returns a `LintReport` against a clean fixture; module imports cleanly.
<!-- opsx:phase-summary:2:end -->


- [x] 2.1 Define `LintFinding` (frozen dataclass: `artifact_path: str`, `message: str`).
- [x] 2.2 Define `LintReport` (frozen dataclass: `findings: tuple[LintFinding, ...]`, with `__bool__` returning `bool(findings)` so callers can write `if report:`).
<!-- opsx:tdd:2.2:begin -->
  - **Input**: Construct `LintReport(findings=())` and `LintReport(findings=(LintFinding('p','m'),))` in a unit test; assert truthiness.
  - **Expected Output**: Empty report → `bool(report) is False`; non-empty report → `bool(report) is True`.
  - **Validation**: Unit test asserts both truthiness cases and that `LintReport` rejects mutation (frozen).
  - **TDD Test Cases (write these first):**
    - TC1: empty findings tuple → bool(report) is False
    - TC2: one finding → bool(report) is True
    - TC3: attempt to mutate findings → raises FrozenInstanceError
<!-- opsx:tdd:2.2:end -->
- [x] 2.3 Define `lint_warehouse(warehouse_path: Path) -> LintReport` that calls each private rule helper (declared but unimplemented as `return []`), concatenates findings in the fixed order documented in `design.md` §2, and returns `LintReport`.
<!-- opsx:tdd:2.3:begin -->
  - **Input**: Six `_lint_*` stubs declared in `lint.py` each returning `[]`; call `lint_warehouse(tmp_path)`.
  - **Expected Output**: Returns `LintReport(findings=())`; helpers are invoked in the design.md §2 order (structure → skill_frontmatter → skill_requires → agent_manifest → agent_frontmatter → knowledge_links).
  - **Validation**: Smoke test imports and calls succeed; a follow-up test with monkey-patched stubs returning distinct sentinel findings asserts concatenation order.
  - **TDD Test Cases (write these first):**
    - TC1: all helpers return [] → LintReport.findings == ()
    - TC2: each helper returns a single sentinel finding → result preserves declared order (1→2→3→4→5→6)
    - TC3: warehouse_path is a relative path → orchestrator resolves to absolute before invoking helpers
<!-- opsx:tdd:2.3:end -->
- [x] 2.4 Resolve `warehouse_path` via `Path(warehouse_path).expanduser().resolve()` at the top of `lint_warehouse` so every rule helper receives an absolute path.
- [x] 2.5 Write a smoke unit test asserting `lint_warehouse` against an empty `tmp_path` returns a `LintReport` whose findings include the expected structural-error count (proves the wiring works before any rule has logic).
<!-- opsx:tdd:2.5:begin -->
  - **Input**: pytest libs/beacon/tests/unit/domains/warehouse/test_lint.py::test_smoke_empty_dir
  - **Expected Output**: Test passes; assertion `len(report.findings) > 0` holds (empty dir trips structure preflight).
  - **Validation**: After rule 3 lands, this test continues to pass — pins the wiring.
<!-- opsx:tdd:2.5:end -->

## 3. Rule — structure preflight

<!-- opsx:phase-summary:3:begin -->
**Goal**: Wire the existing `WarehouseValidator` into the lint orchestrator and translate its error strings into `LintFinding`s scoped to the right path, without short-circuiting downstream rules.
**Input**: Stub `_lint_structure` from phase 2; `WarehouseValidator.validate` unchanged in `domains/warehouse/validator.py`.
**Output**: `_lint_structure` returns one `LintFinding` per `ValidationResult.errors` entry, correctly scoped to `<warehouse>` or to the specific path the error names.
**Validation**: Three unit tests pass (missing `docs/`, missing path, project-not-warehouse); each emits exactly one finding with the expected message and path scope.
<!-- opsx:phase-summary:3:end -->


- [x] 3.1 Implement `_lint_structure(warehouse_path)`: call `WarehouseValidator().validate(warehouse_path)`, convert each error string into a `LintFinding` scoped to the path the error names; fall back to `"<warehouse>"` for warehouse-level errors that name no specific path (e.g. "Missing required directory: docs/").
<!-- opsx:tdd:3.1:begin -->
  - **Input**: Fixture warehouse missing `docs/`; call `_lint_structure(fixture)`.
  - **Expected Output**: Returns `[LintFinding(artifact_path='<warehouse>', message='Missing required directory: docs/')]`.
  - **Validation**: Returned list length matches `ValidationResult.errors` length; each finding's `artifact_path` is `<warehouse>` for directory-level errors, or the specific file path for file-level errors.
  - **TDD Test Cases (write these first):**
    - TC1: clean warehouse → returns []
    - TC2: missing docs/ only → 1 finding scoped to <warehouse>
    - TC3: missing docs/ AND missing README → 2 findings, both at <warehouse>
    - TC4: target path does not exist → 1 finding mentioning 'Path not found'
    - TC5: target is a project (.agentic-beacon/artifacts/ present) → 1 finding mentioning 'project directory'
    - TC6: target is a file, not a directory → 1 finding mentioning 'not a directory'
<!-- opsx:tdd:3.1:end -->
- [x] 3.2 Unit test: fixture warehouse missing `docs/` but with everything else valid → one finding scoped to `"<warehouse>"` mentioning `docs/`.
<!-- opsx:tdd:3.2:begin -->
  - **Input**: Build a tmp_path warehouse with `agents/`, `contexts/`, `skills/`, `README.md` but no `docs/`. Call `_lint_structure`.
  - **Expected Output**: len(result) == 1; result[0].artifact_path == '<warehouse>'; 'docs/' in result[0].message.
  - **Validation**: Test passes in isolation and as part of the full suite.
<!-- opsx:tdd:3.2:end -->
- [x] 3.3 Unit test: target path that does not exist → one finding mentioning "Path not found".
<!-- opsx:tdd:3.3:begin -->
  - **Input**: Call `_lint_structure(tmp_path / 'does-not-exist')`.
  - **Expected Output**: len(result) == 1; 'Path not found' in result[0].message.
  - **Validation**: Test passes; no exception raised — error is converted to a finding.
<!-- opsx:tdd:3.3:end -->
- [x] 3.4 Unit test: target path is a project (contains `.agentic-beacon/artifacts/`) → one finding mentioning "appears to be a project directory".
<!-- opsx:tdd:3.4:begin -->
  - **Input**: Build a tmp_path that contains `.agentic-beacon/artifacts/`. Call `_lint_structure`.
  - **Expected Output**: len(result) == 1; 'project directory' in result[0].message.
  - **Validation**: Test passes; pins the safety-check that lint won't silently scan a project.
<!-- opsx:tdd:3.4:end -->

## 4. Rule — skill frontmatter

<!-- opsx:phase-summary:4:begin -->
**Goal**: Catch the exact PER-114 regression (skill merged without frontmatter) plus YAML parse errors and skill-to-skill dependency violations, reusing `parse_frontmatter` + `SkillFrontmatter` without modifying them.
**Input**: Stub `_lint_skill_frontmatter`; `parse_frontmatter` and `SkillFrontmatter` unchanged.
**Output**: Per-skill finding emitted for: missing frontmatter, malformed YAML, schema validation failure, forbidden `skills:` key. Valid skills produce no finding.
**Validation**: Four unit tests pass; the regression test produces the exact message `"File has no YAML frontmatter (must start with ---)"` scoped to `skills/delegate-to-cc/SKILL.md`.
<!-- opsx:phase-summary:4:end -->


- [x] 4.1 Implement `_lint_skill_frontmatter(warehouse_path)`: iterate `skills/*/SKILL.md`, call `parse_frontmatter(path)`; on `result.success == False`, emit a finding using `result.message`; on success, attempt `SkillFrontmatter(**result.data)` and emit a finding per `ValidationError` (one finding per validation error, message includes the field path + reason).
<!-- opsx:tdd:4.1:begin -->
  - **Input**: Fixture warehouse with one valid skill, one missing-frontmatter skill, one skill with malformed YAML. Call `_lint_skill_frontmatter(fixture)`.
  - **Expected Output**: Two findings, scoped to the two defective skills; the valid skill produces none.
  - **Validation**: Each finding's `artifact_path` is the warehouse-relative `skills/<name>/SKILL.md`; messages match the `parse_frontmatter` / pydantic error strings verbatim.
  - **TDD Test Cases (write these first):**
    - TC1: skill with valid frontmatter and valid `requires.contexts: [foo]` → no finding
    - TC2: skill with no frontmatter block → 1 finding, message starts with 'File has no YAML frontmatter'
    - TC3: skill with frontmatter opened but never closed → 1 finding, message mentions 'never closed'
    - TC4: skill with malformed YAML inside the block → 1 finding mentioning 'YAML parse error'
    - TC5: skill with `requires: {skills: [...]}` → 1 finding mentioning 'Skill-to-skill dependencies are not supported'
    - TC6: skill with `requires` missing `contexts` key → 1 finding from Pydantic validation
    - TC7: skill where frontmatter parses to a non-dict (e.g. a YAML list) → 1 finding mentioning 'invalid-frontmatter'
    - TC8: two skills each with a different defect → 2 findings, one per skill, ordering stable
<!-- opsx:tdd:4.1:end -->
- [x] 4.2 Unit test: skill with no `---` frontmatter block → finding matches the exact regression message `"File has no YAML frontmatter (must start with ---)"`, scoped to `skills/delegate-to-cc/SKILL.md` (use the PER-114 regression name in the fixture).
<!-- opsx:tdd:4.2:begin -->
  - **Input**: Build fixture with `skills/delegate-to-cc/SKILL.md` containing only body text, no frontmatter. Call `_lint_skill_frontmatter`.
  - **Expected Output**: Exactly one finding: artifact_path=='skills/delegate-to-cc/SKILL.md', message=='File has no YAML frontmatter (must start with ---)'.
  - **Validation**: Equality assertion on the message string (verbatim from `parse_frontmatter`); test name calls out PER-114 regression.
<!-- opsx:tdd:4.2:end -->
- [x] 4.3 Unit test: skill with malformed YAML inside the frontmatter block → finding mentions YAML parse error.
<!-- opsx:tdd:4.3:begin -->
  - **Input**: Fixture with `skills/bad-yaml/SKILL.md` containing `---\n  : invalid\n---\nbody`. Call `_lint_skill_frontmatter`.
  - **Expected Output**: len == 1; 'YAML parse error' in finding.message.
  - **Validation**: Substring match on message; finding scoped to the defective skill path.
<!-- opsx:tdd:4.3:end -->
- [x] 4.4 Unit test: skill with `requires: {skills: [...]}` → finding mentions "Skill-to-skill dependencies are not supported".
<!-- opsx:tdd:4.4:begin -->
  - **Input**: Fixture skill with frontmatter `requires: {skills: [other], contexts: [foo]}`. Call `_lint_skill_frontmatter`.
  - **Expected Output**: len == 1; 'Skill-to-skill dependencies are not supported' in finding.message.
  - **Validation**: Pins the `SkillRequires.reject_skills_key` enforcement path.
<!-- opsx:tdd:4.4:end -->
- [x] 4.5 Unit test: skill with valid `requires.contexts` → no finding from this rule.
<!-- opsx:tdd:4.5:begin -->
  - **Input**: Fixture skill with valid frontmatter `requires: {contexts: [some-ctx]}` and matching `contexts/some-ctx.md`. Call `_lint_skill_frontmatter`.
  - **Expected Output**: result == [].
  - **Validation**: Happy path: no false positives for well-formed skills.
<!-- opsx:tdd:4.5:end -->

## 5. Rule — skill `requires.contexts` resolution

<!-- opsx:phase-summary:5:begin -->
**Goal**: Verify every context name in a skill's `requires.contexts` resolves to an actual `contexts/<name>.md` file — a defect class no existing primitive catches.
**Input**: Phase 4 complete (skip skills with invalid frontmatter, since rule 4 reports those); `contexts/` directory may or may not contain the named files.
**Output**: One finding per missing context name, scoped to the declaring `SKILL.md`. Skills with empty/valid `requires.contexts` produce no finding from this rule.
**Validation**: Three unit tests pass (single missing, two missing, valid); failing fixture produces one finding per missing context, not one combined finding.
<!-- opsx:phase-summary:5:end -->


- [x] 5.1 Implement `_lint_skill_requires(warehouse_path)`: re-parse each `skills/*/SKILL.md` frontmatter (skip files whose frontmatter is invalid — those are reported by rule 4); for each name in `requires.contexts`, emit a finding if `contexts/<name>.md` does not exist.
<!-- opsx:tdd:5.1:begin -->
  - **Input**: Fixture: skill `foo` declares `requires.contexts: [missing-ctx]`, no `contexts/missing-ctx.md`. Call `_lint_skill_requires`.
  - **Expected Output**: One finding scoped to `skills/foo/SKILL.md` mentioning `missing-ctx`.
  - **Validation**: Finding count matches missing-context count; valid-context skills produce zero findings; rule does NOT double-report skills whose frontmatter rule 4 already failed.
  - **TDD Test Cases (write these first):**
    - TC1: skill with all referenced contexts existing → no finding
    - TC2: skill references one missing context → 1 finding, message names the missing context name
    - TC3: skill references two missing contexts → 2 findings, both scoped to same skill
    - TC4: skill with invalid frontmatter (no `---` block) → 0 findings from this rule (rule 4 handles it)
    - TC5: skill with empty `requires.contexts: []` → no finding
    - TC6: skill references a context whose file exists but is a directory, not a file → 1 finding (treat as missing)
<!-- opsx:tdd:5.1:end -->
- [x] 5.2 Unit test: skill `foo` declares `requires.contexts: [missing-ctx]`, no `contexts/missing-ctx.md` → one finding scoped to `skills/foo/SKILL.md` naming `missing-ctx`.
<!-- opsx:tdd:5.2:begin -->
  - **Input**: Build fixture as described. Call `_lint_skill_requires`.
  - **Expected Output**: len == 1; finding.artifact_path == 'skills/foo/SKILL.md'; 'missing-ctx' in finding.message.
  - **Validation**: Substring + path equality.
<!-- opsx:tdd:5.2:end -->
- [x] 5.3 Unit test: skill `foo` declares two missing contexts → two findings, both scoped to `skills/foo/SKILL.md`.
<!-- opsx:tdd:5.3:begin -->
  - **Input**: Skill `foo` with `requires.contexts: [a, b]`, neither file exists. Call rule.
  - **Expected Output**: len == 2; both findings have artifact_path == 'skills/foo/SKILL.md'; each names one of `a`, `b`.
  - **Validation**: Pins the per-item fan-out semantics.
<!-- opsx:tdd:5.3:end -->
- [x] 5.4 Unit test: skill with no `requires.contexts` items → no finding from this rule.
<!-- opsx:tdd:5.4:begin -->
  - **Input**: Skill with frontmatter `requires: {contexts: []}`. Call rule.
  - **Expected Output**: result == [].
  - **Validation**: Edge case: empty list must not crash and must produce no findings.
<!-- opsx:tdd:5.4:end -->

## 6. Rule — agent manifest

<!-- opsx:phase-summary:6:begin -->
**Goal**: Compose the four existing agent-manifest validators into a single lint pass that aggregates every defect class, surviving the first raise.
**Input**: Stub `_lint_agent_manifest`; all four primitives unchanged in `core/dependencies/manifest.py`.
**Output**: On parse failure, one finding per `\n`-split line of the `AgentManifestError`; on successful parse, every downstream validator runs and its errors fan out into per-defect findings scoped to `agents/<name>.md` or `agents/agents.yaml`.
**Validation**: Five unit tests pass; the multi-defect fixture (two missing manifest entries) produces two findings — pins the `\n`-split contract.
<!-- opsx:phase-summary:6:end -->


- [x] 6.1 Implement `_lint_agent_manifest(warehouse_path)`: call `load_agent_manifest`; on `AgentManifestError`, emit one finding scoped to `agents/agents.yaml` per `\n`-split line of the exception message, and return early (downstream manifest-dependent checks need a parsed manifest).
<!-- opsx:tdd:6.1:begin -->
  - **Input**: Fixture with `agents/agents.yaml` containing `: : :` (unparseable). Call `_lint_agent_manifest`.
  - **Expected Output**: All findings scoped to `agents/agents.yaml`; no downstream-validator-shaped errors (early return triggered).
  - **Validation**: Findings count equals lines in the raised exception's message after splitting on `\n`; subsequent helper logic is not executed.
  - **TDD Test Cases (write these first):**
    - TC1: agents.yaml is valid → no finding from this code path; downstream validators run
    - TC2: agents.yaml has YAML syntax error → ≥1 finding scoped to agents/agents.yaml, all from the parse phase
    - TC3: agents.yaml is not a mapping (e.g. a list at top level) → 1 finding mentioning 'must be a YAML mapping'
    - TC4: agents.yaml has `contexts:` at agent-entry level (forbidden) → 1 finding mentioning schema validation
    - TC5: agents.yaml does not exist → no finding (file is optional)
<!-- opsx:tdd:6.1:end -->
- [x] 6.2 Same helper, on successful manifest load: call `validate_agents_directory`, `validate_agent_frontmatter_clean`, `validate_declared_skills` in turn; for each, catch `AgentManifestError`, split message on `\n`, and emit one finding per line scoped to the artifact path the message names (parse the message; if no path is recoverable, scope to `agents/agents.yaml`).
<!-- opsx:tdd:6.2:begin -->
  - **Input**: Fixture where manifest parses cleanly but every downstream validator finds defects (agent missing from manifest, agent with `requires:`, declared skill missing).
  - **Expected Output**: Findings from all three downstream validators present; each scoped to the path the error names (`agents/<name>.md` or `agents/agents.yaml` when ambiguous).
  - **Validation**: All three downstream raises are caught; messages fan out to per-defect findings; ordering matches the helper-call order.
  - **TDD Test Cases (write these first):**
    - TC1: 1 missing-manifest-entry + 1 orphan-manifest-entry → 2 findings, one per defect
    - TC2: 1 agent with `requires:` in frontmatter → 1 finding scoped to agents/<name>.md mentioning legacy 'requires:'
    - TC3: agent declares skill `missing-skill` not present in skills/ → 1 finding scoped to agents/<name>.md naming the missing skill
    - TC4: defects from all three validators present simultaneously → findings from all three, none lost
    - TC5: AgentManifestError whose message contains no recoverable path → finding falls back to agents/agents.yaml scope
    - TC6: clean manifest + clean agents → no finding
<!-- opsx:tdd:6.2:end -->
- [x] 6.3 Unit test: `agents/foo.md` exists, `agents.yaml` has no `foo:` key → one finding mentioning the missing manifest entry, scoped to `agents/foo.md`.
<!-- opsx:tdd:6.3:begin -->
  - **Input**: Build fixture with `agents/foo.md` (valid frontmatter) and `agents.yaml` empty mapping `{}`. Call `_lint_agent_manifest`.
  - **Expected Output**: len == 1; finding.artifact_path == 'agents/foo.md'; message mentions 'no entry in agents/agents.yaml'.
  - **Validation**: Pins the `validate_agents_directory` integration.
<!-- opsx:tdd:6.3:end -->
- [x] 6.4 Unit test: `agents.yaml` declares agent `foo` with `skills: [missing-skill]` → one finding mentioning the missing skill, scoped to `agents/foo.md`.
<!-- opsx:tdd:6.4:begin -->
  - **Input**: Fixture with `agents/foo.md` + `agents.yaml: {foo: {skills: [missing-skill]}}` and no `skills/missing-skill/`. Call rule.
  - **Expected Output**: len == 1; 'missing-skill' in message; scope is `agents/foo.md`.
  - **Validation**: Pins the `validate_declared_skills` integration.
<!-- opsx:tdd:6.4:end -->
- [x] 6.5 Unit test: `agents/foo.md` carries `requires: {skills: [...]}` in frontmatter → one finding mentioning the legacy `requires:` key, scoped to `agents/foo.md`.
<!-- opsx:tdd:6.5:begin -->
  - **Input**: Fixture with `agents/foo.md` whose frontmatter still has `requires:` block + matching agents.yaml entry. Call rule.
  - **Expected Output**: len == 1; 'requires:' in message; scope is `agents/foo.md`.
  - **Validation**: Pins the `validate_agent_frontmatter_clean` integration.
<!-- opsx:tdd:6.5:end -->
- [x] 6.6 Unit test (multi-defect): fixture with two agents missing from `agents.yaml` → two findings (one per agent), not one combined finding — pins the `\n`-split convention.
<!-- opsx:tdd:6.6:begin -->
  - **Input**: Fixture with `agents/foo.md` + `agents/bar.md` and empty agents.yaml. Call rule.
  - **Expected Output**: len == 2; one finding scoped to `agents/foo.md`, one to `agents/bar.md`.
  - **Validation**: Critical regression test: protects the `\n`-split contract design.md decision §6 depends on.
<!-- opsx:tdd:6.6:end -->
- [x] 6.7 Unit test: `agents/agents.yaml` is unparseable YAML → one finding scoped to `agents/agents.yaml`, downstream manifest checks skipped (no spurious findings).
<!-- opsx:tdd:6.7:begin -->
  - **Input**: Fixture with `agents.yaml` content `:::` (unparseable) plus valid `agents/foo.md`. Call rule.
  - **Expected Output**: len == 1; scope is `agents/agents.yaml`; no findings against `agents/foo.md`.
  - **Validation**: Pins the early-return-on-parse-failure behaviour.
<!-- opsx:tdd:6.7:end -->

## 7. Rule — agent frontmatter (`name` + `description`)

<!-- opsx:phase-summary:7:begin -->
**Goal**: Enforce the brand-new requirement that every `agents/*.md` (excluding README) carries `name:` and `description:` keys — no precedent anywhere in Beacon today.
**Input**: Stub `_lint_agent_frontmatter`; `parse_frontmatter` unchanged; `README.md` is excluded from iteration.
**Output**: One finding per missing key (`name` or `description`), or one combined missing-frontmatter finding when the block is wholly absent (avoids noise).
**Validation**: Six unit tests pass, including the README-exclusion test and the wholly-missing-frontmatter test that asserts exactly one finding (not two).
<!-- opsx:phase-summary:7:end -->


- [x] 7.1 Implement `_lint_agent_frontmatter(warehouse_path)`: iterate every `agents/*.md` excluding `README.md`; call `parse_frontmatter`; if frontmatter is missing or malformed, emit one finding using the message from `FrontmatterResult`; on success, emit a finding for each of `name` and `description` that is absent from the parsed dict.
<!-- opsx:tdd:7.1:begin -->
  - **Input**: Fixture with one agent missing `name`, one missing `description`, one with both, one with no frontmatter, plus `agents/README.md` with no frontmatter. Call `_lint_agent_frontmatter`.
  - **Expected Output**: Three findings total: missing-name, missing-description, missing-frontmatter. README produces none. The both-keys agent produces none.
  - **Validation**: Wholly-missing-frontmatter case produces exactly one finding (not two), pinning the noise-avoidance rule.
  - **TDD Test Cases (write these first):**
    - TC1: agent with {name: foo, description: '...'} → no finding
    - TC2: agent with {description: '...'} only → 1 finding 'missing required key `name`'
    - TC3: agent with {name: foo} only → 1 finding 'missing required key `description`'
    - TC4: agent with neither key but valid frontmatter dict → 2 findings (one per missing key)
    - TC5: agent with no `---` block at all → 1 finding (the missing-frontmatter error), NOT 2
    - TC6: agents/README.md with no frontmatter → no finding (excluded by name)
    - TC7: agent file with `name:` value not a string (e.g. integer) → no finding from this rule (only key presence checked; type enforcement deferred)
<!-- opsx:tdd:7.1:end -->
- [x] 7.2 Unit test: `agents/foo.md` with `{description: "..."}` only → finding "missing required key `name`", scoped to `agents/foo.md`.
<!-- opsx:tdd:7.2:begin -->
  - **Input**: Build agent with frontmatter that has `description:` only. Call rule.
  - **Expected Output**: len == 1; '`name`' in finding.message; scope is `agents/foo.md`.
  - **Validation**: Substring match on the required-key wording.
<!-- opsx:tdd:7.2:end -->
- [x] 7.3 Unit test: `agents/foo.md` with `{name: foo}` only → finding "missing required key `description`".
<!-- opsx:tdd:7.3:begin -->
  - **Input**: Build agent with frontmatter that has `name:` only. Call rule.
  - **Expected Output**: len == 1; '`description`' in finding.message.
  - **Validation**: Substring match.
<!-- opsx:tdd:7.3:end -->
- [x] 7.4 Unit test: `agents/foo.md` with both keys → no finding from this rule.
<!-- opsx:tdd:7.4:begin -->
  - **Input**: Build agent with `{name: foo, description: '...'}`. Call rule.
  - **Expected Output**: result == [].
  - **Validation**: Happy path.
<!-- opsx:tdd:7.4:end -->
- [x] 7.5 Unit test: `agents/README.md` with no frontmatter → no finding (README is excluded).
<!-- opsx:tdd:7.5:begin -->
  - **Input**: Fixture with only `agents/README.md` (no frontmatter). Call rule.
  - **Expected Output**: result == [].
  - **Validation**: README exclusion is observed by name; pins the iteration filter.
<!-- opsx:tdd:7.5:end -->
- [x] 7.6 Unit test: `agents/foo.md` with no frontmatter block → exactly one finding (the missing-frontmatter error), NOT one each for `name` and `description` (avoid noise when frontmatter is wholly absent).
<!-- opsx:tdd:7.6:begin -->
  - **Input**: Build agent with only body text, no `---`. Call rule.
  - **Expected Output**: len == 1; message mentions 'no YAML frontmatter'; NO additional findings for missing `name` or `description`.
  - **Validation**: Critical noise-control test; pins the design decision that when frontmatter is wholly missing we emit one error, not three.
<!-- opsx:tdd:7.6:end -->

## 8. Rule — knowledge link integrity

<!-- opsx:phase-summary:8:begin -->
**Goal**: Promote broken knowledge links from warning to error at lint time without modifying `scan_file_for_knowledge`. Reuse the lower-level link helpers directly.
**Input**: Stub `_lint_knowledge_links`; `extract_markdown_links`, `resolve_link`, `classify_knowledge_ref` unchanged; `scan_file_for_knowledge` MUST remain untouched.
**Output**: One finding per broken knowledge-classified link, scoped to the source `contexts/*.md` or `skills/*/SKILL.md`. Absolute URLs and non-knowledge links produce no finding.
**Validation**: Seven unit tests pass; the regression test confirms `scan_file_for_knowledge` still returns a `set[str]` and does not raise — pins the primitive-unchanged invariant.
<!-- opsx:phase-summary:8:end -->


- [x] 8.1 Implement `_lint_knowledge_links(warehouse_path)`: iterate `contexts/*.md` and `skills/*/SKILL.md`; for each, read content, call `extract_markdown_links`, normalise each target, call `resolve_link` against the warehouse root, classify with `classify_knowledge_ref`, and emit a finding when the resolved path does not exist on disk.
<!-- opsx:tdd:8.1:begin -->
  - **Input**: Fixture with `contexts/foo.md` containing `[X](../knowledge/foo/bar.md)` but no `knowledge/foo/bar.md` on disk. Call `_lint_knowledge_links`.
  - **Expected Output**: One finding scoped to `contexts/foo.md` whose message names the broken knowledge target.
  - **Validation**: Finding count equals number of broken knowledge-classified links; absolute URLs and non-knowledge paths produce zero findings; reuses `scanner` helpers directly (no call to `scan_file_for_knowledge`).
  - **TDD Test Cases (write these first):**
    - TC1: context with valid knowledge link → no finding
    - TC2: context with one broken knowledge link → 1 finding, message names the link target
    - TC3: context with two broken knowledge links → 2 findings
    - TC4: skill with broken knowledge link → 1 finding scoped to skills/<name>/SKILL.md
    - TC5: context with absolute URL → no finding
    - TC6: context with link to non-knowledge file (./other.md) → no finding
    - TC7: context with link to knowledge file that exists → no finding
    - TC8: context with reference-style link [X][ref] resolving to a knowledge path → finding (or not, per scanner semantics — pin behaviour)
    - TC9: file unreadable due to permission error → handled gracefully (no crash; either skipped or produces a single 'unreadable' finding)
<!-- opsx:tdd:8.1:end -->
- [x] 8.2 The finding message MUST name the broken target (e.g. `"broken knowledge link: ../knowledge/foo/bar.md → knowledge/foo/bar.md (file not found)"`).
<!-- opsx:tdd:8.2:begin -->
  - **Input**: Fixture from 8.1 TC2. Inspect the emitted finding's message string.
  - **Expected Output**: Message contains both the raw link text (`../knowledge/foo/bar.md`) and the resolved warehouse-relative path (`knowledge/foo/bar.md`), plus a 'file not found' marker.
  - **Validation**: Substring assertions on all three components.
<!-- opsx:tdd:8.2:end -->
- [x] 8.3 Unit test: `contexts/foo.md` contains `[X](../knowledge/foo/bar.md)`, no target file → one finding scoped to `contexts/foo.md`.
<!-- opsx:tdd:8.3:begin -->
  - **Input**: Build fixture as described. Call rule.
  - **Expected Output**: len == 1; artifact_path == 'contexts/foo.md'.
  - **Validation**: Path scope assertion.
<!-- opsx:tdd:8.3:end -->
- [x] 8.4 Unit test: `skills/foo/SKILL.md` contains `[X](../../knowledge/foo/bar.md)`, no target file → one finding scoped to `skills/foo/SKILL.md`.
<!-- opsx:tdd:8.4:begin -->
  - **Input**: Build fixture as described. Call rule.
  - **Expected Output**: len == 1; artifact_path == 'skills/foo/SKILL.md'.
  - **Validation**: Path scope assertion; pins skill-side scanning.
<!-- opsx:tdd:8.4:end -->
- [x] 8.5 Unit test: `contexts/foo.md` contains an absolute URL link `[X](https://example.com)` → no finding (absolute URLs are out of scope).
<!-- opsx:tdd:8.5:begin -->
  - **Input**: Build fixture with only an https link. Call rule.
  - **Expected Output**: result == [].
  - **Validation**: Pins the `is_absolute_url` early-return path.
<!-- opsx:tdd:8.5:end -->
- [x] 8.6 Unit test: `contexts/foo.md` contains a link to a non-knowledge path (`[X](./other.md)`) → no finding (only knowledge-classified targets are checked).
<!-- opsx:tdd:8.6:begin -->
  - **Input**: Build fixture with relative link to a non-knowledge path. Call rule.
  - **Expected Output**: result == [].
  - **Validation**: Pins the `classify_knowledge_ref` filter.
<!-- opsx:tdd:8.6:end -->
- [x] 8.7 Regression test: confirm `scan_file_for_knowledge` was NOT modified (import the function, call it on the same broken-link fixture, assert it returns a set and does not raise — pins the "primitive unchanged" invariant).
<!-- opsx:tdd:8.7:begin -->
  - **Input**: Import `scan_file_for_knowledge` from `beacon.core.scanner.scanner`. Call it against the fixture from 8.3.
  - **Expected Output**: Returns a `set[str]` (not a list, not None); broken target IS in the returned set; no exception raised.
  - **Validation**: isinstance check + membership assertion; protects design decision §4.
  - **TDD Test Cases (write these first):**
    - TC1: broken-link fixture → returns a set containing the broken target path
    - TC2: same fixture invoked again → idempotent return value (same set)
    - TC3: file path that does not exist → returns empty set (no exception)
<!-- opsx:tdd:8.7:end -->

## 9. Orchestrator integration test

<!-- opsx:phase-summary:9:begin -->
**Goal**: Prove all six rule helpers compose correctly into a single `lint_warehouse` call against a multi-defect fixture, with stable cross-platform ordering.
**Input**: All rule helpers implemented (phases 3–8); a multi-defect fixture warehouse constructible from `tmp_path`.
**Output**: Test asserting every rule category appears in the report, findings sorted by `(artifact_path, message)`, total count matches expectation.
**Validation**: Orchestrator-level unit test passes; the fixture intentionally exercises one defect per rule and the assertion enumerates them all.
<!-- opsx:phase-summary:9:end -->


- [x] 9.1 Build a fixture warehouse with one defect from each of rules 3–8 (e.g. missing `docs/`, one skill with no frontmatter, one skill with a missing context, one agent missing from `agents.yaml`, one agent missing `name`, one context with a broken knowledge link).
<!-- opsx:tdd:9.1:begin -->
  - **Input**: Create a `tmp_path`-rooted fixture builder helper. Construct the six-defect fixture.
  - **Expected Output**: Fixture has the expected directory layout (everything but `docs/`), the six intentional defects, and is otherwise valid.
  - **Validation**: Helper is reusable from both the orchestrator integration test and (optionally) future tests; smoke-call each rule helper individually and confirm exactly the intended defect appears.
<!-- opsx:tdd:9.1:end -->
- [x] 9.2 Unit test: `lint_warehouse(fixture)` returns a `LintReport` containing exactly the expected count of findings, every category represented, findings sorted by `(artifact_path, message)` so iteration order is stable across platforms.
<!-- opsx:tdd:9.2:begin -->
  - **Input**: Call `lint_warehouse(fixture_from_9_1)`.
  - **Expected Output**: Findings count matches the sum across all helpers; every rule category is represented; `[f.artifact_path for f in findings]` is non-decreasing.
  - **Validation**: Sorted-order assertion makes the test deterministic across OS filesystem orderings.
  - **TDD Test Cases (write these first):**
    - TC1: six-defect fixture → six findings, one per category
    - TC2: clean warehouse → empty report (bool(report) is False)
    - TC3: same fixture lint-ed twice → identical reports (idempotency)
    - TC4: findings list is sorted by (artifact_path, message) ascending
    - TC5: report includes structural finding (<warehouse> scope) when structure is broken
<!-- opsx:tdd:9.2:end -->

## 10. CLI handler

<!-- opsx:phase-summary:10:begin -->
**Goal**: Add the `abc warehouse lint` Click handler + Rich formatter, with no logic in the handler so the CLI thinness invariant holds.
**Input**: `lint_warehouse` complete (phase 9); `cli/warehouse.py` currently has `warehouse_template_upgrade` as the closest precedent.
**Output**: `warehouse_lint` Click command + `_print_lint_report` formatter added to `cli/warehouse.py`; exit 0 on clean, exit 1 on any finding; output grouped by artifact path with `error:` prefix.
**Validation**: `test_architecture.py` still passes (no logic in CLI layer); CliRunner-based unit tests assert exit codes and output structure; `abc warehouse lint --help` renders without error.
<!-- opsx:phase-summary:10:end -->


- [x] 10.1 Add `warehouse_lint` Click handler under `@warehouse.command(name="lint")` in `libs/beacon/src/beacon/cli/warehouse.py`, mirroring the `warehouse_template_upgrade` argument signature (optional positional `warehouse_path` → defaults to `Path.cwd()`).
<!-- opsx:tdd:10.1:begin -->
  - **Input**: Run `abc warehouse lint --help` after the handler is added.
  - **Expected Output**: Help text shows the optional `WAREHOUSE_PATH` positional and no other flags; exit code 0.
  - **Validation**: `click.testing.CliRunner().invoke(warehouse, ['lint', '--help'])` returns exit code 0 and the expected option list.
<!-- opsx:tdd:10.1:end -->
- [x] 10.2 Implement `_print_lint_report(report: LintReport, console: Console)` in the same file: print `[green]✓ Lint passed.[/green]` when `report` is empty; otherwise group findings by `artifact_path`, print `[bold]{path}[/bold]` then one `  [red]error:[/red] {message}` per finding under it, with a final summary line `[red]Found {N} error(s) across {M} file(s).[/red]`.
<!-- opsx:tdd:10.2:begin -->
  - **Input**: Construct a `LintReport` with three findings across two paths; pass a Rich `Console(record=True)`; call `_print_lint_report`.
  - **Expected Output**: Recorded output contains both path headers, three `error:` lines under them grouped correctly, and a summary line `Found 3 error(s) across 2 file(s).`.
  - **Validation**: Substring + grouping assertions on `console.export_text()`.
  - **TDD Test Cases (write these first):**
    - TC1: empty report → output contains '✓ Lint passed.' and no error lines
    - TC2: one finding → output has 1 path header, 1 error line, summary 'Found 1 error(s) across 1 file(s).'
    - TC3: 3 findings across 2 paths → 2 headers, 3 error lines grouped under correct headers
    - TC4: 5 findings under same path → 1 header, 5 error lines, summary 'Found 5 error(s) across 1 file(s).'
    - TC5: groups appear in lexicographically sorted order regardless of insertion order
    - TC6: within a group, findings appear sorted by message
<!-- opsx:tdd:10.2:end -->
- [x] 10.3 Handler exits via `sys.exit(1 if report.findings else 0)`. No `--json` flag.
<!-- opsx:tdd:10.3:begin -->
  - **Input**: Invoke `warehouse_lint` via `CliRunner` against a clean fixture and against a defective fixture.
  - **Expected Output**: Clean → exit_code == 0; defective → exit_code == 1. Passing `--json` → exit_code != 0 with Click's 'no such option' error.
  - **Validation**: CliRunner result assertions on exit_code.
  - **TDD Test Cases (write these first):**
    - TC1: clean fixture → exit_code 0
    - TC2: defective fixture → exit_code 1
    - TC3: invoking with --json → exit_code 2 (Click's unknown-option exit)
<!-- opsx:tdd:10.3:end -->
- [x] 10.4 Confirm `libs/beacon/tests/unit/test_architecture.py` still passes (CLI thinness invariant — the handler must contain no logic, just parse → call `lint_warehouse` → call `_print_lint_report` → `sys.exit`).
<!-- opsx:tdd:10.4:begin -->
  - **Input**: pytest libs/beacon/tests/unit/test_architecture.py
  - **Expected Output**: All architecture tests pass; CLI thinness rule does not flag `warehouse_lint`.
  - **Validation**: Exit code 0; if it fails, refactor logic out of the handler before proceeding.
<!-- opsx:tdd:10.4:end -->
- [x] 10.5 Unit test: invoke `warehouse_lint` via Click's `CliRunner` against a clean fixture, assert exit 0 and "Lint passed" in stdout.
<!-- opsx:tdd:10.5:begin -->
  - **Input**: CliRunner().invoke(warehouse, ['lint', str(clean_fixture)]).
  - **Expected Output**: result.exit_code == 0; 'Lint passed' in result.output.
  - **Validation**: Two assertions.
<!-- opsx:tdd:10.5:end -->
- [x] 10.6 Unit test: invoke via `CliRunner` against a defective fixture, assert exit 1 and grouped output structure.
<!-- opsx:tdd:10.6:begin -->
  - **Input**: CliRunner().invoke(warehouse, ['lint', str(defective_fixture)]).
  - **Expected Output**: result.exit_code == 1; output contains the expected path headers and `error:` lines; the summary line is present.
  - **Validation**: Substring assertions covering each defect.
<!-- opsx:tdd:10.6:end -->

## 11. CLI integration test (subprocess)

<!-- opsx:phase-summary:11:begin -->
**Goal**: Verify the end-to-end CLI surface from the user's perspective by spawning a real `abc warehouse lint` subprocess against fixture warehouses.
**Input**: Phase 10 complete; existing integration-test infrastructure (`uv run` pattern) usable as precedent.
**Output**: Two subprocess tests (clean fixture → exit 0; multi-defect fixture → exit 1 with expected stdout); both gated under `@pytest.mark.integration` and honouring `BEACON_OFFLINE=1`.
**Validation**: `pytest -m integration libs/beacon/tests/integration/domains/warehouse/test_lint_cli.py` exits 0 with both tests green; `BEACON_OFFLINE=1 pytest -m integration ...` skips them.
<!-- opsx:phase-summary:11:end -->


- [x] 11.1 In `libs/beacon/tests/integration/domains/warehouse/test_lint_cli.py`, build a fixture warehouse with at least three defects spanning at least two artifacts.
<!-- opsx:tdd:11.1:begin -->
  - **Input**: Create a tmp_path warehouse builder helper that places three defects across at least two files (e.g. one missing-frontmatter skill, one broken-knowledge-link context, one agent missing `name`).
  - **Expected Output**: Fixture exists on disk under tmp_path with the expected layout and defects.
  - **Validation**: Smoke-assert directory contents before subprocess invocation.
<!-- opsx:tdd:11.1:end -->
- [x] 11.2 Invoke `abc warehouse lint <fixture-path>` via subprocess (use the project's `uv run` pattern from existing integration tests). Assert exit code 1, assert stdout contains each defect's `error:` line and each affected artifact's group header.
<!-- opsx:tdd:11.2:begin -->
  - **Input**: subprocess.run(['uv', 'run', '--', 'abc', 'warehouse', 'lint', str(fixture)], capture_output=True, text=True).
  - **Expected Output**: returncode == 1; stdout contains every defect's `error:` line and every affected path's group header.
  - **Validation**: Substring assertions on stdout; stderr is empty or contains only Rich rendering noise.
  - **TDD Test Cases (write these first):**
    - TC1: three-defect fixture → returncode 1, stdout contains all three error lines
    - TC2: stdout group ordering is alphabetical by path
    - TC3: stdout summary line shows correct N and M counts
<!-- opsx:tdd:11.2:end -->
- [x] 11.3 Invoke `abc warehouse lint <clean-fixture-path>` via subprocess. Assert exit code 0 and "Lint passed" in stdout.
<!-- opsx:tdd:11.3:begin -->
  - **Input**: subprocess.run on a clean fixture.
  - **Expected Output**: returncode == 0; 'Lint passed' in stdout.
  - **Validation**: Two assertions.
<!-- opsx:tdd:11.3:end -->
- [x] 11.4 Mark both tests with `@pytest.mark.integration` and verify they are skipped when `BEACON_OFFLINE=1` is set (if they shell out via `uv run --no-project`).
<!-- opsx:tdd:11.4:begin -->
  - **Input**: BEACON_OFFLINE=1 pytest -m integration libs/beacon/tests/integration/domains/warehouse/test_lint_cli.py -v
  - **Expected Output**: Both tests reported as 'skipped'; pytest exit code 0.
  - **Validation**: Skip behaviour confirmed; running without the env var executes both tests normally.
<!-- opsx:tdd:11.4:end -->

## 12. Docs

<!-- opsx:phase-summary:12:begin -->
**Goal**: Make the new command discoverable: README mention + site-docs reference page + cross-link from the warehouse-command landing page.
**Input**: Phases 1–11 complete; existing README and site-docs structure in place.
**Output**: Three doc edits: `libs/beacon/README.md` entry, new `site-docs/` page for `warehouse lint`, cross-link from the warehouse-commands index.
**Validation**: Manual review: command appears in both surfaces; example invocation matches the implemented signature; mkdocs builds (if configured) with no broken links.
<!-- opsx:phase-summary:12:end -->


- [x] 12.1 Add `abc warehouse lint [PATH]` to the warehouse command list in `libs/beacon/README.md` with one example.
- [x] 12.2 Add a `warehouse lint` reference page under the `site-docs/` warehouse CLI section, including: synopsis, behaviour (the seven rule groups), exit codes, an example invocation, and a note that the strict knowledge-link rule is lint-only (`abc sync` is unchanged).
- [x] 12.3 Cross-link the new page from any existing site-docs landing page that lists warehouse commands.

## 13. Validation and release prep

<!-- opsx:phase-summary:13:begin -->
**Goal**: Smoke-test the command against real warehouses (the production `hl-knowledge-market` and the bundled template) before opening the PR, then ship via the standard release-please path.
**Input**: All code + docs complete (phases 1–12); local `hl-knowledge-market` clone available; bundled template warehouse path identified.
**Output**: `pytest` green; local lint run against `hl-knowledge-market` surfaces expected real-world defects; lint against a fresh `abc warehouse init` template exits 0; PR opened referencing this OpenSpec change and PER-114; release-please cuts a new minor version and the PyPI publish workflow succeeds.
**Validation**: PR merged via GitHub UI; `agentic-beacon` shows up on PyPI at the new version; `uvx agentic-beacon==<new-version> warehouse lint --help` works.
<!-- opsx:phase-summary:13:end -->


- [x] 13.1 Run `pytest` (full suite) from the repo root; all tests pass.
<!-- opsx:tdd:13.1:begin -->
  - **Input**: cd ~/Code/oss/agentic-beacon && pytest
  - **Expected Output**: All tests pass; exit code 0; no skipped tests caused by failure (integration tests may skip if `BEACON_OFFLINE=1`).
  - **Validation**: pytest summary shows '0 failed'.
<!-- opsx:tdd:13.1:end -->
- [ ] 13.2 **[MANUAL]** Run `abc warehouse lint .` against the local `hl-knowledge-market` clone and confirm it surfaces the known defects (delegate-to-cc frontmatter was already fixed upstream; verify the two known broken knowledge links and any agent files missing `name`/`description` are reported).
<!-- opsx:tdd:13.2:begin -->
  - **Input**: cd ~/Code/knowledge/hl-knowledge-market && uv run --project ~/Code/oss/agentic-beacon -- abc warehouse lint .
  - **Expected Output**: Exit code 1; output reports the two known broken knowledge links and every agent file missing `name`/`description`.
  - **Validation**: Manual inspection of the output against the known-defect list; document the count in the PR description.
<!-- opsx:tdd:13.2:end -->
- [x] 13.3 Run `abc warehouse lint` against the warehouse template (`libs/beacon/src/beacon/data/skills/...` parent — wherever the bundled template warehouse lives) and confirm exit 0; a freshly-`init`-ed warehouse must be lint-clean.
<!-- opsx:tdd:13.3:begin -->
  - **Input**: mktemp -d /tmp/wh-XXXX; cd $_; abc warehouse init test-wh; abc warehouse lint test-wh
  - **Expected Output**: Exit code 0; 'Lint passed' in stdout.
  - **Validation**: If this fails, the template ships defects — fix template before merging this change.
<!-- opsx:tdd:13.3:end -->
- [ ] 13.4 **[MANUAL]** Open PR on `agentic-beacon` from `warehouse-lint-cli-for-ci` → `main` with a description that references this OpenSpec change and PER-114.
<!-- opsx:tdd:13.4:begin -->
  - **Input**: gh pr create --base main --head warehouse-lint-cli-for-ci --title 'feat(warehouse): add `abc warehouse lint` for warehouse-side CI' --body '<see template>'
  - **Expected Output**: PR URL returned by gh; PR body links to PER-114 and to `openspec/changes/warehouse-lint-cli-for-ci/`.
  - **Validation**: Manual review of PR description; CI green on the PR.
<!-- opsx:tdd:13.4:end -->
- [ ] 13.5 **[MANUAL]** After merge, confirm release-please cuts a new minor version and the PyPI publish workflow succeeds.
<!-- opsx:tdd:13.5:begin -->
  - **Input**: Watch the release-please PR appear on `main`; merge it; watch the publish workflow.
  - **Expected Output**: Release-please opens a version-bump PR; merging it tags `release/v<new>` and triggers the publish workflow; the new version appears on PyPI.
  - **Validation**: `pip index versions agentic-beacon` shows the new version; `uvx agentic-beacon==<new> warehouse lint --help` works.
<!-- opsx:tdd:13.5:end -->

## 14. Archive

<!-- opsx:phase-summary:14:begin -->
**Goal**: Move the OpenSpec change into `openspec/changes/archive/` once the PR has merged and the release has landed.
**Input**: Phase 13 complete; PR merged; new version published.
**Output**: `openspec/changes/warehouse-lint-cli-for-ci/` moved to `openspec/changes/archive/<date>-warehouse-lint-cli-for-ci/` via the `/opsx-archive` skill.
**Validation**: `openspec list --json` no longer shows the change as active; the archived directory is committed to `main` via a follow-up `docs:` commit.
<!-- opsx:phase-summary:14:end -->


- [X] 14.1 **[MANUAL]** After PR merges and release lands, run `/opsx-archive warehouse-lint-cli-for-ci` to move the change into `openspec/changes/archive/`.
<!-- opsx:tdd:14.1:begin -->
  - **Input**: /opsx-archive warehouse-lint-cli-for-ci
  - **Expected Output**: Skill moves the change directory under `openspec/changes/archive/<date>-warehouse-lint-cli-for-ci/`; `openspec list --json` no longer shows it as active.
  - **Validation**: `openspec list --json` does not include the change name in the active list; archived directory exists in the repo and is committed.
<!-- opsx:tdd:14.1:end -->

## 15. Cross-repo follow-up

Moved to Linear: **[PER-182 — Roll out warehouse lint in hl-knowledge-market](https://linear.app/shadowsong-personal/issue/PER-182/roll-out-warehouse-lint-in-hl-knowledge-market)** (under the `harness-improvements` project). That ticket tracks the warehouse-side migration (agent frontmatter), the broken-knowledge-link fixes, and the lint CI workflow — all of which modify `hl-knowledge-market`, not `agentic-beacon`.

<!-- opsx:metadata:begin -->
---

## Enhancement Metadata

**Enhanced**: 2026-05-17
**Methodology**: Spec-Driven Development + TDD
**Enhancements Applied**:
- TDD Workflow Header
- Repositories & Branches table
- Phase summaries (Goal/Input/Output/Validation)
- Task-level TDD criteria on 56 task(s)
- 73 test case(s) across complex tasks
- 4 task(s) flagged [MANUAL]

**Status**: Ready for implementation via `/opsx-apply <name>`.
<!-- opsx:metadata:end -->
