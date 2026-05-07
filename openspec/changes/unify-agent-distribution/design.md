## Context

Beacon currently distributes agents differently from every other artifact. Contexts and skills are declared in `beacon.yaml.artifacts.*`, symlinked under `.agentic-beacon/artifacts/`, and wired into project-local agent dirs (`.opencode/skills/`, `.claude/skills/`, `opencode.json`, `CLAUDE.md`) by `abc sync`. Agents bypass all of that: `beacon.yaml.artifacts.agents` is a usage declaration consumed only by `core/dependencies/resolver.py` to validate the agent→skill graph; the actual install is `abc agents sync`, a separate machine-global sweep that copies every `agents/*.md` from the warehouse into `~/.claude/agents/` and `~/.config/opencode/agents/`, ignoring `beacon.yaml`.

This split was originally chosen because Claude Code's `~/.claude/agents/` was the only documented agent location and we wanted "agent everywhere on the machine." Both tools have since shipped project-local support (`.claude/agents/` for Claude Code, `.opencode/agents/` for OpenCode; OpenCode also accepts `.opencode/agent/` as a legacy alias). With both tools confirmed to honor project-local dirs (verified empirically by spinning up scratch projects with marker agents and observing tool resolution), the rationale for keeping agents global has dissolved.

The current state generates two visible smells:

1. `abc agents` is a Click group with a single subcommand, parallel to no other artifact. Cosmetic, but signals the underlying inconsistency.
2. `abc adopt`'s agent tab is dishonest. Accept/reject only mutates `beacon.yaml`; the symlink in `~/.claude/agents/` was already there or wasn't, regardless of choice.

PER-109 proposed solving the "agents are too broadly installed" pain by adding an interactive picker on top of the global sweep. PER-113 proposed solving it by making agents project-scoped like everything else. The latter unifies the model; the former bolts a UI onto the special case. This change implements PER-113 and supersedes PER-109.

**Stakeholders:** Beacon CLI users (project authors), warehouse maintainers, downstream tools (Claude Code, OpenCode).

## Goals / Non-Goals

**Goals:**

- Make agents behave like contexts and skills end-to-end: declared in `beacon.yaml`, symlinked under `.agentic-beacon/artifacts/`, wired into project-local tool dirs by `abc sync`, accept/reject in `abc adopt` is truthful.
- Delete the global agent install model: `abc agents sync`, the `agents` Click group, `~/.claude/agents/` and `~/.config/opencode/agents/` writes from any Beacon path.
- Migrate cleanly: existing global symlinks pointing into a Beacon warehouse get cleaned on first post-upgrade `abc sync`, with a one-line user-visible notice.
- Keep `abc warehouse init` non-disruptive at runtime (no automatic agent population), but make the post-init hint surface `abc adopt` so users know how to wire agents.
- Preserve `abc list agents` as a working command during the transition, with semantics flipped to project-declared agents.

**Non-Goals:**

- Outright deletion of `abc list agents`. The user wants a future cleanup ticket; this change keeps the command alive with the new semantics.
- Re-architecting how skills or contexts are wired. The agent wiring is built parallel to the existing skill wiring pattern; no refactoring of the existing functions.
- Cross-machine sharing of agent files via git. `.claude/agents/` and `.opencode/agents/` are gitignored; the manifest of which agents to wire (i.e., `beacon.yaml.artifacts.agents`) is the team-shared SSOT.
- Restoring "agents in any directory" UX. The trade-off is named in the proposal and accepted.

## Decisions

### 1. Project-local symlink model

Wire each declared agent at `.agentic-beacon/artifacts/agents/<name>.md` (already produced by sync) into both `.claude/agents/<name>.md` and `.opencode/agents/<name>.md`, gated by `detect_agents()` (the existing project-level tool detection used by `wire_skill`).

**Why:** Symmetric with how skills are wired. Single artifact path → multiple tool destinations is already the established pattern. Project-local symlinks are per-machine state and must not be committed (see decision 4).

