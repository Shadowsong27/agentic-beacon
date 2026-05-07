## Why

Agents are the only Beacon artifact type whose installation ignores `beacon.yaml`. Today `abc agents sync` does a separate, machine-global sweep into `~/.claude/agents/` and `~/.config/opencode/agents/`, while `beacon.yaml.artifacts.agents` is a usage-tracking declaration that has no install effect. The split creates two visible smells: `abc adopt`'s agent tab is dishonest (accepting only edits the manifest, the file was already global), and `abc sync` does something orthogonal to the manifest only for agents. Both Claude Code and OpenCode have been verified empirically to honor project-local agent directories (`.claude/agents/`, `.opencode/agents/`), unblocking unification.

## What Changes

- **BREAKING:** `beacon.yaml.artifacts.agents` becomes the install manifest, not a usage declaration. Adding/removing entries (via `abc adopt` or hand edits) wires/unwires symlinks under `.claude/agents/<name>.md` and `.opencode/agents/<name>.md`.
- **BREAKING:** Delete `abc agents sync` and the entire `abc agents` Click group.
- **BREAKING:** Stop installing agents into `~/.claude/agents/` and `~/.config/opencode/agents/`. Agents become project-scoped, like contexts and skills.
- `abc sync` expands `beacon.yaml.artifacts.agents` and wires symlinks into project-local agent directories, gated by `detect_agents()` (the existing project-level tool detection used by skill wiring).
- `abc sync` performs a one-time migration: scans `~/.claude/agents/` and `~/.config/opencode/agents/` for symlinks pointing into the connected warehouse, removes them, and prints `Cleaned up N legacy global agent symlinks (PER-113 migration).`
- `abc adopt`: accepting an agent now actually wires it; rejecting unwires; deferring is a no-op (mirrors contexts/skills).
- `abc setup` adds `.claude/agents/` and `.opencode/agents/` to project `.gitignore` (per-machine symlinks must not be committed).
- `abc warehouse init` continues to ship `agents: []` in the default `beacon.yaml`. The init hint instructs the user to run `abc adopt` to wire agents.
- `abc list agents` flips to read project-declared agents from `.agentic-beacon/artifacts/agents/`. Outright deletion is deferred to a follow-up ticket.
- Drop the PER-112 fresh-machine fallback; subsumed by deleting `sync_agents_from_warehouse`.
- Closes PER-113 in Linear; supersedes PER-109 (selectivity now comes from `beacon.yaml` gating, not a separate picker).

## Capabilities

### New Capabilities

- `project-agent-wiring`: Project-local symlink wiring of declared agents from `.agentic-beacon/artifacts/agents/<name>.md` into both `.claude/agents/<name>.md` and `.opencode/agents/<name>.md` during `abc sync`, with adoption-driven write/remove.
- `legacy-agent-cleanup`: One-time, idempotent removal of orphaned symlinks under `~/.claude/agents/` and `~/.config/opencode/agents/` that point into the connected warehouse, performed during `abc sync` post-upgrade.

### Modified Capabilities

- `project-agent-declaration`: Reverses the "declaration is not an install filter" rule. The manifest now drives both wiring and unwiring. Removing an entry removes the project-local symlinks; nothing in the user's home directory is touched.
- `global-agent-install`: Removed. The capability's requirements are deleted entirely as agents are no longer installed globally.
- `global-agent-delta`: Removed. `abc delta` no longer compares against global agent directories; agents now follow the snapshot-based comparison used by other project artifacts.

## Impact

**Code (delete):**
- `libs/beacon/src/beacon/cli/agent.py` — entire `agents` Click group; `list_cmd` is preserved but rewritten to read `.agentic-beacon/artifacts/agents/`.
- `libs/beacon/src/beacon/domains/artifact/agent.py` — `sync_agents_from_warehouse`, `install_agent_global`, `uninstall_agent_global`, `global_agent_dirs`, `detect_agents_global`, `_agent_link_conflicts`, `list_global_agents`.

**Code (keep):**
- `libs/beacon/src/beacon/domains/artifact/agent.py` — `read_agent_definition`, `detect_agents`, `update_agent_gitignores`.

**Code (add/modify):**
- `libs/beacon/src/beacon/domains/setup/wiring.py` — new `wire_agents_*` and `unwire_agent` functions, parallel to skills/contexts.
- `libs/beacon/src/beacon/domains/distribution/orchestrator.py` — agent expansion + wiring step; legacy-symlink cleanup hook.
- `libs/beacon/src/beacon/domains/setup/initializer.py` — extend `abc setup` to add `.claude/agents/` and `.opencode/agents/` to `.gitignore`.
- `libs/beacon/src/beacon/domains/adoption/apply.py` — adoption accept/reject now triggers wire/unwire.
- `libs/beacon/src/beacon/cli/main.py` — unregister `agents` group.

**Tests:**
- `libs/beacon/tests/integration/test_auto_pull_deps_e2e.py:303` — invert the assertion that `abc sync` does NOT call `sync_agents_from_warehouse`.
- `libs/beacon/tests/integration/test_agents_sync_command.py` — retire.
- New `wire_agents` unit and integration tests parallel to existing skills wiring tests.
- New legacy-cleanup migration test.

**Docs / examples:**
- `libs/beacon/src/beacon/data/templates/agents/README.md`, `libs/beacon/src/beacon/data/templates/README.md` — drop "globally installed" language.
- `libs/beacon/src/beacon/domains/setup/wiring.py` `create_beacon_template` comment — update.
- `examples/sample-warehouse/` — regenerate after init/template changes.
- `site-docs/` — update agent distribution docs.

**External / migration:**
- Existing `~/.claude/agents/` and `~/.config/opencode/agents/` symlinks pointing into a Beacon warehouse will be removed on the user's first `abc sync` after upgrade. A one-line notice is printed.
- Lost capability: agents resolved in arbitrary directories (e.g. `cd /tmp && claude --agent code-reviewer`). After the change, agents resolve only inside Beacon-wired projects.
