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
| `agentic-beacon` | `~/Code/oss/agentic-beacon` | `unify-agent-distribution` | Code changes — entire change scope: libs/beacon/ CLI + domain modules, tests, examples/sample-warehouse regeneration, site-docs |
| `Linear (PER-109, PER-113)` | `n/a — issue tracker` | `n/a` | Operational only — PER-109 closed as superseded; PER-113 marked complete on merge. No code changes. |
<!-- opsx:repos-table:end -->

## 1. Domain layer — agent install plumbing

<!-- opsx:phase-summary:1:begin -->
**Goal**: Add the project-local agent wiring primitives (wire/unwire) parallel to the existing skill wiring functions in domains/setup/wiring.py.
**Input**: Current wiring.py contains wire_contexts_*, unwire_skill, unwire_pruned_artifacts but no agent equivalents. beacon.yaml template still references global install.
**Output**: wire_agent_claudecode, wire_agent_opencode, unwire_agent functions exist; unwire_pruned_artifacts handles agents; beacon.yaml template comment matches the new model.
**Validation**: pytest libs/beacon/tests/unit/ for wiring.py passes; grep 'wire_agent_' in domains/setup/wiring.py finds the new functions; the template comment no longer contains 'AND installed globally'.
<!-- opsx:phase-summary:1:end -->


- [x] 1.1 In `libs/beacon/src/beacon/domains/setup/wiring.py`, add `wire_agent_claudecode(project_root, artifact_file) -> Path | None` that creates a symlink at `.claude/agents/<name>.md` pointing at the artifact file; idempotent; creates parent dir.
<!-- opsx:tdd:1.1:begin -->
  - **Input**: from beacon.domains.setup.wiring import wire_agent_claudecode; wire_agent_claudecode(Path('/tmp/proj'), Path('/tmp/proj/.agentic-beacon/artifacts/agents/spec-planner.md'))
  - **Expected Output**: Returns Path('/tmp/proj/.claude/agents/spec-planner.md'); the file at that path is a symlink whose readlink target equals the artifact file path.
  - **Validation**: Path exists, is_symlink() is True, readlink() resolves to the artifact_file argument; second call with same args is a no-op (no exception, returns same Path).
  - **TDD Test Cases (write these first):**
    - TC1: project has no .claude/agents/ → directory is created and symlink written
    - TC2: project already has .claude/agents/spec-planner.md as identical symlink → no-op, returns the path
    - TC3: project already has .claude/agents/spec-planner.md as a different symlink → reconciled to point at the new artifact file
    - TC4: artifact_file does not exist on disk → function still creates the symlink (lazy resolution; warehouse may produce the file later)
    - TC5: project_root is read-only filesystem → raises OSError, no partial state
<!-- opsx:tdd:1.1:end -->
- [x] 1.2 In the same file, add `wire_agent_opencode(project_root, artifact_file) -> Path | None` that creates a symlink at `.opencode/agents/<name>.md` pointing at the artifact file; idempotent; creates parent dir.
<!-- opsx:tdd:1.2:begin -->
  - **Input**: wire_agent_opencode(Path('/tmp/proj'), Path('/tmp/proj/.agentic-beacon/artifacts/agents/spec-planner.md'))
  - **Expected Output**: Returns Path('/tmp/proj/.opencode/agents/spec-planner.md'); file at that path is a symlink to the artifact file.
  - **Validation**: Same as 1.1 but for the .opencode/agents/ destination; idempotent on second call.
  - **TDD Test Cases (write these first):**
    - TC1: fresh project → directory created and symlink written
    - TC2: idempotent re-run → no error, no duplicate
    - TC3: stale symlink pointing at old artifact path → updated to new target
<!-- opsx:tdd:1.2:end -->
- [x] 1.3 In the same file, add `unwire_agent(project_root, agent_name)` that removes both `.claude/agents/<name>.md` and `.opencode/agents/<name>.md` if present (mirrors `unwire_skill`).
<!-- opsx:tdd:1.3:begin -->
  - **Input**: unwire_agent(Path('/tmp/proj'), 'spec-planner')
  - **Expected Output**: Both .claude/agents/spec-planner.md and .opencode/agents/spec-planner.md are removed if they existed; missing files are silently skipped.
  - **Validation**: After call, neither path exists; function does not raise FileNotFoundError when one or both are missing.
  - **TDD Test Cases (write these first):**
    - TC1: both symlinks present → both removed
    - TC2: only Claude symlink present → it is removed; OpenCode path absence is not an error
    - TC3: neither symlink present → no-op, no exception
    - TC4: agent_name with subdirectory characters (e.g. 'team/reviewer') → only the resolved leaf paths are touched, no traversal escapes
