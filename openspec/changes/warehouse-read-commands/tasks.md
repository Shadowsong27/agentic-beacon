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
| `agentic-beacon` | `~/repos/agentic-beacon` | `feat/warehouse-read-commands` | Code changes — new abc read commands, domain modules, tests, site-docs |
| `agentic-conductor` | `~/repos/agentic-conductor` | `main` | Not involved — consumer; its migration to these commands is separate tickets |
| `hl-knowledge-market` | `~/repos/hl-knowledge-market` | `main` | Not involved — the warehouse read by the commands; no edits |
<!-- opsx:repos-table:end -->

## 1. Shared helpers

<!-- opsx:phase-summary:1:begin -->
**Goal**: Add the format splitters the read commands share, without changing existing behaviour.
**Input**: origin/main @ 3bf855a
**Output**: split_frontmatter, public is_context_path, split_owned_imports
**Validation**: Unit tests pass; existing frontmatter, sync and diagnostics tests pass unchanged
<!-- opsx:phase-summary:1:end -->


- [x] 1.1 Add `split_frontmatter(text) -> FrontmatterSplit` to
      `core/dependencies/frontmatter.py` with the line-based rule, null/warning cases and
      `str()` conversion of non-JSON values (design D5). Leave `parse_frontmatter_text`
      unchanged.
<!-- opsx:tdd:1.1:begin -->
  - **Input**: split_frontmatter(text) on in-memory strings; uv run pytest libs/beacon/tests/unit -q -k split_frontmatter
  - **Expected Output**: FrontmatterSplit(frontmatter, body, warning) per design D5
  - **Validation**: All split_frontmatter cases pass; existing test_frontmatter.py passes unchanged
  - **TDD Test Cases (write these first):**
    - TC1: '---\nname: a\n---\n# A\n' → frontmatter {'name': 'a'}, body '# A\n', warning None
    - TC2: no leading '---' line → frontmatter None, body == text, warning None
    - TC3: opener but no closing line → frontmatter None, body == text, warning None
    - TC4: block with invalid YAML → frontmatter None, body is text after closing line, warning names the reason
    - TC5: block parses to a list → frontmatter None, warning 'not a YAML object'
    - TC6: leading BOM before '---' → parsed as frontmatter
    - TC7: value 'a --- b' inside the block → closing line is the next line equal to '---', not the inline match
    - TC8: date value → converted with str() so json.dumps succeeds
<!-- opsx:tdd:1.1:end -->
- [x] 1.2 Rename `_is_context_path` to public `is_context_path` in
      `domains/warehouse/context_index.py` and update its one caller (design D7).
- [x] 1.3 Add public `split_owned_imports(content) -> tuple[list[str], list[str]]` to
      `domains/setup/wiring.py`, returning owned refs in file order with duplicates, and
      re-implement `_strip_owned_refs` as `set(refs)` over it (design D8, R7). Existing
      sync and diagnostics tests pass unchanged.
<!-- opsx:tdd:1.3:begin -->
  - **Input**: uv run pytest libs/beacon/tests/unit -q -k 'owned_imports or wiring' && uv run pytest libs/beacon/tests/integration/test_sync_wiring.py -q
  - **Expected Output**: split_owned_imports returns ordered refs with duplicates and the kept lines
  - **Validation**: New cases pass; test_sync_wiring.py and test_diagnostics.py pass unchanged (design R7)
  - **TDD Test Cases (write these first):**
    - TC1: two owned @ lines and prose → refs in file order, prose lines kept with line endings
    - TC2: same owned ref twice → listed twice in refs
    - TC3: '@AGENTS.md' and '@docs/x.md' → not owned, kept
    - TC4: '  @.agentic-beacon/artifacts/contexts/a.md  ' (surrounding spaces) → owned (strip() rule)
    - TC5: '@./.agentic-beacon/artifacts/contexts/a.md' → not owned, kept (design D8, R4)
