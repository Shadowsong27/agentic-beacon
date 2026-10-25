## Context

The predecessor change `move-agent-requires-to-warehouse-manifest` established `<warehouse>/agents/agents.yaml` as the single source of truth for agent → skill dependencies at the warehouse level. That change is a pure metadata move — it fixes a frontmatter-leak bug and gives Beacon a parseable dependency declaration, but it deliberately does not change any runtime behaviour.

This change closes the remaining gap in agent lifecycle: **projects have no way to declare which agents they use, so Beacon has no way to validate that a project has the skills its agents need.** The design concern manifests in three spots:

- `libs/beacon/src/beacon/domains/adoption/apply.py:39` — explicit `continue  # agents are managed globally, not via beacon.yaml` skip in the adopt apply path.
- `libs/beacon/src/beacon/domains/artifact/agent.py::sync_agents_from_warehouse` — batch-installs every warehouse agent into every detected global tool dir, regardless of any project signal.
- `openspec/specs/artifact-adoption/spec.md:61` — "Agents are global machine-level artifacts. The adopt TUI MAY show agents as global-install candidates... Selecting an agent triggers a global machine-level installation and does NOT update project `beacon.yaml`. Persistent selected-global-agent state and `abc sync` installing selected agents is deferred to PER-109."

This change is PER-109, restructured. It adds project-level agent declaration, connects the adopt flow to the new declaration, and teaches `abc sync` to validate transitive skill dependencies through the manifest that the predecessor change introduced.

## Goals / Non-Goals

**Goals:**
- Add `artifacts.agents: [<agent-path>, ...]` to `beacon.yaml`, used purely as a dependency-declaration pointer.
- Rewire `abc adopt` to treat agents as a project-scoped selectable category, consistent with contexts and skills.
- Implement auto-tick of required skills in the adopt TUI with a visual provenance marker.
- Implement hard-lock: user cannot untick a skill in the adopt TUI while a requiring agent is ticked.
- Implement interactive Y/N repair prompt at `abc sync` when a declared agent's required skill is missing; hard error in non-interactive or on N.
- Preserve global install semantics: `sync_agents_from_warehouse` continues to batch-install every warehouse agent; `abc install agents/<name>.md` continues to work unchanged as an escape hatch.
- Leave global agent uninstall behaviour untouched — dropping an agent from `beacon.yaml` does not remove the global symlink.

**Non-Goals:**
- Filtering global agent installation by `beacon.yaml.artifacts.agents`. Agents stay batch-installed; the field is a dependency pointer, not an install filter.
- Cross-project uninstall logic. When Project A drops `spec-planner` from its declaration, Project B's machine state is untouched.
- Per-project agent instances in `.opencode/agents/` or `.claude/agents/`. Agents remain global artifacts on the filesystem.
- Auto-backfilling `beacon.yaml.artifacts.agents` for existing projects. Users re-run `abc adopt` to declare.
- Runtime validation at the moment of `@agent` invocation inside OpenCode/Claude Code. Beacon has no runtime hook there; validation happens at `abc sync`.
- Consuming any fields in `agents.yaml` other than `skills:` (e.g. forward-compatibility keys like `default`). Those remain preserved-but-unread.

## Decisions

### Decision 1 — `artifacts.agents` is a dependency pointer, not an install filter

**Chosen:** `beacon.yaml.artifacts.agents` declares the agents this project depends on for correctness (specifically, their required skills must be available here). It does NOT control which agents are installed globally. `sync_agents_from_warehouse` continues its current behaviour: batch-installing every warehouse agent into every detected global tool directory.

**Alternatives considered:**