<!-- opsx:tdd:1.3:end -->
- [x] 1.4 Extend `unwire_pruned_artifacts` in `wiring.py` to handle `artifact_type == "agents"` by calling `unwire_agent`.
<!-- opsx:tdd:1.4:begin -->
  - **Input**: unwire_pruned_artifacts(Path('/tmp/proj'), ['agents/spec-planner.md'], Path('/tmp/proj/.agentic-beacon/artifacts'))
  - **Expected Output**: unwire_agent is invoked with project_root and 'spec-planner'; the .claude/agents and .opencode/agents symlinks are removed.
  - **Validation**: Use a unittest.mock.patch on unwire_agent to assert the call signature; assert filesystem state matches.
<!-- opsx:tdd:1.4:end -->
- [x] 1.5 Update the `create_beacon_template` comment block to drop "AND installed globally" language and reference `abc adopt` for wiring.

## 2. Domain layer — delete global install code

<!-- opsx:phase-summary:2:begin -->
**Goal**: Remove the entire global-install path from domains/artifact/agent.py and repurpose update_agent_gitignores to manage the project .gitignore.
**Input**: domains/artifact/agent.py contains seven global-install functions; update_agent_gitignores writes per-tool agent dirs.
**Output**: Seven listed functions deleted; update_agent_gitignores now writes .claude/agents/ and .opencode/agents/ to the project .gitignore idempotently; read_agent_definition and detect_agents preserved.
**Validation**: grep 'sync_agents_from_warehouse|install_agent_global|uninstall_agent_global|global_agent_dirs|detect_agents_global|_agent_link_conflicts|list_global_agents' libs/beacon/src/ returns zero references; ruff/pyright clean (no unused imports).
<!-- opsx:phase-summary:2:end -->


- [x] 2.1 Delete from `libs/beacon/src/beacon/domains/artifact/agent.py`: `sync_agents_from_warehouse`, `install_agent_global`, `uninstall_agent_global`, `global_agent_dirs`, `detect_agents_global`, `_agent_link_conflicts`, `list_global_agents`.
<!-- opsx:tdd:2.1:begin -->
  - **Input**: rg -n 'sync_agents_from_warehouse|install_agent_global|uninstall_agent_global|global_agent_dirs|detect_agents_global|_agent_link_conflicts|list_global_agents' libs/beacon/src
  - **Expected Output**: Zero matches across libs/beacon/src.
  - **Validation**: Exit code 1 from rg (no matches); pytest libs/beacon/tests/unit/ collects and runs without ImportError.
<!-- opsx:tdd:2.1:end -->
- [x] 2.2 Repurpose `update_agent_gitignores` to operate on the project `.gitignore` rather than per-tool agent dirs; ensure `.claude/agents/` and `.opencode/agents/` entries are appended idempotently.
<!-- opsx:tdd:2.2:begin -->
  - **Input**: update_agent_gitignores(Path('/tmp/proj'))
  - **Expected Output**: .gitignore at project root contains exactly one line each for '.claude/agents/' and '.opencode/agents/' regardless of how many times the function is called.
  - **Validation**: grep -c '^\.claude/agents/$' .gitignore equals 1; grep -c '^\.opencode/agents/$' .gitignore equals 1; pre-existing .gitignore content is preserved.
  - **TDD Test Cases (write these first):**
    - TC1: no .gitignore exists → file is created with both entries
    - TC2: .gitignore exists with unrelated entries → both entries appended, original entries preserved
    - TC3: .gitignore already has '.claude/agents/' but not '.opencode/agents/' → only the missing entry is appended
    - TC4: .gitignore already has both → no-op, file unchanged
    - TC5: project_root is not a directory → raises FileNotFoundError, no partial write
<!-- opsx:tdd:2.2:end -->
- [x] 2.3 Verify `read_agent_definition` and `detect_agents` (project-level) remain and have no unused imports after deletions.
<!-- opsx:tdd:2.3:begin -->
  - **Input**: ruff check libs/beacon/src/beacon/domains/artifact/agent.py && python -c 'from beacon.domains.artifact.agent import read_agent_definition, detect_agents'
  - **Expected Output**: ruff exits 0 with no F401 (unused import) findings; the import statement succeeds.
  - **Validation**: Both commands return exit code 0.
<!-- opsx:tdd:2.3:end -->

## 3. Distribution orchestrator — wire on sync

<!-- opsx:phase-summary:3:begin -->
**Goal**: Make abc sync expand beacon.yaml.artifacts.agents and write the project-local tool symlinks per the project-agent-wiring spec.
**Input**: orchestrator.py currently only iterates contexts and skills for wiring; agents are read into the resolver but not wired.
**Output**: orchestrator.py writes .claude/agents/<name>.md and .opencode/agents/<name>.md for each declared agent (gated by detect_agents); pruned agents are unwired via unwire_pruned_artifacts.
**Validation**: Integration test from task 9.3 passes: declared agent → both symlinks exist; remove entry → both symlinks gone.
<!-- opsx:phase-summary:3:end -->


