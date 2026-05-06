## Why

Agents are the one Beacon artifact type with no project-level record. They are installed globally (`~/.config/opencode/agents/`, `~/.claude/agents/`) via `abc install` or `abc adopt`, but `beacon.yaml` has no concept of "this project uses these agents." That asymmetry causes three real problems:

1. **No dependency validation possible.** An agent like `spec-planner` requires a skill like `opsx-enhance-tasks`. With agents globally installed and projects declaring only contexts and skills, Beacon cannot tell whether a project is correctly set up to use an agent that it implicitly uses. When the user invokes `@spec-planner` in a project missing the required skill, the agent silently works in a degraded state.

2. **Transitive resolution has no entry point.** The `requires:` auto-pull logic (implemented for skills in the `auto-pull-artifact-dependencies` change, now living in `artifact-dependency-resolution`) has nothing to hook onto at the agent tier. Required skills cannot flow into a project without a project-level declaration of which agents matter here.

3. **The `abc adopt` flow treats agents inconsistently with other artifacts.** `apply.py:39` has a hard-coded `continue  # agents are managed globally, not via beacon.yaml`. Contexts and skills flow through the same codepath (add to `beacon.yaml`, sync, wire); agents bypass it entirely. Every spec that mentions agents has to hedge on this asymmetry — it produces recurring design complexity ("agents are global but also partially tracked per-project").

The follow-up change `move-agent-requires-to-warehouse-manifest` (the immediate predecessor) relocated agent dependency metadata from frontmatter into `<warehouse>/agents/agents.yaml`. That change gives this one the input it needs: a machine-readable declaration of each agent's required skills. Now we can close the loop — projects declare which agents they use, Beacon resolves the transitive skill closure, validates the project has what its declared agents need, and fixes the broken agent-lifecycle layering.

## What Changes

- **New field `artifacts.agents: [<agent-path>, ...]` in `beacon.yaml`**, parallel to the existing `artifacts.contexts` and `artifacts.skills`. Declares which warehouse agents this project uses. Paths are warehouse-relative, of the form `agents/<name>.md`.
- **`artifacts.agents` is a dependency declaration, NOT an install filter.** Global agent installation continues unchanged — `sync_agents_from_warehouse` continues to batch-install every warehouse agent into `~/.config/opencode/agents/` and `~/.claude/agents/`. An agent's presence in `beacon.yaml.artifacts.agents` means "this project asserts its skill dependencies should be satisfied here," not "install this agent on this machine."
- **`abc adopt` treats agents as a project-scoped selectable category.** Agents appear as checkboxes in the TUI alongside contexts and skills. Selecting an agent:
  1. Adds `agents/<name>.md` to `beacon.yaml.artifacts.agents`.
  2. Globally installs the agent (unchanged behaviour, still happens).
  3. **Auto-ticks required skills in the same TUI session.** Reads the agent's `skills:` list from `agents.yaml` and ticks those skills visually, with a label indicating provenance (`required by <agent>`). Multiple agents requiring the same skill show combined provenance.
  4. **Hard-locks skill unticking while a requiring agent is ticked.** User cannot produce a broken selection via the TUI — to remove a required skill, the user must first untick the agent that requires it.
- **`abc sync` validates agent → skill transitive closure.** For each agent in `beacon.yaml.artifacts.agents`, reads `<warehouse>/agents/agents.yaml`, asserts every required skill appears in `beacon.yaml.artifacts.skills` (or resolves transitively). If any required skill is missing, `abc sync` prompts the user interactively (Y/N, default N) to add the skill to `beacon.yaml` and sync it. On Y: appends and continues. On N or in non-interactive mode: hard error, exit non-zero. A `--yes` flag auto-accepts; a `--strict` equivalent is implicit via the hard-error default.
- **`apply.py` removes the `continue  # agents are managed globally` skip.** Agent adoptions are recorded in `beacon.yaml` the same way contexts and skills are.
- **`abc adopt` unadoption mirror.** Removing an agent from `beacon.yaml.artifacts.agents` does NOT uninstall the global symlink (agents remain globally available across projects). It only drops the project's declaration. Required skills that become orphaned follow the same prune/preserve rules already defined for transitive contexts.
- **BREAKING for existing projects**: after upgrading Beacon, projects with agents installed globally via earlier `abc adopt` runs will have an empty `artifacts.agents` in `beacon.yaml`. No auto-backfill; users re-run `abc adopt` to re-declare. Rationale: agent global install state is not reliable enough to infer project intent ("globally installed" ≠ "this project uses it").

