# warehouse-lint-command Specification

## Purpose
TBD - created by archiving change warehouse-lint-cli-for-ci. Update Purpose after archive.
## Requirements
### Requirement: `abc warehouse lint [PATH]` validates an arbitrary warehouse end-to-end

The system SHALL provide an `abc warehouse lint [PATH]` command that runs every Beacon-owned artifact validation rule against the warehouse directory rooted at PATH. PATH SHALL be optional and SHALL default to the current working directory when omitted, matching the precedent of `abc warehouse template-upgrade`. The command SHALL operate without requiring a `beacon.yaml` or any project context — the target is a raw warehouse clone, not an adopting project.

#### Scenario: Lint a clean warehouse

- **WHEN** the user runs `abc warehouse lint` (no PATH) from inside a warehouse clone whose every skill, agent, context, and knowledge link is valid
- **THEN** the system prints a success summary and exits with code 0

#### Scenario: Lint a specific path

- **WHEN** the user runs `abc warehouse lint /some/other/warehouse`
- **THEN** the system validates that directory as a warehouse, not the current directory

#### Scenario: PATH is not a warehouse

- **WHEN** the user runs `abc warehouse lint /tmp/empty-dir` against a directory that is missing required warehouse structure (no `skills/`, `agents/`, `contexts/`, `docs/`)
- **THEN** the system reports the structural defects and exits with code 1

### Requirement: Structure preflight

The system SHALL invoke the existing `WarehouseValidator` structural check as the first phase of lint. Subsequent artifact-level rules SHALL still be run even if the structural check finds defects, so a single lint invocation reports every category of error at once.

#### Scenario: Missing required directory does not short-circuit downstream checks

- **WHEN** the user lints a directory that is missing `docs/` but has valid `skills/`, `agents/`, and `contexts/`
- **THEN** the output reports both the missing `docs/` directory AND every artifact-level finding (skill frontmatter, agent manifest, etc.) in a single run

### Requirement: Skill frontmatter validation

The system SHALL validate every `skills/*/SKILL.md` file. For each skill file, the system SHALL parse YAML frontmatter, fail when frontmatter is absent or malformed, and validate the parsed object against `SkillFrontmatter` (the same Pydantic model `abc sync` uses), reporting any field-level error. Skill names (directory stems) are not required as explicit frontmatter keys; the existing `requires.contexts`-only rule for skills is preserved.

#### Scenario: Skill missing frontmatter (the delegate-to-cc regression)

- **GIVEN** `skills/delegate-to-cc/SKILL.md` exists with body content but no `---` frontmatter block
- **WHEN** the user runs `abc warehouse lint`
- **THEN** the system reports `skills/delegate-to-cc/SKILL.md: error: File has no YAML frontmatter (must start with ---)` and exits with code 1

#### Scenario: Skill frontmatter has malformed YAML

- **GIVEN** a SKILL.md whose frontmatter block contains a YAML parse error
- **WHEN** the user runs lint
- **THEN** the system reports the YAML parse error scoped to that skill file and exits with code 1

#### Scenario: Skill declares forbidden skill-to-skill dependency

- **GIVEN** a SKILL.md with `requires: { skills: [...], contexts: [...] }`
- **WHEN** the user runs lint
- **THEN** the system reports that skill-to-skill dependencies are not supported and exits with code 1

### Requirement: Skill `requires.contexts` references resolve

The system SHALL verify that every context name listed in a skill's `requires.contexts` block corresponds to an existing `contexts/<name>.md` file in the warehouse.

#### Scenario: Skill requires a missing context

- **GIVEN** `skills/foo/SKILL.md` has `requires.contexts: [missing-ctx]` but `contexts/missing-ctx.md` does not exist
- **WHEN** the user runs lint
- **THEN** the system reports that skill `foo` requires context `missing-ctx` which is not present in the warehouse, and exits with code 1

### Requirement: Agent manifest validation

The system SHALL invoke the existing agent manifest validators on the target warehouse: `load_agent_manifest`, `validate_agents_directory` (bidirectional `agents/*.md` ↔ `agents.yaml` correspondence), `validate_agent_frontmatter_clean` (no leftover `requires:` keys in agent files), and `validate_declared_skills` (every skill declared in `agents.yaml` exists under `skills/`).

#### Scenario: Agent file has no entry in agents.yaml

- **GIVEN** `agents/foo.md` exists but `agents.yaml` has no `foo:` key
- **WHEN** the user runs lint
- **THEN** the system reports the missing manifest entry and exits with code 1

#### Scenario: agents.yaml declares a skill that does not exist

- **GIVEN** `agents.yaml` declares agent `foo` with `skills: [missing-skill]` but `skills/missing-skill/SKILL.md` does not exist
- **WHEN** the user runs lint
- **THEN** the system reports the missing skill scoped to agent `foo` and exits with code 1