- [x] 3.1 In `libs/beacon/src/beacon/domains/distribution/orchestrator.py`, after the existing artifact symlink reconciliation, iterate `beacon.artifacts.agents` and for each, call `wire_agent_claudecode` and `wire_agent_opencode` gated by `detect_agents(project_root)` returning the corresponding tool key.
<!-- opsx:tdd:3.1:begin -->
  - **Input**: abc sync run in a project whose beacon.yaml has artifacts.agents=['agents/spec-planner.md'] and both .claude/ and .opencode/ directories present
  - **Expected Output**: .claude/agents/spec-planner.md and .opencode/agents/spec-planner.md exist as symlinks pointing at .agentic-beacon/artifacts/agents/spec-planner.md.
  - **Validation**: Both project-local symlinks exist after sync; readlink resolves to the artifact path; sync exits 0.
  - **TDD Test Cases (write these first):**
    - TC1: both .claude/ and .opencode/ present → both symlinks created
    - TC2: only .claude/ present → only .claude/agents/<name>.md created; no .opencode/ wiring
    - TC3: neither tool dir present → only artifact symlink created; no wiring; no error
    - TC4: agents list empty → no wiring attempted; sync still succeeds for skills/contexts
    - TC5: agent declared but warehouse missing the file → resolver-level error before wiring (existing behaviour preserved)
<!-- opsx:tdd:3.1:end -->
- [x] 3.2 Ensure `unwire_pruned_artifacts` is called for any `agents/<name>.md` entries that were removed since the previous sync.
<!-- opsx:tdd:3.2:begin -->
  - **Input**: Run abc sync after removing 'agents/spec-planner.md' from beacon.yaml.artifacts.agents in a project where it was previously declared and wired.
  - **Expected Output**: .claude/agents/spec-planner.md, .opencode/agents/spec-planner.md, and .agentic-beacon/artifacts/agents/spec-planner.md are all removed.
  - **Validation**: All three paths are absent post-sync; sync exits 0.
<!-- opsx:tdd:3.2:end -->

## 4. Distribution orchestrator — legacy global cleanup

<!-- opsx:phase-summary:4:begin -->
**Goal**: On every abc sync, scrub legacy ~/.claude/agents/ and ~/.config/opencode/agents/ symlinks pointing into the connected warehouse, and print a one-line notice if any were removed.
**Input**: Users upgrading from prior versions have orphaned symlinks under home agent dirs. The current sync path does not touch home dirs.
**Output**: cleanup_legacy_global_agent_symlinks function exists and is called from abc sync after wiring. Prints 'Cleaned up N legacy global agent symlinks (PER-113 migration).' only when N>0. Idempotent on subsequent runs.
**Validation**: Integration test from task 9.5 passes: pre-seeded legacy symlink is removed and notice prints; second sync prints nothing.
<!-- opsx:phase-summary:4:end -->


- [x] 4.1 Add `cleanup_legacy_global_agent_symlinks(warehouse_path) -> int` (placement: `libs/beacon/src/beacon/domains/distribution/orchestrator.py`, or a new `migrations.py` sibling). Scans `~/.claude/agents/` and `~/.config/opencode/agents/` non-recursively; for each entry that is a symlink whose `resolve()` is under `warehouse_path / "agents"`, unlink it. Returns the total count.
<!-- opsx:tdd:4.1:begin -->
  - **Input**: cleanup_legacy_global_agent_symlinks(Path('/tmp/warehouse'))
  - **Expected Output**: Returns the integer count of symlinks removed across both home agent dirs; only matching symlinks are unlinked.
  - **Validation**: Pre-seed test fixtures: matching symlinks are gone, non-matching symlinks remain, regular files remain, non-existent home dirs do not raise. Returned count equals the number of matches.
  - **TDD Test Cases (write these first):**
    - TC1: legacy symlink in ~/.claude/agents/ targeting warehouse/agents/foo.md → removed; count incremented by 1
    - TC2: legacy symlink in ~/.config/opencode/agents/ targeting warehouse/agents/foo.md → removed; count incremented by 1
    - TC3: symlink in ~/.claude/agents/ pointing at /tmp/elsewhere.md (not under warehouse) → preserved
    - TC4: regular file in ~/.claude/agents/handcrafted.md → preserved
    - TC5: ~/.config/opencode/agents/ does not exist → function skips it without error
    - TC6: dangling symlink (target does not exist) → preserved (resolve() does not match warehouse path)
    - TC7: subdirectory containing symlinks → not recursed into; nested entries preserved
    - TC8: warehouse_path itself is a symlink → resolution still matches against the canonical warehouse_path/agents prefix
    - TC9: empty home agent dirs → returns 0; no exception
    - TC10: 50 matching symlinks → all 50 removed; returned count is 50
