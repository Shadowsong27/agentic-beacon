# legacy-agent-cleanup Specification

## Purpose
Defines the one-time-style migration cleanup that runs during `abc sync` to remove legacy global agent symlinks left over from the pre-PER-113 distribution model (where agents were installed into `~/.claude/agents/` and `~/.config/opencode/agents/`). Created by archiving change `unify-agent-distribution`.

## Requirements

### Requirement: Sync removes legacy global agent symlinks pointing into the warehouse

During `abc sync`, after the artifact symlinks under `.agentic-beacon/artifacts/` are reconciled and project-local agent wiring runs, the system SHALL scan `~/.claude/agents/` and `~/.config/opencode/agents/` non-recursively. For each entry that is a symlink whose `resolve(strict=False)` target is under the connected warehouse's `agents/` directory, the system SHALL `unlink` it and increment a counter. After the scan, if the counter is greater than zero, the system SHALL print a single-line user-visible notice of the form `Cleaned up <N> legacy global agent symlinks (PER-113 migration).` to stdout. The cleanup SHALL be idempotent — subsequent invocations find no matching symlinks and print nothing.

#### Scenario: Pre-existing legacy symlink in ~/.claude/agents/ pointing into warehouse
- **WHEN** `~/.claude/agents/spec-planner.md` is a symlink whose target resolves to `<warehouse>/agents/spec-planner.md` AND `abc sync` is run
- **THEN** the symlink is removed and the counter increments by 1

#### Scenario: Pre-existing legacy symlink in ~/.config/opencode/agents/
- **WHEN** `~/.config/opencode/agents/spec-planner.md` is a symlink whose target resolves into the warehouse's `agents/` directory AND `abc sync` is run
- **THEN** the symlink is removed and the counter increments

#### Scenario: Symlink pointing outside the warehouse is preserved
- **WHEN** `~/.claude/agents/foo.md` is a symlink whose target is `/tmp/elsewhere.md` (not under the warehouse) AND `abc sync` is run
- **THEN** the symlink is left untouched; the counter does not change

#### Scenario: Regular file is preserved
- **WHEN** `~/.claude/agents/handcrafted.md` exists as a regular file (not a symlink) AND `abc sync` is run
- **THEN** the file is left untouched; the counter does not change

#### Scenario: Missing tool directory tolerated
- **WHEN** `~/.config/opencode/agents/` does not exist on the user's machine AND `abc sync` is run
- **THEN** the cleanup skips that directory without error

#### Scenario: Dangling symlink whose target path resolves into the warehouse
- **WHEN** a symlink at `~/.claude/agents/dangling.md` points at `<warehouse>/agents/nonexistent.md` (path resolves under `warehouse/agents/` but the file itself does not exist)
- **THEN** the symlink is removed (its target path is under the warehouse's `agents/` even though the file is missing — `resolve(strict=False)` returns the canonical path regardless)

#### Scenario: Subdirectory entries not recursed
- **WHEN** `~/.claude/agents/` contains a subdirectory `~/.claude/agents/subdir/` with symlinks inside
- **THEN** the cleanup does not recurse into the subdirectory; nested entries are preserved

#### Scenario: User-visible notice
- **WHEN** the cleanup removed `N >= 1` symlinks during a sync invocation
- **THEN** stdout contains exactly one line `Cleaned up <N> legacy global agent symlinks (PER-113 migration).`

#### Scenario: Idempotent on subsequent runs
- **WHEN** `abc sync` is run a second time after a successful cleanup with no new legacy symlinks introduced between runs
- **THEN** the counter returns 0 and no notice is printed
