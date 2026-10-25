## ADDED Requirements

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
The system SHALL launch a textual-based full-screen TUI application that displays adoption candidates as categorized checkboxes (contexts, skills, knowledge) with descriptions, allowing toggle selection.

#### Scenario: TUI displays categorized candidates
- **WHEN** there are 2 context candidates and 1 skill candidate
- **THEN** TUI shows "Contexts" section with 2 checkboxes and "Skills" section with 1 checkbox

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
The system SHALL append selected artifact paths to the appropriate `artifacts.<type>` list in `beacon.yaml` after user confirms selection.

#### Scenario: Context adopted into beacon.yaml
- **WHEN** user selects `contexts/platform-team.md` for adoption
- **THEN** `beacon.yaml` `artifacts.contexts` list includes `contexts/platform-team.md`

#### Scenario: Skill adopted with directory path
- **WHEN** user selects skill `generate-tests`
- **THEN** `beacon.yaml` `artifacts.skills` list includes `skills/generate-tests/` (directory form with trailing slash)

#### Scenario: Multiple types adopted at once
- **WHEN** user selects 1 context and 2 knowledge files
- **THEN** `beacon.yaml` is updated with all 3 entries under their respective types in a single write

### Requirement: Post-adoption sync and wiring
The system SHALL immediately sync and wire adopted artifacts after updating `beacon.yaml`, using the same mechanisms as `abc sync`.

#### Scenario: Adopted context is synced and wired
- **WHEN** user adopts `contexts/platform-team.md`
- **THEN** file is copied to `.agentic-beacon/artifacts/contexts/platform-team.md` AND wired into CLAUDE.md and opencode.json

#### Scenario: Adopted skill is synced and wired
- **WHEN** user adopts `skills/generate-tests/`
- **THEN** skill files are copied to `.agentic-beacon/artifacts/skills/generate-tests/` AND installed to `.claude/skills/generate-tests/` and `.opencode/skills/generate-tests/`

#### Scenario: Adoption summary printed
- **WHEN** adoption of 2 artifacts completes successfully
- **THEN** system prints "Added 2 artifact(s) to beacon.yaml" and "Synced and wired" with the list of adopted paths
