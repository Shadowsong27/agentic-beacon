## Context

Warehouse agents currently declare their context/skill dependencies via YAML frontmatter:

```yaml
---
name: spec-planner
description: Planning agent for the OpenSpec workflow…
requires:
  contexts: [openspec-workflow]
  skills: [opsx-enhance-tasks]
---
```

This block is Beacon metadata — `requires:` is never a concept OpenCode or Claude Code understands. But because it lives in the frontmatter of a file OpenCode scans (`~/.config/opencode/agents/*.md`), it enters OpenCode's config pipeline.

Tracing OpenCode's source (`packages/opencode/src/config/agent.ts`):

```ts
const KNOWN_KEYS = new Set([
  "name", "model", "variant", "prompt", "description",
  "temperature", "top_p", "mode", "hidden", "color", "steps",
  "maxSteps", "options", "permission", "disable", "tools",
])

const normalize = (agent) => {
  const options = { ...agent.options }
  for (const [key, value] of Object.entries(agent)) {
    if (!KNOWN_KEYS.has(key)) options[key] = value  // ← any unknown key becomes provider option
  }
  ...
}
```

Unknown top-level keys are promoted into `options`, which is spread verbatim into the AI SDK call. OpenCode's own docs (`/docs/agents/#additional`) confirm this is a deliberate feature: *"Any other options you specify in your agent configuration will be passed through directly to the provider as model options."*

When the provider SDK is lenient (Anthropic native), unknown fields are silently dropped. When it's strict (LiteLLM's Pydantic model for Bedrock, OpenAI-via-LiteLLM, etc.), the request is rejected pre-flight with `Extra inputs are not permitted`. A temporary probe agent with `probe_marker:` reproduced this exactly under a Bedrock-backed LiteLLM model.

The architectural mistake is that Beacon's metadata lives inside a file that a third-party coding agent scans. Any framework adding non-standard keys to agent frontmatter will hit this same wall on any strict provider. The fix is to remove the metadata from that file entirely.

## Goals / Non-Goals

**Goals:**
- Eliminate the provider-rejection bug by removing `requires:` from every warehouse agent's frontmatter.
- Preserve the dependency-declaration capability warehouse authors need, by relocating it into a warehouse-owned manifest.
- Keep the change scope-tight: Beacon-side file-format migration only. No changes to `abc adopt`, `abc sync`, `abc install`, or the global/project scoping of agents.
- Lay a clean foundation for the follow-up `project-scoped-agents` change to consume.

**Non-Goals:**
- Changing the global install model for agents (`sync_agents_from_warehouse` unchanged).
- Adding `artifacts.agents:` to `beacon.yaml`. Deferred to the follow-up change.
- Running `abc sync` validation of agent → skill dependencies against project state. Deferred.
- Auto-tick / transitive selection in the adopt TUI for agents. Deferred.
- Supporting `contexts:` as an agent-level dependency. Explicitly removed: contexts are a project-level concern; an agent does not inherently require any context.
- Upstream fix to OpenCode's pass-through behaviour. That is a separate (optional) community PR and is not on this change's critical path.
- Fixing LiteLLM strictness. Their strictness is correct behaviour; the payload shouldn't contain unknown fields in the first place.

## Decisions

### Decision 1 — Centralized manifest, not per-agent sidecar or body-block

**Chosen:** single file at `<warehouse>/agents/agents.yaml` containing dependency metadata for every agent in the warehouse.

**Alternatives considered:**

