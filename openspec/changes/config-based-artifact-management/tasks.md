## 1. Configuration Management

**Goal**: Establish configuration infrastructure for beacon.yaml (artifact dependencies) and config.toml (warehouse connection)
**Input**: Empty project with no .agentic-beacon directory
**Output**: Parsers, validators, and readers/writers for both config files
**Validation**: Successfully parse and validate example beacon.yaml and config.toml files; write and read back with identical content

- [ ] 1.1 Create beacon.yaml schema and parser for artifact dependencies
- [ ] 1.2 Create config.toml schema and parser for warehouse connection
- [ ] 1.3 Implement configuration reader that loads both config.toml and beacon.yaml
  - **Input**: `from beacon.core.config import ConfigReader; reader = ConfigReader(); config = reader.load()`
  - **Expected Output**: Config object with warehouse.local_path and artifacts dict loaded from both files
  - **Validation**: Config object has expected attributes, no exceptions raised, missing files handled gracefully
- [ ] 1.4 Implement configuration writer for persisting warehouse connection
  - **Input**: `writer.write_connection(local_path="/path/to/warehouse")`
  - **Expected Output**: `.agentic-beacon/config.toml` file created with [warehouse] section
  - **Validation**: File exists, contains correct TOML structure, roundtrip read returns same path
- [ ] 1.5 Add validation for beacon.yaml structure (artifacts grouped by type)
- [ ] 1.6 Add validation to ensure .agentic-beacon directory exists before config operations

## 2. Warehouse Structure Validation

**Goal**: Implement validation logic to ensure directories are valid warehouses before accepting connection
**Input**: Candidate warehouse directory path (may be valid or invalid warehouse)
**Output**: WarehouseValidator class that validates required structure and files
**Validation**: Validator correctly accepts examples/sample-warehouse/ and rejects invalid directories with clear error messages

- [ ] 2.1 Create WarehouseValidator class with structure validation methods
- [ ] 2.2 Implement validation for required directories (contexts/, knowledge/, knowledge/global/, skills/, docs/)
- [ ] 2.3 Implement validation for required files (contexts/AGENTS.global.md, README files)
  - **Input**: `validator.validate("/path/to/warehouse")`
  - **Expected Output**: `ValidationResult(valid=True)` for examples/sample-warehouse/, `ValidationResult(valid=False, errors=["Missing contexts/AGENTS.global.md"])` for invalid
  - **Validation**: Returns True for valid warehouse, False with specific missing file/directory names for invalid
