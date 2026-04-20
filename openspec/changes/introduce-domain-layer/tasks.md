# Implementation Tasks — introduce-domain-layer

## Repositories & Branches

| Repo | Path | Branch | Role |
|------|------|--------|------|
| `agentic-beacon` | `~/Code/oss/agentic-beacon` | `refactor/introduce-domain-layer` | Single long-running draft PR — all phases land on this branch |

Single-repo change. No registra, no orchestrator — this is the framework itself.

**Workflow**: agent pushes incremental commits to the draft branch; reviewer comments continuously; agent addresses feedback in follow-up commits. The PR is marked ready-for-merge only when all phases are complete.

---

## 🔴 TDD WORKFLOW — MANDATORY FOR SPEC-TEST TASKS

**CRITICAL**: The `test_architecture.py` added in PR 0 is genuine TDD. Its scenarios are written **before** any code is moved. Subsequent PRs flip `xfail` markers to passing assertions as each slice lands.

The code-move tasks themselves are **behavior-preserving refactors**, not new features. The existing test suite (`pytest libs/beacon/tests/`) is the regression test — it must stay green after every PR. No new per-move test cases are needed because no behavior changes.

### RED-GREEN-REFACTOR Cycle (for the architecture test)

1. **🔴 RED Phase — Write Failing Tests FIRST (Phase 1, task 1.2)**
   - Implement every scenario from `specs/layered-architecture/spec.md` as a pytest test in `libs/beacon/tests/unit/test_architecture.py`.
   - Scenarios that would fail against today's tree (e.g. "no `.py` files directly under `beacon/`", "no `_`-prefixed cross-module imports") are marked `@pytest.mark.xfail(strict=True, reason="will pass after phase N")`.
   - Run `pytest libs/beacon/tests/unit/test_architecture.py -v` — the currently-passing scenarios pass, `xfail`s report as expected failures, suite exits 0.

