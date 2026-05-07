## Context

This change is the resolution of PER-111 (pending artifacts flow) combined with the long-overdue revamp of `record-knowledge` and `record-skill` against the current artifact model. The three pieces are tightly coupled: `pending.yaml` without authoring-skill writers is an empty file nobody populates; the record-* revamp without a staging buffer has nowhere to send its output without polluting `beacon.yaml`; and `abc adopt` without both sides has nothing distinctive to resolve.

Predecessor context that shapes this change:

- **`project-scoped-agents`** (in progress, 31/45 tasks done at planning time) introduces `artifacts.agents` to `beacon.yaml` and reworks the `abc adopt` TUI to treat agents as project-scoped selectables with transitive skill dependencies. This change builds on that TUI rather than forking a second one — the three-way accept/reject/defer semantics graft onto the existing TUI infrastructure (`textual`-based, already in tree).
- **Artifact distribution model.** The warehouse is the single write target for artifacts; projects consume via per-file symlinks under `.agentic-beacon/artifacts/`. The record-* skills today write into the symlink tree, which happens to work but backwards — this change realigns them to write into the warehouse working tree directly, discovered via `.agentic-beacon/config.toml`.
- **`config.toml` as the warehouse pointer.** Already modelled as `WorkspaceConfig` in `core/manifest/workspace.py`; already the canonical answer for "where is the warehouse" in every existing command (`sync`, `contribute`, `status`, `diagnostics`). Authoring skills adopt the same mechanism.
- **Current `create_skill.py`.** 210-line interactive scaffolder with three responsibilities (prompting, templating, file writes), all of which the LLM handles more naturally in markdown instructions. Its hardcoded target (`.agentic-beacon/artifacts/skills/<name>/`) is incompatible with the warehouse-write model.

## Goals / Non-Goals

**Goals:**
- Introduce `.agentic-beacon/pending.yaml` as the single staging buffer for authored artifacts; populate via authoring skills only; never via `abc sync` or `abc warehouse contribute`.
- Rebuild `record-knowledge` and `record-skill` to target the warehouse working tree, append to `pending.yaml`, and not touch `AGENTS.md` / `beacon.yaml` directly.
- Extend `abc adopt` with three-way per-entry actions (accept / reject / defer) and session-atomic commit (no mutations until confirm; full rollback on mid-commit failure).
- Add a one-line alert to every in-project `abc` invocation when `pending.yaml` is non-empty.
- Retire `create_skill.py`; replace with LLM-driven scaffold flow + per-skill PEP 723 helper scripts for mechanical plumbing only.

**Non-Goals:**
- Refactoring the warehouse-side artifact taxonomy (`knowledge/`, `skills/`, `contexts/`, `agents/`). Unchanged.
- Introducing a shared helper module across skills. Each record-* skill carries its own `scripts/` directory with independent copies — duplication is cheaper than coupling.
- Changing `abc warehouse contribute`. It remains warehouse-scoped and orthogonal to `pending.yaml`.
- Uninstalling or pruning artifacts on reject. Reject touches `pending.yaml` only; warehouse files are preserved.
- Per-entry atomic mutations during the adopt TUI session. Commits are session-atomic; partial state during choice-marking is never persisted to disk.
- Auto-backfilling `pending.yaml` on upgrade. Users with hand-authored warehouse artifacts rely on the `.last-adopt` diff path to surface them.
- A separate `abc try` command. `abc adopt` is the single resolution surface for both pending and warehouse-modified entries.

## Decisions

### Decision 1 — Warehouse root via `config.toml`, not symlink resolution

**Chosen:** Authoring skills walk up from `$PWD` to find `.agentic-beacon/config.toml` and read `[warehouse] local_path`. Hard-error if the file is absent or the field is missing.

**Alternatives considered:**

- **Symlink resolution.** `readlink .agentic-beacon/artifacts/<something>` → walk up to warehouse root. Rejected: fails when the project has zero adopted artifacts (no symlinks exist yet), relies on per-platform `readlink -f` semantics, and doesn't match the rest of the codebase where `config.toml` is already the canonical answer.
- **Environment variable `BEACON_WAREHOUSE_ROOT`.** Rejected: introduces external state that has to be kept in sync with `config.toml`; invisible per-shell configuration invites drift.
- **New pointer file at `.agentic-beacon/warehouse-path`.** Rejected: would duplicate what `config.toml` already stores.

