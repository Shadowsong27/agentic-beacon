## ADDED Requirements

### Requirement: Skill frontmatter declares context dependencies
The system SHALL require every skill entrypoint file (`skills/<name>/SKILL.md`) in a warehouse to declare its context dependencies via a `requires:` block in its YAML frontmatter. The `requires:` block SHALL contain the key `contexts:` as a list of context filename stems. Empty list is permitted; absence of the `requires:` key is not.

Skills SHALL NOT declare dependencies on other skills in this version of the specification. The `skills:` key is not permitted inside a skill's `requires:` block.

Agents are global machine-level artifacts not tracked in project `beacon.yaml`. Agent `requires:` frontmatter may exist as warehouse metadata for future groundwork (PER-109) but is not validated or read during `abc sync` in this change.

#### Scenario: Skill with context dependency
- **WHEN** a skill file `skills/python-refactor/SKILL.md` has frontmatter `requires: { contexts: [python-standards] }`
- **THEN** the system records the skill's dependencies as contexts=[`python-standards`]

#### Scenario: Skill with empty requires
- **WHEN** a skill file has frontmatter `requires: { contexts: [] }`
- **THEN** the system treats the skill as having no sibling-tier dependencies and validation passes

#### Scenario: Skill missing requires block
- **WHEN** an adopted skill entrypoint has YAML frontmatter but no `requires:` key
- **THEN** `abc sync` fails with an error identifying the skill and linking to the migration document

#### Scenario: Skill declares skill dependency
- **WHEN** a skill entrypoint has `requires: { contexts: [...], skills: [...] }`
- **THEN** `abc sync` fails with an error explaining that skill-to-skill dependencies are not supported

### Requirement: Required context resolution is auto-pull; missing-from-warehouse is a hard error
The system SHALL at `abc sync` include every `requires.contexts` entry declared by an adopted skill in the effective context set transitively, even if the context is not explicitly listed in `beacon.yaml.artifacts.contexts`.

If a required context exists in the warehouse (`contexts/<name>.md`), the system SHALL auto-pull and symlink it without error. If a required context does NOT exist in the warehouse, the system SHALL refuse to sync and SHALL emit an error that (1) names the requiring skill, (2) names the missing context, and (3) links to the migration document.

#### Scenario: Required context auto-pulled from warehouse
- **WHEN** adopted skill `python-refactor` requires context `python-standards`, `python-standards` exists in the warehouse, but is NOT in `beacon.yaml.artifacts.contexts`
- **THEN** `abc sync` succeeds; `python-standards` is auto-pulled into the effective context set and a symlink is created

#### Scenario: Required context missing from warehouse
- **WHEN** adopted skill `python-refactor` requires context `nonexistent`, and `nonexistent` does NOT exist as `contexts/nonexistent.md` in the warehouse
- **THEN** `abc sync` exits non-zero with an error: "skill 'python-refactor' requires context 'nonexistent' which is not found in the warehouse"

#### Scenario: Required context pulled transitively
- **WHEN** adopted skill requires context `python-standards`, and `python-standards` exists in the warehouse
- **THEN** `abc sync` succeeds; the context is included in the effective set regardless of whether it is also explicitly adopted

### Requirement: Migration document exists and is referenced
The system SHALL ship a migration document at `docs/migrations/artifact-dependencies-frontmatter.md` in the agentic-beacon repository. Every error message raised by the sync flow due to missing or malformed `requires:` frontmatter on skills SHALL include a URL pointing to this document.

#### Scenario: Error message links to migration doc
- **WHEN** `abc sync` fails due to a missing `requires:` block on a skill
- **THEN** the error message includes the string "docs/migrations/artifact-dependencies-frontmatter.md"

### Requirement: Contexts have no frontmatter dependencies
The system SHALL NOT inspect context files for a `requires:` block. Context files have no sibling-tier dependencies: they reach knowledge via markdown links in the body and do not depend on other contexts or skills.

#### Scenario: Context with requires block is ignored
- **WHEN** a context file has a `requires:` block in its frontmatter
- **THEN** the system neither validates nor acts on the block; it is treated as unused frontmatter
