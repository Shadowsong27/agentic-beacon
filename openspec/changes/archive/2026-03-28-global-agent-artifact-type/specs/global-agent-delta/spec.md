## ADDED Requirements

### Requirement: Delta compares warehouse agents against global install directories
`abc delta` SHALL include agent files from the warehouse's `agents/` directory in its comparison output, comparing each against the corresponding file in globally detected agent directories (`~/.config/opencode/agents/<name>.md` and `~/.claude/agents/<name>.md`). No artifact snapshot (`.agentic-beacon/artifacts/`) is used for agents.

#### Scenario: Agent in warehouse not globally installed
- **WHEN** `agents/<name>.md` exists in the warehouse but not in any detected global agent directory
- **THEN** delta reports `MISSING` for that agent

#### Scenario: Agent globally installed with matching content
- **WHEN** `agents/<name>.md` exists in the warehouse AND the globally installed file has identical content
- **THEN** delta reports `IN SYNC` for that agent

#### Scenario: Agent globally installed with different content
- **WHEN** `agents/<name>.md` exists in the warehouse AND the globally installed file exists but has different content
- **THEN** delta reports `MODIFIED` for that agent

#### Scenario: No agents directory in warehouse
- **WHEN** the warehouse has no `agents/` directory or it is empty
- **THEN** delta output contains no agent entries (no error is raised)

### Requirement: Delta reports per-tool agent status
When multiple agent tools are detected globally (OpenCode and Claude Code), delta SHALL report the status for each tool separately, so a developer can see if only one tool's installation is out of date.

#### Scenario: One tool in sync, other modified
- **WHEN** `~/.config/opencode/agents/<name>.md` matches the warehouse AND `~/.claude/agents/<name>.md` differs
- **THEN** delta shows `IN SYNC` for opencode and `MODIFIED` for claudecode for that agent

### Requirement: Delta agent comparison uses DeltaComparator with global live paths
The delta logic SHALL route the `agents/` path prefix to a new `_agent_live_path()` helper (analogous to `_skill_live_path()`) that resolves global home-directory paths, rather than the project-relative `artifacts_path`.

#### Scenario: Agent comparison uses home directory paths
- **WHEN** `compare_file()` is called with a path starting with `agents/`
- **THEN** it resolves the live path using `_agent_live_path()` pointing to `~/.config/opencode/agents/` or `~/.claude/agents/`, not the local artifacts directory
