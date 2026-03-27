## Why

Developers using Agentic Beacon warehouses increasingly want to distribute pre-built coding agent definitions (e.g., `code-reviewer`, `registra-developer`) alongside knowledge, contexts, and skills. Unlike the three existing artifact types that are project-scoped, agent definitions are developer-machine-global — they need to land in `~/.config/opencode/agents/` and/or `~/.claude/agents/`, not inside the repo. There is currently no supported path for warehouses to distribute and manage these files.

Separately, the current sync/install behaviour silently overwrites local modifications — there is no user-visible signal when local content diverges from the warehouse before an overwrite occurs. This creates risk in both directions: a developer can unknowingly lose uncontributed local edits on sync, or contribute stale content to the warehouse. A consistent conflict-awareness model is needed across all commands.

## What Changes

### Agents artifact type (PER-42)

- **New warehouse directory**: `agents/` becomes a first-class warehouse directory, scaffolded by `abc warehouse init`
- **New global install routing**: `abc install agents/<name>.md` detects globally available agent tools (`~/.config/opencode/` and `~/.claude/`) and installs to the appropriate global agent directories
- **New global detection helper**: `_detect_agents_global()` in `cli.py` checks global home-directory paths (distinct from existing project-level `_detect_agents()`)
- **Extended `abc delta`**: agent files are compared between the warehouse and global agent directories — no artifact snapshot needed
- **Global agent sync state**: new `~/.config/agentic-beacon/sync-state.json` tracks installed warehouse SHA and content hash per agent file, enabling accurate delta reporting

### Conflict-awareness model (new across all commands)

- **Soft block on `abc sync` and `abc install`**: when local content differs from warehouse, warn the user and prompt y/N before overwriting. `--preserve` skips. `--force` overwrites without prompt (for scripting). In non-interactive mode, a content diff is treated as a hard block unless `--preserve` or `--force` is explicitly passed.
- **`--preserve` on `abc install`**: extend the existing `abc sync --preserve` behaviour to `abc install`
- **`abc contribute` no-op detection**: when local artifacts are identical to the warehouse, print "nothing to contribute" and exit cleanly instead of creating an empty PR
- **Bundled skills exempt**: `_install_bundled_skills_globally()` always overwrites — these are package-managed files, not user content
- **`abc reset` command** (**BREAKING**): replaces `abc update`; same force-overwrite semantics, exempt from soft blocks, prints a count of overwritten files. `abc update` becomes a hidden deprecated alias.

## Capabilities

### New Capabilities

- `warehouse-agent-scaffold`: Scaffold `agents/` directory with README template when running `abc warehouse init`; add `agents/README.md` to `TEMPLATE_FILES` so `abc warehouse template-upgrade` tracks it
- `global-agent-install`: Route `abc install agents/<name>.md` to global agent directories for both OpenCode and Claude Code; soft block (warn + y/N) when content differs; install agents during `abc setup` alongside existing artifact types
- `global-agent-delta`: Extend `abc delta` to compare warehouse `agents/` entries against globally installed files in `~/.config/opencode/agents/` and `~/.claude/agents/`; surface `STALE` status when the installed content matches the last-synced snapshot but the warehouse HEAD has since moved on
- `global-agent-sync-state`: Track installed warehouse SHA and content hash per agent file in `~/.config/agentic-beacon/sync-state.json` (versioned schema); relink-prompt TUI when the warehouse path has changed (e.g. after a rename/move)
- `sync-soft-block`: Warn + y/N confirmation on `abc sync` and `abc install` when content differs; `--force` bypasses; non-interactive = hard block without explicit flag; pre-check runs at the CLI layer — `SyncEngine` remains non-interactive
- `install-flags`: Add `--preserve` and `--force` flags to `abc install` for parity with `abc sync`; when the user responds N to the soft-block prompt, `beacon.yaml` is NOT updated
- `contribute-noop`: Verify existing no-op detection extends cleanly to agent contribute paths; `abc contribute --all` on an unchanged workspace exits 0 with "nothing to contribute"
- `reset-command`: **BREAKING** — rename `abc update` to `abc reset`; keep `abc update` as hidden deprecated alias
- `warehouse-list-agents`: Surface `agents/` entries in `abc warehouse list` (warehouse-side view of available agent files) and in `abc list` (globally installed agents view)

