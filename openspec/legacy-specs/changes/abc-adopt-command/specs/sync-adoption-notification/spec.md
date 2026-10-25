## ADDED Requirements

### Requirement: Post-sync notification of unadopted artifacts
The system SHALL print a notification at the end of `abc sync` when the warehouse contains artifacts added since the previous sync that are not in `beacon.yaml`.

#### Scenario: New artifacts available after sync
- **WHEN** `abc sync` completes and 3 warehouse artifacts were added since the previous sync SHA and are not in `beacon.yaml`
- **THEN** system prints "3 new artifact(s) available -- run abc adopt to review" after the sync summary

#### Scenario: No new unadopted artifacts
- **WHEN** `abc sync` completes and all warehouse artifacts since the previous sync are already in `beacon.yaml`
- **THEN** no adoption notification is printed

#### Scenario: First-ever sync (no previous SHA)
- **WHEN** `abc sync` runs for the first time (no prior `.sync-state` file)
- **THEN** no adoption notification is printed (there is no baseline to diff against)

#### Scenario: Dry run does not show notification
- **WHEN** user runs `abc sync --dry-run`
- **THEN** no adoption notification is printed

### Requirement: Lightweight notification check
The system SHALL perform the unadopted-artifact count using only `git diff --name-only` and beacon.yaml comparison, without extracting descriptions or constructing full adoption candidates.

#### Scenario: Notification does not slow down sync
- **WHEN** warehouse has many artifacts
- **THEN** notification check uses only file-path-level operations (no file reads for descriptions)