<!-- opsx:tdd:1.3:end -->

## 2. Warehouse read domain

<!-- opsx:phase-summary:2:begin -->
**Goal**: Implement the five warehouse reads with the missing vs unreadable split.
**Input**: Phase 1 helpers
**Output**: domains/warehouse/warehouse_read.py
**Validation**: Unit tests for warehouse_read pass
<!-- opsx:phase-summary:2:end -->


- [x] 2.1 Create `domains/warehouse/warehouse_read.py` with `WarehouseReadError`,
      `ItemMissingError(WarehouseReadError)` holding the missing paths, the file-record
      and result dataclasses with `to_dict()` in the shapes of design D5 and D6, and a
      per-item read that uses `list_tree_paths` exact match for missing (exit 3) versus
      `None` for unreadable (exit 1), then `read_blob` and UTF-8 decode (design D3, D9).
<!-- opsx:tdd:2.1:begin -->
  - **Input**: uv run pytest libs/beacon/tests/unit -q -k warehouse_read
  - **Expected Output**: Missing path raises ItemMissingError; list_tree_paths None or read_blob None or non-UTF-8 raises WarehouseReadError
  - **Validation**: Each branch of the per-item read is covered by a test against a real tmp git repo or the integration suite
  - **Note**: ItemMissingError subclasses WarehouseReadError, so the CLI must catch it first (design D9).
<!-- opsx:tdd:2.1:end -->
- [x] 2.2 Add `read_contexts(warehouse, ref, cwd, names)` with the name check of design
      D4, de-duplicated input order, and one `ItemMissingError` naming every missing path.
<!-- opsx:tdd:2.2:begin -->
  - **Input**: abc context show alpha teams/beta --warehouse <fixture> --ref <sha>
  - **Expected Output**: Exit 0; JSON {warehouse, ref, sha, contexts:[alpha, teams/beta]} in input order
  - **Validation**: json.loads(stdout) succeeds; records carry name, path, text, frontmatter, body
  - **TDD Test Cases (write these first):**
    - TC1: two existing names → both records, in the order given
    - TC2: 'alpha alpha' → one record
    - TC3: one existing and two missing names → exit 3, stderr names both missing paths and the SHA, stdout empty
    - TC4: name 'alpha.md' → exit 2
    - TC5: name '../x' or 'a//b' → exit 2
    - TC6: subdirectory name 'teams/beta' → path contexts/teams/beta.md
<!-- opsx:tdd:2.2:end -->
- [x] 2.3 Add `read_intake_policy` and `read_operate_profile`, mapping BOARD and DOMAIN to
      `contexts/intake-policy-<BOARD>.md` and `contexts/operate-<DOMAIN>.md` (design D4, D6).
<!-- opsx:tdd:2.3:begin -->
  - **Input**: abc context intake-policy AB --warehouse <fixture>; abc context operate-profile conductor --warehouse <fixture>
  - **Expected Output**: Exit 0; JSON with board/policy and domain/profile keys, paths contexts/intake-policy-AB.md and contexts/operate-conductor.md
  - **Validation**: Missing board or domain exits 3; 'A/B' or '-x' exits 2
  - **TDD Test Cases (write these first):**
    - TC1: existing board → policy record, name intake-policy-AB
    - TC2: absent board ZZ → exit 3
    - TC3: board 'ab' when only 'AB' exists → exit 3 (case-sensitive)
    - TC4: domain 'airflow-platform' → valid
    - TC5: domain 'x.y' or '../x' → exit 2
<!-- opsx:tdd:2.3:end -->
- [x] 2.4 Add `read_agents(warehouse, ref, cwd, names)` reading `agents/<NAME>.md`; exit 1
      when the SHA has no `agents/` directory (design D3, D6).
