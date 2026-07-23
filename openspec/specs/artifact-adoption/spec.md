# artifact-adoption Specification

## Purpose
Define the `abc adopt` command for discovering and adopting warehouse artifacts into a project's beacon.yaml configuration.
## Requirements
### Requirement: Git-diff-based artifact discovery
The system SHALL discover warehouse artifacts added since the user's last sync by diffing the recorded sync-state SHA against the current warehouse HEAD, then filtering out artifacts already declared in `beacon.yaml`.

#### Scenario: New artifacts detected after warehouse update
- **WHEN** warehouse has 2 new contexts added since the user's last sync SHA and neither is in `beacon.yaml`
- **THEN** system returns both as adoption candidates with `is_new=True`

#### Scenario: Already adopted artifacts excluded
- **WHEN** warehouse has a new skill added since last sync but it is already in `beacon.yaml`
- **THEN** system does not include it in the adoption candidates

#### Scenario: No sync state exists
- **WHEN** user runs `abc adopt` and `.sync-state` file does not exist
- **THEN** system exits with error: "No sync baseline found. Run `abc sync` first to establish a warehouse cursor, then re-run `abc adopt`."

#### Scenario: No new artifacts since last sync
- **WHEN** warehouse HEAD matches sync-state SHA or diff contains no new artifact paths
- **THEN** system reports "All warehouse artifacts are already adopted" and exits cleanly

### Requirement: Full warehouse scan with --all flag
The system SHALL support a `--all` flag that scans the entire warehouse for artifacts not present in `beacon.yaml`, regardless of when they were added.

#### Scenario: All unadopted artifacts shown
- **WHEN** user runs `abc adopt --all` and warehouse has 5 artifacts total, 2 in `beacon.yaml`
- **THEN** system returns the remaining 3 as adoption candidates with `is_new=False`

#### Scenario: All already adopted
- **WHEN** user runs `abc adopt --all` and every warehouse artifact is in `beacon.yaml`
- **THEN** system reports "All warehouse artifacts are already adopted"

### Requirement: Artifact description extraction
The system SHALL extract human-readable descriptions from artifact content: SKILL.md frontmatter `description:` field for skills, first markdown heading for contexts and knowledge files.

#### Scenario: Skill description from SKILL.md
- **WHEN** a skill's SKILL.md contains YAML frontmatter with `description: Generate unit tests`
- **THEN** adoption candidate shows description "Generate unit tests"

#### Scenario: Context description from heading
- **WHEN** a context file starts with `# Platform Team Standards`
- **THEN** adoption candidate shows description "Platform Team Standards"

#### Scenario: No description available
- **WHEN** an artifact file has no extractable description
- **THEN** adoption candidate shows the file path as fallback with empty description

### Requirement: Updated artifact detection
The system SHALL detect artifacts that are already in `beacon.yaml` but have been modified in the warehouse since the last sync, and display them as informational (not selectable).

#### Scenario: Adopted artifact was modified
- **WHEN** `knowledge/python/async.md` is in `beacon.yaml` and was modified in warehouse since last sync
- **THEN** system shows it in an "Already adopted (updated)" section with a hint to run `abc sync`

### Requirement: Interactive TUI for artifact selection
The system SHALL launch a textual-based full-screen TUI application that displays adoption candidates as categorized checkboxes for contexts, skills, and agents, with descriptions, allowing toggle selection. Knowledge is NOT a selectable category in the TUI; knowledge is derived at sync time from adopted contexts and skills.

Agents are project-scoped selectable candidates. Selecting an agent in the TUI SHALL:
1. Queue the agent for recording in `beacon.yaml.artifacts.agents`.
2. Queue the agent for global installation into `~/.config/opencode/agents/` and `~/.claude/agents/` per the existing `global-agent-install` behaviour.
3. Auto-tick every skill listed in the agent's `skills:` entry in `<warehouse>/agents/agents.yaml`, with a visual provenance marker on each auto-ticked skill indicating which agent(s) require it.

The TUI SHALL enforce a hard-lock: while any ticked agent requires a given skill, that skill's checkbox SHALL be non-togglable (attempts to untick are refused with a visible status message indicating which agent(s) require it). To remove the skill, the user MUST first untick all requiring agents.

