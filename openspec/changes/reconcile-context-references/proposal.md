## Why

De-adopting a context (removing it from `beacon.yaml`) leaves its reference behind in `CLAUDE.md` (an `@`-include) and `opencode.json` (an `instructions` entry). `abc doctor` on this very repo surfaces the fallout: a **broken reference** (`@…/contexts/linear-ops.md` — the file was renamed to `plane-ops.md` in the warehouse, so the include now points at nothing) and, from the mirror side, an **unmanaged reference** (`…/contexts/cicd-flow.md` present but not listed in `beacon.yaml`).

Root cause: context reference wiring is **append-only on the add side and prune-gated on the remove side** — it is never reconciled against the declared set. This is the reference-layer twin of AB-94's gitignore bug (append-per-line, no wholesale reconciliation).

- **Add side scans the directory, not the declared set.** `wire_contexts_opencode` / `wire_contexts_claudecode` (`domains/setup/wiring.py`) enumerate **every** `*.md` under `.agentic-beacon/artifacts/contexts/` via `rglob` and append any not already referenced. A file physically present but undeclared (an un-pruned orphan) gets wired → **unmanaged reference**.
- **Remove side fires only on a confirmed prune.** The *only* trigger that removes a context reference is `orchestrator.py` `if summary.pruned_paths: unwire_pruned_artifacts(...)`, and `pruned_paths` holds only orphans the user **interactively confirmed** for deletion (`confirm_prune` → `click.confirm(default=False)`). There is **no** step that drops a reference simply because a context left the declared/effective set.
- **The adopt path is additive-only too.** `domains/adoption/apply.py` calls the same append-only `wire_contexts_*`; rejecting a pending context never unwires anything.
- **`abc doctor` flags the drift but cannot repair it.** The reference checks (`_check_path_references`) already report broken/unmanaged references, but `--fix` (real since AB-94 for gitignore) does not touch references.

So a reference leaks whenever a context leaves the declared set without a confirmed prune: prune declined; a non-interactive sync; a warehouse rename (the `linear-ops.md` → `plane-ops.md` case — the file vanishes outside the prune path, leaving a dangling symlink + broken include); a manual `rm`; or an `abc adopt` reject.

This change reframes context-reference ownership the same way AB-94 reframed gitignore ownership: **adopting Beacon means the artifact-reference layer of `CLAUDE.md` / `opencode.json` is Beacon-owned**, reconciled wholesale to the effective set on every sync, with `abc doctor --fix` repairing existing drift on repos that already leaked.

## What Changes

- **One reconciler** — a shared `reconcile_context_references(project_root, artifacts_dir)` in `domains/setup/wiring.py` that, given the desired set of synced context files, brings `CLAUDE.md` and `opencode.json` to **exactly** that set: add missing references, **remove Beacon-owned references no longer in the set**. Idempotent — a second run makes no change.
- **Scoped ownership boundary.** Beacon owns only references under the `.agentic-beacon/artifacts/` namespace. Non-artifact lines are **never touched**: `@AGENTS.md` and other project-local `@`-includes in `CLAUDE.md`; the `$schema` key and any user-authored `instructions` entries in `opencode.json`; ordering of all preserved entries. (In `CLAUDE.md`/`opencode.json` the only artifact references that exist are context references — skills and agents wire as symlinks/dirs, not references — so the reference reconciler is contexts-only by nature.)
- **Reconcile target = the effective set.** The desired reference set is derived from `effective_set.contexts` (what sync actually materializes under `contexts/`), not the raw directory scan — so a de-adopted context's reference is dropped even if its file is still on disk, and a warehouse-renamed context's dangling reference is dropped.
- **Every wiring path reconciles.** `run_sync` (replacing the append-only `wire_contexts_*` + prune-gated `unwire_pruned_artifacts` context branch) and `abc adopt` (the accept/reject path in `apply.py`) both call the reconciler, so de-adopt + sync (or adopt) self-heals — including this repo on its next sync.
- **`abc doctor --fix` repairs reference drift** — a new `repair_reference_drift(project_root, beacon_manifest, warehouse_path)` in `domains/setup/diagnostics.py`, called from `run_project_diagnostics` when `--fix` is set (alongside the existing `repair_gitignore_drift`), recording the repair in `fixes_applied`. After `--fix`, the broken- and unmanaged-reference checks pass.

## Capabilities

### New Capabilities
- `beacon-context-reference-management`: the context-reference reconciler and its ownership contract — the artifact-namespace ownership boundary, wholesale reconciliation of `CLAUDE.md` `@`-includes and `opencode.json` `instructions` to the effective set (add missing / remove departed), surgical preservation of non-artifact and user lines plus ordering, idempotency, the single-reconciler-called-from-every-wiring-path guarantee, and the `abc doctor --fix` reference-drift repair.

### Modified Capabilities
- `artifact-adoption`: the "context is wired into `CLAUDE.md` and `opencode.json` on adopt" requirement is extended — wiring is now a reconcile (add **and** remove), so un-adopting a context (or rejecting it) removes its reference, not only adopting one adds it.

## Impact

- **Code**: `domains/setup/wiring.py` (new `reconcile_context_references`; the append-only `wire_contexts_opencode`/`wire_contexts_claudecode` become thin add-only helpers used by the reconciler, or are absorbed into it; the context branch of `unwire_pruned_artifacts` is superseded by reconcile — skill/agent branches stay); `domains/distribution/orchestrator.py` (`run_sync` calls the reconciler instead of append-only wiring; the prune-triggered context unwire is removed); `domains/adoption/apply.py` (accept/reject path calls the reconciler); `domains/setup/diagnostics.py` (`repair_reference_drift` + wire into `run_project_diagnostics`); `cli/diagnostics.py` (surface reference repairs in `fixes_applied`).
- **Behavior**: after any `abc sync` / `abc adopt`, the artifact-reference set in `CLAUDE.md` / `opencode.json` equals the effective context set exactly; de-adopting a context removes its reference; warehouse-renamed/deleted contexts no longer leave dangling includes; existing leaked repos self-heal on next sync or via `abc doctor --fix`.
- **Tests**: unit tests for the reconciler (add missing, remove departed, preserve non-artifact + user entries + ordering, idempotency, `opencode.json` JSON-shape preservation, dangling/warehouse-rename case); path coverage through `abc sync` and `abc adopt`; doctor detection + real `--fix` repair loop; architecture test still green.
- **Docs**: `beacon-ops.md` note that the artifact-reference layer of `CLAUDE.md`/`opencode.json` is Beacon-managed and reconciled (delivered via the warehouse per-project model).
- **Scope**: single repo (`agentic-beacon`). No warehouse or cross-repo work. Reference-integrity family only — dangling symlinks, non-portable absolute paths, and stale beacon.yaml globs remain their own follow-ups. Review-flagged (rewrites user-facing `CLAUDE.md` / `opencode.json`).