<!-- opsx:tdd:4.1:end -->
- [x] 4.2 Wire `cleanup_legacy_global_agent_symlinks` into `abc sync` after the artifact wiring step. If the returned count is > 0, print `Cleaned up <N> legacy global agent symlinks (PER-113 migration).` to stdout via the rich console. If 0, print nothing.
<!-- opsx:tdd:4.2:begin -->
  - **Input**: Run abc sync in a project whose home dirs contain 3 legacy symlinks pointing into the connected warehouse.
  - **Expected Output**: stdout contains the line `Cleaned up 3 legacy global agent symlinks (PER-113 migration).`; the 3 legacy symlinks are gone.
  - **Validation**: Capture stdout; assert the literal line is present once; re-run sync and assert the line is absent on the second run.
<!-- opsx:tdd:4.2:end -->
- [x] 4.3 Confirm the cleanup is idempotent and tolerates missing tool directories (`~/.claude/agents/` or `~/.config/opencode/agents/` not existing) without error.
<!-- opsx:tdd:4.3:begin -->
  - **Input**: Run abc sync on a fresh machine where ~/.claude/agents/ does not exist; then run again.
  - **Expected Output**: First run: no error, no notice (count == 0). Second run: identical.
  - **Validation**: Both invocations exit 0; stdout contains no cleanup notice; no exception is raised.
<!-- opsx:tdd:4.3:end -->

## 5. CLI layer — delete `agents` group, flip `list agents`

<!-- opsx:phase-summary:5:begin -->
**Goal**: Remove the abc agents Click group and re-point abc list agents at the project artifact directory.
**Input**: cli/agent.py exports an `agents` group with a sync subcommand; list_cmd reads global home dirs for agents.
**Output**: The `agents` group is gone; list_cmd reads .agentic-beacon/artifacts/agents/; cli/main.py no longer registers the group; SyncEngine.list_artifacts handles 'agents'.
**Validation**: abc agents --help exits non-zero (no such command); abc list agents shows project-declared agents only; pytest tests/unit/test_architecture.py passes.
<!-- opsx:phase-summary:5:end -->


- [x] 5.1 In `libs/beacon/src/beacon/cli/agent.py`, delete the `agents` Click group and its `agents_sync` subcommand entirely.
<!-- opsx:tdd:5.1:begin -->
  - **Input**: abc agents --help
  - **Expected Output**: Click prints 'Error: No such command \'agents\'.' and exits non-zero.
  - **Validation**: Exit code != 0; stderr contains 'No such command'; grep '@click.group' libs/beacon/src/beacon/cli/agent.py finds no `agents` group definition.
<!-- opsx:tdd:5.1:end -->
- [x] 5.2 In the same file, rewrite `list_cmd`'s `artifact_type == "agents"` branch to use `SyncEngine.list_artifacts("agents")` (or equivalent direct read of `.agentic-beacon/artifacts/agents/*.md`), mirroring how skills/contexts are listed.
<!-- opsx:tdd:5.2:begin -->
  - **Input**: abc list agents in a project with .agentic-beacon/artifacts/agents/spec-planner.md and .agentic-beacon/artifacts/agents/code-reviewer.md
  - **Expected Output**: Output contains both 'spec-planner' and 'code-reviewer' under a 'Synced Agents' table; nothing is read from ~/.claude/agents/.
  - **Validation**: Capture stdout; assert both names appear; mock home agent dirs to confirm they are not opened.
<!-- opsx:tdd:5.2:end -->
- [x] 5.3 Update the `list_cmd` docstring to reflect that agents are project-scoped (drop the "Globally installed" sentence).
- [x] 5.4 In `libs/beacon/src/beacon/cli/main.py`, unregister the `agents` group import and `add_command` call.
<!-- opsx:tdd:5.4:begin -->
  - **Input**: rg -n 'from beacon.cli.agent import agents|cli.add_command\(agents\)' libs/beacon/src/beacon/cli/main.py
  - **Expected Output**: Zero matches.
  - **Validation**: Exit code 1 from rg; abc --help no longer lists 'agents' as a subcommand.
<!-- opsx:tdd:5.4:end -->
- [x] 5.5 Add a `valid_types` entry for `agents` in `SyncEngine.list_artifacts` if not already present, parallel to `skills` and `contexts`.

## 6. Adoption — accept/reject hooks

<!-- opsx:phase-summary:6:begin -->
**Goal**: Make abc adopt's agent tab honest: accept actually wires the agent, reject actually unwires it, both inside the atomic adopt commit.
**Input**: domains/adoption/apply.py only mutates beacon.yaml entries for agents; no symlink writes/removes happen on accept/reject.
**Output**: On accept: artifact symlink + tool symlinks created atomically; on reject: all are removed atomically; rollback machinery covers the new writes.
**Validation**: Integration test from task 9.4 passes; manual abc adopt run shows symlinks appear/disappear immediately on confirm.
<!-- opsx:phase-summary:6:end -->


