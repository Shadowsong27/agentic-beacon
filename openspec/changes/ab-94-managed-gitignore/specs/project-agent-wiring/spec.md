## MODIFIED Requirements

### Requirement: Agent directories are gitignored unconditionally via the managed block

The prior behavior — `abc setup` / `abc sync` / `abc adopt` adding `.claude/agents/` and `.opencode/agents/` to the root `.gitignore` only when agents are declared, via the `update_agent_gitignores` / `ensure_agent_dirs_gitignored` helper, and pruning those entries when agents are removed — is superseded. Agent directories SHALL be owned by the Tier A managed block (see the `beacon-gitignore-management` capability) as unconditional entries. `abc sync`, `abc adopt` accept, and `abc warehouse connect` SHALL each write `.claude/agents/` and `.opencode/agents/` into the managed block regardless of whether any agent is declared in `beacon.yaml.artifacts.agents`. The agent-dir-specific helpers and the prune-on-empty behavior SHALL be removed.

#### Scenario: Agent dirs ignored even with no agents declared

- **GIVEN** a project with `beacon.yaml.artifacts.agents: []`
- **WHEN** `abc sync` runs
- **THEN** the root `.gitignore` managed block contains `.claude/agents/` and `.opencode/agents/`

#### Scenario: Fresh project — .gitignore created with agent dirs in the block

- **GIVEN** a project with no `.gitignore`
- **WHEN** `abc sync` runs (with or without declared agents)
- **THEN** a `.gitignore` is created whose managed block includes `.claude/agents/` and `.opencode/agents/`

#### Scenario: Agent dirs are not pruned when agents are removed

- **GIVEN** a wired project whose `beacon.yaml.artifacts.agents` is emptied
- **WHEN** `abc sync` runs
- **THEN** `.claude/agents/` and `.opencode/agents/` remain in the managed block (they are unconditional, not pruned)

#### Scenario: Idempotent re-run

- **WHEN** `abc sync` runs twice in sequence
- **THEN** the agent entries appear exactly once, inside the single managed block