#### Scenario: Agent file still contains a `requires:` key in frontmatter

- **GIVEN** `agents/foo.md` has `requires: { skills: [...] }` in its YAML frontmatter (legacy form)
- **WHEN** the user runs lint
- **THEN** the system reports that agent files MUST NOT carry `requires:` (moved to `agents.yaml`) and exits with code 1

### Requirement: Agent frontmatter requires `name` and `description`

The system SHALL require that every `agents/*.md` file (excluding `README.md`) contains a YAML frontmatter block defining both a `name` key (string) and a `description` key (string). This is a new lint-only rule with no enforcement elsewhere in Beacon today.

#### Scenario: Agent frontmatter missing `name`

- **GIVEN** `agents/foo.md` has frontmatter `{description: "..."}` but no `name:` key
- **WHEN** the user runs lint
- **THEN** the system reports that `agents/foo.md` is missing the `name` key in frontmatter and exits with code 1

#### Scenario: Agent frontmatter missing `description`

- **GIVEN** `agents/foo.md` has frontmatter `{name: foo}` but no `description:` key
- **WHEN** the user runs lint
- **THEN** the system reports that `agents/foo.md` is missing the `description` key in frontmatter and exits with code 1

#### Scenario: Agent has both keys

- **GIVEN** `agents/foo.md` has frontmatter `{name: foo, description: "..."}` and an entry in `agents.yaml`
- **WHEN** the user runs lint and no other defects exist
- **THEN** the system reports no error against this agent

### Requirement: Knowledge link integrity (lint-only error promotion)

The system SHALL scan every `contexts/*.md` and `skills/*/SKILL.md` file for inline markdown links whose target resolves to a path under `knowledge/` ending in `.md`, and SHALL report any such link whose resolved file does not exist on disk as an error. The lint-side check SHALL NOT modify the existing `scan_file_for_knowledge` primitive — that primitive retains its current warning-only posture so that `abc sync` behaviour is unchanged.

#### Scenario: Context links to a missing knowledge file

- **GIVEN** `contexts/foo.md` contains `[X](../knowledge/foo/bar.md)` and `knowledge/foo/bar.md` does not exist
- **WHEN** the user runs lint
- **THEN** the system reports the broken knowledge link scoped to `contexts/foo.md` and exits with code 1

#### Scenario: Skill links to a missing knowledge file

- **GIVEN** `skills/foo/SKILL.md` contains `[X](../../knowledge/foo/bar.md)` and the target does not exist
- **WHEN** the user runs lint
- **THEN** the system reports the broken link scoped to `skills/foo/SKILL.md` and exits with code 1

#### Scenario: `abc sync` behaviour unchanged after lint shipping

- **GIVEN** a project whose adopted artifacts include a context with a broken knowledge link
- **WHEN** the user runs `abc sync` (not `abc warehouse lint`)
- **THEN** the system completes sync and logs a warning, identical to today's behaviour, exiting with code 0

### Requirement: Output format and exit codes

The system SHALL print findings to the console grouped by artifact path, with each finding on its own line prefixed by `error:`. The system SHALL exit with code 0 when no errors were found, and with code 1 when one or more errors were found. The system SHALL NOT produce warnings — every defect under the lint's purview is an error under the agreed scope.

#### Scenario: Clean warehouse exit code

- **WHEN** lint finds no errors
- **THEN** the process exits with code 0 and prints a success summary

#### Scenario: Any defect produces exit 1

- **WHEN** lint finds at least one error
- **THEN** the process exits with code 1

#### Scenario: Findings are grouped by artifact

- **GIVEN** a warehouse with two defects in `skills/foo/SKILL.md` and one defect in `agents/bar.md`
- **WHEN** the user runs lint
- **THEN** the output contains a section per artifact path with its findings listed beneath, and the two `skills/foo/SKILL.md` findings are not interleaved with the `agents/bar.md` finding

#### Scenario: No JSON output flag in v1

- **WHEN** the user passes `--json`
- **THEN** the system rejects the unknown flag (standard Click behaviour); no JSON output mode is offered in this version

### Requirement: Path-agnostic operation

The command SHALL operate against any directory the caller points at, regardless of where the caller is invoked from. The command SHALL NOT read or require a project-side `beacon.yaml`, `.agentic-beacon/` directory, or any project-scoped configuration.

#### Scenario: Lint runs against a path with no surrounding project

- **WHEN** the user runs `abc warehouse lint /path/to/raw/warehouse/clone` from a directory that is not a Beacon project
- **THEN** the system validates the target warehouse without attempting to load any project manifest, and reports results scoped only to the target path
