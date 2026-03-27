# agent-assisted-setup Specification

## Purpose
TBD - created by archiving change config-based-artifact-management. Update Purpose after archive.
## Requirements
### Requirement: Three setup workflows for beacon.yaml creation
The system SHALL support three distinct workflows for creating and populating beacon.yaml configuration.

#### Scenario: Manual setup creates empty template
- **WHEN** user runs `abc setup` and chooses manual workflow
- **THEN** system creates empty beacon.yaml with commented examples for user to edit

#### Scenario: Copy from existing project
- **WHEN** user copies beacon.yaml from another project to `.agentic-beacon/`
- **THEN** running `abc sync` uses that copied configuration

#### Scenario: Agent-assisted setup installs skill
- **WHEN** user runs `abc setup` for first time
- **THEN** system offers to install "project-setup" skill for agent-assisted configuration

### Requirement: Project-setup skill for agent assistance
The system SHALL provide a project-setup skill that enables agent-assisted beacon.yaml population.

#### Scenario: Skill generates warehouse catalog
- **WHEN** user invokes project-setup skill
- **THEN** skill scans connected warehouse and generates markdown file listing all available artifacts

#### Scenario: Catalog shows artifact structure
- **WHEN** skill generates catalog
- **THEN** catalog displays warehouse directory tree with knowledge, skills, and contexts organized

#### Scenario: Agent reads catalog and project files
- **WHEN** user's AI agent (Cursor, Copilot, etc.) is instructed to use catalog
- **THEN** agent analyzes project files (package.json, requirements.txt, etc.) and warehouse catalog to suggest relevant artifacts

### Requirement: Empty template structure
The system SHALL provide clear template structure when creating empty beacon.yaml.

#### Scenario: Template shows all artifact types
- **WHEN** system creates empty beacon.yaml template
- **THEN** file contains commented examples for knowledge, skills, and contexts sections

#### Scenario: Template includes glob pattern examples
- **WHEN** system creates empty beacon.yaml template
- **THEN** comments show examples of both specific paths and glob patterns

### Requirement: Setup workflow selection
The system SHALL allow users to choose setup workflow based on their needs.

#### Scenario: Interactive setup prompts for workflow choice
- **WHEN** user runs `abc setup` interactively
- **THEN** system asks which workflow: agent-assisted, manual, or skip (will copy from elsewhere)

#### Scenario: Non-interactive setup uses default
- **WHEN** user runs `abc setup --manual` or `abc setup --agent-assisted`
- **THEN** system uses specified workflow without prompting

### Requirement: Catalog generation for agent assistance
The system SHALL generate catalog of warehouse artifacts for agent to read.

#### Scenario: Catalog saved to discoverable location
- **WHEN** project-setup skill generates catalog
- **THEN** catalog saved as `.agentic-beacon/warehouse-catalog.md` for agent to reference

#### Scenario: Catalog includes artifact descriptions
- **WHEN** catalog is generated
- **THEN** each artifact section includes brief description of contents when available

#### Scenario: Catalog format optimized for LLM reading
- **WHEN** catalog is generated
- **THEN** format uses clear markdown structure with paths and descriptions that LLMs can easily parse
