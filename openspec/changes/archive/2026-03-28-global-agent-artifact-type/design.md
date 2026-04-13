## Context

Agentic Beacon currently supports three project-scoped artifact types: `knowledge`, `contexts`, and `skills`. Agent definitions (`.md` files in `~/.config/opencode/agents/` or `~/.claude/agents/`) are a natural next step: developer-machine-global tools that travel with the person, not the repo.

In addition, the current sync/install behaviour silently overwrites local modifications. This creates two risks: developers lose uncontributed local edits on sync, and they may contribute stale content to the warehouse. This change introduces a consistent conflict-awareness model across all write commands.

Current relevant code:
- `_detect_agents(project_root)` — project-level detection (checks `opencode.json`, `.claude/`, `CLAUDE.md`)
- `_skill_live_path()` in `delta.py` — precedent for routing comparison to a live dir
- `_install_skill_opencode/claudecode()` — precedent for type-based install branching
- `_install_bundled_skills_globally()` — global install path (always overwrites; stays exempt)
- `_write_sync_state()` / `_check_sync_state()` — existing per-project sync state baseline
- `_check_warehouse_git_clean()` — existing hard block on contribute (warehouse not clean or behind remote)
- `SyncEngine.copy_file()` — core file copy with `preserve` flag; soft-block pre-check runs at the CLI layer before this is called (see Decision 10)
- `abc update` — force-overwrite command being renamed to `abc reset`

## Goals / Non-Goals

**Goals:**
- Introduce `agents/` as a warehouse directory with global install, delta, sync-state tracking, and `STALE` detection in `abc delta`
- Surface `agents` in `abc warehouse list` (warehouse-side view) and `abc list` (globally installed view)
- Guide users to `abc install agents/<name>` during `abc setup` (agents are global, not project-synced)
- Add `agents` to `WarehouseValidator.REQUIRED_DIRECTORIES` so `abc warehouse connect` validates the directory
- Add a soft-block (warn + y/N) on `abc sync` and `abc install` when content differs; pre-check runs at the CLI layer — `SyncEngine` remains non-interactive
- Add `--force` to `abc sync` and `--preserve`/`--force` to `abc install`; when user responds N to the soft-block prompt, `beacon.yaml` is NOT updated
- Verify existing no-op contribute detection extends cleanly to agent contribute paths
- Rename `abc update` → `abc reset` (deprecate old name)

**Non-Goals:**
- Adding `agents` to `ArtifactsConfig`, `beacon.yaml`, or `abc sync` (agents are globally installed, not project-scoped snapshots)
- Installing agents via `abc sync`
- Snapshotting agents into `.agentic-beacon/artifacts/`
- Per-file y/N prompting (one batch prompt covers all conflicts in a command run)
- Merge/diff tooling for conflicting files
- Linking global sync-state to a remote git URL; path-based keying is sufficient with the relink-prompt TUI for local warehouse moves

## Decisions

### Decision 1: Dedicated global detection function, not overloading `_detect_agents`

**Choice:** New `_detect_agents_global() -> list[str]` function in `cli.py`.

**Rationale:** `_detect_agents(project_root)` checks project-relative paths — those signals are irrelevant for global install. A dedicated function with home-dir checks makes the distinction explicit and testable in isolation.

**Alternatives considered:**
- `global=True` flag on `_detect_agents` — rejected, muddies the function contract.

---

### Decision 2: Reuse `_skill_live_path` pattern for `_agent_live_path` in delta.py

**Choice:** `_agent_live_path(agent, relative_path) -> Path` strips `agents/` prefix and resolves against the tool's global agents directory.

**Agent live directory mapping:**
```
opencode   → ~/.config/opencode/agents/
claudecode → ~/.claude/agents/
```

---

### Decision 3: Per-tool delta reporting for agents, including STALE detection

**Choice:** Report `IN SYNC` / `MODIFIED` / `MISSING` / `STALE` per tool separately. `STALE` is a first-class status exposed in `abc delta`.

