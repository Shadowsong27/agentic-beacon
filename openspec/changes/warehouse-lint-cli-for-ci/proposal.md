## Why

The `hl-knowledge-market` warehouse is the single write entrypoint for every harness artifact on a machine, but it has no CI. A merge to its `main` that violates the artifact contract — missing skill frontmatter, an agent referencing a deleted context, an unparseable `requires:` block — only surfaces hours later when a downstream project runs `abc sync` and the dependency resolver throws. The recent `delegate-to-cc/SKILL.md` regression (merged without any YAML frontmatter, broke `abc sync` in `agentic-beacon`) is the concrete motivating bug.

Beacon already owns the validation primitives that catch every such defect. They are project-scoped today (called from inside `compute_effective_set` during sync) but the underlying validators are path-agnostic. We need a thin warehouse-wide entrypoint that composes them, so the warehouse repo's own CI can run the same checks Beacon enforces at sync time — without inventing a parallel ruleset that can drift.

## What Changes

- Add `abc warehouse lint [PATH]` CLI command that validates an arbitrary warehouse directory end-to-end. PATH defaults to cwd; matches `abc warehouse template-upgrade` precedent.
- Add a new lint module under `domains/warehouse/` that composes existing path-agnostic primitives (`WarehouseValidator.validate`, `load_agent_manifest` + friends, `parse_frontmatter` + `SkillFrontmatter`, plus a new broken-knowledge-link collector). No refactor of existing code; ~110 LOC of new module + ~30 LOC of CLI handler.
- **NEW lint rule**: every `agents/*.md` (excluding `README.md`) must have a YAML frontmatter block containing both a `name` key and a `description` key. This rule exists nowhere in Beacon today.
- **Strictness promotion (lint-only)**: broken knowledge links (`[..](../knowledge/X.md)` that resolve to a missing file) are reported as errors by lint. The shared `scan_file_for_knowledge` primitive keeps its current warning-only behaviour — `abc sync` is unaffected.
- Output: Rich console grouped by artifact path, `error:` prefixed findings, exit 0 on clean / 1 on any error. No `--json` flag in v1.
- Cross-repo rollout (documented in `design.md`, executed separately): a PR in `hl-knowledge-market` will (a) migrate every agent `.md` to add `name:` frontmatter, (b) fix the two known broken knowledge links, (c) add `.github/workflows/lint.yml` running on `ubuntu-latest` via `setup-uv` + `uvx agentic-beacon==<pinned> warehouse lint .`.

This change is purely additive: no existing CLI, capability, or primitive changes behaviour for any existing caller.

## Capabilities

### New Capabilities

- `warehouse-lint-command`: Defines the `abc warehouse lint [PATH]` CLI surface, its validation scope (structure, agent manifest, agent frontmatter, skill frontmatter, skill→context references, knowledge link integrity), output format, and exit-code semantics.

### Modified Capabilities

None. The new lint command reuses existing primitives without changing their contracts. `knowledge-reference-scanning` is *not* modified — `scan_file_for_knowledge` keeps its current warning-only posture; lint's stricter take lives in the new lint module, not the scanner.

## Impact

**Code (agentic-beacon repo):**
- New: `libs/beacon/src/beacon/domains/warehouse/lint.py` (lint orchestrator)
- New: `libs/beacon/src/beacon/cli/warehouse.py` adds a `warehouse_lint` Click handler
- New: unit tests under `libs/beacon/tests/unit/domains/warehouse/test_lint.py` covering each rule in isolation
- New: one integration test under `libs/beacon/tests/integration/domains/warehouse/test_lint_cli.py` that runs the CLI via subprocess against a multi-defect fixture warehouse

**Docs (agentic-beacon repo):**
- Add lint command to the warehouse CLI reference in `site-docs/`
- Brief mention in `libs/beacon/README.md` warehouse command list

**Release:**
- New minor version of `agentic-beacon` via release-please; warehouse CI will pin to this version

**Cross-repo follow-up (hl-knowledge-market, not modelled in this change's specs/tasks):**
- Agent `.md` file migration (add `name:` frontmatter to every agent)
- Fix 2+ known broken knowledge links
- New `.github/workflows/lint.yml`
- Documented in `design.md` under Impacted Repositories; tracked as PR_B in the rollout plan

**Out of scope for this change:**
- Branch protection on `hl-knowledge-market` main (account-plan limitation — branch protection on private personal repos is not available)
- Orphan detection (skills/contexts/knowledge that nothing references)
- `model:` requirement on agent frontmatter (ticket-text aspiration; undefined "where applicable" semantics)
- Strict frontmatter on skills (skills retain their current `requires.contexts`-only rule)
- `--json` / SARIF output (defer until a consumer needs it)
