## Context

`agentic-beacon` ships two bundled skills today (`record-knowledge`, `record-skill`) under `libs/beacon/src/beacon/data/skills/`. Each is a directory containing a `SKILL.md` plus a `scripts/` folder of PEP 723 helper scripts that the skill body invokes via `uv run`. The same wiring path (`_BUNDLED_SKILL_FILES` in `domains/setup/initializer.py`, `wire_bundled_skills_per_project` in `domains/artifact/skill.py`) installs them into every connected project's per-agent skill directories and generates OpenCode command stubs for slash-command invocation.

PER-175 asks for a third bundled skill, `contribute-warehouse`, that wraps the existing `abc warehouse contribute` CLI with conversational pre-flight (intent triage, semantic dedup, cohesion split) and atomic push. Two key dependencies were established during grilling:

* The skill enforces an `abc warehouse lint` pre-flight gate. That CLI is being added by the active `warehouse-lint-cli-for-ci` change (PER-114), which is partly designed but not yet implemented. **This change is gated on PER-114 shipping first.**
* Two enhancements were explicitly deferred to follow-up tickets: PER-178 (rename existing bundled skills with an `abc-` prefix) and PER-179 (vectorized cross-warehouse semantic dedup index).

The CLI side is already mature: `domains/warehouse/contribute.py` resolves the warehouse, calls `get_tracked_paths()` (filters by `beacon.yaml` patterns), runs `git add` + `git commit` against just those paths, and returns a typed `ContributeResult` that distinguishes `committed` from `push_failed` cleanly. The skill does not need to re-implement any of that — its job is the conversational layer above.

## Goals / Non-Goals

**Goals:**

* Ship a bundled skill, distributed identically to the existing two, that an LLM can invoke via `/contribute-warehouse` to drive a safe, intent-aware contribution flow.
* Push the unique value of an LLM-driven skill — file-level intent triage, knowledge dedup, multi-commit cohesion — without re-implementing primitives that live in the CLI or the lint module.
* Keep airgap behaviour simple and reactive: rely on the CLI's existing `push_failed` return and `push_warehouse.py`'s recovery-command output. No upfront network probing.
* Atomic push: all commits land locally first, then exactly one `git push` at the end.
* Strict lint gate: if `abc warehouse lint` reports any error against the warehouse working tree, abort before committing — even if the failing files are outside the user's intended contribution scope.

**Non-Goals:**

* No `abc-` prefix on the new skill's name (deferred to PER-178; the new skill follows the existing un-prefixed convention to keep this change focused).
* No vectorized dedup index (deferred to PER-179; v1 uses an LLM-driven scan scoped to sibling files in `knowledge/<topic>/<kind>/`).
* No new CLI commands or flags. The skill consumes existing surfaces (`abc warehouse contribute`, `abc warehouse lint`) without modifying them.
* No path-scoped lint, no stash-based lint workaround. Strict gate against the full working tree.
* No branch creation or branch-strategy logic. The skill commits to whatever branch the warehouse is on.
* No knowledge-base placement validation. That stays in `record-knowledge` at write time.
* No cross-repo orphan-link detection. Out of scope for both this change and PER-114 v1.

## Decisions

### Decision 1: Skill orchestrates `abc warehouse contribute`; does not re-implement git plumbing

The skill body invokes `abc warehouse contribute -m "<msg>"` per cohesive group of files, and lets the existing CLI handle path filtering, staging, and commit. The skill never shells out to `git add`, `git commit`, or `git stash` directly.

**Alternatives considered:** Have the skill drive git directly via `subprocess`. Rejected — duplicates `get_tracked_paths()` semantics, risks drift the moment that filter changes (e.g. when `beacon.yaml.ignore_patterns` evolves), and bypasses `ensure_sync_ready()` precondition checks. Single source of truth wins.

### Decision 2: Push is the only operation the skill drives directly via git

`abc warehouse contribute` already accepts a `--push` flag, but using it would push after *each* commit in a multi-commit split. The skill instead invokes contribute *without* `--push`, lets all N commits land locally, then calls `push_warehouse.py` exactly once. This keeps multi-commit pushes to one network round-trip and one failure mode to handle.

**Alternatives considered:**

* Push per commit via `--push`: simpler call shape, but N pushes means N possible airgap failure points, awkward partial-success states, and slower flows on poor networks.
* Add a `--no-push` flag to `abc warehouse contribute` and a separate `abc warehouse push` command: a cleaner CLI surface, but expands PER-175's scope into CLI design and is not necessary — `git -C <warehouse> push` is a one-liner the helper script wraps cleanly.

