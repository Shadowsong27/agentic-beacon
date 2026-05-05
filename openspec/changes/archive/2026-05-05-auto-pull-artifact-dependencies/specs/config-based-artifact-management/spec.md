## MODIFIED Requirements

### Requirement: Beacon.yaml config file for artifact dependencies
The system SHALL support a beacon.yaml configuration file that declares which artifacts from the warehouse should be synced to the project. The file declares explicit adoptions for contexts and skills; knowledge is not declared and is computed automatically at sync time by scanning the adopted artifacts.

#### Scenario: Create beacon.yaml in project
- **WHEN** user runs `abc setup` after connecting to warehouse
- **THEN** system creates `.agentic-beacon/beacon.yaml` with template structure containing `artifacts.contexts` and `artifacts.skills`

#### Scenario: Beacon.yaml grouped by artifact type
- **WHEN** system reads beacon.yaml
- **THEN** artifacts are organized under `contexts:` and `skills:` groups; no `knowledge:` group exists

#### Scenario: Beacon.yaml is committed to git
- **WHEN** user creates beacon.yaml for project
- **THEN** file should be committed to version control (not in .gitignore) for team sharing

#### Scenario: Legacy beacon.yaml with knowledge field
- **WHEN** a project's `beacon.yaml` from a prior version contains `artifacts.knowledge: [...]` and the user runs `abc sync`
- **THEN** the system emits a one-time informational log "`artifacts.knowledge` removed; knowledge is now auto-derived", drops the field, and writes the updated `beacon.yaml` without it

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

### Requirement: Validation of artifact paths in beacon.yaml
The system SHALL validate that artifact paths in beacon.yaml exist in the connected warehouse, AND that every `requires:` dependency declared by an adopted skill resolves to a context that exists in the warehouse. Required contexts that exist in the warehouse are auto-pulled transitively; they need not be explicit in `beacon.yaml`.

#### Scenario: Valid artifact paths
- **WHEN** user runs `abc sync` and all beacon.yaml paths exist in warehouse and all `requires:` dependencies resolve to warehouse contexts
- **THEN** system syncs artifacts successfully; skill-required contexts are auto-pulled

#### Scenario: Missing artifact in warehouse
- **WHEN** user runs `abc sync` and beacon.yaml references a path that doesn't exist in the warehouse
- **THEN** system displays an error listing missing artifacts and exits non-zero

#### Scenario: Required context missing from warehouse
- **WHEN** an adopted skill declares `requires.contexts: [nonexistent]` and `contexts/nonexistent.md` does not exist in the warehouse
- **THEN** `abc sync` exits non-zero with an error naming the skill and the missing dependency, and linking to the migration document

#### Scenario: Empty beacon.yaml
- **WHEN** user runs `abc sync` with empty or minimal beacon.yaml
- **THEN** system completes successfully without syncing any artifacts
