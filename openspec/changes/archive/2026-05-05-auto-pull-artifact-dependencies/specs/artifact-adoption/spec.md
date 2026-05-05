## MODIFIED Requirements

### Requirement: Interactive TUI for artifact selection
The system SHALL launch a textual-based full-screen TUI application that displays adoption candidates as categorized checkboxes for contexts and skills, with descriptions, allowing toggle selection. Knowledge is NOT a selectable category in the TUI; knowledge is derived at sync time from adopted contexts and skills.

Agents are global machine-level artifacts. The adopt TUI MAY show agents as global-install candidates alongside contexts and skills. Selecting an agent triggers a global machine-level installation and does NOT update project `beacon.yaml`. Persistent selected-global-agent state and `abc sync` installing selected agents is deferred to PER-109.

#### Scenario: TUI displays categorized candidates
- **WHEN** there are 2 context candidates and 1 skill candidate
- **THEN** TUI shows "Contexts" section with 2 checkboxes and "Skills" section with 1 checkbox; Agents may appear as a machine-level global-install section; no "Knowledge" section appears

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
The system SHALL append selected artifact paths to the appropriate `artifacts.<type>` list in `beacon.yaml` after user confirms selection. The permitted types are `contexts` and `skills`; knowledge is never written to `beacon.yaml`.

#### Scenario: Context adopted into beacon.yaml
- **WHEN** user selects `contexts/platform-team.md` for adoption
- **THEN** `beacon.yaml.artifacts.contexts` list includes `contexts/platform-team.md`

#### Scenario: Skill adopted with directory path
- **WHEN** user selects skill `generate-tests`
- **THEN** `beacon.yaml.artifacts.skills` list includes `skills/generate-tests/`

#### Scenario: Multiple types adopted at once
- **WHEN** user selects 1 context and 1 skill
- **THEN** `beacon.yaml` is updated with both entries under their respective types in a single write; no `knowledge:` list is created or modified

## ADDED Requirements

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