#### Scenario: TUI displays categorized candidates
- **WHEN** there are 2 context candidates, 1 skill candidate, and 1 agent candidate
- **THEN** TUI shows "Contexts", "Skills", and "Agents" sections with their respective checkboxes; no "Knowledge" section appears

#### Scenario: Select all via keybinding
- **WHEN** user presses `a` in the TUI
- **THEN** all checkboxes are toggled on; auto-tick propagation runs for every selected agent

#### Scenario: Select none via keybinding
- **WHEN** user presses `n` in the TUI
- **THEN** all checkboxes are toggled off; no auto-tick locks remain

#### Scenario: Confirm selection
- **WHEN** user presses `Enter` with 2 items checked
- **THEN** TUI exits and returns the 2 selected artifact paths, grouped by type

#### Scenario: Cancel selection
- **WHEN** user presses `Escape` or `q`
- **THEN** TUI exits with no selection and no modifications are made

#### Scenario: Ticking an agent auto-ticks its required skills
- **WHEN** the user ticks agent `spec-planner`, and `agents.yaml` lists `spec-planner.skills = [opsx-enhance-tasks]`
- **THEN** skill `opsx-enhance-tasks` is immediately ticked in the same screen, with a provenance marker `required by spec-planner`

#### Scenario: Multiple agents require the same skill
- **WHEN** the user ticks `spec-planner` and `registra-developer`, both of which require `opsx-enhance-tasks`
- **THEN** the skill `opsx-enhance-tasks` shows provenance `required by spec-planner, registra-developer`

#### Scenario: Unticking a required skill is blocked
- **WHEN** `opsx-enhance-tasks` is ticked via agent-requirement and the user attempts to untick it while `spec-planner` is still ticked
- **THEN** the TUI refuses the toggle, displays a message "Required by: spec-planner — untick agent first", and leaves the skill ticked

#### Scenario: Unticking the last requiring agent releases the skill
- **WHEN** `spec-planner` is the only agent requiring `opsx-enhance-tasks`, and the user unticks `spec-planner`
- **THEN** the skill `opsx-enhance-tasks` becomes togglable; if the user never explicitly ticked it, it is auto-unticked; if the user had explicitly ticked it before ticking the agent, it remains ticked

#### Scenario: Malformed warehouse blocks adopt TUI
- **WHEN** the connected warehouse has an invalid `agents.yaml` (missing entry for an existing agent file, orphan entry for a non-existent agent file, an agent's declared skill missing from the warehouse, or a leftover `requires:` block in an agent's frontmatter) and the user runs `abc adopt`
- **THEN** the command validates the warehouse using the same validators invoked by `abc warehouse status`, exits non-zero with the same error output (including the migration document URL), and the TUI is never rendered

### Requirement: Non-interactive fallback
The system SHALL detect non-TTY environments and fall back to printing the adoptable artifacts list with instructions to edit `beacon.yaml` manually.

#### Scenario: Piped output
- **WHEN** `abc adopt` runs in a non-interactive terminal (stdin is not a TTY)
- **THEN** system prints the list of adoptable artifacts and exits without launching TUI

### Requirement: Dry run preview
The system SHALL support a `--dry-run` flag that lists adoptable artifacts without modifying `beacon.yaml`, syncing, or wiring.

#### Scenario: Dry run shows candidates
- **WHEN** user runs `abc adopt --dry-run` and there are 3 adoptable artifacts
- **THEN** system prints a table of candidates grouped by type and exits without changes

### Requirement: beacon.yaml update on adoption
The system SHALL append selected artifact paths to the appropriate `artifacts.<type>` list in `beacon.yaml` after user confirms selection. The permitted types are `contexts`, `skills`, and `agents`; knowledge is never written to `beacon.yaml`.

Agent adoption SHALL:
1. Append `agents/<name>.md` to `beacon.yaml.artifacts.agents`.
2. Invoke the existing global-install flow (identical to `abc install agents/<name>.md`) as a side effect.
3. Ensure the transitive skill closure (skills auto-ticked by agent selection) is also appended to `beacon.yaml.artifacts.skills` in the same write.

#### Scenario: Context adopted into beacon.yaml
- **WHEN** user selects `contexts/platform-team.md` for adoption
- **THEN** `beacon.yaml.artifacts.contexts` list includes `contexts/platform-team.md`

