## Why

New skills, knowledge, and context files shouldn't be wired into a project's `AGENTS.md` / `opencode.json` until they've been intentionally adopted (per the existing "adopt stays manual and intentional" rule). But during authoring and testing, these artifacts inevitably need to appear in wiring files to actually be exercised — creating awkward git diffs that risk premature commit.

Simultaneously, the two authoring skills (`record-knowledge` and `record-skill`) encode pre-warehouse assumptions that no longer hold: they write into `.agentic-beacon/artifacts/` (the project-side symlink tree), offer to edit `AGENTS.md` as if it were a knowledge index, and use a standalone interactive Python scaffolder that ships its own prompt loop. The artifact distribution model has since moved to warehouse-authored + symlink-consumed, and the `project-scoped-agents` change makes agents a declared project-level artifact with transitive skill dependencies. The record-* skills need to be rebuilt against the new world, and they need a staging surface for artifacts they just authored.

This change introduces that staging surface — `pending.yaml` — along with the `abc adopt` changes to resolve it, and rebuilds `record-knowledge` and `record-skill` to write to the warehouse, append to `pending.yaml`, and leave `AGENTS.md` / `beacon.yaml` alone. All three pieces are tightly coupled and meaningless in isolation: writers without a pending buffer have no staging surface; the pending buffer without writers stays empty; `abc adopt` without the two-sided flow has nothing to resolve.

## What Changes

- **New project-scoped file `.agentic-beacon/pending.yaml`.** Gitignored per-developer working state. Populated only by intent gestures — authoring skills append to it when they write a new or modified warehouse artifact. `abc warehouse contribute` (warehouse-scoped) does not touch it.
- **New entry schema** for `pending.yaml`: each entry carries `path` (warehouse-relative), `type` (`knowledge | skill | context | agent`), `action` (`created | modified`), `source` (free-form authoring-skill name), and `created_at` (ISO-8601 UTC). All fields required in v1.
- **New `.agentic-beacon/.last-adopt` timestamp marker.** Gitignored. Advanced only on a successful `abc adopt` commit; serves as the cursor for detecting manually-authored warehouse artifacts that skipped `pending.yaml`.
- **Alert injection in every `abc` command entry point.** When run inside a project, checks for non-empty `pending.yaml` and prints a one-line stderr notice: `⚠ N pending artifacts. Run 'abc adopt' to wire them.`
- **`abc adopt` reworked into the single resolution surface.** TUI scans both `pending.yaml` entries and warehouse files modified since `.last-adopt`. Per-entry options: **accept** (add to `beacon.yaml`, sync symlinks), **reject** (drop from `pending.yaml`; warehouse file untouched), **defer** (keep in `pending.yaml`). Session-atomic: no mutations until the user hits Apply and confirms the summary screen. `.last-adopt` advances only on successful commit.
- **`record-knowledge` rebuilt.** Writes knowledge files to `<warehouse>/knowledge/<type>/<name>.md` (not `.agentic-beacon/artifacts/`). Discovers warehouse root via `.agentic-beacon/config.toml`; hard-errors if no warehouse is connected. Offers pointer insertion into a warehouse context file (never `AGENTS.md`) under an existing section only — never auto-creating sections. On selection, LLM proposes the diff; user confirms. Appends one or two entries to `pending.yaml` (the new knowledge file plus optionally the modified context file).
- **`record-skill` rebuilt.** Writes new skills to `<warehouse>/skills/<name>/SKILL.md` (plus optional `scripts/<name>.py` PEP 723 script). Before writing, LLM scans `<warehouse>/contexts/*.md` and suggests a `requires.contexts:` list based on the skill's declared purpose; user accepts / edits / skips. Appends a single `skills` entry to `pending.yaml`.
- **RETIRE `create_skill.py`.** The existing monolithic interactive scaffolder (210 lines of `input()`-driven prompts + f-string templating) is removed. Each record-* skill instead ships thin PEP 723 helpers under its own `scripts/` directory for mechanical plumbing (config.toml parsing, pending.yaml append). Content generation, templating, and user interaction move into the skill's markdown instructions where the LLM handles them natively.
- **BREAKING for `record-knowledge` users:** writes now target the warehouse working tree, not `.agentic-beacon/artifacts/`. Running the skill in a project without `.agentic-beacon/config.toml` hard-errors with a pointer to `abc warehouse connect`. Existing flow of "writes into project's symlink tree and happens to land in warehouse by accident" stops working.
- **BREAKING for `record-skill` users:** same as above. The `uv run .../create_skill.py` invocation is removed; `record-skill` is now driven entirely through LLM conversation plus scoped helpers.

