# warehouse-agent-scaffold Specification

## Purpose
TBD - created by archiving change global-agent-artifact-type. Update Purpose after archive.
## Requirements
### Requirement: Warehouse init creates agents directory
When `abc warehouse init` is run, the initializer SHALL create an `agents/` directory in the warehouse root alongside the existing `contexts/`, `knowledge/`, `skills/`, and `docs/` directories.

#### Scenario: Fresh warehouse initialization
- **WHEN** a user runs `abc warehouse init <name>` on a new directory
- **THEN** the warehouse root contains an `agents/` directory

#### Scenario: Idempotent re-initialization
- **WHEN** a user runs `abc warehouse init` on an existing warehouse that already has `agents/`
- **THEN** the existing `agents/` directory is not overwritten or emptied

### Requirement: Warehouse init writes agents README template
The initializer SHALL write a `README.md` into the `agents/` directory explaining the markdown frontmatter format (OpenCode/Claude Code standard keys only, no `requires:`), the `abc install agents/<name>.md` workflow, and the role of the `agents.yaml` manifest. The README is written only when no `README.md` already exists.

#### Scenario: README created in new warehouse
- **WHEN** `abc warehouse init` is run and no `agents/README.md` exists
- **THEN** `agents/README.md` is created from the bundled template

#### Scenario: README not overwritten
- **WHEN** `abc warehouse init` is run and `agents/README.md` already exists
- **THEN** the existing file is left unchanged

#### Scenario: README documents agents.yaml
- **WHEN** the bundled README template is inspected
- **THEN** it contains a section documenting `agents/agents.yaml` as the location for Beacon dependency metadata and explicitly states that `requires:` must not appear in agent frontmatter

### Requirement: Sample warehouse reflects agents directory
The `examples/sample-warehouse/` included in the repository SHALL contain an `agents/README.md` matching the current template AND an `agents/agents.yaml` manifest consistent with the current validation rules. Both files stay consistent with the `abc warehouse init` output.

#### Scenario: Sample warehouse is consistent
- **WHEN** the template file `data/templates/agents/README.md` is updated
- **THEN** `examples/sample-warehouse/agents/README.md` is manually updated to match before release

#### Scenario: Sample warehouse ships agents.yaml
- **WHEN** the sample warehouse is inspected
- **THEN** `examples/sample-warehouse/agents/agents.yaml` exists (empty mapping is valid if no sample agents ship) and passes `abc warehouse status` validation
