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
