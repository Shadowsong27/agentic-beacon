# config-based-artifact-management Specification

## Purpose
TBD - created by archiving change config-based-artifact-management. Update Purpose after archive.
## Requirements
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

### Requirement: Glob pattern support in artifact paths
The system SHALL support glob patterns in beacon.yaml artifact specifications for flexible selection.

#### Scenario: Wildcard glob for all files in directory
- **WHEN** beacon.yaml contains `languages/python/**/*.md`
- **THEN** system syncs all markdown files under languages/python/ and subdirectories

#### Scenario: Specific file path
- **WHEN** beacon.yaml contains `infrastructure/docker-standards.md`
- **THEN** system syncs only that specific file

#### Scenario: Invalid glob pattern
- **WHEN** beacon.yaml contains invalid glob pattern
- **THEN** system displays error with pattern that failed and suggested correction

### Requirement: Declarative dependency specification
The system SHALL treat beacon.yaml as the declarative specification of the project's explicit artifact adoptions for contexts and skills. Knowledge is NOT declared in beacon.yaml; it is derived at sync time.

#### Scenario: Artifacts list defines what should exist
- **WHEN** beacon.yaml lists specific contexts and skills
- **THEN** running `abc sync` ensures exactly those artifacts exist locally, plus all knowledge files referenced by the adopted contexts and skills

#### Scenario: Removing artifact from beacon.yaml
- **WHEN** user removes an artifact path from beacon.yaml and runs `abc sync`
- **THEN** system removes that artifact from local `.agentic-beacon/artifacts/`, and also prunes any knowledge symlinks that are no longer referenced by any remaining adopted artifact

#### Scenario: Adding artifact to beacon.yaml
- **WHEN** user adds a new context or skill path to beacon.yaml and runs `abc sync`
- **THEN** system syncs that artifact, scans it for knowledge references, and creates symlinks for any newly-referenced knowledge files

### Requirement: Reproducible artifact selection
The system SHALL enable reproducible artifact selection across team members using shared beacon.yaml.

#### Scenario: Team member clones project
- **WHEN** new team member clones project with beacon.yaml, connects to warehouse, and runs `abc sync`
- **THEN** they receive exact same artifacts as defined in beacon.yaml

#### Scenario: Beacon.yaml ensures consistency
- **WHEN** two team members sync from same beacon.yaml
- **THEN** both have identical artifacts in their local projects

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
