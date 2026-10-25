## Why

After `abc contribute` pushes an artifact to the warehouse via PR, there is no ergonomic way for teammates (or the contributor themselves) to discover and opt-in to it. `abc sync` only syncs what is already declared in `beacon.yaml`, so new warehouse artifacts are invisible until someone manually inspects the warehouse and edits the config. This creates a gap in the contribute-to-adopt lifecycle that grows more painful as team and warehouse size increase.

## What Changes

- New `abc adopt` command with **git-diff-based discovery**: compares warehouse HEAD against the last sync cursor (`.sync-state`) to surface only artifacts added since the user's last sync, cross-referenced against `beacon.yaml` to exclude already-adopted items
- Interactive **textual TUI** for artifact selection: categorized checkboxes (contexts, skills, knowledge) with descriptions, select-all/none, confirm/cancel
- **`--all` flag** for full warehouse scan (shows everything unadopted, not just new-since-last-sync)
- **`--dry-run` flag** for preview without modification
- **Non-interactive fallback**: prints adoptable list with manual edit instructions when not running in a TTY
- **Sync notification**: at the end of `abc sync`, prints "N new artifact(s) available -- run `abc adopt` to review" when unadopted artifacts are detected
- After selection, adopt **updates beacon.yaml**, runs a targeted sync, and wires artifacts into agent configs (CLAUDE.md, opencode.json, skill directories)

## Capabilities

### New Capabilities
- `artifact-adoption`: Discovery, interactive selection, and adoption of new warehouse artifacts into beacon.yaml with automatic sync and wiring
- `sync-adoption-notification`: Lightweight detection and notification of unadopted artifacts at the end of `abc sync`

### Modified Capabilities
- `snapshot-based-sync`: Adds `_read_sync_sha()` helper and captures old SHA before write to enable post-sync notification

## Impact

- **New dependency**: `textual>=0.80.0` added to `libs/beacon/pyproject.toml`
- **New module**: `libs/beacon/src/beacon/adopt.py` (discovery logic, data model, TUI app, beacon.yaml updater)
- **Modified**: `libs/beacon/src/beacon/cli.py` (new `abc adopt` command, sync notification hook, `_read_sync_sha` helper)
- **New tests**: `libs/beacon/tests/test_adopt.py`
- **Existing functions reused**: `_get_warehouse_head_sha()`, `_extract_skill_description()`, `_is_interactive()`, `BeaconSettings.from_yaml()`/`.to_yaml()`, `WarehouseDistributor.list_available()`, wiring functions

## Manual Intervention Requirements

No manual intervention required - all changes can be automated. The feature is a local CLI command with no external service registration, no production deployment gates, and no out-of-band authentication. Publishing to PyPI is handled by the existing Release-Please CI/CD pipeline.

---

## Enhancement Metadata

**Enhanced**: 2026-04-16
**Methodology**: Spec-Driven Development
**Enhancements Applied**:
- Manual intervention requirements identified
- Impacted modules and systems documented
- Task verification steps added
- TDD Input/Output/Validation criteria added to key tasks
- Risk mitigation strategies formalized

**Status**: Ready for implementation via `/opsx:apply abc-adopt-command`
