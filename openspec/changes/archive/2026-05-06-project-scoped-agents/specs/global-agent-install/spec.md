## MODIFIED Requirements

### Requirement: Install does not modify beacon.yaml
`abc install agents/<name>.md` SHALL NOT add any entry to `beacon.yaml` under any artifact type key. This command remains available as a power-user escape hatch for global agent installation without project-level declaration; the project-scoped entry point for agent adoption is `abc adopt` (see `artifact-adoption` capability).

#### Scenario: beacon.yaml unchanged after agent install
- **WHEN** `abc install agents/<name>.md` completes successfully
- **THEN** the project's `beacon.yaml` (if present) is identical to before the command was run — `artifacts.agents` is not modified

#### Scenario: Global install coexists with project declaration
- **WHEN** a user runs `abc install agents/spec-planner.md` in a project where `beacon.yaml.artifacts.agents` does NOT include `agents/spec-planner.md`
- **THEN** the agent is globally symlinked and `beacon.yaml` is unchanged; a subsequent `abc adopt` invocation will show the agent as an unadopted candidate that the user can opt into declaring
