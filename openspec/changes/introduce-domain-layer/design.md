## Context

The `beacon` Python package currently has no consistent layering:

```
libs/beacon/src/beacon/
├── cli.py                    # 5 lines — shim (ok)
├── adopt.py                  # 1175 lines — service
├── distributor.py            #  454 lines — service
├── initializer.py            #  230 lines — service
├── upgrader.py               #  265 lines — service
├── checksums.py              #   56 lines — service (tiny)
├── core/
│   ├── cli/                  # ← CLI inside "core"
│   │   ├── main.py           # 1757 lines — Click handlers + direct imports of _private helpers
│   │   └── warehouse.py      #  396 lines
│   ├── manifest/             # domain models (ok)
│   ├── delta.py              #  671 lines — sync engine, not a model
│   ├── sync.py               #  436 lines — sync engine, not a model
│   ├── gitignore.py
│   ├── settings.py
│   └── exceptions.py
├── utils/                    # ~3400 lines of business logic labelled "utils"
│   ├── agents.py             #  470 lines
│   ├── contribute.py         #  605 lines
│   ├── delta.py              #  878 lines
│   ├── skills.py             #  489 lines
│   ├── wiring.py             #  355 lines
│   ├── sync_state.py         #  213 lines
│   ├── catalog.py            #  132 lines
│   ├── display.py            #  119 lines — actually a utility
│   └── git.py                #  207 lines — actually a utility
└── warehouse/
    └── validator.py
```

`core/cli/main.py` imports ~40 `_`-prefixed functions from seven different `utils/*` modules. The leading underscore is a lie — these are cross-module public APIs. `AGENTS.md` already documents a "CLI Layer Discipline" rule but has no structural enforcement: the only place to put new code that isn't clearly CLI or a domain model is `utils/`, so that's where everything lands.

The team has started moving in the right direction (the recent `refactor: split cli into core/cli package` and `refactor: extract manifest models into core/manifest/` commits), but there is no destination for domain logic.

## Goals / Non-Goals

**Goals:**

- Introduce a `domains/` layer between `cli/` and `core/`+`utils/`, split by bounded context, so every unit of business logic has one obvious home.
- Reduce `utils/` to genuine shared primitives (git, display, filesystem). Target: under 500 lines total.
- Make the CLI layer thin: each handler is ≤ ~40 lines of argument validation + one domain service call + output formatting.
- Remove `_`-prefix names on any function that crosses a module boundary. A leading underscore must mean "module-private".
- Encode the architecture as a testable OpenSpec capability (`layered-architecture`) so future proposals can be checked against it.
- Preserve 100% of user-facing behavior. The `abc` CLI, file formats, and spec-level behavior do not change.

**Non-Goals:**

- **Not** introducing interfaces, DI containers, or hexagonal ports/adapters. Python's import system is the layering mechanism; we enforce direction by convention and (optionally) a lint rule.
- **Not** splitting the package into multiple distributions.
- **Not** rewriting any existing logic. Every function moves; none are re-authored. Renames are limited to removing leading underscores.
- **Not** changing the test framework or adding a new test layer (no "unit vs. integration" split in this change).
- **Not** touching the warehouse examples or docs beyond import-path updates.

## Decisions

### Decision 1 — Target layout: four layers, domain owns the middle

```
beacon/
├── cli/              # presentation (Click handlers, Rich output)
├── domains/          # application + domain per bounded context
│   ├── warehouse/
│   ├── setup/
│   ├── adoption/
│   ├── distribution/
│   ├── contribution/
│   └── artifact/
├── core/             # cross-domain primitives (models, settings, exceptions)
└── utils/            # generic helpers (git, display, fs)
```

**Dependency rule (enforced by convention, verified by spec):**

```
cli → domains → core, utils
                domains may import sibling domains' public APIs
core, utils  never import from domains or cli
```

**Why flat `domains/<name>/` rather than separating `application/` and `domain/` sub-layers (classical DDD):** the codebase is ~9,500 lines; a two-sub-layer split per domain would create 14 packages where 7 suffice. Python lacks the ceremony (no interfaces, no IoC) that justifies the classical split. A single domain package with free functions and Pydantic models is idiomatic and sufficient.

