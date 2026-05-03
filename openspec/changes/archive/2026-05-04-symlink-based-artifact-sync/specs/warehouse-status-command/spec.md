# warehouse-status-command

## ADDED Requirements

### Requirement: `abc warehouse status` shows warehouse working-tree state
The system SHALL provide an `abc warehouse status` command that reports uncommitted changes in the warehouse clone's working tree, scoped to artifacts referenced by the current project's `beacon.yaml`.

#### Scenario: Status shows uncommitted artifact edits
- **WHEN** a user has edited a synced artifact via its project symlink and runs `abc warehouse status` from the project directory
- **THEN** the system lists that file as modified, using paths relative to the warehouse root

#### Scenario: Clean warehouse reports no changes
- **WHEN** user runs `abc warehouse status` and the warehouse working tree has no uncommitted changes to files referenced by the project
- **THEN** the system reports that the warehouse is clean for this project's artifacts

### Requirement: Status reports unpushed commits
The system SHALL report commits present in the warehouse's current branch that are ahead of the branch's upstream remote.

#### Scenario: Warehouse ahead of remote
- **WHEN** user runs `abc warehouse status` and the warehouse branch is two commits ahead of its upstream
- **THEN** the system reports the number of unpushed commits and suggests `abc warehouse contribute --push` or `git push`

#### Scenario: No upstream configured
- **WHEN** the warehouse branch has no upstream configured
- **THEN** the system reports that the branch has no upstream and does not fail

### Requirement: Detailed diff for a specific artifact
The system SHALL accept an optional file path argument and SHALL produce a unified diff (via `git diff`) for that file inside the warehouse clone.

#### Scenario: Status with file path shows diff
- **WHEN** user runs `abc warehouse status knowledge/languages/python/lessons.md`
- **THEN** the system displays the unified diff of uncommitted changes to that file inside the warehouse

#### Scenario: File not tracked by beacon.yaml
- **WHEN** user passes a path that is not listed or matched by `beacon.yaml`
- **THEN** the system exits with a non-zero status and an error indicating the file is not tracked

### Requirement: No project-vs-warehouse delta
The system SHALL NOT compute or report differences between the project's `.agentic-beacon/artifacts/` tree and the warehouse, because under the symlink model they share the same on-disk files.

#### Scenario: Legacy `abc delta` is not recognized
- **WHEN** user runs `abc delta` after upgrading
- **THEN** the system exits with a non-zero status and an error directing the user to `abc warehouse status`