- **`artifacts.agents` as an install filter.** Would mean `abc sync` in Project A installs only Project A's declared agents globally. Creates multi-project problems: Project B running `abc sync` would face a choice between uninstalling agents it hasn't declared (invasive; changes other projects' machine state) or leaving stale agents (then what does "declared" mean?). Every coherent answer produced either a no-op or a cross-project semantic.
- **`artifacts.agents` as a dependency pointer, global install unchanged** (chosen). Clean separation: global install axis is additive and warehouse-wide; project axis is about correctness of declared dependencies. No cross-project state coupling.

**Rationale:** the user clarified this directly during planning — the field's role is to tell Beacon "this project uses these agents, so their required skills must be present here." That's dependency declaration, not install filter. Keeping the install axis unchanged means no migration for existing users' global agent state; the only visible change is that `abc adopt` now writes `beacon.yaml` and `abc sync` now validates declared agents.

### Decision 2 — Auto-tick in the adopt TUI, with hard-lock on skill unticking

**Chosen:** when a user ticks an agent in the adopt TUI, Beacon reads `agents.yaml` and immediately ticks that agent's required skills in the same screen. Each auto-ticked skill displays provenance (`required by spec-planner`). When multiple agents share a required skill, provenance shows all requirers. If the user attempts to untick a skill while any requiring agent is ticked, the toggle is blocked (visually: greyed out or refused with a status line). To remove the skill, the user must first untick the agent that requires it.

**Alternatives considered:**

- **Soft warn on untick.** Allow the user to produce a "broken" selection; on confirm, surface a warning that `abc sync` will later fail. Rejected: invites confusion — user confirms, sync fails minutes later, user has to re-enter adopt. Broken-window pattern.
- **Auto-tick with no lock.** Skills tick on agent-select, but the user can freely untick them. Rejected for the same reason.
- **Hard-lock** (chosen). The TUI enforces the invariant that a selection cannot be broken with respect to declared agent dependencies. User action maps 1:1 to valid state transitions.
- **No auto-tick (user declares skills manually).** Rejected: doubles the user's work for no benefit; the skill requirement is already declared machine-readably in `agents.yaml`.

**Rationale:** the adopt TUI's job is to produce a valid `beacon.yaml`. Letting it produce an invalid selection and then failing at `abc sync` is worse UX than enforcing correctness at the point of input. Hard-lock is the existing pattern for required skills (see `artifact-adoption` spec's provenance rules) — this just extends it up one tier.

### Decision 3 — Interactive repair prompt at `abc sync`, hard error non-interactive

**Chosen:** when `abc sync` finds a declared agent whose required skill is not in `beacon.yaml.artifacts.skills` (and cannot be pulled transitively through other means), Beacon prompts:

```
Agent 'spec-planner' (declared in beacon.yaml) requires skill 'opsx-enhance-tasks',
which is not declared in this project.

Add 'skills/opsx-enhance-tasks/' to beacon.yaml and sync it? [y/N]
```

- **y** — append to `beacon.yaml`, pull the skill, continue sync.
- **N** — hard error, exit non-zero, sync fails.
- **Non-interactive (no TTY)** — hard error by default. `--yes` flag auto-accepts.
- **`--strict`** — not needed as a separate flag; the default behaviour is already "fail unless user opts in," so `--strict` would be a no-op.

**Alternatives considered:**

- **Always error, no prompt.** Consistent with how skill → context missing is handled in the existing `artifact-dependency-resolution` spec. Rejected because the user has a natural in-the-loop response ("yes, add it") that pressing Enter twice saves a context switch to `abc adopt`.
- **Always auto-add silently.** Rejected: modifies `beacon.yaml` without user consent; git-diff surprise.
- **Warn only, don't block.** Rejected: sync "succeeds" but the project is broken. Breaks the declarative-state invariant.
- **Interactive Y/N with non-interactive hard error** (chosen). Matches `abc adopt`'s interactive model; CI paths get clean failures; self-healing for the common case.

**Rationale:** the user clarified during planning that interactive repair is the desired UX over silent auto-add or pure error. The default Y/N answer is N to be consistent with Beacon's general "no destructive action without explicit opt-in" policy.

### Decision 4 — No auto-backfill for existing projects

**Chosen:** after Beacon upgrade, projects with previously-globally-installed agents have an empty `artifacts.agents` in `beacon.yaml`. No migration step infers declarations from global install state. Users re-run `abc adopt` to re-declare agents they want tracked per-project.

**Alternatives considered:**