### Decision 3: `abc warehouse lint` is the sole pre-flight validator; no in-skill link or frontmatter checks

PER-114 (active OpenSpec change `warehouse-lint-cli-for-ci`) ships `abc warehouse lint [PATH]` whose explicit scope covers every check Category 3 of the design grilling proposed: broken knowledge links, agent frontmatter, skill→context references, structure. Reusing it gives a single source of truth between sync-time, CI-time, and contribute-time validation.

**Alternatives considered:**

* Bake the same checks into `summarize_changes.py`: rejected — guaranteed drift the moment PER-114's lint module evolves.
* Skip lint entirely and trust the user: rejected — the whole motivation for PER-114 is that warehouse `main` was poisoned by a frontmatter-less skill. The contribute path is exactly the path that poisoning takes; gating it is the right fix.

### Decision 4: Strict lint gate against the full working tree (no path scoping, no stashing)

If the warehouse has lint-failing files in any tracked path — including files outside the user's intended contribution — the skill aborts. The user must resolve the failures (commit-fix, revert, or remove) before re-running.

**Alternatives considered:**

* Path-scoped lint (lint only the files about to be committed): would require expanding PER-114 with a `--paths` flag. Inflates scope across two changes for marginal UX benefit.
* Stash-then-lint: would mean stashing the leave-for-later set, linting, committing, popping. Contradicts the explicit "do nothing and tell" decision for leave-for-later files (any stash is a destructive-feeling op in a skill context and creates a real "user lost their work" failure mode if pop fails).
* Warn-and-proceed: defeats the purpose of the gate. PER-114 exists because warning-only validation didn't prevent regressions.

### Decision 5: Intent-first triage classifies dirty files; leave-for-later files are untouched

The skill asks the user (or infers) the contribution's intent, maps it onto dirty tracked paths, and classifies each as include or leave-for-later. Leave-for-later files are not staged, not stashed, not modified. The final summary names them so the user can address them in a later contribution.

**Alternatives considered:**

