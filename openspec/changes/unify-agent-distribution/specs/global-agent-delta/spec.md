## REMOVED Requirements

### Requirement: Delta compares warehouse agents against global install directories
**Reason:** Agents are no longer installed globally. There is no global state to compare against.

**Migration:** Agent comparison falls back to the snapshot-based comparison used by other project artifacts. Each project's `.agentic-beacon/artifacts/agents/<name>.md` is the local snapshot; `abc delta` compares warehouse agent files against those snapshots, reporting `IN SYNC`, `MODIFIED`, or `MISSING` per the existing `snapshot-based-sync` model.

### Requirement: Delta reports per-tool agent status
**Reason:** Without global per-tool installation, there is no per-tool divergence to report. Project-local symlinks always point at the same artifact snapshot, so per-tool status is always identical.

**Migration:** No replacement requirement is needed. `abc delta` reports a single status per agent based on the project artifact snapshot.

### Requirement: Delta agent comparison uses DeltaComparator with global live paths
**Reason:** The `_agent_live_path()` helper resolved global home-directory paths (`~/.config/opencode/agents/`, `~/.claude/agents/`). With agents now project-scoped, the live path is the project artifact snapshot under `.agentic-beacon/artifacts/agents/`, which is the default routing for any path prefix in `DeltaComparator`.

**Migration:** Delete `_agent_live_path()` and the `agents/` prefix routing. No special-case live-path resolution is needed; agents follow the same path resolution as skills and contexts.