**Alternative considered — `services/` instead of `domains/`:** rejected because several contexts (e.g., `warehouse`, `artifact`) hold both behavior and data; "service" overstates the behavior-only reading.

### Decision 2 — Bounded contexts

Six contexts, derived by grouping the current code by what it actually operates on:

| Domain | Current sources | Owns |
|---|---|---|
| `warehouse` | `warehouse/validator.py`, `utils/catalog.py`, warehouse CLI pieces | Warehouse connect/validate/catalog |
| `setup` | `initializer.py`, `utils/wiring.py` | `abc setup`, beacon.yaml creation, CLAUDE.md/opencode wiring |
| `adoption` | `adopt.py` | `abc adopt` flow |
| `distribution` | `distributor.py`, `upgrader.py`, `core/sync.py`, `core/delta.py`, `utils/sync_state.py` | Warehouse → project sync, upgrades, and sync-state bookkeeping |
| `contribution` | `utils/contribute.py`, `utils/delta.py` | Project → warehouse contribute flow |
| `artifact` | `utils/agents.py`, `utils/skills.py`, `checksums.py` | Agent/skill/rule artifact operations |

**Why `distribution` owns the sync and delta engines** (not `core/`): they implement a domain workflow (pulling snapshots from a warehouse into a project), not a cross-domain primitive. Keeping them in `core/` would reproduce today's confusion.

**Why `sync_state` belongs inside `distribution`** (not a separate domain): sync state is the distribution engine's own bookkeeping — written at the end of a successful sync, and read back on the next sync to detect staleness. That other domains (contribution, CLI doctor) read it is normal cross-domain access, not a reason to lift it to its own domain. An aggregate owns its state.

**Why `artifact` is a domain, not part of `setup`/`distribution`**: agent and skill handling cross-cuts — `setup` wires them, `distribution` syncs them, `contribution` deltas them. A shared `artifact` domain holds the artifact model/operations all three depend on.

### Decision 3 — Naming and privacy

- Domain package names are singular and kebab-translated to snake_case (`warehouse`, `artifact`, not `warehouses`).
- Function names: drop the `_` prefix on anything called from outside its defining module. `_build_agents_paths` → `build_agents_paths`. Keep `_` only for truly module-local helpers.
- `__init__.py` stays empty (docstring only) per the existing project rule — imports go to the defining module.
- No re-exports, no `__all__`.

### Decision 4 — `core/` vs `utils/` split

Keep both layers; their purposes differ:

- **`core/`** — cross-domain building blocks that encode *project concepts*: manifest models, settings schema, exceptions, the `.gitignore` writer (because it represents a project invariant).
- **`utils/`** — generic technical helpers with no project-specific semantics: git subprocess wrappers, Rich console helpers, filesystem ops. A file only belongs here if it could theoretically be lifted into another Python project unchanged.

This lets us reject the current lazy pattern of dropping anything non-CLI into `utils/`.

### Decision 5 — Migration strategy: one domain per PR

Do **not** attempt a single atomic refactor. Sequence:

1. **PR 0** — add `domains/` skeleton, move no code. Land the `layered-architecture` spec.
2. **PR 1** — move `artifact` domain (agents, skills, checksums). Lowest-coupling first — feeds into every other domain.
3. **PR 2** — move `warehouse` domain (validator, catalog).
4. **PR 3** — move `distribution` domain (distributor, upgrader, sync engine, delta engine, sync_state). Largest; pulls `core/sync.py` + `core/delta.py` out of `core/`.
5. **PR 4** — move `setup` domain (initializer, wiring).
6. **PR 5** — move `adoption` domain (adopt.py is 1175 lines; isolate last).
7. **PR 6** — move `contribution` domain (contribute + user-facing delta views).
8. **PR 7** — thin `cli/main.py`: replace imports-from-utils with imports-from-domains, un-underscore public names.
9. **PR 8** — delete empty shells, update `AGENTS.md`, update knowledge base pointers.

Each PR is self-contained and leaves tests green. Rollback of any PR is just a revert.

**Why not do it in a single PR:** a single PR touching ~9,500 lines would be unreviewable and would block other work for days. Per-domain PRs are reviewable in under an hour each and parallelisable with other feature work.

### Decision 6 — Enforcement

Three mechanisms, ordered by cost:

