## ADDED Requirements

### Requirement: Agent partials live at top-level `agent-partials/`

Shared agent partials SHALL reside in the warehouse at the top-level `agent-partials/` directory (a sibling of `agents/`), not under `agents/_partials/`. Because `agent-partials/` is outside the `agents/` tree, partials SHALL NOT be treated as agents by any agent-discovery, manifest, wiring, or scaffold logic.

#### Scenario: Partial is not discovered as an agent

- **GIVEN** the warehouse contains `agent-partials/deep-review-checklist.md`
- **WHEN** agent discovery and manifest validation run
- **THEN** the partial is not listed or validated as an agent

### Requirement: Agent partials distribute only into the artifacts mirror

During `abc sync`, when at least one agent is declared in `beacon.yaml.artifacts.agents`, the system SHALL distribute every file under `agent-partials/**` into the project at `.agentic-beacon/artifacts/agent-partials/**` (preserving relative structure), so that canonical links of the form `.agentic-beacon/artifacts/agent-partials/<name>.md` resolve from the project root. The system SHALL NOT create any partial symlink, wrapper, or copy under `.claude/agents/` or `.opencode/agents/`.

#### Scenario: Partial materialized in the mirror

- **GIVEN** `beacon.yaml.artifacts.agents` lists `agents/diligent-supervisor.md` and the warehouse has `agent-partials/deep-review-checklist.md`
- **WHEN** `abc sync` runs
- **THEN** `.agentic-beacon/artifacts/agent-partials/deep-review-checklist.md` exists and resolves the supervisor's canonical link

#### Scenario: No partial wired into tool directories

- **GIVEN** the project has `.claude/` and `.opencode/` configured and a declared agent that references a partial
- **WHEN** `abc sync` runs
- **THEN** no file or symlink is created under `.claude/agents/_partials/`, `.claude/agents/agent-partials/`, `.opencode/agents/_partials/`, or `.opencode/agents/agent-partials/`

#### Scenario: No agents declared

- **GIVEN** `beacon.yaml.artifacts.agents` is empty
- **WHEN** `abc sync` runs
- **THEN** no `agent-partials/` files are distributed

### Requirement: Partial co-distribution stopgap removed

The interim behavior that co-distributed agent partials into the tool directories wrapped in a `disable: true` frontmatter block SHALL be removed. Sync SHALL no longer emit any partial wrapper file, and SHALL prune any previously-created Beacon-owned partial symlink or wrapper under `.claude/agents/` and `.opencode/agents/`.

#### Scenario: Stale tool-dir partial pruned on sync

- **GIVEN** a project from a prior version has a Beacon-owned `.opencode/agents/_partials/deep-review-checklist.md`
- **WHEN** `abc sync` runs on the new version
- **THEN** the stale tool-dir partial is removed and not recreated
