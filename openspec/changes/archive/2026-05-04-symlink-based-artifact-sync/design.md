# Design: Symlink-Based Artifact Sync

## Context

The Agentic Beacon CLI distributes artifacts (skills, knowledge files, harness structures) from a team-shared warehouse repository into individual project repositories. The current implementation (`domains/distribution/`) copies files physically into each project's `.agentic-beacon/artifacts/` tree, captures a sync-state SHA, and provides an `abc contribute` path to push project-side edits back into the warehouse via a manual merge.

The copy model was chosen for project isolation, snapshot semantics, and "safe local experimentation" (recorded in `openspec/specs/snapshot-based-sync/spec.md`). In practice, the intended upside hasn't materialized and the downsides have: the dominant editing workflow is an agent improving a skill or knowledge file inside whichever project happens to be open, and those edits have a strong tendency to happen in two projects before either contributes. The result is a last-writer-wins regression that the tool cannot detect because both sides diff cleanly against their stale bases.

This design collapses the duplication: the locally-cloned warehouse becomes the single on-disk copy of every synced artifact, and projects reference those files via symlinks. Editing through a project's `.agentic-beacon/artifacts/` path is literally editing the warehouse working tree. Contribution becomes a git operation on the warehouse repo, wrapped by `abc warehouse contribute` for ergonomics.

Stakeholders: framework authors (us), teams maintaining shared harnesses, agents acting on users' behalf. Platform constraint: macOS and Linux only; Windows is explicitly out of scope.

## Goals / Non-Goals

**Goals:**

- Eliminate the duplicate-copy class of regressions by ensuring exactly one physical file per logical artifact on any given machine.
- Preserve the "edit-and-test-immediately" workflow that makes harness development fast: an agent-driven edit to a skill is visible to the project's tools with no intermediate step.
- Keep the project-relative path surface (`.agentic-beacon/artifacts/…`) stable so tool configs (Claude, opencode) do not need to be rewritten.
- Provide a clean, one-shot migration for existing projects without data loss.
- Replace the removed `abc contribute` / `abc delta` commands with warehouse-scoped equivalents (`abc warehouse contribute`, `abc warehouse status`) that match the new mental model.

**Non-Goals:**

- Windows support. The design deliberately uses POSIX symlinks and rejects Windows at runtime.
- Per-project version pinning. Under this design all projects on a machine float on the warehouse working tree's current state. Pinning, if needed, is a future focused feature (e.g., `abc pin <path>`), not part of this change.
- Replacing warehouse git state management. `abc sync` does not run `git pull`; warehouse-side git (pull, branch switching, fetch) remains the user's responsibility.
- Multi-machine synchronization. Projects on different machines still rely on the warehouse remote as the sharing point.
- Preserving snapshot semantics in any form. The copy-based "snapshot at time of sync" contract is removed, not replaced.

## Decisions

### Decision 1: Symlink each artifact individually, not the directory tree
The sync engine creates real directories under `.agentic-beacon/artifacts/` and places a per-file symlink at each leaf pointing to the corresponding file inside the warehouse clone.

Why not symlink `.agentic-beacon/artifacts/` directly to `<warehouse>/`?
- The warehouse layout is a superset of what any single project wants. `beacon.yaml` filters the subset.
- Per-file symlinks let `beacon.yaml` glob expansion continue to behave as it does today — we resolve the match list, then materialize it as symlinks. The rest of the warehouse stays invisible to the project.
- Per-file links avoid tool config surprises from extra files appearing under `.agentic-beacon/artifacts/`.

Alternative considered: symlink each top-level directory (`.agentic-beacon/artifacts/skills/` → `<warehouse>/skills/`). Rejected because it exposes every skill in the warehouse to every project regardless of `beacon.yaml`.

### Decision 2: Use absolute symlink targets
Symlink targets are absolute paths to the warehouse clone. Relative targets would break if `.agentic-beacon/artifacts/` were copied or moved without the warehouse, but that copy/move is explicitly not a supported operation under this design and absolute paths eliminate a whole class of "link resolves to the wrong thing from a subshell" bugs.

Alternative: relative symlinks computed from `.agentic-beacon/artifacts/<rel>` to `<warehouse>/<rel>`. Rejected for fragility across project relocations and for making diagnostics harder (the target is not self-explanatory when printed).

### Decision 3: Project config stores the warehouse path; `abc sync` validates it
`abc warehouse connect` writes an absolute path to the warehouse clone into `.agentic-beacon/config.toml`. `abc sync` reads that path, verifies it exists and is a git working tree, and aborts with a clear error if not. No auto-discovery, no fallback to tarball or remote download.

