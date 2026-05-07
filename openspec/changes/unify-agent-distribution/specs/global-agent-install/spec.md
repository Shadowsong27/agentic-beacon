## REMOVED Requirements

### Requirement: Install routes agents to global directories
**Reason:** Agents are no longer installed into global tool directories. Installation is now project-scoped via `beacon.yaml.artifacts.agents` and the `project-agent-wiring` capability.

**Migration:** The `abc install agents/<name>.md` invocation path for agents is removed alongside `abc agents sync`. Users install agents per project by adding entries to `beacon.yaml.artifacts.agents` (typically via `abc adopt`) and running `abc sync`. The new install destinations are `.claude/agents/<name>.md` and `.opencode/agents/<name>.md` inside each project, gated by `detect_agents()`. Existing global symlinks are removed automatically by the legacy-cleanup pass on first post-upgrade `abc sync` (see `legacy-agent-cleanup`).

### Requirement: Install creates parent agent directories
**Reason:** Removed alongside the global install routing. Project-local wiring creates `.claude/agents/` and `.opencode/agents/` parent dirs as needed (see `project-agent-wiring`).

**Migration:** Behaviour is preserved at the new project-local destinations.

### Requirement: Install applies soft block when content differs
**Reason:** Removed alongside the global install routing. The soft-block model continues to apply at the project-local destinations as a property of `abc sync`'s general symlink reconciliation; no agent-specific path is needed.

**Migration:** No user action required. The soft-block model defined in `sync-soft-block` continues to govern how `abc sync` handles conflicts at the project-local symlink destinations.