- [x] 6.1 In `libs/beacon/src/beacon/domains/adoption/apply.py`, on accept of an agent, after appending to `beacon_settings.artifacts.agents`, create the artifact symlink and call `wire_agent_claudecode`/`wire_agent_opencode` gated by `detect_agents`.
<!-- opsx:tdd:6.1:begin -->
  - **Input**: Simulate abc adopt accepting agents/spec-planner.md and confirming the commit in a project that has both .claude/ and .opencode/.
  - **Expected Output**: After confirm: beacon.yaml lists agents/spec-planner.md; .agentic-beacon/artifacts/agents/spec-planner.md is a symlink into the warehouse; .claude/agents/spec-planner.md and .opencode/agents/spec-planner.md are symlinks into the artifact path.
  - **Validation**: All four filesystem artefacts exist post-confirm; abc warehouse status reports the agent as IN SYNC.
  - **TDD Test Cases (write these first):**
    - TC1: accept with both tools detected → all four paths written
    - TC2: accept with only Claude detected → artifact + .claude symlink written; no .opencode/agents written
    - TC3: accept fails mid-commit (force I/O error on second wiring) → all writes rolled back; beacon.yaml, pending.yaml, and any partial symlinks restored to pre-commit state
    - TC4: accept on an agent already in beacon.yaml.artifacts.agents → no duplicate; symlinks reconciled idempotently
<!-- opsx:tdd:6.1:end -->
- [x] 6.2 In the same file, on reject of an agent, after removing from `beacon_settings.artifacts.agents`, remove the artifact symlink and call `unwire_agent`.
<!-- opsx:tdd:6.2:begin -->
  - **Input**: Simulate abc adopt rejecting agents/spec-planner.md (already wired) and confirming.
  - **Expected Output**: beacon.yaml no longer lists the agent; .agentic-beacon/artifacts/agents/spec-planner.md and both project-local tool symlinks are gone; nothing under ~/.claude/agents/ or ~/.config/opencode/agents/ is touched.
  - **Validation**: All three filesystem paths absent; mock home dirs to verify no writes/deletes there.
  - **TDD Test Cases (write these first):**
    - TC1: reject of a wired agent → all three project-level paths removed
    - TC2: reject of an agent that was declared but tool symlinks somehow missing → no error; the absent paths are silently skipped
    - TC3: reject does not modify ~/.claude/agents/ or ~/.config/opencode/agents/ regardless of state
<!-- opsx:tdd:6.2:end -->
- [x] 6.3 Verify the existing atomic-commit / rollback machinery in apply.py covers the new symlink writes; extend the rollback set to include the new tool symlinks if not.
<!-- opsx:tdd:6.3:begin -->
  - **Input**: Inject a forced exception after the first tool symlink is written but before the second; observe rollback.
  - **Expected Output**: After the exception, the first symlink is removed, beacon.yaml is reverted, pending.yaml is reverted, and .last-adopt is restored.
  - **Validation**: Filesystem state matches pre-commit snapshot byte-for-byte; pytest assertion compares directory tree hashes before vs after the failed commit.
<!-- opsx:tdd:6.3:end -->

## 7. Setup — `.gitignore` wiring

<!-- opsx:phase-summary:7:begin -->
**Goal**: Ensure abc setup configures the project .gitignore to exclude per-machine agent symlinks and that abc warehouse init advertises abc adopt as the wiring entry point.
**Input**: abc setup currently does not manage .claude/agents/ or .opencode/agents/ in .gitignore. Init hint does not mention abc adopt.
**Output**: .gitignore contains both agent-dir entries after abc setup (idempotently); init hint includes the line `Run 'abc adopt' to wire agents.`
**Validation**: Run abc setup in a scratch project; cat .gitignore | grep -c 'agents/' returns 2; abc warehouse init shows the hint.
<!-- opsx:phase-summary:7:end -->


- [x] 7.1 In `libs/beacon/src/beacon/domains/setup/initializer.py` (or wherever `abc setup` runs its wiring tasks), call the repurposed `update_agent_gitignores` to append `.claude/agents/` and `.opencode/agents/` to the project `.gitignore`.
<!-- opsx:tdd:7.1:begin -->
  - **Input**: Run abc setup in a fresh scratch project (no .gitignore); then run abc setup again.
  - **Expected Output**: After first run: .gitignore exists and contains both '.claude/agents/' and '.opencode/agents/' lines. After second run: file is byte-identical (idempotent).
  - **Validation**: diff between the two states is empty; both entries are present exactly once.
<!-- opsx:tdd:7.1:end -->
- [x] 7.2 Ensure the post-init hint in `abc warehouse init` includes the line `Run 'abc adopt' to wire agents.`

## 8. Tests — unit

