# install-flags Specification

## Purpose
TBD - created by archiving change global-agent-artifact-type. Update Purpose after archive.
## Requirements
### Requirement: abc install accepts --preserve flag
`abc install` SHALL accept a `--preserve` flag that causes any file whose target already exists with different content to be skipped silently, without prompting. This mirrors the existing `abc sync --preserve` behaviour.

#### Scenario: --preserve skips conflicting files
- **WHEN** `abc install --preserve` is run AND a target file differs from the warehouse
- **THEN** the file is skipped without any prompt or warning

#### Scenario: --preserve does not affect fresh installs
- **WHEN** `abc install --preserve` is run AND no target file exists yet
- **THEN** the file is written normally (no conflict to preserve)

### Requirement: abc install accepts --force flag
`abc install` SHALL accept a `--force` flag that causes all files to be overwritten without prompting, regardless of content difference or interactive mode.

#### Scenario: --force overwrites without prompt
- **WHEN** `abc install --force` is run AND a target file differs from the warehouse
- **THEN** the file is overwritten without any prompt, even in interactive mode

#### Scenario: --force and --preserve are mutually exclusive
- **WHEN** both `--force` and `--preserve` are passed to `abc install`
- **THEN** the CLI exits with an error: "Cannot use --force and --preserve together"

### Requirement: abc sync accepts --force flag
`abc sync` SHALL accept a `--force` flag that causes all differing files to be overwritten without prompting, for scripting and CI use. This complements the existing `--preserve` flag.

#### Scenario: abc sync --force overwrites without prompt
- **WHEN** `abc sync --force` is run AND local files differ from warehouse
- **THEN** all files are overwritten without any prompt

#### Scenario: abc sync --force and --preserve are mutually exclusive
- **WHEN** both `--force` and `--preserve` are passed to `abc sync`
- **THEN** the CLI exits with an error: "Cannot use --force and --preserve together"
