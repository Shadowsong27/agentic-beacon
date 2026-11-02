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
| `agentic-beacon` | `~/Code/agentic-beacon` | `openspec/context-frontmatter-description-lint` | Code changes — lint severity, context frontmatter rule, tests, site-docs |
| `hl-knowledge-market` | `~/Code/knowledge/hl-knowledge-market` | `main` | Not involved — adding descriptions to warehouse contexts is AB-118, a separate foreground item after this merges |
<!-- opsx:repos-table:end -->

## 1. Lint severity model

<!-- opsx:phase-summary:1:begin -->
**Goal**: Give lint findings a severity so a rule can warn without failing the run (design D1, D2).
**Input**: LintFinding has no severity; CLI exits 1 on any finding.
**Output**: LintFinding.severity, LintReport.errors/warnings, CLI renders both and exits 1 only on errors.
**Validation**: pytest libs/beacon/tests/unit/domains/warehouse/test_lint.py -v
<!-- opsx:phase-summary:1:end -->


- [x] 1.1 Add `severity: Literal["error", "warning"] = "error"` to `LintFinding`, and
      `errors` / `warnings` properties to `LintReport`; make `LintReport.__bool__` return
      `bool(self.errors)` (design D1, R4).
<!-- opsx:tdd:1.1:begin -->
  - **Input**: pytest libs/beacon/tests/unit/domains/warehouse/test_lint.py -v
  - **Expected Output**: All existing lint tests pass unchanged; new report tests pass
  - **Validation**: A LintReport with only warning findings is falsy and has empty errors; a report with one default-severity finding is truthy
  - **TDD Test Cases (write these first):**
    - TC1: LintFinding built without severity → severity == 'error'
    - TC2: report of two warnings → errors == (), len(warnings) == 2, bool(report) is False
    - TC3: report of one error and one warning → bool(report) is True, both properties partition findings
    - TC4: empty report → falsy, both properties empty
<!-- opsx:tdd:1.1:end -->
- [x] 1.2 Update `_print_lint_report` in `cli/warehouse.py` to render `error:` / `warning:`
      prefixes and the three summary lines from design D2, keeping `rich.markup.escape()`.
<!-- opsx:tdd:1.2:begin -->
  - **Input**: pytest libs/beacon/tests/unit/domains/warehouse/test_lint.py -v -k print_lint_report
  - **Expected Output**: Output lines carry 'error:' or 'warning:' prefixes and the D2 summary line
  - **Validation**: String assertions on captured Console output pass
  - **TDD Test Cases (write these first):**
    - TC1: no findings → '✓ Lint passed.' only
    - TC2: warnings only → 'warning:' lines and '✓ Lint passed with N warning(s) across K file(s).'
    - TC3: errors only → summary text identical to current 'Found N error(s) across K file(s).'
    - TC4: errors and warnings → 'Found N error(s) and M warning(s) across K file(s).'
    - TC5: message containing '[bold]' → printed literally (escape preserved)
<!-- opsx:tdd:1.2:end -->
- [x] 1.3 Change `warehouse_lint` to exit `1 if report.errors else 0` and update its
      docstring (validated rules list, exit codes) (design D1, D8).
<!-- opsx:tdd:1.3:begin -->
  - **Input**: CliRunner invoke `abc warehouse lint <fixture>`
  - **Expected Output**: exit 0 for warnings-only fixture, exit 1 for any error
  - **Validation**: result.exit_code assertions pass
  - **TDD Test Cases (write these first):**
    - TC1: warnings-only warehouse → exit 0
    - TC2: one error plus warnings → exit 1
    - TC3: clean warehouse → exit 0
<!-- opsx:tdd:1.3:end -->

## 2. Context frontmatter rule

<!-- opsx:phase-summary:2:begin -->
**Goal**: Validate context description frontmatter (design D3, D4, D5, D6).
**Input**: Phase 1 merged in the branch; contexts unchecked by lint.
**Output**: ContextFrontmatter model and _lint_context_frontmatter wired into lint_warehouse, with unit and integration tests.
**Validation**: pytest libs/beacon/tests/unit/domains/warehouse libs/beacon/tests/integration/domains/warehouse
<!-- opsx:phase-summary:2:end -->


- [x] 2.1 Add `domains/warehouse/context_frontmatter.py` with `ContextFrontmatter`
      (`extra="forbid"`, strict optional string `description`, non-empty validator)
      (design D3, D6).
