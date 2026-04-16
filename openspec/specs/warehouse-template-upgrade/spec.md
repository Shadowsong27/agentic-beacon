# warehouse-template-upgrade Specification

## Purpose
Created by archiving change warehouse-template-upgrade. Update Purpose after archive.
## Requirements

### Requirement: Command is registered under the warehouse group
`abc warehouse template-upgrade` SHALL be a subcommand of the existing `abc warehouse` command group.

#### Scenario: Command is discoverable
- **WHEN** user runs `abc warehouse --help`
- **THEN** `template-upgrade` appears in the listed subcommands with a brief description

### Requirement: File classification before any writes
Before writing any file, the command SHALL classify every tracked template file into exactly one of three states:

- **unmodified**: on-disk hash matches stored checksum → safe to upgrade
- **user-modified**: on-disk hash differs from stored checksum → protect by default
- **legacy-unmodified**: no checksum file exists AND on-disk hash matches a known pristine hash in the historical hashes registry → safe to upgrade

#### Scenario: Unmodified file is upgraded
- **WHEN** a templated file's on-disk SHA256 matches the hash stored in `.beacon/template-checksums.json`
- **THEN** the command overwrites the file with the current template content
- **THEN** the command prints a success line: `✓ Upgraded <path>`

#### Scenario: User-modified file is skipped by default
- **WHEN** a templated file's on-disk SHA256 does NOT match the stored checksum
- **AND** `--force` and `--interactive` are not passed
- **THEN** the command writes the new template to `<path>.new`
- **THEN** the command prints a warning: `⚠ <path> was modified. New template written to <path>.new — merge manually.`
- **THEN** the original file is NOT modified

#### Scenario: .new sidecar is not overwritten if already present
- **WHEN** a `<path>.new` file already exists
- **THEN** the command skips writing the `.new` sidecar
- **THEN** the command prints: `⚠ <path>.new already exists — skipping sidecar write.`

#### Scenario: Legacy-unmodified file is upgraded
- **WHEN** no `.beacon/template-checksums.json` exists
- **AND** a templated file's on-disk SHA256 matches a hash in `KNOWN_TEMPLATE_HASHES`
- **THEN** the command treats the file as unmodified and upgrades it
- **THEN** the command prints: `✓ Upgraded <path> (legacy warehouse)`

#### Scenario: Legacy warehouse with unknown file hash
- **WHEN** no `.beacon/template-checksums.json` exists
- **AND** a templated file's on-disk SHA256 does NOT match any known hash
- **THEN** the command treats the file as user-modified and writes a `.new` sidecar

### Requirement: --dry-run shows planned actions without writing
When `--dry-run` is passed, the command SHALL print what it would do for each file without writing anything.

#### Scenario: Dry run output
- **WHEN** `abc warehouse template-upgrade --dry-run` is executed
- **THEN** each file's planned action is printed (e.g., `[would upgrade]`, `[would write .new sidecar]`)
- **THEN** no files are created or modified on disk
- **THEN** `.beacon/template-checksums.json` is NOT updated

### Requirement: --force overwrites all files without prompting
When `--force` is passed, the command SHALL overwrite every tracked template file with the current template, regardless of classification.

#### Scenario: Force upgrade of user-modified file
- **WHEN** `abc warehouse template-upgrade --force` is executed
- **AND** a file is classified as user-modified
- **THEN** the file is overwritten with the new template content
- **THEN** no `.new` sidecar is written
- **THEN** the command prints: `✓ Force-upgraded <path>`

### Requirement: --interactive prompts per user-modified file
When `--interactive` / `-i` is passed, the command SHALL pause on each user-modified file, display a coloured unified diff, and prompt the user before overwriting.

#### Scenario: Interactive diff and confirm
- **WHEN** `abc warehouse template-upgrade --interactive` is executed
- **AND** a file is classified as user-modified
- **THEN** a coloured unified diff is printed (red for removed lines, green for added lines)
- **THEN** the user is prompted: `Overwrite <path> with new template? [y/N]`
- **WHEN** the user confirms with `y`
- **THEN** the file is overwritten
- **WHEN** the user declines
- **THEN** the `.new` sidecar is written instead

### Requirement: Summary printed after completion
After processing all files, the command SHALL print a summary line.

#### Scenario: Completion summary
- **WHEN** the command finishes
- **THEN** a summary is printed: `Template upgrade complete. X upgraded, Y skipped (see *.new files).`
