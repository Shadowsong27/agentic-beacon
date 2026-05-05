# Agentic Beacon Project Context

Project-level instructions for AI agents working on the Agentic Beacon framework.

---

## Project Overview

**Agentic Beacon** is an opinionated framework for standardizing and distributing agentic engineering artifacts across teams.

**Repository Purpose:**
- Framework source code (CLI tool in `libs/beacon/`)
- Design documentation (`docs/`)
- Usage guides (`guides/`)
- Example warehouse (`examples/sample-warehouse/`)

**This is NOT a warehouse** - it's the framework itself. Users create warehouses with `abc warehouse init`.

**Read:** [Repository Structure](.agentic-beacon/artifacts/knowledge/facts/repository-structure.md)

---

## Development Guidelines

### Artifact Distribution Model

**Decision:** The locally-cloned warehouse is the single write entrypoint for every harness artifact on a machine. Projects reference it via per-file symlinks under `.agentic-beacon/artifacts/`.

- `abc sync` creates symlinks, not copies. One logical artifact = one physical file per machine.
- `abc warehouse contribute` is a thin wrapper around `git add` + `git commit` inside the warehouse clone — it is the **only** supported write path back to the warehouse.
- Cross-project visibility of harness edits on a single machine is **intended**, not a leak: editing a skill through Project A's symlink is editing the warehouse working tree, so Project B's agent sees the edit immediately.
- Platform: macOS / Linux only. Windows is rejected.

**Read:** [Decision: Single Warehouse Write Entrypoint](.agentic-beacon/artifacts/knowledge/decisions/single-warehouse-write-entrypoint.md)

### Configuration Management Patterns

**Decision:** Use Pydantic Settings patterns with consistent terminology

- Module name: `settings.py` (not `config.py`)
- Class names: `WarehouseSettings`, `BeaconSettings`, `SettingsReader`, `SettingsWriter`
- Terminology: Use "settings" consistently throughout (not "config" or "configuration")
- Exceptions: Separate into `exceptions.py` module
- Pattern: Pydantic BaseSettings with TOML support
- Custom structures: Manual parsing with Pydantic validation (beacon.yaml)

**Read:**
- [Decision: Settings Module Structure](.agentic-beacon/artifacts/knowledge/decisions/settings-module-structure.md)
- [Decision: Pydantic Settings Patterns](.agentic-beacon/artifacts/knowledge/decisions/pydantic-settings-patterns.md)

## Development Guidelines

### Temporary Documentation Pattern

**Rule:** Do NOT commit temporary handoff documentation created during agentic coding sessions.

**Examples:** Session handoff docs, implementation checklists, agent-to-agent context files, one-off decision documents.

**Read:** [Decision: No Temporary Docs in Repository](.agentic-beacon/artifacts/knowledge/decisions/no-temporary-docs.md)

### Working with the CLI Package

**Location:** `libs/beacon/`

**Project uses uv workspace** — single `.venv` at repo root, `libs/beacon` is a workspace member.

**Quick commands:**
```bash
# From repo root (one-time setup)
uv sync --group dev

# Test CLI
.venv/bin/abc --version
# OR activate venv first:
source .venv/bin/activate
abc --version
abc warehouse init test-warehouse
```

**Read:** [CLI Development Workflow](.agentic-beacon/artifacts/knowledge/facts/cli-development-workflow.md)

### Domain Layer

The `beacon` package uses a four-layer architecture: `cli/` → `domains/` → `core/`, `utils/`.

**Five domains** (each in `libs/beacon/src/beacon/domains/<name>/`):
- `warehouse` — warehouse connect / validate / catalog; git health; `abc warehouse status` / `abc warehouse contribute`
- `setup` — `abc warehouse init` / `abc setup` flows; CLAUDE.md / opencode wiring
- `adoption` — `abc adopt` flow
- `distribution` — warehouse→project symlink sync, migration from copy-based trees, upgrades
- `artifact` — agent / skill / rule artifact operations

**Dependency rule:** `cli → domains → core, utils`. Cross-domain imports are allowed; `core/` and `utils/` must never import from `domains/` or `cli/`.

**CLI layer rule:** Each handler in `beacon/cli/` must contain only: argument parsing + one domain call + output formatting. No free helper functions; no I/O calls directly in handlers. Enforced by `libs/beacon/tests/unit/test_architecture.py`.

**Read:** [Layered Architecture Spec](openspec/specs/layered-architecture/spec.md)

### Unit Testing Workflow

**Brief:** Standard workflow: `uv sync --group dev` at repo root → `pytest` (no cd into libs/beacon required)