## Capabilities

### New Capabilities
- `project-agent-declaration`: Defines `beacon.yaml.artifacts.agents` — its role as dependency-declaration pointer, its schema, and the invariant that it is NOT an install filter.
- `agent-skill-dependency-sync`: Defines `abc sync`'s behaviour when a declared agent's required skills are missing — interactive Y/N repair prompt, non-interactive hard error, `--yes` flag.

### Modified Capabilities
- `artifact-adoption`: adopt TUI becomes agent-aware; selecting an agent auto-ticks required skills; skill unticking is hard-locked while requiring agents are selected; `apply.py` records agent selections in `beacon.yaml`.
- `config-based-artifact-management`: `beacon.yaml` schema extended with `artifacts.agents` field; sync validation extended with agent → skill transitive check.
- `global-agent-install`: clarifies that `abc install agents/<name>.md` remains a power-user escape hatch (global install only, bypasses project declaration); `abc adopt` is now the project-scoped entry point.
- `artifact-dependency-resolution`: extends the `requires:` resolver to read agent skill requirements from `agents.yaml` (written by the predecessor change) and feed them into the transitive closure at `abc sync`.

## Impact

- **Depends on:** `move-agent-requires-to-warehouse-manifest` merged. `agents.yaml` must exist and validate in the warehouse before this change's code can consume it.
- **Affected code:**
  - `libs/beacon/src/beacon/core/manifest/beacon.py` — add `agents: list[str]` field to `ArtifactsConfig`.
  - `libs/beacon/src/beacon/domains/adoption/apply.py` — remove the `continue  # agents are managed globally` skip; record agent selections in `beacon.yaml`.
  - `libs/beacon/src/beacon/domains/adoption/discovery.py` — `is_adopted()` extended to recognise agent paths.
  - `libs/beacon/src/beacon/domains/adoption/tui.py` — agent checkboxes, auto-tick logic, hard-lock skill-untick guard.
  - `libs/beacon/src/beacon/core/dependencies/resolver.py` — read `agents.yaml` for declared agents, compute transitive skill closure, surface gaps.
  - `libs/beacon/src/beacon/cli/sync.py` (or equivalent) — interactive repair prompt for missing agent-required skills.
  - `libs/beacon/src/beacon/domains/artifact/agent.py` — unchanged install path; `sync_agents_from_warehouse` still batch-installs all warehouse agents.
- **Affected fixtures:**
  - `examples/sample-warehouse/` — regenerate if the sample warehouse gains example agents declaring skill requirements.
  - Integration test fixtures mimicking multi-agent warehouse + project.
- **Affected docs:**
  - `docs/migrations/artifact-dependencies-frontmatter.md` — new section: "Project-scoped agents: opt-in via `beacon.yaml`".
  - `AGENTS.md` (repo root) — reflect new `abc adopt` behaviour.
  - Any site-docs pages describing `beacon.yaml` schema.
- **User-facing behaviour changes:**
  - `abc adopt` shows agents as selectable checkboxes with auto-tick transitive skill selection.
  - `beacon.yaml` gains `artifacts.agents` field.
  - `abc sync` may prompt Y/N for missing agent-required skills (interactive) or error (non-interactive).
  - `abc install agents/<name>.md` unchanged (global install, no `beacon.yaml` update).
- **Retires / supersedes language in existing specs:**
  - `artifact-adoption`'s "Agents are global machine-level artifacts... MAY show agents as global-install candidates" is superseded by the new project-scoped treatment.
  - `config-based-artifact-management`'s schema description is extended.