**Rationale:** `config.toml` is the system of record for "which warehouse is this project connected to." Every existing `abc` command already uses it (`preconditions.ensure_sync_ready`). Authoring skills adopting the same mechanism keeps one discovery path across the codebase.

### Decision 2 — `pending.yaml` entry schema: five required fields, no optionals

**Chosen:** `path`, `type`, `action`, `source`, `created_at` — all required in v1. `source` is free-form string; everything else is a fixed enum or typed scalar.

**Alternatives considered:**

- **Minimal (`path` only).** Rejected: insufficient for TUI grouping, can't distinguish created-vs-modified, no provenance for mixed-source populated files.
- **Rich + wiring hints** (e.g. `suggested_target: artifacts.contexts`). Rejected as premature coupling: the TUI is the source of wiring truth per PER-111's design; embedding writer-side hints couples writers to TUI logic and creates drift when adopt logic evolves. Adopt recomputes wiring from `type` alone.
- **`source` as fixed enum** (e.g. `record-knowledge | record-skill | manual`). Rejected: every new authoring skill would require a beacon release to extend the enum. Free-form string with graceful "unknown source" handling is strictly more extensible.

**Rationale:** Five fields are the minimum to support the TUI's display/grouping/dedup logic without over-fitting to current behaviour. Free-form `source` keeps the schema open to future authoring skills without beacon releases.

### Decision 3 — Pointer targets are warehouse contexts only; never `AGENTS.md`

**Chosen:** `record-knowledge` offers `<warehouse>/contexts/*.md` plus "skip" as the pointer target list. `AGENTS.md` never appears.

**Alternatives considered:**

- **Keep `AGENTS.md` as the default target** (current behaviour). Rejected: `AGENTS.md` holds project-specific context — editing it from a warehouse-authoring skill is a category confusion, and pointers from a project-local file can't propagate to other projects that adopt the same knowledge.
- **Let the user pick any file** (warehouse or project). Rejected: blurs the project-vs-warehouse boundary and invites pointer sprawl. The distinction matters.
- **Drop the pointer step entirely.** Rejected: regresses discoverability. Knowledge without a context pointer is effectively orphaned; the existing "Brief / Read" pattern in warehouse contexts is exactly what makes the knowledge base navigable.

**Rationale:** Knowledge files exist to be found through context files. The context-pointer edge is how skills and agents transitively surface relevant knowledge via `requires.contexts`. `AGENTS.md` is out-of-band for that model.

### Decision 4 — Inserts must land under an existing section; never auto-create section headings

**Chosen:** When inserting a pointer into a context file, the LLM identifies an existing section (`## <heading>`) that best fits the topic. If none fits, the skill surfaces that and asks the user to skip or pick a section manually. The skill never auto-creates section headings.

**Alternatives considered:**

- **Allow auto-create when no section fits.** Rejected: creating a new section is a structural change to the context file; it should be a deliberate user decision, not a side effect of `record-knowledge`. Auto-creation produces noisy diffs and invites one-off section sprawl.
- **Always append at the end of the file.** Rejected: order in context files carries semantic grouping; end-appending scrambles that.

**Rationale:** Record-knowledge's job is content; structural edits to context files are a human decision. The "skip or pick manually" fallback preserves the skill's usefulness for edge cases without letting it quietly reshape context files.

### Decision 5 — Session-atomic adopt with explicit Apply + confirm

**Chosen:** TUI accumulates choice marks in memory. No filesystem or config mutation until the user hits Apply and confirms the summary screen. On confirm, all mutations execute as a single logical transaction; any mid-commit failure triggers a full rollback to pre-commit state.

**Alternatives considered:**

- **Per-entry atomic** (apply each choice as the user clicks it). Rejected: gives no path to "undo" within a session; a mistake marked at entry 1 is already committed by entry 3. Also fragile against crashes mid-session.
- **Session-atomic, per-category batches** (accept all → reject all → defer all). Effectively equivalent to the chosen design but framed differently. Chosen design is more transparent to users.

**Rationale:** The confirm step is worth the extra keystroke because the adopt TUI's mutations are substantive (beacon.yaml edits, symlink syncs, pending.yaml rewrites). Preview-then-commit is the pattern users expect for anything touching git-tracked state.

### Decision 6 — Reject drops from `pending.yaml` only; warehouse untouched

**Chosen:** Rejecting an entry removes it from `pending.yaml`. The warehouse file is preserved byte-identical. Warehouse cleanup is separately the user's deliberate decision.

**Alternatives considered:**

