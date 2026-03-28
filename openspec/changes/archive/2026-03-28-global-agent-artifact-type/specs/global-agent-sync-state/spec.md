## ADDED Requirements

### Requirement: Global sync state file tracks agent installations
After a successful `abc install agents/<name>.md`, the CLI SHALL write a record to `~/.config/agentic-beacon/sync-state.json` capturing the warehouse path, the installed file's content hash, and the warehouse HEAD SHA at install time. This state is used by `abc delta` to show meaningful per-agent status.

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

### Requirement: abc delta uses global sync state for agent status
When `abc delta` evaluates agent entries, it SHALL read `~/.config/agentic-beacon/sync-state.json` to enrich per-tool status output. If the recorded warehouse HEAD differs from the current warehouse HEAD, the delta output SHALL indicate the installation is potentially stale.

#### Scenario: Recorded warehouse HEAD matches current — IN SYNC
- **WHEN** the global agent file content matches the warehouse AND the recorded warehouse HEAD matches the current HEAD
- **THEN** delta reports `IN SYNC`

#### Scenario: Recorded warehouse HEAD differs — STALE
- **WHEN** the global agent file content matches the warehouse file content AND the recorded warehouse HEAD differs from the current warehouse HEAD
- **THEN** delta reports `STALE` (warehouse has moved on but global file hasn't been re-installed)

#### Scenario: Content differs — MODIFIED
- **WHEN** the global agent file content differs from the warehouse file content
- **THEN** delta reports `MODIFIED` regardless of HEAD comparison

#### Scenario: No state file — treated as untracked
- **WHEN** `~/.config/agentic-beacon/sync-state.json` does not exist or has no entry for an agent
- **THEN** delta falls back to content comparison only (no STALE detection)
