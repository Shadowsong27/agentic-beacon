## Why

Markdown links inside warehouse artifacts (the `[text](path)` references in skill/context/agent/knowledge bodies) are written as filesystem-relative paths that only resolve on the original author's machine. The moment an artifact is distributed via symlink into a downstream project — where the `.agentic-beacon/artifacts/` tree sits at a different depth, and where agents land *outside* that tree entirely (`.claude/agents/`, `.opencode/agents/`) — those links silently break for every consumer except the author. This defeats the whole portability premise of the distribution model. We need one canonical link form, a lint that enforces it, a migration that converts existing artifacts, and an end-to-end test that proves links resolve after a real `abc sync`.

## What Changes

- **Canonical link form**: every intra-warehouse cross-artifact markdown link must be written as a project-root-relative path `.agentic-beacon/artifacts/<warehouse-relative-path>` — never relative to the linking file's directory. This is the one form that an LLM agent (the primary runtime consumer) can `Read()` directly from a downstream project root, and that is uniform across every artifact type including agents that distribute outside the mirror. **Tradeoff accepted**: this form does not resolve in a raw GitHub view of the warehouse repo; resolution always goes through a Beacon-aware consumer.
- **Lint link-integrity rules** (extends `abc warehouse lint`): classify every markdown link and
  - **error** on a cross-artifact link written in directory-relative form (must be canonical),
  - **error** on a canonical link whose target file does not exist in the warehouse,
  - **error** on an anchor that does not resolve to a heading in the target file (GitHub-exact slugify),
  - **error** on a relative link that escapes the warehouse root (unportable),
  - **allow** a relative link that stays inside a skill's own directory (bundled assets travel together).
- **`abc warehouse lint --fix`**: auto-rewrite the fixable category (cross-artifact relative → canonical, anchors preserved) in place; leave external-escape errors for a human. The one-time migration of existing artifacts is this command run once.
- **Contribute gate**: the `contribute-warehouse` bundled skill runs `abc warehouse lint` and blocks on error-level findings before committing.
- **Agent partials restructure (absorbs PER-238)**: move warehouse `agents/_partials/` → top-level `agent-partials/`; keep distributing partials into the `.agentic-beacon/artifacts/agent-partials/` mirror (retarget the dependency glob); **stop** co-distributing partials into `.claude/agents/` & `.opencode/agents/`; **remove** the PER-238 `disable: true` stopgap wrapper; rewrite the two supervisor agents' partial links to canonical form. This closes **PER-238**. **BREAKING** (warehouse layout): `agents/_partials/` no longer exists.
- **Integration test suite**: a hermetic synthetic-fixture warehouse + downstream project, real symlinks, real `abc sync`, then walk every distributed artifact and assert each canonical link resolves from the project root (with anchors), plus a negative fixture proving a broken link is caught. Runs in CI.
- **Docs**: `CONTRIBUTING.md` + the authoring guide document the canonical-link convention and the `lint` / `--fix` workflow.

CI itself needs **no change in this repo** — the warehouse repo's existing `lint.yml` (`uv tool install agentic-beacon` → `abc warehouse lint .`) picks up the new rules after release.

## Capabilities

### New Capabilities
- `canonical-artifact-links`: the canonical project-root link convention, the strip-prefix resolution rule, the four-way link classifier (canonical / cross-artifact-relative / own-skill-folder / external), and GitHub-exact anchor slugification. The contract for what a valid intra-warehouse link is.

### Modified Capabilities
- `warehouse-lint-command`: broadens the existing "knowledge link integrity" rule into full artifact-link integrity (malformed-form, missing-target, unresolved-anchor, warehouse-escape) and adds the `--fix` auto-rewrite mode.
- `project-agent-wiring`: agent partials distribute only into the `.agentic-beacon/artifacts/agent-partials/` mirror (retargeted from `agents/_partials/`), are **not** wired into the `.claude/` / `.opencode/` tool directories, and the `disable: true` partial-wrapper stopgap is removed.

## Impact

- **Code**: `domains/warehouse/lint.py` (new link rules + report), `core/scanner/scanner.py` (canonical resolution + classifier + slugifier), `cli/warehouse.py` (`--fix` flag), `domains/distribution/orchestrator.py` + `distributor.py` + `delta.py` (partial glob retarget), `domains/setup/wiring.py` (remove co-distribution + stopgap).
- **Warehouse repo (`hl-knowledge-market`)**: one-time `lint --fix` migration of existing artifacts; warehouse file move `agents/_partials/` → `agent-partials/`; the existing `lint.yml` gate begins enforcing after the next `agentic-beacon` release.
- **Tickets**: closes PER-238 (partials no longer exposed as opencode subagents).
- **Bundled skill**: `data/skills/contribute-warehouse` gains a pre-commit lint gate.
- **Tests**: new unit tests (slugifier table, classifier) + new integration test (synthetic warehouse, real sync, link-resolution walk + negative fixture).
- **Release**: requires a new `agentic-beacon` release so the warehouse CI enforces the rules.
