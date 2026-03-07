## ADDED Requirements

### Requirement: Warehouse initialization via subcommand
The system SHALL provide warehouse initialization functionality through `abc warehouse init <name>` command.

#### Scenario: Create new warehouse with subcommand
- **WHEN** user runs `abc warehouse init my-warehouse`
- **THEN** system creates a new warehouse directory structure with the specified name

#### Scenario: Initialization output matches previous behavior
- **WHEN** user runs `abc warehouse init <name>`
- **THEN** system creates the same directory structure and files as the previous `abc init <name>` command

#### Scenario: All initialization options supported
- **WHEN** user runs `abc warehouse init` with options like --languages, --domains, --org
- **THEN** system processes those options identically to the previous implementation

### Requirement: Error message for deprecated command
The system SHALL provide helpful error message when users attempt to use the deprecated `abc init` command.

#### Scenario: Helpful error for deprecated command
- **WHEN** user runs `abc init <name>`
- **THEN** system displays error message suggesting `abc warehouse init <name>` instead

#### Scenario: Error includes migration guidance
- **WHEN** user runs deprecated `abc init`
- **THEN** error message explains this is a breaking change in v2.0.0

### Requirement: Backward compatibility for existing warehouses
The system SHALL continue to work with warehouses created by previous versions using `abc init`.

#### Scenario: Connect to warehouse created with old command
- **WHEN** user connects to a warehouse directory created with `abc init` from previous version
- **THEN** system validates and connects successfully without requiring migration

#### Scenario: Old warehouse structure recognized
- **WHEN** system validates a warehouse created by previous version
- **THEN** validation succeeds if structure meets requirements regardless of creation method
