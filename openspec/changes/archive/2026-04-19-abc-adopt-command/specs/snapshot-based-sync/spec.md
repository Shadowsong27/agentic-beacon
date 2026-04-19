## MODIFIED Requirements

### Requirement: Snapshot at point in time
The system SHALL create snapshot of artifacts at time of sync, not dynamic link to warehouse state. The system SHALL also capture the previous sync-state SHA before overwriting it, to enable post-sync notification of new warehouse artifacts.

#### Scenario: Warehouse changes don't auto-update project
- **WHEN** artifact is modified in warehouse after sync
- **THEN** project's copy remains at previous state until next `abc sync`

#### Scenario: Project isolation
- **WHEN** multiple projects sync from same warehouse at different times
- **THEN** each project has independent snapshot reflecting warehouse state at their sync time

#### Scenario: Previous sync SHA captured before overwrite
- **WHEN** `abc sync` runs and a `.sync-state` file exists from a prior sync
- **THEN** system reads the old SHA before writing the new one, making it available for post-sync notification logic
