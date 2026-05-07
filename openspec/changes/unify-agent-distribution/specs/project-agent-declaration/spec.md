## MODIFIED Requirements

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

## REMOVED Requirements

### Requirement: Declaration is not an install filter
**Reason:** This change inverts the rule. `beacon.yaml.artifacts.agents` becomes the install manifest; agents are installed into the project (not globally), and the manifest filters which agents are installed.

**Migration:** Replaced by the wiring requirements in the new `project-agent-wiring` capability. Specifically, "Sync wires declared agents into project-local tool directories" defines the new install behaviour, and "Sync unwires pruned agents" defines what happens when entries are removed.

### Requirement: Unadopting an agent leaves the global install in place
**Reason:** Global install is removed entirely. There is no global state for unadoption to leave alone.

**Migration:** Replaced by the unwiring requirements in `project-agent-wiring`: "Sync unwires pruned agents" and "Adoption reject unwires agents immediately." Removing an entry from `beacon.yaml.artifacts.agents` (via either `abc adopt` reject or hand edit + `abc sync`) removes the project-local symlinks; nothing in the user's home directory is touched.