- **HTML comment in agent body** (`<!-- beacon:requires ... -->`). Invented a micro-convention with no established precedent; extra prompt tokens; bespoke parser required.
- **Fenced YAML code block with info string in agent body** (```` ```yaml beacon:requires ````). More conventional than HTML comments; matches Quarto / Jupyter patterns. But the dependency data would live in N agent files instead of one; ~50 tokens of prompt pollution per agent per call; parser still bespoke.
- **Per-agent sidecar** (`agents/spec-planner.beacon.yaml`). Clean separation, but two files per agent, and duplicates the "one logical artifact = one file" convention Beacon currently holds for skills.
- **Centralized manifest** (chosen). One file to parse, one file to review, zero prompt pollution, symmetric with how `beacon.yaml` already serves as a project-level manifest. Warehouse-level agent manifest is its natural twin.

**Rationale:** the centralized form produces contiguous diffs when agents change dependencies, gives Beacon a single well-known file to validate, and keeps the `agents/*.md` files purely as coding-agent-prompt content. The per-agent sidecar was the runner-up — the main argument against it was the strict "one file per artifact" convention Beacon holds and the N-file surface for review diffs. The centralized form wins on simplicity.

### Decision 2 — Schema: skills only, no contexts

**Chosen:** `{ <agent-name>: { skills: [<skill-stem>, ...] } }`. No `contexts:` key, ever.

**Alternatives considered:**

- **Preserve `contexts:` and `skills:`** matching the old frontmatter shape. Initially the natural default for a "lossless move."
- **Skills only** (chosen). Contexts are project-level: they shape what the LLM understands *in a specific project*. Agents are reusable across projects. An agent asserting "I require context X in every project" would be telling projects what to load, which contradicts how contexts work (projects opt into contexts via their own `beacon.yaml`). Skills are different: a skill is a concrete capability an agent invokes. `spec-planner` genuinely *uses* `opsx-enhance-tasks`; without that skill installed, the agent doesn't work.

**Rationale:** dropping `contexts:` fixes a conceptual bug in the original frontmatter design, not just a format. Warehouse authors that previously listed contexts under an agent were overstating the relationship — those contexts belonged in the *project's* `beacon.yaml`, not the agent's metadata. Migration surfaces this: during manual migration, warehouse authors delete context lists; nothing downstream consumes them today (existing specs already hedge "agent `requires:` is not read during `abc sync`").

### Decision 3 — Warehouse-only file, never distributed

**Chosen:** `agents.yaml` lives at `<warehouse>/agents/agents.yaml` and nowhere else. It is never symlinked, copied, or referenced from any tool directory (`~/.config/opencode/agents/`, `~/.claude/agents/`, `.opencode/`, `.claude/`).

**Alternatives considered:**

- **Symlink alongside agents in global install dir.** Makes the dependency metadata travel with the agent install. Rejected: risks future OpenCode loader changes picking up `.yaml` files in its agent scan; creates collision between multiple warehouses trying to place `agents.yaml` at the same global location.
- **Per-agent sidecar symlinks.** Reverts to the sidecar idea, just justified differently. Rejected for the same "one logical artifact = one file" reasons.
- **Warehouse-only** (chosen). Beacon reads `agents.yaml` from the connected warehouse path. OpenCode and Claude Code never encounter it. Symmetric with `beacon.yaml`, which also lives at a known project location and is never symlinked into tool directories.

**Rationale:** the failure mode that motivated this change — `requires:` reaching a provider because it landed in a directory a tool scans — cannot recur if the replacement file is never placed in any scannable directory. Keeping `agents.yaml` purely warehouse-side preserves a clean invariant: install destinations are dumb mirrors that hold exactly what their respective tools expect.

### Decision 4 — Strict schema; missing manifest entry for an existing agent is a hard error

**Chosen:** every `agents/*.md` file in the warehouse must have a corresponding top-level key in `agents.yaml`. Missing entry → hard error at validation time. Empty skill list (`{}`  or `skills: []`) is the valid way to say "this agent has no skill dependencies."

**Alternatives considered:**

- **Treat missing entry as "no dependencies."** Convenient, but silently accepts malformed warehouses and makes "did I forget to declare this?" invisible. Same argument the archived `artifact-dependency-resolution` change made for skill frontmatter: absence of the `requires:` key is an error, not a default.
- **Strict schema** (chosen). Consistent with the rule already established for skill frontmatter. Warehouse authors must explicitly opt every agent into the manifest; silent omissions fail fast.

**Rationale:** the warehouse is a structured artifact store. Its validation is strict on purpose — partial or implicit metadata leads to runtime surprises. The cost of typing `name: {}` per agent is trivial; the benefit of catching omissions at warehouse-read time is significant.

### Decision 5 — Validation happens at warehouse-read sites, not at agent install

**Chosen:** Beacon validates `agents.yaml` during `abc warehouse status` and `abc sync`. `abc install agents/<name>.md` is unchanged and does *not* validate. `sync_agents_from_warehouse` is unchanged.

**Alternatives considered:**

- **Validate at `abc install` too.** Tempting, but `abc install` operates on a single agent file — it would need to load the whole manifest to validate. Adds I/O and failure surface to a fast command.
- **Validate only at `abc sync`.** Misses `abc warehouse status`, which already does structural validation of the warehouse and is the natural place to surface format errors early.
- **Validate at both `abc warehouse status` and `abc sync`** (chosen). Status is the warehouse-author's diagnostic tool; sync is the consumer-project's entry point. Both benefit from catching malformed `agents.yaml` early.

**Rationale:** the existing validation surface in `domains/warehouse/validator.py` is the right home. Adding `agents.yaml` checks there reuses the error-reporting and exit-code contract already established for other warehouse structural issues.

### Decision 6 — Migration: warehouse authors migrate manually, assisted by a script

**Chosen:** no automatic in-place rewrite during `abc sync`. Warehouse authors run a one-time migration script (provided alongside this change) that reads every `agents/*.md`, extracts the `requires:` block, emits `agents/agents.yaml`, and strips `requires:` from the frontmatter. Script is idempotent.

**Alternatives considered:**

- **Auto-migrate at `abc sync`** the first time a legacy warehouse is read. Rejected: implicit mutation of warehouse state by a consumer-side command violates the SSOT model (warehouse is written only via `abc warehouse contribute` or direct warehouse edits).
- **Require manual edit, no script.** Works but invites errors on warehouses with 8–20 agents.
- **Migration script that the warehouse author runs in their warehouse checkout** (chosen). Explicit, reviewable via `git diff`, one-shot.

**Rationale:** Beacon's warehouse model is clear that consumer-side commands never write to the warehouse. A migration script that runs *in* the warehouse repo is the correct shape — it's equivalent to any other repo migration a maintainer would run.

## Risks / Trade-offs

**[Risk]** Breaking change: existing warehouses stop working until migrated.
**Mitigation:** Error messages from `abc warehouse status` and `abc sync` point at the migration doc (`docs/migrations/artifact-dependencies-frontmatter.md`). The migration script is one command. The doc includes before/after examples. Because the archived `artifact-dependency-resolution` change already said agent `requires:` was "warehouse metadata for future groundwork, not read during `abc sync`," no *project* break results — projects continue to work; only warehouses need migration before their authors upgrade Beacon.

**[Risk]** Warehouse authors who have existing agents with `contexts:` listed lose that metadata when migrating (the new schema drops the field).
**Mitigation:** the migration script prints a summary of dropped `contexts:` entries, flagging them as "no longer recorded — move to project `beacon.yaml` if the project needs them." Manual review catches any legitimate ones. The archived specs already establish that agent-declared contexts weren't being read at sync time, so no behaviour regression.

**[Risk]** `agents.yaml` becomes a hand-edited file with no schema-backed editor assistance.
**Mitigation:** Beacon validates it strictly on every warehouse-read, so typos and malformed entries surface loudly. A JSON Schema could be published later for IDE support — out of scope here.

**[Risk]** Two sources of truth: frontmatter and `agents.yaml` coexist in warehouses mid-migration.
**Mitigation:** Beacon's validation refuses to proceed if any warehouse agent still has a `requires:` block in its frontmatter. One state or the other, never both. Migration is atomic per warehouse.

**[Risk]** The follow-up `project-scoped-agents` change may want fields in `agents.yaml` that this change doesn't anticipate.
**Mitigation:** the schema is permissive at the agent-entry level — `{ <agent-name>: { skills: [...] } }` is the current requirement, but unknown keys under each agent entry are allowed-but-ignored, giving the follow-up change room to add fields (e.g. `default: true` for PER-109) without a schema break.

## Migration Plan

**For this repo (agentic-beacon):**

1. Ship the parser change, validation, and migration script on a feature branch.
2. Update `examples/sample-warehouse/` to the new format — remove `requires:` from its agent files, add an `agents/agents.yaml`.
3. Update `docs/migrations/artifact-dependencies-frontmatter.md` with the new manifest shape.
4. Merge.

**For each warehouse (separate repo, separate commit cycle):**

1. Checkout the warehouse branch.
2. Run the migration script: reads every `agents/*.md`, writes `agents/agents.yaml`, strips `requires:` from frontmatter, prints summary of dropped `contexts:` entries.
3. Review `git diff`. Manually handle any edge cases flagged.
4. Run `abc warehouse status` to confirm validation passes.
5. Commit and push.

**Rollback:** revert the warehouse-side migration commit. Revert the agentic-beacon release. Both are independent git operations. No data loss — `requires:` data is preserved verbatim in `agents.yaml`.

## Open Questions

None at this time. All design decisions confirmed during planning.
