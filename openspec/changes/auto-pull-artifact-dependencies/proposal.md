## Why

Knowledge artifacts are adopted in `beacon.yaml` independently of the contexts and skills that actually reference them. The result is silent drift: this very repo ships `.agentic-beacon/artifacts/contexts/python-standards.md` with 12+ markdown links into `../knowledge/python-standards/...`, but `beacon.yaml.knowledge` is empty — every link is a dangling symlink target. Nobody uses knowledge in isolation, so making it a first-class adoptable artifact with its own lifecycle creates orphans, drift, and tedious manual sync.

This change makes cross-artifact dependencies explicit and machine-resolved: knowledge is transitively pulled from the markdown links inside adopted contexts and skills; skills declare their context dependencies via YAML frontmatter. `beacon.yaml` stops tracking knowledge at all.

## What Changes

- **BREAKING**: Remove the `artifacts.knowledge` field from `beacon.yaml`. On first `abc sync` after upgrade, the field is silently dropped and regenerated output omits it.
- **BREAKING**: Skill files (`skills/<name>/SKILL.md`) must declare `requires: { contexts: [...] }` in YAML frontmatter. Skills cannot declare skill-to-skill dependencies in this version.
- Knowledge is derived at sync time by scanning adopted contexts and skills for markdown links that resolve to paths under `<warehouse-root>/knowledge/`. Derived knowledge is symlinked into `.agentic-beacon/artifacts/knowledge/`. Orphaned knowledge symlinks (no remaining referrer) are pruned.
- `abc adopt` removes knowledge as a selectable category. Contexts and skills remain as the two selectable project artifact types. `abc adopt` may show agents as global-install candidates; selecting an agent installs it globally immediately and does not update project `beacon.yaml`. PER-109 adds persistent selected-global-agent state and `abc sync` installing those selected global agents.
- `abc sync` validates that every adopted skill's `requires.contexts` resolves to a context that exists in the warehouse. Required contexts that exist in the warehouse are auto-pulled transitively; a required context missing from the warehouse is a hard error.
- Context files are not scanned for frontmatter dependencies; contexts have no sibling-tier `requires`. Context-to-context dependencies are not supported.
- Context transitive provenance is derived from skill-required contexts: a context pulled only because an adopted skill requires it is pruned when the skill is unadopted.
- Agent files are not part of the project `beacon.yaml` or sync flow. Agent `requires:` frontmatter is warehouse metadata for future groundwork (PER-109), not read during `abc sync`.
- A migration document (`docs/migrations/artifact-dependencies-frontmatter.md`, already drafted) is added to this repo and linked from the hard-error messages. No legacy mode.
- `abc doctor` is **not** part of this change — tracked as a follow-up.

## Capabilities

### New Capabilities

- `artifact-dependency-resolution`: Frontmatter schema (`requires: { contexts }`) for skills, and the dependency graph semantics that use it. Defines validation rules, error messages, and the migration doc contract.
- `knowledge-reference-scanning`: The scanner that reads warehouse-source context and skill files, resolves relative markdown links, classifies knowledge-shaped links, and emits the derived knowledge set for sync.

### Modified Capabilities

- `config-based-artifact-management`: Removes the `artifacts.knowledge` field from the `beacon.yaml` schema. Adds the migration behaviour that silently drops the field on first sync.
- `artifact-adoption`: Removes knowledge from the adopt TUI picker. Adds transitive/orphan provenance tracking for contexts (explicit adoption survives referrer unadoption; skill-pulled-only contexts are pruned).
- `snapshot-based-sync`: Adds the dependency-resolution and reference-scanning steps to the sync pipeline. Adds the hard-error surface for unadopted skill `requires.contexts` targets. Adds knowledge symlink pruning based on referrer set.

## Impact

**Affected code:**
- `libs/beacon/src/beacon/core/manifest/beacon.py` — remove `knowledge` field from `ArtifactsConfig`; add migration hook.
- `libs/beacon/src/beacon/domains/adoption/` — drop knowledge from discovery/TUI; add transitive/orphan provenance tracking for contexts.
- `libs/beacon/src/beacon/domains/distribution/` — new scanner module; orchestrator changes for derived knowledge and frontmatter validation.
- New module `libs/beacon/src/beacon/core/dependencies/` (or similar) for the dependency-graph and frontmatter-parsing primitives.
- `examples/sample-warehouse/` — add `requires:` frontmatter to every skill so the example matches the new contract.

**Affected users:**
- Personal warehouse at `~/Code/knowledge/hl-knowledge-market/` needs a one-shot manual frontmatter pass before this change lands (prompt drafted).
- Any external warehouse maintainer must follow `docs/migrations/artifact-dependencies-frontmatter.md` before their consumers upgrade.
- Existing `beacon.yaml` files with a populated `knowledge` list will see it silently dropped on first post-upgrade sync.

**Non-goals:**
- `abc doctor` validation command (separate change).
- Context-to-context dependencies (explicitly rejected).
- Legacy / transition mode for warehouses without frontmatter (explicitly rejected).
- Skill-to-skill dependencies (explicitly deferred; revisit case-by-case on user request).
- Persistent selected-global-agent state and `abc sync` consuming agent `requires` — deferred to PER-109. Agent global install via `abc install agents/<name>.md` and `abc adopt` already exists.
