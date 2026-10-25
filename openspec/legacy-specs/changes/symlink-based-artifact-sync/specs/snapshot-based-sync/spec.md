# snapshot-based-sync (delta)

## REMOVED Requirements

### Requirement: Pure copy sync from warehouse to project
**Reason**: Copy-based sync is the root cause of the concurrent-edit regression problem this change fixes. Two on-disk copies of the same logical artifact allow divergent edits that silently clobber each other at contribution time.
**Migration**: On next `abc sync`, the `copy-to-symlink-migration` capability converts existing copies into symlinks after surfacing any local changes. See `symlink-based-sync` for the new sync semantics.

### Requirement: Snapshot at point in time
**Reason**: Point-in-time snapshots created implicit version pinning per project, which produced the drift that `abc contribute` then had to reconcile. Under the new model, all projects float on the warehouse working tree's current state. Explicit pinning, if needed later, will be introduced as a separate focused feature rather than as a side effect of sync.
**Migration**: Projects that relied on snapshot isolation should treat the warehouse clone's git history as the versioning mechanism (checkout a specific SHA in the warehouse, or maintain a pinned branch) instead of relying on stale project copies.

### Requirement: Idempotent sync operation
**Reason**: The idempotency contract tied to copy semantics (e.g., `--preserve` to skip overwriting local changes) is not meaningful under symlinks because there is no separate project-side file to preserve.
**Migration**: Idempotency is preserved by the new `symlink-based-sync` capability but scoped to symlink state, not file content. The `--preserve` flag is removed.

### Requirement: Safe local experimentation
**Reason**: "Safe experimentation" under the copy model meant mutating a project-local copy that could silently diverge. Under the new model, experiments are uncommitted changes in the warehouse working tree and benefit from the warehouse repo's native git tooling (`git stash`, `git checkout --`, branches).
**Migration**: Users who want to experiment without affecting their warehouse working tree should use `git stash` or a throwaway branch inside the warehouse clone.

### Requirement: Directory structure preservation
**Reason**: Replaced by an equivalent requirement in `symlink-based-sync` that preserves structure via real directories containing per-file symlinks.
**Migration**: No user-visible change; directory layout under `.agentic-beacon/artifacts/` is unchanged.

### Requirement: Glob expansion during sync
**Reason**: Replaced by an equivalent requirement in `symlink-based-sync` covering glob expansion for symlink creation.
**Migration**: No user-visible change in glob semantics.
