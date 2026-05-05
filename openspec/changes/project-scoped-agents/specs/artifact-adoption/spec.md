## MODIFIED Requirements

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

## REMOVED Requirements

### Requirement: Agent TUI handling is global-install-only
**Reason**: Superseded by project-scoped agent adoption. Agents now follow the same flow as contexts and skills — selection records the agent in `beacon.yaml.artifacts.agents` AND triggers global install (formerly, it did global install only). The "MAY show agents as global-install candidates... does NOT update project `beacon.yaml`" language in the previous requirement is replaced by the new agent handling in the `Interactive TUI for artifact selection` requirement above.

**Migration**: Existing projects that previously globally-installed agents via `abc adopt` have no record of which agents they depend on. Users re-run `abc adopt` after upgrading Beacon; agents appear as selectable candidates, auto-tick their required skills, and update `beacon.yaml.artifacts.agents`. The `abc install agents/<name>.md` command remains available as an escape hatch for pure global install without project declaration (see `global-agent-install` capability).