<!-- opsx:phase-summary:8:begin -->
**Goal**: Cover the new wiring primitives, the repurposed gitignore writer, and the legacy-cleanup scanner with sub-second mocked unit tests.
**Input**: Existing unit tests cover skill wiring; nothing covers the new agent-specific functions.
**Output**: Unit tests for wire_agent_claudecode, wire_agent_opencode, unwire_agent, update_agent_gitignores (repurposed), and cleanup_legacy_global_agent_symlinks. test_architecture.py reflects the deleted/added handler files.
**Validation**: pytest libs/beacon/tests/unit/ exits 0 with all new tests collected and passing.
<!-- opsx:phase-summary:8:end -->


- [x] 8.1 Add unit tests in `libs/beacon/tests/unit/` for `wire_agent_claudecode`, `wire_agent_opencode`, and `unwire_agent`: idempotency, parent-dir creation, missing source handling, both-tools / one-tool scenarios.
<!-- opsx:tdd:8.1:begin -->
  - **Input**: pytest libs/beacon/tests/unit/test_wire_agents.py -v
  - **Expected Output**: All test functions pass; coverage for the three new wiring functions reaches the scenarios listed in tasks 1.1–1.3.
  - **Validation**: pytest exits 0; coverage report shows wire_agent_claudecode, wire_agent_opencode, unwire_agent all > 90% line coverage.
<!-- opsx:tdd:8.1:end -->
- [x] 8.2 Add a unit test for `update_agent_gitignores` repurposed behaviour: fresh `.gitignore`, existing file, idempotent re-run.
<!-- opsx:tdd:8.2:begin -->
  - **Input**: pytest libs/beacon/tests/unit/test_agent_gitignore.py -v
  - **Expected Output**: All scenarios from task 2.2 (TC1–TC5) are exercised and pass.
  - **Validation**: pytest exits 0; assertions on .gitignore contents match the spec.
<!-- opsx:tdd:8.2:end -->
- [x] 8.3 Add a unit test for `cleanup_legacy_global_agent_symlinks`: symlink-into-warehouse removed, non-warehouse symlink preserved, regular file preserved, missing tool dir tolerated.
<!-- opsx:tdd:8.3:begin -->
  - **Input**: pytest libs/beacon/tests/unit/test_legacy_agent_cleanup.py -v
  - **Expected Output**: All scenarios from task 4.1 (TC1–TC10) are exercised and pass.
  - **Validation**: pytest exits 0; tmp_path fixtures simulate home dirs without touching real ~/.claude or ~/.config.
<!-- opsx:tdd:8.3:end -->
- [x] 8.4 Update `libs/beacon/tests/unit/test_architecture.py` if any new CLI handler files are added; remove entries for deleted ones.
<!-- opsx:tdd:8.4:begin -->
  - **Input**: pytest libs/beacon/tests/unit/test_architecture.py -v
  - **Expected Output**: Architecture test passes; the asserted CLI handler file set matches the actual files in cli/.
  - **Validation**: pytest exits 0; no AssertionError about unexpected/missing handler files.
<!-- opsx:tdd:8.4:end -->

## 9. Tests — integration

<!-- opsx:phase-summary:9:begin -->
**Goal**: End-to-end coverage of sync wiring, adopt accept/reject, and the migration cleanup using real subprocess invocations of abc.
**Input**: test_auto_pull_deps_e2e.py:303 has a guard asserting sync does NOT call sync_agents_from_warehouse; test_agents_sync_command.py covers the deleted command.
**Output**: Guard test inverted to assert wiring; test_agents_sync_command.py retired; new tests for sync+wire, adopt+wire, and legacy cleanup exist and pass.
**Validation**: pytest libs/beacon/tests/integration/ exits 0; the inverted guard test is green; old test file is deleted from the tree.
<!-- opsx:phase-summary:9:end -->


- [x] 9.1 Flip `libs/beacon/tests/integration/test_auto_pull_deps_e2e.py:303` — invert the assertion that `abc sync` does NOT call `sync_agents_from_warehouse`. New assertion: `abc sync` wires declared agents into project-local `.claude/agents/` and `.opencode/agents/`.
<!-- opsx:tdd:9.1:begin -->
  - **Input**: pytest libs/beacon/tests/integration/test_auto_pull_deps_e2e.py -v -k 'agents'
  - **Expected Output**: The previously-passing 'does not call sync_agents_from_warehouse' assertion is replaced with 'creates .claude/agents/<name>.md and .opencode/agents/<name>.md' and now passes.
  - **Validation**: pytest exits 0; the test source no longer references sync_agents_from_warehouse.
<!-- opsx:tdd:9.1:end -->
- [x] 9.2 Retire `libs/beacon/tests/integration/test_agents_sync_command.py`.
<!-- opsx:tdd:9.2:begin -->
  - **Input**: ls libs/beacon/tests/integration/test_agents_sync_command.py 2>&1; pytest libs/beacon/tests/integration/ --collect-only
  - **Expected Output**: ls reports 'No such file or directory'; pytest collection completes without ImportError or missing-fixture error from the deleted file.
  - **Validation**: File is absent; full integration test collection succeeds.
