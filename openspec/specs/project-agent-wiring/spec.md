# project-agent-wiring Specification

## Purpose
Defines how `abc sync` and `abc adopt` create and remove project-local agent symlinks under `.claude/agents/` and `.opencode/agents/`, plus the related `.gitignore` and `abc list` behavior introduced by PER-113. Created by archiving change `unify-agent-distribution`.

## Requirements

### Requirement: Sync wires declared agents into project-local tool directories

During `abc sync`, after symlinking declared agents from `<warehouse>/agents/<name>.md` into `.agentic-beacon/artifacts/agents/<name>.md`, the system SHALL create symlinks at `.claude/agents/<name>.md` and `.opencode/agents/<name>.md` pointing at the corresponding `.agentic-beacon/artifacts/agents/<name>.md` file. Wiring SHALL be gated by `detect_agent_targets()` — only the tool directories that the project has configured (`.claude/` and/or `.opencode/`) receive symlinks.

#### Scenario: Both tools configured
- **WHEN** the project has both `.claude/` and `.opencode/` directories AND `beacon.yaml.artifacts.agents` lists `agents/spec-planner.md`
- **THEN** `abc sync` creates symlinks at `.claude/agents/spec-planner.md` and `.opencode/agents/spec-planner.md`, both pointing at `.agentic-beacon/artifacts/agents/spec-planner.md`

#### Scenario: Only Claude Code configured
- **WHEN** the project has `.claude/` but not `.opencode/` AND `beacon.yaml.artifacts.agents` lists `agents/spec-planner.md`
- **THEN** `abc sync` creates a symlink only at `.claude/agents/spec-planner.md`

#### Scenario: Neither tool configured
- **WHEN** the project has neither `.claude/` nor `.opencode/` AND `beacon.yaml.artifacts.agents` lists `agents/spec-planner.md`
- **THEN** `abc sync` creates the artifact symlink at `.agentic-beacon/artifacts/agents/spec-planner.md` but no project-local tool symlinks; no error is raised

#### Scenario: Parent directories created
- **WHEN** wiring an agent and the target tool directory (`.claude/agents/` or `.opencode/agents/`) does not yet exist
- **THEN** the directory is created automatically before the symlink is written

### Requirement: Sync unwires pruned agents

During `abc sync`, when an agent is no longer declared in `beacon.yaml.artifacts.agents` (i.e., the entry was removed since the previous sync), the system SHALL remove the project-local symlinks at `.claude/agents/<name>.md` and `.opencode/agents/<name>.md`, in addition to removing the artifact symlink at `.agentic-beacon/artifacts/agents/<name>.md`. The `unwire_pruned_artifacts` mechanism SHALL be extended to handle `artifact_type == "agents"`.

#### Scenario: Agent removed from beacon.yaml
- **WHEN** `beacon.yaml.artifacts.agents` previously contained `agents/spec-planner.md` and the entry is removed AND `abc sync` is run
- **THEN** `.claude/agents/spec-planner.md`, `.opencode/agents/spec-planner.md`, and `.agentic-beacon/artifacts/agents/spec-planner.md` are all removed

#### Scenario: Pruned agent had no tool symlinks
- **WHEN** the project never had `.claude/` or `.opencode/` and an agent is removed from `beacon.yaml`
- **THEN** only the artifact symlink is removed; no error is raised for missing tool symlinks

### Requirement: Adoption accept wires agents immediately

When `abc adopt` accepts an agent (action: `accept`), the system SHALL append the warehouse-relative path (`agents/<name>.md`) to `beacon.yaml.artifacts.agents`, create the artifact symlink at `.agentic-beacon/artifacts/agents/<name>.md`, AND wire the symlinks at `.claude/agents/<name>.md` and `.opencode/agents/<name>.md` (gated by `detect_agent_targets()`), as part of the atomic adopt commit. The user SHALL NOT need to run `abc sync` separately to see the agent become available.

#### Scenario: Accept wires immediately
- **WHEN** the user marks `agents/spec-planner.md` as `accept` in `abc adopt` and confirms the commit
- **THEN** `beacon.yaml.artifacts.agents` includes `agents/spec-planner.md`, `.agentic-beacon/artifacts/agents/spec-planner.md` exists, and the project-local tool symlinks (for whichever tools are configured) exist — all written in the same atomic commit

#### Scenario: Accept rolls back on failure
- **WHEN** the wiring step fails mid-commit (e.g., I/O error writing one of the tool symlinks)
- **THEN** `beacon.yaml`, `pending.yaml`, the artifact symlink, and any partially-created tool symlinks are restored to their pre-commit state

