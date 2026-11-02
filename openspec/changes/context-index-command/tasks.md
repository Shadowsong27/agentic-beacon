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
| `agentic-beacon` | `~/Code/agentic-beacon` | `openspec/context-index-command` | Code changes — abc context index command, domain module, git and frontmatter helpers, tests, site-docs |
| `hl-knowledge-market` | `~/Code/knowledge/hl-knowledge-market` | `main` | Not involved — the warehouse the command reads; used read-only for the task 5.3 smoke run, never edited |
| `agentic-conductor` | `~/Code/agentic-conductor` | `main` | Not involved — the HARN-433 selector consumes the JSON in a separate ticket |
<!-- opsx:repos-table:end -->

## 1. Shared readers

<!-- opsx:phase-summary:1:begin -->
**Goal**: Give the domain a way to parse frontmatter from text and to read git objects at a SHA.
**Input**: origin/main @ 427f4ec: parse_frontmatter reads only from disk; utils/git.py has get_file_hash_at_sha only.
**Output**: parse_frontmatter_text in core/dependencies/frontmatter.py; resolve_commit, list_tree_paths, read_blob in utils/git.py.
**Validation**: pytest libs/beacon/tests/unit/core/dependencies/test_frontmatter.py passes unchanged; test_architecture.py passes.
<!-- opsx:phase-summary:1:end -->


- [ ] 1.1 Add `parse_frontmatter_text(content: str) -> FrontmatterResult` to
      `core/dependencies/frontmatter.py` and make `parse_frontmatter(path)` delegate to it
      after its file checks (design D8, R7). Existing frontmatter tests pass unchanged.
<!-- opsx:tdd:1.1:begin -->
  - **Input**: pytest libs/beacon/tests/unit/core/dependencies/test_frontmatter.py -v
  - **Expected Output**: All existing tests pass with no edits to them; new parametrized cases for parse_frontmatter_text pass.
  - **Validation**: Zero failed tests; parse_frontmatter results for every existing fixture are identical (design R7).
  - **Note**: Extend the existing test file with parametrize; do not duplicate the parse_frontmatter cases (testing context, Test Scope).
  - **TDD Test Cases (write these first):**
    - TC1: text with valid frontmatter containing description → success, data dict with the key
    - TC2: text with no leading --- → error missing-frontmatter
    - TC3: opener with no closing --- → error unterminated-frontmatter
    - TC4: invalid YAML between markers → error yaml-parse-error
    - TC5: frontmatter that parses to a list or scalar → error invalid-frontmatter
    - TC6: leading BOM and blank lines before --- → parsed as with parse_frontmatter today
<!-- opsx:tdd:1.1:end -->
- [ ] 1.2 Add `resolve_commit`, `list_tree_paths` and `read_blob` to `utils/git.py`,
      copying the subprocess pattern of `get_file_hash_at_sha` (10 s timeout, `None` on
      failure). `resolve_commit` uses `rev-parse --verify --quiet <ref>^{commit}` (design D4).

## 2. Domain

<!-- opsx:phase-summary:2:begin -->
**Goal**: Build the context index from a warehouse and a ref, with the description rules and errors of design D2-D7.
**Input**: Phase 1 helpers.
**Output**: domains/warehouse/context_index.py with ContextEntry, ContextIndex, ContextIndexError, describe_context, resolve_index_warehouse, build_context_index.
**Validation**: Unit tests for describe_context pass; the module imports nothing from cli/.
<!-- opsx:phase-summary:2:end -->


- [ ] 2.1 Create `domains/warehouse/context_index.py` with `ContextEntry`, `ContextIndex`
      (with `to_dict()`), `ContextIndexError`, and the pure `describe_context` that applies
      the description rules of design D3 and the naming of design D6.
- [ ] 2.2 Add `resolve_index_warehouse(warehouse, cwd)`: use `--warehouse` when given, else
      the connected warehouse from `config.toml` via `WorkspaceConfig`, then
      `validate_warehouse_path`; raise `ContextIndexError` with the messages in design D2
      and D7.
