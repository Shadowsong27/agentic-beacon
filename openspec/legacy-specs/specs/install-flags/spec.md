# install-flags Specification

## Purpose

Expose `--preserve` and `--force` flags on `abc install` so users can control conflict behavior non-interactively (CI pipelines, scripted installs, bulk operations).

> Historical context: earlier versions of this spec also covered `abc sync --preserve` and `abc sync --force`. Under the symlink-based sync model (see `openspec/specs/symlink-based-sync/spec.md`), `abc sync` no longer overwrites files — it creates or repairs symlinks into the warehouse clone — so the conflict flags were removed from `abc sync`. The flags remain on `abc install` for target paths that may already contain user-managed regular files.

## Requirements

### Requirement: abc install accepts --preserve flag

`abc install` SHALL accept a `--preserve` flag that causes any file whose target already exists with different content to be skipped silently, without prompting.

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