**Alternatives considered:**
- Copy file contents instead of symlinking. Rejected: forks from the contexts/skills model and breaks "edit through any project hits the warehouse" cross-project visibility (called out in `AGENTS.md`).
- Wire to only the detected tool. Rejected: `wire_skill` already writes unconditionally to both because `detect_agents` returns whichever the project has configured, and we want symmetry.

### 2. Adoption accept/reject drives wire/unwire

`abc adopt` accept on an agent: append to `beacon.yaml.artifacts.agents`, sync the symlink under `.agentic-beacon/artifacts/agents/`, and call `wire_agent_*` to write `.claude/agents/<name>.md` and `.opencode/agents/<name>.md`. Reject: remove the entry from `beacon.yaml`, call `unwire_agent` to remove the project-local symlinks, and remove `.agentic-beacon/artifacts/agents/<name>.md`. Defer: no-op.

**Why:** Mirrors contexts/skills. Eliminates the "accepting an agent is a no-op visually" smell named in PER-113.

**Alternatives considered:**
- Defer wiring to next `abc sync`. Rejected: leaves a window where `beacon.yaml` and the filesystem disagree; trips up `abc warehouse status` and other diagnostics.

### 3. Legacy-symlink migration on first `abc sync`

During `abc sync`, after the artifact symlinks are reconciled, scan `~/.claude/agents/` and `~/.config/opencode/agents/`. For each entry that is a symlink whose target resolves under the connected warehouse path (read from `WorkspaceConfig().warehouse.local_path`), `unlink` it. Print `Cleaned up N legacy global agent symlinks (PER-113 migration).` only if N > 0. Idempotent: subsequent runs find nothing and print nothing.

**Why:** Users with existing setups should not be left with orphaned symlinks pointing into directories that may be renamed or removed. The notice trades silence for trust — users see exactly what was mutated in their home directory.

**Alternatives considered:**
- Ship a separate `abc migrate-agents` command. Rejected by user during grill: too much ceremony for a one-time fix.
- Leave orphans alone. Rejected: harmless until they are not (e.g. warehouse path moves and the broken symlinks confuse the tool).
- Verbose per-path output. Rejected: noisy on first run for users with many agents synced globally.

### 4. `.gitignore` updated by `abc setup`

`abc setup` adds `.claude/agents/` and `.opencode/agents/` to the project's `.gitignore` (or appends if the file exists). `update_agent_gitignores` in `domains/artifact/agent.py` is repurposed for this.

**Why:** The symlinks point into `.agentic-beacon/artifacts/agents/`, which itself points into a per-machine warehouse path. Committing the symlinks creates broken refs on teammates' machines. The team-shared SSOT is `beacon.yaml.artifacts.agents`; sync recreates the symlinks anywhere.

**Alternatives considered:**
- Commit the `.md` files (copy semantics). Rejected: see decision 1.
- Don't touch user `.gitignore`. Rejected: invites broken-symlink commits from new users who don't understand the implication.

### 5. `abc warehouse init` keeps `agents: []`

`abc warehouse init` generates a `beacon.yaml` with `agents: []` (the existing behaviour). The post-init hint adds: `Run 'abc adopt' to wire agents.`

**Why (user choice):** Preserves opt-in semantics. The user explicitly preferred `[]` over auto-populating with the full warehouse set, accepting the cost of fresh projects starting with zero wired agents in exchange for explicit consent. The hint covers the discoverability gap.

**Alternatives considered:**
- Pre-populate with all `*.md` under `warehouse/agents/`. Rejected by user: too much implicit behaviour. The "where did `code-reviewer` go?" UX question is answered by the post-init hint and the adopt flow.
- Curated minimal set. Rejected: introduces a hardcoded list that goes stale.

### 6. `abc list agents` flips, deletion deferred

`abc list agents` is rewritten to read `.agentic-beacon/artifacts/agents/` (mirroring `abc list skills`/`abc list contexts`). The global-dir reading code path (`list_global_agents`) is deleted along with the rest of the global model.

