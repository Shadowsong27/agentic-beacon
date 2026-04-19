# Implementation Tasks — introduce-domain-layer

## Repositories & Branches

| Repo | Path | Branch | Role |
|------|------|--------|------|
| `agentic-beacon` | `~/Code/oss/agentic-beacon` | `refactor/domain-*` (one branch per PR — see design.md "Repository Branch Strategy") | Code changes — all moves, renames, import updates, and the new `test_architecture.py` |

Single-repo change. No registra, no orchestrator — this is the framework itself.

---

## 🔴 TDD WORKFLOW — MANDATORY FOR SPEC-TEST TASKS

**CRITICAL**: The `test_architecture.py` added in PR 0 is genuine TDD. Its scenarios are written **before** any code is moved. Subsequent PRs flip `xfail` markers to passing assertions as each slice lands.

The code-move tasks themselves are **behavior-preserving refactors**, not new features. The existing test suite (`pytest libs/beacon/tests/`) is the regression test — it must stay green after every PR. No new per-move test cases are needed because no behavior changes.

### RED-GREEN-REFACTOR Cycle (for the architecture test)

1. **🔴 RED Phase — Write Failing Tests FIRST (PR 0, task 1.2)**
   - Implement every scenario from `specs/layered-architecture/spec.md` as a pytest test in `libs/beacon/tests/test_architecture.py`.
   - Scenarios that would fail against today's tree (e.g. "no `.py` files directly under `beacon/`", "no `_`-prefixed cross-module imports") are marked `@pytest.mark.xfail(strict=True, reason="will pass after PR N")`.
   - Run `pytest tests/test_architecture.py -v` — the currently-passing scenarios pass, `xfail`s report as expected failures, suite exits 0.