<!-- opsx:tdd:2.1:begin -->
  - **Input**: pytest libs/beacon/tests/unit/domains/warehouse/test_lint.py -v -k context_frontmatter
  - **Expected Output**: ContextFrontmatter accepts {'description': 'text'} and {} and rejects the error cases
  - **Validation**: ValidationError raised exactly for the error cases
  - **TDD Test Cases (write these first):**
    - TC1: {'description': 'Load when working on CI.'} → valid
    - TC2: {} → valid, description None
    - TC3: {'description': ''} or '   ' → ValidationError
    - TC4: {'description': 3} → ValidationError (no coercion)
    - TC5: {'description': 'x', 'load': 'always'} → ValidationError naming 'load'
    - TC6: {'description': None} → valid, treated as missing
<!-- opsx:tdd:2.1:end -->
- [x] 2.2 Add `_lint_context_frontmatter` to `lint.py` after `_lint_agent_frontmatter`,
      scanning `contexts/**/*.md` except `README.md`, mapping parse and validation results
      to warnings and errors per design D4 and D5; call it from `lint_warehouse`.
<!-- opsx:tdd:2.2:begin -->
  - **Input**: pytest libs/beacon/tests/unit/domains/warehouse/test_lint.py -v
  - **Expected Output**: Findings match design D4 per fixture; findings sorted with the rest
  - **Validation**: Each fixture yields the exact severity and count listed in the test cases
  - **TDD Test Cases (write these first):**
    - TC1: context with valid description → no finding
    - TC2: context with no frontmatter → 1 warning
    - TC3: frontmatter without description → 1 warning
    - TC4: unterminated frontmatter → 1 error
    - TC5: invalid YAML → 1 error
    - TC6: frontmatter that is a YAML list → 1 error
    - TC7: unknown key → 1 error naming the key
    - TC8: contexts/teams/backend.md without description → warning with path contexts/teams/backend.md
    - TC9: contexts/README.md and contexts/teams/README.md → no finding
    - TC10: no contexts/ dir → no finding, no crash
<!-- opsx:tdd:2.2:end -->
- [x] 2.3 Unit tests in `tests/unit/domains/warehouse/test_lint.py`: valid description
      (no finding); no frontmatter (one warning); frontmatter without description (one
      warning); unterminated / bad YAML / non-mapping frontmatter (error); unknown key
      (error naming the key); empty and non-string description (error); subdirectory
      context is checked; `contexts/README.md` is skipped. Use `parametrize` for the
      input-only error variants.
- [x] 2.4 Report and CLI tests: a warnings-only report prints `warning:` and the
      "passed with N warning(s)" line and exits 0; a mixed report exits 1 and prints both
      counts; an error-only report keeps today's summary text. Extend the existing
      `_print_lint_report` and CLI tests rather than adding parallel classes.
- [x] 2.5 Confirm a fresh `abc warehouse init` warehouse still prints `✓ Lint passed.` and
      exits 0 (extend the existing clean-fixture CLI test in
      `tests/integration/domains/warehouse/test_lint_cli.py` with a context that has a
      valid description, and assert a context without one yields a warning and exit 0).
<!-- opsx:tdd:2.5:begin -->
  - **Input**: pytest libs/beacon/tests/integration/domains/warehouse/test_lint_cli.py -v
  - **Expected Output**: Clean fixture with a described context → exit 0 and 'Lint passed'; undescribed context → exit 0 and 'warning:'
  - **Validation**: Subprocess returncode and stdout assertions pass
<!-- opsx:tdd:2.5:end -->

## 3. Wiring unchanged

<!-- opsx:phase-summary:3:begin -->
**Goal**: Prove frontmatter does not change what abc sync wires (design D7).
**Input**: Wiring writes only paths today.
**Output**: A test pinning identical wiring with and without frontmatter.
**Validation**: pytest libs/beacon/tests/unit -k wiring
<!-- opsx:phase-summary:3:end -->


- [x] 3.1 Add a unit test that runs context wiring (`wire_contexts_claudecode` and
      `wire_contexts_opencode`) over a contexts dir holding one context with frontmatter
      and one without, and asserts the `@` lines and `opencode.json` instruction entries
      are exactly the paths, identical to a run with no frontmatter (design D7).
