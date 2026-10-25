## Why

OpenCode forwards every unknown top-level key in an agent's YAML frontmatter into the provider call's option bag (`packages/opencode/src/config/agent.ts::normalize()` explicitly promotes any non-allowlisted key into `options`). Anthropic's native SDK silently drops unknowns, but LiteLLM's Pydantic request model — used on every non-Anthropic path including Bedrock, OpenAI-via-LiteLLM, and Vertex-via-LiteLLM — rejects them with `Extra inputs are not permitted`. Our `requires:` frontmatter on warehouse agents triggers this exact failure the moment a user switches model. A probe agent (`~/.config/opencode/agents/tmp-frontmatter-probe.md`) reproduced the failure verbatim using a made-up `probe_marker:` key under a Bedrock-backed model.

The bug's root cause is that **agent `requires:` frontmatter travels into OpenCode's scannable surface**, where OpenCode's documented pass-through design then leaks it to the provider. Fixing it in LiteLLM is wrong (their strictness is a correct feature; the payload shouldn't contain unknown fields in the first place). Fixing it upstream in OpenCode is slow and doesn't help existing installs. The correct fix is to move Beacon's dependency metadata out of the agent file entirely, into a warehouse-level manifest that Beacon owns and no coding-agent tool ever reads.

## What Changes

- **New file `<warehouse>/agents/agents.yaml`** — a centralized dependency manifest at the warehouse level. Maps each warehouse agent to its required skills. Schema: `{ <agent-name>: { skills: [<skill-stem>, ...] } }`. No `contexts:` field — agents don't natively require contexts (contexts are a project-level concern, not an agent-level one).
- **BREAKING**: remove `requires:` from the YAML frontmatter of every warehouse `agents/*.md` file. Every warehouse must migrate by moving the same information into `agents/agents.yaml`. Beacon errors on `abc warehouse status` and `abc sync` if agent frontmatter still contains `requires:` or if `agents.yaml` is missing when `agents/` is non-empty.
- **Validation**: Beacon validates `agents.yaml` at every warehouse-reading operation: every agent key must correspond to a file at `agents/<key>.md`; every skill name in `skills:` must resolve to `skills/<skill>/SKILL.md`. Hard error with migration-doc URL on any mismatch.
- **`agents.yaml` is warehouse-only metadata.** Beacon reads it; OpenCode and Claude Code never see it. It is not symlinked, copied, or distributed to any tool directory. No change to `abc install agents/<name>.md`, no change to `sync_agents_from_warehouse`, no change to `abc adopt` agent handling. Agents continue to be managed as global artifacts under the existing model.
- **Migration doc** at `docs/migrations/artifact-dependencies-frontmatter.md` updated to describe the frontmatter → manifest move, the rationale (frontmatter leak), and the concrete migration steps.
- **Sample warehouse** (`examples/sample-warehouse/`) regenerated to match the new shape.
- **Existing specs that describe agent `requires:` frontmatter as warehouse metadata** (`artifact-dependency-resolution`, `snapshot-based-sync`, `knowledge-reference-scanning`, `warehouse-agent-scaffold`) updated to point at `agents.yaml` instead.

## Capabilities

### New Capabilities
- `agent-requires-manifest`: Defines the `<warehouse>/agents/agents.yaml` file — its schema, validation rules, and the invariant that it is warehouse-only and never distributed.

### Modified Capabilities
- `artifact-dependency-resolution`: currently says agent `requires:` frontmatter is warehouse metadata for future groundwork (PER-109). Updated to say agent requires live in `agents.yaml`, validated at warehouse read time, not read during project `abc sync`.
- `warehouse-agent-scaffold`: currently describes the `agents/` directory initializer writing a README about frontmatter-based `requires:`. Updated to describe `agents.yaml` as the required metadata file alongside the README.
- `knowledge-reference-scanning`: currently notes agents reach knowledge "transitively through contexts and skills declared in their frontmatter." Updated to read "declared in `agents.yaml`."

## Impact

- **Affected code**:
  - `libs/beacon/src/beacon/core/dependencies/frontmatter.py` — the `AgentFrontmatter` parser is deleted or narrowed; a new `AgentManifest` loader in `core/dependencies/` parses `agents.yaml`.
  - `libs/beacon/src/beacon/core/dependencies/resolver.py` — any agent-requires code paths (currently unused per the archived scope hedge) rewired to read `agents.yaml`.
  - `libs/beacon/src/beacon/domains/warehouse/validator.py` — extend validation to check `agents.yaml` exists when `agents/` is non-empty, and that every agent file has a manifest entry.
  - `libs/beacon/src/beacon/data/` — update bundled sample warehouse fixtures if any contain agent `requires:`.
  - Tests: unit tests for the new `AgentManifest` parser; architecture tests stay green.
- **Affected files in the personal warehouse** (`~/Code/knowledge/hl-knowledge-market/`) — every `agents/*.md` needs its `requires:` block removed; one new `agents/agents.yaml` created. Migration script scoped to this change.
- **Affected sample warehouse** (`examples/sample-warehouse/`) — regenerate after migration.
- **Affected docs** — `docs/migrations/artifact-dependencies-frontmatter.md`, any guides referencing agent frontmatter.
- **No user-facing CLI changes.** `abc warehouse status`, `abc sync`, `abc install`, `abc adopt` all continue to work; the only behaviour difference is that validation now catches `agents.yaml` errors.
- **No dependency on PER-109.** This change is independent; PER-109 / the follow-up `project-scoped-agents` change consumes `agents.yaml` as input but is not blocked by anything here.
- **Forward compatibility**: the follow-up change `project-scoped-agents` (to be proposed separately) adds `artifacts.agents: [...]` to `beacon.yaml` and rewires `abc sync` to consume `agents.yaml` for transitive-skill resolution. That change builds on the manifest introduced here.
