## ADDED Requirements

### Requirement: abc reset command replaces abc update
A new `abc reset` command SHALL be introduced that performs a force-overwrite sync from warehouse to local artifacts — identical in behaviour to the current `abc update` but with a clearer name that signals destructive intent. `abc reset` is exempt from soft blocks; it always overwrites.

#### Scenario: abc reset overwrites all differing files
- **WHEN** `abc reset` is run
- **THEN** all artifact files declared in `beacon.yaml` are copied from the warehouse, overwriting any local modifications without prompting

#### Scenario: abc reset prints overwrite summary
- **WHEN** `abc reset` completes
- **THEN** the CLI prints a summary including the count of files overwritten (content replaced) vs files already in sync

#### Scenario: abc reset does not apply soft blocks
- **WHEN** `abc reset` is run AND local files differ from warehouse
- **THEN** files are overwritten without any warning or prompt (by design — reset is explicit)

### Requirement: abc update is deprecated with a redirect
The existing `abc update` command SHALL be kept as a hidden alias that prints a deprecation notice and then executes `abc reset`.

#### Scenario: abc update prints deprecation notice
- **WHEN** a user runs `abc update`
- **THEN** the CLI prints "[yellow]Warning:[/yellow] 'abc update' is deprecated — use 'abc reset' instead." before executing the reset behaviour

#### Scenario: abc update hidden from help
- **WHEN** a user runs `abc --help`
- **THEN** `abc update` does not appear in the command list (`hidden=True`)
