## Context

Today Agentic Beacon tracks three categories of adoptable artifact in `beacon.yaml`: `contexts`, `skills`, `knowledge`. Adoption for each is independent. At sync time, the orchestrator reads each list, expands globs and node-paths, and creates per-file symlinks into `.agentic-beacon/artifacts/`.

This separation breaks the moment a context links to a knowledge file. The link is plain markdown; no code reads it, validates it, or pulls the target. The concrete failure mode lives in this repository right now: `.agentic-beacon/artifacts/contexts/python-standards.md` contains 12+ links into `../knowledge/python-standards/...`, but `beacon.yaml.artifacts.knowledge` is `[]`. The links dangle against nothing.

Agents are global machine-level artifacts, not project-scoped symlinks, and are not tracked in project `beacon.yaml`. Agent dependency resolution is deferred to PER-109. This change focuses on the container tiers: contexts, skills, and auto-derived knowledge.

Stakeholders: warehouse maintainers (Shadowsong27 and any future warehouse owners), project users who consume a warehouse, and the Beacon CLI itself which must enforce consistency.

Current state on disk:
- `libs/beacon/src/beacon/core/manifest/beacon.py` — `ArtifactsConfig` has three list fields.
- `libs/beacon/src/beacon/domains/adoption/` — discovery, TUI, apply; all three types treated symmetrically.
- `libs/beacon/src/beacon/domains/distribution/orchestrator.py:173-205` — sync expansion of all three lists.
- Personal warehouse: `~/Code/knowledge/hl-knowledge-market/` with 8 agents and ~20 skills; no frontmatter dependency metadata yet.

## Goals / Non-Goals

**Goals:**
- Make cross-artifact dependencies explicit and machine-resolvable.
- Eliminate silent drift between declared adoption and actually-referenced artifacts.
- Remove the tedium of manually adopting knowledge.
- Preserve clean layered semantics: skills → contexts → knowledge, no horizontal edges.
- Loud errors with remediation pointers for any warehouse or project not in the new model.
- Preserve user agency: users still pick contexts and skills explicitly.

**Non-Goals:**
- `abc doctor` validation command — separate follow-up change.
- Context-to-context dependencies — explicitly rejected; keeps the graph acyclic by design.
- Skill-to-skill dependencies — explicitly deferred; no mechanism in this version.
- Legacy / transitional mode for warehouses without frontmatter — explicitly rejected; legacy mode reintroduces exactly the drift this change exists to eliminate.
- Automatic inference of frontmatter dependencies from prose — not attempted; migration is manual, guided by the migration document.
- Changing the symlink sync mechanism, warehouse connect flow, or `abc contribute` — out of scope.

## Decisions

### D1. Two-tier dependency graph within project scope, with two expression mechanisms

The graph within project scope has two tiers and two kinds of edges:

```
Skills  --(frontmatter.requires)-->  Contexts
Contexts, Skills  --(markdown links)-->  Knowledge
```

Frontmatter `requires:` expresses sibling-tier (skill→context) dependencies. Markdown links express leaf-tier (knowledge) dependencies. Context files do not declare `requires:` frontmatter. Skill files declare `requires.contexts` only (no `skills` key).

Agents are global machine-level artifacts deferred to PER-109. Their `requires:` frontmatter is warehouse metadata for future groundwork, not read by `abc sync` in this change.

**Why this shape:**
- Knowledge is naturally inline-cited in context/skill prose ("See [X]"). Markdown links match how authors already write.
- Skill→context is the natural composition edge: a skill depends on standards/context that it references.
- Two expression mechanisms maps cleanly to two dependency directions (horizontal sibling vs. downward leaf).

**Alternative considered — one uniform mechanism (all deps in frontmatter):**
Simpler parser, but forces authors to duplicate every knowledge reference into both a markdown link and a frontmatter entry. Authors would drift.

**Alternative considered — URI scheme like `beacon://knowledge/foo/bar`:**
Location-independent like frontmatter, but introduces a new syntax with a new parser for every markdown renderer. Too much infrastructure for a per-project change.

### D2. `beacon.yaml.artifacts.knowledge` is deleted, not deprecated

The field is removed from the Pydantic model entirely. On first sync after upgrade, if an existing `beacon.yaml` contains the field, the CLI drops it silently (with a one-shot info log) and rewrites the file.

