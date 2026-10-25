# project-agent-declaration Specification

## Purpose
Defines the `beacon.yaml.artifacts.agents` field as the project's authoritative install manifest for agents. Updated by archiving change `unify-agent-distribution` (PER-113): the field was previously a usage declaration with no install effect; it is now the install manifest that drives project-local symlink wiring, removal, and dependency validation. The two former requirements ("Declaration is not an install filter" and "Unadopting an agent leaves the global install in place") were removed because global agent install was eliminated entirely — see the `project-agent-wiring` capability for the new wiring/unwiring rules.

## Requirements

### Requirement: beacon.yaml declares project-scoped agents
The system SHALL extend the `beacon.yaml.artifacts` schema with a new field `agents: [<agent-path>, ...]`, parallel to the existing `contexts` and `skills` fields. Each entry SHALL be a warehouse-relative path of the form `agents/<name>.md`. The field MAY be empty (or absent; absence is treated as empty). The field SHALL represent the agents installed into the project — it is the **install manifest**, used both for dependency validation at `abc sync` and to drive project-local symlink wiring (see `project-agent-wiring`).

#### Scenario: Empty agents field
- **WHEN** a project's `beacon.yaml` has `artifacts.agents: []` or omits the field entirely
- **THEN** the system treats the project as having no installed agents; no project-local symlinks are written under `.claude/agents/` or `.opencode/agents/`

#### Scenario: Agent declared in beacon.yaml
- **WHEN** `beacon.yaml` has `artifacts.agents: [agents/spec-planner.md]`
- **THEN** the system records the project as installing `spec-planner`; `abc sync` creates the artifact symlink and project-local tool symlinks per the `project-agent-wiring` capability

#### Scenario: Path normalisation
- **WHEN** a `beacon.yaml` entry is written by `abc adopt` for `spec-planner`
- **THEN** the entry is recorded as `agents/spec-planner.md` — warehouse-relative, includes the `agents/` prefix, ends in `.md`