<!-- opsx:tdd:3.1:begin -->
  - **Input**: pytest libs/beacon/tests/unit -k wiring -v
  - **Expected Output**: Wiring output identical with and without frontmatter
  - **Validation**: CLAUDE.md @ lines and opencode.json instructions equal the sorted context paths in both runs
  - **TDD Test Cases (write these first):**
    - TC1: one context with frontmatter, one without → CLAUDE.md contains exactly two @ path lines
    - TC2: same dir → opencode.json instructions list exactly the two paths
    - TC3: rerun after removing frontmatter → byte-identical CLAUDE.md and opencode.json
<!-- opsx:tdd:3.1:end -->

## 4. Documentation

<!-- opsx:phase-summary:4:begin -->
**Goal**: Document the field and the rule in site-docs (design D8).
**Input**: Docs say lint enforces no shape in contexts/.
**Output**: Contexts guide subsection and cli.md rule 7 plus exit-code text.
**Validation**: Read the rendered pages; mkdocs build if configured passes
<!-- opsx:phase-summary:4:end -->


- [x] 4.1 In `site-docs/guides/creating-knowledge-and-contexts.md`, add a "Context
      frontmatter" subsection under Contexts (field, example, guidance, lint behaviour),
      and correct the line-77 statement that lint enforces no shape in `contexts/` (design D8).
- [x] 4.2 In `site-docs/reference/cli.md`, add rule 7 (context frontmatter) to the
      `abc warehouse lint` rule list and update the exit-code text: warnings print with
      `warning:` and never change the exit code (design D8).

## 5. Verification

<!-- opsx:phase-summary:5:begin -->
**Goal**: Confirm the full suite, lint hooks, the CLI happy path and a real harness import.
**Input**: Phases 1-4 complete.
**Output**: Green suite and recorded happy-path and claude -p evidence in the PR.
**Validation**: pytest and pre-commit exit 0; PR description holds the 5.2 and 5.3 evidence
<!-- opsx:phase-summary:5:end -->


- [x] 5.1 Run `pytest` from the repo root and `pre-commit run --all-files`; both pass.
<!-- opsx:tdd:5.1:begin -->
  - **Input**: pytest && pre-commit run --all-files (from repo root)
  - **Expected Output**: Zero failed tests; every hook Passed, no files modified
  - **Validation**: Both commands exit 0
<!-- opsx:tdd:5.1:end -->
- [x] 5.2 Happy path: create a scratch warehouse with `abc warehouse init`, add one
      context with a valid description, one without frontmatter, and one with an unknown
      key; run `abc warehouse lint` and confirm one warning, one error, exit 1; remove the
      bad one and confirm exit 0 with the warning summary.
<!-- opsx:tdd:5.2:begin -->
  - **Input**: abc warehouse init /tmp/wh && add three contexts && abc warehouse lint /tmp/wh
  - **Expected Output**: 1 warning, 1 error, exit 1; after removing the bad context, warning summary and exit 0
  - **Validation**: Exit codes and summary lines match design D2
<!-- opsx:tdd:5.2:end -->
- [ ] 5.3 End-to-end harness check: in a scratch project whose `CLAUDE.md` `@`-imports a
      context that starts with a `description` frontmatter block and holds a unique marker
      rule in its body, run `claude -p "Quote the marker rule from your loaded context"` and
      confirm the reply contains the marker. Record the command and reply in the PR
      description (design D7).
<!-- opsx:tdd:5.3:begin -->
  - **Input**: claude -p "Quote the marker rule from your loaded context" in a scratch project whose CLAUDE.md @-imports the frontmatter context
  - **Expected Output**: Reply contains the unique marker string
  - **Validation**: Marker present in reply; command and reply pasted into the PR description
<!-- opsx:tdd:5.3:end -->

<!-- opsx:metadata:begin -->
---

## Enhancement Metadata

**Enhanced**: 2026-11-02
**Methodology**: Spec-Driven Development + TDD
**Enhancements Applied**:
- TDD Workflow Header
- Repositories & Branches table
- Phase summaries (Goal/Input/Output/Validation)
- Task-level TDD criteria on 10 task(s)
- 31 test case(s) across complex tasks
- 0 task(s) flagged [MANUAL] (blocking pause)
- 0 task(s) flagged [MANUAL-DEFER] (non-blocking)
- 0 task(s) flagged [OPS]
- 0 task(s) routed to Cross-Repo Follow-ups

**Status**: Ready for implementation.
<!-- opsx:metadata:end -->
