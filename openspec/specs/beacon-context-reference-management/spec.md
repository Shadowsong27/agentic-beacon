# beacon-context-reference-management Specification

## Purpose
TBD - created by archiving change reconcile-context-references. Update Purpose after archive.
## Requirements
### Requirement: Context references reconciled to the effective set

Beacon SHALL reconcile the artifact-context references in `CLAUDE.md` (as `@`-includes) and `opencode.json` (as `instructions` array entries) to **exactly** the effective context set on every wiring path. Reconciliation SHALL add a reference for each effective context that is missing and SHALL remove any Beacon-owned reference that is no longer in the effective set. The reconciler SHALL NOT append-only, and SHALL NOT depend on an interactive prune confirmation to remove a departed reference. Reconciliation SHALL be idempotent: re-running it against files that already match the effective set SHALL make no change.

#### Scenario: De-adopted context reference is removed

- **GIVEN** `CLAUDE.md` and `opencode.json` reference `.agentic-beacon/artifacts/contexts/linear-ops.md`, and `linear-ops` is no longer in the effective set
- **WHEN** the reconciler runs
- **THEN** the `@…/contexts/linear-ops.md` include is removed from `CLAUDE.md` and the matching `instructions` entry is removed from `opencode.json`

#### Scenario: Missing reference for an effective context is added

- **GIVEN** `beacon-ops` is in the effective set but neither file references `.agentic-beacon/artifacts/contexts/beacon-ops.md`
- **WHEN** the reconciler runs
- **THEN** the `@`-include is added to `CLAUDE.md` and the `instructions` entry is added to `opencode.json`

#### Scenario: Dangling reference from a warehouse rename is removed

- **GIVEN** the warehouse renamed `contexts/linear-ops.md` to `contexts/plane-ops.md`, leaving `linear-ops` out of the effective set and its reference dangling
- **WHEN** the reconciler runs
- **THEN** the dangling `linear-ops` reference is removed from both files

#### Scenario: Idempotent re-run

- **GIVEN** both files already match the effective set exactly
- **WHEN** the reconciler runs again
- **THEN** neither file is written and no reference is added or removed

### Requirement: Ownership is scoped to the artifact namespace

The reconciler SHALL treat a reference as Beacon-owned only when its path begins with `.agentic-beacon/artifacts/`. It SHALL NOT add, remove, or reorder any reference outside that namespace, and SHALL preserve the `opencode.json` `$schema` key and all user-authored `instructions` entries.

#### Scenario: Non-artifact CLAUDE.md includes are preserved

- **GIVEN** `CLAUDE.md` contains `@AGENTS.md` and `@docs/house-style.md` alongside artifact-context includes
- **WHEN** the reconciler removes a de-adopted context reference
- **THEN** `@AGENTS.md` and `@docs/house-style.md` remain untouched and in place

#### Scenario: opencode.json schema and user instructions are preserved

- **GIVEN** `opencode.json` has a `$schema` key and a user `instructions` entry `docs/house-style.md` alongside artifact-context entries
- **WHEN** the reconciler runs
- **THEN** `$schema` and `docs/house-style.md` are preserved, the file stays valid JSON with 2-space indentation and a trailing newline, and only artifact-context entries under `.agentic-beacon/artifacts/` are changed

#### Scenario: Empty effective set clears only owned references

- **GIVEN** the effective set contains no contexts
- **WHEN** the reconciler runs
- **THEN** every `.agentic-beacon/artifacts/contexts/*` reference is removed from both files while all non-artifact lines and keys are preserved

### Requirement: Every wiring path reconciles references

The context-reference reconciler SHALL be invoked from `abc sync` and from the `abc adopt` accept/reject path, replacing the previous append-only wiring and prune-gated context unwiring. After any `abc sync` or `abc adopt`, the artifact-context reference set in `CLAUDE.md` and `opencode.json` SHALL equal the effective context set.

#### Scenario: Sync after de-adoption self-heals

- **GIVEN** a context was removed from `beacon.yaml` and its file no longer resolves in the warehouse
- **WHEN** the user runs `abc sync`
- **THEN** the context's reference is removed from both files without requiring an interactive prune confirmation

### Requirement: abc doctor --fix repairs reference drift

`abc doctor` SHALL continue to report broken references (a reference whose target does not exist) and unmanaged references (an artifact reference not in `beacon.yaml`). When `--fix` is set, `abc doctor` SHALL repair reference drift by invoking the same reconciler and SHALL record the repair in the applied-fixes summary. After a `--fix` run, the reference checks SHALL report no drift.

#### Scenario: --fix repairs broken and unmanaged references

- **GIVEN** a repo whose `CLAUDE.md` / `opencode.json` hold a broken reference (`contexts/linear-ops.md`, file gone) and an unmanaged reference (`contexts/cicd-flow.md`, not in `beacon.yaml`)
- **WHEN** the user runs `abc doctor --fix`
- **THEN** both references are reconciled away, the repair is listed in the applied-fixes summary, and a subsequent `abc doctor` reports no broken or unmanaged references

#### Scenario: Healthy repo is not written

- **GIVEN** a repo whose references already match the effective set
- **WHEN** the user runs `abc doctor --fix`
- **THEN** no reference repair is recorded and neither file is written