**Why silent drop:**
- User accepted destructive migration during grilling.
- The only information a populated `knowledge` field carried was "what knowledge the user thinks they want." That intent is now expressed via which contexts and skills they adopt. Silent drop is not data loss; it is removal of a field that was always a symptom of the problem.
- Keeping a deprecation warning across releases extends the implementation surface for a feature used by perhaps three users today.

**Alternative considered — keep as optional pin list:**
A "pinned knowledge" escape hatch. Rejected because the scanning mechanism means there is no legitimate reason to pin: if you want a knowledge file, adopt the context that references it, or create one. A pin list would recreate drift on a smaller scale.

### D3. Scanner reads warehouse source files, not project symlinks

The scanner resolves the warehouse clone path via `WarehouseSettings`, opens files directly from the warehouse tree, and uses the file's own directory for relative link resolution.

**Why warehouse-source:**
- Scanning must complete before symlinks are created (otherwise sync has no plan). Project symlinks don't exist yet on first sync.
- Scanning warehouse source is order-independent: the plan is a pure function of `(beacon.yaml, warehouse-HEAD)`.
- The bytes are identical either way — symlinks point at the warehouse — so there is no behavioural difference, only ordering.

### D4. Link classification rule

A markdown link counts as a knowledge reference if and only if:
1. The link is a relative reference (not absolute URL, not mailto, not fragment-only).
2. Resolving it against the scanned file's directory yields a path inside the warehouse root.
3. That resolved path, expressed relative to the warehouse root, starts with `knowledge/`.
4. The resolved path ends in `.md`.

Path resolution: `(scanned_file.parent / link_target).resolve()`, using pathlib with `strict=False` so that links to files not yet created still resolve structurally. Missing-file detection runs as a separate step with a warning, not a classifier gate.

Links that fail the classifier — including links to files outside the warehouse, links to other contexts, links to images, links to READMEs — are silently ignored. They are not errors; contexts legitimately link to all kinds of things.

**Why path-based instead of string-matched:**
- Survives refactors. A context moved from `contexts/python-standards.md` to `contexts/languages/python.md` uses `../../knowledge/...` instead of `../knowledge/...`; the classifier doesn't care.
- Survives alternate warehouse layouts as long as they keep the canonical `knowledge/` top-level dir.
- Single classifier rule applies uniformly to contexts and skills regardless of nesting depth.

### D5. Frontmatter schema and validation (skills only)

```yaml
---
name: <string, matches dir name>
description: <optional string>
requires:
  contexts: [<stem>, ...]
---
```

Validation rules:
- `requires:` key is mandatory on skill entrypoints. Absence is a hard error.
- `requires.contexts` is a list of strings; empty list is permitted.
- `requires.skills` is not permitted on skills.
- Each name must resolve to a file that exists in the warehouse (`contexts/<name>.md`).
- Each name must correspond to an adopted context at sync time (checked after dependency resolution).

Agent `requires:` frontmatter may exist as warehouse metadata for future groundwork (PER-109) but is not validated or read during `abc sync`.

Validation is a separate pass before sync. Errors are collected and presented together where possible ("skill X requires context A which is not adopted") rather than failing on the first miss.

### D6. Explicit vs transitive provenance for contexts

`beacon.yaml.artifacts.contexts` continues to hold explicit user adoptions. Sync computes a larger "effective set":

```
effective_contexts = explicit_contexts
                   ∪ required_by_adopted_skills
```

Symlinks are created for the effective set. On unadoption, pruning uses set logic: a context's symlink is removed only when it is in neither `explicit_contexts` nor required by any adopted skill in the new effective set.

This is the same pattern as knowledge, one tier up. It preserves the invariant that explicit adoption is user-visible in `beacon.yaml`, while transitive adoption is auditable only through dependency walks.

**Alternative considered — mark provenance in `beacon.yaml` with metadata:**
`contexts: [{name: python-standards, source: transitive}]`. Rejected because YAML becomes noisy, diffs get uglier, and the information is trivially recomputable from the graph. Provenance is machine state, not user-visible state.

### D7. Skill-to-skill dependencies not supported

Skills may not declare `requires.skills` — the `skills:` key is rejected at parse time on skill frontmatter.

**Why the restriction:**
- Skill-to-skill is composition: a skill "uses" another skill. The use cases we surveyed all reduce to either (a) duplicating the other skill's content, (b) extracting the shared part into a context, or (c) having the agent require both skills and let the agent orchestrate (future PER-109).
- If real skill-to-skill cases appear, the restriction is easy to lift in a future change. Shipping without it keeps the graph shallow.

### D8. Error reporting format