This is a hardening of the existing `connect` behavior — the path was already stored, but sync would tolerate missing warehouses by failing partway through copy. Now the precondition is checked up front.

### Decision 4: `abc contribute` → `abc warehouse contribute` (command relocation)
Contribute is no longer a project-scoped operation; it acts on the warehouse. The command moves under a new `warehouse` subcommand group rather than staying at the root:
- `abc warehouse connect` (existing)
- `abc warehouse contribute` (new — replaces `abc contribute`)
- `abc warehouse status` (new — partially replaces `abc delta`)

The old `abc contribute` and `abc delta` commands are removed entirely (not hidden aliases). Running them produces a clear error directing the user to the new command. Keeping hidden aliases was considered and rejected — the command semantics have changed (contribute no longer merges copies, it wraps git), so preserving the name would mislead users about what it does.

### Decision 5: Migration runs inside `abc sync`, not as a separate command
When `abc sync` detects regular files under `.agentic-beacon/artifacts/` at paths that should be symlinks, it enters migration mode: for each mismatched file, compute hash against warehouse file, prompt the user to `contribute` or `discard` local changes, then replace the file with a symlink.

Why inline in `sync`?
- Users running `abc sync` for the first time after upgrading are exactly the ones who need migration. Making it a separate command (`abc migrate`) creates a discoverability problem.
- Migration is fundamentally a one-time variant of sync's core job.

Why not silent auto-resolve?
- Silent wins discard data. The whole point of this change is to stop losing data from silent conflicts.

`--contribute-local` and `--discard-local` flags provide non-interactive escape hatches (CI, scripted upgrades) with explicit, auditable choice.

### Decision 6: No project-vs-warehouse delta command
Under symlinks, the project and warehouse share inodes. There is no delta to compute. The useful concept — "what uncommitted warehouse state is attributable to work I did through this project?" — becomes `abc warehouse status`, which runs `git status` / `git diff` inside the warehouse clone, filtered by the current project's `beacon.yaml`.

This preserves the valuable parts of `abc delta` (beacon.yaml-aware scoping, per-file diff) while removing the parts that have no meaning anymore (hash comparison, `[Missing]` / `[Added]` categorization).

### Decision 7: Accept concurrent-warehouse-edit risk as user discipline
Two simultaneous project sessions both editing the same warehouse file through their respective symlinks will produce entangled changes — git cannot protect against that because both are mutating the same working tree. This design accepts the risk because:
- The primary editor is the agent, and agents within this framework typically don't run two concurrent sessions against the same artifact.
- `git status` in the warehouse (or `abc warehouse status`) surfaces the state immediately.
- Mitigating it properly (locking, per-session branches) would re-introduce the complexity we just removed.

The risk is documented in user-facing docs; no code-level protection is implemented.

### Decision 8: Philosophy shift — single write entrypoint, intended cross-project visibility
This change is not a refactor of sync mechanics; it is a shift in the product's philosophy about how harness files relate to projects. The prior model treated each project as an isolated sandbox: local edits were a feature, and merge-back was an explicit, user-mediated operation. The new model treats the warehouse clone as the single write entrypoint, with projects as read/write windows into that clone via symlinks.

A direct consequence: on a single machine, a harness edit made while working in Project A is immediately visible to Project B's agent the next time it reads that artifact. This is **intended behavior**, not a leak or a bug.

Rationale (empirical, not theoretical):
- One month of real use under the old isolation model showed that concurrent harness-development across projects on the same machine is not a workflow that actually occurs.
- When a user genuinely needs different harness behavior for different projects, the right answer is to author distinct skills/agents (which the existing artifact system already supports), not to duplicate the same artifact file across projects.
- The cost of the old isolation (the concurrent-edit regression loop) massively outweighed its realized benefit.

This is a **one-way decision**: the sync mechanism (symlinks vs copies) is mechanically reversible, but the philosophy (per-project isolation vs single-entrypoint) is not. A future change that wanted to re-introduce isolation would need to reopen this decision explicitly with fresh evidence.

The philosophy is recorded as a permanent knowledge entry at `knowledge/decisions/single-warehouse-write-entrypoint.md` (task 11.1) and referenced from the root `AGENTS.md` so future agents reading the repo inherit the rule.

## Risks / Trade-offs

