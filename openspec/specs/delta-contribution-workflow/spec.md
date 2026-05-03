# delta-contribution-workflow Specification

## Purpose
**Retired.** This capability described the previous `abc delta` command and the project-vs-warehouse drift-review workflow that preceded contribution. Under the symlink-based sync model, project artifacts and warehouse artifacts share the same inode, so there is no drift to compare. The useful parts of the old workflow have been split into two successor capabilities:

- Read-side review is covered by [`warehouse-status-command`](../warehouse-status-command/spec.md), which reports uncommitted and unpushed state in the warehouse clone scoped to the current project's `beacon.yaml`.
- Write-side contribution is covered by [`warehouse-contribute-command`](../warehouse-contribute-command/spec.md), which wraps `git add` + `git commit` inside the warehouse clone.

All previous requirements of this capability have been removed. See the `symlink-based-artifact-sync` change for the rationale and migration details.

## Requirements

### Requirement: Capability retired
This capability SHALL be treated as retired. The system SHALL NOT implement a project-vs-warehouse delta command; review and contribution behavior is defined by `warehouse-status-command` and `warehouse-contribute-command`.

#### Scenario: `abc delta` is not available
- **WHEN** user runs `abc delta` after upgrading
- **THEN** the system exits with a non-zero status and an error directing the user to `abc warehouse status`

#### Scenario: References to the old workflow are redirected
- **WHEN** a contributor encounters this capability in the spec index
- **THEN** they follow the pointers in Purpose to `warehouse-status-command` and `warehouse-contribute-command` for the current behavior