* Sweep all dirty tracked files into one commit (today's CLI behaviour): rejected — defeats half the value of a guided skill.
* Last-modified-time heuristic (auto-include files modified within N minutes): rejected — fragile, non-deterministic, magical from a UX perspective.
* Strict single-file mode: rejected — breaks legitimate multi-file commits like a brief plus its lesson.

### Decision 6: Semantic dedup is LLM-driven, scoped to `knowledge/<topic>/<kind>/` siblings

For each included file under `knowledge/**`, the skill reads peer files in the same `<topic>/<kind>/` directory and asks the LLM to flag overlaps. Files outside `knowledge/` (contexts, skills, agents) are not scanned.

**Alternatives considered:**

* Vectorized cross-warehouse search: filed as PER-179. Faster, broader scope, but adds an embedding model dependency and an index-management story that PER-175 doesn't need to ship.
* No dedup at all: leaves the "I just wrote a duplicate of an existing lesson" failure mode wide open. Cheap to catch with a directory-scoped LLM scan.
* Filename-similarity match only: catches obvious cases but misses the hard ones (different titles, same idea).

### Decision 7: Cohesion check produces N cohesive commits; user confirms split

After triage and dedup, the skill asks the LLM whether the included file set is cohesive. If yes, one commit; if no, propose a split into N groups, user confirms, then one `abc warehouse contribute` call per group.

**Alternatives considered:**

* Always one commit: produces lumpy `git log` history. The skill's killer feature is exactly this kind of judgement.
* One file per commit: too granular; legitimate multi-file commits become a noisy commit chain.

### Decision 8: Helper-script split (four files, not one mega-script)

Four scripts: `resolve_warehouse.py` (boilerplate, mirrored from existing skills), `summarize_changes.py` (read-only inspection), `draft_commit_message.py` (deterministic message construction), `push_warehouse.py` (atomic push with recovery output). Each is small (<100 LOC), single-purpose, and unit-testable.

**Alternatives considered:**

* One mega-script: a single Click app with subcommands. Tighter packaging but harder to test and harder to reason about — each subcommand mixes concerns. The existing skills have already established the multi-script pattern; consistency wins.
* Pure-markdown skill that calls the CLI for everything: works for `summarize` only if we add `abc warehouse status --json` (CLI scope creep). Cleaner to ship the script.

### Decision 9: Commit-message scope derivation is deterministic, subject is LLM-supplied

`draft_commit_message.py` takes `--paths` and `--subject` and produces a Conventional Commits message. The scope is derived deterministically from the longest common path prefix (e.g. `contexts/python-standards.md` + `knowledge/python-standards/lessons/foo.md` → scope `python-standards`; otherwise falls back to the top-level dir like `contexts`, `knowledge`, `skills`). The type prefix (`feat`, `fix`, `docs`) is also derived from path semantics. The user-facing subject is whatever the LLM (with user confirmation) supplies.

**Alternatives considered:**

* Free-form LLM message: produces inconsistent `git log` style.
* Strict commit-types enum forcing the LLM to pick from `feat|fix|docs|refactor|chore`: workable but the path-derived rule already covers 95% of cases without LLM input.

### Decision 10: Tests cover the helper scripts and the distribution contract; the conversational layer is intentionally untested

* Distribution test: assert `skills/contribute-warehouse/SKILL.md` is in `_BUNDLED_SKILL_FILES`.
* Unit tests on `summarize_changes.py`: JSON shape, age computation, tracked-path filtering against fixture warehouses.
* Unit tests on `draft_commit_message.py`: scope derivation rules, Conventional Commits formatting.
* No tests on the LLM conversational logic: it's intrinsically non-deterministic, and end-to-end tests of "did the LLM make the right judgement" are flaky and low-signal.

**Alternatives considered:** Snapshot-test the prompt body. Rejected — couples test to skill copy, brittle, no real signal on correctness.

## Risks / Trade-offs

* **[PER-114 dependency]** This change cannot ship until `abc warehouse lint` exists. → Mitigation: the design spec explicitly notes the dependency; the implementation tasks include a gate ("only merge after PER-114 lands"). If PER-114 stalls, we can ship a degraded v0 of `contribute-warehouse` that warns instead of gating, but that recreates the problem PER-114 is solving — not recommended.

* **[Strict lint gate is annoying for users with messy working trees]** Users with half-finished WIP in unrelated files will be blocked from contributing the file they care about. → Mitigation: clear error message naming the failing files and suggesting `git stash`, `git checkout`, or move-to-a-branch as user-driven recovery. The skill itself does not stash. If feedback shows this is a real friction, PER-114 can add `--paths` later (filed as a future concern, not blocking).

* **[LLM dedup scan has false positives and false negatives]** A directory-scoped LLM scan over 5–20 sibling files will miss cross-topic duplicates and may flag spurious overlaps. → Mitigation: PER-179 is the planned upgrade. v1 ships with the LLM scan because zero dedup is worse than imperfect dedup.

* **[Push failure recovery requires the user to read the recovery command and run it]** If the network comes back later, the user must run the printed `git -C <path> push origin <branch>` themselves; the skill does not retry automatically. → Mitigation: this is the documented airgap-safe contract per PER-175 acceptance criteria. Auto-retry would require a state file and a watcher — complexity not justified for v1.

* **[Skill body length pushes the LLM context budget]** Each bundled skill's `SKILL.md` is loaded into the agent context. A long skill body for `contribute-warehouse` (orchestrating 4 scripts + multi-step conversation) competes with other context. → Mitigation: keep the body lean by referencing helper scripts rather than inlining their behaviour, mirror the structure of `record-skill`'s body which has settled around 250 lines.

* **[The skill is bypassable]** Nothing forces a user to use `/contribute-warehouse`; they can still call `abc warehouse contribute` directly and skip the lint gate, dedup scan, and cohesion check. → Acceptable. The skill is opinionated guidance, not a hard policy. PER-114's CI-side lint is the policy enforcement layer; the skill is the developer-time convenience layer. They are complementary, not redundant.

## Migration Plan

* No data migration. Existing projects get the new skill on their next `abc sync` or `abc warehouse init`.
* No breaking changes to existing CLI surfaces or to `record-knowledge` / `record-skill`.
* Existing user `pending.yaml` files are unaffected (no schema change, no name changes).
* Release: minor version bump of `agentic-beacon` via release-please.

## Open Questions

* **Scope-derivation rule for `draft_commit_message.py`** — exact mapping table from path prefix → type/scope (e.g. when does a path land as `feat(skills):` vs `docs(skills):`?). To be settled in implementation; tasks.md will require a small mapping table with unit tests as part of the script's deliverable.
* **Helper scripts: copy or symlink `resolve_warehouse.py`?** — the existing skills each ship their own copy. To be decided in implementation; default is "copy, mirror existing convention" unless we want to factor out a `_shared/` script first (which is its own refactor and out of scope here).
