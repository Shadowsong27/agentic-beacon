# Design — Managed-block gitignore engine (AB-94)

## Context

Gitignore ownership is currently spread across three mechanisms with three gating rules, and the `abc adopt` path skips Tier A entirely (it calls `sync_engine.sync_all(...)` directly rather than `run_sync`, so the orchestrator's `GitignoreManager(project_root).ensure_entries()` never runs). The result is drift: Tier B nested `.gitignore`s get written while the Tier A root block does not, leaving the whole `.claude/`/`.opencode/`/`.agentic-beacon/` scaffold un-ignored. `abc doctor --fix` is a stub. This design consolidates all of it into one engine with a marker-delimited, wholesale-regenerated managed block, invoked from every wiring path, plus a doctor check that detects and repairs drift.

The grill resolved five decisions (see "Resolved decisions" below): a single managed BEGIN/END block regenerated wholesale; **all Tier A lines unconditional** (agent dirs folded in, prune retired); **surgical** legacy migration; doctor **error** + **real `--fix`** via the shared writer; and **full unification** — Tier B folded into the same engine.

## Resolved decisions

1. **Ownership model** — a single managed block delimited by `# >>> Agentic Beacon (managed) >>>` … `# <<< Agentic Beacon (managed) <<<`, regenerated wholesale each run, written by one engine called from every wiring path. Chosen over minimal per-line append because only wholesale regeneration lets the entry set evolve and lets existing repos self-heal; it also makes `doctor --fix` trivial (same writer).
2. **Gating — all Tier A lines unconditional.** The block always lists the full set regardless of tool-dir presence or declared agents. This retires the "only when agents declared" conditioning **and** the `prune_agent_dirs_gitignore_entries` path. Rationale: deterministic, tool-presence-independent output that is trivial to verify; a `.claude/skills/` line in a repo without `.claude/` is harmless. (Note: this intentionally departs from the ticket's "dir-gated" wording, per the grill.)
3. **Migration — surgical.** On first meeting a legacy loose-line `# Agentic Beacon` region: insert the managed block, dedup exact managed lines, drop the emptied legacy bare header, preserve every non-managed line. Never delete a line we don't own. Idempotent.
4. **Doctor — error severity + real `--fix`.** A new drift check reports at `error`; `--fix` calls the same engine and populates `fixes_applied` (Beacon's first working `--fix`).
5. **Scope — full unification.** Tier B nested `.gitignore`s are folded into the same managed-block engine. Their **entry sets are preserved exactly** from today's constants and locked by regression tests (the risk being folding already-working code into the new engine).

## Architecture — where the code lives

Gitignore ownership is now genuinely **cross-domain** (consumed by distribution/sync, adoption/adopt, warehouse/connect, and setup/doctor). Therefore the full policy **and** mechanism live in `core/gitignore.py`, promoted to the single source of truth. This **supersedes** the earlier decision that kept `CLAUDE_DIR_GITIGNORE_ENTRIES` / `OPENCODE_DIR_GITIGNORE_ENTRIES` local to the distribution orchestrator (those constants move into core). `core/` importing nothing from `domains/` is preserved — the engine takes a `project_root: Path` and works purely on the filesystem.

```
core/gitignore.py  (mechanism + policy — the single source of truth)
├── managed-block markers (BEGIN/END constants)
├── TIER_A_ENTRIES            (unconditional root set — 10 lines)
├── TIER_B_CLAUDE_ENTRIES     (skills/, scheduled_tasks.lock, worktrees/)
├── TIER_B_OPENCODE_ENTRIES   (skills/, command/, bun.lock, package.json, package-lock.json, node_modules/)
├── TRACKED_ON_PURPOSE        (beacon.yaml, nested .gitignores, CLAUDE.md, opencode.json, .worktreeinclude)
├── apply_managed_block(gitignore_path, entries)   # write/regenerate one block + surgical migration
├── read_managed_block(gitignore_path) -> list[str] | None
├── apply_all_gitignores(project_root)             # Tier A (root, unconditional) + Tier B (nested, dir-gated by file location)
└── diff_gitignores(project_root) -> list[GitignoreDrift]   # expected vs actual, for doctor (read-only)

consumers (all call apply_all_gitignores / diff_gitignores):
├── domains/distribution/orchestrator.py  run_sync   → apply_all_gitignores
├── domains/adoption/apply.py             accept path → apply_all_gitignores   (FIXES THE BUG)
├── domains/warehouse/connector.py        connect     → apply_all_gitignores
└── domains/setup/diagnostics.py          doctor      → diff_gitignores (check) ; cli/diagnostics.py --fix → apply_all_gitignores
```

Removed: `domains/artifact/agent.py::ensure_agent_dirs_gitignored` and `::prune_agent_dirs_gitignore_entries`; the `CLAUDE_DIR_/OPENCODE_DIR_GITIGNORE_ENTRIES` constants and conditional gitignore blocks in `orchestrator.py`; the conditional `ensure_agent_dirs_gitignored` call in `apply.py`. `GitignoreManager`'s existing `ensure_entries`/`remove_entries`/`verify_beacon_yaml_not_ignored` may be retained for backward-compat callers or refactored into the engine — the tracked-set assertion extends `verify_beacon_yaml_not_ignored` to `TRACKED_ON_PURPOSE`.

## Managed block — exact shape

Root `.gitignore` (Tier A, always all lines):

```
# >>> Agentic Beacon (managed) >>>
.agentic-beacon/config.toml
.agentic-beacon/artifacts/
.agentic-beacon/warehouse-catalog.md
.agentic-beacon/pending.yaml
.claude/skills/
.claude/commands/
.claude/agents/
.opencode/skills/
.opencode/command/
.opencode/agents/
# <<< Agentic Beacon (managed) <<<
```

Nested `.claude/.gitignore` (Tier B, written only if `.claude/` exists):

```
# >>> Agentic Beacon (managed) >>>
skills/
scheduled_tasks.lock
worktrees/
# <<< Agentic Beacon (managed) <<<
```

Nested `.opencode/.gitignore` (Tier B, written only if `.opencode/` exists):

```
# >>> Agentic Beacon (managed) >>>
skills/
command/
bun.lock
package.json
package-lock.json
node_modules/
# <<< Agentic Beacon (managed) <<<
```

## Algorithms

### `apply_managed_block(path, entries)`

1. Read the file (empty string if absent).
2. If a managed block (BEGIN/END markers) exists → replace its body with `entries` verbatim; leave everything else byte-identical. Return.
3. Else (surgical migration): drop any loose line that exactly equals a member of `entries`; if a bare legacy `# Agentic Beacon` header line remains with no owned lines beneath it in its region, drop that header; append the managed block. Preserve all other lines and their order.
4. Write only if content changed (idempotency). Preserve trailing-newline shape.

### `apply_all_gitignores(project_root)`

- Tier A: `apply_managed_block(project_root/".gitignore", TIER_A_ENTRIES)` — always.
- Tier B: if `(project_root/".claude").is_dir()` → `apply_managed_block(project_root/".claude/.gitignore", TIER_B_CLAUDE_ENTRIES)`; same for `.opencode/`.
- Guarded by `if not dry_run` at each call site, matching existing sync semantics.

### `diff_gitignores(project_root)` (doctor, read-only)

Returns drift records for: Tier A block missing/incomplete; a nested Tier B block missing/incomplete while its tool dir exists; any `TRACKED_ON_PURPOSE` file currently git-ignored. Doctor renders each as an `error`. `--fix` = `apply_all_gitignores(project_root)` then record fixes.

## Edge cases

- **No `.gitignore`** → created with just the managed block (Tier A always; Tier B when dir exists).
- **Managed block present but body stale/reordered** → body regenerated to canonical order; markers preserved.
- **Legacy header with mixed owned + unknown lines** (this repo: `.claude/scheduled_tasks.lock`, `.agentic-beacon/.legacy-migrated`, `sample-warehouse/`, scattered `.claude/agents/`) → managed lines deduped, unknowns preserved, bare legacy header dropped.
- **User manually added a managed marker** → treated as the managed block and regenerated (documented; markers are Beacon-owned).
- **Tracked set safety** → Tier A ignores subpaths only, never whole `.claude/`/`.opencode/`, so `CLAUDE.md`, `opencode.json`, `.worktreeinclude`, `beacon.yaml`, and nested `.gitignore`s are never caught. Asserted by the doctor tracked-set check.

## Testing strategy

- **Engine unit tests**: fresh-file creation; wholesale regen replaces stale body; idempotent re-apply (byte-equal); surgical migration dedups managed + preserves unknowns + drops bare legacy header; migration no-op on 2nd run; unconditional Tier A set present without tool dirs / without declared agents.
- **Tier B regression lock**: exact `.claude/.gitignore` and `.opencode/.gitignore` entry sets and dir-gating unchanged from prior behavior (guards the fold-into-engine risk).
- **Path coverage**: adopt-accept writes Tier A (the regression that would have caught the original bug) + nested Tier B; sync writes both tiers; connect routes through the engine.
- **Doctor**: detects Tier-A-missing-while-Tier-B-present; healthy project → no drift; tracked-set-ignored → error; `--fix` repairs and re-run is clean.
- **Architecture test** (`tests/unit/test_architecture.py`) still passes — `core/` imports no `domains/`.

## Out of scope

- Changing Tier B **entry contents** (only the writing mechanism changes; contents preserved).
- Reconciling the pre-existing doc-vs-code drift in the Tier B set beyond preserving current code behavior (possible follow-up).
- Any warehouse or cross-repo work.
