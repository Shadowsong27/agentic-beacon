# config-based-artifact-management Specification

## Purpose
TBD - created by archiving change config-based-artifact-management. Update Purpose after archive.
## Requirements
### Requirement: Beacon.yaml config file for artifact dependencies
The system SHALL support a beacon.yaml configuration file that declares which artifacts from the warehouse should be synced to the project.

#### Scenario: Create beacon.yaml in project
- **WHEN** user runs `abc setup` after connecting to warehouse
- **THEN** system creates `.agentic-beacon/beacon.yaml` with template structure

#### Scenario: Beacon.yaml grouped by artifact type
- **WHEN** system reads beacon.yaml
- **THEN** artifacts are organized under `knowledge:`, `skills:`, and `contexts:` groups

#### Scenario: Beacon.yaml is committed to git
- **WHEN** user creates beacon.yaml for project
- **THEN** file should be committed to version control (not in .gitignore) for team sharing

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
The system SHALL treat beacon.yaml as declarative specification of project's artifact dependencies.

#### Scenario: Artifacts list defines what should exist
- **WHEN** beacon.yaml lists specific artifacts
- **THEN** running `abc sync` ensures exactly those artifacts exist locally

#### Scenario: Removing artifact from beacon.yaml
- **WHEN** user removes artifact path from beacon.yaml and runs `abc sync --prune`
- **THEN** system removes that artifact from local `.agentic-beacon/artifacts/`

#### Scenario: Adding artifact to beacon.yaml
- **WHEN** user adds new artifact path to beacon.yaml and runs `abc sync`
- **THEN** system copies that artifact from warehouse to local artifacts directory

### Requirement: Reproducible artifact selection
The system SHALL enable reproducible artifact selection across team members using shared beacon.yaml.

#### Scenario: Team member clones project
- **WHEN** new team member clones project with beacon.yaml, connects to warehouse, and runs `abc sync`
- **THEN** they receive exact same artifacts as defined in beacon.yaml

#### Scenario: Beacon.yaml ensures consistency
- **WHEN** two team members sync from same beacon.yaml
- **THEN** both have identical artifacts in their local projects

### Requirement: Validation of artifact paths in beacon.yaml
The system SHALL validate that artifact paths in beacon.yaml exist in connected warehouse.

#### Scenario: Valid artifact paths
- **WHEN** user runs `abc sync` and all beacon.yaml paths exist in warehouse
- **THEN** system syncs artifacts successfully

#### Scenario: Missing artifact in warehouse
- **WHEN** user runs `abc sync` and beacon.yaml references path that doesn't exist in warehouse
- **THEN** system displays warning listing missing artifacts and continues with available ones

#### Scenario: Empty beacon.yaml
- **WHEN** user runs `abc sync` with empty or minimal beacon.yaml
- **THEN** system completes successfully without syncing any artifacts
