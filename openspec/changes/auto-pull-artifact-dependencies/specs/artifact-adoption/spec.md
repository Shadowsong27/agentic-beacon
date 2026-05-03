## REMOVED Requirements

### Requirement: Interactive TUI for artifact selection
**Reason**: The TUI continues to exist, but knowledge is removed from it as a selectable category. The requirement is being restated to reflect the new category set (contexts, skills, agents; no knowledge) — see MODIFIED below. This REMOVED entry exists only to record that the prior "three categories including knowledge" wording is deprecated; the replacement lives in MODIFIED Requirements.

**Migration**: No user-facing migration. The TUI simply no longer shows a knowledge section. Users who previously adopted knowledge through the TUI will find those knowledge files auto-pulled via the contexts and skills that reference them.

## MODIFIED Requirements

### Requirement: Interactive TUI for artifact selection
The system SHALL launch a textual-based full-screen TUI application that displays adoption candidates as categorized checkboxes for contexts, skills, and agents, with descriptions, allowing toggle selection. Knowledge is NOT a selectable category in the TUI; knowledge is derived at sync time from adopted contexts and skills.

#### Scenario: TUI displays categorized candidates
- **WHEN** there are 2 context candidates, 1 skill candidate, and 1 agent candidate
- **THEN** TUI shows "Contexts" section with 2 checkboxes, "Skills" section with 1 checkbox, and "Agents" section with 1 checkbox; no "Knowledge" section appears

#### Scenario: Select all via keybinding
- **WHEN** user presses `a` in the TUI
- **THEN** all checkboxes are toggled on

#### Scenario: Select none via keybinding
- **WHEN** user presses `n` in the TUI
- **THEN** all checkboxes are toggled off

#### Scenario: Confirm selection
- **WHEN** user presses `Enter` with 2 items checked
- **THEN** TUI exits and returns the 2 selected artifact paths

#### Scenario: Cancel selection
- **WHEN** user presses `Escape` or `q`
- **THEN** TUI exits with no selection and no modifications are made

### Requirement: beacon.yaml update on adoption
The system SHALL append selected artifact paths to the appropriate `artifacts.<type>` list in `beacon.yaml` after user confirms selection. The permitted types are `agents`, `contexts`, and `skills`; knowledge is never written to `beacon.yaml`.

#### Scenario: Context adopted into beacon.yaml
- **WHEN** user selects `contexts/platform-team.md` for adoption
- **THEN** `beacon.yaml.artifacts.contexts` list includes `contexts/platform-team.md`

#### Scenario: Skill adopted with directory path
- **WHEN** user selects skill `generate-tests`
- **THEN** `beacon.yaml.artifacts.skills` list includes `skills/generate-tests/`

#### Scenario: Agent adopted
- **WHEN** user selects `agents/python-reviewer.md`
- **THEN** `beacon.yaml.artifacts.agents` list includes `agents/python-reviewer.md`

#### Scenario: Multiple types adopted at once
- **WHEN** user selects 1 context and 1 agent
- **THEN** `beacon.yaml` is updated with both entries under their respective types in a single write; no `knowledge:` list is created or modified

## ADDED Requirements

### Requirement: Dependency prompting during adoption
The system SHALL inspect the `requires:` frontmatter of each agent and skill selected for adoption and SHALL prompt the user to also adopt any listed contexts or skills that are not already adopted.

#### Scenario: Adopting an agent with unadopted required context
- **WHEN** user selects agent `python-reviewer` with `requires.contexts: [python-standards]` and `python-standards` is not in `beacon.yaml`
- **THEN** the TUI prompts "Agent 'python-reviewer' requires context 'python-standards'. Adopt it?" with default yes, and on confirmation the context is also added to the adoption set

#### Scenario: All required dependencies already adopted
- **WHEN** user selects an agent whose every required context and skill is already in `beacon.yaml`
- **THEN** no dependency prompt is shown

#### Scenario: User declines to adopt a required dependency
- **WHEN** the dependency prompt is shown and the user declines
- **THEN** the primary agent is still adopted, but a warning is printed identifying the missing dependency and noting that `abc sync` will fail until it is adopted

### Requirement: Context adoption provenance
The system SHALL distinguish between explicitly-adopted contexts (written into `beacon.yaml.artifacts.contexts` by user action) and transitively-pulled contexts (required by an adopted agent or skill but not explicitly adopted by the user).

The system SHALL NOT prune an explicitly-adopted context simply because no referrer requires it anymore. The system SHALL prune a transitively-pulled context when no adopted agent or skill declares it as a dependency.

#### Scenario: Explicitly adopted context survives referrer removal
- **WHEN** context `python-standards` is in `beacon.yaml.artifacts.contexts` (explicit) and the only agent that required it is unadopted
- **THEN** the context remains adopted and its symlink is preserved

#### Scenario: Transitively pulled context is pruned
- **WHEN** the user never explicitly adopted context `python-standards` but it was auto-added because an agent required it, and that agent is later unadopted with no other referrer
- **THEN** the context is removed from the transitive set and its symlink is pruned on the next sync

### Requirement: Unadoption pruning
The system SHALL support removing artifacts from `beacon.yaml` via the adopt flow or manual edit, and SHALL on next sync prune local symlinks for any artifact no longer adopted explicitly or transitively. This includes pruning of orphaned knowledge symlinks discovered via reference scanning.

#### Scenario: Explicit unadoption prunes local symlink
- **WHEN** user removes `contexts/python-standards.md` from `beacon.yaml` and runs `abc sync`
- **THEN** the symlink `.agentic-beacon/artifacts/contexts/python-standards.md` is removed

#### Scenario: Knowledge pruned after last referrer unadopted
- **WHEN** the only adopted context that referenced `knowledge/python-standards/lessons/foo.md` is unadopted, and the user runs `abc sync`
- **THEN** the symlink `.agentic-beacon/artifacts/knowledge/python-standards/lessons/foo.md` is pruned