- **Reject → delete warehouse file.** Rejected: `pending.yaml` is project-local state; the warehouse is shared across projects. One project's reject MUST NOT mutate shared state.
- **Reject → prompt whether to also delete warehouse file.** Rejected: even an opt-in cross-project mutation is a bad pattern. Keep the project / warehouse axes orthogonal.

**Rationale:** The invariant "pending.yaml is local working state; warehouse is shared" keeps the mental model simple and prevents accidental cross-project deletion.

### Decision 7 — Retire `create_skill.py`; no `_shared/` helper module

**Chosen:** Delete `libs/beacon/src/beacon/data/skills/record-skill/scripts/create_skill.py`. Move content generation, templating, and prompting into the skill's markdown instructions. Keep a thin `scripts/` directory per record-* skill with PEP 723 helpers (`resolve_warehouse.py`, `append_pending.py`). Duplicate these helpers across the two skills rather than introducing a shared module.

**Alternatives considered:**

- **Keep `create_skill.py`, rewrite it for warehouse targets.** Rejected: rewriting line-by-line would preserve a layer of indirection with no functional upside. The LLM handles prompting, templating, and conversation more naturally.
- **Introduce `_shared/authoring_helpers.py`.** Rejected: a shared module becomes an implicit contract between every future authoring skill. Two small duplications are cheaper than one coupling point that expands over time.
- **Move all plumbing into markdown** (no scripts). Rejected: YAML/TOML parsing and filesystem walks expressed as markdown instructions invite LLM drift; these deterministic bits belong in Python.

**Rationale:** The right split is LLM for judgment and content, PEP 723 helpers for mechanical plumbing. Per-skill ownership of helpers keeps skills independently reshapable.

### Decision 8 — `requires.contexts` suggestion at scaffold time

**Chosen:** `record-skill` scans `<warehouse>/contexts/*.md` and proposes a `requires.contexts:` list for the new skill, with rationale per match. User accepts, edits, or skips. Suggestion writes to the generated SKILL.md frontmatter; empty list permitted; always hand-editable afterward.

**Alternatives considered:**

- **Force the user to declare `requires.contexts` explicitly.** Rejected: doubles user work for a field most new skills start empty.
- **Always default to empty; require post-scaffold hand-edit.** Rejected: the warehouse contexts are readable at scaffold time; there's no reason to punt the suggestion to later.

**Rationale:** Opportunistic suggestion is cheap (read the warehouse we already know how to find) and removes friction for the common case. The escape hatch of "skip" preserves the hand-edit path.

### Decision 9 — `.last-adopt` advances only on successful commit

**Chosen:** The marker is touched only when `abc adopt` commits successfully. Session open, cancel, or Ctrl-C leaves the marker unchanged.

**Alternatives considered:**

- **Advance on session open.** Rejected: breaks the invariant that the marker represents "last successful resolution"; cancelled sessions would hide warehouse-modified entries on next run.
- **Advance on any session close, success or cancel.** Same problem.

**Rationale:** The marker's purpose is to serve as a cursor for "what has the user actually resolved." Tying advancement to successful commit is the only semantics that preserves that.

### Decision 10 — Alert suppressed outside a project

**Chosen:** The pre-command pending alert only fires when `.agentic-beacon/config.toml` is discoverable via cwd-walk. Commands like `abc warehouse init` run from fresh directories do not trigger the check.

**Alternatives considered:**

- **Always attempt the alert check.** Rejected: emits confusing no-op logs outside projects; couples unrelated commands to a project-scoped invariant.

**Rationale:** Symmetric with how the rest of the codebase scopes "is this a project" — `config.toml` discoverability is the boolean.

## Risks / Trade-offs

**[Risk]** Users accustomed to `create_skill.py`'s interactive prompts get confused by the new LLM-driven flow, particularly in non-LLM contexts (e.g. running the skill from plain shell).
**Mitigation:** The skill is explicitly an LLM-driven authoring tool — invoking it without an LLM context has never been a supported workflow. Release notes and `record-skill`'s updated SKILL.md clarify this.

**[Risk]** Authoring skills writing directly into the warehouse working tree pollute the warehouse's git status even when the user hasn't committed their work.
**Mitigation:** This is intentional and already how the current record-* skills work (via the symlink path). The `abc adopt` flow is the explicit hand-off point; users who want to discard can `git restore` in the warehouse. `pending.yaml` serves as a handoff record for exactly this state.

