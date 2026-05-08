# Agentic Beacon Project Context

Project-level instructions for AI agents working on the Agentic Beacon framework.

---

## Project Overview

**Agentic Beacon** is an opinionated framework for standardizing and distributing agentic engineering artifacts across teams.

**Repository layout:**

```
agentic-beacon/
├── libs/beacon/          # CLI source (uv workspace member)
│   └── src/beacon/
│       ├── cli/          # Thin Click handlers (parse + one domain call + format)
│       ├── domains/      # Five domain modules (see Domain Layer below)
│       ├── core/         # Cross-domain primitives: exceptions, manifest models, settings, file_filter
│       ├── utils/        # Stateless helpers: git, display, interaction, platform
│       └── data/skills/  # Bundled skills — SSOT for every skill distributed by abc init
├── examples/sample-warehouse/  # Must always match abc init output exactly
├── docs/                 # Design documentation
├── site-docs/            # MkDocs source
├── openspec/             # OpenSpec change artifacts (changes/, specs/)
└── AGENTS.md             # ← you are here
```

**This is NOT a warehouse.** Users create warehouses with `abc warehouse init`.

---

## Development Setup

**Location:** `libs/beacon/`
**uv workspace** — single `.venv` at repo root; `libs/beacon` is a workspace member.

```bash
uv sync --group dev        # one-time / after dependency changes
pytest                     # run from repo root (testpaths configured in root pyproject.toml)
.venv/bin/abc --version    # verify CLI
```

Never `cd libs/beacon` to run tests. Never create a venv inside `libs/beacon/`.

---

## Architecture

### Four-Layer Architecture

```
cli/ → domains/ → core/, utils/
```

- `cli/` — argument parsing + one domain call + output formatting. No logic, no I/O.
- `domains/` — all application logic, one module per bounded context
- `core/` — cross-cutting primitives consumed by **multiple** domains: exceptions, manifest models, settings, `file_filter`
- `utils/` — stateless helpers with no domain knowledge: git, display, interaction, platform

**Dependency rule:** `core/` and `utils/` must **never** import from `domains/` or `cli/`.

**CLI layer rule:** enforced by `libs/beacon/tests/unit/test_architecture.py`.

**Domain placement rule:** New logic belongs in the domain that owns the concept — not `core/` or `utils/` by default. If a module is only consumed by one domain, it belongs inside that domain. `core/` is for things multiple domains share.

### Five Domains

Each in `libs/beacon/src/beacon/domains/<name>/`:

| Domain | Responsibility |
|---|---|
| `warehouse` | connect / validate / catalog; git health; `abc warehouse status / contribute` |
| `setup` | `abc warehouse init` / `abc setup`; CLAUDE.md / opencode wiring |
| `adoption` | `abc adopt` flow: three-way (accept/reject/defer) TUI, confirm screen, atomic commit with rollback, `pending.yaml` + `.last-adopt` management |
| `distribution` | warehouse→project symlink sync, migration, upgrades |
| `artifact` | agent / skill / rule artifact operations |

**Read:** [Layered Architecture Spec](openspec/specs/layered-architecture/spec.md)

---

## Artifact Distribution Model

The locally-cloned warehouse is the **single write entrypoint** for every harness artifact on a machine. Projects reference it via per-file symlinks under `.agentic-beacon/artifacts/`.

- `abc sync` creates symlinks, not copies. One logical artifact = one physical file per machine.
- `abc warehouse contribute` is the primary way to push warehouse working-tree changes back upstream.
- Authoring skills (`record-knowledge`, `record-skill`) write directly to the warehouse. Project-wired artifacts (contexts, skills, agents) are appended to `.agentic-beacon/pending.yaml`; wiring into `beacon.yaml` happens later via `abc adopt`. Knowledge files are auto-derived during sync/adopt and are not tracked in `pending.yaml`.
- Cross-project visibility of harness edits on a single machine is **intended**: editing a skill through Project A's symlink edits the warehouse working tree; Project B sees the change immediately.
- Platform: macOS / Linux only. Windows is rejected.
- Agents are declared per-project in `beacon.yaml.artifacts.agents` **AND** installed globally via symlinks into `~/.config/opencode/agents/` and `~/.claude/agents/`.

### Pending Artifacts

`.agentic-beacon/pending.yaml` tracks warehouse artifacts authored in the current project but not yet wired into `beacon.yaml`. It is gitignored. Use `abc adopt` to review and accept/reject/defer pending entries.

**`abc adopt` three-way actions:**

| Action | Effect |
|---|---|
| **accept** | Add to `beacon.yaml`, sync symlinks, remove from `pending.yaml` |
| **reject** | Remove from `pending.yaml` only; warehouse file untouched |
| **defer** (default) | Keep in `pending.yaml`; no `beacon.yaml` change |

After marking entries, a confirm screen shows the projected mutations before any filesystem writes. All writes are atomic — a mid-commit failure restores `beacon.yaml`, `pending.yaml`, and `.last-adopt` to their pre-commit state.

**Pending alert:** Every `abc` subcommand prints a one-line stderr notice when `pending.yaml` is non-empty. This does not affect the subcommand's exit code.

---

## Python Standards

Beacon-specific additions on top of global Python standards:

**Absolute imports only** — never relative:
```python
# correct
from beacon.core.manifest.beacon import BeaconManifest
# wrong
from ..core.manifest import BeaconManifest
```

**`__init__.py` files are empty package markers** — no re-exports, no `__all__`. Import directly from the defining module:
```python
# correct
from beacon.core.manifest.beacon import BeaconManifest
# wrong
from beacon.core.manifest import BeaconManifest
```

---

## Documentation Standards

- Keep docs current with code changes
- `examples/sample-warehouse/` must always match `abc warehouse init` output exactly — regenerate after any change to `domains/setup/initializer.py`
- Warehouse context files use **free descriptive names** — not the `AGENTS.*` prefix (that convention applies only at project/user root level)

---

## Common Patterns

### Adding a New CLI Command

1. Add thin handler in `cli/<group>.py` — argument parsing + one domain call + output formatting
2. Implement logic in `domains/<name>/`
3. Add unit tests; add to architecture test if new handler file
4. Update docs (README, site-docs if user-facing)
5. Test: `abc <command> --help` and happy path

### Updating Warehouse Structure

1. Edit `domains/setup/initializer.py`
2. Delete and regenerate `examples/sample-warehouse/`
3. Update any docs that show the structure diagram
4. Test `abc warehouse init` and `abc setup` end-to-end

---

## Release Process

Tag prefix for this package: `agentic-beacon@vX.X.X`.

```bash
git fetch origin
git push origin refs/tags/agentic-beacon@vX.X.X:refs/heads/release/vX.X.X
```

---

## CI Bot Configuration

**Switch the OpenCode PR review model** without editing the workflow:

```bash
gh variable set OPENCODE_REVIEW_MODEL -R Shadowsong27/agentic-beacon --body "<model>"
gh variable delete OPENCODE_REVIEW_MODEL -R Shadowsong27/agentic-beacon  # revert to workflow default
```

The workflow at `.github/workflows/opencode-review.yml` reads `vars.OPENCODE_REVIEW_MODEL` and falls back to `openai/gpt-5.5`.

---

## Critical Safeguards

- **Keep examples updated** — `examples/sample-warehouse/` must match `abc warehouse init` output
- **Test before pushing** — `abc --version`, `abc warehouse init test-warehouse`, `pytest`

---

**Last Updated:** 2026-05-08