1. **Convention documented in the `layered-architecture` spec** — required; zero-cost; the baseline.
2. **A short `tests/test_architecture.py`** that walks `beacon/` and asserts dependency direction (e.g., `core/` modules have no `from beacon.domains` or `from beacon.cli` imports). Low-cost; runs in CI. **Include in this change.**
3. **An `import-linter` or `ruff` custom rule** — deferred to a follow-up if the test proves flaky or hard to read.

## Impacted Modules & Systems

**Code Changes (source):**
- `libs/beacon/src/beacon/cli.py` — entry-point shim; import path updates only
- `libs/beacon/src/beacon/core/cli/main.py` (1757 lines) — every import-from-utils replaced; each handler trimmed to thin delegation; eventually renamed to `beacon/cli/main.py`
- `libs/beacon/src/beacon/core/cli/warehouse.py` (396 lines) — same as main.py; renamed to `beacon/cli/warehouse.py`
- `libs/beacon/src/beacon/adopt.py` (1175 lines) → `libs/beacon/src/beacon/domains/adoption/adopter.py`
- `libs/beacon/src/beacon/distributor.py` (454 lines) → `libs/beacon/src/beacon/domains/distribution/distributor.py`
- `libs/beacon/src/beacon/initializer.py` (230 lines) → `libs/beacon/src/beacon/domains/setup/initializer.py`
- `libs/beacon/src/beacon/upgrader.py` (265 lines) → `libs/beacon/src/beacon/domains/distribution/upgrader.py`
- `libs/beacon/src/beacon/checksums.py` (56 lines) → `libs/beacon/src/beacon/domains/artifact/checksums.py`
- `libs/beacon/src/beacon/core/sync.py` (436 lines) → `libs/beacon/src/beacon/domains/distribution/sync_engine.py`
- `libs/beacon/src/beacon/core/delta.py` (671 lines) → `libs/beacon/src/beacon/domains/distribution/delta.py`
- `libs/beacon/src/beacon/warehouse/validator.py` (124 lines) → `libs/beacon/src/beacon/domains/warehouse/validator.py` (the `warehouse/` package is then deleted)
- `libs/beacon/src/beacon/utils/agents.py` (470 lines) → `libs/beacon/src/beacon/domains/artifact/agent.py`
- `libs/beacon/src/beacon/utils/skills.py` (489 lines) → `libs/beacon/src/beacon/domains/artifact/skill.py`
- `libs/beacon/src/beacon/utils/contribute.py` (605 lines) → `libs/beacon/src/beacon/domains/contribution/contributor.py`
- `libs/beacon/src/beacon/utils/delta.py` (878 lines) → split between `domains/contribution/delta_view.py` and `domains/distribution/delta.py`
- `libs/beacon/src/beacon/utils/wiring.py` (355 lines) → `libs/beacon/src/beacon/domains/setup/wiring.py`
- `libs/beacon/src/beacon/utils/sync_state.py` (213 lines) → `libs/beacon/src/beacon/domains/distribution/state.py`
- `libs/beacon/src/beacon/utils/catalog.py` (132 lines) → `libs/beacon/src/beacon/domains/warehouse/catalog.py`
- `libs/beacon/src/beacon/utils/git.py` (207 lines) — stays in `utils/` (genuine utility)
- `libs/beacon/src/beacon/utils/display.py` (119 lines) — stays in `utils/` (genuine utility)
- `libs/beacon/src/beacon/core/manifest/` — stays in `core/` (domain models)
- `libs/beacon/src/beacon/core/settings.py`, `exceptions.py`, `gitignore.py` — stay in `core/`

**Code Changes (tests):**
- `libs/beacon/tests/**/*.py` — every test that imports from `beacon.utils.*`, `beacon.adopt`, `beacon.distributor`, `beacon.initializer`, `beacon.upgrader`, `beacon.checksums`, `beacon.core.sync`, `beacon.core.delta`, or `beacon.warehouse` must update its import paths. Test logic unchanged.
- `libs/beacon/tests/test_architecture.py` — **new** file added in PR 0, validates every architectural rule in `specs/layered-architecture/spec.md`.

**Data/Schema Changes:**
- None. No database, no Pydantic model, no file format changes.

**Configuration Changes:**
- None. `pyproject.toml`, `settings.toml`, `beacon.yaml`, and CI workflows are untouched.

