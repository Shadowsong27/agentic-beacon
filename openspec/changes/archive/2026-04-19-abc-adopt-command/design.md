## Context

`abc sync` syncs only artifacts declared in `beacon.yaml`. After a teammate contributes a new artifact to the warehouse and it gets merged, other developers have no way to discover it exists without manually inspecting the warehouse. The current workaround is `abc warehouse list` + manual `beacon.yaml` editing, which is tedious and doesn't distinguish new additions from long-standing artifacts.

The sync-state cursor (`.agentic-beacon/artifacts/.sync-state`) already records the warehouse HEAD SHA after every successful sync. This provides a natural baseline for git-diff-based discovery. The CLI already uses `click` for prompts and `rich` for display, and the `textual` library (by the same author as `rich`) is the natural choice for a richer interactive experience.

## Goals / Non-Goals

**Goals:**
- Let users discover warehouse artifacts added since their last sync
- Provide an interactive TUI for selecting which artifacts to adopt
- Automatically update `beacon.yaml`, sync, and wire adopted artifacts
- Notify users passively at the end of `abc sync` when new artifacts are available
- Support `--all` for full warehouse scan and `--dry-run` for preview

**Non-Goals:**
- Changing `abc contribute` to auto-wire artifacts (explicitly out of scope -- contribute remains upload-only)
- Auto-adopting artifacts without user consent (explicit opt-in model is intentional)
- Push notifications or webhook-based discovery
- Comment-preserving YAML round-trip (accepted trade-off with existing PyYAML pattern)

## Decisions

### D1: New `adopt.py` module rather than extending `cli.py`

Place all adopt logic (data model, discovery, TUI app, beacon.yaml updater) in `libs/beacon/src/beacon/adopt.py`. The CLI command in `cli.py` imports and orchestrates.

**Rationale:** `cli.py` is already ~4500 lines. This follows the existing pattern where feature modules (`distributor.py`, `initializer.py`, `upgrader.py`) are standalone and imported by `cli.py`. Keeps the module focused and testable.

**Alternatives considered:**
- Inline in `cli.py`: rejected due to file size and mixing TUI framework code with click commands
- Separate `tui/` package: premature -- single file is sufficient for now, can extract later

### D2: Git-diff-based discovery as default, full scan via `--all`

Default mode diffs `old_sync_sha..HEAD` on the warehouse to find only recently added artifacts. `--all` flag scans the entire warehouse and shows everything not in `beacon.yaml`.

**Rationale:** As warehouses grow, showing everything unadopted becomes noisy. Git-diff surfaces only what's actionable (recent additions). The `--all` flag serves the catch-up use case (new team member, initial setup).

**Alternatives considered:**
- Full scan only: rejected -- gets noisy at scale, doesn't distinguish new from long-standing
- Git-diff only (no `--all`): rejected -- need a way to discover older artifacts

### D3: Textual TUI for interactive selection

Use the `textual` library (>=0.80.0) for a full-screen terminal app with categorized checkboxes, keybindings, and footer.

**Rationale:** The user explicitly chose textual for the fun factor. Textual is from the same author as `rich` (already a dependency), offers `app.run()` that blocks and returns a result, and has a built-in test harness (`run_test()`) for headless testing.

**Alternatives considered:**
- InquirerPy: simpler but less polished, new ecosystem
- Custom with rich.live: no new dep but significant code to write
- simple-term-menu: too basic for categorized selection

### D4: Notification-only sync integration

At the end of `abc sync`, print a one-liner when unadopted artifacts are detected. No interactive prompt, no auto-launch of adopt.

**Rationale:** Keeps sync fast and non-interactive-safe (CI pipelines). Discovery is passive; action is explicit via `abc adopt`. Avoids making sync chatty or changing its established behavior.

**Alternatives considered:**
- Interactive prompt at end of sync ("Adopt now? [Y/n]"): rejected -- makes sync unpredictable in scripts
- No integration at all: rejected -- users would never know to run `abc adopt`

### D5: Capture old sync SHA before overwriting

Read the sync-state file into `old_sync_sha` before `_write_sync_state()` overwrites it (around cli.py line 1494). The old SHA is needed post-sync to compute the diff for the notification.

**Rationale:** The write happens before conflict checking (intentional per existing comment). We need the old value later for the notification, so we capture it first. New `_read_sync_sha()` helper is a trivial file read.

### D6: beacon.yaml update via existing Pydantic round-trip

Use `BeaconSettings.from_yaml()` to load, mutate the `artifacts` lists, then `to_yaml()` to write back.

**Rationale:** Consistent with existing patterns. PyYAML doesn't preserve comments, but this matches how `to_yaml()` is already used throughout the codebase.

### D7: Post-adoption sync + wire reuses existing functions

After updating `beacon.yaml`, call into the same sync and wiring logic that `abc sync` uses. Specifically: `SyncEngine.sync_all()` for file copying, then `_wire_contexts_opencode()`, `_wire_contexts_claudecode()`, and `_wire_skills_post_sync()` for agent config integration.

**Rationale:** Avoid duplicating sync/wire logic. The existing functions are well-tested and handle edge cases (idempotent writes, conflict detection, gitignore updates).

## Impacted Modules & Systems

**Code Changes:**
- `libs/beacon/src/beacon/adopt.py` (NEW) - AdoptCandidate dataclass, discover_adoptable() discovery logic, AdoptApp textual TUI, apply_adoption() beacon.yaml updater
- `libs/beacon/src/beacon/cli.py` - New `abc adopt` click command (~60 lines), `_read_sync_sha()` helper, post-sync notification hook (~15 lines inserted after wiring block around line 1654)

**Configuration Changes:**
- `libs/beacon/pyproject.toml` - Add `textual>=0.80.0` to dependencies list

**Test Changes:**
- `libs/beacon/tests/test_adopt.py` (NEW) - Unit tests for discovery, apply_adoption, description extraction; textual `run_test()` harness tests for TUI; integration test for CLI dry-run

**No Data/Schema Changes** - beacon.yaml schema is unchanged; adopt only appends to existing artifact lists.

**No Infrastructure Changes** - Pure CLI feature, no CI/CD pipeline modifications needed.

**Repository Branch Strategy:**
- Repository to be modified: `agentic-beacon`
- Feature branch name: `feat/abc-adopt-command`
- Base branch: `main`

## Risks / Trade-offs

**Risk:** `to_yaml()` strips comments from `beacon.yaml` on round-trip
-> **Mitigation:** This matches existing behavior across the codebase. Comment-preserving YAML (`ruamel.yaml`) can be added later if users request it.

**Risk:** Textual dependency adds ~2MB to install size
-> **Mitigation:** Textual is well-maintained, from the same ecosystem as `rich` (already a dependency), and provides significant UX value for the interactive selector.

**Risk:** Discovery depends on `git diff`, requiring git in the warehouse
-> **Mitigation:** Non-git warehouses already have limited functionality throughout the CLI. Error message is clear and actionable.

**Risk:** `abc adopt` without prior sync state exits with error (first-time users)
-> **Mitigation:** Clear error message directs user to run `abc sync` first, which is the natural prerequisite in the workflow.

**Risk:** Textual TUI may not render correctly in all terminal emulators
-> **Mitigation:** Non-interactive fallback (`_is_interactive()` check) prints a plain list. `--dry-run` also works without TUI. Users in limited terminals can still edit beacon.yaml manually.
