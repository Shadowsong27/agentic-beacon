## ADDED Requirements

### Requirement: Managed-block gitignore engine

Beacon SHALL own its `.gitignore` entries through a single managed block delimited by the exact markers `# >>> Agentic Beacon (managed) >>>` (begin) and `# <<< Agentic Beacon (managed) <<<` (end). On every application the engine SHALL regenerate the block's body **wholesale** from the current entry set — it SHALL NOT append entries line by line. Applying the engine SHALL be idempotent: re-running it against a file that already holds the correct managed block SHALL make no change.

#### Scenario: Block created in a fresh .gitignore

- **GIVEN** a project whose root `.gitignore` has no managed block (or no `.gitignore` at all)
- **WHEN** the engine applies the Tier A entry set
- **THEN** the file contains exactly one managed block, delimited by the begin/end markers, listing every Tier A entry

#### Scenario: Wholesale regeneration replaces stale body

- **GIVEN** a managed block whose body is missing one required entry
- **WHEN** the engine re-applies the current entry set
- **THEN** the block body is replaced with the full current entry set, the markers are unchanged, and content outside the block is untouched

#### Scenario: Idempotent re-application

- **GIVEN** a `.gitignore` already holding the correct managed block
- **WHEN** the engine applies the same entry set again
- **THEN** the file bytes are unchanged

### Requirement: Tier A entry set is unconditional

The Tier A managed block in the project root `.gitignore` SHALL always contain the full entry set regardless of which tool directories exist: `.agentic-beacon/config.toml`, `.agentic-beacon/artifacts/`, `.agentic-beacon/warehouse-catalog.md`, `.agentic-beacon/pending.yaml`, `.claude/skills/`, `.claude/commands/`, `.claude/agents/`, `.opencode/skills/`, `.opencode/command/`, `.opencode/agents/`. Entries SHALL NOT be gated on the presence of `.claude/` or `.opencode/`, nor on whether agents are declared in `beacon.yaml`.

#### Scenario: Full set written even without tool dirs

- **GIVEN** a wired project that has neither `.claude/` nor `.opencode/` and declares no agents
- **WHEN** the engine applies Tier A
- **THEN** the managed block still contains all ten entries, including the `.claude/*` and `.opencode/*` symlink-dir lines

#### Scenario: Agent dirs present without declared agents

- **GIVEN** a wired project with an empty `beacon.yaml.artifacts.agents`
- **WHEN** the engine applies Tier A
- **THEN** `.claude/agents/` and `.opencode/agents/` are present in the managed block

### Requirement: Tier B nested gitignores flow through the same engine

The nested `.claude/.gitignore` and `.opencode/.gitignore` files SHALL be written as managed blocks by the same engine. A nested file SHALL be written only when its tool directory (`.claude/` or `.opencode/`) exists. The Tier B entry sets SHALL be preserved unchanged from the prior implementation: `.claude/.gitignore` = `skills/`, `scheduled_tasks.lock`, `worktrees/`; `.opencode/.gitignore` = `skills/`, `command/`, `bun.lock`, `package.json`, `package-lock.json`, `node_modules/`.

#### Scenario: Nested block written when tool dir exists

- **GIVEN** a project with a `.claude/` directory
- **WHEN** the engine applies Tier B
- **THEN** `.claude/.gitignore` contains a managed block listing exactly `skills/`, `scheduled_tasks.lock`, `worktrees/`

#### Scenario: Nested block skipped when tool dir absent

- **GIVEN** a project with no `.opencode/` directory
- **WHEN** the engine applies Tier B
- **THEN** no `.opencode/.gitignore` is created

### Requirement: Surgical migration of legacy loose-line blocks

When the engine first encounters a legacy `# Agentic Beacon` region (an unmanaged header followed by loose entry lines), it SHALL insert the managed block, remove any loose line that exactly matches a managed entry, drop the now-empty legacy bare header, and preserve every non-managed line in place. The engine SHALL NOT delete any line it does not own. Migration SHALL be idempotent.