- [ ] 2.3 Add `build_context_index(warehouse, ref)`: resolve the ref (D4), list the file
      set (D5), read each blob (D9), describe each, sort by path, and collect warnings.
      Raise `ContextIndexError` for an unknown ref, no `contexts/` at the commit, or a git
      failure (D7).
- [ ] 2.4 Unit-test `describe_context` for each D3 case (usable string stripped; no
      frontmatter; parse error; key absent; non-string; empty; whitespace-only; invalid
      UTF-8) and for D6 naming of a nested path, using `parametrize`.
<!-- opsx:tdd:2.4:begin -->
  - **Input**: pytest libs/beacon/tests/unit/domains/warehouse -k describe_context -v
  - **Expected Output**: One parametrized test passes for every case below.
  - **Validation**: Zero failures; a mutant that drops the whitespace check fails TC5.
  - **TDD Test Cases (write these first):**
    - TC1: frontmatter description '  Python rules.  ' → description 'Python rules.', no warning
    - TC2: no frontmatter → description '', warning names the path
    - TC3: unterminated or invalid YAML frontmatter → description '', warning
    - TC4: frontmatter without description key, other keys present → description '', warning; other keys ignored
    - TC5: description is whitespace-only or empty → description '', warning
    - TC6: description is an int or a list → description '', warning
    - TC7: blob is not valid UTF-8 (text None) → description '', warning
    - TC8: path contexts/teams/backend.md → name 'teams/backend', path unchanged
    - TC9: path contexts/testing.md → name 'testing'
<!-- opsx:tdd:2.4:end -->

## 3. CLI

<!-- opsx:phase-summary:3:begin -->
**Goal**: Expose the index as abc context index with a thin handler.
**Input**: Phase 2 domain module.
**Output**: cli/context.py registered in cli/main.py; abc context index --help works.
**Validation**: .venv/bin/abc context index --help exits 0 and lists --warehouse and --ref; test_architecture.py passes with no new whitelist entry.
<!-- opsx:phase-summary:3:end -->


- [ ] 3.1 Create `cli/context.py` with the `context` group and the `index` command
      (`--warehouse PATH`, `--ref TEXT` default `HEAD`). The handler makes one domain call,
      echoes `warning: <path>: <reason>` lines and `error: <message>` to stderr, prints the
      JSON from design D1 to stdout, and exits 1 on `ContextIndexError` (design D7, D8).
- [ ] 3.2 Register the group in `cli/main.py`. `tests/unit/test_architecture.py` passes
      with no new whitelist entry.

## 4. Integration test

<!-- opsx:phase-summary:4:begin -->
**Goal**: Prove the command end to end against a real temporary git warehouse, including every exit-1 case.
**Input**: Phases 1-3.
**Output**: An integration test module under libs/beacon/tests/integration/.
**Validation**: pytest -m integration -k context_index passes.
<!-- opsx:phase-summary:4:end -->


- [ ] 4.1 In `tests/integration/`, build a temporary git warehouse with two commits and run
      the real CLI through Click's `CliRunner` with separate stdout and stderr. Cover: the
      D1 shape and `sha` equal to the resolved commit; `--ref` of the first commit returns
      that commit's file set; a nested context and a `README.md` (D5, D6); a context with no
      frontmatter listed with `""` and one stderr warning (D3); an uncommitted working-tree
      edit not shown (D9); stdout parses as JSON while a non-empty `pending.yaml` exists in
      the working directory (R6).
