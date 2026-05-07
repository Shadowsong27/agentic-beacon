## ADDED Requirements

### Requirement: Sync removes legacy global agent symlinks pointing into the warehouse

During `abc sync`, the system SHALL scan `~/.claude/agents/` and `~/.config/opencode/agents/` for entries that are symlinks whose resolved target lies under `<warehouse>/agents/`, where `<warehouse>` is the connected warehouse root (read from `WorkspaceConfig().warehouse.local_path`). For each such entry, the system SHALL remove the symlink. The scan SHALL run after the project-local agent wiring step and before sync exits.

#### Scenario: Legacy symlink removed
- **WHEN** `~/.claude/agents/spec-planner.md` is a symlink whose target resolves to `<warehouse>/agents/spec-planner.md` AND `abc sync` is run
- **THEN** the symlink at `~/.claude/agents/spec-planner.md` is removed

#### Scenario: Non-warehouse symlink preserved
- **WHEN** `~/.claude/agents/my-personal-agent.md` is a symlink whose target lies outside the connected warehouse
- **THEN** the symlink is left in place

#### Scenario: Regular file preserved
- **WHEN** `~/.claude/agents/handcrafted.md` is a regular file (not a symlink)
- **THEN** the file is left in place

#### Scenario: Both tool dirs scanned
- **WHEN** legacy symlinks exist in both `~/.claude/agents/` and `~/.config/opencode/agents/`
- **THEN** both directories are scanned and matching symlinks in either are removed

#### Scenario: Tool directory does not exist
- **WHEN** `~/.config/opencode/agents/` does not exist on the user's machine
- **THEN** the scan skips that directory without error

### Requirement: Cleanup notice printed once when symlinks are removed

When the legacy-symlink cleanup removes one or more entries during `abc sync`, the system SHALL print exactly one line to stdout: `Cleaned up N legacy global agent symlinks (PER-113 migration).`, where N is the total count across both tool directories. When no entries are removed, the system SHALL print nothing about the cleanup.

#### Scenario: Cleanup with removals
- **WHEN** `abc sync` removes 3 legacy symlinks
- **THEN** stdout contains the line `Cleaned up 3 legacy global agent symlinks (PER-113 migration).`

#### Scenario: Cleanup with nothing to remove
- **WHEN** `abc sync` finds no legacy symlinks
- **THEN** no cleanup-related output is printed

#### Scenario: Idempotent on subsequent runs
- **WHEN** `abc sync` is run a second time after a prior cleanup completed
- **THEN** the second run prints no cleanup notice (nothing to remove)

### Requirement: Cleanup never touches files outside the configured tool directories

The cleanup SHALL only inspect entries directly inside `~/.claude/agents/` and `~/.config/opencode/agents/` (no recursion into subdirectories). The cleanup SHALL NOT remove files in any other location, including `~/.claude/`, `~/.config/opencode/`, or anywhere outside the user's home directory.

#### Scenario: Subdirectory symlink ignored
- **WHEN** `~/.claude/agents/subgroup/nested.md` is a symlink into the warehouse
- **THEN** it is not removed (cleanup does not recurse)

#### Scenario: Other home directories untouched
- **WHEN** the cleanup runs
- **THEN** files in `~/.claude/skills/`, `~/.config/opencode/skills/`, `~/.claude/CLAUDE.md`, and any other location are not inspected or modified