<!-- opsx:tdd:2.4:begin -->
  - **Input**: abc agent show context-selector --warehouse <fixture>
  - **Expected Output**: Exit 0; agents[0].frontmatter.name == 'context-selector'; body has no frontmatter block
  - **Validation**: Missing agent exits 3; a SHA with no agents/ exits 1
  - **TDD Test Cases (write these first):**
    - TC1: existing agent → record with parsed frontmatter and body
    - TC2: missing agent name → exit 3
    - TC3: commit with no agents/ directory → exit 1
    - TC4: agent with broken frontmatter → exit 0, frontmatter null, one stderr warning
<!-- opsx:tdd:2.4:end -->
- [x] 2.5 Add the pure `decision_rules_section(text)` and `read_decision_rules` with the
      exact algorithm, ordering, naming and empty-result rules of design D7.
<!-- opsx:tdd:2.5:begin -->
  - **Input**: uv run pytest libs/beacon/tests/unit -q -k decision_rules; abc context decision-rules --warehouse <fixture>
  - **Expected Output**: rules list sorted by path, one entry per context with a '## Decision rules' heading
  - **Validation**: Bodies equal the conductor algorithm's output for the same text (design D7)
  - **TDD Test Cases (write these first):**
    - TC1: section followed by '## Next' → body stops before '## Next'
    - TC2: section followed by a '---' line → body stops before it
    - TC3: section at end of file → body runs to EOF
    - TC4: leading and trailing blank lines → dropped, no trailing newline
    - TC5: two '## Decision rules' headings → only the first is used
    - TC6: heading with empty body → included with body ''
    - TC7: no context has the heading → exit 0, rules []
    - TC8: '### Decision rules' (h3) → not matched
<!-- opsx:tdd:2.5:end -->

## 3. Project instructions domain

<!-- opsx:phase-summary:3:begin -->
**Goal**: Read a repo AGENTS.md at a ref with beacon-owned imports removed.
**Input**: split_owned_imports and the error types from phase 2
**Output**: domains/setup/project_instructions.py
**Validation**: Unit tests for project_instructions pass
<!-- opsx:phase-summary:3:end -->


- [x] 3.1 Create `domains/setup/project_instructions.py` with
      `read_project_instructions(repo, ref)`: validate the repo path, resolve the ref, read
      root `AGENTS.md` at the SHA (missing → `ItemMissingError`), strip with
      `split_owned_imports`, collapse blank runs, trim, and return `repo`, `ref`, `sha`,
      `path`, `text`, `removed` (design D8).
<!-- opsx:tdd:3.1:begin -->
  - **Input**: abc project instructions --repo <fixture-project> --ref <sha>
  - **Expected Output**: Exit 0; JSON {repo, ref, sha, path: 'AGENTS.md', text, removed}
  - **Validation**: text has no owned @ lines, ends with exactly one newline; removed lists paths in file order
  - **TDD Test Cases (write these first):**
    - TC1: AGENTS.md with prose and three owned imports → removed has three paths, text keeps prose
    - TC2: removal leaves 3+ blank lines in a row → collapsed to one blank line
    - TC3: AGENTS.md of only owned imports → text '', removed non-empty
    - TC4: no AGENTS.md at the ref → exit 3
    - TC5: --repo pointing at a non-repo directory → exit 1
    - TC6: uncommitted edit to AGENTS.md → output reflects the committed version
<!-- opsx:tdd:3.1:end -->

## 4. CLI

<!-- opsx:phase-summary:4:begin -->
**Goal**: Expose the six reads as thin Click handlers with the D3 exit codes.
**Input**: Phase 2 and 3 domain functions
**Output**: abc context show/intake-policy/operate-profile/decision-rules, abc agent show, abc project instructions
**Validation**: abc <cmd> --help works; test_architecture.py passes
<!-- opsx:phase-summary:4:end -->


- [x] 4.1 Add `show`, `intake-policy`, `operate-profile` and `decision-rules` to
      `cli/context.py`, each with `--warehouse` and `--ref` (design D1, D2). Name checks
      raise `click.BadParameter` (exit 2).