**Why:** Once the global cleanup runs, `~/.claude/agents/` will be empty (or close to it) and `list agents` would silently say "No agents found" while the project has wired agents — that is a worse lie than the current one. Flipping the semantics is mechanical (12 lines of code change). Deletion is the right end state but is a separate scope per user direction.

**Alternatives considered:**
- Two-section output (project-declared + global leftovers). Rejected: adds code that would be deleted in the follow-up ticket.
- Delete the command in this change. Rejected by user: separate ticket.

### 7. Single OpenSpec change

All of the above ships as one change. No staged rollout.

**Why:** The pieces are coupled. Shipping the wiring without deleting the global sweep would mean both run; shipping the deletion without the wiring would orphan declared agents. The migration cleanup and the wiring are two halves of the same upgrade.

**Alternatives considered:**
- Split into "add wiring" + "remove global" + "migration." Rejected: coordination overhead for no reduction in risk.

## Risks / Trade-offs

**[Risk] Users on shared dev VMs lose the "agent in any directory" UX.**
Today, `cd /tmp && claude --agent code-reviewer` works because `~/.claude/agents/` is read globally. After this change, agents only resolve inside Beacon-wired projects.
→ **Mitigation:** Named in the proposal as a known semantic loss. Users who genuinely want machine-wide availability can manually drop a copy into `~/.claude/agents/`; that path is no longer Beacon-managed but remains tool-honored.

**[Risk] Users with many existing global symlinks see the cleanup notice and worry.**
The first `abc sync` after upgrade may delete dozens of symlinks.
→ **Mitigation:** The notice prints the count and references "PER-113 migration." Linking the migration document in `site-docs/` provides full context.

**[Risk] `abc adopt` reject now mutates the filesystem (removes symlinks) where it previously did not.**
Existing users of adopt expect reject to be a `beacon.yaml`-only edit.
→ **Mitigation:** The new behaviour is consistent with how reject already works for contexts and skills — adopt's domain layer (`domains/adoption/apply.py`) already calls unwire functions for those types. Users will not be surprised by symmetry; the surprise was the asymmetry.

**[Risk] Migration cleanup mistakes a non-warehouse symlink for a Beacon symlink.**
The cleanup pattern is "symlink whose target resolves under the connected warehouse path." A user who manually symlinked an unrelated file into `~/.claude/agents/` from inside the warehouse directory tree would have it removed.
→ **Mitigation:** The check is strict (target must be under the warehouse's `agents/` subdir, not just under the warehouse). The migration runs once; subsequent runs find nothing.

**[Risk] `detect_agents` returns an empty list (project has neither `.claude/` nor `.opencode/`).**
With the new model, `abc sync` would silently wire nothing.
→ **Mitigation:** This is correct behaviour for a project that has not run `abc setup`. The existing skill wiring already short-circuits the same way.

**[Risk] `examples/sample-warehouse/` drift.**
The init/template changes will require regenerating the example.
→ **Mitigation:** Listed as a task; called out in `AGENTS.md` as a critical safeguard.

## Migration Plan

1. Land the change with the legacy-cleanup hook in `abc sync`.
2. Users upgrade `beacon` (via `uv sync` or `pip install -U beacon`).
3. First `abc sync` after upgrade:
   - Wires any agents already declared in `beacon.yaml.artifacts.agents` into project-local dirs.
   - Cleans legacy global symlinks; prints the one-line notice.
4. Users who had no agents declared previously (i.e. relied on global install) run `abc adopt` to wire the agents they want.
5. Document the migration in `site-docs/` with a section that says: "Run `abc sync` after upgrading; if you previously relied on global agents, also run `abc adopt`."

**Rollback:** Revert the version bump. The cleanup is destructive (legacy symlinks are gone) but the warehouse files are untouched, so re-running `abc agents sync` (after rollback) recreates the global state.

## Open Questions

None. All decision branches were closed during the explore/grill phase.
