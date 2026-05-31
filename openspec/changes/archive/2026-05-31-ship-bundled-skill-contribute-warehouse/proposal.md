## Why

Promoting local warehouse edits back to `origin` today requires the user to drive `abc warehouse contribute` themselves, decide which dirty files belong in the commit, draft a conventional commit message, and recover from `push_failed` by hand. There is no LLM-facing scaffolding around the CLI, so contribution work either stays manual (slow, easy to lump unrelated edits into one commit) or relies on the agent ad-hoc shell-driving git directly (bypasses the tracked-paths filter and the precondition checks the CLI enforces).

PER-175 asks for a bundled contribution skill. The skill's value over the raw CLI is the conversational pre-flight: separating intended edits from incidental dirty files, catching semantic duplicates against existing knowledge entries, splitting incoherent file-sets into multiple cohesive commits, and gating the whole thing on `abc warehouse lint` so the warehouse `main` is never poisoned by the contribution path itself.

## What Changes

- Add a new bundled skill `contribute-warehouse` under `libs/beacon/src/beacon/data/skills/contribute-warehouse/`, distributed alongside `record-knowledge` and `record-skill` via `_BUNDLED_SKILL_FILES` in `domains/setup/initializer.py`.
- Skill ships four PEP 723 helper scripts:
  - `resolve_warehouse.py` (reused pattern from existing skills)
  - `summarize_changes.py` (structured JSON: tracked-path filter, `git status`, `git diff --stat`, last-commit age per file)
  - `draft_commit_message.py` (deterministic scope derivation from changed paths; LLM supplies the subject)
  - `push_warehouse.py` (atomic push wrapper; on failure, prints the exact recovery command and leaves commits intact)
- Skill orchestrates the existing `abc warehouse contribute -m "<msg>"` CLI for the commit step (no `--push`); pushes once at the end via `push_warehouse.py`.
- Skill calls `abc warehouse lint <warehouse-root>` as a strict pre-flight gate. If lint exits non-zero, the skill aborts before any commit. **Depends on PER-114 / `warehouse-lint-cli-for-ci` shipping first.**
- Distribution test asserts `skills/contribute-warehouse/SKILL.md` is in the bundled-skill manifest.
- README and site-docs document the new skill alongside the existing two.

Out of scope (filed as follow-ups):
- `abc-` prefix convention rename for all bundled skills → **PER-178**
- Vectorized cross-warehouse semantic deduplication → **PER-179**
- Cross-warehouse orphan-link detection at contribute time → covered by future PER-114 work (orphan detection explicitly deferred there)
- Knowledge-base placement validation at contribute time → stays with the `record-knowledge` skill at write time

**Note:** A `--paths` flag was added to `abc warehouse contribute` during implementation. This was originally listed as out of scope but proved necessary to enable the SKILL.md's per-group commit promises (leave-for-later files and multi-commit cohesion splits). The flag scopes commits within the beacon.yaml-tracked set without bypassing any existing contracts.

## Capabilities

### New Capabilities

- `contribute-warehouse-skill`: Defines the bundled `contribute-warehouse` skill — its invocation surface, the helper scripts it ships, the conversational flow (intent triage, dedup scan, cohesion check, commit drafting, atomic push), the lint gate it imposes, and its distribution contract (must ship in `_BUNDLED_SKILL_FILES`, must wire as a slash command for every detected agent).

### Modified Capabilities

None. The skill consumes existing CLI surfaces (`abc warehouse contribute`, `abc warehouse lint`) without altering their contracts.

## Impact

**Code (agentic-beacon repo):**
- New: `libs/beacon/src/beacon/data/skills/contribute-warehouse/SKILL.md`
- New: `libs/beacon/src/beacon/data/skills/contribute-warehouse/scripts/resolve_warehouse.py` (mirrors the existing pattern in `record-skill` and `record-knowledge`)
- New: `libs/beacon/src/beacon/data/skills/contribute-warehouse/scripts/summarize_changes.py`
- New: `libs/beacon/src/beacon/data/skills/contribute-warehouse/scripts/draft_commit_message.py`
- New: `libs/beacon/src/beacon/data/skills/contribute-warehouse/scripts/push_warehouse.py`
- Modified: `libs/beacon/src/beacon/domains/setup/initializer.py` — add `skills/contribute-warehouse/SKILL.md` (and any helper scripts) to `_BUNDLED_SKILL_FILES`
- Modified: `libs/beacon/src/beacon/cli/adoption.py` — update docstring listing of bundled skills (record-knowledge, record-skill, contribute-warehouse)
- New unit tests: `libs/beacon/tests/unit/data/skills/contribute_warehouse/test_summarize_changes.py`, `test_draft_commit_message.py`
- New distribution test (or extension of existing one): asserts `contribute-warehouse` is in the bundled manifest

**Docs:**
- `libs/beacon/README.md` — add the skill to the bundled-skills list
- `site-docs/` — short page or section for `/contribute-warehouse` invocation and flow

**Release:**
- Minor version bump of `agentic-beacon` via release-please.

**Dependency:**
- This change is gated on `warehouse-lint-cli-for-ci` (PER-114) shipping. The skill cannot enforce its lint gate until `abc warehouse lint` exists.

**Out of scope:**
- Any rename of existing bundled skills (deferred to PER-178).
- Embedding-based dedup index (deferred to PER-179).
- Network reachability probing pre-push (skill relies on the CLI's existing `push_failed` return path).
- Branch-strategy automation (the skill does not create branches; it commits to whatever branch the warehouse is on).
