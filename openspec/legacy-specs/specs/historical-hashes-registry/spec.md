# historical-hashes-registry Specification

## Purpose
Created by archiving change warehouse-template-upgrade. Update Purpose after archive.
## Requirements

### Requirement: Registry module ships inside the CLI package
A module `libs/beacon/src/beacon/data/historical_hashes.py` SHALL exist and be importable as part of the installed package. It SHALL export a single dict:

```python
KNOWN_TEMPLATE_HASHES: dict[str, list[str]]
```

Keys are relative file paths (matching template file names, e.g., `"docs/architecture.md"`). Values are lists of SHA256 hex digests representing every known pristine version of that file.

#### Scenario: Module is importable
- **WHEN** `from beacon.data.historical_hashes import KNOWN_TEMPLATE_HASHES` is executed in the installed package
- **THEN** it succeeds without error
- **THEN** `KNOWN_TEMPLATE_HASHES` is a non-empty dict

### Requirement: Registry is updated when a template changes
Whenever a template file under `data/templates/` is modified, the corresponding entry in `KNOWN_TEMPLATE_HASHES` SHALL be updated to include the SHA256 of the new template content before the release ships.

#### Scenario: CI regression test catches missing registry entry
- **WHEN** a template file is changed in a commit
- **AND** `KNOWN_TEMPLATE_HASHES` does not include the new file's hash
- **THEN** the test suite fails with a descriptive message identifying the missing hash

### Requirement: Registry lookup is case-insensitive to path separators
The lookup SHALL normalise path separators so that `docs/architecture.md` and `docs\architecture.md` match the same registry key.

#### Scenario: Cross-platform path lookup
- **WHEN** the upgrade command looks up a file path on Windows (backslash separator)
- **THEN** the lookup returns the correct hash list as if forward slashes were used
