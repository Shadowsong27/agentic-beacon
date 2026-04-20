# snapshot-based-sync Specification

## Purpose
TBD - created by archiving change config-based-artifact-management. Update Purpose after archive.
## Requirements
### Requirement: Pure copy sync from warehouse to project
The system SHALL perform pure file copy from warehouse to project artifacts directory, never using symlinks.

#### Scenario: Sync copies files physically
- **WHEN** user runs `abc sync`
- **THEN** system copies artifact files from warehouse to `.agentic-beacon/artifacts/` directory

#### Scenario: No symlinks created
- **WHEN** system syncs artifacts
- **THEN** no symbolic links are created; all artifacts are actual file copies

#### Scenario: Copied files are independent
- **WHEN** user modifies file in `.agentic-beacon/artifacts/`
- **THEN** warehouse file remains unchanged (copy not reference)

### Requirement: Snapshot at point in time
The system SHALL create snapshot of artifacts at time of sync, not dynamic link to warehouse state. The system SHALL also capture the previous sync-state SHA before overwriting it, to enable post-sync notification of new warehouse artifacts.

#### Scenario: Warehouse changes don't auto-update project
- **WHEN** artifact is modified in warehouse after sync
- **THEN** project's copy remains at previous state until next `abc sync`

#### Scenario: Project isolation
- **WHEN** multiple projects sync from same warehouse at different times
- **THEN** each project has independent snapshot reflecting warehouse state at their sync time

#### Scenario: Previous sync SHA captured before overwrite
- **WHEN** `abc sync` runs and a `.sync-state` file exists from a prior sync
- **THEN** system reads the old SHA before writing the new one, making it available for post-sync notification logic

### Requirement: Idempotent sync operation
The system SHALL make `abc sync` idempotent - running multiple times produces same result.

#### Scenario: Sync twice with no changes
- **WHEN** user runs `abc sync`, makes no changes, then runs `abc sync` again
- **THEN** second sync detects no differences and completes quickly without copying

#### Scenario: Sync after local modifications
- **WHEN** user modifies local artifact and runs `abc sync`
- **THEN** system overwrites local changes with warehouse version (warehouse is source of truth)

#### Scenario: Sync with --preserve flag
- **WHEN** user has local modifications and runs `abc sync --preserve`
- **THEN** system skips overwriting files with local changes and warns user

### Requirement: Safe local experimentation
The system SHALL enable users to safely modify local artifact copies without affecting warehouse or other projects.

#### Scenario: Modify local knowledge file
- **WHEN** user edits `.agentic-beacon/artifacts/knowledge/lessons.md` locally
- **THEN** warehouse version and other projects' copies remain unchanged

#### Scenario: Test local changes with agent
- **WHEN** user modifies local artifact to test improved instructions
- **THEN** agent uses modified local version without affecting team's shared warehouse

### Requirement: Directory structure preservation
The system SHALL preserve warehouse directory structure when syncing to project.

#### Scenario: Nested paths maintained
- **WHEN** warehouse has `knowledge/languages/python/lessons.md` and user syncs
- **THEN** project has `.agentic-beacon/artifacts/knowledge/languages/python/lessons.md` with same structure

#### Scenario: Empty directories created
- **WHEN** warehouse structure includes empty intermediate directories
- **THEN** system creates those directories in project even if empty

### Requirement: Glob expansion during sync
The system SHALL expand glob patterns in beacon.yaml to actual files during sync.

#### Scenario: Glob matches multiple files
- **WHEN** beacon.yaml contains `languages/**/*.md` and warehouse has 10 matching files
- **THEN** system syncs all 10 files to project

#### Scenario: Glob matches no files
- **WHEN** beacon.yaml contains glob pattern that matches no files
- **THEN** system warns user that pattern matched nothing

#### Scenario: Glob expansion logged
- **WHEN** running `abc sync --verbose` with glob patterns
- **THEN** system logs which files were matched by each glob pattern
