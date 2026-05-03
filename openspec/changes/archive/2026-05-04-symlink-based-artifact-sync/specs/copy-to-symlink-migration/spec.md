# copy-to-symlink-migration

## ADDED Requirements

### Requirement: Detect pre-existing copy-based artifact tree
The system SHALL detect when `.agentic-beacon/artifacts/` contains regular files (not symlinks) at paths where the new symlink-based sync would place links, and SHALL treat this as a legacy copy-based tree requiring migration.

#### Scenario: Regular files under artifacts trigger migration mode
- **WHEN** user runs `abc sync` and any file in `.agentic-beacon/artifacts/` matched by `beacon.yaml` is a regular file
- **THEN** the system enters migration mode instead of proceeding directly to symlink creation

#### Scenario: Fully symlinked tree skips migration
- **WHEN** user runs `abc sync` and every `beacon.yaml`-matched entry under `.agentic-beacon/artifacts/` is already a symlink (or absent)
- **THEN** the system proceeds with normal symlink sync and does not emit migration prompts

### Requirement: Surface local changes before conversion
The system SHALL, in migration mode, compare each legacy copy against its corresponding warehouse file and SHALL surface any differences to the user before replacing the copy with a symlink.

#### Scenario: Modified legacy copy detected
- **WHEN** migration mode runs and a legacy copy differs from the warehouse file
- **THEN** the system prints a unified diff (or summary) for that file and prompts the user to choose between `contribute` (copy local content into the warehouse working tree) and `discard` (drop local content, use warehouse version)

#### Scenario: Unchanged legacy copy converted silently
- **WHEN** migration mode runs and a legacy copy is byte-identical to the warehouse file
- **THEN** the system replaces the copy with a symlink without prompting

### Requirement: Contribute-or-discard resolution
The system SHALL apply the user's chosen resolution per file before creating the symlink.

#### Scenario: Contribute resolution writes to warehouse
- **WHEN** the user selects `contribute` for a modified legacy copy
- **THEN** the system writes the legacy copy's content into the warehouse file (leaving it as an uncommitted change in the warehouse working tree) and then replaces the legacy copy with a symlink pointing to that warehouse file

#### Scenario: Discard resolution drops local content
- **WHEN** the user selects `discard` for a modified legacy copy
- **THEN** the system deletes the legacy copy and creates a symlink to the warehouse file without modifying the warehouse content

### Requirement: Migration is one-shot and resumable
The system SHALL complete migration in a single `abc sync` invocation when the user answers all prompts, and SHALL leave the tree in a consistent mixed state that can be resumed if the user aborts.

#### Scenario: User aborts mid-migration
- **WHEN** the user aborts `abc sync` during migration prompts
- **THEN** already-resolved files remain as symlinks, unresolved files remain as regular files, and a subsequent `abc sync` resumes migration for the remaining files

#### Scenario: Migration completes converts all matched files
- **WHEN** migration mode runs to completion
- **THEN** every `beacon.yaml`-matched file under `.agentic-beacon/artifacts/` is a symlink pointing to the warehouse

### Requirement: Non-interactive migration is disallowed without explicit flag
The system SHALL refuse to auto-resolve modified legacy copies without explicit user instruction.

#### Scenario: Non-TTY without flag refuses to migrate modified copies
- **WHEN** `abc sync` runs in a non-interactive environment (no TTY) and encounters modified legacy copies without `--discard-local` or `--contribute-local` flags
- **THEN** the system exits with a non-zero status and an error listing the modified files and instructing the user to rerun interactively or with an explicit flag

#### Scenario: `--discard-local` resolves all modified copies to discard
- **WHEN** `abc sync --discard-local` runs
- **THEN** every modified legacy copy is treated as `discard` and converted to a symlink pointing at the warehouse file

#### Scenario: `--contribute-local` resolves all modified copies to contribute
- **WHEN** `abc sync --contribute-local` runs
- **THEN** every modified legacy copy's content is written into the warehouse working tree and then the path becomes a symlink