<!-- opsx:tdd:9.2:end -->
- [x] 9.3 Add an integration test: declare an agent in `beacon.yaml`, run `abc sync`, assert artifact symlink + both project-local tool symlinks exist; remove the entry, run sync again, assert all three are gone.
<!-- opsx:tdd:9.3:begin -->
  - **Input**: pytest libs/beacon/tests/integration/test_agent_sync_lifecycle.py -v
  - **Expected Output**: Test sets up a scratch warehouse + project, runs abc sync via subprocess, asserts symlink lifecycle on add and remove.
  - **Validation**: pytest exits 0; both lifecycle phases (add-and-wire, remove-and-unwire) pass.
<!-- opsx:tdd:9.3:end -->
- [x] 9.4 Add an integration test for adoption: simulate an `accept` action on an agent, assert `beacon.yaml`, artifact symlink, and tool symlinks are written atomically; simulate a `reject`, assert all are cleaned up.
<!-- opsx:tdd:9.4:begin -->
  - **Input**: pytest libs/beacon/tests/integration/test_adopt_agent.py -v
  - **Expected Output**: Test invokes the adopt apply path with accept then reject actions; all four state changes (yaml, artifact, .claude/agents, .opencode/agents) are asserted at each step.
  - **Validation**: pytest exits 0; rollback scenario also covered (force I/O error mid-commit).
<!-- opsx:tdd:9.4:end -->
- [x] 9.5 Add an integration test for legacy cleanup: pre-create a fake legacy symlink at `~/.claude/agents/test.md` pointing into the warehouse, run `abc sync`, assert the symlink is removed and the notice line is printed; run sync again, assert no notice line.
<!-- opsx:tdd:9.5:begin -->
  - **Input**: pytest libs/beacon/tests/integration/test_legacy_agent_cleanup.py -v
  - **Expected Output**: Test uses a tmp HOME (monkeypatched HOME env var) to seed legacy symlinks, runs abc sync via subprocess, asserts the cleanup notice and absence of the symlinks; second sync produces no notice.
  - **Validation**: pytest exits 0; HOME is isolated to tmp_path so no real ~/.claude is touched.
<!-- opsx:tdd:9.5:end -->

## 10. Docs and examples

<!-- opsx:phase-summary:10:begin -->
**Goal**: Bring documentation and bundled examples in line with the project-scoped agent model.
**Input**: data/templates/agents/README.md and templates/README.md both describe global install. examples/sample-warehouse drifts after init/template edits. site-docs has no migration note.
**Output**: Templates describe the project-local model; sample-warehouse regenerated from abc warehouse init; site-docs has a PER-113 migration section.
**Validation**: diff examples/sample-warehouse/ against fresh `abc warehouse init` output is empty; grep 'globally installed' returns no hits in templates; site-docs renders without errors.
<!-- opsx:phase-summary:10:end -->


- [x] 10.1 Update `libs/beacon/src/beacon/data/templates/agents/README.md` to drop "globally installed" language and describe the project-local model.
- [x] 10.2 Update `libs/beacon/src/beacon/data/templates/README.md` if it references the old global model.
- [ ] 10.3 **[MANUAL]** Regenerate `examples/sample-warehouse/` from `abc warehouse init` and commit any drift.
<!-- opsx:tdd:10.3:begin -->
  - **Input**: rm -rf examples/sample-warehouse && abc warehouse init examples/sample-warehouse && git diff --exit-code examples/sample-warehouse/
  - **Expected Output**: git diff exits 0 (no drift) after regeneration; if drift exists, it is committed.
  - **Validation**: git status reports examples/sample-warehouse/ either unchanged or with the regenerated contents staged; AGENTS.md critical-safeguard requirement satisfied.
<!-- opsx:tdd:10.3:end -->
- [x] 10.4 Update `site-docs/` agent-distribution page to describe the new model and the migration step.
- [x] 10.5 Add a short migration note to `CHANGELOG`-equivalent (release notes section) referencing PER-113.

## 11. Linear ticket housekeeping

<!-- opsx:phase-summary:11:begin -->
**Goal**: Close PER-109 and update PER-113 in Linear with the merged-change context.
**Input**: PER-109 and PER-113 are both 'In Progress' on the Linear board.
**Output**: PER-109 closed with a superseded-by comment; PER-113 marked complete with a link to the OpenSpec change archive.
**Validation**: Linear API query returns state='Done' (or 'Cancelled' for superseded) for both tickets.
<!-- opsx:phase-summary:11:end -->


- [ ] 11.1 **[MANUAL]** Close PER-109 in Linear with a comment linking to this OpenSpec change and noting that selectivity now comes from `beacon.yaml` gating rather than a separate picker.
<!-- opsx:tdd:11.1:begin -->
  - **Input**: Linear web UI / API: navigate to PER-109, post a comment linking openspec/changes/unify-agent-distribution and the merged PR; mark the issue as Cancelled (superseded) or Done.
  - **Expected Output**: PER-109 state transitions out of 'In Progress'; comment is visible on the ticket.
  - **Validation**: GraphQL query `issue(id: "PER-109") { state { name } comments { nodes { body } } }` confirms the new state and the comment text.
