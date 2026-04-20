## Why

The `beacon` package has no clear domain layer. Business logic is scattered across three inconsistent locations: top-level service files (`adopt.py` — 1175 lines, `distributor.py`, `initializer.py`, `upgrader.py`), a `utils/` directory (~3400 lines across 10 files) that hosts cross-cutting business logic despite its name, and a `core/` package that mixes domain models, the sync engine, and the CLI itself. The CLI module imports ~40 private (`_`-prefixed) helpers directly from `utils/*.py`, proving those are not utilities at all — they are domain operations leaking their privacy convention. Adding a new domain concept today requires touching all three layers and picking one arbitrarily; developers cannot answer "where does this code belong?" from the folder structure alone.

## What Changes

- **Introduce a domain layer** at `beacon/domains/` split by bounded context: `warehouse`, `setup`, `adoption`, `distribution`, `contribution`, `artifact`. Each domain owns its services, models, workflows, and persisted state as a self-contained package.
- **Thin the CLI layer** (`beacon/cli/`, renamed from `beacon/core/cli/`): Click handlers only — argument parsing, output formatting, and a single call into a domain service per command. No file I/O or business logic in handlers.
- **Shrink `utils/`** to genuine shared primitives only: `git.py` (project-root detection, clean checks), `display.py` (Rich console helpers), and a new `fs.py` if filesystem helpers emerge. Everything else moves to the appropriate domain.
- **Dissolve the top-level service files**: `adopt.py` → `domains/adoption/`; `distributor.py` → `domains/distribution/`; `initializer.py` → `domains/setup/`; `upgrader.py` → `domains/distribution/upgrader.py`; `checksums.py` → `domains/artifact/`.
- **Rationalize `core/`** into `beacon/core/` holding only cross-domain primitives: `manifest/` models, `exceptions.py`, `settings.py`, `gitignore.py`. The sync engine (`core/sync.py`) and delta engine (`core/delta.py`) move to `domains/distribution/sync_engine.py` and `domains/distribution/delta.py`.
- **Remove the `_private` naming on cross-module functions**. Functions imported by another module are part of a public domain API and must be renamed without the leading underscore as part of the move.
- **BREAKING (internal only)**: Import paths change. No public Python API is documented, so external consumers are unaffected; the `abc` CLI surface is unchanged.

## Capabilities

### New Capabilities

- `layered-architecture`: Codifies the rules of the new layered architecture — which concerns belong in CLI, domain, core/shared, and utils layers; the allowed direction of dependencies between layers; naming conventions for domain packages; and the prohibition of private-prefixed names across module boundaries. Future work is validated against this spec.

### Modified Capabilities

<!-- No behavioral spec changes. This refactor preserves all existing behavior; every existing spec continues to hold. -->

## Impact

- **Affected code**: Every `.py` file under `libs/beacon/src/beacon/` except `__init__.py` files. Roughly 9,500 lines of source move or get re-homed.
- **Affected tests**: All tests in `libs/beacon/tests/` must update their import paths. No test logic changes.
- **Public surface**: The `abc` CLI entry point (`beacon.cli:main`) is preserved. `beacon/cli.py` shim keeps working. No change to user-facing behavior, file formats, or configuration.
- **Internal API**: All internal imports change. Anyone importing from `beacon.utils.*`, `beacon.adopt`, `beacon.distributor`, `beacon.initializer`, `beacon.upgrader`, or `beacon.core.*` will need to update.
- **Knowledge base**: The `CLI Layer Discipline` rule in `AGENTS.md` is generalized into the new `layered-architecture` spec. Several `knowledge/decisions/*.md` entries need pointers updated.
- **Dependencies**: None. No new packages; no packages removed.
- **Migration**: Single long-running draft PR accumulates all domain moves incrementally (see design.md for sequencing). Review happens continuously; the branch must stay green. One final squash-merge lands the new architecture atomically.

## Manual Intervention Requirements

- **[Manual Step] Review and merge the single draft PR via the GitHub UI**
  - **Rationale**: Per project policy, merges are performed by a human via GitHub — the agent pushes commits to the draft branch and addresses review feedback, but does not press the green button. Review happens continuously as the draft evolves; one merge at the end lands the full refactor.
  - **Timing**: When all 9 phases are complete, CI is green, and review threads are resolved.

- **[Manual Step] (Optional) Acceptance smoke-test before final merge**
  - **Rationale**: `adopt.py` is 1175 lines and covers the interactive `abc adopt` flow; the CLI thinning phase restructures every handler. These are high-value points for a human to exercise the CLI on a real project to catch interaction regressions the automated smoke tests may miss.
  - **Timing**: Before marking the draft ready-for-merge. The agent runs automated smokes after each phase, but a human review of the interactive UX is strongly advised.

All other work — moves, renames, import rewrites, test runs, non-interactive smoke tests, draft PR management — is automated by the agent.

---

## Enhancement Metadata

**Enhanced**: 2026-04-19
**Methodology**: Spec-Driven Development + TDD
**Enhancements Applied**:
- ✅ Manual intervention requirements identified (PR merges; interactive-flow acceptance after PR 5 and PR 7)
- ✅ Impacted modules and systems documented (full source-to-destination mapping in design.md)
- ✅ Repository branch strategy documented (one branch per PR, strict sequencing)
- ✅ TDD criteria added to the architecture-test task (PR 0) — the one genuine RED-GREEN-REFACTOR cycle in this refactor
- ✅ Phase-level Goal/Input/Output/Validation summaries added to all nine phases
- ✅ Input/Expected Output/Validation added to each PR's regression + smoke-test tasks
- ✅ Risk mitigation strategies formalized in design.md

**Methodology note for reviewers**: Code-move tasks intentionally do NOT carry TC1-TC10 test cases. This refactor is behavior-preserving; the existing test suite IS the regression test, and each PR's success criterion is "pytest still green + smoke-test still green + xfail markers correctly flipped". Inventing new per-move test cases would be test theatre.

**Status**: Ready for implementation via `/opsx:apply introduce-domain-layer`