Every error message produced by frontmatter validation, dependency resolution, or migration includes:
1. The offending artifact name.
2. The nature of the error in one sentence.
3. A URL to the migration document: `docs/migrations/artifact-dependencies-frontmatter.md` (rendered as a GitHub URL in CI output and as a local path in project-side errors).

Errors are surfaced via `loguru` at `ERROR` level and via non-zero exit codes from `abc sync` / `abc adopt`.

## Risks / Trade-offs

- **[Risk] Migration breaks consumers of the canonical warehouse on upgrade day.**
  → Mitigation: the manual warehouse pass must land before the code change; this is why the warehouse migration prompt exists and is handed to a separate model. The migration doc explicitly warns other warehouse maintainers to coordinate CLI upgrades with their frontmatter migration.

- **[Risk] Scanner performance on very large warehouses.**
  → Mitigation: for a warehouse with 100 contexts and 100 skills, the scanner reads ~200 files per sync. At ~1ms per file with pathlib, that's 200ms — imperceptible. Defer caching until someone actually hits a performance wall.

- **[Risk] Silent drop of legacy `knowledge` field surprises users who had a meaningful pin.**
  → Mitigation: informational log on first migrated sync. Git diff of `beacon.yaml` will show the field removed — standard code review catches unexpected changes. No in-flight data is lost; the user can always re-adopt a context that references what they wanted.

- **[Risk] Skill→context one-way dependency feels asymmetric.**
  → Accepted. Better to ship a shallow graph and lift the restriction on demand than to design for anticipated needs that never materialize.

- **[Risk] Markdown link resolution has edge cases (URL-encoded characters, anchors like `file.md#section`).**
  → Mitigation: strip anchors before classification; use `urllib.parse.unquote` on the link target before resolving. Tested explicitly.

- **[Trade-off] Skill maintainers must remember the frontmatter contract.**
  → Accepted. It's a one-line contract documented in the migration doc. Loud errors at sync time catch omissions immediately. The alternative (scanning prose) would be worse by every measure.

- **[Trade-off] No `abc doctor` command in this change means validation only runs on `abc sync`.**
  → Accepted. Sync is the natural validation point; running a separate doctor command is redundant until we have validation types that shouldn't block sync (format warnings, style hints, etc.). Those are genuinely follow-up work.

## Migration Plan

### Phase 0 — Pre-flight (before any code lands)

1. Human operator runs the warehouse migration prompt (drafted; lives in the session handoff) against `~/Code/knowledge/hl-knowledge-market/`.
2. Human reviews the resulting frontmatter additions, fixes any `TODO: verify` flags, commits to warehouse main.
3. Same review standard applied to any other warehouse the team uses.

### Phase 1 — Code change (this OpenSpec change)

1. Add `docs/migrations/artifact-dependencies-frontmatter.md` (already drafted).
2. Implement frontmatter parser and validator for skills.
3. Implement knowledge reference scanner.
4. Update `ArtifactsConfig` to remove `knowledge` field and add legacy-drop migration hook.
5. Update adoption domain: remove knowledge from discovery/TUI; add transitive/orphan provenance tracking for contexts.
6. Update distribution orchestrator: compute effective sets, run validation, derive knowledge, prune orphans.
7. Update `examples/sample-warehouse/` so every skill carries the new frontmatter; remove `knowledge:` from sample `beacon.yaml`.
8. Tests: unit tests for parser, scanner, dependency resolver; integration test for a full sync that exercises a skill→context→knowledge graph.

### Phase 2 — Rollout

1. Merge code change to `main`.
2. Release-Please PR bumps version; merge.
3. Users on old CLI + new warehouse: their sync still works because the old CLI ignores frontmatter.
4. Users on new CLI + old warehouse: their sync errors loudly (skills missing `requires:`) with a pointer to the migration doc.
5. Users on new CLI + new warehouse: silent happy path.

### Rollback

If the change ships broken:
1. Revert the code change on `main`.
2. Release-Please bumps version; users downgrade or stay on old CLI.
3. Warehouse frontmatter additions are harmless under old CLI (it ignores the block entirely).

No irreversible actions at any point. The warehouse migration is additive YAML; the CLI migration of `beacon.yaml` just drops a field that was already meaningless.

## Open Questions

None remaining after the planning grill. All decision-tree branches (D1–D8, migration phases, risks) have been walked and resolved with the requester. If implementation surfaces new questions — e.g., a YAML edge case the spec didn't anticipate — resolve them with minimal scope expansion and record the decision in `knowledge/decisions/` as usual.