- **Auto-backfill on first `abc sync` after upgrade.** Scan global agent directories, find ones matching warehouse agents, add them all to `beacon.yaml.artifacts.agents`. Rejected: global install state doesn't mean "this project uses this agent" — a user may have `code-reviewer` installed globally for general use but not actively using it in Project X.
- **Warn on first `abc sync` post-upgrade.** Print "no agents declared; re-run `abc adopt` to opt in." Redundant with the general adopt flow; would fire on every project that hasn't yet been updated.
- **No backfill, silent** (chosen). Projects that never used agents see no change. Projects that did use agents re-run `abc adopt` once to re-declare. One-time manual step, zero inference risk.

**Rationale:** inferring intent from machine state is fragile, and the user confirmed that existing-project migration should be zero-friction manual. Re-running `abc adopt` is ~10 seconds per project. The alternative (bad backfill) could take minutes to clean up per project if the inference is wrong.

### Decision 5 — `abc install agents/<name>.md` survives as escape hatch

**Chosen:** keep `abc install agents/<name>.md` as a power-user command that globally installs an agent without updating any `beacon.yaml`. Document it as "bypasses project scoping; use for machine-wide agents like `record-knowledge` that aren't associated with a particular project." The `beacon.yaml`-aware path is `abc adopt`.

**Alternatives considered:**

- **Remove `abc install agents/...`** entirely, route everything through `abc adopt`. Rejected: genuine use cases exist for "install this agent globally, don't tie it to any project" — e.g. utility agents. Removing the escape hatch would force contrived project-level declarations for these.
- **Keep with no changes** (chosen). The command's existing behaviour (global install, no `beacon.yaml` touch) is correct for its use case. The rename/re-scope of `abc adopt` doesn't conflict.

**Rationale:** the two commands now have clearly distinct semantics: `abc adopt` is project-scoped declaration + global install; `abc install agents/...` is pure global install. Documentation makes the distinction; users pick by intent.

### Decision 6 — `apply.py` records agent selection in `beacon.yaml`

**Chosen:** remove the `continue  # agents are managed globally, not via beacon.yaml` line. Extend the agent branch in `apply_adoption` to append `candidate.path` (of the form `agents/<name>.md`) to `beacon_settings.artifacts.agents`. Global install continues to run via the existing `abc install` mechanism called from the adopt apply flow.

**Alternatives considered:**

- **Record agent selection, but keep global install logic in the same place as today.** Rejected: would require duplicating install logic between `apply.py` and `sync_agents_from_warehouse`. Cleaner to keep the responsibilities split — `apply.py` updates `beacon.yaml`, global install is a side effect of the existing adopt-time install helper.
- **New dedicated subcommand `abc adopt-agent` for agent-only adoption.** Rejected: splits the adopt TUI into multiple commands for no user-visible gain.

**Rationale:** consistent treatment of agents, contexts, and skills in the adopt flow is the goal. Removing the single-line skip gets us there without requiring a structural change to `apply_adoption`.

### Decision 7 — Unadoption does NOT uninstall the global agent symlink

**Chosen:** when a user unadopts an agent (removes it from `beacon.yaml.artifacts.agents`), Beacon does NOT remove the symlink in `~/.config/opencode/agents/` or `~/.claude/agents/`. Other projects may rely on that global install; uninstalling it from one project's unadopt would affect all projects.

**Alternatives considered:**

- **Uninstall on unadopt.** Rejected: cross-project side effect.
- **Uninstall with confirmation prompt.** Rejected: same problem, just opt-in. User could easily confirm and break a sibling project unknowingly.
- **Offer a separate `abc uninstall agents/<name>.md` command.** Out of scope for this change but conceptually cleaner. If needed, add later.
- **Leave symlink in place, do nothing on unadopt** (chosen). Simple, safe, reversible.

**Rationale:** the install axis and the declaration axis are independent by design (Decision 1). Unadoption affects only the declaration; install state is managed separately, exactly symmetric with how this change leaves `sync_agents_from_warehouse` unchanged.

## Risks / Trade-offs

