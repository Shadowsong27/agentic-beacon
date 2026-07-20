# Design — Context-reference reconciliation (AB-96)

## Context

Context-reference wiring into `CLAUDE.md` (an `@`-include per context) and `opencode.json` (an `instructions` array entry per context) is currently **append-only on the add side** (`wire_contexts_*` scan the physical `contexts/` directory and append) and **prune-gated on the remove side** (`unwire_pruned_artifacts` runs only on `summary.pruned_paths`, i.e. orphans the user interactively confirmed for deletion). Nothing reconciles the reference set against the declared/effective set, so a context that leaves the set without a confirmed prune — de-adopt + declined prune, non-interactive sync, warehouse rename (`linear-ops.md` → `plane-ops.md`), manual `rm`, adopt-reject — leaks a stale reference. `abc doctor` already reports these as **broken** (file gone) and **unmanaged** (undeclared) references but cannot repair them.

This is the reference-layer analog of AB-94's gitignore fix. This design consolidates add + remove into one **wholesale reconciler** scoped to the Beacon artifact namespace, invoked from every wiring path, plus a doctor `--fix` repair that reuses it.

## Resolved decisions

The grill resolved these (see the AB-96 decision tree):

1. **Ownership boundary — warehouse-artifact references only.** Beacon owns every reference under `.agentic-beacon/artifacts/` (in practice, `…/contexts/*.md`). It reconciles exactly those to the effective set and **never touches** non-artifact lines: `@AGENTS.md` and other project-local includes in `CLAUDE.md`; the `$schema` key and user-authored `instructions` entries in `opencode.json`. Chosen over "regenerate the whole include list wholesale" because Beacon has no knowledge of `@AGENTS.md` (this repo's SSOT chain) or user includes and would strip them. Chosen over a marker-block model because `opencode.json` is JSON and cannot hold comment markers — a path-prefix ownership rule is the one model that works uniformly for both files.
2. **Reconcile target — the effective set.** The desired reference set is derived from `effective_set.contexts` (what sync materializes under `contexts/`), expanded to `.agentic-beacon/artifacts/contexts/<name>.md`. Not the raw `rglob` of the directory (that is the source of the "unmanaged reference" bug) — so a de-adopted-but-still-on-disk context and a dangling warehouse-renamed reference are both dropped.
3. **Mechanism — surgical, per-file.** `CLAUDE.md`: manage only lines whose stripped form is `@<artifact-ref>` under the artifact prefix; add missing, remove departed, leave every other line (and blank-line structure) byte-identical otherwise. `opencode.json`: manage only `instructions` entries under the artifact prefix; preserve `$schema`, user entries, and relative order; re-serialize with the existing 2-space-indent + trailing-newline convention.
4. **Fix location — both paths, one function.** A single `reconcile_context_references` is called from `run_sync` (replacing append-only wiring) and from `abc adopt`; `abc doctor --fix` gets a `repair_reference_drift` that reuses the reconciler and records the repair in `fixes_applied` (the pattern AB-94 established for gitignore).
5. **Scope — reference-integrity family only.** Broken references and unmanaged references, via the reconciler. Skill/agent symlink cleanup (their own prune-gated paths), dangling-symlink relink, non-portable absolute paths, and stale beacon.yaml globs are **out of scope** — separate follow-ups.
6. **Idempotency + dry-run.** Reconcile writes only when content changes; a second run is a no-op. Under `dry_run` it computes the add/remove delta for reporting but performs no writes.
7. **Review-flagged.** It rewrites user-facing config files → the implementation-supervisor stops at a bot-clean PR rather than auto-merging. Single repo, no fan-out.

## Architecture — where the code lives

The reconciler stays in the **setup** domain alongside the existing wiring/diagnostics helpers it supersedes — it is not cross-domain (only sync, adopt, and doctor consume it, all of which already import from `domains/setup/wiring.py` and `domains/setup/diagnostics.py`). No `core/` promotion is needed (contrast AB-94, where gitignore was genuinely cross-domain).

```
domains/setup/wiring.py  (the reconciler — source of truth for reference ownership)
├── ARTIFACT_REF_PREFIX  = ".agentic-beacon/artifacts/"        # ownership boundary
├── desired_context_refs(effective_contexts) -> list[str]      # effective set -> rel paths
├── reconcile_context_references(project_root, desired_refs) -> ReferenceReconcileResult
│     ├── _reconcile_opencode_json(project_root, desired_refs)   # instructions array, surgical
│     └── _reconcile_claude_md(project_root, desired_refs)       # @-includes, surgical
└── (wire_contexts_opencode / wire_contexts_claudecode / unwire_context_* absorbed or reduced to helpers)

consumers:
├── domains/distribution/orchestrator.py  run_sync   → reconcile_context_references (replaces append-only wire_* + prune-gated context unwire)
├── domains/adoption/apply.py             accept/reject → reconcile_context_references
└── domains/setup/diagnostics.py          repair_reference_drift → reconcile_context_references ; run_project_diagnostics(--fix) calls it
```

`ReferenceReconcileResult` carries `added: list[str]` and `removed: list[str]` per file so callers (sync output, doctor `fixes_applied`) can report precisely and so dry-run can preview without writing.

Removed/superseded: the directory-scan behavior of `wire_contexts_opencode`/`wire_contexts_claudecode` (they either become internal add-only helpers driven by the desired set, or are folded into the reconciler); the **context branch** of `unwire_pruned_artifacts` (the reconciler now owns context removal) — its **skill and agent branches stay** (those are prune-driven symlink/dir removals, out of scope here).

## The desired set

```python
ARTIFACT_REF_PREFIX = ".agentic-beacon/artifacts/"

def desired_context_refs(effective_contexts: set[str]) -> list[str]:
    # effective_contexts are names like "python-standards" (resolver format)
    return sorted(f"{ARTIFACT_REF_PREFIX}contexts/{name}.md" for name in effective_contexts)
```

A reference is **Beacon-owned** iff its path (the `@`-target in CLAUDE.md, or the array string in opencode.json) starts with `ARTIFACT_REF_PREFIX`. Owned references not in the desired set are removed; desired references not present are added; everything else is untouched.

## Algorithms

### `_reconcile_opencode_json(project_root, desired_refs)`

1. Resolve `opencode.json` (root, else `.opencode/opencode.json`); if absent, return empty result.
2. Parse JSON; read `instructions: list[str]` (default `[]`).
3. Partition: `owned = [x for x in instructions if x.startswith(ARTIFACT_REF_PREFIX)]`; `kept = [x for x in instructions if not owned]` — preserving order.
4. New list = `kept` with the desired context refs merged into the position where owned refs were (append desired refs after the last kept entry, or keep them grouped where the first owned ref was — deterministic, order-stable). `removed = owned − desired`; `added = desired − owned`.
5. Write only if `instructions` changed; re-serialize with `json.dumps(data, indent=2) + "\n"`.

### `_reconcile_claude_md(project_root, desired_refs)`

1. Resolve `CLAUDE.md` (`.claude/CLAUDE.md`, else root `CLAUDE.md`); if absent, return empty result.
2. Split into lines. A line is **owned** iff `line.strip()` matches `@<path>` with `path` under `ARTIFACT_REF_PREFIX`.
3. Remove owned lines whose path ∉ desired (dropping any now-redundant blank-line pair introduced by the removal, matching the existing append style). Keep all other lines verbatim.
4. Append `@<ref>` lines for desired refs not already present, using the file's existing separator convention (blank-line-separated, as the current `wire_contexts_claudecode` does).
5. Write only if content changed.

### `reconcile_context_references(project_root, desired_refs, *, dry_run=False)`

Runs both file reconcilers; aggregates `added`/`removed`. Under `dry_run`, both reconcilers compute the delta but skip the write. Returns `ReferenceReconcileResult`.

### `repair_reference_drift(project_root, beacon_manifest, warehouse_path)` (doctor `--fix`)

Compute the effective set (same normalization as `run_sync`), build `desired_refs`, call `reconcile_context_references`; return a human-readable fix line per file that changed for `fixes_applied`. Mirrors `repair_gitignore_drift`.

## Edge cases

- **No `opencode.json` / no `CLAUDE.md`** → that file's reconcile is a no-op (return empty result); the other still runs.
- **Dangling owned reference** (warehouse rename: `linear-ops.md` gone) → not in the effective set → removed. This is the exact reported broken-reference case.
- **Undeclared-but-on-disk context** (orphan not yet pruned) → not in the effective set → its reference is removed (resolves "unmanaged reference"); the orphan **file** itself is handled by the existing prune flow, unchanged.
- **User hand-added an `@…/artifacts/contexts/x.md` include for a context they did not adopt** → treated as Beacon-owned (it is in Beacon's namespace) and removed on reconcile. Per the resolved ownership decision, that namespace is Beacon's; the user should adopt the context instead. Documented.
- **Non-artifact includes** (`@AGENTS.md`, `@docs/x.md`) and **opencode `$schema` / user instructions** → never match the prefix → always preserved.
- **Empty effective set** (no contexts) → all owned references removed from both files; non-artifact content preserved.
- **Idempotency** → after one reconcile, `added` and `removed` are both empty on the next run; no write occurs.

## Testing strategy

- **Reconciler unit tests**: add-missing; remove-departed; add+remove in one pass; preserve `@AGENTS.md` / user includes / `$schema` / user instructions and their order; idempotent re-run (byte-equal); `opencode.json` re-serialization shape (2-space indent, trailing newline); empty-effective-set clears owned refs only; dangling/warehouse-rename reference removed.
- **Path coverage**: `abc sync` after de-adopting a context removes its reference from both files (the reported bug, both directions); `abc adopt` accept adds, reject/un-adopt removes.
- **Doctor**: a repo with a broken + an unmanaged reference → both flagged; `abc doctor --fix` repairs both and the re-run is clean; healthy repo → no reference drift, no spurious write; `fixes_applied` non-empty on repair.
- **Regression against the live repo state**: reproduce this repo's `linear-ops.md` (broken) + `cicd-flow.md` (unmanaged) condition in a fixture and assert `--fix` clears both.
- **Architecture test** (`tests/unit/test_architecture.py`) still passes.

## Out of scope

- Skill/agent symlink cleanup on leave-set (their prune-gated paths are unchanged).
- Other doctor findings: dangling symlinks (relink/prune), non-portable absolute paths (rewrite), stale beacon.yaml globs — separate follow-up tickets.
- Any change to the orphan-file prune flow or its confirmation prompt (the reconciler only touches references, not artifact files).
- Any warehouse or cross-repo work.