### Requirement: Adoption reject unwires agents immediately

When `abc adopt` rejects an agent (action: `reject`), the system SHALL remove the entry from `beacon.yaml.artifacts.agents` (if present), remove the artifact symlink at `.agentic-beacon/artifacts/agents/<name>.md`, AND remove the project-local symlinks at `.claude/agents/<name>.md` and `.opencode/agents/<name>.md`, as part of the atomic adopt commit. Reject SHALL NOT mutate any file in `~/.claude/agents/` or `~/.config/opencode/agents/`.

#### Scenario: Reject removes wiring
- **WHEN** the user marks an already-wired `agents/spec-planner.md` as `reject` in `abc adopt` and confirms
- **THEN** `beacon.yaml`, `.agentic-beacon/artifacts/agents/spec-planner.md`, `.claude/agents/spec-planner.md`, and `.opencode/agents/spec-planner.md` are all cleaned up

#### Scenario: Reject does not touch home directory
- **WHEN** any reject action runs
- **THEN** no file under `~/.claude/agents/` or `~/.config/opencode/agents/` is created, modified, or removed

### Requirement: Defer is a no-op for agents

When `abc adopt` defers an agent (action: `defer`, the default), the system SHALL leave `beacon.yaml`, the artifact symlink, and any project-local tool symlinks unchanged for that entry.

#### Scenario: Defer leaves state untouched
- **WHEN** the user marks `agents/spec-planner.md` as `defer` in `abc adopt`
- **THEN** the entry remains in `pending.yaml`; no symlinks are created or removed

### Requirement: abc setup adds agent directories to .gitignore

`abc setup` (or, post-PR-109 round 6, `abc sync` and `abc adopt` accept whenever agents are first declared) SHALL ensure the project's root `.gitignore` contains `.claude/agents/` and `.opencode/agents/` entries, creating the file if it does not exist and appending entries idempotently. The `update_agent_gitignores` helper SHALL be gated on declared/accepted agents so contexts-only or skills-only projects are not modified.

#### Scenario: Fresh project — .gitignore created
- **WHEN** `abc sync` runs against a project that declares one or more agents and has no `.gitignore`
- **THEN** a `.gitignore` is created containing `.claude/agents/` and `.opencode/agents/`

#### Scenario: Existing .gitignore — entries appended
- **WHEN** `abc sync` runs in a project with an existing `.gitignore` that does not include the agent entries AND agents are declared
- **THEN** `.claude/agents/` and `.opencode/agents/` are appended to the file; existing entries are preserved

#### Scenario: Idempotent re-run
- **WHEN** `abc sync` runs twice in sequence with agents declared
- **THEN** the agent entries appear exactly once in `.gitignore`

#### Scenario: Skills-only or contexts-only sync does not touch .gitignore
- **WHEN** `abc sync` runs in a project with `beacon.yaml.artifacts.agents: []`
- **THEN** the project root `.gitignore` is not modified by the agent-gitignore helper

### Requirement: abc list agents reads project-declared agents

`abc list agents` SHALL read `.agentic-beacon/artifacts/agents/` (the project artifact directory) and list the agents present there, mirroring the format used by `abc list skills` and `abc list contexts`. The command SHALL NOT read `~/.claude/agents/` or `~/.config/opencode/agents/`. When no agents are present at the project artifact path, the command SHALL distinguish "no agents declared in beacon.yaml" from "agents declared but not synced" so the user gets an actionable next step.

#### Scenario: Project has wired agents
- **WHEN** `.agentic-beacon/artifacts/agents/` contains `spec-planner.md` and `code-reviewer.md`
- **THEN** `abc list agents` lists both agents

#### Scenario: No agents declared
- **WHEN** `.agentic-beacon/artifacts/agents/` is empty AND `beacon.yaml.artifacts.agents` is empty or absent
- **THEN** `abc list agents` prints "No agents declared in beacon.yaml" with a hint to run `abc adopt`

#### Scenario: Agents declared but not synced
- **WHEN** `.agentic-beacon/artifacts/agents/` is empty AND `beacon.yaml.artifacts.agents` is non-empty
- **THEN** `abc list agents` prints how many agents are declared and a hint to run `abc sync`

#### Scenario: Global agent dirs ignored
- **WHEN** `~/.claude/agents/` contains files but `.agentic-beacon/artifacts/agents/` is empty
- **THEN** `abc list agents` reports no agents — global directories are not read
