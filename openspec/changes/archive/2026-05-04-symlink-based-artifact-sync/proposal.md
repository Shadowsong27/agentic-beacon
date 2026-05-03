# Symlink-Based Artifact Sync

## Why

The current copy-based sync model distributes artifacts (skills, knowledge, harness structures) as real file copies into each project's `.agentic-beacon/artifacts/` directory. When the same artifact is edited in two different project copies before either is contributed back, the second contribution silently overwrites the first — "last writer wins" — causing regressions that are invisible until the artifact is exercised. The merge-back cycle (edit → contribute → pull → edit again in the other project) compounds the problem and makes iteration on the team's shared harness fragile.

The practical trigger for this change is the most common workflow: an agent edits a skill or knowledge file inside a project to improve the harness, then hours later the same agent in another project edits the same file. Both edits are against the same stale base. Contributing both produces silent regressions.

The root cause is that two on-disk copies exist for one logical file. The fix is to collapse that duplication: the warehouse clone is the single on-disk source of truth, and projects reference it via symlinks.

## What Changes

- **BREAKING**: `abc sync` replaces file copies with symlinks pointing into the local warehouse clone. Project-local artifact files are no longer independent copies.
- **BREAKING**: `abc contribute` is removed. It is replaced by `abc warehouse contribute`, a thin wrapper around `git add` + `git commit` executed inside the warehouse clone, invokable from any project directory.
- **BREAKING**: `abc delta` is removed. Drift between project and warehouse no longer exists because they share the same inode. A new `abc warehouse status` (or `abc warehouse delta`) command surfaces uncommitted/unpushed warehouse state instead.
- **BREAKING**: Windows is explicitly unsupported. `abc sync` fails loudly on Windows with a clear error message; no hardlink or copy fallback is provided.
- `abc sync` adds a one-shot migration path: when existing real-file copies are detected, it runs a final delta pass, prompts the user to contribute or discard local changes, then replaces the files with symlinks.
- `abc sync` does NOT run `git pull` in the warehouse clone; warehouse git state remains the user's responsibility. A future `abc warehouse pull` may be added but is out of scope.
- `.agentic-beacon/artifacts/` directory is preserved as a directory of symlinks so tool configs (Claude, opencode) continue to see a stable project-relative path.
- The warehouse clone is required to be locally present at sync time (already the common case). No tarball/remote-only mode.

## Capabilities

### New Capabilities

- `symlink-based-sync`: Symlink-based distribution of warehouse artifacts into projects. Covers link creation, idempotency, beacon.yaml glob expansion, missing-warehouse detection, and Windows rejection.
- `warehouse-contribute-command`: `abc warehouse contribute` command that stages and commits changes inside the warehouse clone from any project directory, replacing the removed project-level `abc contribute`.
- `warehouse-status-command`: `abc warehouse status` command that shows uncommitted and unpushed state of warehouse artifacts, replacing the removed `abc delta` with a warehouse-scoped equivalent.
- `copy-to-symlink-migration`: One-time migration behavior inside `abc sync` that converts existing copy-based artifact trees into symlinks after surfacing and resolving any pending local changes.

### Modified Capabilities

- `snapshot-based-sync`: REMOVED. Copy semantics ("pure copy, never symlinks", "copied files are independent", "warehouse changes don't auto-update project") are the bugs this change eliminates. Replaced wholesale by `symlink-based-sync`.
- `delta-contribution-workflow`: REMOVED. Project-vs-warehouse delta no longer exists. The remaining useful idea — comparing warehouse local state against its remote — is covered by the new `warehouse-status-command`.

## Impact

- **Code**: `domains/distribution/` (sync engine, distributor, state, reset) rewritten around symlinks. `domains/contribution/` removed or reduced to a warehouse-git wrapper. New `domains/warehouse/` operations for `contribute` and `status`. CLI handlers in `cli/` updated: `abc contribute` removed, `abc delta` removed, `abc warehouse contribute` and `abc warehouse status` added.
- **Specs**: `openspec/specs/snapshot-based-sync/` and `openspec/specs/delta-contribution-workflow/` archived. New specs added for each capability above.
- **Warehouse contract**: Local clone of the warehouse is now a hard requirement of `abc sync`. `abc connect` must resolve and record the warehouse path; `abc sync` must validate it exists and is a git working tree.
- **Platforms**: Windows support removed. macOS and Linux only.
- **Users**: All existing projects must run `abc sync` once after upgrading to trigger migration. Users on Windows will be unable to upgrade without switching platforms.
- **Documentation**: mass sweep across README, AGENTS.md, guides, docs, knowledge, sample warehouse, and baked-in `abc init` templates to remove stale copy-model language and describe the new symlink model and single-write-entrypoint philosophy. Stale content moves to a top-level `archive/` tree rather than being deleted, preserving historical context.
- **Philosophy shift (recorded as a new knowledge decision)**: under the new model, the warehouse clone is the single write entrypoint, and per-machine cross-project visibility of harness edits is **intended**, not a bug. One month of empirical use of the old isolation model showed that concurrent-project harness development does not happen in practice; when it does, the correct response is to author distinct skills/agents, not to duplicate files.
- **Follow-ups (tracked, not in this change)**:
  - [PER-106](https://linear.app/shadowsong-personal/issue/PER-106/abc-warehouse-pull-command): `abc warehouse pull` convenience wrapper.
  - [PER-107](https://linear.app/shadowsong-personal/issue/PER-107/abc-status-project-level-adoption-status): `abc status` for project-level adoption state (declared vs linked).
  - [PER-108](https://linear.app/shadowsong-personal/issue/PER-108/abc-doctor-static-checks-across-artifacts): `abc doctor` for static validation of cross-references between agents, skills, context, and knowledge files.