- [ ] 2.4 Add validation error messages with specific guidance for each failure type
- [ ] 2.5 Implement path resolution to handle relative and absolute paths (~/warehouse, ../warehouse)
- [ ] 2.6 Add check to ensure warehouse is not confused with artifacts/ structure (doesn't exist in warehouse)

## 3. Warehouse Connect Command

**Goal**: Enable users to connect project to local warehouse via CLI command
**Input**: User at project root with local warehouse directory available
**Output**: `abc warehouse connect` command that validates and persists connection
**Validation**: Run `abc warehouse connect --path examples/sample-warehouse` from clean project; `.agentic-beacon/config.toml` created with correct warehouse path

- [ ] 3.1 Add warehouse command group using @click.group()
- [ ] 3.2 Implement warehouse connect command with --path parameter support
- [ ] 3.3 Add interactive prompt workflow when --path not provided
- [ ] 3.4 Integrate WarehouseValidator to validate structure before accepting connection
- [ ] 3.5 Implement connection persistence using config.toml writer
- [ ] 3.6 Add success confirmation messaging with connection details
- [ ] 3.7 Add progress indicators during validation steps
  - **Input**: `abc warehouse connect --path ~/org-warehouse`
  - **Expected Output**: Progress messages ("✓ Validating warehouse structure...", "✓ Connected successfully!"), exit code 0
  - **Validation**: Config.toml exists with correct path, no errors displayed, confirmation message shows absolute path

## 4. Beacon.yaml Setup Command

**Goal**: Provide `abc setup` command that creates beacon.yaml with three workflow options
**Input**: Project with warehouse connected, no beacon.yaml yet
**Output**: `abc setup` command that creates beacon.yaml template or installs project-setup skill
**Validation**: Run `abc setup --manual`; `.agentic-beacon/beacon.yaml` created with empty template structure

- [ ] 4.1 Implement abc setup command for project initialization
  - **Input**: `abc setup` (after warehouse connected)
  - **Expected Output**: Interactive prompt asking which workflow (agent-assisted/manual/skip), beacon.yaml created
  - **Validation**: Command succeeds, beacon.yaml exists, contains artifacts: {} structure
- [ ] 4.2 Create empty beacon.yaml template with commented examples
- [ ] 4.3 Add support for three workflows: agent-assisted, copy, manual
- [ ] 4.4 Implement project-setup skill installation for agent-assisted workflow
- [ ] 4.5 Add interactive workflow selection prompts
- [ ] 4.6 Add --manual and --agent-assisted flags for non-interactive mode

## 5. Project-Setup Skill for Agent Assistance

**Goal**: Create skill that generates warehouse catalog for agent-assisted beacon.yaml population
**Input**: Connected warehouse with various artifacts
**Output**: project-setup skill that scans warehouse and generates markdown catalog
**Validation**: Run skill; `.agentic-beacon/warehouse-catalog.md` created with tree structure of warehouse artifacts

- [ ] 5.1 Create project-setup skill with SKILL.md
- [ ] 5.2 Implement warehouse catalog generation (scan warehouse, output markdown tree)
- [ ] 5.3 Save catalog to .agentic-beacon/warehouse-catalog.md
- [ ] 5.4 Format catalog for LLM readability (clear markdown structure)
- [ ] 5.5 Include artifact descriptions in catalog when available
- [ ] 5.6 Add instructions in skill for agent to analyze project files and populate beacon.yaml
- [ ] **[MANUAL]** 5.7 Test catalog with actual AI agent (Cursor/Copilot) to verify agent can populate beacon.yaml
  - **Input**: Invoke project-setup skill, have agent read warehouse-catalog.md
  - **Expected Output**: Agent successfully populates beacon.yaml with relevant artifacts based on project analysis
  - **Validation**: Generated beacon.yaml contains appropriate artifacts for project type, no hallucinated paths

## 6. Snapshot-Based Sync Implementation

**Goal**: Implement SyncEngine that performs pure copy (no symlinks) of artifacts from warehouse to project
**Input**: beacon.yaml with artifact list, connected warehouse
**Output**: SyncEngine class that copies artifacts preserving directory structure and supporting glob patterns
**Validation**: Create test beacon.yaml with glob pattern; SyncEngine copies matching files to .agentic-beacon/artifacts/ with correct structure

- [ ] 6.1 Create SyncEngine class for artifact syncing
- [ ] 6.2 Implement pure copy sync (no symlinks) from warehouse to .agentic-beacon/artifacts/
  - **Input**: `sync_engine.sync()` with beacon.yaml containing `knowledge: ["languages/python/**/*.md"]`
  - **Expected Output**: All matching .md files copied to .agentic-beacon/artifacts/knowledge/languages/python/ structure
  - **Validation**: Files are actual copies (not symlinks), directory structure preserved, `os.path.islink()` returns False for all
- [ ] 6.3 Add glob pattern expansion support using Python glob module
- [ ] 6.4 Implement directory structure preservation during copy
- [ ] 6.5 Add idempotent sync logic (detect unchanged files, skip copying)
- [ ] 6.6 Implement --preserve flag to skip files with local modifications
- [ ] 6.7 Add --prune flag to remove artifacts no longer in beacon.yaml
- [ ] 6.8 Add verbose logging showing which files were synced and which glob patterns matched

## 7. ABC Sync Command

**Goal**: Provide declarative `abc sync` command that reads beacon.yaml and invokes SyncEngine
**Input**: Project with warehouse connected and beacon.yaml populated
**Output**: `abc sync` command that syncs artifacts according to beacon.yaml
**Validation**: Modify beacon.yaml to add/remove artifacts, run `abc sync`; artifacts directory matches beacon.yaml specification

- [ ] 7.1 Implement abc sync command (reads beacon.yaml, invokes SyncEngine)
  - **Input**: `abc sync` with beacon.yaml containing 5 artifacts
  - **Expected Output**: Progress messages showing sync status, exit code 0, "✓ Synced N artifacts"
  - **Validation**: `.agentic-beacon/artifacts/` contains exactly the artifacts specified in beacon.yaml, no extras
- [ ] 7.2 Add validation that warehouse is connected before syncing
- [ ] 7.3 Add validation that beacon.yaml exists before syncing
- [ ] 7.4 Implement artifact path validation (warn if beacon.yaml references missing warehouse files)
- [ ] 7.5 Add progress output during sync operation
- [ ] 7.6 Handle empty beacon.yaml gracefully (no-op sync)
- [ ] 7.7 Add error handling for invalid glob patterns

## 8. Delta Comparison Implementation

**Goal**: Implement DeltaComparator for comparing local artifacts against warehouse
**Input**: Project with synced artifacts, some locally modified
**Output**: DeltaComparator class with hash-based comparison and git diff integration
**Validation**: Modify local artifact, run comparison; returns [Modified] status with correct file path

- [ ] 8.1 Create DeltaComparator class for comparing local vs warehouse artifacts
- [ ] 8.2 Implement hash-based comparison for summary view
- [ ] 8.3 Implement categorization: [Modified], [Added], [Missing]
  - **Input**: `comparator.compare_all()` with 1 modified, 1 added (local only), 1 missing artifact
  - **Expected Output**: `[{path: "knowledge/lessons.md", status: "Modified"}, {path: "skills/new", status: "Added"}, {path: "contexts/backend", status: "Missing"}]`
  - **Validation**: Correct categorization, all artifacts in beacon.yaml checked, extra files ignored
- [ ] 8.4 Add support for comparing only artifacts in beacon.yaml (not all files)
- [ ] 8.5 Integrate git diff --no-index for detailed file comparison
- [ ] 8.6 Add color output support for diff highlighting

## 9. ABC Delta Command

**Goal**: Provide `abc delta` command showing summary or detailed diff
**Input**: Project with local modifications to synced artifacts
**Output**: `abc delta` showing summary, `abc delta <file>` showing detailed diff
**Validation**: Modify artifact locally, run `abc delta`; shows [Modified] status. Run `abc delta <file>`; shows unified diff

- [ ] 9.1 Implement abc delta command with optional file argument
  - **Input**: `abc delta` (no args) after modifying knowledge/lessons.md
  - **Expected Output**: Summary with `[Modified] knowledge/lessons.md` and suggestion to run `abc delta <file>` for details
  - **Validation**: Exit code 0, all modified files listed, clear status indicators
- [ ] 9.2 Add summary view when no file argument provided (all artifacts)
- [ ] 9.3 Add detailed diff view when file argument provided
  - **Input**: `abc delta knowledge/lessons.md`
  - **Expected Output**: Unified diff format showing added/removed lines with color highlighting
  - **Validation**: Diff output matches `git diff --no-index` format, shows actual line changes
- [ ] 9.4 Handle case where file not in beacon.yaml (error message)
- [ ] 9.5 Handle case where no differences found (success message)
- [ ] 9.6 Add clear status indicators in output ([Modified], [Added], [Missing])
- [ ] 9.7 Add suggestion to run abc sync when [Missing] artifacts found

## 10. Command Structure Reorganization

**Goal**: Reorganize CLI to use warehouse subcommand for warehouse operations
**Input**: Existing flat command structure with `abc init`
**Output**: Warehouse subcommand group with init moved under it, deprecated error for old command
**Validation**: Run `abc warehouse init test-warehouse`; creates warehouse. Run `abc init`; shows deprecation error suggesting new command

- [ ] 10.1 Move init command under warehouse group as warehouse init
- [ ] 10.2 Update help text for all warehouse subcommands
- [ ] 10.3 Add deprecated command handler for abc init (suggest abc warehouse init)
  - **Input**: `abc init my-warehouse`
  - **Expected Output**: Error message: "Command deprecated. Use 'abc warehouse init my-warehouse' instead (Breaking change in v2.0.0)"
  - **Validation**: Exit code 1, helpful error message, no warehouse created
- [ ] 10.4 Ensure warehouse connect, warehouse init are properly grouped
- [ ] 10.5 Keep sync and delta at top level (client operations)

## 11. Gitignore Management

**Goal**: Automatically manage .gitignore to exclude config.toml and artifacts/ while keeping beacon.yaml
**Input**: Project with or without existing .gitignore
**Output**: .gitignore properly configured for agentic-beacon
**Validation**: Create connection and sync; `.gitignore` contains `.agentic-beacon/config.toml` and `.agentic-beacon/artifacts/`, does NOT contain `beacon.yaml`

- [ ] 11.1 Add automatic .gitignore update to exclude .agentic-beacon/config.toml
- [ ] 11.2 Add automatic .gitignore update to exclude .agentic-beacon/artifacts/
- [ ] 11.3 Ensure .agentic-beacon/beacon.yaml is NOT in .gitignore
- [ ] 11.4 Create .gitignore if it doesn't exist in project root
- [ ] 11.5 Append to existing .gitignore without destroying user content

## 12. Error Handling and User Feedback

**Goal**: Provide clear, actionable error messages for all failure scenarios
**Input**: Various error conditions (invalid paths, missing files, etc.)
**Output**: Helpful error messages guiding users to resolution
**Validation**: Trigger each error condition; verify error message is clear and includes actionable suggestion

- [ ] 12.1 Add error handling for non-existent warehouse paths
- [ ] 12.2 Add error handling for invalid warehouse structure with clear messages
- [ ] 12.3 Add error handling for warehouse path that becomes invalid after connection
- [ ] 12.4 Add error handling for missing beacon.yaml when running sync
- [ ] 12.5 Add error handling for connection not established when running sync/delta
- [ ] 12.6 Implement clear error messages with actionable suggestions
- [ ] 12.7 Add helpful error when user tries deprecated abc init command

## 13. Testing

**Goal**: Comprehensive test coverage for all components and workflows
**Input**: Implemented code for all components
**Output**: Unit and integration tests achieving >80% coverage
**Validation**: Run `pytest tests/ -v --cov`; all tests pass, coverage >80%, zero import errors

- [ ] 13.1 Add unit tests for WarehouseValidator with various invalid structures
  - **Input**: `pytest tests/test_warehouse_validator.py -v`
  - **Expected Output**: All test cases pass (valid warehouse, missing directories, missing files, invalid structure)
  - **Validation**: Exit code 0, >10 test cases covering all validation scenarios
- [ ] 13.2 Add unit tests for beacon.yaml parser and validator
- [ ] 13.3 Add unit tests for config.toml read/write operations
- [ ] 13.4 Add unit tests for SyncEngine pure copy logic
- [ ] 13.5 Add unit tests for glob pattern expansion
- [ ] 13.6 Add unit tests for DeltaComparator hash comparison
- [ ] 13.7 Add integration tests for abc warehouse connect workflow
  - **Input**: `pytest tests/integration/test_connect.py -v`
  - **Expected Output**: Test connects to sample warehouse, verifies config.toml created, validates connection persists
  - **Validation**: Exit code 0, integration test covers full connect workflow end-to-end
- [ ] 13.8 Add integration tests for abc setup with different workflows
- [ ] 13.9 Add integration tests for abc sync with various beacon.yaml configurations
- [ ] 13.10 Add integration tests for abc delta summary and detailed views
- [ ] 13.11 Add tests for command structure (warehouse subcommand group)
- [ ] 13.12 Add tests for deprecated abc init error message
- [ ] 13.13 Add tests for gitignore management

## 14. Documentation Updates

**Goal**: Complete documentation for all new commands and workflows
**Input**: Implemented features
**Output**: Comprehensive docs with examples, migration guide, and CHANGELOG update
**Validation**: Review all docs for accuracy, test all example commands, verify migration guide completeness

- [ ] **[MANUAL]** 14.1 Update README.md to change abc init to abc warehouse init
  - **Rationale**: Requires reviewing entire README for all occurrences and updating examples
  - **Timing**: After command implementation complete
- [ ] 14.2 Add comprehensive documentation for beacon.yaml config format
- [ ] 14.3 Document the three setup workflows (agent-assisted, copy, manual)
- [ ] 14.4 Add documentation for abc warehouse connect command
- [ ] 14.5 Add documentation for abc sync command and flags (--preserve, --prune, --verbose)
- [ ] 14.6 Add documentation for abc delta command (summary and detailed views)
- [ ] 14.7 Create usage guide showing complete workflow from connect to sync to delta
- [ ] 14.8 Document glob pattern support with examples
- [ ] 14.9 Add node_modules analogy explanation in documentation
- [ ] 14.10 Document gitignore requirements and automatic management
- [ ] 14.11 Update CHANGELOG.md with breaking change notice
- [ ] **[MANUAL]** 14.12 Create migration guide for users updating from v1.x
  - **Rationale**: Requires understanding user pain points and testing migration scenarios
  - **Timing**: After implementation complete and manual testing with v1.x projects
- [ ] 14.13 Update CLI help text and examples throughout codebase

## 15. Example Warehouse and Project-Setup Skill

**Goal**: Provide working example warehouse and project-setup skill for testing and reference
**Input**: examples/sample-warehouse/ directory
**Output**: Valid warehouse with project-setup skill that generates catalog
**Validation**: Run `abc warehouse connect --path examples/sample-warehouse`; connection succeeds. Invoke project-setup skill; catalog generated

- [ ] 15.1 Create project-setup skill in examples/sample-warehouse/skills/
- [ ] 15.2 Implement catalog generation script in project-setup skill
- [ ] 15.3 Add example beacon.yaml files for different project types
- [ ] 15.4 Verify examples/sample-warehouse/ structure is valid for connection
  - **Input**: `abc warehouse connect --path examples/sample-warehouse`
  - **Expected Output**: "✓ Connected successfully!" message, connection config created
  - **Validation**: WarehouseValidator accepts structure, all required files/directories present
- [ ] 15.5 Test abc warehouse connect with examples/sample-warehouse/
- [ ] 15.6 Test project-setup skill catalog generation with sample warehouse
  - **Input**: Run project-setup skill against examples/sample-warehouse/
  - **Expected Output**: warehouse-catalog.md created with complete artifact tree
  - **Validation**: Catalog lists all knowledge/skills/contexts from sample warehouse

## 16. Backward Compatibility

**Goal**: Ensure warehouses created with v1.x continue to work with v2.0
**Input**: Warehouse created with `abc init` from v1.x
**Output**: v2.0 code successfully validates and connects to old warehouses
**Validation**: Test with actual v1.x warehouse; connection and validation succeed without migration needed

- [ ] 16.1 Verify existing warehouses created with abc init work with new warehouse connect
  - **Input**: Create warehouse with v1.x `abc init`, then connect with v2.0 `abc warehouse connect`
  - **Expected Output**: Connection succeeds, warehouse validates successfully
  - **Validation**: No structural changes required, all validation passes
- [ ] 16.2 Test that warehouse structure validation accepts old warehouses
- [ ] 16.3 Ensure no breaking changes to warehouse structure itself
