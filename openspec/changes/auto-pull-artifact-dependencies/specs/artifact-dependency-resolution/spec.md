## ADDED Requirements

### Requirement: Agent frontmatter declares context and skill dependencies
The system SHALL require every agent file (`agents/<name>.md`) in a warehouse to declare its sibling-tier dependencies via a `requires:` block in its YAML frontmatter. The `requires:` block SHALL contain two keys: `contexts:` and `skills:`, each a list of artifact names. Empty lists are permitted; absence of the `requires:` key is not.

The artifact names in `requires.contexts` are filename stems of files under the warehouse's `contexts/` directory (no extension, no directory prefix). The artifact names in `requires.skills` are directory names under the warehouse's `skills/` directory.

#### Scenario: Agent with populated requires
- **WHEN** an agent file `agents/python-reviewer.md` has frontmatter `requires: { contexts: [python-standards], skills: [record-knowledge] }`
- **THEN** the system records the agent's dependencies as contexts=[`python-standards`] and skills=[`record-knowledge`]

#### Scenario: Agent with empty requires
- **WHEN** an agent file has frontmatter `requires: { contexts: [], skills: [] }`
- **THEN** the system treats the agent as having no sibling-tier dependencies and validation passes

#### Scenario: Agent missing requires block
- **WHEN** an adopted agent file has YAML frontmatter but no `requires:` key
- **THEN** `abc sync` fails with an error identifying the agent and linking to `docs/migrations/artifact-dependencies-frontmatter.md`

#### Scenario: Agent with no frontmatter
- **WHEN** an adopted agent file has no YAML frontmatter at all
- **THEN** `abc sync` fails with the same error as a missing `requires:` block

### Requirement: Skill frontmatter declares context dependencies
The system SHALL require every skill entrypoint file (`skills/<name>/SKILL.md`) in a warehouse to declare its context dependencies via a `requires:` block in its YAML frontmatter. The `requires:` block SHALL contain the key `contexts:` as a list of context filename stems. Empty list is permitted; absence of the `requires:` key is not.

Skills SHALL NOT declare dependencies on other skills in this version of the specification. The `skills:` key is not permitted inside a skill's `requires:` block.

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

### Requirement: Unadopted dependency is a hard error at sync
The system SHALL validate at `abc sync` that every `requires.contexts` entry in an adopted agent or skill resolves to a context that is explicitly or transitively adopted, and that every `requires.skills` entry in an adopted agent resolves to an adopted skill.

If a required dependency is missing, the system SHALL refuse to sync and SHALL emit an error that (1) names the requiring artifact, (2) names the missing dependency, and (3) links to the migration document.

#### Scenario: Required context not adopted
- **WHEN** adopted agent `python-reviewer` requires context `python-standards`, and `python-standards` is not in `beacon.yaml.artifacts.contexts` nor pulled by another adopted artifact
- **THEN** `abc sync` exits non-zero with an error: "agent 'python-reviewer' requires context 'python-standards' which is not adopted"

#### Scenario: Required skill not adopted
- **WHEN** adopted agent `python-reviewer` requires skill `record-knowledge`, and `record-knowledge` is not adopted
- **THEN** `abc sync` exits non-zero with an error naming both the agent and the missing skill

#### Scenario: Required context pulled transitively
- **WHEN** adopted agent requires context `python-standards`, and `python-standards` is listed in `beacon.yaml.artifacts.contexts` only because another artifact pulled it
- **THEN** `abc sync` succeeds; transitive adoption satisfies the requirement

### Requirement: Adopt-time prompting for required dependencies
The system SHALL, during interactive `abc adopt`, inspect the `requires:` frontmatter of each agent and skill the user is about to adopt, and SHALL prompt the user to also adopt any required contexts or skills that are not already adopted.

#### Scenario: Adopting an agent with unadopted required contexts
- **WHEN** user selects agent `python-reviewer` (which requires contexts=[`python-standards`]) and `python-standards` is not already adopted
- **THEN** the TUI prompts "Agent 'python-reviewer' requires context 'python-standards'. Adopt it as well?" with default yes

#### Scenario: Adopting an agent with all required contexts already adopted
- **WHEN** user selects an agent whose required contexts are all in `beacon.yaml`
- **THEN** no additional prompt is shown for those dependencies

#### Scenario: User declines to adopt a required dependency
- **WHEN** user declines the prompt to adopt a required dependency
- **THEN** adoption of the agent proceeds but a warning is printed: "Agent 'X' will fail `abc sync` until 'Y' is adopted"

### Requirement: Migration document exists and is referenced
The system SHALL ship a migration document at `docs/migrations/artifact-dependencies-frontmatter.md` in the agentic-beacon repository. Every error message raised by the sync or adopt flows due to missing or malformed `requires:` frontmatter SHALL include a URL pointing to this document.

#### Scenario: Error message links to migration doc
- **WHEN** `abc sync` fails due to a missing `requires:` block on an agent or skill
- **THEN** the error message includes the string "docs/migrations/artifact-dependencies-frontmatter.md"

### Requirement: Contexts have no frontmatter dependencies
The system SHALL NOT inspect context files for a `requires:` block. Context files have no sibling-tier dependencies: they reach knowledge via markdown links in the body and do not depend on other contexts or skills.

#### Scenario: Context with requires block is ignored
- **WHEN** a context file has a `requires:` block in its frontmatter
- **THEN** the system neither validates nor acts on the block; it is treated as unused frontmatter