- **[Risk]** Users on Windows cannot upgrade. → **Mitigation**: `abc sync` fails fast with a clear error naming the platform and pointing at macOS/Linux. Release notes call this out as a breaking change. Pre-upgrade `abc --version` remains usable to diagnose.
- **[Risk]** A project whose warehouse clone is deleted or moved produces dangling symlinks that are confusing to debug. → **Mitigation**: `abc sync` validates the warehouse path up front. `abc warehouse status` reports broken-link state. Tool-level errors (agent reads dangling symlink) include warehouse path hints via existing error messages.
- **[Risk]** Migration's interactive prompts block scripted upgrades. → **Mitigation**: `--contribute-local` and `--discard-local` flags resolve all modified files in bulk; non-interactive mode without either flag fails with a listing of files to resolve.
- **[Risk]** Snapshot-semantics users (if any exist) silently lose version pinning. → **Mitigation**: Proposal and release notes document that projects now float on warehouse HEAD. Users who need pinning check out a specific warehouse SHA or branch. An explicit pinning feature remains possible as a follow-up.
- **[Risk]** Two concurrent project sessions entangle edits in the warehouse working tree. → **Mitigation**: Documented; surfaced by `abc warehouse status`. Accepted risk.
- **[Trade-off]** Project isolation is reduced. An in-progress edit in Project A is visible to Project B's agent the moment Project B's agent reads the artifact. → This is the intended trade — isolation was the source of the regression. Teams wanting isolation per work-in-progress should use warehouse branches.
- **[Trade-off]** `.agentic-beacon/artifacts/` can no longer be committed into the project repo as a standalone snapshot. → Not a practical loss; it's already in `.gitignore` in scaffolded projects and was never intended as committable content.

## Migration Plan

**Deployment (per-project, user-initiated):**

1. User upgrades the `beacon` CLI to the release containing this change.
2. User runs `abc sync` in an existing project.
3. CLI detects copy-based tree → enters migration mode.
4. For each modified file, prompts `contribute` / `discard`. For unchanged files, converts silently.
5. After all prompts, tree is fully symlinked.
6. User commits warehouse changes (if any) via `abc warehouse contribute -m "migrate local edits"` or via direct git in the warehouse.

**Rollback strategy:**

If a user needs to roll back:
1. Pin the previous `beacon` CLI version.
2. In the project, run a one-shot restore: `find .agentic-beacon/artifacts -type l -exec sh -c 'cp --remove-destination "$(readlink "$1")" "$1"' _ {} \;` (or equivalent Python) to replace symlinks with real copies.
3. Resume on the old CLI.

Rollback is one-way safe (symlinks → copies) because the warehouse file is the source — no data is lost. The reverse (downgrade without copy restore) would leave dangling paths; the CLI's `abc doctor` should detect and repair this.

**Communication:**

- Release notes flag the breaking changes: symlinks now used, Windows removed, `abc contribute` → `abc warehouse contribute`, `abc delta` → `abc warehouse status`.
- Sample warehouse README updated to describe the new editing loop.
- CI / warehouse template updated to reflect new commands.

## Resolved Questions and Follow-Ups

All open questions from the initial draft have been resolved. Follow-up work is tracked in Linear so it doesn't block this change.

### 1. `abc warehouse pull` — deferred to [PER-106](https://linear.app/shadowsong-personal/issue/PER-106/abc-warehouse-pull-command)
**Resolution**: Not in this change. `abc sync` remains link-only; users run `git pull` in the warehouse themselves until the convenience wrapper ships.

### 2. Status command split — deferred to [PER-107](https://linear.app/shadowsong-personal/issue/PER-107/abc-status-project-level-adoption-status)
**Resolution**: There are genuinely two distinct status views and they should be two commands:

- **`abc warehouse status`** (this change): warehouse working tree vs remote, scoped by `beacon.yaml`. Answers *"what have I edited that isn't committed/pushed?"*
- **`abc status`** (PER-107, follow-up): project-scoped adoption state. Answers *"what's declared in `beacon.yaml` vs what's actually linked in this project?"* — adopted / missing / orphaned / broken link states.

This change ships only `abc warehouse status`. The project-level `abc status` is a separate scope that would have bloated this proposal.

### 3. Symlink target outside the warehouse — resolved: error
**Resolution**: `abc sync` errors out when it detects a `beacon.yaml` entry whose resolved warehouse path does not live under the configured warehouse clone root. The error names the offending entry and the resolved path. No silent skip, no symlink creation pointing outside the warehouse. This is the safe default — path mismatches almost always indicate misconfiguration and should surface loudly.

### 4. `abc doctor` — deferred to [PER-108](https://linear.app/shadowsong-personal/issue/PER-108/abc-doctor-static-checks-across-artifacts)
**Resolution**: Scope expanded beyond dangling-symlink detection. The real user need is static validation of cross-references across agents, skills, context files, and knowledge entries — links between these break silently as files are renamed or moved. PER-108 captures the full scope: link integrity, cross-reference checks (markdown links between artifacts, AGENTS.md → knowledge references, skill → doc references), and config sanity. Deliberately out of scope for this change because it's a much bigger feature than a rollback-repair helper.