**Infrastructure Changes:**
- None.

**Documentation Changes:**
- `AGENTS.md` — "CLI Layer Discipline" rule replaced with pointer to new spec; new "Domain Layer" section naming the six domains.
- `knowledge/facts/repository-structure.md` — regenerated with new tree.
- `knowledge/decisions/follow-global-python-standards.md` — strengthened if the new spec adds rules beyond what exists.

**Repository Branch Strategy:**
- Repositories to be modified: `agentic-beacon` (this repo; single-repo change)
- Feature branch naming: one branch per PR in the sequence — e.g., `refactor/domain-skeleton` (PR 0), `refactor/domain-artifact` (PR 1), `refactor/domain-warehouse` (PR 2), `refactor/domain-distribution` (PR 3), `refactor/domain-setup` (PR 4), `refactor/domain-adoption` (PR 5), `refactor/domain-contribution` (PR 6), `refactor/cli-thinning` (PR 7), `refactor/cleanup-docs` (PR 8)
- Base branch: `main` for PR 0; each subsequent PR branches from the previous PR's merge commit on `main` (strict sequencing — no parallel PRs in this refactor)
- Branch cutting: the agent runs `git checkout main && git pull && git checkout -b <branch>` before each PR's work begins

## Risks / Trade-offs

- **[Risk] Merge conflicts during the multi-PR sequence** → Mitigation: each PR is scoped to one domain; sequence them serially. Pause other refactors in affected files until the sequence completes.
- **[Risk] Hidden call-sites miss the rename from `_private` to `public`** → Mitigation: grep-verify before and after each PR; the architecture test catches imports from `_`-prefixed names at module boundaries.
- **[Risk] Developers continue to drop new logic into `utils/` out of habit** → Mitigation: the `layered-architecture` spec's "utils eligibility" scenario is testable; CI review catches violations.
- **[Risk] The `artifact` domain becomes a second dumping ground** → Mitigation: the spec requires each domain's scope to be articulable in one sentence; `artifact` = "definition, identification, and integrity of distributable artifact types (agents, skills, rules, commands, contexts)". Anything that doesn't fit that sentence does not belong there.
- **[Trade-off] No DDD ceremony (aggregates, repositories, domain events)** → we gain simplicity at the cost of formal purity. The package is too small to benefit from full DDD; we adopt only the bounded-context idea. If scale grows, we can layer the rest on.
- **[Trade-off] `domains/*` cross-imports are allowed** → simpler than forcing every cross-domain call through a shared facade, but risks tangling. Mitigation: the spec requires cross-domain imports to use the importee's top-level `domains/<name>/*.py` modules, not internals.

## Migration Plan

1. Merge PR 0 (skeleton + spec). Freeze non-trivial edits to `utils/` and top-level service files during the sequence.
2. Execute PRs 1–8 in order. After each, run the full test suite (`pytest`) and one happy-path smoke: `abc init`, `abc warehouse connect`, `abc sync` against `examples/sample-warehouse/`.
3. On completion, update `AGENTS.md`:
   - Replace "CLI Layer Discipline" rule with a pointer to the new spec.
   - Add a "Domain Layer" section naming the six domains.
4. Update `knowledge/facts/repository-structure.md` with the new tree.
5. Open a follow-up issue for the optional `import-linter` rule (Decision 6, mechanism 3).

**Rollback**: each PR is reverted independently. If a later-sequence PR uncovers a design flaw, revert only from that PR forward; earlier domain moves stand on their own.

## Open Questions

- Should `cli/main.py` be split per-subcommand-group (`cli/setup.py`, `cli/sync.py`, etc.) in PR 8, or left as one large file? Leaning toward splitting, because 1757 lines will still be too large even after logic is removed — but this is a presentation concern that can slip to a follow-up.
- Should `core/` be renamed to `shared/` once the sync/delta engines leave? Argument for: "core" is overloaded and the remaining contents (models, settings) read as "shared primitives". Argument against: churn. Default: keep `core/`.
- Does `contribution` need its own delta-view module, or should it import from `distribution/delta.py`? Current `utils/delta.py` is 878 lines and mixes both engine output and contribution user-facing views. Resolve during PR 7 with a second read.