**[Risk]** Session-atomic adopt with rollback-on-failure makes the commit logic significantly more complex than today's linear mutation.
**Mitigation:** The transaction model is bounded — three files (`beacon.yaml`, `pending.yaml`, `.last-adopt`) plus N symlinks. Pre-commit snapshots of the three files plus idempotent symlink operations give a tractable rollback implementation. Integration test covers mid-commit failure.

**[Risk]** `.last-adopt` + `pending.yaml` diverge (e.g. file corruption, manual edit, partial git operations), surfacing stale or inconsistent adopt candidates.
**Mitigation:** Both files are gitignored local state — any inconsistency is recoverable by deleting them and re-running `abc adopt`, which falls back to "everything is new." The alert system surfaces obvious divergences (e.g. non-empty `pending.yaml` after user thought they adopted) via the count mismatch.

**[Risk]** The warehouse-context-only pointer restriction frustrates users who have adopted a context into their project and want the pointer to appear "in their AGENTS.md" automatically.
**Mitigation:** The pointer lands in the warehouse context; when the user adopts that context (already in `beacon.yaml`), the symlink surfaces the updated context body — the pointer propagates automatically via the adopt mechanism. No manual `AGENTS.md` edit needed. This is actually the better UX; the restriction protects it.

**[Risk]** Two record-* skills each shipping independent copies of `resolve_warehouse.py` and `append_pending.py` creates drift when one skill fixes a bug the other doesn't.
**Mitigation:** Accepted as the cost of avoiding cross-skill coupling. The helper scripts are each <50 lines; divergence is visible in `git diff`. A future change can consolidate if duplication genuinely becomes painful — but introducing shared infrastructure speculatively is the worse failure mode.

## Migration Plan

**For this repo (agentic-beacon):**

1. Land `project-scoped-agents` first (already in progress, blocking this change).
2. Implement in the order: (a) `pending.py` core module + gitignore update, (b) `.last-adopt` handling in adoption domain, (c) alert hook in CLI entry point, (d) `abc adopt` TUI three-way actions + session-atomic commit, (e) `record-knowledge` rewrite + new `scripts/`, (f) `record-skill` rewrite + new `scripts/`, (g) delete `create_skill.py`.
3. Regenerate `examples/sample-warehouse/` if the sample's gitignore template changes.
4. Integration tests covering the happy path (author → pending → adopt → wired) and rollback path (author → adopt → mid-commit failure → state preserved).
5. Update migration doc and `AGENTS.md` wiring notes.

**For existing users:**

1. Upgrade Beacon. Existing projects gain `.agentic-beacon/pending.yaml` and `.agentic-beacon/.last-adopt` as optional local state (both gitignored).
2. First `abc adopt` after upgrade: `.last-adopt` is absent, so every warehouse file modified since the existing sync cursor appears as a discovery candidate. Users either defer everything (noisy-but-safe) or accept selectively. Subsequent adopts are tight.
3. Authoring skills (`record-knowledge`, `record-skill`) work differently on first use — warehouse-target write, `pending.yaml` append. Release notes call this out.

**Rollback:** Revert the Beacon release. `pending.yaml` and `.last-adopt` become unknown local files; older Beacon ignores them. `record-knowledge` / `record-skill` fail hard on invocation (they depend on the new flow). Users pin to the previous Beacon version and re-upgrade once the issue is fixed.

## Open Questions

**Q1:** Should the pre-command pending alert be suppressible via a flag (e.g. `--quiet-pending` or `BEACON_NO_ALERT=1`) for scripted contexts?

**Proposed default:** No, not in v1. The alert is one line on stderr; scripts can already redirect `2>/dev/null`. Adding a suppression flag invites forgetting to clear the flag in interactive sessions. Revisit if real users ask.

**Q2:** When an authoring skill fails partway through (e.g. warehouse write succeeds, `pending.yaml` append fails), what's the recovery?

**Proposed default:** Hard error with both paths surfaced. The skill prints: "Wrote `<warehouse path>` but failed to append to `pending.yaml`: <reason>. The warehouse file exists; to register it, either fix `pending.yaml` and re-run, or discard via `git restore` in the warehouse." Simple, explicit, no implicit retries.

**Q3:** Should `pending.yaml` entries carry an expiry / age-out rule (e.g. "older than 30 days → auto-reject")?

**Proposed default:** No. Deferred entries stay until the user resolves them. Auto-expiry would silently drop state the user explicitly kept. If the buffer bloats over time, that's a signal the user should `abc adopt` more often, not a case for automatic cleanup.
