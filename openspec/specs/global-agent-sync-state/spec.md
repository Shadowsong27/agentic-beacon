# global-agent-sync-state Specification

## Purpose

After a successful `abc install agents/<name>.md`, the CLI records installation state to a global sync-state file so that later invocations of `abc install` (and any future global-agent inspection tool) can detect whether the installed file is unchanged, modified, or stale relative to the warehouse.

> Historical context: earlier versions of this spec described `abc delta` consuming this state. `abc delta` has been removed (see `knowledge/decisions/single-warehouse-write-entrypoint.md`); the state file remains because `abc install` still tracks global agent installations, which live outside the warehouse tree and therefore cannot be symlinked.

## Requirements

### Requirement: Global sync state file tracks agent installations

After a successful `abc install agents/<name>.md`, the CLI SHALL write a record to `~/.config/agentic-beacon/sync-state.json` capturing the warehouse path, the installed file's content hash, and the warehouse HEAD SHA at install time.

#### Scenario: State written after successful agent install
- **WHEN** `abc install agents/<name>.md` completes without error
- **THEN** `~/.config/agentic-beacon/sync-state.json` contains an entry for that agent under the warehouse path key, with fields: `content_hash`, `warehouse_head`, `installed_at`

#### Scenario: State file created if absent
- **WHEN** `~/.config/agentic-beacon/sync-state.json` does not exist at install time
- **THEN** the file and its parent directory are created automatically

#### Scenario: State updated on reinstall
- **WHEN** `abc install agents/<name>.md` is run again (overwrite or no-op)
- **THEN** the existing state entry is updated with the new hashes and timestamp

#### Scenario: State not written on skipped install
- **WHEN** the agent install is skipped (content identical, or user answers N to soft block, or --preserve)
- **THEN** the existing state entry is unchanged

### Requirement: Global sync state is keyed per warehouse

The sync state file SHALL be organised by warehouse path so that a developer using multiple warehouses does not have state entries collide.

#### Scenario: Two warehouses, same agent name
- **WHEN** `abc install agents/code-reviewer.md` is run from two different warehouse connections
- **THEN** `sync-state.json` contains two separate entries under their respective warehouse path keys