**Read:** [Fact: Unit Testing Workflow](.agentic-beacon/artifacts/knowledge/facts/unit-testing-workflow.md)

**Rule:** ALL tests must be resolved before marking tasks complete - either fixed, removed with justification, or skipped with documented reason.

**Read:** [Lesson: Complete Test Resolution Before Marking Tasks Done](.agentic-beacon/artifacts/knowledge/lessons/complete-test-resolution.md)

**Rule:** After unit tests pass, verify happy path functionality with real-world usage to ensure the feature actually works.

**Read:** [Lesson: Verify Both Unit Tests and Happy Path Functionality](.agentic-beacon/artifacts/knowledge/lessons/verify-unit-tests-and-happy-path.md)

### Release Process

**Workflow:** Conventional commits → Release-Please PR → Merge → Create release branch → Auto-publish to PyPI

**Steps:**
1. Merge the Release-Please PR on GitHub (it bumps the version and creates the tag)
2. Create the release branch from the tag to trigger PyPI publish:
   ```bash
   git fetch origin
   git push origin refs/tags/agentic-beacon@vX.X.X:refs/heads/release/vX.X.X
   ```
3. Verify on PyPI once the publish workflow completes:
   ```bash
   curl -s https://pypi.org/pypi/agentic-beacon/json | python3 -c \
     "import sys,json; d=json.load(sys.stdin); print(d['info']['version'])"
   ```

**Note:** Release branches are permanent snapshots — never delete them.

**Read:** [Release Workflow](.agentic-beacon/artifacts/knowledge/facts/release-workflow.md)

---

## Project Standards

### Python Standards

Follow the global Python standards from the user's AGENTS.md context:
- Type annotations without quotes (unless forward references)
- Use primitive types (list, dict) over typing module types
- Pydantic BaseModel for data carriers
- Dataclass for service classes only
- Conventional commits for all changes

**Rule:** Always use **absolute imports** from `beacon` — never relative imports (`from ..utils import X` is wrong; `from beacon.utils.module import X` is correct).

**Rule:** `__init__.py` files must **not** re-export names or define `__all__`. They are empty package markers (docstring only). Import directly from the module that defines the name: `from beacon.core.manifest.beacon import BeaconManifest`, not `from beacon.core.manifest import BeaconManifest`.

**Read:** [Decision: Follow Global Python Standards](.agentic-beacon/artifacts/knowledge/decisions/follow-global-python-standards.md)

### Documentation Standards

- Keep docs current with code changes
- Use examples from `abc init` output
- Link to proper documentation, don't duplicate
- Update both README and package-specific docs when needed
- Warehouse context files use **free descriptive names** — not the `AGENTS.*` prefix

**Read:** [Lesson: Warehouse Context Files Use Free Naming](.agentic-beacon/artifacts/knowledge/lessons/warehouse-context-free-naming.md)

---

## Common Patterns

### Adding a New CLI Command

**Brief:** Add handler in `cli/<group>.py` → Implement domain logic in `domains/<name>/` → Add tests → Update docs → Test thoroughly

**Read:** [Lesson: Adding CLI Command](.agentic-beacon/artifacts/knowledge/lessons/adding-cli-command.md)

### Updating Warehouse Structure

**Brief:** Update `domains/setup/initializer.py` → Regenerate `examples/sample-warehouse/` → Update docs → Test `abc warehouse init` and `abc setup`

**Read:** [Lesson: Updating Warehouse Structure](.agentic-beacon/artifacts/knowledge/lessons/updating-warehouse-structure.md)

---

## Project Skills

### Recording Knowledge

**Brief:** Use `/record-knowledge` to capture decisions, lessons, and facts into the knowledge base.

**How it works:**
1. Analyzes your description to determine type (decision/lesson/fact)
2. Creates properly formatted knowledge file
3. Asks where to add pointer (defaults to AGENTS.md)
4. Updates context file with reference

**Example:** `/record-knowledge We use Release-Please for automated versioning based on conventional commits`

**Read:** [Skill: Record Knowledge](libs/beacon/src/beacon/data/skills/record-knowledge/SKILL.md)

---

## Critical Safeguards

- **Never commit secrets** - PyPI tokens, API keys stay in GitHub Secrets
- **Keep examples updated** - `examples/sample-warehouse/` must match `abc warehouse init` output (and the public starter warehouse)
- **Test before release** - Always test CLI commands locally before pushing
- **Document breaking changes** - Use `feat!:` or `fix!:` commits for breaking changes

**Read:** [Lesson: Critical Project Safeguards](.agentic-beacon/artifacts/knowledge/lessons/critical-safeguards.md)

---

**Last Updated:** 2026-05-03
