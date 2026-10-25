## MODIFIED Requirements

### Requirement: Skill frontmatter declares context dependencies
The system SHALL require every skill entrypoint file (`skills/<name>/SKILL.md`) in a warehouse to declare its context dependencies via a `requires:` block in its YAML frontmatter. The `requires:` block SHALL contain the key `contexts:` as a list of context filename stems. Empty list is permitted; absence of the `requires:` key is not.

Skills SHALL NOT declare dependencies on other skills in this version of the specification. The `skills:` key is not permitted inside a skill's `requires:` block.

Agents are global machine-level artifacts not tracked in project `beacon.yaml`. Agent dependency metadata SHALL live in the warehouse-level manifest `<warehouse>/agents/agents.yaml` (see the `agent-requires-manifest` capability) and SHALL NOT be carried in agent YAML frontmatter. The contents of `agents.yaml` are validated at warehouse-read time but are not read during project `abc sync` in this change; their consumption by `abc sync` is deferred to the follow-up `project-scoped-agents` change.

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

#### Scenario: Agent file with leftover requires block
- **WHEN** an `agents/<name>.md` file in the warehouse contains a `requires:` block in its YAML frontmatter
- **THEN** `abc warehouse status` and `abc sync` both fail with an error instructing the user to move the block into `agents/agents.yaml` and linking to the migration document