<!-- opsx:tdd:11.1:end -->
- [ ] 11.2 **[MANUAL]** Update PER-113 with a link to the merged change once apply completes.
<!-- opsx:tdd:11.2:begin -->
  - **Input**: Linear web UI / API: post a comment on PER-113 linking the merged PR and the archived OpenSpec change; mark Done.
  - **Expected Output**: PER-113 state == Done; comment is visible.
  - **Validation**: GraphQL query confirms state and comment.
<!-- opsx:tdd:11.2:end -->

## 12. Verification

<!-- opsx:phase-summary:12:begin -->
**Goal**: Run the full verification matrix: unit + integration tests, end-to-end CLI exercise, and migration validation.
**Input**: All implementation tasks (phases 1–10) complete on the unify-agent-distribution branch.
**Output**: All tests green; scratch-project E2E shows correct symlink lifecycle; migration cleanup verified with real legacy symlinks; codebase grep confirms no remaining global-install references.
**Validation**: All four 12.x sub-tasks pass; ready to open PR.
<!-- opsx:phase-summary:12:end -->


- [x] 12.1 Run `pytest` from the repo root; all unit and integration tests pass.
<!-- opsx:tdd:12.1:begin -->
  - **Input**: cd ~/Code/oss/agentic-beacon && pytest
  - **Expected Output**: Pytest reports 0 failures, 0 errors across the full unit + integration suite.
  - **Validation**: Exit code 0; final summary shows '== N passed in Ms ==' with no skipped-without-reason or xfailed entries.
<!-- opsx:tdd:12.1:end -->
- [ ] 12.2 **[MANUAL]** Run `abc --version`, `abc warehouse init test-warehouse`, `abc setup`, `abc adopt`, `abc sync` end-to-end in a scratch directory; verify `.claude/agents/` and `.opencode/agents/` get correct symlinks for accepted agents and nothing for rejected/deferred ones.
<!-- opsx:tdd:12.2:begin -->
  - **Input**: Manual: cd to a tmp dir, run the listed CLI sequence, accept one agent in adopt and reject another, then inspect the project tree.
  - **Expected Output**: Accepted agent has all three symlinks (artifact + both tool dirs); rejected agent has none; deferred agent stays in pending.yaml only.
  - **Validation**: ls -la .claude/agents/ and .opencode/agents/ confirm the expected lifecycle for each action; cat beacon.yaml matches the accept/reject decisions.
<!-- opsx:tdd:12.2:end -->
- [ ] 12.3 **[MANUAL]** In a project that previously ran `abc agents sync`, run `abc sync` once more; verify the legacy-cleanup notice prints with a non-zero count, then re-run and verify it is silent.
<!-- opsx:tdd:12.3:begin -->
  - **Input**: On the dev machine (or a fixture replicating the pre-upgrade state), abc sync; abc sync.
  - **Expected Output**: First run: stdout contains exactly one line `Cleaned up <N> legacy global agent symlinks (PER-113 migration).` with N > 0. Second run: no such line.
  - **Validation**: Captured stdout matches the pattern on first run and is empty (of cleanup notice) on second run; ~/.claude/agents/ and ~/.config/opencode/agents/ no longer contain warehouse-pointing symlinks.
<!-- opsx:tdd:12.3:end -->
- [x] 12.4 Confirm `~/.claude/agents/` and `~/.config/opencode/agents/` no longer receive any new symlinks from any Beacon CLI path (grep the codebase for the literal strings to confirm only the cleanup function references them).
<!-- opsx:tdd:12.4:begin -->
  - **Input**: rg -n '~/.claude/agents/|~/.config/opencode/agents/|.claude.*agents|opencode.*agents' libs/beacon/src/
  - **Expected Output**: The only matches are inside `cleanup_legacy_global_agent_symlinks` (and possibly its docstring/tests). No write or symlink-creation call targets these paths.
  - **Validation**: Manual review of every match confirms no `Path.symlink_to`, `os.symlink`, or `shutil.copy*` operation writes to the global home agent dirs.
<!-- opsx:tdd:12.4:end -->

<!-- opsx:metadata:begin -->
---

## Enhancement Metadata

**Enhanced**: 2026-05-07
**Methodology**: Spec-Driven Development + TDD
**Enhancements Applied**:
- TDD Workflow Header
- Repositories & Branches table
- Phase summaries (Goal/Input/Output/Validation)
- Task-level TDD criteria on 35 task(s)
- 39 test case(s) across complex tasks
- 5 task(s) flagged [MANUAL]

**Status**: Ready for implementation via `/opsx-apply <name>`.
<!-- opsx:metadata:end -->