**Rationale:** A developer may have only one tool installed. Per-tool rows make it clear exactly which global directory needs updating. `STALE` means: the installed content matches the last-recorded snapshot hash in `sync-state.json`, but the warehouse HEAD has since moved on — the file may be functionally identical but the developer should re-install to stay current.

**Detection logic for STALE:**
1. Hash the installed agent file — it matches `content_hash` in `sync-state.json` (so it is not `MODIFIED`)
2. Compare `warehouse_head` in `sync-state.json` against the current warehouse HEAD SHA — they differ
3. → Status is `STALE`

STALE enrichment runs at the CLI layer in `_show_delta_summary()`, which reads `~/.config/agentic-beacon/sync-state.json` after `DeltaComparator` produces its results. `DeltaComparator` itself remains a pure hash-comparison engine; it does not read sync-state.

**`DeltaStatus.STALE` must be added to the enum** in `delta.py` and to the priority map in `_compare_skill_file()` (priority lower than `MODIFIED`, higher than `MISSING` is not applicable to agents — STALE is enriched post-comparison, not rolled up from agent_statuses).

---

### Decision 4: Soft block on sync/install — Option B (content comparison only)

**Choice:** Any content difference between warehouse file and target file triggers a soft block (warn + y/N). No per-file timestamp or sync-state direction analysis needed.

**Rationale:** Simple and consistent. The sync-state baseline already handles the "stale snapshot" signal on `abc contribute`. For sync/install, the developer needs to opt in to overwriting any local divergence. Direction (who changed it) adds complexity without enough UX value for v1.

**Full conflict matrix:**

| Situation | Interactive | Non-interactive |
|---|---|---|
| Content identical | Skip (no-op) | Skip (no-op) |
| Content differs, default | Warn + y/N | Hard block (exit 1) |
| Content differs, `--preserve` | Skip silently | Skip silently |
| Content differs, `--force` | Overwrite silently | Overwrite silently |
| Fresh file (no local) | Copy | Copy |

**`abc install` + beacon.yaml interaction under soft block:**
When the user responds **N** (do not overwrite) to the soft-block prompt during `abc install`, no files are copied and `beacon.yaml` is NOT updated. The `_update_beacon_yaml()` call must be gated on at least one file having been successfully copied — it must not be called unconditionally after the copy loop.

**Alternatives considered:**
- Per-file direction detection (Option A — extend sync state with per-file hashes) — deferred; adds complexity, can be layered on later once content-comparison UX is validated.
- Warn-and-skip always (no y/N) — rejected; too passive, developer can't easily proceed without re-running with `--force`.

---

### Decision 5: Bundled skills always overwrite, no soft block

**Choice:** `_install_bundled_skills_globally()` retains its current silent-overwrite behaviour and is explicitly exempt from soft blocks.

**Rationale:** Bundled skills are ABC-package-managed files — they are not user content. A developer customising them is edge-case; silently overwriting keeps the package-managed experience clean. The developer can inspect with `abc delta` if they want to see what changed.

---

### Decision 6: Global agent sync state at `~/.config/agentic-beacon/`

**Choice:** `~/.config/agentic-beacon/sync-state.json`, keyed by warehouse path, with a top-level `version` field for forward compatibility.

```json
{
  "version": 1,
  "warehouses": {
    "/path/to/warehouse": {
      "agents/code-reviewer.md": {
        "content_hash": "sha256:...",
        "warehouse_head": "abc123",
        "installed_at": "2026-03-28T10:00:00Z"
      }
    }
  }
}
```

**Rationale:** XDG-compliant (`~/.config/`), mirrors the `~/.config/opencode/` convention already used in the codebase. Keyed by warehouse path supports multi-warehouse setups. Written on every successful install (no-op skips are NOT written, so state reflects actual last-written content). The `version` field allows future readers to detect and migrate old schemas gracefully — a reader encountering an unknown version should warn and skip, not crash.