### Modified Capabilities

- `abc setup`: Updated to describe the `agents/` artifact type and guide the user to `abc install agents/<name>` (agents are globally installed, not project-synced, so they do not appear in `beacon.yaml`)

## Impact

- `libs/beacon/src/beacon/cli.py` — `_detect_agents_global()`, `_install_agent_global()`, agents branch in `install_artifact()`, soft block pre-check (CLI layer) in `sync` and `install_artifact()`, `--preserve`/`--force` flags on `abc install`, `abc reset` command, `abc update` deprecated alias, contribute no-op verification, `abc warehouse list` and `abc list` updated to surface `agents`, `abc setup` updated to describe agent install flow
- `libs/beacon/src/beacon/core/delta.py` — `_agent_live_path()`, `agents_paths` attribute on `DeltaComparator`, `_compare_agent_file()`, `DeltaStatus.STALE` added to enum, STALE enrichment in `_show_delta_summary()` (reads global sync-state to detect stale agent installs)
- `libs/beacon/src/beacon/core/sync.py` — new `classify_conflicts(artifact_paths) -> list[str]` public method on `SyncEngine` (used by CLI soft-block pre-check); `SyncEngine` itself remains non-interactive
- `libs/beacon/src/beacon/initializer.py` — `_create_agents()`, `_create_structure()`, `TEMPLATE_FILES` updated to include `agents/README.md`
- `libs/beacon/src/beacon/warehouse/validator.py` — `REQUIRED_DIRECTORIES` updated to include `agents`
- `libs/beacon/src/beacon/data/templates/agents/README.md` — new template
- `~/.config/agentic-beacon/sync-state.json` — new global sync state file (user home, not repo); versioned schema with relink-prompt migration for warehouse path changes
- `examples/sample-warehouse/agents/README.md` — update sample warehouse
- Tests and docs

## Risks

- **Soft block on `abc sync` is a behaviour change** for any future automation or CI usage (currently all `abc sync` runs are local/interactive). Scripts that rely on silent overwrite will need `--force` or `--preserve`. Document in release notes as a behaviour change (low urgency for current users; good hygiene for future pipeline adoption).
- **`abc reset` rename** — users with `abc update` in scripts will see a deprecation warning but it still works. The hidden alias ensures no breakage.
- **`~/.config/agentic-beacon/` is a new user home directory** — created lazily on first agent install; document in release notes.
- **Global sync-state keyed by warehouse path** — if the warehouse is moved or renamed, the key becomes stale. Mitigated by a relink-prompt TUI (see Decision 6 in design.md).
- **Sample warehouse drift** — `examples/sample-warehouse/agents/README.md` must stay in sync with the template. A content-parity test in CI will catch drift.

## Manual Intervention Requirements

- **[MANUAL] Merge the pull request**: After implementation is complete and CI passes, merge the PR via GitHub UI.
  - **Rationale**: Project standards require human PR review and merge.
  - **Timing**: After task 10.3 (full test suite passes) and CI is green.

---

## Enhancement Metadata

**Enhanced**: 2026-03-28
**Methodology**: Spec-Driven Development
**Enhancements Applied**:
- ✅ Manual intervention requirements identified
- ✅ Impacted modules and systems documented
- ✅ Task verification steps added
- ✅ TDD Input/Output/Validation criteria added to key tasks
- ✅ Risk mitigation strategies formalized

**Status**: Ready for implementation via `/opsx-apply global-agent-artifact-type`