## Capabilities

### New Capabilities
- `pending-artifacts-flow`: Defines `pending.yaml` schema, authoring-skill write contract, `.last-adopt` cursor semantics, `abc` command alert, and the `abc adopt` session-atomic TUI that resolves pending + modified-warehouse entries into three-way accept/reject/defer outcomes.

### Modified Capabilities
_(None — record-knowledge and record-skill are skill artifacts, not capabilities in the OpenSpec sense. Their behavioural contract lives inside `pending-artifacts-flow` as the "authoring skill write contract" requirement set.)_

## Impact

- **Depends on:** `project-scoped-agents` merged (the field `artifacts.agents` in `beacon.yaml` and the adopt-TUI categorisation of agents as project-scoped selectables). `pending.yaml`'s adopt surface builds on top of that TUI rather than forking a second one.
- **Affected code:**
  - `libs/beacon/src/beacon/core/manifest/pending.py` — new module defining `PendingEntry` and `PendingManifest` Pydantic models with `from_yaml` / `to_yaml` round-trip.
  - `libs/beacon/src/beacon/core/gitignore.py` — add `.agentic-beacon/pending.yaml` and `.agentic-beacon/.last-adopt` to the gitignore template.
  - `libs/beacon/src/beacon/cli/main.py` (or equivalent CLI entry) — hook for the pre-command pending-alert check.
  - `libs/beacon/src/beacon/domains/adoption/discovery.py` — extend discovery to merge `pending.yaml` entries with warehouse-modified-since-`.last-adopt` files.
  - `libs/beacon/src/beacon/domains/adoption/tui.py` — accept / reject / defer three-way per-entry actions, session-atomic Apply + confirm step, `.last-adopt` advance on commit.
  - `libs/beacon/src/beacon/domains/adoption/apply.py` — session-atomic transaction semantics; reject drops from `pending.yaml` only.
  - `libs/beacon/src/beacon/data/skills/record-knowledge/SKILL.md` — rewritten for warehouse-target + pending-append flow.
  - `libs/beacon/src/beacon/data/skills/record-knowledge/scripts/resolve_warehouse.py` — new PEP 723 helper.
  - `libs/beacon/src/beacon/data/skills/record-knowledge/scripts/append_pending.py` — new PEP 723 helper.
  - `libs/beacon/src/beacon/data/skills/record-skill/SKILL.md` — rewritten; retires the interactive scaffolder.
  - `libs/beacon/src/beacon/data/skills/record-skill/scripts/resolve_warehouse.py` — new PEP 723 helper (duplicated per the "duplication over coupling" design decision).
  - `libs/beacon/src/beacon/data/skills/record-skill/scripts/append_pending.py` — new PEP 723 helper.
  - `libs/beacon/src/beacon/data/skills/record-skill/scripts/create_skill.py` — **DELETED**.
- **Affected fixtures:**
  - `examples/sample-warehouse/` — no structural change; record-* skills already ship as bundled skills but their behaviour changes.
  - Integration test fixtures mimicking a project with non-empty `pending.yaml`.
- **Affected docs:**
  - `docs/migrations/` — new page: "pending.yaml flow and record-* skill revamp".
  - `AGENTS.md` (repo root) — reflect new `abc adopt` three-way actions.
  - Any site-docs pages describing `.agentic-beacon/` layout.
- **User-facing behaviour changes:**
  - Every `abc` command surfaces the one-line pending alert when the project has non-empty `pending.yaml`.
  - `abc adopt` gains per-entry reject / defer actions and a session-atomic confirm step.
  - `record-knowledge` and `record-skill` write to the warehouse, not the project; fail loudly on missing warehouse connection.
- **Retires / supersedes:**
  - `create_skill.py` interactive scaffolder (replaced by LLM-driven flow in `record-skill`'s SKILL.md).
  - The AGENTS.md-pointer affordance in `record-knowledge` (pointers now target warehouse contexts only).