**Relink-prompt TUI for warehouse path changes:**
When any global agent command reads `sync-state.json` and finds no entry for the current warehouse path, but does find one or more entries under other paths whose warehouse directory name matches the current warehouse name, prompt the user:

> "No tracking state found for `/new/path/to/warehouse`. Found existing state for `/old/path/to/warehouse`. Is this the same warehouse? [y/N] (Relinks tracking state)"

If the user confirms, rename the key in `sync-state.json` from the old path to the new path. This handles the common case of a warehouse being moved or renamed locally without any network calls or remote git dependency.

**Alternatives considered:**
- `~/.agentic-beacon/sync-state.json` — rejected; `~/.agentic-beacon/` is not established as a global dir in the codebase.
- Per-agent-dir state file — rejected; centralised file is easier to inspect and manage.
- Keying by git remote URL — rejected; `abc` intentionally supports pure-local warehouses with no remote.

---

### Decision 7: Batch soft block prompt (one y/N for all conflicts)

**Choice:** List all conflicting files upfront, then ask once: "Overwrite N file(s) with local changes? [y/N]". Applies to both `abc sync` and `abc install`.

**Rationale:** Per-file prompting on `abc sync` with 20 artifacts would be an unusable UX. One batch prompt is faster, still informative, and consistent with how `--preserve` already works (all-or-nothing per run).

---

### Decision 8: Non-interactive mode treats soft block as hard block

**Choice:** When stdin is not a TTY and `--preserve`/`--force` are not explicitly set, a content conflict causes the command to exit 1 with a clear error listing conflicting files.

**Rationale:** Silent overwrites in CI would be a regression over the current silent behaviour. Explicit flags (`--preserve` or `--force`) make CI usage intentional and auditable. This matches the `abc contribute` pattern where git checks become hard blocks.

---

### Decision 9: `abc update` → `abc reset` with hidden deprecated alias

**Choice:** New `abc reset` command with same force-overwrite behaviour. `abc update` kept as hidden command that prints a deprecation warning and delegates to `abc reset`.

**Rationale:** "reset" better communicates destructive intent ("I want warehouse to win, overwrite everything") vs "update" which implies a safe incremental operation. The hidden alias preserves backward compatibility for any existing scripts. No `--version` bump strategy change needed — the alias is permanent until a future major release removes it.

**Alternatives considered:**
- Remove `abc update` entirely — rejected; could break existing user scripts.
- Keep both as full commands — rejected; dual naming creates confusion.

---

### Decision 10: Soft-block pre-check runs at the CLI layer — `SyncEngine` remains non-interactive

**Choice:** The soft-block content-comparison pre-check runs at the CLI layer (in `sync` and `install_artifact` command handlers), before invoking `sync_engine.sync_all()` or `sync_engine.copy_file()`. `SyncEngine` is not modified to handle interactive state.

**Rationale:** `SyncEngine` is a pure `@dataclass` file-copy engine with no console, click, or sys.stdin dependencies. Its contract is "copy files, return results." The existing `preserve` flag follows the same pattern — the CLI decides the policy before calling the engine. Adding interactive concerns to `SyncEngine` would violate its contract and make it untestable in isolation.

**Implementation:** A new public method `classify_conflicts(artifact_paths: list[str]) -> list[str]` is added to `SyncEngine`. It iterates the paths, calls `_files_identical()` for each path where both source and destination exist, and returns the list of conflicting relative paths. The CLI calls this before `sync_all()` and applies the soft-block logic (prompt / hard block / skip / force) using only standard CLI utilities. `_files_identical()` is promoted from private to public (rename to `files_identical()`).

**Alternatives considered:**
- `global=True` flag or interactive callback on `SyncEngine` — rejected; introduces console/click dependency into core module.
- Inline conflict check in `sync_all()` with a callback — rejected; same concern, harder to test.

## Impacted Modules & Systems

