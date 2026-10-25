# warehouse-contribute-command Specification

## Purpose
Define the `abc warehouse contribute` command, the sole write entrypoint for promoting local harness edits back to the shared warehouse. Invoked from any beacon-configured project directory, it resolves the configured warehouse clone and wraps `git add` + `git commit` (and optionally `git push`) inside that clone. It replaces the removed project-scoped `abc contribute` command, which is no longer meaningful under the symlink model where the project and warehouse share the same on-disk files.

## Requirements

### Requirement: `abc warehouse contribute` stages and commits warehouse changes
The system SHALL provide an `abc warehouse contribute` command that, when invoked from any project directory configured with a warehouse, stages and commits uncommitted changes inside the warehouse clone's working tree.

#### Scenario: Contribute from project commits warehouse changes
- **WHEN** a user has edited a synced artifact (via its project symlink) and runs `abc warehouse contribute -m "improve skill"` from inside the project
- **THEN** the system runs `git add` and `git commit` inside the warehouse clone and the commit contains the edited file

#### Scenario: Contribute with no warehouse changes exits cleanly
- **WHEN** user runs `abc warehouse contribute` and the warehouse working tree has no uncommitted changes
- **THEN** the system reports that there is nothing to contribute and exits with status zero

### Requirement: Contribute resolves the warehouse path from project config
The system SHALL resolve the target warehouse clone by reading the current project's `.agentic-beacon/config.toml`, the same mechanism used by `abc sync`.

#### Scenario: Project not connected to a warehouse
- **WHEN** user runs `abc warehouse contribute` in a directory that is not a beacon-configured project
- **THEN** the system exits with a non-zero status and an error message instructing the user to run `abc warehouse connect` first

#### Scenario: Configured warehouse path missing
- **WHEN** user runs `abc warehouse contribute` and the configured warehouse path does not exist on disk
- **THEN** the system exits with a non-zero status and an error message naming the missing path

### Requirement: Commit message handling
The system SHALL accept a commit message via a `-m/--message` flag and SHALL reject the command when neither a message flag nor an existing staged commit template is supplied.

#### Scenario: Commit message provided via flag
- **WHEN** user runs `abc warehouse contribute -m "add lesson"`
- **THEN** the resulting warehouse commit uses exactly that message

#### Scenario: Missing commit message
- **WHEN** user runs `abc warehouse contribute` without `-m/--message`
- **THEN** the system exits with a non-zero status and an error indicating a commit message is required

### Requirement: Optional push to warehouse remote
The system SHALL support a `--push` flag that, after a successful commit, pushes the warehouse branch to its configured remote.

#### Scenario: Push flag pushes after commit
- **WHEN** user runs `abc warehouse contribute -m "msg" --push`
- **THEN** the system performs the commit and then runs `git push` inside the warehouse clone

#### Scenario: Push fails after successful commit
- **WHEN** `abc warehouse contribute --push` successfully commits but `git push` fails
- **THEN** the system reports the push failure, leaves the commit in place, and exits with a non-zero status

### Requirement: No project-level contribute fallback
The system SHALL NOT provide a project-scoped `abc contribute` command; contribute is exclusively a warehouse-level operation.

#### Scenario: Legacy `abc contribute` is not recognized
- **WHEN** user runs `abc contribute` after upgrading
- **THEN** the system exits with a non-zero status and an error directing the user to `abc warehouse contribute`
