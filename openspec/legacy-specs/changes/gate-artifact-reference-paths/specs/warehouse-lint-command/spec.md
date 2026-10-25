## MODIFIED Requirements

### Requirement: Knowledge link integrity (lint-only error promotion)

The system SHALL scan every `contexts/*.md`, `skills/*/SKILL.md`, `agents/*.md`, and `knowledge/**/*.md` file for inline markdown links and SHALL report, as an error, every link that fails the canonical-artifact-links contract:

- a **cross-artifact relative** link (resolves to a different artifact inside the warehouse but is not written in canonical `.agentic-beacon/artifacts/` form),
- a **canonical** link whose resolved target file does not exist in the warehouse,
- a link (canonical or same-file) whose **anchor** does not resolve to a heading in the target file (GitHub-compatible slugify),
- a **warehouse-escape** relative link (resolves outside the warehouse root).

An **own-folder** relative link (resolving inside the linking skill's own directory) and an **absolute URL** SHALL NOT be reported. The lint-side check SHALL NOT modify the existing `scan_file_for_knowledge` primitive — that primitive retains its current warning-only posture so that `abc sync` behaviour is unchanged.

#### Scenario: Cross-artifact relative link is rejected

- **GIVEN** `skills/foo/SKILL.md` contains `[ctx](../../contexts/bar.md)` and `contexts/bar.md` exists
- **WHEN** the user runs lint
- **THEN** the system reports a malformed-link error scoped to `skills/foo/SKILL.md` (must use canonical form) and exits with code 1

#### Scenario: Canonical link to a missing target is rejected

- **GIVEN** `contexts/foo.md` contains `[X](.agentic-beacon/artifacts/knowledge/foo/bar.md)` and `knowledge/foo/bar.md` does not exist
- **WHEN** the user runs lint
- **THEN** the system reports a missing-target error scoped to `contexts/foo.md` and exits with code 1

#### Scenario: Unresolved anchor is rejected

- **GIVEN** `skills/foo/SKILL.md` contains `[X](.agentic-beacon/artifacts/contexts/bar.md#no-such-heading)`, the file `contexts/bar.md` exists, but no heading slugifies to `no-such-heading`
- **WHEN** the user runs lint
- **THEN** the system reports an unresolved-anchor error scoped to `skills/foo/SKILL.md` and exits with code 1

#### Scenario: Warehouse-escape link is rejected

- **GIVEN** `skills/foo/SKILL.md` contains `[X](../../../apps/backtest/docs/schema.md)` resolving outside the warehouse
- **WHEN** the user runs lint
- **THEN** the system reports a warehouse-escape error scoped to `skills/foo/SKILL.md` and exits with code 1

#### Scenario: Own-folder asset link is accepted

- **GIVEN** `skills/foo/SKILL.md` contains `[api](references/api.md)` and `skills/foo/references/api.md` exists
- **WHEN** the user runs lint
- **THEN** the system reports no finding for that link

#### Scenario: `abc sync` behaviour unchanged after lint shipping

- **GIVEN** a project whose adopted artifacts include a context with a broken link
- **WHEN** the user runs `abc sync` (not `abc warehouse lint`)
- **THEN** the system completes sync and logs a warning, identical to today's behaviour, exiting with code 0

## ADDED Requirements

### Requirement: `abc warehouse lint --fix` auto-rewrites fixable links

When invoked with `--fix`, `abc warehouse lint` SHALL rewrite, in place, every **cross-artifact relative** link into its canonical `.agentic-beacon/artifacts/` form, preserving any anchor fragment, and SHALL report the count of rewritten links and the files touched. The `--fix` mode SHALL NOT alter own-folder links, absolute URLs, or already-canonical links, and SHALL NOT attempt to fix **warehouse-escape** links — those remain reported as errors for human resolution. Without `--fix`, lint SHALL be read-only and make no file modifications. The one-time migration of existing artifacts to canonical form is `abc warehouse lint --fix` run once.

#### Scenario: Fix rewrites a cross-artifact relative link

- **GIVEN** `skills/foo/SKILL.md` contains `[ctx](../../contexts/bar.md#multi-repo)`
- **WHEN** the user runs `abc warehouse lint --fix`
- **THEN** the link becomes `[ctx](.agentic-beacon/artifacts/contexts/bar.md#multi-repo)` and the change is reported

#### Scenario: Fix leaves warehouse-escape links for the human

- **GIVEN** `skills/foo/SKILL.md` contains a link escaping the warehouse root
- **WHEN** the user runs `abc warehouse lint --fix`
- **THEN** the escape link is not rewritten and remains reported as an error, and the process exits with code 1

#### Scenario: Lint without --fix is read-only

- **GIVEN** a warehouse with fixable malformed links
- **WHEN** the user runs `abc warehouse lint` (no `--fix`)
- **THEN** no file is modified and the malformed links are reported as errors