#### Scenario: Managed lines deduped, unknown lines preserved

- **GIVEN** a root `.gitignore` with a legacy `# Agentic Beacon` header followed by `.agentic-beacon/config.toml`, `.agentic-beacon/artifacts/`, `.agentic-beacon/.legacy-migrated`, and `sample-warehouse/`
- **WHEN** the engine applies Tier A
- **THEN** the managed block is present, the two managed lines no longer appear as loose duplicates, the bare legacy `# Agentic Beacon` header is gone, and `.agentic-beacon/.legacy-migrated` and `sample-warehouse/` are still present

#### Scenario: Migration is a no-op on second run

- **GIVEN** a `.gitignore` already migrated to the managed block with preserved unknown lines
- **WHEN** the engine applies the same entry set again
- **THEN** the file is unchanged

### Requirement: Every wiring path applies both tiers

`abc sync` (`run_sync`), `abc adopt` (accept), and `abc warehouse connect` SHALL each apply the unified engine so that both tiers are written on every path. No wiring path SHALL emit one tier without the other.

#### Scenario: Adopt writes Tier A (regression for the reported bug)

- **GIVEN** a project being wired for the first time via `abc adopt` where accepted artifacts create `.claude/` and/or `.opencode/`
- **WHEN** the adopt accept completes
- **THEN** the root `.gitignore` contains the Tier A managed block AND the nested Tier B blocks exist for each present tool dir

#### Scenario: Sync writes both tiers

- **GIVEN** a wired project
- **WHEN** `abc sync` runs
- **THEN** the Tier A managed block and the nested Tier B managed blocks (for present tool dirs) are all present and current

### Requirement: Tracked-on-purpose set stays visible

The engine's entry sets SHALL never cause Beacon's tracked-on-purpose files to be ignored: `.agentic-beacon/beacon.yaml`, the nested `.claude/.gitignore` and `.opencode/.gitignore`, `CLAUDE.md`, `opencode.json`, and `.worktreeinclude`. Because Tier A ignores specific subpaths (never a whole `.claude/` or `.opencode/` directory), these files remain tracked.

#### Scenario: beacon.yaml and configs not ignored

- **GIVEN** a wired project with the full managed blocks applied
- **WHEN** git evaluates ignore status for `.agentic-beacon/beacon.yaml`, `CLAUDE.md`, `opencode.json`, `.worktreeinclude`, and the nested `.gitignore` files
- **THEN** none of them are ignored

### Requirement: Doctor detects gitignore drift

`abc doctor` SHALL report a gitignore-drift issue at severity **error** when a wired project's Tier A managed block is missing or incomplete, when a nested Tier B block is missing or incomplete while its tool dir exists, or when any tracked-on-purpose file is ignored. The specific reported case — a Tier B nested block present while the Tier A block is absent — SHALL be detected.

#### Scenario: Tier A missing while Tier B present is flagged

- **GIVEN** a wired project with a nested `.opencode/.gitignore` managed block but no Tier A managed block in the root `.gitignore`
- **WHEN** `abc doctor` runs
- **THEN** it reports a gitignore-drift error identifying the missing Tier A block

#### Scenario: Healthy project reports no drift

- **GIVEN** a wired project with correct Tier A and Tier B managed blocks
- **WHEN** `abc doctor` runs
- **THEN** no gitignore-drift issue is reported

### Requirement: Doctor --fix repairs the drift

`abc doctor --fix` SHALL repair detected gitignore drift by applying the same managed-block engine to the root and nested `.gitignore` files, and SHALL record each repair in the doctor's applied-fixes summary. A subsequent `abc doctor` run SHALL report no gitignore drift.

#### Scenario: --fix rewrites the managed blocks

- **GIVEN** a wired project flagged with gitignore drift
- **WHEN** `abc doctor --fix` runs
- **THEN** the Tier A and Tier B managed blocks are written correctly, the fix is listed in the applied-fixes summary, and a re-run of `abc doctor` reports no drift
