# Architecture

This file describes the overall design of Agentic Beacon: the four-layer architecture, the five domain modules, key data flows, and the major design decisions that shape the codebase.

---

## Overview

Agentic Beacon is a pure CLI tool with no HTTP server, no database, and no persistent background processes. Its entire surface area is a set of `abc` subcommands that manipulate the local filesystem and call `git` as a subprocess. The architecture is designed to be easy to test and easy to enforce — hence the strict layering, which is verified by automated AST analysis in the test suite.

---

## Four-Layer Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        cli/                             │  ← Layer 1
│  Thin Click handlers: parse args, one domain call,      │
│  format output. No logic, no I/O.                       │
└──────────────────────────┬──────────────────────────────┘
                           │ calls
┌──────────────────────────▼──────────────────────────────┐
│                      domains/                           │  ← Layer 2
│  Five domain modules. All application logic lives here. │
│  warehouse | setup | adoption | distribution | artifact │
└──────────┬──────────────────────────┬───────────────────┘
           │ imports                  │ imports
┌──────────▼───────────┐  ┌──────────▼───────────────────┐
│       core/          │  │          utils/               │  ← Layer 3 + 4
│  Cross-domain        │  │  Stateless helpers:           │
│  primitives:         │  │  git, display, interaction,   │
│  exceptions,         │  │  platform                     │
│  manifests,          │  └───────────────────────────────┘
│  settings, resolver  │
└──────────────────────┘
```

**Dependency rule:** `cli/` imports from `domains/`. `domains/` imports from `core/` and `utils/`. `core/` and `utils/` do not import from `domains/` or `cli/`. This is one-directional; never reversed.

**Enforcement:** `libs/beacon/tests/unit/test_architecture.py` uses Python's `ast` module to walk all source files and verify these rules at every CI run. Violations fail CI before they merge.

---

## Five Domains

Each domain encapsulates a bounded context. New logic belongs in the domain that owns the concept.

```
domains/
├── warehouse/      — warehouse connect/validate/catalog; git health; status/contribute
├── setup/          — abc warehouse init; opencode.json and CLAUDE.md wiring
├── adoption/       — abc adopt: TUI browser, three-way (accept/reject/defer), atomic commit
├── distribution/   — symlink sync engine, migration, upgrade, orphan pruning
└── artifact/       — skill and agent artifact operations (wire/unwire, checksums)
```

---

## Entry Points and Key Flows

### CLI Entry Point

The root Click group is registered as `abc` in `pyproject.toml`:
```
abc = "beacon.cli.main:main"
```

`cli/main.py` registers all subcommands and fires `maybe_emit_pending_alert()` on every invocation (cross-cutting concern).

---

### Flow: `abc sync`

`abc sync` is the most complex command. The orchestrator in `domains/distribution/orchestrator.py` drives the following pipeline:

```
cli/sync.py::sync()
  └─► domains/distribution/orchestrator.py::run_sync()
        1. ensure_sync_ready()          — validate .agentic-beacon/config.toml
        2. validate agent manifest      — check agents.yaml + frontmatter
        3. git clean check              — warehouse must be clean
        4. load beacon.yaml             — validate skill entries
        5. dependency resolution        — expand globs, resolve requires:, handle gaps
        6. validate_paths()             — all-or-nothing pre-flight (no partial writes)
        7. detect regular files         — identify migration cases
        8. migrate regular files        — if needed (one-time upgrade)
        9. detect orphans               — symlinks not in beacon.yaml
       10. confirm_prune(orphans)       — ask user which orphans to remove
       11. sync_engine.sync_all()       — create/repair/prune symlinks
       12. post-sync wiring             — .gitignore, opencode.json, CLAUDE.md,
                                          skills, agents, bundled skills, legacy cleanup
```

**Key design:** Step 6 (`validate_paths`) checks all paths before any filesystem mutations. If any path is outside the warehouse, the entire batch aborts with no partial writes.

---

### Flow: `abc adopt`

```
cli/adoption.py::adopt()
  ├─► domains/adoption/discovery.py::discover_pending()    — read .agentic-beacon/pending.yaml
  ├─► domains/adoption/discovery.py::discover_adoptable()  — scan warehouse catalog
  ├─► domains/adoption/tui.py::AdoptApp.run()              — interactive Textual TUI
  │     └─► returns AdoptResult(to_adopt, to_unadopt, pending_accept, pending_reject)
  └─► domains/adoption/apply.py::commit_session()          — atomic commit with rollback
        1. snapshot beacon.yaml + pending.yaml (raw bytes)
        2. apply_adoption()     — update beacon.yaml
        3. sync symlinks        — create/remove artifact symlinks
        4. post-sync wiring     — wire contexts, skills, agents
        5. rewrite pending.yaml — remove accepted/rejected, keep deferred
        ── on any error: _rollback() restores all three pre-states ──