**Code Changes:**
- `libs/beacon/src/beacon/cli.py` — `_detect_agents_global()`, `_install_agent_global()`, agents branch in `install_artifact()`, soft block pre-check (CLI layer) in `abc sync` and `abc install`, `--preserve`/`--force` on `abc install`, `--force` on `abc sync`, `abc reset` command, `abc update` deprecated alias, contribute no-op verification, `abc warehouse list` and `abc list` updated to surface `agents`, `abc setup` updated to guide user to `abc install agents/<name>`
- `libs/beacon/src/beacon/core/delta.py` — `_agent_live_path()`, `agents_paths` attribute on `DeltaComparator`, `_compare_agent_file()`, `DeltaStatus.STALE` added to enum, STALE enrichment post-processing in `_show_delta_summary()` (reads `~/.config/agentic-beacon/sync-state.json`)
- `libs/beacon/src/beacon/core/sync.py` — `files_identical()` promoted from private to public; new `classify_conflicts(artifact_paths: list[str]) -> list[str]` method; `SyncEngine` itself remains non-interactive
- `libs/beacon/src/beacon/initializer.py` — `_create_agents()`, `_create_structure()`, `TEMPLATE_FILES` updated to include `"agents/README.md"`
- `libs/beacon/src/beacon/warehouse/validator.py` — `REQUIRED_DIRECTORIES` updated to include `"agents"`

**New Files:**
- `libs/beacon/src/beacon/data/templates/agents/README.md`
- `~/.config/agentic-beacon/sync-state.json` (runtime, not repo; versioned schema)
- `examples/sample-warehouse/agents/README.md`

**Test Changes:**
- New unit tests for all new functions
- New integration tests for soft block flows, agent install, reset command, contribute no-op, STALE delta display, relink-prompt TUI
- Template parity test (`agents/README.md` in sample warehouse matches template)

**Repository Branch Strategy:**
- Repository: `agentic-beacon` at `~/Code/oss/agentic-beacon`
- Feature branch: `global-agent-artifact-type`
- Base branch: `main`

## Risks / Trade-offs

**Risk:** Soft block on `abc sync` is a behaviour change for any future automation usage (currently `abc sync` is exclusively a local/interactive command). Scripts that rely on silent overwrite will need `--force` or `--preserve`.
→ **Mitigation:** Non-interactive hard block only fires without explicit flags. Document in release notes as a behaviour change; low urgency for current users.

**Risk:** `abc reset` rename is a breaking change — users with `abc update` in scripts will see a deprecation warning but it still works.
→ **Mitigation:** Hidden alias ensures no breakage; deprecation warning makes the migration path clear.

**Risk:** `~/.config/agentic-beacon/` is a new directory in the user's home — unexpected for users who haven't seen it before.
→ **Mitigation:** Created lazily on first agent install; document in release notes.

**Risk:** Global sync-state keyed by warehouse filesystem path — will silently orphan state if the warehouse is moved or renamed.
→ **Mitigation:** Relink-prompt TUI (Decision 6) handles the common rename/move case by matching on warehouse directory name. Pure-local warehouses are fully supported without any remote git dependency.

**Risk:** Sample warehouse drift between `examples/sample-warehouse/agents/README.md` and the template.
→ **Mitigation:** `TEMPLATE_FILES` updated to include `agents/README.md`; content-parity test catches drift in CI.

## Migration Plan

- `abc sync` / `abc install`: behaviour change (silent overwrite → soft block). Scripts need `--force` or `--preserve` to preserve old behaviour. Document clearly in changelog.
- `abc reset`: purely additive. `abc update` deprecated alias means zero breakage.
- `agents/` directory: additive. Existing warehouses unaffected.
- `~/.config/agentic-beacon/`: created lazily, no action needed from users.

## Open Questions

_All open questions resolved._

1. **Where does the soft-block pre-check live?** → Closed as **Decision 10**: CLI layer. `SyncEngine` remains non-interactive.

2. **Should `abc delta` show `STALE` status for project artifacts?** → Closed as **Non-Goal** for this change. STALE detection is implemented for agent artifacts only (via global sync-state). Project artifact STALE detection (`_check_sync_state` → delta surface) is deferred to a future change.
