## Why

Beacon owning a wired repo's `.gitignore` is currently a fragmented, drift-prone side effect rather than a guaranteed capability. The evidence (AB-94, found onboarding **agentic-conductor** during HARN-65): `abc adopt`/`abc sync` had emitted the **Tier B** nested `.gitignore` files — which even reference "the root .gitignore (Tier A)" in their own comments — but the **Tier A** block was never written to the root `.gitignore`. The whole `.claude/`, `.opencode/`, `.agentic-beacon/` scaffold showed as untracked and nothing Beacon-owned was actually ignored; a naive `git add -A` would have committed `artifacts/`, symlinks, `node_modules/`, and lockfiles.

Root cause: gitignore ownership is spread across three mechanisms with three different gating rules, and one whole entry point skips Tier A entirely.

- Tier A base entries (`config.toml`, `artifacts/`, `pending.yaml`) are written by `GitignoreManager.ensure_entries()` **only on the `run_sync` path** — `abc adopt` calls `sync_engine.sync_all(...)` directly and never runs it.
- `warehouse-catalog.md` and the beacon-owned symlink dirs (`.claude/skills|commands/`, `.opencode/skills|command/`) are **never written to the root** at all.
- Agent dirs (`.claude/agents/`, `.opencode/agents/`) are written by `ensure_agent_dirs_gitignored` **only when agents are declared**, and pruned otherwise.
- Entries are appended **per-line with no end marker**, so a legacy/partial block can never self-heal, and `abc doctor --fix` is a **no-op stub** (`fixes_applied` is never populated).

This change reframes gitignore ownership from "a bug to patch once" into a first-class Beacon capability: after `abc adopt`/`abc sync`, a wired repo is **guaranteed** to have both gitignore tiers present and correct, and `abc doctor` surfaces (and `--fix` repairs) drift on repos that already exist.

## What Changes

- **One managed-block gitignore engine** in `core/gitignore.py`, promoted to the single cross-domain source of truth for Beacon gitignore ownership. It writes a **marker-delimited managed block** (`# >>> Agentic Beacon (managed) >>>` … `# <<< Agentic Beacon (managed) <<<`) that is **regenerated wholesale** on every run. Both tiers flow through this one engine.
  - **Tier A** (root `.gitignore`) — every managed line is written **unconditionally** (independent of which tool dirs exist): `.agentic-beacon/{config.toml, artifacts/, warehouse-catalog.md, pending.yaml}` + `.claude/{skills,commands,agents}/` + `.opencode/{skills,command,agents}/`.
  - **Tier B** (nested `.claude/.gitignore`, `.opencode/.gitignore`) — **folded into the same engine** (full unification). The nested files still materialize only when their tool dir exists (inherent — the file lives inside it); the **entry sets are preserved exactly** from today's `CLAUDE_DIR_GITIGNORE_ENTRIES` / `OPENCODE_DIR_GITIGNORE_ENTRIES` and locked by regression tests.
- **Single writer, called from every wiring path** — `run_sync`, `abc adopt` (the path that skipped Tier A — the reported bug), and `abc warehouse connect`. All three converge on the same managed-block application, so no path can emit one tier without the other.
- **Retire the conditional agent-dir logic** — `ensure_agent_dirs_gitignored` / `prune_agent_dirs_gitignore_entries` and the "only when agents declared" gating are removed; agent dirs are just three more unconditional lines in the Tier A block.
- **Surgical, idempotent migration** — when the engine first meets a legacy loose-line `# Agentic Beacon` region, it inserts the managed block, removes any loose line that exactly matches a managed entry (no double-ignore), drops the now-empty legacy bare header, and **preserves every non-managed line** (`.legacy-migrated`, `sample-warehouse/`, user lines). Re-runs are no-ops.
- **`abc doctor` gitignore-drift check (severity: error)** — flags a wired repo whose Tier A managed block is missing/incomplete, whose Tier B nested block is missing/incomplete when the tool dir exists (directly catching the reported "Tier B present, Tier A absent" case from both sides), or whose tracked-on-purpose set (`beacon.yaml`, both nested `.gitignore`s, `CLAUDE.md`, `opencode.json`, `.worktreeinclude`) is ignored.
- **`abc doctor --fix` becomes real** — it calls the same managed-block engine to repair Tier A and Tier B in place and records the repairs in `fixes_applied`. This is Beacon's first working `--fix`.

## Capabilities

### New Capabilities
- `beacon-gitignore-management`: the managed-block gitignore engine and its ownership contract — the marker-delimited managed block, wholesale regeneration, the two tiers and their (unconditional Tier A / preserved Tier B) entry sets, the surgical migration of legacy loose-line blocks, the single-writer-called-from-every-wiring-path guarantee, the tracked-on-purpose set that must stay visible, and the `abc doctor` drift check + real `--fix`.

### Modified Capabilities
- `project-agent-wiring`: the "abc setup adds agent directories to .gitignore" requirement is superseded — agent dirs (`.claude/agents/`, `.opencode/agents/`) are now owned unconditionally by the Tier A managed block rather than gated on declared agents, and the `update_agent_gitignores` / prune-on-empty behavior is removed.

## Impact

- **Code**: `core/gitignore.py` (managed-block engine: apply/read/migrate + expected-vs-actual diff; Tier A + Tier B entry-set constants promoted here from the distribution orchestrator); `domains/distribution/orchestrator.py` (call the unified engine; remove `CLAUDE_DIR_GITIGNORE_ENTRIES` / `OPENCODE_DIR_GITIGNORE_ENTRIES` and the conditional agent-dir calls); `domains/adoption/apply.py` (invoke the unified engine on the adopt path — fixes the bug); `domains/warehouse/connector.py` (route through the engine); `domains/artifact/agent.py` (retire `ensure_agent_dirs_gitignored` / `prune_agent_dirs_gitignore_entries`); `domains/setup/diagnostics.py` (gitignore-drift check); `cli/diagnostics.py` (wire real `--fix`).
- **Behavior**: every beacon-wired repo converges on the same two-tier managed gitignore after any `adopt`/`sync`/`connect`; agent dirs are ignored whether or not agents are currently declared; existing repos with legacy blocks self-heal on next run or via `abc doctor --fix`.
- **Tests**: unit tests for the engine (wholesale regen idempotency, surgical migration preserving unknowns, unconditional Tier A set, Tier B entry-set regression lock), doctor drift-detection + `--fix` repair, and the adopt-path Tier A coverage that would have caught the original bug.
- **Docs**: `beacon-ops.md` two-tier gitignore section + `AGENTS.md` reflect the managed-block engine and the unconditional/dir-gating decision.
- **Scope**: single repo (`agentic-beacon`). No warehouse or cross-repo work. Review-flagged (core `adopt`/`sync`/`connect` path, high blast radius across every wired repo).
