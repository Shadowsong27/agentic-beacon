# snapshot-based-sync Specification

## Purpose
**Retired.** This capability described the previous copy-based sync model in which `abc sync` copied artifact files from the warehouse into each project's `.agentic-beacon/artifacts/` tree, creating per-project point-in-time snapshots. The model has been replaced by [`symlink-based-sync`](../symlink-based-sync/spec.md), which distributes artifacts as symlinks into the local warehouse clone so that every logical artifact resolves to exactly one physical file per machine. The one-shot conversion of existing copy-based trees into symlinks is specified by [`copy-to-symlink-migration`](../copy-to-symlink-migration/spec.md).

All previous requirements of this capability have been removed. See the `symlink-based-artifact-sync` change for the rationale and migration details.
## Requirements
### Requirement: Capability retired
This capability SHALL be treated as retired. The system SHALL NOT implement copy-based sync semantics; all artifact distribution behavior is defined by `symlink-based-sync` and `copy-to-symlink-migration`.

#### Scenario: `abc sync` does not produce file copies
- **WHEN** user runs `abc sync` on a supported platform
- **THEN** the system materializes artifacts as symlinks per `symlink-based-sync` and does not fall back to copying files

#### Scenario: References to the old copy model are redirected
- **WHEN** a contributor encounters this capability in the spec index
- **THEN** they follow the pointers in Purpose to `symlink-based-sync` and `copy-to-symlink-migration` for the current behavior

### Requirement: Sync resolves dependencies before copying
The system SHALL, at the start of every `abc sync`, compute the full dependency set from `beacon.yaml` and warehouse artifacts before creating or pruning any files. The dependency set includes:

1. The explicitly-adopted contexts and skills listed in `beacon.yaml`.
2. Every context required (via `requires:` frontmatter) by an adopted skill.
3. The derived knowledge set computed by scanning every adopted context and skill for markdown links resolving to warehouse paths under `knowledge/`.

The system SHALL halt with a hard error if any step of dependency resolution detects a required context that does not exist in the warehouse, or a skill with no `requires:` block or malformed frontmatter. Required contexts that exist in the warehouse are auto-pulled transitively even if not explicit in `beacon.yaml`.

#### Scenario: Dependency resolution runs first
- **WHEN** `abc sync` is invoked
- **THEN** the system computes the full dependency set (explicit adoptions + skill-required transitive contexts + derived knowledge) before any file copy, symlink creation, or pruning occurs

#### Scenario: Sync halts on required context missing from warehouse
- **WHEN** dependency resolution detects an adopted skill requires a context that does not exist in the warehouse
- **THEN** `abc sync` exits non-zero before touching any files, and no partial sync state results

#### Scenario: Sync halts on malformed frontmatter
- **WHEN** an adopted skill file has unparseable YAML frontmatter
- **THEN** `abc sync` exits non-zero with an error naming the file and the YAML parse error

### Requirement: Sync prunes orphaned knowledge symlinks
The system SHALL, after creating all required symlinks for the computed dependency set, remove any knowledge symlinks under `.agentic-beacon/artifacts/knowledge/` whose target file is not in the derived knowledge set. The system SHALL also clean up empty parent directories resulting from pruning.

#### Scenario: Orphaned symlink removed
- **WHEN** a previous sync created a symlink to `knowledge/python-standards/lessons/foo.md` but the current derived set no longer contains that file
- **THEN** the symlink is removed during the current sync

#### Scenario: Symlink preserved when still referenced
- **WHEN** a knowledge file is still referenced by at least one adopted context or skill
- **THEN** its symlink is preserved and re-validated (target still points at the warehouse file)

### Requirement: Legacy knowledge field migration
The system SHALL, on reading a `beacon.yaml` that contains an `artifacts.knowledge` field, drop the field silently, emit a single informational log message identifying the migration, and rewrite the file without the field when the first post-migration sync produces any file change. Subsequent syncs find no legacy field and produce no migration log.

#### Scenario: First sync after upgrade drops knowledge field
- **WHEN** a project's `beacon.yaml` contains `artifacts.knowledge: [knowledge/old-entry]` and the user runs `abc sync` on a CLI version that implements this spec
- **THEN** the system logs "`artifacts.knowledge` removed; knowledge is now auto-derived", removes the field from `beacon.yaml`, and completes the sync using the derived knowledge set

#### Scenario: Subsequent sync produces no migration log
- **WHEN** the user runs `abc sync` a second time after the legacy field was already dropped
- **THEN** no migration log message is emitted

#### Scenario: Knowledge previously in beacon.yaml not referenced by any artifact
- **WHEN** the legacy `artifacts.knowledge` list contained entries that no adopted context or skill references
- **THEN** those knowledge files are NOT synced after migration (they are effectively dropped); the user is expected to adopt an artifact that references them if they want them back
