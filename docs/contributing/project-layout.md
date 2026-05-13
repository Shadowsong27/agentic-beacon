# Project Layout

This file describes the directory structure of the Agentic Beacon repository and explains the organizing principles that govern where code lives.

← [Back to CONTRIBUTING.md](../../CONTRIBUTING.md)

---

## Top-level Structure

```
agentic-beacon/
├── libs/
│   └── beacon/               # The CLI package — the primary development target
│       ├── src/beacon/       # All production source code
│       ├── tests/            # All tests (unit + integration)
│       └── pyproject.toml    # Package manifest for agentic-beacon
├── docs/                     # Conceptual design documentation
│   ├── contributing/         # This directory — contributor reference docs
│   └── ...
├── site-docs/                # MkDocs source for the public documentation site
├── examples/                 # Example beacon.yaml configurations
├── guides/                   # User-facing workflow guides
├── openspec/                 # OpenSpec change artifacts (design specs and tasks)
│   ├── changes/              # In-progress and archived changes
│   └── specs/                # Canonical specifications
├── scripts/                  # Utility scripts (e.g. release automation)
├── pyproject.toml            # Workspace root manifest (uv workspace definition)
├── mkdocs.yml                # MkDocs configuration
├── AGENTS.md                 # Project context for AI coding agents
├── CLAUDE.md                 # Claude Code context pointer (references AGENTS.md)
├── CONTRIBUTING.md           # Contributor onboarding guide
└── CHANGELOG.md              # Release changelog (managed by release-please)
```

The repository is a **uv workspace** with a single member: `libs/beacon`. The root `pyproject.toml` declares the workspace; the member's `pyproject.toml` at `libs/beacon/pyproject.toml` declares the published package metadata, dependencies, and build configuration.

**This repo is not itself a warehouse.** A warehouse is a separate git repo that users create with `abc warehouse init`. Do not add `contexts/`, `skills/`, or `knowledge/` directories to this repo.

---

## Source Code Layout (`libs/beacon/src/beacon/`)

The source is organized into a strict **four-layer architecture**:

```
src/beacon/
├── cli/                      # Layer 1: Thin Click command handlers
│   ├── main.py               # Root Click group and command registration
│   ├── adoption.py           # abc adopt
│   ├── agent.py              # abc agents *
│   ├── diagnostics.py        # abc doctor
│   ├── pending_alert.py      # Cross-cutting pending alert helper
│   ├── setup.py              # abc setup, abc warehouse init/connect
│   ├── sync.py               # abc sync, abc status, abc reset, abc list, abc clean
│   └── warehouse.py          # abc warehouse status/contribute
├── domains/                  # Layer 2: All application logic
│   ├── adoption/             # abc adopt flow: TUI, discovery, atomic commit
│   ├── artifact/             # Skill and agent artifact operations
│   ├── distribution/         # Symlink sync, migration, upgrade
│   ├── setup/                # Warehouse init, opencode/CLAUDE.md wiring
│   └── warehouse/            # Connect, validate, catalog, status, contribute
├── core/                     # Layer 3: Cross-domain primitives
│   ├── dependencies/         # Frontmatter parsing, dependency resolver, agent manifest
│   ├── manifest/             # Pydantic models: beacon.yaml, pending.yaml, workspace config
│   ├── scanner/              # Markdown link scanner (for knowledge auto-derivation)
│   ├── exceptions.py         # Exception hierarchy
│   ├── file_filter.py        # Glob pattern matching and path filtering
│   ├── gitignore.py          # .gitignore read/write operations
│   └── settings.py           # Runtime settings (pydantic-settings, ABC_* env vars)
├── utils/                    # Layer 4: Stateless helpers
│   ├── display.py            # Rich-based terminal output helpers
│   ├── git.py                # Git subprocess wrappers
│   ├── interaction.py        # Interactive prompt helpers
│   └── platform.py           # Platform detection and enforcement
├── data/                     # Bundled data distributed with the package
│   ├── skills/               # Bundled skills (record-knowledge, record-skill)
│   │   ├── record-knowledge/ # SKILL.md + scripts/ for knowledge authoring workflow
│   │   └── record-skill/     # SKILL.md + scripts/ for skill scaffolding workflow
│   └── historical_hashes.py  # Checksums for migration detection
└── __init__.py               # Package version declaration
```

---

## Organizing Principles

### Layer boundaries are strictly enforced

The `cli/` layer may only parse arguments and format output. All logic lives in `domains/`. The `core/` and `utils/` layers may not import from `domains/` or `cli/`. These rules are enforced by `tests/unit/test_architecture.py` using AST analysis — a PR that violates them will fail CI.

### Each domain owns its concern completely

The five domains (`adoption`, `artifact`, `distribution`, `setup`, `warehouse`) each encapsulate a bounded context. Logic that belongs to one domain lives entirely within that domain's directory. If a module is only consumed by one domain, it lives inside that domain — not in `core/`.

### `core/` is for multi-domain primitives only

`core/` contains things that multiple domains share: exception types, manifest models (BeaconManifest, PendingManifest, WorkspaceConfig), the dependency resolver, file filter, gitignore manager, and settings. If you are not sure whether something belongs in `core/` or a domain, ask: "Is this consumed by more than one domain?" If no, put it in the domain.

### `__init__.py` files are empty markers

No re-exports, no `__all__`, no convenience imports. Every import must target the defining module directly. This is enforced by TC7 in the architecture tests.

---

## Test Layout

```
libs/beacon/tests/
├── unit/                     # Fast unit tests (run on every push)
│   ├── cli/                  # Tests for CLI-layer behavior
│   ├── core/                 # Tests for core primitives
│   │   ├── dependencies/     # Dependency resolver tests
│   │   ├── manifest/         # Manifest model tests
│   │   └── scanner/          # Scanner tests
│   ├── domains/              # Tests for domain logic
│   │   ├── adoption/         # Adoption TUI and apply tests
│   │   ├── distribution/     # Sync engine and artifact listing tests
│   │   └── warehouse/        # Connector and validator tests
│   ├── utils/                # Utility helper tests
│   ├── warehouse/            # Warehouse contribute and path tests
│   └── test_architecture.py  # Layer boundary enforcement (AST-based)
└── integration/              # End-to-end tests (run on PRs to main)
    ├── conftest.py            # Shared fixtures (e2e_warehouse, e2e_project, isolated_home)
    ├── test_e2e_happy_path.py # Full CLI workflow
    └── ...                    # 20+ integration test files
```

Tests mirror the source structure. A source file at `domains/adoption/apply.py` has a corresponding test at `tests/unit/domains/adoption/test_apply_commit.py`.
