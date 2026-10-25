## ADDED Requirements

### Requirement: Compare all artifacts in beacon.yaml
The system SHALL provide `abc delta` command that compares local artifacts against warehouse for all items in beacon.yaml.

#### Scenario: Delta with no arguments shows summary
- **WHEN** user runs `abc delta` without arguments
- **THEN** system displays summary of all artifacts with status: [Modified], [Added], [Missing]

#### Scenario: No differences found
- **WHEN** user runs `abc delta` and all artifacts match warehouse
- **THEN** system displays message "No differences found. Local artifacts match warehouse."

#### Scenario: Multiple differences shown
- **WHEN** user runs `abc delta` and several artifacts differ
- **THEN** system lists all differences with clear status indicators

### Requirement: Compare specific file with detailed diff
The system SHALL provide detailed line-by-line diff when specific file argument is provided.

#### Scenario: Delta with file path shows diff
- **WHEN** user runs `abc delta knowledge/languages/python/lessons.md`
- **THEN** system displays unified diff showing exact line changes between local and warehouse

#### Scenario: File not in beacon.yaml
- **WHEN** user runs `abc delta` on file not listed in beacon.yaml
- **THEN** system displays error indicating file is not tracked in beacon.yaml

#### Scenario: File matches warehouse
- **WHEN** user runs `abc delta` on file that matches warehouse
- **THEN** system displays message "No differences" for that file

### Requirement: Hash-based comparison for summary
The system SHALL use file hash comparison for efficient summary view.

#### Scenario: Hash comparison detects changes
- **WHEN** local artifact has different hash than warehouse version
- **THEN** system categorizes as [Modified]

#### Scenario: Local-only artifact detected
- **WHEN** local artifact exists but not in warehouse
- **THEN** system categorizes as [Added] (local addition)

#### Scenario: Missing local artifact detected
- **WHEN** beacon.yaml lists artifact but not present locally
- **THEN** system categorizes as [Missing] (needs sync)

### Requirement: Git diff for detailed comparison
The system SHALL use git diff --no-index for detailed file comparison.

#### Scenario: Unified diff format
- **WHEN** user requests detailed diff for specific file
- **THEN** system uses `git diff --no-index` to show standard unified diff format

#### Scenario: Syntax highlighting in diff
- **WHEN** terminal supports color
- **THEN** diff output includes color highlighting for added/removed lines

### Requirement: Contribution workflow support
The system SHALL enable workflow for contributing local improvements back to warehouse.

#### Scenario: Review local changes before contributing
- **WHEN** user runs `abc delta` after making local improvements
- **THEN** user sees exactly what changed and can decide whether to contribute to warehouse

#### Scenario: Delta output guides manual contribution
- **WHEN** user sees [Modified] artifacts in delta output
- **THEN** user can manually copy changes to warehouse directory and commit

#### Scenario: Delta shows benefit of local changes
- **WHEN** developer tests improved instructions locally
- **THEN** `abc delta` helps review changes before proposing to team

### Requirement: Beacon.yaml-aware comparison
The system SHALL only compare artifacts listed in beacon.yaml, not all files.

#### Scenario: Ignores files not in beacon.yaml
- **WHEN** user has extra files in artifacts directory not in beacon.yaml
- **THEN** `abc delta` does not report those files

#### Scenario: Focuses on declared dependencies
- **WHEN** warehouse has 100 artifacts but beacon.yaml lists 10
- **THEN** `abc delta` only compares those 10 artifacts

### Requirement: Clear status indicators
The system SHALL use clear, consistent status indicators for different types of differences.

#### Scenario: Modified indicator
- **WHEN** local and warehouse versions differ
- **THEN** status shows `[Modified]` with file path

#### Scenario: Added indicator
- **WHEN** artifact exists locally but not in warehouse
- **THEN** status shows `[Added]` with file path

#### Scenario: Missing indicator
- **WHEN** artifact in beacon.yaml but not synced locally
- **THEN** status shows `[Missing]` with file path and suggestion to run `abc sync`
