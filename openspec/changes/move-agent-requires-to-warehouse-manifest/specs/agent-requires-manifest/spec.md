## ADDED Requirements

### Requirement: Warehouse ships an agents.yaml manifest when agents directory is non-empty
The system SHALL require every warehouse that contains at least one `agents/*.md` file (other than `README.md`) to ship a file at `<warehouse>/agents/agents.yaml`. This file SHALL be the sole source of truth for Beacon-managed agent metadata, specifically the skill dependencies each agent has. The file SHALL NOT be symlinked, copied, or otherwise distributed to any tool directory (`~/.config/opencode/agents/`, `~/.claude/agents/`, `.opencode/`, `.claude/`, `.agentic-beacon/artifacts/`).

#### Scenario: Warehouse with agents has agents.yaml
- **WHEN** a warehouse contains `agents/spec-planner.md` and `agents/agents.yaml` with a valid entry for `spec-planner`
- **THEN** `abc warehouse status` validation passes

#### Scenario: Warehouse with agents missing agents.yaml
- **WHEN** a warehouse contains `agents/spec-planner.md` but no `agents/agents.yaml`
- **THEN** `abc warehouse status` and `abc sync` both fail with an error identifying the missing file and linking to `docs/migrations/artifact-dependencies-frontmatter.md`

#### Scenario: Empty agents directory
- **WHEN** a warehouse contains an `agents/` directory with only `README.md` (or is empty)
- **THEN** `agents/agents.yaml` is not required; validation passes

#### Scenario: agents.yaml never distributed
- **WHEN** `abc install agents/<name>.md`, `abc sync`, or `sync_agents_from_warehouse` runs
- **THEN** no symlink, copy, or reference to `agents/agents.yaml` is created under `~/.config/opencode/`, `~/.claude/`, `.opencode/`, `.claude/`, or `.agentic-beacon/artifacts/`

### Requirement: agents.yaml schema and keys
The `agents.yaml` file SHALL be a YAML mapping whose top-level keys are agent name stems (filename of `agents/<name>.md` without the `.md` extension). Each value SHALL be a mapping containing at least the key `skills:`, which SHALL be a list of skill name stems (directory name of `skills/<name>/`). The `skills:` value MAY be an empty list. The top-level mapping MAY contain entries for additional keys under each agent to support forward compatibility, which MUST be preserved but are otherwise unvalidated in this capability.

The `contexts:` key SHALL NOT be present inside any agent entry in this capability; if present, it is a validation error.

#### Scenario: Agent with skill dependencies
- **WHEN** `agents.yaml` contains `spec-planner: { skills: [opsx-enhance-tasks] }`
- **THEN** Beacon records the agent `spec-planner` as depending on skill `opsx-enhance-tasks`

#### Scenario: Agent with no skill dependencies
- **WHEN** `agents.yaml` contains `pipeline-developer: { skills: [] }`
- **THEN** Beacon records the agent `pipeline-developer` as having no skill dependencies and validation passes

#### Scenario: Agent entry with contexts key
- **WHEN** `agents.yaml` contains `spec-planner: { skills: [...], contexts: [python-standards] }`
- **THEN** validation fails with an error naming the agent and stating that `contexts:` is not permitted under an agent entry

#### Scenario: Agent entry with forward-compatible extra key
- **WHEN** `agents.yaml` contains `spec-planner: { skills: [...], default: true }` where `default` is a forward-compatible key not validated by this capability
- **THEN** the extra key is preserved in the parsed manifest and validation passes

### Requirement: Every agent file has a manifest entry; every manifest key resolves to a file
The system SHALL validate bidirectional correspondence between `agents/*.md` files and `agents.yaml` entries. Every `agents/<name>.md` file (other than `README.md`) SHALL have a top-level key `<name>` in `agents.yaml`. Every top-level key `<name>` in `agents.yaml` SHALL correspond to an existing file `agents/<name>.md` in the warehouse.

Missing entry for an existing agent file is a hard error. An orphan entry for a non-existent agent file is a hard error.

#### Scenario: Every agent file declared
- **WHEN** the warehouse contains `agents/spec-planner.md` and `agents/pipeline-developer.md`, and `agents.yaml` has top-level keys `spec-planner` and `pipeline-developer`
- **THEN** validation passes

#### Scenario: Agent file without manifest entry
- **WHEN** the warehouse contains `agents/new-agent.md` but `agents.yaml` has no `new-agent` key
- **THEN** validation fails with an error naming `new-agent` and linking to the migration document

#### Scenario: Manifest entry without agent file
- **WHEN** `agents.yaml` contains a top-level key `ghost-agent` but no `agents/ghost-agent.md` exists
- **THEN** validation fails with an error naming `ghost-agent` as an orphan entry

### Requirement: Every declared skill resolves to a warehouse skill directory
For every agent entry in `agents.yaml`, every skill name in `skills:` SHALL resolve to an existing `skills/<name>/SKILL.md` in the same warehouse. Missing-from-warehouse is a hard error.

#### Scenario: Declared skill exists in warehouse
- **WHEN** `agents.yaml` has `spec-planner: { skills: [opsx-enhance-tasks] }` and `skills/opsx-enhance-tasks/SKILL.md` exists in the warehouse
- **THEN** validation passes

#### Scenario: Declared skill missing from warehouse
- **WHEN** `agents.yaml` has `spec-planner: { skills: [nonexistent] }` and no `skills/nonexistent/SKILL.md` exists
- **THEN** validation fails with an error naming the agent, the missing skill, and linking to the migration document

### Requirement: Warehouse agent frontmatter must not contain a requires block
The system SHALL refuse to operate on a warehouse in which any `agents/*.md` file contains a `requires:` key in its YAML frontmatter. This guarantees that agent dependency metadata exists in exactly one place — `agents.yaml` — and never leaks back into a coding-agent-scannable file.

#### Scenario: Agent file with leftover requires block
- **WHEN** an `agents/spec-planner.md` still contains `requires: { skills: [...] }` in its frontmatter
- **THEN** `abc warehouse status` and `abc sync` both fail with an error identifying the file and linking to the migration document, instructing the user to move the block into `agents.yaml`

#### Scenario: Agent file without requires block
- **WHEN** an `agents/spec-planner.md` has YAML frontmatter containing `name`, `description`, `mode`, and other OpenCode-standard keys, but no `requires:` key
- **THEN** validation of the file's frontmatter passes

### Requirement: Validation is performed at warehouse-read operations
The system SHALL perform `agents.yaml` validation — schema check, bidirectional correspondence, skill resolution, and frontmatter-free check — during `abc warehouse status` and during `abc sync`. `abc install agents/<name>.md` and `sync_agents_from_warehouse` SHALL NOT be extended with additional validation in this capability; they continue to operate on agent markdown files as today.

#### Scenario: abc warehouse status validates agents.yaml
- **WHEN** a user runs `abc warehouse status` in a project connected to a warehouse with a malformed `agents.yaml`
- **THEN** the command exits non-zero and reports the validation error

#### Scenario: abc sync validates agents.yaml
- **WHEN** a user runs `abc sync` and the connected warehouse has a malformed `agents.yaml`
- **THEN** the command exits non-zero and reports the validation error before performing any sync operations

#### Scenario: abc install does not re-validate agents.yaml
- **WHEN** a user runs `abc install agents/spec-planner.md` against a warehouse whose `agents.yaml` exists and is valid for the specific agent being installed
- **THEN** the install proceeds without loading or re-validating the full manifest
