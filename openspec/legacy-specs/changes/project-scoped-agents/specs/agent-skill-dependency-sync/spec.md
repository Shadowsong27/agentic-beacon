## ADDED Requirements

### Requirement: Sync validates declared agents' required skills
The system SHALL, during `abc sync`, compute for every agent listed in `beacon.yaml.artifacts.agents` the set of required skills by reading the agent's entry in `<warehouse>/agents/agents.yaml` (introduced by the `agent-requires-manifest` capability). For each required skill, the system SHALL verify that the skill is present in the project's effective skill set — either directly in `beacon.yaml.artifacts.skills`, or transitively pulled by another means.

#### Scenario: All required skills declared
- **WHEN** `beacon.yaml` declares agent `spec-planner`, `agents.yaml` lists `spec-planner.skills = [opsx-enhance-tasks]`, and `opsx-enhance-tasks` is in `beacon.yaml.artifacts.skills`
- **THEN** `abc sync` proceeds without any agent-skill validation prompt or error

#### Scenario: Required skill missing
- **WHEN** `beacon.yaml` declares agent `spec-planner`, `agents.yaml` lists `spec-planner.skills = [opsx-enhance-tasks]`, and `opsx-enhance-tasks` is NOT in `beacon.yaml.artifacts.skills` (nor transitively pulled)
- **THEN** `abc sync` halts before any file operations, surfaces the gap, and initiates the repair flow

### Requirement: Interactive repair prompt for missing required skill
The system SHALL, when a required-skill gap is detected and the session is interactive (TTY attached), prompt the user with a Y/N question whose default answer is **N**. The prompt SHALL name the requiring agent, the missing skill, and offer to append the skill to `beacon.yaml.artifacts.skills` and continue sync.

On `y`: the system SHALL append the skill to `beacon.yaml` (normalised to `skills/<name>/` directory form), save the file, and continue sync as if the skill had been declared.

On `N` (or Enter on the default): the system SHALL exit non-zero with a hard error naming the gap. The error message SHALL include the migration document URL.

#### Scenario: User accepts repair
- **WHEN** `abc sync` prompts "Add 'skills/opsx-enhance-tasks/' to beacon.yaml and sync it? [y/N]" and the user answers `y`
- **THEN** `beacon.yaml.artifacts.skills` is updated with `skills/opsx-enhance-tasks/` before the file is written; sync proceeds and symlinks the skill

#### Scenario: User declines repair
- **WHEN** the same prompt is answered `N` (or Enter)
- **THEN** `abc sync` exits non-zero, prints an error naming the declared agent and missing skill, and makes no modifications to `beacon.yaml`

#### Scenario: Multiple gaps
- **WHEN** two declared agents each require a skill not in `beacon.yaml.artifacts.skills` (two distinct skills)
- **THEN** the system presents the prompts sequentially; each is independently accepted or declined; any decline causes the overall sync to exit non-zero after processing all prompts

### Requirement: Non-interactive mode is hard error unless --yes
The system SHALL, when a required-skill gap is detected in a non-interactive session (no TTY attached or stdin is piped), exit non-zero with the same error format as declining the prompt — unless the `--yes` flag has been passed to `abc sync`.

When `--yes` is passed, non-interactive sessions SHALL auto-accept each repair as if the user had answered `y`, appending required skills to `beacon.yaml` and continuing sync.

#### Scenario: Non-interactive sync with gap
- **WHEN** a CI job runs `abc sync` (no TTY) and a declared agent requires a missing skill
- **THEN** `abc sync` exits non-zero without prompting and without modifying `beacon.yaml`

#### Scenario: Non-interactive sync with --yes
- **WHEN** a CI job runs `abc sync --yes` and a declared agent requires a missing skill
- **THEN** `abc sync` auto-appends the skill to `beacon.yaml.artifacts.skills`, syncs, and exits zero

### Requirement: Validation gap does not produce partial sync state
The system SHALL perform agent-skill validation as part of the sync-time dependency resolution pass (alongside `requires:` resolution for skills), before any symlink creation, pruning, or file operation. If a gap is unresolved (user declined or non-interactive error), the system SHALL exit without creating, modifying, or removing any artifact symlinks.

#### Scenario: Declined prompt leaves filesystem untouched
- **WHEN** the user declines the repair prompt
- **THEN** `.agentic-beacon/artifacts/` and the project's `.opencode/` and `.claude/` skill directories are in exactly the same state as before `abc sync` was invoked

### Requirement: Prompt ordering, atomicity, and transitive cascade
The system SHALL apply the following rules when one or more required-skill gaps are detected:

**Ordering.** When multiple gaps exist, prompts SHALL fire in sorted `(agent_path, skill_name)` order — lexicographic ascending. This ordering SHALL be deterministic and reproducible across runs regardless of `beacon.yaml` key ordering or `agents.yaml` key ordering.

**Atomicity.** The system SHALL collect every user response (Y/N) across all gap prompts **before** writing to `beacon.yaml`. If and only if every gap is accepted (all Y, or `--yes` in non-interactive mode), `beacon.yaml` SHALL be written once with all accepted skills appended, and sync SHALL proceed. If any single gap is declined (any N), the system SHALL abort with zero mutations to `beacon.yaml` and zero filesystem changes.

**Transitive cascade.** On acceptance (Y or `--yes`), after appending the named skill(s) to `beacon.yaml.artifacts.skills` and persisting, the system SHALL re-run the full dependency resolver against the updated manifest state. Any transitive contexts or knowledge required by the newly-added skill(s) SHALL be pulled via the existing silent-auto-pull logic defined in the `artifact-dependency-resolution` capability. No additional prompts fire for transitive contexts; only direct agent→skill gaps prompt.

#### Scenario: Deterministic prompt order
- **WHEN** `abc sync` detects two gaps: agent `registra-developer` missing skill `hl-clickhouse-connect`, and agent `pipeline-developer` missing skill `airflow-debug`
- **THEN** the system prompts for `pipeline-developer` / `airflow-debug` first, then `registra-developer` / `hl-clickhouse-connect`, sorted by `(agent_path, skill_name)` lexicographically ascending

#### Scenario: Partial-acceptance rejection (atomicity)
- **WHEN** two gaps are prompted; user answers `y` to the first, `N` to the second
- **THEN** `beacon.yaml` is NOT modified (neither the accepted skill nor the declined one is written); sync exits non-zero; the filesystem is in exactly the same state as before `abc sync` was invoked

#### Scenario: Full-acceptance triggers single atomic write
- **WHEN** three gaps are prompted; user answers `y` to all three
- **THEN** `beacon.yaml` is written exactly once with all three skills appended to `artifacts.skills`; the resolver re-runs against the updated state; sync proceeds

#### Scenario: Transitive context auto-pull after accepted repair
- **WHEN** the user accepts adding skill `opsx-enhance-tasks`, and that skill's frontmatter declares `requires.contexts: [openspec-workflow]`, and `openspec-workflow` exists in the warehouse but is not in `beacon.yaml.artifacts.contexts`
- **THEN** after `beacon.yaml` is updated with the skill, the resolver re-runs, auto-pulls `openspec-workflow` into the effective context set via the silent transitive logic, and sync proceeds with symlinks for both the skill and the context — with no additional prompt for the context
