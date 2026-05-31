## Context

Warehouse artifacts (contexts, skills, agents, knowledge) cross-reference each other with inline markdown links. They are authored once in a warehouse clone and distributed via **per-file symlinks** into N downstream projects under `.agentic-beacon/artifacts/` — except agents, which are additionally symlinked into `.claude/agents/` and `.opencode/agents/`, *outside* that mirror.

Because the symlinked file content is byte-identical everywhere (no copy, no transform step), a link's correctness depends entirely on the literal path string working at the surface that consumes it. Today three link styles coexist in the live warehouse: directory-relative (`../../contexts/foo.md`), project-root-anchored-but-broken (`../../../.agentic-beacon/artifacts/...`), and genuinely external (`../../../apps/...`). The middle form only resolves by accident of filesystem depth; the external form never survives distribution. The result is links that work for the author and silently break for every downstream consumer.

The lint engine (`abc warehouse lint` → `lint_warehouse()`) and a markdown link scanner (`core/scanner/scanner.py`) already exist, but the lint only flags missing `knowledge/` targets. The warehouse repo (`hl-knowledge-market`) already gates PRs with `abc warehouse lint .` via `uv tool install agentic-beacon`.

## Goals / Non-Goals

**Goals:**
- One canonical link form for intra-warehouse cross-artifact references.
- A lint that errors on every non-canonical / unresolvable intra-warehouse link, including anchors.
- An in-place auto-migration (`lint --fix`) and a one-time migration of the existing warehouse.
- A contribute-time gate (in the `contribute-warehouse` skill).
- An end-to-end integration test proving links resolve after a real `abc sync`.
- Close PER-238: agent partials stop being exposed as opencode subagents.

**Non-Goals:**
- Frontmatter base-name resolution (`contexts:` / `skills:`) — already works via the artifact resolver.
- Knowledge-file auto-derivation paths.
- Making canonical links resolve in a raw GitHub view of the warehouse repo (consciously sacrificed).
- A `preview`/`render` command (possible future follow-up, not in scope).
- Adding any CI workflow to this repo (the warehouse repo already gates).

## Decisions

### D1. Canonical form is project-root-relative `.agentic-beacon/artifacts/<warehouse-rel>`

Every intra-warehouse cross-artifact link is written as `.agentic-beacon/artifacts/<target-warehouse-relative-path>`, identical regardless of the linking file's own location.

**Why over directory-relative (`../../contexts/foo.md`):** The primary runtime consumer is an LLM agent running in a downstream project with cwd = project root. The project-root form is a literal zero-computation `Read()` target; directory-relative forces the agent to compute its own location through a symlink (logical ≠ physical path), which LLMs do unreliably. Decisively, **agents distribute outside the `.agentic-beacon/artifacts/` mirror** (into `.claude/agents/`), so directory-relative is structurally impossible for agent→partial links — project-root is the only form that unifies all artifact types.

