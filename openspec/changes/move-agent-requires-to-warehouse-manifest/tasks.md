## 1. Scaffolding & schema

- [x] 1.1 Add `AgentManifest` pydantic model in `libs/beacon/src/beacon/core/dependencies/manifest.py` — top-level `dict[str, AgentEntry]`, where `AgentEntry` has `skills: list[str]` (required, default empty) and permits extra keys (forward compatibility). Reject `contexts:` explicitly with a validator.
- [x] 1.2 Add `load_agent_manifest(warehouse_path: Path) -> AgentManifest | None` — returns `None` if `agents/agents.yaml` absent; raises `AgentManifestError` with migration URL on parse/schema failure.
- [x] 1.3 Add `validate_agents_directory(warehouse_path: Path, manifest: AgentManifest | None) -> None` — checks bidirectional correspondence between `agents/*.md` files (excluding `README.md`) and manifest top-level keys; raises on missing or orphan entries.
- [x] 1.4 Add `validate_agent_frontmatter_clean(warehouse_path: Path) -> None` — scans each `agents/*.md`, asserts no `requires:` key in frontmatter; raises with migration URL.
- [x] 1.5 Add `validate_declared_skills(warehouse_path: Path, manifest: AgentManifest) -> None` — for every agent's `skills:` list, asserts `skills/<name>/SKILL.md` exists.
- [x] 1.6 Unit tests for 1.1–1.5 under `libs/beacon/tests/unit/core/dependencies/test_agent_manifest.py`, covering happy path, each failure mode, and every scenario enumerated in `specs/agent-requires-manifest/spec.md`.

## 2. Wire validation into warehouse-read operations

- [x] 2.1 Extend `libs/beacon/src/beacon/domains/warehouse/validator.py` to call the four validators from Section 1 when `agents/` is non-empty. Respect the "empty agents directory is permitted" rule.
- [x] 2.2 Ensure `abc warehouse status` surfaces the new errors with clear file paths and the migration-doc URL.
- [x] 2.3 Extend `abc sync` entry to run the same validation before any sync work begins; fail fast with exit nonzero on validation error.
- [x] 2.4 Confirm `abc install agents/<name>.md` and `sync_agents_from_warehouse` are NOT modified by this change.
- [x] 2.5 Unit tests: `abc warehouse status` and `abc sync` fail on malformed warehouse; both succeed on well-formed warehouse. Integration test at `libs/beacon/tests/integration/` using a temp warehouse fixture.

## 3. Warehouse scaffolding & templates

- [x] 3.1 Update `libs/beacon/src/beacon/data/templates/agents/README.md` — remove any mention of `requires:` in frontmatter; add a section documenting `agents/agents.yaml` with a small worked example; state explicitly that `requires:` must not appear in agent frontmatter.
- [x] 3.2 Update `libs/beacon/src/beacon/domains/setup/initializer.py` to write `agents/agents.yaml` during `abc warehouse init`. File content: an empty mapping with commented-out examples teaching the schema shape. Template:
  ```yaml
  # Beacon agent dependency manifest.
  # Each top-level key maps an agent (agents/<key>.md) to its required skills.
  #
  # Example:
  # spec-planner:
  #   skills:
  #     - opsx-enhance-tasks
  #     - openspec-propose
  #
  # pipeline-developer:
  #   skills: []
  ```
  Empty file is still valid (parses to empty mapping); validation passes when `agents/` is also empty.
- [x] 3.3 Regenerate `examples/sample-warehouse/` — remove any `requires:` frontmatter from `examples/sample-warehouse/agents/*.md`; add `examples/sample-warehouse/agents/agents.yaml`. Ensure `abc warehouse status` passes against the sample.
- [x] 3.4 Unit/integration test: `abc warehouse init` in a temp dir produces a warehouse that passes `abc warehouse status` with no additional edits.

## 4. Migration tooling & docs

- [x] 4.1 Write one-shot migration script at `scripts/migrate-agent-requires.py` — reads every `agents/*.md` in the warehouse provided as argument; extracts each file's `requires:` frontmatter; writes `agents/agents.yaml` (skills only; drops contexts); strips `requires:` from each file's frontmatter. Idempotent; errors with clear message if `agents.yaml` already exists and differs. Prints a summary of dropped `contexts:` entries per agent with a note "moved to agents.yaml — nothing" or "dropped — contexts are project-level."
- [x] 4.2 Unit-test the script: fixture warehouse with 3 agents (one with skills+contexts, one with skills only, one with no requires), run script, assert post-state matches expected `agents.yaml` and stripped frontmatter.
- [x] 4.3 Update `docs/migrations/artifact-dependencies-frontmatter.md` — new section: "Agent requires move (frontmatter → agents.yaml)". Explain the bug (provider-level unknown-key rejection), the fix shape, the `contexts:` drop rationale, and the migration script invocation. Link from every error message emitted by Beacon's new validators.
- [x] 4.4 Verify every new error message raised by validators in Section 1 contains the string `docs/migrations/artifact-dependencies-frontmatter.md` — add a unit test asserting this.

## 5. Personal warehouse migration (manual, outside this repo)

- [x] 5.1 In `~/Code/knowledge/hl-knowledge-market/`, create branch `agent-requires-manifest-migration`.
- [x] 5.2 Run migration script from Section 4 against the warehouse.
- [x] 5.3 Review `git diff` — sanity-check generated `agents/agents.yaml`; confirm stripped frontmatter is clean; confirm dropped `contexts:` entries are genuinely project-level and don't lose meaningful metadata.
- [x] 5.4 Locally install the Beacon feature branch via uv workspace; run `abc warehouse status` against the migrated warehouse; confirm validation passes.
- [x] 5.5 Commit and push the warehouse migration branch. (Warehouse merge to main happens independently after Beacon release.)

## 6. Documentation & release

- [x] 6.1 Update `AGENTS.md` in this repo if it references agent `requires:` behaviour (search & replace to point at `agents.yaml`).
- [x] 6.2 Update any site-docs pages under `site-docs/` describing warehouse agent files.
- [x] 6.3 Add an entry to release notes describing the breaking change: warehouses must migrate before Beacon upgrade.
- [x] 6.4 Run full test suite (`pytest` from repo root) — all passing.
- [x] 6.5 Manual smoke: `abc warehouse init test-warehouse` → confirm scaffolded `agents.yaml`; `abc warehouse status` in sample-warehouse → passes; `abc sync` against migrated personal warehouse → passes with no `requires:`-related errors.
