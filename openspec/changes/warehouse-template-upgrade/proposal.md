## Why

When the Agentic Beacon CLI evolves (commands renamed, removed, or added), documentation files already generated in existing warehouses go stale — they still reference outdated commands. There is currently no mechanism to bring those files up to date without manually rewriting them.

## What Changes

- New `abc warehouse template-upgrade` CLI command that re-applies the latest templates to an existing warehouse
- New `.beacon/template-checksums.json` written at `abc warehouse init` time, recording the SHA256 of each generated file
- New `data/historical_hashes.py` shipped inside the CLI package, containing known pristine template hashes for all prior versions — used to bootstrap legacy warehouses that predate checksum tracking
- Upgrade logic classifies each templated file into one of three states: **unmodified** (safe to overwrite), **user-modified** (skip + write `.new` sidecar), or **legacy-unmodified** (detected via historical hashes, treated as safe)
- `--force` flag: bypasses all checks, blindly overwrites all files (scripting-friendly)
- `--interactive` / `-i` flag: for user-modified files, shows a coloured unified diff and prompts per-file before overwriting
- `--dry-run` flag: prints what would change without writing anything

## Capabilities

### New Capabilities

- `template-checksum-tracking`: Writing and reading `.beacon/template-checksums.json` at warehouse init and upgrade time
- `warehouse-template-upgrade`: The `abc warehouse template-upgrade` command — upgrade logic, file classification, `.new` sidecar writing, flag handling
- `historical-hashes-registry`: The in-package registry of known pristine template hashes for legacy warehouse bootstrapping

### Modified Capabilities

- None — `abc warehouse init` gains checksum writing as an additive side-effect, no existing requirements change

## Impact

- `libs/beacon/src/beacon/initializer.py` — write `.beacon/template-checksums.json` on init
- `libs/beacon/src/beacon/cli.py` — register new `warehouse template-upgrade` subcommand
- `libs/beacon/src/beacon/data/historical_hashes.py` — new module, maintained alongside template changes
- `libs/beacon/tests/` — new unit tests for upgrade logic and checksum tracking
- `examples/sample-warehouse/` — gains `.beacon/template-checksums.json` example file

## Manual Intervention Requirements

- **[Manual] Merge PR for prerequisite** (`feat/extract-warehouse-templates`): The template-as-files extraction PR must be merged before this change can be implemented.
  - **Rationale**: PRs are always merged via GitHub UI per project standards — the agent creates the PR but cannot merge it.
  - **Timing**: Before beginning any implementation tasks.

- **[Manual] Merge this feature PR**: Once implementation is complete and CI passes, merge the resulting PR via GitHub UI.
  - **Rationale**: Same as above — merges are always a human action.
  - **Timing**: After task 6 (integration / happy path) is verified.

---

## Enhancement Metadata

**Enhanced**: 2026-03-17
**Methodology**: Spec-Driven Development + TDD
**Enhancements Applied**:
- ✅ Manual intervention requirements identified
- ✅ Impacted modules and systems documented in design.md
- ✅ Task phase summaries added (Goal/Input/Output/Validation)
- ✅ TDD criteria with test cases added to key tasks
- ✅ Risk mitigation strategies formalized

**Status**: Ready for implementation via `/opsx:apply warehouse-template-upgrade`