2. **🟢 GREEN Phase — Refactor to Make Tests Pass (Phases 2–9)**
   - Each subsequent phase moves one domain, then flips the corresponding `xfail` markers in `test_architecture.py`.
   - If a scenario flips to passing too early (e.g. phase 2 accidentally satisfies phase 4's scenario), remove the `xfail` immediately — don't leave stale markers.

3. **🔵 REFACTOR Phase — Improve Code Quality (Phases 8 and 9)**
   - Phase 8 thins each CLI handler; phase 9 deletes dead code. Tests must stay green throughout.

### Task Completion Criteria

A task is **not** complete until:
- ✅ All architecture-test scenarios relevant to the phase are flipped from `xfail` to regular asserts and passing
- ✅ Full `pytest` suite passes on the draft branch
- ✅ The per-phase smoke test listed in the task runs cleanly (exit 0, expected output)
- ✅ Changes are pushed to the draft PR on GitHub with CI green

### Running Tests

```bash
# From repo root
uv sync --group dev
.venv/bin/pytest libs/beacon/tests/ -v --tb=short
```

See `AGENTS.md` → "Unit Testing Workflow" and `knowledge/lessons/complete-test-resolution.md`.

---

## 1. Skeleton and architecture test

**Goal**: Land the empty domain skeleton and the TDD harness (`test_architecture.py`) that will enforce the new layering as subsequent phases land.
**Input**: Current `main`; no `domains/` package exists.
**Output**: `beacon/domains/` package with six empty subpackages; `libs/beacon/tests/unit/test_architecture.py` committed with correct `xfail` markers.
**Validation**: `pytest libs/beacon/tests/` exits 0; `.venv/bin/abc --version` prints the version; `tree libs/beacon/src/beacon/domains/` shows six empty subpackages.

- [x] 1.1 Create empty `beacon/domains/` package with six empty subpackages: `warehouse/`, `setup/`, `adoption/`, `distribution/`, `contribution/`, `artifact/` (each with docstring-only `__init__.py`)
- [x] 1.2 Add `libs/beacon/tests/unit/test_architecture.py` implementing the architecture scenarios from `specs/layered-architecture/spec.md`
- [x] 1.3 Verify `pytest` collects and passes the new architecture test against the current (pre-refactor) tree, then mark expected-failure scenarios as `xfail` with a reference to the follow-up PR that will fix them
- [x] 1.4 Push skeleton to draft branch
  - **Input**: `git push origin refactor/introduce-domain-layer`
  - **Expected Output**: CI green on draft PR; `.venv/bin/abc --version` still prints expected version.
  - **Validation**: Full `pytest libs/beacon/tests/` exits 0; no existing test regressed.

## 2. Move `artifact` domain

**Goal**: Relocate agent, skill, and checksum logic — the lowest-coupling domain — to establish the pattern subsequent phases will follow.
**Input**: Skeleton committed on draft branch. `agents.py` (470 lines), `skills.py` (489 lines), and `checksums.py` (56 lines) still in their original locations with `_`-prefixed cross-module names.
**Output**: `beacon/domains/artifact/{agent,skill,checksums}.py` with public (non-underscored) names; no `beacon.utils.agents`/`beacon.utils.skills`/`beacon.checksums` call-sites remain.
**Validation**: `grep -r "from beacon.utils.agents\|from beacon.utils.skills\|from beacon.checksums" libs/beacon/` returns no hits; `pytest` + `abc sync` smoke are green; architecture-test scenarios TC4, TC5, TC6 flip to passing for the artifact slice.

- [x] 2.1 Move `beacon/utils/agents.py` → `beacon/domains/artifact/agent.py`
- [x] 2.2 Move `beacon/utils/skills.py` → `beacon/domains/artifact/skill.py`
- [x] 2.3 Move `beacon/checksums.py` → `beacon/domains/artifact/checksums.py`
- [x] 2.4 Rename all `_`-prefixed functions referenced outside their defining module (drop the leading `_`)
- [x] 2.5 Update every `from beacon.utils.agents import …`, `from beacon.utils.skills import …`, `from beacon.checksums import …` call-site (CLI, adopt.py, distributor.py, tests)
- [x] 2.6 Run regression + smoke tests
- [x] 2.7 Flip the corresponding `xfail` markers in `test_architecture.py` to regular assertions
- [x] 2.8 Push artifact domain move to draft branch

## 3. Move `warehouse` domain

**Goal**: Consolidate warehouse connect/validate/catalog under one domain; delete the orphaned top-level `warehouse/` package.
**Input**: Artifact domain moved on draft branch. `warehouse/validator.py` and `utils/catalog.py` still in original locations; `beacon/warehouse/` package still exists as a single-file package.
**Output**: `beacon/domains/warehouse/{validator,catalog}.py`; `beacon/warehouse/` deleted.
**Validation**: `ls libs/beacon/src/beacon/warehouse/` fails (directory removed); `pytest` + `abc warehouse connect` + `abc warehouse validate` smoke all green.

- [x] 3.1 Move `beacon/warehouse/validator.py` → `beacon/domains/warehouse/validator.py`
- [x] 3.2 Move `beacon/utils/catalog.py` → `beacon/domains/warehouse/catalog.py`
- [x] 3.3 Remove the now-empty `beacon/warehouse/` package
- [x] 3.4 Rename `_`-prefixed cross-module names
- [x] 3.5 Update all call-sites (`beacon/core/cli/warehouse.py`, adopt, tests)
- [x] 3.6 Run regression + smoke
- [x] 3.7 Push warehouse domain move to draft branch

## 4. Move `distribution` domain

**Goal**: Move the sync engine, delta engine, distributor, upgrader, and sync-state bookkeeping into a single domain. This is the largest phase; it also vacates `core/sync.py` and `core/delta.py` from `core/`.
**Input**: Warehouse domain moved on draft branch. Sync engine and delta engine still in `core/`; distributor/upgrader still top-level; sync_state still in `utils/`.
**Output**: `beacon/domains/distribution/{distributor,upgrader,sync_engine,delta,state}.py`; `beacon/core/sync.py` and `beacon/core/delta.py` deleted; `beacon/distributor.py`, `beacon/upgrader.py`, `beacon/utils/sync_state.py` deleted.
**Validation**: `pytest` + `abc sync` (fresh + incremental) + `abc upgrade` + `abc doctor` all green; sync state file `.sync-state` still written with same format.

- [x] 4.1 Move `beacon/distributor.py` → `beacon/domains/distribution/distributor.py`
- [x] 4.2 Move `beacon/upgrader.py` → `beacon/domains/distribution/upgrader.py`
- [x] 4.3 Move `beacon/core/sync.py` → `beacon/domains/distribution/sync_engine.py`
- [x] 4.4 Move `beacon/core/delta.py` → `beacon/domains/distribution/delta.py` (the engine; contribution-facing views move in PR 6)
- [x] 4.5 Move `beacon/utils/sync_state.py` → `beacon/domains/distribution/state.py` (sync-state bookkeeping is distribution's own aggregate)
- [x] 4.6 Rename cross-module `_`-prefixed names (e.g. `_check_sync_state` → `check_sync_state`, `_read_sync_sha` → `read_sync_sha`, etc.)
- [x] 4.7 Update all call-sites (CLI main, adopt, contribute, tests)
- [x] 4.8 Run regression + smoke
  - **Input**: `.venv/bin/pytest libs/beacon/tests/` then, in a scratch project connected to `examples/sample-warehouse/`: `abc sync` (fresh clone), `abc sync` (again, incremental path), `abc upgrade`, `abc doctor`
  - **Expected Output**: Pytest exits 0. Fresh `abc sync` emits "Synced N artifacts"; incremental emits "Already up to date" or a delta summary. `abc upgrade` reports template status. `abc doctor` prints a clean report.
  - **Validation**: All commands exit 0; `.sync-state` file in the scratch project contains a 40-char SHA matching `git -C examples/sample-warehouse rev-parse HEAD`.
- [x] 4.9 Push distribution domain move to draft branch

## 5. Move `setup` domain

**Goal**: Consolidate `abc init`/`abc setup` flows and CLAUDE.md/opencode wiring under one domain.
**Input**: Distribution domain moved on draft branch. `initializer.py` and `utils/wiring.py` in their original locations with ~15 `_`-prefixed cross-module names in wiring.py.
**Output**: `beacon/domains/setup/{initializer,wiring}.py`; all wiring helpers public-named.
**Validation**: `abc init`, `abc setup --manual`, and `abc setup --agent-assisted` all succeed end-to-end on a scratch project.

- [x] 5.1 Move `beacon/initializer.py` → `beacon/domains/setup/initializer.py`
- [x] 5.2 Move `beacon/utils/wiring.py` → `beacon/domains/setup/wiring.py`
- [x] 5.3 Rename cross-module `_`-prefixed names (~15 functions in wiring.py alone)
- [x] 5.4 Update all call-sites (CLI main, tests)
- [x] 5.5 Run regression + smoke
  - **Input**: `.venv/bin/pytest libs/beacon/tests/` then, in a scratch project: `abc init`, `abc setup --manual`, remove `beacon.yaml`, `abc setup --agent-assisted`
  - **Expected Output**: Pytest exits 0. `abc init` creates `.agentic-beacon/` with expected files; `abc setup --manual` writes `beacon.yaml` with an empty template; `abc setup --agent-assisted` installs the project-setup skill and prints next-steps guidance.
  - **Validation**: Exit 0 on each; `.agentic-beacon/beacon.yaml` and `.agentic-beacon/config.toml` match baseline; CLAUDE.md/opencode.json wiring identical to pre-PR baseline (diff-check against a pre-PR snapshot).
- [x] 5.6 Push setup domain move to draft branch

## 6. Move `adoption` domain

**Goal**: Isolate the largest single file (`adopt.py`, 1175 lines) into its own domain. Considered late because its complexity carries the highest chance of subtle breakage, and the previous phases teach us the move pattern.
**Input**: Setup domain moved on draft branch. `adopt.py` still at top-level.
**Output**: `beacon/domains/adoption/adopter.py` (or split if natural seams appear during the move).
**Validation**: `abc adopt` on a sample project reproduces the previous-phase output byte-for-byte on non-interactive paths; interactive paths reviewed by a human.

- [x] 6.1 Move `beacon/adopt.py` → `beacon/domains/adoption/adopter.py` (consider splitting 1175-line file during move if natural seams exist; otherwise move as-is and file a follow-up)
- [x] 6.2 Rename cross-module `_`-prefixed names
- [x] 6.3 Update all call-sites (CLI main, tests)
- [x] 6.4 Run regression + smoke
  - **Input**: `.venv/bin/pytest libs/beacon/tests/` then `abc adopt --dry-run` against a sample project that has existing agents (see `examples/sample-warehouse` for a template)
  - **Expected Output**: Pytest exits 0. `abc adopt --dry-run` prints the same proposed changes as a pre-PR snapshot.
  - **Validation**: `diff <(abc adopt --dry-run)` against baseline is empty; any difference investigated before merging.
- [x] 6.5 **[MANUAL]** Human acceptance smoke — run `abc adopt` (interactive, no `--dry-run`) on a real sample project; confirm the prompts, preview output, and final `.agentic-beacon/` contents match expectations. Required before merging PR 5 per proposal.md "Manual Intervention Requirements".
- [x] 6.6 Push adoption domain move to draft branch

## 7. Move `contribution` domain

**Goal**: Relocate contribute flow and split the 878-line `utils/delta.py` between the distribution engine (any remaining engine glue) and the contribution user-facing views.
**Input**: Adoption domain moved on draft branch. `contribute.py` (605 lines) and `utils/delta.py` (878 lines) still in `utils/`.
**Output**: `beacon/domains/contribution/{contributor,delta_view}.py`; any engine leftovers from `utils/delta.py` absorbed into `domains/distribution/delta.py` (consistent with design.md Open Question resolved here).
**Validation**: `abc contribute --all` and `abc contribute <artifact>` behave identically to pre-phase baseline.

- [x] 7.1 Move `beacon/utils/contribute.py` → `beacon/domains/contribution/contributor.py`
- [x] 7.2 Analyse `beacon/utils/delta.py` (878 lines) — separate engine callers from user-facing views (per design.md Open Questions)
- [x] 7.3 Move user-facing pieces of `utils/delta.py` → `beacon/domains/contribution/delta_view.py`; any remaining engine glue moves to `domains/distribution/delta.py`
- [x] 7.4 Rename cross-module `_`-prefixed names
- [x] 7.5 Update all call-sites (CLI main, tests)
- [x] 7.6 Run regression + smoke
  - **Input**: `.venv/bin/pytest libs/beacon/tests/` then, in a scratch project with local changes vs. the warehouse: `abc contribute --all --dry-run` and `abc contribute <specific-artifact> --dry-run`
  - **Expected Output**: Pytest exits 0. Contribute preview output matches pre-PR baseline.
  - **Validation**: Diff of `abc contribute --all --dry-run` output against baseline is empty.
- [x] 7.7 Push contribution domain move to draft branch

## 8. Thin the CLI layer

**Goal**: Move CLI to its canonical location (`beacon/cli/`), replace all `utils/` imports with `domains/` imports, and enforce the thin-CLI rule (each handler = parsing + one domain call + formatting).
**Input**: Contribution domain moved on draft branch. CLI still lives at `beacon/core/cli/`; `main.py` is 1757 lines with dozens of `from beacon.utils.*` imports.
**Output**: `beacon/cli/` package; no `utils.*` imports in CLI; TC8 (`test_cli_handlers_have_no_io`) flips from `xfail` to passing.
**Validation**: Every `abc` subcommand still works; `main.py` size reduced (target: below 800 lines, split by group if needed).

- [x] 8.1 Rename `beacon/core/cli/` → `beacon/cli/`; update `beacon/cli.py` shim import
- [x] 8.2 Replace all `from beacon.utils.*` imports in `cli/main.py` and `cli/warehouse.py` with `from beacon.domains.*` imports
- [x] 8.3 Verify each handler contains only: argument parsing + one domain call + output formatting (per the "Thin CLI layer" spec requirement). Inline any leftover helpers into their owning domain.
  - **Input**: `.venv/bin/pytest libs/beacon/tests/unit/test_architecture.py::test_cli_handlers_have_no_io -v`
  - **Expected Output**: Test passes (no longer `xfail`).
  - **Validation**: No CLI handler body contains `open()`, `Path.write_text`, `Path.read_text`, `yaml.load`, `tomllib.load`, or `subprocess.run`; AST scan confirms.
- [x] 8.4 Split `cli/main.py` by subcommand group: `cli/setup.py`, `cli/sync.py`, `cli/contribute.py`, `cli/agent.py`. Keep `cli/main.py` as the Click group + registration only.
- [x] 8.5 Run regression + full subcommand smoke
  - **Input**: `.venv/bin/pytest libs/beacon/tests/` then run every `abc` subcommand once on a scratch project (at minimum: `--version`, `init`, `warehouse connect`, `setup --manual`, `sync`, `doctor`, `contribute --all --dry-run`, `upgrade`, `agent list`, `agent install <name>`).
  - **Expected Output**: Every subcommand exits 0 with the same user-visible output as pre-PR.
  - **Validation**: No regressions; `abc --help` output diff vs. baseline is empty.
- [x] 8.6 **[MANUAL]** Human acceptance smoke — required before merging PR 7 per proposal.md "Manual Intervention Requirements". Exercise interactive flows (`abc init`, `abc setup`, `abc adopt`) manually to confirm UX is unchanged.
- [x] 8.7 Push CLI thinning to draft branch

## 9. Clean up and documentation

**Goal**: Delete empty shells, shrink `utils/` and `core/` to their final intended contents, update AGENTS.md and the knowledge base, archive the OpenSpec change.
**Input**: CLI thinning complete on draft branch. Possibly some dead exports in `utils/__init__.py`; `AGENTS.md` still has the old "CLI Layer Discipline" rule.
**Output**: `utils/` contains only `git.py`, `display.py` (total < 500 lines); `core/` contains only `manifest/`, `settings.py`, `exceptions.py`, `gitignore.py`; `AGENTS.md` references the new spec; OpenSpec change archived.
**Validation**: `wc -l libs/beacon/src/beacon/utils/*.py | tail -1` under 500; `ls libs/beacon/src/beacon/core/` lists exactly the four allowed entries; `openspec list` no longer shows the change in `changes/`.

- [x] 9.1 Delete any now-empty modules; delete `beacon/utils/__init__.py` re-exports if any remain
- [x] 9.2 Verify `beacon/utils/` contains only `git.py`, `display.py` (and any new `fs.py`); file sizes total < 500 lines
- [x] 9.3 Verify `beacon/core/` contains only `manifest/`, `settings.py`, `exceptions.py`, `gitignore.py`
- [x] 9.4 Update `AGENTS.md`: replace "CLI Layer Discipline" rule with a pointer to `openspec/specs/layered-architecture/spec.md`; add a "Domain Layer" section naming the six domains
- [x] 9.5 Update `knowledge/facts/repository-structure.md` with the new tree
- [x] 9.6 Update `knowledge/decisions/follow-global-python-standards.md` if the absolute-import rule is strengthened by the new spec
- [ ] 9.7 Archive this change via `/opsx:archive`
  - **Input**: `/opsx:archive introduce-domain-layer`
  - **Expected Output**: Change moves to `openspec/changes/archive/introduce-domain-layer/`; spec merges into `openspec/specs/layered-architecture/spec.md`.
  - **Validation**: `openspec list --json | jq '.changes[] | select(.name == "introduce-domain-layer")'` returns nothing (change no longer active); `ls openspec/specs/layered-architecture/` shows the merged `spec.md`.
- [x] 9.8 File follow-up issue: optional `import-linter` rule (Decision 6 mechanism 3)
- [x] 9.9 Add upgrader coverage test for `_read_new_template` disk path
  - **Rationale**: All 22 existing upgrader tests pass `template_overrides=...`, short-circuiting before the disk lookup. The regression where ruff deleted the `TEMPLATES_DIR / rel_path` branch was only caught by human review, not CI.
  - **Test**: `test_read_new_template_falls_back_to_templates_dir` — call `WarehouseUpgrader._read_new_template(rel_path="README.md", template_overrides={})` and assert it returns non-empty content matching `data/templates/README.md`.
  - **Validation**: Test passes before and after the fix; fails on the broken commit (19ed637~1).
- [ ] 9.10 Mark draft ready-for-merge and merge
