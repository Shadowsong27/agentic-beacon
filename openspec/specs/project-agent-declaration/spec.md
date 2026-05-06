# project-agent-declaration Specification

## Purpose
TBD - created by archiving change project-scoped-agents. Update Purpose after archive.
## Requirements
### Requirement: beacon.yaml declares project-scoped agents
The system SHALL extend the `beacon.yaml.artifacts` schema with a new field `agents: [<agent-path>, ...]`, parallel to the existing `contexts` and `skills` fields. Each entry SHALL be a warehouse-relative path of the form `agents/<name>.md`. The field MAY be empty (or absent; absence is treated as empty). The field SHALL represent the agents whose dependency declarations this project opts into tracking — it is a **dependency declaration**, not a global-install filter.

#### Scenario: Empty agents field
- **WHEN** a project's `beacon.yaml` has `artifacts.agents: []` or omits the field entirely
- **THEN** the system treats the project as having no project-scoped agent declarations; global agent installation behaviour is unaffected

#### Scenario: Agent declared in beacon.yaml
- **WHEN** `beacon.yaml` has `artifacts.agents: [agents/spec-planner.md]`
- **THEN** the system records the project as depending on `spec-planner` for the purpose of dependency validation at `abc sync`

#### Scenario: Path normalisation
- **WHEN** a `beacon.yaml` entry is written by `abc adopt` for `spec-planner`
- **THEN** the entry is recorded as `agents/spec-planner.md` — warehouse-relative, includes the `agents/` prefix, ends in `.md`

### Requirement: Declaration is not an install filter
The system SHALL NOT use `beacon.yaml.artifacts.agents` to filter which agents are globally installed. Global agent installation via `sync_agents_from_warehouse` SHALL continue to install every `agents/*.md` file from the warehouse into every detected global tool directory, regardless of whether the agent is declared in any project's `beacon.yaml`.

#### Scenario: Project declares no agents; global install still batches
- **WHEN** a project's `beacon.yaml.artifacts.agents` is empty, and `abc sync` is run
- **THEN** `sync_agents_from_warehouse` still symlinks every warehouse agent into `~/.config/opencode/agents/` and `~/.claude/agents/` as today

#### Scenario: Project declares one agent; all warehouse agents still globally installed
- **WHEN** a project's `beacon.yaml.artifacts.agents` contains only `agents/spec-planner.md`, but the warehouse contains `spec-planner`, `pipeline-developer`, and `registra-developer`
- **THEN** all three agents are symlinked into the global tool directories on `abc sync`; only `spec-planner` is used for project-scoped dependency validation

### Requirement: Unadopting an agent leaves the global install in place
The system SHALL NOT remove the global agent symlink (`~/.config/opencode/agents/<name>.md`, `~/.claude/agents/<name>.md`) when an agent is removed from `beacon.yaml.artifacts.agents`. Global install state is shared across projects; unadoption in one project SHALL NOT mutate that shared state.

#### Scenario: Unadopt removes declaration only
- **WHEN** a project removes `agents/spec-planner.md` from `beacon.yaml.artifacts.agents` and runs `abc sync`
- **THEN** `beacon.yaml` no longer lists the agent, but the global symlinks for `spec-planner` remain in place for any other project that still depends on it

#### Scenario: Transitively-required skill behaviour mirrors existing rules
- **WHEN** the only agent declaring a transitively-pulled skill is unadopted
- **THEN** the skill follows the existing provenance rules in `artifact-adoption`: if it was only transitively pulled, it is pruned; if it was explicitly adopted, it remains
