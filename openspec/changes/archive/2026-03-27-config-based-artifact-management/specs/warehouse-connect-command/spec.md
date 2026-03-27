## ADDED Requirements

### Requirement: Connect project to local warehouse
The system SHALL provide a command to connect a project to a local warehouse directory, creating configuration that persists the connection.

#### Scenario: Connect with explicit path parameter
- **WHEN** user runs `abc warehouse connect --path /path/to/warehouse`
- **THEN** system validates warehouse structure, creates `.agentic-beacon/config.toml` with local_path, and confirms connection

#### Scenario: Interactive connection prompts for path
- **WHEN** user runs `abc warehouse connect` without path parameter
- **THEN** system prompts for warehouse path, validates structure, and creates config

#### Scenario: Connection with relative path
- **WHEN** user provides relative path like `~/org-warehouse` or `../my-warehouse`
- **THEN** system resolves to absolute path before storing in config

### Requirement: Warehouse structure validation
The system SHALL validate that a directory contains required warehouse structure before accepting connection.

#### Scenario: Valid warehouse structure
- **WHEN** system validates directory with required directories (`contexts/`, `knowledge/`, `knowledge/global/`, `skills/`, `docs/`) and files (`contexts/AGENTS.global.md`, etc.)
- **THEN** system accepts warehouse as valid

#### Scenario: Missing required directory
- **WHEN** system validates directory missing `contexts/` or `knowledge/` or other required directory
- **THEN** system rejects connection with error message specifying which directory is missing

#### Scenario: Missing required file
- **WHEN** system validates directory missing `contexts/AGENTS.global.md` or other required file
- **THEN** system rejects connection with error message specifying which file is missing

#### Scenario: Invalid directory does not exist
- **WHEN** user provides path to non-existent directory
- **THEN** system displays error indicating path not found

### Requirement: Configuration persistence
The system SHALL persist warehouse connection in project-level gitignored config file.

#### Scenario: Create config file on first connection
- **WHEN** user connects to warehouse and `.agentic-beacon/config.toml` does not exist
- **THEN** system creates `.agentic-beacon/` directory and `config.toml` file with warehouse path

#### Scenario: Update existing config on reconnection
- **WHEN** user connects to different warehouse and config.toml already exists
- **THEN** system updates local_path in existing config file

#### Scenario: Config includes connection timestamp
- **WHEN** system creates or updates connection config
- **THEN** config includes connected_at timestamp for reference

### Requirement: Path validation on command execution
The system SHALL validate connected warehouse path still exists and is valid when executing commands that require warehouse access.

#### Scenario: Valid connected warehouse
- **WHEN** user runs command requiring warehouse and connected path exists with valid structure
- **THEN** system proceeds with command execution

#### Scenario: Connected warehouse no longer exists
- **WHEN** user runs command requiring warehouse and connected path has been deleted or moved
- **THEN** system displays error with suggestion to reconnect using `abc warehouse connect`

#### Scenario: Connected warehouse structure changed
- **WHEN** user runs command requiring warehouse and structure no longer valid
- **THEN** system displays error explaining validation failure and suggests reconnecting
