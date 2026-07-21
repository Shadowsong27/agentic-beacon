## MODIFIED Requirements

### Requirement: Post-adoption sync and wiring
The system SHALL immediately sync and wire adopted artifacts after updating `beacon.yaml`, using the same mechanisms as `abc sync`. Wiring of context references into `CLAUDE.md` and `opencode.json` SHALL be a **reconciliation** to the effective context set — adding references for newly-adopted contexts **and removing references for un-adopted (or rejected) contexts** — not an append-only operation. Reference removal SHALL NOT depend on an interactive prune confirmation.

#### Scenario: Adopted context is synced and wired
- **WHEN** user adopts `contexts/platform-team.md`
- **THEN** file is copied to `.agentic-beacon/artifacts/contexts/platform-team.md` AND its reference is reconciled into CLAUDE.md and opencode.json

#### Scenario: Adopted skill is synced and wired
- **WHEN** user adopts `skills/generate-tests/`
- **THEN** skill files are copied to `.agentic-beacon/artifacts/skills/generate-tests/` AND installed to `.claude/skills/generate-tests/` and `.opencode/skills/generate-tests/`

#### Scenario: Un-adopted context reference is removed
- **WHEN** user removes `contexts/platform-team.md` from `beacon.yaml` (via the adopt flow or manual edit) and syncs
- **THEN** the `@…/contexts/platform-team.md` include is removed from CLAUDE.md and the matching `instructions` entry is removed from opencode.json, without requiring an interactive prune confirmation

#### Scenario: Adoption summary printed
- **WHEN** adoption of 2 artifacts completes successfully
- **THEN** system prints "Added 2 artifact(s) to beacon.yaml" and "Synced and wired" with the list of adopted paths