- [x] 4.2 Add an `agent` group with `show` to `cli/agent.py`, and a new `cli/project.py`
      with a `project` group and `instructions` (`--repo`, `--ref`). Register both in
      `cli/main.py`. Keep `abc list` unchanged.
- [x] 4.3 In every handler: one domain call, catch `ItemMissingError` → exit 3 before
      `WarehouseReadError` → exit 1, `error: <message>` and `warning: ...` lines on stderr,
      JSON on stdout only on success (design D3, D6). `test_architecture.py` passes.
<!-- opsx:tdd:4.3:begin -->
  - **Input**: uv run pytest libs/beacon/tests/unit/test_architecture.py -q
  - **Expected Output**: All architecture tests pass
  - **Validation**: Zero failures; no handler has I/O, free functions, or more than one domain call
<!-- opsx:tdd:4.3:end -->

## 5. Tests

<!-- opsx:phase-summary:5:begin -->
**Goal**: Prove each command's contract end to end against fixture repos.
**Input**: Phases 1-4
**Output**: Unit and integration tests
**Validation**: uv run pytest exits 0
<!-- opsx:phase-summary:5:end -->


- [x] 5.1 Unit tests for `split_frontmatter`, `decision_rules_section`,
      `split_owned_imports` and the name checks, extending existing test files where they
      exist (testing.md Test Scope).
- [x] 5.2 Integration tests against a fixture git warehouse and a fixture project repo
      through `CliRunner`: success JSON and SHA per command, exit 3 for each missing item,
      exit 1 for a missing path, a non-repo and an unknown ref, exit 2 for a bad name, an
      uncommitted edit not changing the output, `git status --porcelain` unchanged, and
      `json.loads(stdout)` with a non-empty `pending.yaml` present (design D10, R6).
<!-- opsx:tdd:5.2:begin -->
  - **Input**: uv run pytest libs/beacon/tests/integration -q -k read
  - **Expected Output**: All new integration tests pass
  - **Validation**: Each exit code 0/1/2/3 is asserted at least once per command family; git status --porcelain unchanged after each command
  - **Note**: Mutation check: change the exit-3 mapping to 1 in a scratch copy and confirm a test fails (testing.md Test Quality).
<!-- opsx:tdd:5.2:end -->
- [ ] 5.3 Run `uv run pytest` from the repo root; all tests pass.
<!-- opsx:tdd:5.3:begin -->
  - **Input**: uv run pytest
  - **Expected Output**: Exit 0
  - **Validation**: Zero failed tests, zero errors
<!-- opsx:tdd:5.3:end -->

## 6. Docs

<!-- opsx:phase-summary:6:begin -->
**Goal**: List the commands in site-docs.
**Input**: Final command shapes
**Output**: site-docs/reference/cli.md sections and Quick Reference rows
**Validation**: Docs show every command, its JSON shape and the exit-code table
<!-- opsx:phase-summary:6:end -->


- [x] 6.1 Document the six commands, their JSON shapes and the shared exit-code table in
      `site-docs/reference/cli.md`, with Quick Reference rows (design D11).

<!-- opsx:metadata:begin -->
---

## Enhancement Metadata

**Enhanced**: 2026-11-03
**Methodology**: Spec-Driven Development + TDD
**Enhancements Applied**:
- TDD Workflow Header
- Repositories & Branches table
- Phase summaries (Goal/Input/Output/Validation)
- Task-level TDD criteria on 11 task(s)
- 42 test case(s) across complex tasks
- 0 task(s) flagged [MANUAL] (blocking pause)
- 0 task(s) flagged [MANUAL-DEFER] (non-blocking)
- 0 task(s) flagged [OPS]
- 0 task(s) routed to Cross-Repo Follow-ups

**Status**: Ready for implementation.
<!-- opsx:metadata:end -->