2. **🟢 GREEN Phase — Refactor to Make Tests Pass (PRs 1–8)**
   - Each subsequent PR moves one domain, then flips the corresponding `xfail` markers in `test_architecture.py`.
   - If a scenario flips to passing too early (e.g. PR 1 accidentally satisfies PR 4's scenario), remove the `xfail` immediately — don't leave stale markers.

3. **🔵 REFACTOR Phase — Improve Code Quality (PR 7 and PR 8)**
   - PR 7 thins each CLI handler; PR 8 deletes dead code. Tests must stay green throughout.

### Task Completion Criteria

A task is **not** complete until:
- ✅ All architecture-test scenarios relevant to the PR are flipped from `xfail` to regular asserts and passing
- ✅ Full `pytest` suite passes on the feature branch
- ✅ The per-PR smoke test listed in the task runs cleanly (exit 0, expected output)
- ✅ PR opened on GitHub with CI green

### Running Tests

```bash
# From repo root
uv sync --group dev
.venv/bin/pytest libs/beacon/tests/ -v --tb=short
```

See `AGENTS.md` → "Unit Testing Workflow" and `knowledge/lessons/complete-test-resolution.md`.

---

## 1. Skeleton and architecture test (PR 0)

**Goal**: Land the empty domain skeleton and the TDD harness (`test_architecture.py`) that will enforce the new layering as subsequent PRs land.
**Input**: Current `main` at commit `4c1f3c7`; no `domains/` package exists.
**Output**: `beacon/domains/` package with six empty subpackages; `libs/beacon/tests/test_architecture.py` committed with correct `xfail` markers; `spec.md` merged into `openspec/specs/layered-architecture/`.
**Validation**: `pytest libs/beacon/tests/` exits 0; `.venv/bin/abc --version` prints the version; `tree libs/beacon/src/beacon/domains/` shows six empty subpackages.

- [ ] 1.1 Create empty `beacon/domains/` package with six empty subpackages: `warehouse/`, `setup/`, `adoption/`, `distribution/`, `contribution/`, `artifact/` (each with docstring-only `__init__.py`)
- [ ] 1.2 Add `libs/beacon/tests/test_architecture.py` implementing the architecture scenarios from `specs/layered-architecture/spec.md`
  - **Input**: `.venv/bin/pytest libs/beacon/tests/test_architecture.py -v`
  - **Expected Output**: Collected 8+ tests; currently-satisfied scenarios pass; scenarios that can't pass until later PRs report as `xfail (expected)`; suite exits 0.
  - **Validation**: No test is `xpassed` (would indicate a stale marker); every `xfail` has a `reason="will pass after PR N"` pointing to the concrete PR that fixes it.
  - **TDD Test Cases (write these first):**
    - TC1: `test_six_domains_exist` → Asserts `beacon/domains/` contains exactly six subpackages matching the spec's bounded-context table; no extras, no missing.
    - TC2: `test_no_stray_top_level_modules` → Walks `beacon/` and asserts the only `.py` files directly under it are `__init__.py` and `cli.py`. **`xfail` until PR 5 (adopt), PR 4 (setup), PR 3 (distribution) all land.**
    - TC3: `test_core_has_no_domain_imports` → Parses every `beacon/core/**/*.py` with `ast`, asserts no `from beacon.domains` or `from beacon.cli` imports.
    - TC4: `test_utils_has_no_higher_layer_imports` → Parses every `beacon/utils/**/*.py`, asserts no `from beacon.cli`, `from beacon.domains`, or `from beacon.core` imports. **`xfail` until PR 1 (artifact) moves agents/skills out, since those currently import from `beacon.utils.git`.**
    - TC5: `test_cross_domain_imports_use_top_level` → For each `from beacon.domains.<A>.<...>` import in `beacon/domains/<B>/**`, asserts `<...>` has depth exactly 1 (a module directly under `domains/<A>/`, not a deeper internal). **`xfail` until PR 1.**
    - TC6: `test_no_underscore_cross_module_imports` → For every `from beacon.` import across the package, asserts the imported name does not begin with `_`. **`xfail` until each PR renames its `_`-prefixed functions.**
    - TC7: `test_init_files_are_empty` → Parses every `__init__.py` under `beacon/`, asserts its AST body contains only a module docstring (Expr node with Str/Constant) or is empty.
    - TC8: `test_cli_handlers_have_no_io` → Parses every function in `beacon/cli/**/*.py` decorated with `@click.command()`/`@<group>.command()`; asserts the function body contains no calls to `open()`, `Path.write_text`, `Path.read_text`, `yaml.load`, `tomllib.load`, `subprocess.run`. **`xfail` until PR 7 (CLI thinning).**
- [ ] 1.3 Verify `pytest` collects and passes the new architecture test against the current (pre-refactor) tree, then mark expected-failure scenarios as `xfail` with a reference to the follow-up PR that will fix them
- [ ] 1.4 Land PR 0
  - **Input**: `gh pr create --base main --title "refactor(PR 0): add domain skeleton + architecture test" --body ...`
  - **Expected Output**: CI green; PR URL returned; `.venv/bin/abc --version` still prints expected version.
  - **Validation**: Full `pytest libs/beacon/tests/` exits 0; no existing test regressed.

## 2. Move `artifact` domain (PR 1)

**Goal**: Relocate agent, skill, and checksum logic — the lowest-coupling domain — to establish the pattern subsequent PRs will follow.
**Input**: PR 0 merged on `main`. `agents.py` (470 lines), `skills.py` (489 lines), and `checksums.py` (56 lines) still in their original locations with `_`-prefixed cross-module names.
**Output**: `beacon/domains/artifact/{agent,skill,checksums}.py` with public (non-underscored) names; no `beacon.utils.agents`/`beacon.utils.skills`/`beacon.checksums` call-sites remain.
**Validation**: `grep -r "from beacon.utils.agents\|from beacon.utils.skills\|from beacon.checksums" libs/beacon/` returns no hits; `pytest` + `abc sync` smoke are green; architecture-test scenarios TC4, TC5, TC6 flip to passing for the artifact slice.

- [ ] 2.1 Move `beacon/utils/agents.py` → `beacon/domains/artifact/agent.py`
- [ ] 2.2 Move `beacon/utils/skills.py` → `beacon/domains/artifact/skill.py`
- [ ] 2.3 Move `beacon/checksums.py` → `beacon/domains/artifact/checksums.py`
- [ ] 2.4 Rename all `_`-prefixed functions referenced outside their defining module (drop the leading `_`)
- [ ] 2.5 Update every `from beacon.utils.agents import …`, `from beacon.utils.skills import …`, `from beacon.checksums import …` call-site (CLI, adopt.py, distributor.py, tests)
- [ ] 2.6 Run regression + smoke tests
  - **Input**: `.venv/bin/pytest libs/beacon/tests/ -v` then `cd /tmp && rm -rf abc-smoke && .venv/bin/abc init abc-smoke && cd abc-smoke && .venv/bin/abc sync` (against `examples/sample-warehouse/`)
  - **Expected Output**: Pytest exits 0 with zero failures; `abc sync` completes with the standard "Synced N artifacts" summary line.
  - **Validation**: No test regressed; `abc sync` returns exit code 0; `.agentic-beacon/` in the smoke project contains the expected agents and skills.
- [ ] 2.7 Flip the corresponding `xfail` markers in `test_architecture.py` to regular assertions
- [ ] 2.8 Land PR 1

## 3. Move `warehouse` domain (PR 2)

**Goal**: Consolidate warehouse connect/validate/catalog under one domain; delete the orphaned top-level `warehouse/` package.
**Input**: PR 1 merged. `warehouse/validator.py` and `utils/catalog.py` still in original locations; `beacon/warehouse/` package still exists as a single-file package.
**Output**: `beacon/domains/warehouse/{validator,catalog}.py`; `beacon/warehouse/` deleted.
**Validation**: `ls libs/beacon/src/beacon/warehouse/` fails (directory removed); `pytest` + `abc warehouse connect` + `abc warehouse validate` smoke all green.

- [ ] 3.1 Move `beacon/warehouse/validator.py` → `beacon/domains/warehouse/validator.py`
- [ ] 3.2 Move `beacon/utils/catalog.py` → `beacon/domains/warehouse/catalog.py`
- [ ] 3.3 Remove the now-empty `beacon/warehouse/` package
- [ ] 3.4 Rename `_`-prefixed cross-module names
- [ ] 3.5 Update all call-sites (`beacon/core/cli/warehouse.py`, adopt, tests)
- [ ] 3.6 Run regression + smoke
  - **Input**: `.venv/bin/pytest libs/beacon/tests/` then `.venv/bin/abc warehouse connect --path examples/sample-warehouse` and `.venv/bin/abc warehouse validate`
  - **Expected Output**: Pytest exits 0; connect writes `.agentic-beacon/config.toml`; validate prints "Warehouse is valid" and exits 0.
  - **Validation**: Both subcommands exit 0; no stack traces; `.agentic-beacon/config.toml` contents match previous-PR baseline.
- [ ] 3.7 Land PR 2

## 4. Move `distribution` domain (PR 3)

**Goal**: Move the sync engine, delta engine, distributor, upgrader, and sync-state bookkeeping into a single domain. This is the largest single PR; it also vacates `core/sync.py` and `core/delta.py` from `core/`.
**Input**: PR 2 merged. Sync engine and delta engine still in `core/`; distributor/upgrader still top-level; sync_state still in `utils/`.
**Output**: `beacon/domains/distribution/{distributor,upgrader,sync_engine,delta,state}.py`; `beacon/core/sync.py` and `beacon/core/delta.py` deleted; `beacon/distributor.py`, `beacon/upgrader.py`, `beacon/utils/sync_state.py` deleted.
**Validation**: `pytest` + `abc sync` (fresh + incremental) + `abc upgrade` + `abc doctor` all green; sync state file `.sync-state` still written with same format.

- [ ] 4.1 Move `beacon/distributor.py` → `beacon/domains/distribution/distributor.py`
- [ ] 4.2 Move `beacon/upgrader.py` → `beacon/domains/distribution/upgrader.py`
- [ ] 4.3 Move `beacon/core/sync.py` → `beacon/domains/distribution/sync_engine.py`
- [ ] 4.4 Move `beacon/core/delta.py` → `beacon/domains/distribution/delta.py` (the engine; contribution-facing views move in PR 6)
- [ ] 4.5 Move `beacon/utils/sync_state.py` → `beacon/domains/distribution/state.py` (sync-state bookkeeping is distribution's own aggregate)
- [ ] 4.6 Rename cross-module `_`-prefixed names (e.g. `_check_sync_state` → `check_sync_state`, `_read_sync_sha` → `read_sync_sha`, etc.)
- [ ] 4.7 Update all call-sites (CLI main, adopt, contribute, tests)
- [ ] 4.8 Run regression + smoke
  - **Input**: `.venv/bin/pytest libs/beacon/tests/` then, in a scratch project connected to `examples/sample-warehouse/`: `abc sync` (fresh clone), `abc sync` (again, incremental path), `abc upgrade`, `abc doctor`
  - **Expected Output**: Pytest exits 0. Fresh `abc sync` emits "Synced N artifacts"; incremental emits "Already up to date" or a delta summary. `abc upgrade` reports template status. `abc doctor` prints a clean report.
  - **Validation**: All commands exit 0; `.sync-state` file in the scratch project contains a 40-char SHA matching `git -C examples/sample-warehouse rev-parse HEAD`.
- [ ] 4.9 Land PR 3

## 5. Move `setup` domain (PR 4)

**Goal**: Consolidate `abc init`/`abc setup` flows and CLAUDE.md/opencode wiring under one domain.
**Input**: PR 3 merged. `initializer.py` and `utils/wiring.py` in their original locations with ~15 `_`-prefixed cross-module names in wiring.py.
**Output**: `beacon/domains/setup/{initializer,wiring}.py`; all wiring helpers public-named.
**Validation**: `abc init`, `abc setup --manual`, and `abc setup --agent-assisted` all succeed end-to-end on a scratch project.

- [ ] 5.1 Move `beacon/initializer.py` → `beacon/domains/setup/initializer.py`
- [ ] 5.2 Move `beacon/utils/wiring.py` → `beacon/domains/setup/wiring.py`
- [ ] 5.3 Rename cross-module `_`-prefixed names (~15 functions in wiring.py alone)
- [ ] 5.4 Update all call-sites (CLI main, tests)
- [ ] 5.5 Run regression + smoke
  - **Input**: `.venv/bin/pytest libs/beacon/tests/` then, in a scratch project: `abc init`, `abc setup --manual`, remove `beacon.yaml`, `abc setup --agent-assisted`
  - **Expected Output**: Pytest exits 0. `abc init` creates `.agentic-beacon/` with expected files; `abc setup --manual` writes `beacon.yaml` with an empty template; `abc setup --agent-assisted` installs the project-setup skill and prints next-steps guidance.
  - **Validation**: Exit 0 on each; `.agentic-beacon/beacon.yaml` and `.agentic-beacon/config.toml` match baseline; CLAUDE.md/opencode.json wiring identical to pre-PR baseline (diff-check against a pre-PR snapshot).
- [ ] 5.6 Land PR 4

## 6. Move `adoption` domain (PR 5)

**Goal**: Isolate the largest single file (`adopt.py`, 1175 lines) into its own domain. Considered late because its complexity carries the highest chance of subtle breakage, and the previous PRs teach us the move pattern.
**Input**: PR 4 merged. `adopt.py` still at top-level.
**Output**: `beacon/domains/adoption/adopter.py` (or split if natural seams appear during the move).
**Validation**: `abc adopt` on a sample project reproduces the previous-PR output byte-for-byte on non-interactive paths; interactive paths reviewed by a human.

- [ ] 6.1 Move `beacon/adopt.py` → `beacon/domains/adoption/adopter.py` (consider splitting 1175-line file during move if natural seams exist; otherwise move as-is and file a follow-up)
- [ ] 6.2 Rename cross-module `_`-prefixed names
- [ ] 6.3 Update all call-sites (CLI main, tests)
- [ ] 6.4 Run regression + smoke
  - **Input**: `.venv/bin/pytest libs/beacon/tests/` then `abc adopt --dry-run` against a sample project that has existing agents (see `examples/sample-warehouse` for a template)
  - **Expected Output**: Pytest exits 0. `abc adopt --dry-run` prints the same proposed changes as a pre-PR snapshot.
  - **Validation**: `diff <(abc adopt --dry-run)` against baseline is empty; any difference investigated before merging.
- [ ] 6.5 **[MANUAL]** Human acceptance smoke — run `abc adopt` (interactive, no `--dry-run`) on a real sample project; confirm the prompts, preview output, and final `.agentic-beacon/` contents match expectations. Required before merging PR 5 per proposal.md "Manual Intervention Requirements".
- [ ] 6.6 Land PR 5

## 7. Move `contribution` domain (PR 6)

**Goal**: Relocate contribute flow and split the 878-line `utils/delta.py` between the distribution engine (any remaining engine glue) and the contribution user-facing views.
**Input**: PR 5 merged. `contribute.py` (605 lines) and `utils/delta.py` (878 lines) still in `utils/`.
**Output**: `beacon/domains/contribution/{contributor,delta_view}.py`; any engine leftovers from `utils/delta.py` absorbed into `domains/distribution/delta.py` (consistent with Decision 5 Open Question resolved here).
**Validation**: `abc contribute --all` and `abc contribute <artifact>` behave identically to pre-PR baseline.

- [ ] 7.1 Move `beacon/utils/contribute.py` → `beacon/domains/contribution/contributor.py`
- [ ] 7.2 Analyse `beacon/utils/delta.py` (878 lines) — separate engine callers from user-facing views (per design.md Open Questions)
- [ ] 7.3 Move user-facing pieces of `utils/delta.py` → `beacon/domains/contribution/delta_view.py`; any remaining engine glue moves to `domains/distribution/delta.py`
- [ ] 7.4 Rename cross-module `_`-prefixed names
- [ ] 7.5 Update all call-sites (CLI main, tests)
- [ ] 7.6 Run regression + smoke
  - **Input**: `.venv/bin/pytest libs/beacon/tests/` then, in a scratch project with local changes vs. the warehouse: `abc contribute --all --dry-run` and `abc contribute <specific-artifact> --dry-run`
  - **Expected Output**: Pytest exits 0. Contribute preview output matches pre-PR baseline.
  - **Validation**: Diff of `abc contribute --all --dry-run` output against baseline is empty.
- [ ] 7.7 Land PR 6

## 8. Thin the CLI layer (PR 7)

**Goal**: Move CLI to its canonical location (`beacon/cli/`), replace all `utils/` imports with `domains/` imports, and enforce the thin-CLI rule (each handler = parsing + one domain call + formatting).
**Input**: PR 6 merged. CLI still lives at `beacon/core/cli/`; `main.py` is 1757 lines with dozens of `from beacon.utils.*` imports.
**Output**: `beacon/cli/` package; no `utils.*` imports in CLI; TC8 (`test_cli_handlers_have_no_io`) flips from `xfail` to passing.
**Validation**: Every `abc` subcommand still works; `main.py` size reduced (target: below 800 lines, split by group if needed).

- [ ] 8.1 Rename `beacon/core/cli/` → `beacon/cli/`; update `beacon/cli.py` shim import
- [ ] 8.2 Replace all `from beacon.utils.*` imports in `cli/main.py` and `cli/warehouse.py` with `from beacon.domains.*` imports
- [ ] 8.3 Verify each handler contains only: argument parsing + one domain call + output formatting (per the "Thin CLI layer" spec requirement). Inline any leftover helpers into their owning domain.
  - **Input**: `.venv/bin/pytest libs/beacon/tests/test_architecture.py::test_cli_handlers_have_no_io -v`
  - **Expected Output**: Test passes (no longer `xfail`).
  - **Validation**: No CLI handler body contains `open()`, `Path.write_text`, `Path.read_text`, `yaml.load`, `tomllib.load`, or `subprocess.run`; AST scan confirms.
- [ ] 8.4 (Optional, if file remains > ~800 lines) Split `cli/main.py` by subcommand group: `cli/setup.py`, `cli/sync.py`, `cli/contribute.py`, `cli/agent.py`. Keep `cli/main.py` as the Click group + registration only.
- [ ] 8.5 Run regression + full subcommand smoke
  - **Input**: `.venv/bin/pytest libs/beacon/tests/` then run every `abc` subcommand once on a scratch project (at minimum: `--version`, `init`, `warehouse connect`, `setup --manual`, `sync`, `doctor`, `contribute --all --dry-run`, `upgrade`, `agent list`, `agent install <name>`).
  - **Expected Output**: Every subcommand exits 0 with the same user-visible output as pre-PR.
  - **Validation**: No regressions; `abc --help` output diff vs. baseline is empty.
- [ ] 8.6 **[MANUAL]** Human acceptance smoke — required before merging PR 7 per proposal.md "Manual Intervention Requirements". Exercise interactive flows (`abc init`, `abc setup`, `abc adopt`) manually to confirm UX is unchanged.
- [ ] 8.7 Land PR 7

## 9. Clean up and documentation (PR 8)

**Goal**: Delete empty shells, shrink `utils/` and `core/` to their final intended contents, update AGENTS.md and the knowledge base, archive the OpenSpec change.
**Input**: PR 7 merged. Possibly some dead exports in `utils/__init__.py`; `AGENTS.md` still has the old "CLI Layer Discipline" rule.
**Output**: `utils/` contains only `git.py`, `display.py` (total < 500 lines); `core/` contains only `manifest/`, `settings.py`, `exceptions.py`, `gitignore.py`; `AGENTS.md` references the new spec; OpenSpec change archived.
**Validation**: `wc -l libs/beacon/src/beacon/utils/*.py | tail -1` under 500; `ls libs/beacon/src/beacon/core/` lists exactly the four allowed entries; `openspec list` no longer shows the change in `changes/`.

- [ ] 9.1 Delete any now-empty modules; delete `beacon/utils/__init__.py` re-exports if any remain
- [ ] 9.2 Verify `beacon/utils/` contains only `git.py`, `display.py` (and any new `fs.py`); file sizes total < 500 lines
- [ ] 9.3 Verify `beacon/core/` contains only `manifest/`, `settings.py`, `exceptions.py`, `gitignore.py`
- [ ] 9.4 Update `AGENTS.md`: replace "CLI Layer Discipline" rule with a pointer to `openspec/specs/layered-architecture/spec.md`; add a "Domain Layer" section naming the six domains
- [ ] 9.5 Update `knowledge/facts/repository-structure.md` with the new tree
- [ ] 9.6 Update `knowledge/decisions/follow-global-python-standards.md` if the absolute-import rule is strengthened by the new spec
- [ ] 9.7 Archive this change via `/opsx:archive`
  - **Input**: `/opsx:archive introduce-domain-layer`
  - **Expected Output**: Change moves to `openspec/changes/archive/introduce-domain-layer/`; spec merges into `openspec/specs/layered-architecture/spec.md`.
  - **Validation**: `openspec list --json | jq '.changes[] | select(.name == "introduce-domain-layer")'` returns nothing (change no longer active); `ls openspec/specs/layered-architecture/` shows the merged `spec.md`.
- [ ] 9.8 File follow-up issue: optional `import-linter` rule (Decision 6 mechanism 3)
- [ ] 9.9 Land PR 8
