## MODIFIED Requirements

### Requirement: Required context resolution is auto-pull; missing-from-warehouse is a hard error
The system SHALL at `abc sync` include every `requires.contexts` entry declared by an adopted skill in the effective context set transitively, even if the context is not explicitly listed in `beacon.yaml.artifacts.contexts`.

The system SHALL ALSO at `abc sync` include every `skills` entry declared for an agent in `beacon.yaml.artifacts.agents` via the warehouse `agents.yaml` manifest as a **required** entry in the effective skill set. Unlike skill → context resolution, agent → skill requirements are NOT silently auto-pulled; when a required skill is not in `beacon.yaml.artifacts.skills`, the repair flow defined in the `agent-skill-dependency-sync` capability is invoked (interactive Y/N to append to `beacon.yaml`, or hard error in non-interactive mode). The rationale for the asymmetry: skills are user-facing commands, and silently adopting them on the user's behalf without explicit consent would surprise the user; contexts are subordinate dependencies of skills already adopted.

If a required context exists in the warehouse (`contexts/<name>.md`), the system SHALL auto-pull and symlink it without error. If a required context does NOT exist in the warehouse, the system SHALL refuse to sync and SHALL emit an error that (1) names the requiring skill, (2) names the missing context, and (3) links to the migration document.

If a required skill declared by an agent in `agents.yaml` does NOT exist in the warehouse, the system SHALL refuse to sync and emit an error naming the agent, the missing skill, and linking to the migration document. This error fires regardless of interactive mode.

#### Scenario: Required context auto-pulled from warehouse
- **WHEN** adopted skill `python-refactor` requires context `python-standards`, `python-standards` exists in the warehouse, but is NOT in `beacon.yaml.artifacts.contexts`
- **THEN** `abc sync` succeeds; `python-standards` is auto-pulled into the effective context set and a symlink is created

#### Scenario: Required context missing from warehouse
- **WHEN** adopted skill `python-refactor` requires context `nonexistent`, and `nonexistent` does NOT exist as `contexts/nonexistent.md` in the warehouse
- **THEN** `abc sync` exits non-zero with an error: "skill 'python-refactor' requires context 'nonexistent' which is not found in the warehouse"

#### Scenario: Required context pulled transitively
- **WHEN** adopted skill requires context `python-standards`, and `python-standards` exists in the warehouse
- **THEN** `abc sync` succeeds; the context is included in the effective set regardless of whether it is also explicitly adopted

#### Scenario: Declared agent's required skill missing from beacon.yaml (interactive)
- **WHEN** `beacon.yaml.artifacts.agents` declares `spec-planner`, the warehouse `agents.yaml` has `spec-planner.skills = [opsx-enhance-tasks]`, `opsx-enhance-tasks` exists in the warehouse but is not in `beacon.yaml.artifacts.skills`, and the session is interactive
- **THEN** `abc sync` prompts "Add 'skills/opsx-enhance-tasks/' to beacon.yaml and sync it? [y/N]" and proceeds according to the user's response per the `agent-skill-dependency-sync` capability

#### Scenario: Declared agent's required skill missing from warehouse
- **WHEN** `beacon.yaml.artifacts.agents` declares `spec-planner`, the warehouse `agents.yaml` has `spec-planner.skills = [ghost-skill]`, and no `skills/ghost-skill/SKILL.md` exists in the warehouse
- **THEN** `abc sync` exits non-zero with an error naming `spec-planner`, the missing skill `ghost-skill`, and linking to the migration document — regardless of TTY mode
