# template-checksum-tracking Specification

## Purpose
Created by archiving change warehouse-template-upgrade. Update Purpose after archive.
## Requirements

### Requirement: Checksum file is written on warehouse init
When `abc warehouse init` creates a warehouse, it SHALL write a `.beacon/template-checksums.json` file containing the SHA256 hash of every file that was generated from a template.

The JSON structure SHALL be:
```json
{
  "beacon_version": "<current CLI version>",
  "files": {
    "<relative-path-from-warehouse-root>": "<sha256-hex-digest>"
  }
}
```

#### Scenario: Checksum file created alongside templated files
- **WHEN** `abc warehouse init` successfully generates a warehouse
- **THEN** `.beacon/template-checksums.json` exists in the warehouse root
- **THEN** every template-generated file has an entry in `files` keyed by its relative path
- **THEN** each value is the SHA256 hex digest of the written file's content

#### Scenario: Checksum file is not created if init fails mid-way
- **WHEN** `abc warehouse init` raises an error before completing all file writes
- **THEN** `.beacon/template-checksums.json` is NOT written (no partial state)

### Requirement: Checksum file is updated after a successful template upgrade
After `abc warehouse template-upgrade` finishes, it SHALL overwrite `.beacon/template-checksums.json` to reflect the current on-disk state of all tracked template files (upgraded and skipped).

#### Scenario: Checksums refreshed after upgrade
- **WHEN** `abc warehouse template-upgrade` completes without error
- **THEN** `.beacon/template-checksums.json` contains fresh SHA256 hashes for all template-tracked files
- **THEN** files that were skipped (user-modified) retain their current on-disk hash in the file

### Requirement: Checksum file is ignored by warehouse VCS patterns
The `.beacon/` directory SHALL be excluded from any generated `.gitignore` patterns so that the checksum file is committed alongside the warehouse.

#### Scenario: .beacon directory is not gitignored
- **WHEN** `abc warehouse init` generates a `.gitignore`
- **THEN** `.beacon/` is NOT listed as an ignored path
