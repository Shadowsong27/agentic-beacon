## MODIFIED Requirements

### Requirement: Beacon.yaml config file for artifact dependencies
The system SHALL support a beacon.yaml configuration file that declares which artifacts from the warehouse should be synced to the project. The file declares explicit adoptions for contexts, skills, and agents; knowledge is not declared and is computed automatically at sync time by scanning the adopted artifacts.

#### Scenario: Create beacon.yaml in project
- **WHEN** user runs `abc setup` after connecting to warehouse
- **THEN** system creates `.agentic-beacon/beacon.yaml` with template structure containing `artifacts.contexts`, `artifacts.skills`, and `artifacts.agents`

#### Scenario: Beacon.yaml grouped by artifact type
- **WHEN** system reads beacon.yaml
- **THEN** artifacts are organized under `contexts:`, `skills:`, and `agents:` groups; no `knowledge:` group exists

#### Scenario: Beacon.yaml is committed to git
- **WHEN** user creates beacon.yaml for project
- **THEN** file should be committed to version control (not in .gitignore) for team sharing

#### Scenario: Legacy beacon.yaml with knowledge field
- **WHEN** a project's `beacon.yaml` from a prior version contains `artifacts.knowledge: [...]` and the user runs `abc sync`
- **THEN** the system emits a one-time informational log "`artifacts.knowledge` removed; knowledge is now auto-derived", drops the field, and writes the updated `beacon.yaml` without it

#### Scenario: Pre-upgrade beacon.yaml without agents field
- **WHEN** a project's `beacon.yaml` predates this capability and has no `artifacts.agents` key
- **THEN** the system treats the field as empty (`[]`), requires no migration step, and proceeds normally; the user may populate it by running `abc adopt`

### Requirement: Validation of artifact paths in beacon.yaml
The system SHALL validate that artifact paths in beacon.yaml exist in the connected warehouse, AND that every `requires:` dependency declared by an adopted skill resolves to a context that exists in the warehouse, AND that every agent declared in `artifacts.agents` has a corresponding entry in `<warehouse>/agents/agents.yaml` whose required skills resolve in the project's effective skill set.

Required contexts that exist in the warehouse are auto-pulled transitively; they need not be explicit in `beacon.yaml`. Required skills for declared agents must be present in `beacon.yaml.artifacts.skills` (directly or via transitive pull); when missing, the repair flow defined in the `agent-skill-dependency-sync` capability is invoked.

#### Scenario: Valid artifact paths
- **WHEN** user runs `abc sync` and all beacon.yaml paths exist in warehouse, all `requires:` dependencies resolve to warehouse contexts, and all declared agents' required skills are in the project
- **THEN** system syncs artifacts successfully; skill-required contexts are auto-pulled

#### Scenario: Missing artifact in warehouse
- **WHEN** user runs `abc sync` and beacon.yaml references a path that doesn't exist in the warehouse
- **THEN** system displays an error listing missing artifacts and exits non-zero

#### Scenario: Required context missing from warehouse
- **WHEN** an adopted skill declares `requires.contexts: [nonexistent]` and `contexts/nonexistent.md` does not exist in the warehouse
- **THEN** `abc sync` exits non-zero with an error naming the skill and the missing dependency, and linking to the migration document

#### Scenario: Declared agent's required skill missing
- **WHEN** an agent in `artifacts.agents` declares a skill requirement in `agents.yaml` that is not present in `beacon.yaml.artifacts.skills` (nor transitively pulled)
- **THEN** `abc sync` invokes the repair flow defined in the `agent-skill-dependency-sync` capability (interactive Y/N prompt or non-interactive hard error)

#### Scenario: Declared agent missing from agents.yaml
- **WHEN** `beacon.yaml.artifacts.agents` contains `agents/ghost.md` but the warehouse `agents.yaml` has no `ghost` entry
- **THEN** `abc sync` exits non-zero with an error naming the project declaration and the manifest gap, and linking to the migration document

#### Scenario: Empty beacon.yaml
- **WHEN** user runs `abc sync` with empty or minimal beacon.yaml
- **THEN** system completes successfully without syncing any artifacts