<!-- opsx:tdd:4.1:begin -->
  - **Input**: pytest libs/beacon/tests/integration -k context_index -v
  - **Expected Output**: All happy-path cases pass; stdout of each run parses with json.loads into the design D1 shape.
  - **Validation**: Zero failures; sha equals git rev-parse of the ref used; entries sorted by path.
  - **TDD Test Cases (write these first):**
    - TC1: default ref → sha equals HEAD of the temp warehouse, ref is 'HEAD'
    - TC2: --ref <first commit sha> → only the contexts present at that commit
    - TC3: contexts/README.md present → not listed; contexts/teams/backend.md → listed as 'teams/backend'
    - TC4: context without frontmatter → listed with description '', exactly one 'warning: <path>:' line on stderr, exit 0
    - TC5: uncommitted edit to a context description in the working tree → output shows the committed description
    - TC6: non-empty .agentic-beacon/pending.yaml in cwd → stdout still parses as JSON
<!-- opsx:tdd:4.1:end -->
- [ ] 4.2 Cover the exit-1 cases with empty stdout and an `error:` line on stderr: unknown
      ref, missing path, path not a git repository, no `--warehouse` and no `config.toml`,
      commit with no `contexts/` (D2, D4, D5, D7). Cover the connected-warehouse default
      once with a `config.toml` pointing at the temporary warehouse.
<!-- opsx:tdd:4.2:begin -->
  - **Input**: pytest libs/beacon/tests/integration -k context_index -v
  - **Expected Output**: Each error case exits 1 with empty stdout and one stderr line starting 'error:'.
  - **Validation**: Zero failures; connected-default case exits 0 with warehouse equal to the config.toml path.
  - **TDD Test Cases (write these first):**
    - TC1: --ref does-not-exist → exit 1, "error: ref 'does-not-exist' not found in warehouse <path>"
    - TC2: --warehouse /nonexistent → exit 1, error names the path
    - TC3: --warehouse <plain dir, not a git repo> → exit 1, error
    - TC4: no --warehouse, no .agentic-beacon/config.toml in cwd → exit 1, error mentions --warehouse and abc warehouse connect
    - TC5: commit with no contexts/ directory → exit 1, 'error: no contexts/ directory at <sha>'
    - TC6: no --warehouse, config.toml points at the temp warehouse → exit 0, index printed
<!-- opsx:tdd:4.2:end -->

## 5. Docs and verification

<!-- opsx:phase-summary:5:begin -->
**Goal**: Document the command and its JSON contract, and verify the full suite and a real run.
**Input**: Phases 1-4.
**Output**: site-docs/reference/cli.md section and Quick Reference row; green pytest and pre-commit; smoke-run evidence in the PR description.
**Validation**: pytest and pre-commit run --all-files exit 0; the PR description shows the smoke command and its sha line.
<!-- opsx:phase-summary:5:end -->


- [ ] 5.1 Document `abc context index` in `site-docs/reference/cli.md` and add a Quick
      Reference row (design D10).
- [ ] 5.2 Run `pytest` from the repo root and `pre-commit run --all-files`; both pass.
<!-- opsx:tdd:5.2:begin -->
  - **Input**: pytest && pre-commit run --all-files
  - **Expected Output**: Exit code 0 for both; no files modified by hooks.
  - **Validation**: Zero failed tests; pre-commit reports Passed for every hook.
<!-- opsx:tdd:5.2:end -->
- [ ] 5.3 Run `.venv/bin/abc context index` against a real warehouse clone and record the
      command, the `sha` line and the context count in the PR description.
<!-- opsx:tdd:5.3:begin -->
  - **Input**: .venv/bin/abc context index --warehouse <warehouse clone> --ref HEAD
  - **Expected Output**: Exit 0; JSON with a 40-hex sha and one entry per contexts/*.md except README.md; a warning per context without a description.
  - **Validation**: Entry count equals git ls-tree count of contexts/**/*.md minus README.md; command, sha and count pasted in the PR description.
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
- Task-level TDD criteria on 6 task(s)
- 27 test case(s) across complex tasks
- 0 task(s) flagged [MANUAL] (blocking pause)
- 0 task(s) flagged [MANUAL-DEFER] (non-blocking)
- 0 task(s) flagged [OPS]
- 0 task(s) routed to Cross-Repo Follow-ups

**Status**: Ready for implementation.
<!-- opsx:metadata:end -->
