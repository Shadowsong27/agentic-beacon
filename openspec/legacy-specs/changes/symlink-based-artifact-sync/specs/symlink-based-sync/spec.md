# symlink-based-sync

## ADDED Requirements

### Requirement: Symlink creation from project to warehouse
The system SHALL create filesystem symlinks from the project's `.agentic-beacon/artifacts/` tree to the corresponding paths inside the locally cloned warehouse, one symlink per artifact entry expanded from `beacon.yaml`.

#### Scenario: Sync creates symlinks for declared artifacts
- **WHEN** user runs `abc sync` in a project whose `beacon.yaml` lists `skills/foo/SKILL.md`
- **THEN** the system creates `.agentic-beacon/artifacts/skills/foo/SKILL.md` as a symlink whose target is the absolute path to that file inside the local warehouse clone

#### Scenario: Symlink targets use absolute paths
- **WHEN** the system creates a symlink for any synced artifact
- **THEN** the symlink target is an absolute filesystem path to the warehouse clone

#### Scenario: Symlink reflects warehouse edits immediately
- **WHEN** a user edits an artifact file inside the warehouse clone
- **THEN** reading the same path through the project's `.agentic-beacon/artifacts/` returns the edited content without any further sync

### Requirement: Single on-disk source of truth
The system SHALL ensure that every artifact listed in `beacon.yaml` resolves to exactly one physical file on disk — the file inside the warehouse clone — shared by all projects that sync from the same warehouse.

#### Scenario: Edits via any project modify the warehouse file
- **WHEN** a user or agent modifies `.agentic-beacon/artifacts/skills/foo/SKILL.md` in any project synced from warehouse W
- **THEN** the change is visible through the warehouse clone's working tree and to any other project symlinked to the same file

#### Scenario: No duplicate copies created during sync
- **WHEN** `abc sync` completes successfully
- **THEN** the system has not created any regular-file duplicate of any artifact listed in `beacon.yaml`

### Requirement: Warehouse clone required for sync
The system SHALL require a local git clone of the warehouse at sync time and SHALL refuse to sync when none is present or reachable.

#### Scenario: Missing warehouse path aborts sync
- **WHEN** user runs `abc sync` and `.agentic-beacon/config.toml` does not reference an existing local warehouse clone
- **THEN** the system exits with a non-zero status and an error message instructing the user to run `abc warehouse connect` with a local path

#### Scenario: Warehouse path exists but is not a git working tree
- **WHEN** user runs `abc sync` and the configured warehouse path exists but is not a git repository
- **THEN** the system exits with a non-zero status and an error message indicating the path is not a valid warehouse clone

### Requirement: Symlink targets must resolve inside the warehouse clone
The system SHALL refuse to create any symlink whose resolved target path does not live under the configured warehouse clone root.

#### Scenario: Out-of-warehouse target aborts sync
- **WHEN** a `beacon.yaml` entry resolves to a filesystem path that is not a descendant of the configured warehouse clone root
- **THEN** `abc sync` exits with a non-zero status and an error naming the offending entry and the resolved path, and creates no symlinks for that entry

#### Scenario: Partial sync is not performed on out-of-warehouse targets
- **WHEN** one entry resolves outside the warehouse while others resolve inside
- **THEN** the system aborts before creating any symlinks so the tree does not end up partially materialized

### Requirement: Idempotent link sync
The system SHALL make `abc sync` idempotent for symlinks — re-running with no warehouse or `beacon.yaml` changes SHALL not modify any filesystem entry.

#### Scenario: Sync twice produces identical state
- **WHEN** user runs `abc sync` twice in a row with no changes to `beacon.yaml` or the warehouse layout
- **THEN** the second run makes no filesystem changes and reports that links are up to date

#### Scenario: Sync repairs broken symlink
- **WHEN** a symlink in `.agentic-beacon/artifacts/` has been deleted or points to a non-existent target and user runs `abc sync`
- **THEN** the system recreates the symlink to the correct warehouse path

#### Scenario: Sync removes symlinks for dropped artifacts
- **WHEN** an artifact entry is removed from `beacon.yaml` and user runs `abc sync`
- **THEN** the system removes the corresponding symlink under `.agentic-beacon/artifacts/` and does not touch the warehouse file

### Requirement: Glob expansion during link sync
The system SHALL expand glob patterns in `beacon.yaml` against the warehouse working tree and SHALL create one symlink per matched file.

#### Scenario: Glob matches multiple files
- **WHEN** `beacon.yaml` contains `knowledge/languages/**/*.md` and the warehouse has ten matching files
- **THEN** the system creates ten symlinks, one per matched file, preserving the directory structure under `.agentic-beacon/artifacts/`

#### Scenario: Glob matches no files
- **WHEN** `beacon.yaml` contains a glob pattern that matches no files in the warehouse
- **THEN** the system emits a warning naming the pattern and continues with the remaining entries

### Requirement: Directory structure preserved via symlinks or real directories
The system SHALL preserve the warehouse directory structure for synced artifacts by creating real directories under `.agentic-beacon/artifacts/` and placing per-file symlinks inside them.

#### Scenario: Nested directories created as real directories
- **WHEN** `beacon.yaml` includes `knowledge/languages/python/lessons.md`
- **THEN** the system creates `.agentic-beacon/artifacts/knowledge/`, `languages/`, and `python/` as real directories and places the symlink at `lessons.md` inside them

#### Scenario: Directories are not themselves symlinked
- **WHEN** the system syncs artifacts
- **THEN** no intermediate directory under `.agentic-beacon/artifacts/` is a symlink; only leaf artifact files are symlinks

### Requirement: Sync does not pull warehouse git state
The system SHALL NOT run `git pull` or any other git state-advancing operation in the warehouse clone as part of `abc sync`.

#### Scenario: Sync runs against stale warehouse
- **WHEN** user runs `abc sync` and the warehouse clone is behind its remote
- **THEN** the system creates links against the current local warehouse state and does not attempt to pull the remote

### Requirement: Windows platform rejected
The system SHALL refuse to run `abc sync` on Windows hosts and SHALL emit a clear error directing the user to macOS or Linux.

#### Scenario: Sync on Windows exits with error
- **WHEN** user runs `abc sync` on a Windows host
- **THEN** the system exits with a non-zero status and an error message stating that Windows is not supported

#### Scenario: No fallback to copy or hardlink on Windows
- **WHEN** `abc sync` fails because the host is Windows
- **THEN** the system does not attempt to fall back to copy-based or hardlink-based distribution