```

**Key design:** `commit_session` is transactional. Any failure during steps 2–5 triggers a rollback that restores `beacon.yaml`, `pending.yaml`, and all created/removed symlinks to their pre-call state.

---

### Flow: `abc warehouse contribute`

```
cli/warehouse.py::contribute()
  └─► domains/warehouse/contribute.py::contribute()
        1. git_health_check()          — validate warehouse is a git repo
        2. get_tracked_paths()         — paths from beacon.yaml
        3. git status --porcelain      — filter to tracked paths
        4. git add <paths>             — stage tracked changes
        5. git commit -m <message>     — commit
        6. git push (if --push)        — push upstream
```

---

## Cross-Cutting Concerns

| Concern | Where it lives | Which domains it serves |
|---|---|---|
| Exception hierarchy | `core/exceptions.py` | All domains and CLI |
| Manifest models | `core/manifest/` | All domains that read/write yaml files |
| Runtime settings | `core/settings.py` | distribution, adoption, artifact |
| Dependency resolver | `core/dependencies/` | distribution (orchestrator) |
| Gitignore management | `core/gitignore.py` | distribution, setup, adoption |
| Pending artifact alert | `cli/pending_alert.py` | Fires in `cli/main.py` on every command |
| Platform guard | `utils/platform.py` | Called at `cli/main.py` startup |

---

## Symlink Distribution Model

The core mechanism of Agentic Beacon is per-file symlinks:

```
.agentic-beacon/artifacts/contexts/coding-standards.md
    ↓ symlink
~/my-org-warehouse/contexts/coding-standards.md   (physical file)
```

`SyncEngine` (`domains/distribution/sync_engine.py`) is the component that creates and manages these symlinks. It validates that every symlink target is inside the warehouse before writing anything, and it repairs or removes stale symlinks. Intermediate directories under `.agentic-beacon/artifacts/` are real directories; only leaf files are symlinks.

**Why symlinks instead of copies?** Any project that has adopted an artifact sees edits to that artifact immediately — no re-sync. One physical file per machine means no divergence.

---

## Atomic Commit Pattern

The `commit_session` function in `domains/adoption/apply.py` implements a manual transaction:

1. **Snapshot**: capture raw bytes of `beacon.yaml` and `pending.yaml`, plus per-path pre-states for tool-dir symlinks
2. **Mutate**: write to yaml files, create/remove symlinks, wire tools
3. **Rollback on error**: restore yaml files from snapshots, remove created symlinks, re-create removed symlinks

Rollback accumulators are three lists: `created_paths`, `removed_paths_with_target`, and `tool_snapshots`. These accumulate as mutations succeed; on failure, they are iterated in reverse to undo exactly what was done.

---

## Architecture Test as Enforcement Mechanism

`libs/beacon/tests/unit/test_architecture.py` (732 lines) uses Python's built-in `ast` module — no live imports of production code — to enforce 10 test cases:

- **TC1**: exactly 5 domain directories exist
- **TC2**: no loose modules directly under `beacon/`
- **TC3**: `core/` does not import from `domains/` or `cli/`
- **TC4**: `utils/` does not import from `domains/`, `cli/`, or `core/`
- **TC5**: cross-domain imports do not exceed depth 4
- **TC6**: no `from X import _private` across module boundaries
- **TC7**: all `__init__.py` files are empty (no re-exports)
- **TC8**: CLI handlers call no I/O operations
- **TC9b**: each CLI handler has at most one domain call (with tracked waivers for known violations)
- **TC10**: domains and core do not import `click`, `rich`, or call `sys.exit` (with tracked waivers)

Violations are tracked in explicit waiver dicts (`_TC9B_WAIVERS`, `_TC10_WAIVERS`) with `TODO` comments linking to cleanup tickets. Stale waivers (where the violation has been fixed but the waiver remains) also fail the test — keeping the waiver list honest.
