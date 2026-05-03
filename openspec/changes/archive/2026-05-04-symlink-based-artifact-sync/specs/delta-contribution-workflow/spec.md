# delta-contribution-workflow (delta)

## REMOVED Requirements

### Requirement: Compare all artifacts in beacon.yaml
**Reason**: Under the symlink model, project files and warehouse files share the same inode — there is no drift to compare. The project-vs-warehouse delta has no meaningful semantics in the new architecture.
**Migration**: Users who want to see pending changes should use `abc warehouse status`, which shows uncommitted and unpushed changes in the warehouse clone scoped to the current project's `beacon.yaml`.

### Requirement: Compare specific file with detailed diff
**Reason**: Same as above — there is no project-vs-warehouse difference to diff.
**Migration**: `abc warehouse status <path>` provides a unified diff of uncommitted warehouse changes for a specific file.

### Requirement: Hash-based comparison for summary
**Reason**: Hash comparison was an implementation detail of the removed `abc delta` command.
**Migration**: N/A — the command is removed.

### Requirement: Git diff for detailed comparison
**Reason**: Detailed diff capability moves to `abc warehouse status`, which uses `git diff` directly inside the warehouse clone.
**Migration**: Use `abc warehouse status <path>` for unified diff output.

### Requirement: Contribution workflow support
**Reason**: The "review local changes before contributing" workflow is replaced by the warehouse-native equivalent (`git diff` / `abc warehouse status`) followed by `abc warehouse contribute`.
**Migration**: Use `abc warehouse status` to review, then `abc warehouse contribute -m "message"` to commit.

### Requirement: Beacon.yaml-aware comparison
**Reason**: Preserved as a requirement of `abc warehouse status`, which also scopes its report to `beacon.yaml`-tracked artifacts.
**Migration**: No user-visible change in scoping behavior.

### Requirement: Clear status indicators
**Reason**: The `[Modified] / [Added] / [Missing]` indicator vocabulary was specific to the copy model (where "Added" meant present-locally-not-in-warehouse and "Missing" meant not-synced). These states do not exist under symlinks.
**Migration**: `abc warehouse status` uses git's native vocabulary (`modified`, `staged`, `untracked`, `ahead/behind`) which is more accurate under the new model.