#### Scenario: Skill adopted with directory path
- **WHEN** user selects skill `generate-tests`
- **THEN** `beacon.yaml.artifacts.skills` list includes `skills/generate-tests/`

#### Scenario: Agent adopted into beacon.yaml
- **WHEN** user selects agent `spec-planner`
- **THEN** `beacon.yaml.artifacts.agents` list includes `agents/spec-planner.md`; `spec-planner.md` is globally symlinked into `~/.config/opencode/agents/` and `~/.claude/agents/`; any skills auto-ticked via this agent are also appended to `beacon.yaml.artifacts.skills`

#### Scenario: Multiple types adopted at once
- **WHEN** user selects 1 context, 1 skill, and 1 agent
- **THEN** `beacon.yaml` is updated with all three entries under their respective types in a single write; no `knowledge:` list is created or modified

### Requirement: Post-adoption sync and wiring
The system SHALL immediately sync and wire adopted artifacts after updating `beacon.yaml`, using the same mechanisms as `abc sync`. Wiring of context references into `CLAUDE.md` and `opencode.json` SHALL be a **reconciliation** to the effective context set — adding references for newly-adopted contexts **and removing references for un-adopted (or rejected) contexts** — not an append-only operation. Reference removal SHALL NOT depend on an interactive prune confirmation.

#### Scenario: Adopted context is synced and wired
- **WHEN** user adopts `contexts/platform-team.md`
- **THEN** file is copied to `.agentic-beacon/artifacts/contexts/platform-team.md` AND its reference is reconciled into CLAUDE.md and opencode.json

#### Scenario: Adopted skill is synced and wired
- **WHEN** user adopts `skills/generate-tests/`
- **THEN** skill files are copied to `.agentic-beacon/artifacts/skills/generate-tests/` AND installed to `.claude/skills/generate-tests/` and `.opencode/skills/generate-tests/`

#### Scenario: Un-adopted context reference is removed
- **WHEN** user removes `contexts/platform-team.md` from `beacon.yaml` (via the adopt flow or manual edit) and syncs
- **THEN** the `@…/contexts/platform-team.md` include is removed from CLAUDE.md and the matching `instructions` entry is removed from opencode.json, without requiring an interactive prune confirmation

#### Scenario: Adoption summary printed
- **WHEN** adoption of 2 artifacts completes successfully
- **THEN** system prints "Added 2 artifact(s) to beacon.yaml" and "Synced and wired" with the list of adopted paths

### Requirement: Context adoption provenance
The system SHALL distinguish between explicitly-adopted contexts (written into `beacon.yaml.artifacts.contexts` by user action) and transitively-pulled contexts (required by an adopted skill but not explicitly adopted by the user).

The system SHALL NOT prune an explicitly-adopted context simply because no referrer requires it anymore. The system SHALL prune a transitively-pulled context when no adopted skill declares it as a dependency.

#### Scenario: Explicitly adopted context survives referrer removal
- **WHEN** context `python-standards` is in `beacon.yaml.artifacts.contexts` (explicit) and the only skill that required it is unadopted
- **THEN** the context remains adopted and its symlink is preserved

#### Scenario: Transitively pulled context is pruned
- **WHEN** the user never explicitly adopted context `python-standards` but it was auto-added because a skill required it, and that skill is later unadopted with no other referrer
- **THEN** the context is removed from the transitive set and its symlink is pruned on the next sync

### Requirement: Unadoption pruning
The system SHALL support removing artifacts from `beacon.yaml` via the adopt flow or manual edit, and SHALL on next sync prune local symlinks for any artifact no longer adopted explicitly or transitively. This includes pruning of orphaned knowledge symlinks discovered via reference scanning.

#### Scenario: Explicit unadoption prunes local symlink
- **WHEN** user removes `contexts/python-standards.md` from `beacon.yaml` and runs `abc sync`
- **THEN** the symlink `.agentic-beacon/artifacts/contexts/python-standards.md` is removed

#### Scenario: Knowledge pruned after last referrer unadopted
- **WHEN** the only adopted context that referenced `knowledge/python-standards/lessons/foo.md` is unadopted, and the user runs `abc sync`
- **THEN** the symlink `.agentic-beacon/artifacts/knowledge/python-standards/lessons/foo.md` is pruned
