## ADDED Requirements

### Requirement: Four-layer package structure

The `beacon` package SHALL be organized into exactly four layers, each rooted at `libs/beacon/src/beacon/`:

1. `cli/` — presentation (Click command handlers and Rich output).
2. `domains/<name>/` — bounded-context packages holding application and domain logic.
3. `core/` — cross-domain primitives (project-concept models, settings, exceptions).
4. `utils/` — generic technical helpers with no project-specific semantics.

No other top-level code packages SHALL exist under `beacon/` (test packages, `data/`, and `__init__.py` excepted).

#### Scenario: All business logic lives under `domains/`

- **WHEN** a developer adds a new function that operates on warehouse, project, artifact, or sync state
- **THEN** the function MUST be placed in a module under `beacon/domains/<name>/`, not in `cli/`, `core/`, or `utils/`

#### Scenario: No top-level service files

- **WHEN** the repository is inspected
- **THEN** the only `.py` files directly under `libs/beacon/src/beacon/` SHALL be `__init__.py` and `cli.py` (the entry-point shim)

#### Scenario: Layered test catches stray top-level modules

- **WHEN** `pytest tests/test_architecture.py` runs
- **THEN** it SHALL fail if any `.py` file exists directly under `beacon/` other than `__init__.py` and `cli.py`

### Requirement: Dependency direction

Imports between layers SHALL follow one direction only: `cli → domains → core, utils`. Specifically:

- `cli/**` MAY import from `beacon.domains.*`, `beacon.core.*`, `beacon.utils.*`.
- `domains/<name>/**` MAY import from `beacon.core.*`, `beacon.utils.*`, and sibling `beacon.domains.<other>.*` modules.
- `core/**` MUST NOT import from `beacon.cli.*` or `beacon.domains.*`.
- `utils/**` MUST NOT import from `beacon.cli.*`, `beacon.domains.*`, or `beacon.core.*`.

#### Scenario: `core/` does not depend on `domains/`

- **WHEN** `pytest tests/test_architecture.py` runs
- **THEN** it SHALL fail if any module under `beacon/core/` contains a `from beacon.domains` or `from beacon.cli` import (or the `import beacon.domains` / `import beacon.cli` equivalents)

#### Scenario: `utils/` does not depend on `core/` or above

- **WHEN** `pytest tests/test_architecture.py` runs
- **THEN** it SHALL fail if any module under `beacon/utils/` contains a `from beacon.cli`, `from beacon.domains`, or `from beacon.core` import

#### Scenario: Cross-domain imports go through top-level modules

- **WHEN** a module in `beacon/domains/<A>/` imports from `beacon/domains/<B>/`
- **THEN** the import path MUST reference a module directly under `beacon/domains/<B>/`, not a deeper internal module

### Requirement: Bounded contexts

The `domains/` package SHALL contain exactly these six bounded contexts, each owning the concerns listed:

| Domain | Concerns |
|---|---|
| `warehouse` | Warehouse connect, validate, and catalog operations |
| `setup` | Project initialization, `beacon.yaml` creation, agent-config wiring (CLAUDE.md, AGENTS.md, opencode) |
| `adoption` | The `abc adopt` flow for taking an existing project's artifacts into a warehouse |
| `distribution` | Warehouse-to-project sync engine, delta engine, distributor, upgrader, and sync-state bookkeeping (read by contribution and doctor as cross-domain consumers) |
| `contribution` | Project-to-warehouse contribute flow, user-facing delta views |
| `artifact` | Artifact model and operations for agents, skills, rules, commands, contexts; checksums |

New domains MAY be added by a subsequent change proposal; the set SHALL NOT be expanded ad-hoc.

#### Scenario: Each domain has a one-sentence scope

- **WHEN** a new `.py` file is added under `beacon/domains/<name>/`
- **THEN** the file's contents MUST fit within `<name>`'s scope sentence from the table above

#### Scenario: Adding a new domain requires a spec change

- **WHEN** a developer proposes a new top-level package under `beacon/domains/`
- **THEN** they MUST first submit an OpenSpec change modifying this requirement to include the new domain

### Requirement: Thin CLI layer

Modules under `beacon/cli/` SHALL contain only Click command handlers, argument parsing, and output formatting. Each handler SHALL delegate to one or more `beacon.domains.*` entry points for all business logic.

#### Scenario: No file I/O in CLI handlers

- **WHEN** a CLI handler needs to read or write files
- **THEN** it MUST call a domain function; it MUST NOT call `open()`, `Path.write_text`, `Path.read_text`, `yaml.load`, `tomllib.load`, `subprocess.run`, or similar I/O primitives directly

#### Scenario: No domain logic helpers in `cli/`

- **WHEN** a CLI handler needs a helper function
- **THEN** the helper MUST live in the relevant domain package, not in a `cli/` module

### Requirement: Utility eligibility

A module SHALL only live under `beacon/utils/` if it is a generic technical helper with no project-specific semantics. A module qualifies as generic if it could be lifted into an unrelated Python project without modification.

Project-concept code (warehouse, artifact, manifest, sync, delta, etc.) SHALL NOT live in `utils/`.

#### Scenario: Git helpers qualify

- **WHEN** a module wraps git subprocess invocations with no knowledge of warehouses or beacon files
- **THEN** it MAY live under `beacon/utils/`

#### Scenario: Agent/skill operations do not qualify

- **WHEN** a module handles agent or skill discovery, installation, or wiring
- **THEN** it MUST live under `beacon/domains/artifact/`, not `beacon/utils/`

#### Scenario: Sync state does not qualify

- **WHEN** a module reads or writes sync SHA or relinks sync state
- **THEN** it MUST live under `beacon/domains/distribution/`, not `beacon/utils/`

### Requirement: No underscore-prefixed cross-module names

Any function, class, or constant defined in module A and imported by module B SHALL NOT begin with a leading underscore. The `_` prefix is reserved for truly module-local names.

#### Scenario: Imported name has no leading underscore

- **WHEN** module B contains `from beacon.domains.artifact.agent import X`
- **THEN** `X` MUST NOT start with `_`

#### Scenario: Architecture test catches `_`-prefixed imports

- **WHEN** `pytest tests/test_architecture.py` runs
- **THEN** it SHALL fail if any `from beacon.*` import statement references a name beginning with `_`

### Requirement: Empty `__init__.py` files

Every `__init__.py` under `beacon/` SHALL contain only a module docstring (or be empty). It SHALL NOT re-export names, define `__all__`, or execute import side effects.

#### Scenario: `__init__.py` has no executable imports

- **WHEN** `pytest tests/test_architecture.py` runs
- **THEN** it SHALL fail if any `__init__.py` under `beacon/` contains an `import` or `from` statement, an `__all__` assignment, or any non-docstring statement

### Requirement: Architecture verification test

The repository SHALL include `libs/beacon/tests/test_architecture.py` which validates every scenario marked "architecture test" above. This test SHALL run as part of the default `pytest` invocation.

#### Scenario: Architecture test runs by default

- **WHEN** a contributor runs `pytest` from the repository root
- **THEN** `test_architecture.py` SHALL be collected and executed without requiring extra flags or markers