**[Risk]** Existing users upgrade Beacon, run `abc sync`, see no change (empty `artifacts.agents`), and don't realise they should re-run `abc adopt`.
**Mitigation:** release notes call out the new field. `abc warehouse status` shows `artifacts.agents: []` clearly. First `abc adopt` after upgrade surfaces agents as new candidates — the natural flow rediscovers them.

**[Risk]** Auto-tick in the TUI could surprise users who don't expect skill selection to propagate from agent selection.
**Mitigation:** visual provenance marker (`required by spec-planner`) makes the relationship transparent. Hard-lock on untick tells the user why they can't remove the skill. No silent state changes.

**[Risk]** `abc sync` interactive prompt could feel invasive in automation pipelines that aren't quite "CI" but also aren't fully TTY-attached.
**Mitigation:** non-interactive detection uses the same `is_interactive()` helper used elsewhere; `--yes` explicitly opts into auto-accept; the default hard error is the safer choice.

**[Risk]** `agents.yaml` schema validation (from the predecessor change) and runtime consumption (this change) are now coupled. A malformed `agents.yaml` produced by a warehouse author breaks every consumer project's `abc sync`.
**Mitigation:** that coupling already exists via `abc warehouse status`'s validation. This change adds `abc sync` failing on the same malformed manifest, not a new failure class. Warehouse authors see validation errors immediately at `abc warehouse status`, before consumers hit them.

**[Risk]** Multi-agent warehouses with many agent → skill dependencies make the adopt TUI's auto-tick provenance display busy.
**Mitigation:** cap provenance display to first 3 requirers with `... +N more`; full list shown on hover / focus. Out of scope for this change's spec, but worth noting for the implementation.

## Migration Plan

**For this repo (agentic-beacon):**

1. Ensure the predecessor change (`move-agent-requires-to-warehouse-manifest`) is merged, released, and consumed; warehouses have `agents.yaml` present.
2. Ship the code changes on a feature branch: `BeaconManifest` schema extension, `apply.py` change, TUI rework, sync validation hook.
3. Update sample warehouse to declare an example agent with a skill requirement so the happy path is exercised.
4. Update migration doc with the "project-scoped agents" section.
5. Merge.

**For users (per project):**

1. Upgrade Beacon to the new version.
2. `beacon.yaml.artifacts.agents: []` is added automatically on first read (empty).
3. Run `abc adopt` — agents now appear as selectable candidates alongside contexts and skills.
4. Tick desired agents; required skills auto-tick with provenance.
5. Confirm — `beacon.yaml` is updated.
6. `abc sync` runs; required skills flow through the existing transitive pull; agent global install continues unchanged.

**Rollback:** revert Beacon release. `beacon.yaml.artifacts.agents` becomes an unknown field to the older version; no data loss — older Beacon ignores the field. Projects function as before the upgrade.

## Open Questions

**Q1:** When multiple agents require the same skill, and the user unticks all of them, should the skill auto-untick too?

**Proposed default:** yes — the skill was only pulled transitively. Unticking every requirer restores the "no one needs this" state; the skill returns to unticked. Exception: if the user explicitly ticked the skill first (before ticking any agent), the skill remains ticked. This requires tracking user-explicit vs transitive provenance per skill in the TUI state.

This mirrors the existing `artifact-adoption` provenance rule (explicit adoptions survive; transitive ones prune when last referrer drops). Resolved by analogy — no separate open question.

**Q2:** Should the sync-time repair prompt offer to run `abc adopt` instead of patching `beacon.yaml` inline?

**Proposed default:** no. Inline Y/N is one keystroke; redirecting to `abc adopt` for a single missing skill is overkill. If multiple gaps exist, the prompts stack (one per agent) — still faster than context-switching to `abc adopt`. If the user prefers the TUI, they can answer N to all prompts and run `abc adopt` manually.

**Q3:** Does the adopt TUI need a visual distinction between agents that are declared in `beacon.yaml.artifacts.agents` (project-scoped) vs. agents globally installed but not declared (pre-upgrade state)?

**Proposed default:** no separate visual category needed. Declared agents appear ticked in the adopt TUI (same as adopted contexts/skills today); undeclared globally-installed agents appear unticked but available. This is consistent with how the TUI handles any artifact.