**Alternatives considered:**
- *Directory-relative.* Resolves natively in the GitHub warehouse view for mirror artifacts, but fails for agents and is brittle for LLM resolution. Rejected as the canonical form (it becomes the thing migration rewrites away).
- *Sentinel namespace (`@beacon/...`).* Cleaner and layout-decoupled, but is not a valid relative path either, so it also breaks on GitHub, *and* every consumer (each LLM) must be taught the sentinel before it can `Read()` it. Strictly more friction than project-root for the same resolution behavior.
- *Sync-time rewrite (ticket option #4).* Impossible under the symlink model — rewriting a symlink's content forks it from its single source of truth.

**Accepted cost:** canonical links do not resolve in raw markdown renderers (GitHub warehouse view, plain editor cmd-click). Resolution always goes through a Beacon-aware consumer (lint, agent, future preview). Migration footprint is larger than under directory-relative because today's *working* directory-relative links must also be rewritten.

### D2. Resolution = strip prefix → warehouse root; anchors via GitHub-exact slugify

A resolver strips the literal `.agentic-beacon/artifacts/` prefix and resolves the remainder against the warehouse root. Under the distributed layout this is equivalent to `<project-root>/<link-target>` existing — which is exactly what the integration test asserts. Anchors are validated with a GitHub-compatible heading slugifier (lowercase, strip non-alphanumeric/space/hyphen, spaces→hyphen, preserve punctuation-induced double hyphens, dedup `-1/-2`), required because real anchors include URL-encoded emoji and `---` runs.

### D3. Four-way classifier decides each link's fate

`absolute-url → ignore`, `canonical → validate`, `own-skill-folder relative → allow`, `cross-artifact relative → error (fixable)`, `warehouse-escape relative → error (not fixable)`. The own-folder exception applies only to skills (the sole directory-shaped artifact); contexts, agents, and knowledge are single files and any non-canonical intra-warehouse link from them is malformed.

### D4. Migration ships as `abc warehouse lint --fix`

A reusable autofix on the existing lint, not a throwaway script. Rewrites the fixable category deterministically (compute target's warehouse-relative path, prepend the prefix, preserve anchor), reports counts, leaves warehouse-escape errors for a human. The one-time migration is this command run once against the warehouse.

### D5. Contribute gate lives in the `contribute-warehouse` skill

The skill runs `abc warehouse lint` and blocks on error findings (suggesting `--fix`) before committing. The raw `abc warehouse contribute` CLI stays ungated as the lower-level primitive, matching the existing architecture where the skill is the smart wrapper.

### D6. CI is unchanged in this repo

The lint is a warehouse concern enforced by the warehouse repo's existing `lint.yml`. This repo only ships the rules; a new `agentic-beacon` release propagates them to the warehouse gate via `uv tool install agentic-beacon`.

### D7. Agent partials restructured (absorbs PER-238)

Move `agents/_partials/` → top-level `agent-partials/`; keep distributing partials into the `.agentic-beacon/artifacts/agent-partials/` mirror (retarget the orchestrator dependency glob from `agents/_partials/**` to `agent-partials/**`, gated on "≥1 agent declared"); stop wiring partials into `.claude/`/`.opencode/`; delete the PER-238 `disable: true` stopgap; rewrite the two supervisor agents' links to canonical form; prune stale tool-dir partials on sync.

**Why:** the partial is already in the mirror today, so the canonical link target already exists — the only real bug is the *extra* tool-dir destination that opencode mis-reads as a callable subagent. Removing that destination and moving the partial out of the `agents/` tree closes PER-238 cleanly. Doing it here (rather than leaving links malformed) is forced anyway: the new lint would otherwise go red on the supervisor agents.

## Risks / Trade-offs

- **GitHub warehouse view broken for canonical links** → accepted per D1; mitigation is a possible future `abc preview`. Frontmatter nav and grep still work.
- **Slugifier divergence from GitHub** (emoji/unicode edge cases) → mitigate with a unit-test table seeded from real warehouse anchors; treat unknown-codepoint handling conservatively.
- **Large migration diff touches nearly every artifact** → `lint --fix` is deterministic and idempotent; review the diff in the warehouse PR; the integration test + warehouse `lint.yml` catch regressions.
- **Partial restructure is distribution-code surgery riding with lint work** → covered by the new integration test (partial materialized in mirror, absent from tool dirs) and a stale-prune scenario; PER-238's interim stopgap is removed only once the new path is proven.
- **Rule enforced only after release** → sequence: merge here → release `agentic-beacon` → run `lint --fix` + partial move in the warehouse PR → warehouse `lint.yml` enforces.

## Impacted Modules

**Repository: `agentic-beacon` (this repo)** — create feature branch `gate-artifact-reference-paths`:
- `core/scanner/scanner.py` — canonical resolution, four-way classifier, GitHub slugifier.
- `domains/warehouse/lint.py` — broaden link-integrity rule; finding types; sort/report.
- `cli/warehouse.py` — `--fix` flag + autofix reporting.
- `domains/distribution/orchestrator.py`, `distributor.py` (`is_partial_path`), `delta.py` — retarget partial glob to `agent-partials/**`; stale tool-dir prune.
- `domains/setup/wiring.py` — remove partial co-distribution + `disable: true` stopgap.
- `data/skills/contribute-warehouse/` — add the lint gate step.
- `tests/unit/` (slugifier, classifier, lint findings) + `tests/integration/` (synthetic warehouse sync + link-resolution walk + negative fixture).
- `CONTRIBUTING.md` + authoring guide docs.

**Repository: `hl-knowledge-market` (warehouse)** — separate PR, branch `gate-artifact-reference-paths`:
- Move `agents/_partials/` → `agent-partials/`.
- Run `abc warehouse lint --fix` (one-time migration); hand-fix any warehouse-escape links.
- No workflow change (existing `lint.yml` enforces after release).

## Open Questions

- Exact unicode/emoji normalization corners of the slugifier vs GitHub — resolve empirically against the real anchor set during implementation.
- Whether any existing warehouse-escape links are intentional references that should become plain URLs vs be deleted — decide per-link during the warehouse migration PR.
