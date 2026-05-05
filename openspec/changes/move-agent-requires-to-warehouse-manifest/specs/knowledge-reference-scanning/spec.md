## MODIFIED Requirements

### Requirement: Scanner inspects adopted contexts and skills only
The system SHALL scan for knowledge references only in files that are (1) adopted contexts listed in `beacon.yaml.artifacts.contexts`, and (2) adopted skill entrypoints (`SKILL.md` files) under directories listed in `beacon.yaml.artifacts.skills`.

The system SHALL NOT scan agent files for knowledge references. Agents reach knowledge only transitively through the skills they declare as dependencies in the warehouse-level `agents/agents.yaml` manifest. Agent dependency declarations SHALL NOT carry a `contexts:` list; agents do not natively require contexts, because contexts are a project-level concern declared via `beacon.yaml.artifacts.contexts`.

The system SHALL NOT scan files outside the warehouse (e.g., the project's own `AGENTS.md`, documentation, or unrelated files).

#### Scenario: Adopted context scanned
- **WHEN** `contexts/python-standards.md` is in `beacon.yaml.artifacts.contexts`
- **THEN** the scanner reads the file and extracts all knowledge references from its markdown links

#### Scenario: Adopted skill's SKILL.md scanned
- **WHEN** `skills/python-refactor/` is in `beacon.yaml.artifacts.skills`
- **THEN** the scanner reads `skills/python-refactor/SKILL.md` and extracts knowledge references

#### Scenario: Non-entrypoint skill files not scanned
- **WHEN** a skill directory contains helper files like `scripts/run.py` or `references/guide.md`
- **THEN** the scanner does NOT inspect these files; only `SKILL.md` is scanned

#### Scenario: Agent file not scanned for knowledge
- **WHEN** an adopted agent file contains a markdown link into `knowledge/...`
- **THEN** the scanner does not treat this as a knowledge reference; the link has no effect on derived knowledge
