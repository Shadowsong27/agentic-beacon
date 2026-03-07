## Why

Teams need a reproducible, version-controlled way to manage which agentic artifacts (contexts, knowledge, skills) are used in each project. Currently, there's no config-based "shopping list" approach where projects declare their dependencies, and no clear workflow for syncing artifacts from a local warehouse while allowing safe local experimentation. Users should be able to connect to a local git-versioned warehouse, declare artifact dependencies in a configuration file (like package.json or requirements.txt), and sync snapshots to their project while maintaining the ability to contribute improvements back upstream.

## What Changes

- **BREAKING**: Rename `abc init` to `abc warehouse init` to clarify warehouse-related operations
- Add new `abc warehouse connect` command supporting both parameter-based and interactive workflows for connecting projects to local warehouses
- Introduce **config-based artifact management** with `beacon.yaml` (committed) and `config.toml` (gitignored)
- Implement **snapshot-based pure copy sync** from warehouse to project (no symlinks)
- Add `abc setup` command with three workflows: agent-assisted (via skill), copy from existing project, or manual config creation
- Replace separate install/update commands with single declarative `abc sync` command
- Add `abc delta` command for comparing local modifications against warehouse (enables contribution workflow)
- Support glob patterns in artifact specifications (e.g., `languages/python/**/*.md`)
- Establish that projects get reproducible snapshots of artifacts that can be safely modified locally
- Users responsible for keeping local warehouse in sync with remote (via git pull)
- Reorganize command structure: warehouse operations under `warehouse` subcommand, client operations at top level

## Capabilities

### New Capabilities
- `warehouse-connect-command`: Command to connect projects to local warehouse directories with validation and configuration persistence
- `config-based-artifact-management`: Declarative artifact dependencies via beacon.yaml (like package.json/requirements.txt)
- `snapshot-based-sync`: Pure copy sync from warehouse to project enabling safe local experimentation
- `agent-assisted-setup`: Skill-based project setup that generates warehouse catalog for agent to populate config
- `delta-contribution-workflow`: Compare local changes against warehouse and contribute improvements upstream

### Modified Capabilities
- `warehouse-initialization`: Existing warehouse initialization now accessed via `abc warehouse init` instead of `abc init`

## Impact

**Affected Code:**
- `libs/beacon/src/beacon/cli.py` - Add `warehouse` command group, add `warehouse connect`, `setup`, `sync`, `delta` commands
- `libs/beacon/src/beacon/core/warehouse.py` - Local warehouse connection and validation
- `libs/beacon/src/beacon/core/config.py` - Configuration management (config.toml and beacon.yaml)
- `libs/beacon/src/beacon/core/sync.py` - Snapshot-based artifact syncing with glob support
- `libs/beacon/src/beacon/core/delta.py` - Compare local changes against warehouse

**User Experience:**
- **BREAKING**: `abc init` command becomes `abc warehouse init`
- Config-based artifact management (beacon.yaml) - projects declare dependencies like package.json
- Three setup workflows: agent-assisted (skill-based), copy from existing project, or manual
- Single `abc sync` command for declarative artifact syncing (replaces separate install/update)
- `abc delta` for reviewing local changes and contributing back to warehouse
- Snapshot model enables safe local experimentation without affecting other projects
- Users responsible for keeping local warehouse in sync with remote (git pull)
- Clear separation between warehouse operations and client operations

**File Structure:**
```
project-root/
├── .agentic-beacon/
│   ├── config.toml        # Warehouse connection (gitignored)
│   ├── beacon.yaml        # Artifact dependencies (committed)
│   └── artifacts/         # Synced artifacts (gitignored)
├── .gitignore             # Must include .agentic-beacon/ (except beacon.yaml)
└── ...
```

**Documentation:**
- Update all references from `abc init` to `abc warehouse init`
- Add documentation for config-based artifact management (beacon.yaml)
- Document the three setup workflows (agent-assisted, copy, manual)
- Add documentation for `abc warehouse connect`, `abc setup`, `abc sync`, `abc delta` workflows
- Create guide on local warehouse workflow (see docs/local-warehouse-workflow.md)
- Update README with new command structure and node_modules analogy

**Migration:**
- Users must update scripts/documentation using `abc init`
- Existing projects need to adopt beacon.yaml for declarative artifact management
- Update .gitignore patterns to exclude .agentic-beacon/ (except beacon.yaml)

## Manual Intervention Requirements

- **[Manual Step]**: Update existing scripts and documentation that reference `abc init`
  - **Rationale**: Scripts outside the codebase (CI/CD, user documentation) cannot be automatically updated
  - **Timing**: Before releasing v2.0.0 - update all internal documentation and examples

- **[Manual Step]**: Test example warehouse with all three setup workflows
  - **Rationale**: Agent-assisted workflow requires manual verification with actual AI agent (Cursor, Copilot)
  - **Timing**: During phase 15 (Example Warehouse and Project-Setup Skill) - verify catalog generation and agent interaction

- **[Manual Step]**: Create migration guide for users updating from v1.x
  - **Rationale**: Requires understanding of common user pain points and migration patterns
  - **Timing**: During phase 14 (Documentation Updates) - after implementation is complete and migration path is clear

<!-- No other manual intervention required - all code changes can be automated -->

---

## Enhancement Metadata

**Enhanced**: 2026-03-08
**Methodology**: Spec-Driven Development
**Enhancements Applied**:
- ✅ Manual intervention requirements identified
- ✅ Impacted modules and systems documented
- ✅ Task verification steps added
- ✅ TDD Input/Output/Validation criteria added to key tasks
- ✅ Risk mitigation strategies formalized

**Status**: Ready for implementation via `/opsx-apply config-based-artifact-management`
