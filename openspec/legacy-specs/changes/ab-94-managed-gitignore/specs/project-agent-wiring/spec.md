## REMOVED Requirements

### Requirement: abc setup adds agent directories to .gitignore

**Reason**: Superseded by the `beacon-gitignore-management` capability. Agent directories (`.claude/agents/`, `.opencode/agents/`) are now **unconditional** entries in the Tier A managed block — written by the single managed-block engine from every wiring path regardless of whether any agent is declared — rather than appended by a declared-agents-gated helper. The `update_agent_gitignores` / `ensure_agent_dirs_gitignored` / `prune_agent_dirs_gitignore_entries` helpers and the prune-on-empty behavior are removed. See `beacon-gitignore-management` → "Tier A entry set is unconditional".
