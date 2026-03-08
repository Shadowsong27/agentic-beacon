## 1. Configuration Management

**Goal**: Establish configuration infrastructure for beacon.yaml (artifact dependencies) and config.toml (warehouse connection)
**Input**: Empty project with no .agentic-beacon directory
**Output**: Parsers, validators, and readers/writers for both config files
**Validation**: Successfully parse and validate example beacon.yaml and config.toml files; write and read back with identical content

- [ ] 1.1 Create beacon.yaml schema and parser for artifact dependencies
  - **Input**: `from beacon.core.config import BeaconYamlParser; parser = BeaconYamlParser(); config = parser.parse("path/to/beacon.yaml")`
  - **Expected Output**: Python object with `artifacts` dict containing keys: knowledge, skills, contexts (each with list of paths/globs)
  - **Validation**: Parser loads valid YAML, returns structured object, handles missing sections gracefully, rejects invalid YAML with clear error
  - **TDD Test Cases (write these first):**
    - TC1: Valid complete beacon.yaml → Returns BeaconConfig with all artifact types populated
    - TC2: Valid partial beacon.yaml (only knowledge) → Returns BeaconConfig with empty lists for skills/contexts
    - TC3: Empty artifacts section → Returns BeaconConfig with all types as empty lists
    - TC4: Invalid YAML syntax → Raises YAMLParseError with syntax message
    - TC5: Missing artifacts root key → Raises ValidationError "Missing required 'artifacts' section"
    - TC6: Artifact type not a list (string) → Raises ValidationError "Artifact types must be lists"
    - TC7: Unknown artifact type → Raises ValidationError listing unknown type
    - TC8: File not found → Raises FileNotFoundError with helpful message
    - TC9: File is directory not file → Raises IsADirectoryError
    - TC10: Permission denied reading file → Raises PermissionError with clear message
- [ ] 1.2 Create config.toml schema and parser for warehouse connection
  - **Input**: `from beacon.core.config import ConfigTomlParser; parser = ConfigTomlParser(); config = parser.parse("path/to/config.toml")`
  - **Expected Output**: Python object with `warehouse.local_path` attribute containing absolute path string
  - **Validation**: Parser loads valid TOML, returns structured object with warehouse section, handles missing file gracefully
  - **TDD Test Cases (write these first):**
    - TC1: Valid config.toml with warehouse section → Returns Config with local_path set
    - TC2: Valid config with absolute path → local_path is absolute
    - TC3: Valid config with relative path → Raises ValidationError "local_path must be absolute"
    - TC4: Missing warehouse section → Raises ValidationError "Missing [warehouse] section"
    - TC5: Missing local_path key → Raises ValidationError "Missing local_path in [warehouse]"
    - TC6: Invalid TOML syntax → Raises TOMLParseError with syntax message
    - TC7: local_path is empty string → Raises ValidationError "local_path cannot be empty"
    - TC8: File not found → Returns None or empty config (graceful handling)
    - TC9: local_path is not a string → Raises ValidationError "local_path must be string"
    - TC10: Extra unknown keys in config → Ignored gracefully (forward compatibility)
- [ ] 1.3 Implement configuration reader that loads both config.toml and beacon.yaml
  - **Input**: `from beacon.core.config import ConfigReader; reader = ConfigReader(); config = reader.load()`
  - **Expected Output**: Config object with warehouse.local_path and artifacts dict loaded from both files
  - **Validation**: Config object has expected attributes, no exceptions raised, missing files handled gracefully
  - **TDD Test Cases (write these first):**
    - TC1: Both files exist and valid → Returns complete config with both sections
    - TC2: Only config.toml exists → Returns config with warehouse, artifacts is empty
    - TC3: Only beacon.yaml exists → Returns config with artifacts, warehouse is None
    - TC4: Neither file exists → Returns empty config or raises clear error
    - TC5: config.toml invalid but beacon.yaml valid → Raises error for config.toml
    - TC6: beacon.yaml invalid but config.toml valid → Raises error for beacon.yaml
    - TC7: Both files invalid → Raises error for first encountered issue
    - TC8: .agentic-beacon directory doesn't exist → Raises DirectoryNotFoundError
    - TC9: Files exist but unreadable (permissions) → Raises PermissionError with clear message
    - TC10: Load called multiple times → Returns consistent results (idempotent)
- [ ] 1.4 Implement configuration writer for persisting warehouse connection
  - **Input**: `writer.write_connection(local_path="/path/to/warehouse")`
  - **Expected Output**: `.agentic-beacon/config.toml` file created with [warehouse] section
  - **Validation**: File exists, contains correct TOML structure, roundtrip read returns same path
  - **TDD Test Cases (write these first):**
    - TC1: Write new config.toml → File created with warehouse section and local_path
    - TC2: Overwrite existing config.toml → Existing file replaced with new path
    - TC3: Write with relative path → Converts to absolute before writing
    - TC4: Write with ~ in path → Expands ~ to home directory
    - TC5: Write to non-existent .agentic-beacon dir → Creates directory first
    - TC6: Write with None or empty path → Raises ValueError "local_path required"
    - TC7: Write to read-only directory → Raises PermissionError
    - TC8: Roundtrip write then read → Read returns exact same path
    - TC9: Write preserves other TOML sections → Existing sections not removed
    - TC10: Write with invalid path characters → Raises ValueError with validation message
- [ ] 1.5 Add validation for beacon.yaml structure (artifacts grouped by type)
  - **Input**: `validator.validate_structure(beacon_config)` with config containing artifacts.knowledge, artifacts.skills, artifacts.contexts
  - **Expected Output**: `ValidationResult(valid=True)` for correct structure, `ValidationResult(valid=False, errors=[...])` for invalid keys
  - **Validation**: Accepts valid artifact types, rejects unknown types (e.g., "artifacts.unknown"), validates each type contains list of strings
  - **TDD Test Cases (write these first):**
    - TC1: All three valid artifact types → ValidationResult(valid=True)
    - TC2: Only knowledge type → ValidationResult(valid=True)
    - TC3: Unknown artifact type "plugins" → ValidationResult(valid=False, errors=["Unknown artifact type: plugins"])
    - TC4: Artifact type with non-string item → ValidationResult(valid=False, errors=["All items must be strings"])
    - TC5: Artifact type with nested list → ValidationResult(valid=False, errors=["Nested lists not allowed"])
    - TC6: Artifact type with dict instead of list → ValidationResult(valid=False, errors=["Must be list"])
    - TC7: Empty lists for all types → ValidationResult(valid=True)
    - TC8: Multiple unknown types → ValidationResult lists all unknown types in errors
    - TC9: Mixed valid and invalid types → ValidationResult lists only invalid ones
    - TC10: Artifact paths with invalid characters → ValidationResult(valid=False) with path validation errors
- [ ] 1.6 Add validation to ensure .agentic-beacon directory exists before config operations
  - **Input**: `config_manager.validate_directory()` when .agentic-beacon/ doesn't exist
  - **Expected Output**: Raises DirectoryNotFoundError with message "Project not initialized. Run 'abc setup' first."
  - **Validation**: Check passes when directory exists, raises specific exception when missing, error message is actionable
  - **TDD Test Cases (write these first):**
    - TC1: Directory exists → No exception, returns True
    - TC2: Directory doesn't exist → Raises DirectoryNotFoundError with actionable message
    - TC3: Path exists but is a file not directory → Raises NotADirectoryError
    - TC4: Directory exists but unreadable → Raises PermissionError
    - TC5: Validation called from project root → Checks ./.agentic-beacon
    - TC6: Validation called from subdirectory → Still finds project root's .agentic-beacon
    - TC7: Multiple nested projects → Validates nearest .agentic-beacon
    - TC8: Symbolic link to directory → Follows symlink and validates target
    - TC9: Directory is empty → Passes (contents validated separately)
    - TC10: Validation called multiple times → Consistent results (idempotent)

## 2. Warehouse Structure Validation

**Goal**: Implement validation logic to ensure directories are valid warehouses before accepting connection
**Input**: Candidate warehouse directory path (may be valid or invalid warehouse)
**Output**: WarehouseValidator class that validates required structure and files
**Validation**: Validator correctly accepts examples/sample-warehouse/ and rejects invalid directories with clear error messages

- [ ] 2.1 Create WarehouseValidator class with structure validation methods
  - **Input**: `from beacon.core.warehouse import WarehouseValidator; validator = WarehouseValidator(); result = validator.validate("/path/to/warehouse")`
  - **Expected Output**: ValidationResult object with `valid` boolean and `errors` list
  - **Validation**: Class instantiates without errors, validate() method accepts path argument, returns proper result structure
  - **TDD Test Cases (write these first):**
    - TC1: Valid warehouse structure → ValidationResult(valid=True, errors=[])
    - TC2: Missing all required directories → ValidationResult(valid=False, errors=[...list of 5 missing])
    - TC3: Path doesn't exist → ValidationResult(valid=False, errors=["Path not found"])
    - TC4: Path is file not directory → ValidationResult(valid=False, errors=["Path is not a directory"])
    - TC5: Empty directory → ValidationResult(valid=False) with all missing directories listed
    - TC6: Partial structure (only contexts/) → ValidationResult(valid=False) with 4 missing listed
    - TC7: Absolute path provided → Validates correctly
    - TC8: Relative path provided → Resolves and validates correctly
    - TC9: Path with spaces and special chars → Handles correctly
    - TC10: Symlink to valid warehouse → Follows symlink and validates target
- [ ] 2.2 Implement validation for required directories (contexts/, knowledge/, knowledge/global/, skills/, docs/)
  - **Input**: `validator.validate_directories("/path/to/warehouse")`
  - **Expected Output**: For valid warehouse: empty errors list. For missing dirs: `["Missing directory: contexts/", "Missing directory: knowledge/global/"]`
  - **Validation**: Checks all 5 required directories, reports each missing one specifically, accepts when all present
- [ ] 2.3 Implement validation for required files (contexts/AGENTS.global.md, README files)
  - **Input**: `validator.validate("/path/to/warehouse")`
  - **Expected Output**: For valid warehouse: `ValidationResult(valid=True)` for examples/sample-warehouse/, `ValidationResult(valid=False, errors=["Missing contexts/AGENTS.global.md"])` for invalid
  - **Validation**: Returns True for valid warehouse, False with specific missing file/directory names for invalid
  - **TDD Test Cases (write these first):**
    - TC1: All required files present → ValidationResult(valid=True)
    - TC2: Missing contexts/AGENTS.global.md → ValidationResult lists specific missing file
    - TC3: AGENTS.global.md is directory not file → ValidationResult error "Expected file, found directory"
    - TC4: AGENTS.global.md exists but empty → Passes validation (content validation separate)
    - TC5: AGENTS.global.md unreadable (permissions) → ValidationResult error about permissions
    - TC6: README.md present in root → Passes validation
    - TC7: README.md missing → ValidationResult includes missing README
    - TC8: Multiple README variants (README, README.txt) → At least one present passes
    - TC9: All directories present but all files missing → Lists all missing files
    - TC10: Symlink to required file → Follows symlink and validates target exists
- [ ] 2.4 Add validation error messages with specific guidance for each failure type
  - **Input**: `validator.validate("/invalid/warehouse")`
  - **Expected Output**: Error messages like "Missing directory: contexts/ - Create with 'mkdir -p contexts'" or "Missing file: contexts/AGENTS.global.md - See examples/sample-warehouse for template"
  - **Validation**: Each error includes what's missing, why it's required, and actionable fix suggestion
  - **TDD Test Cases (write these first):**
    - TC1: Missing directory → Error includes "mkdir -p" command
    - TC2: Missing file → Error includes reference to example
    - TC3: Multiple errors → All listed with individual guidance
    - TC4: Error message is user-friendly → No technical jargon, clear actionable steps
    - TC5: Error includes context → Explains why item is required
    - TC6: Permission error → Error suggests checking permissions with chmod command
    - TC7: Invalid warehouse that looks like project → Error explains difference
    - TC8: Partial warehouse → Errors prioritized (critical first)
    - TC9: Error includes help flag → Suggests --help for more info
    - TC10: Error formatting consistent → All errors follow same pattern
- [ ] 2.5 Implement path resolution to handle relative and absolute paths (~/warehouse, ../warehouse)
  - **Input**: `validator.resolve_path("~/org-warehouse")` or `validator.resolve_path("../warehouse")`
  - **Expected Output**: Absolute path string (e.g., "/Users/alice/org-warehouse")
  - **Validation**: Expands ~ to home directory, resolves .. to parent, converts to absolute path, handles symlinks correctly
  - **TDD Test Cases (write these first):**
    - TC1: Absolute path → Returns unchanged
    - TC2: Relative path (./warehouse) → Converts to absolute from cwd
    - TC3: Path with ~ → Expands to user's home directory
    - TC4: Path with .. → Resolves parent directory correctly
    - TC5: Path with multiple .. → Resolves all parent references
    - TC6: Path with symlink → Resolves to real path (or preserves symlink based on design)
    - TC7: Path with ~username → Expands to that user's home
    - TC8: Path with trailing slash → Normalized (removed or kept consistently)
    - TC9: Path with /./ in middle → Normalizes to remove redundant components
    - TC10: Path with spaces → Handles correctly without escaping issues
    - TC11: Windows path (C:\) on Unix → Raises error or handles gracefully
    - TC12: Empty path → Raises ValueError "Path cannot be empty"
- [ ] 2.6 Add check to ensure warehouse is not confused with artifacts/ structure (doesn't exist in warehouse)
  - **Input**: `validator.validate("/path/with/.agentic-beacon/artifacts/")`
  - **Expected Output**: `ValidationResult(valid=False, errors=["This appears to be a project directory, not a warehouse. Warehouse should not contain .agentic-beacon/artifacts/"])`
  - **Validation**: Rejects paths containing artifacts/ subdirectory, provides clear error distinguishing warehouse from project

## 3. Warehouse Connect Command

**Goal**: Enable users to connect project to local warehouse via CLI command
**Input**: User at project root with local warehouse directory available
**Output**: `abc warehouse connect` command that validates and persists connection
**Validation**: Run `abc warehouse connect --path examples/sample-warehouse` from clean project; `.agentic-beacon/config.toml` created with correct warehouse path

- [ ] 3.1 Add warehouse command group using @click.group()
  - **Input**: `abc warehouse --help`
  - **Expected Output**: Help text showing available subcommands (init, connect) with descriptions
  - **Validation**: Command group created, help text displays, subcommands listed correctly
- [ ] 3.2 Implement warehouse connect command with --path parameter support
  - **Input**: `abc warehouse connect --path /path/to/warehouse`
  - **Expected Output**: Success message or validation error, exit code 0 on success
  - **Validation**: Command accepts --path parameter, calls validator, persists connection on success
  - **TDD Test Cases (write these first):**
    - TC1: Valid warehouse path → Exit code 0, config.toml created, success message
    - TC2: Invalid warehouse structure → Exit code 1, no config.toml, validation errors displayed
    - TC3: Non-existent path → Exit code 1, error "Path not found"
    - TC4: Path is file not directory → Exit code 1, error "Not a directory"
    - TC5: Already connected (config.toml exists) → Overwrites with new connection
    - TC6: Relative path provided → Converts to absolute, saves absolute path
    - TC7: Path with ~ → Expands to home directory, saves expanded path
    - TC8: No .agentic-beacon directory → Creates directory, then saves config
    - TC9: Insufficient permissions → Exit code 1, error about permissions
    - TC10: Path argument missing value → Exit code 2, shows usage help
- [ ] 3.3 Add interactive prompt workflow when --path not provided
  - **Input**: `abc warehouse connect` (no --path argument)
  - **Expected Output**: Prompt: "Enter warehouse path:" with ability to type path, then validation proceeds
  - **Validation**: Interactive prompt appears, accepts user input, validates entered path, behaves same as --path mode
- [ ] 3.4 Integrate WarehouseValidator to validate structure before accepting connection
  - **Input**: `abc warehouse connect --path /invalid/path`
  - **Expected Output**: Error output listing validation failures, exit code 1, no config.toml created
  - **Validation**: Validation runs before persistence, errors displayed clearly, connection rejected on validation failure
- [ ] 3.5 Implement connection persistence using config.toml writer
  - **Input**: `abc warehouse connect --path ~/org-warehouse` (valid warehouse)
  - **Expected Output**: `.agentic-beacon/config.toml` file created with [warehouse] section containing local_path
  - **Validation**: File exists after command, contains correct TOML structure, path is absolute not relative
- [ ] 3.6 Add success confirmation messaging with connection details
  - **Input**: `abc warehouse connect --path ~/org-warehouse`
  - **Expected Output**: "✓ Warehouse structure validated", "✓ Connected to: /Users/alice/org-warehouse", "Next steps: Run 'abc setup' to configure artifacts"
  - **Validation**: Multi-line success output, shows absolute path, suggests next command
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
  - **Input**: Template generation function called during `abc setup --manual`
  - **Expected Output**: `.agentic-beacon/beacon.yaml` file with structure:
    ```yaml
    artifacts:
      knowledge: []
        # - languages/python/**/*.md
      skills: []
        # - code-review
      contexts: []
        # - backend-microservice
    ```
  - **Validation**: File created, valid YAML, contains all three artifact types with empty lists, includes helpful comments
- [ ] 4.3 Add support for three workflows: agent-assisted, copy, manual
  - **Input**: `abc setup` (interactive)
  - **Expected Output**: Prompt with 3 choices: "1) Agent-assisted (install project-setup skill)", "2) Manual (create empty template)", "3) Skip (create later)"
  - **Validation**: All three workflows implemented, each produces correct outcome, user can select via number
- [ ] 4.4 Implement project-setup skill installation for agent-assisted workflow
  - **Input**: User selects agent-assisted workflow
  - **Expected Output**: project-setup skill copied from warehouse to `.agentic-beacon/skills/project-setup/`, confirmation message
  - **Validation**: Skill directory created, SKILL.md present, user informed how to invoke skill
- [ ] 4.5 Add interactive workflow selection prompts
  - **Input**: `abc setup` without flags
  - **Expected Output**: Clear prompt describing each workflow option with recommendations
  - **Validation**: Prompt displays before any action, user can choose, invalid selections rejected with retry
- [ ] 4.6 Add --manual and --agent-assisted flags for non-interactive mode
  - **Input**: `abc setup --manual` or `abc setup --agent-assisted`
  - **Expected Output**: Skip prompt, execute selected workflow directly, exit code 0
  - **Validation**: Flags bypass interactive prompt, both flags work correctly, mutually exclusive (error if both provided)

## 5. Project-Setup Skill for Agent Assistance

**Goal**: Create skill that generates warehouse catalog for agent-assisted beacon.yaml population
**Input**: Connected warehouse with various artifacts
**Output**: project-setup skill that scans warehouse and generates markdown catalog
**Validation**: Run skill; `.agentic-beacon/warehouse-catalog.md` created with tree structure of warehouse artifacts

- [ ] 5.1 Create project-setup skill with SKILL.md
  - **Input**: Check `examples/sample-warehouse/skills/project-setup/SKILL.md` exists
  - **Expected Output**: SKILL.md file with clear instructions for agent to generate warehouse catalog and populate beacon.yaml
  - **Validation**: File exists, contains proper skill structure, instructions are clear for LLM consumption
- [ ] 5.2 Implement warehouse catalog generation (scan warehouse, output markdown tree)
  - **Input**: Skill invoked with connected warehouse at `~/org-warehouse`
  - **Expected Output**: Tree structure showing all artifacts by type:
    ```markdown
    # Warehouse Catalog
    ## Knowledge
    - languages/python/fastapi-rules.md
    - languages/python/pydantic-patterns.md
    ## Skills
    - code-review
    - generate-tests
    ## Contexts
    - backend-microservice
    ```
  - **Validation**: Scans all artifact directories, outputs markdown, grouped by type, includes relative paths from warehouse root
- [ ] 5.3 Save catalog to .agentic-beacon/warehouse-catalog.md
  - **Input**: Catalog generation completes
  - **Expected Output**: `.agentic-beacon/warehouse-catalog.md` file created with generated catalog content
  - **Validation**: File exists, contains catalog, readable by user and agent, path is project-relative
- [ ] 5.4 Format catalog for LLM readability (clear markdown structure)
  - **Input**: Generated catalog file
  - **Expected Output**: Proper markdown with headers, bullet points, clear grouping, artifact descriptions if available
  - **Validation**: Valid markdown, renders correctly, hierarchical structure clear, no formatting issues
- [ ] 5.5 Include artifact descriptions in catalog when available
  - **Input**: Warehouse artifacts with frontmatter descriptions (e.g., SKILL.md with description field)
  - **Expected Output**: Catalog includes descriptions: `- code-review: Comprehensive PR review skill following best practices`
  - **Validation**: Descriptions extracted from artifact metadata, shown in catalog, missing descriptions handled gracefully (no description shown)
- [ ] 5.6 Add instructions in skill for agent to analyze project files and populate beacon.yaml
  - **Input**: Agent reads project-setup SKILL.md
  - **Expected Output**: Clear step-by-step instructions for agent: 1) Read warehouse-catalog.md, 2) Analyze project files (package.json, requirements.txt, etc.), 3) Select relevant artifacts, 4) Populate beacon.yaml
  - **Validation**: Instructions actionable by LLM, include examples, specify exact file paths, explain selection criteria
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
  - **TDD Test Cases (write these first):**
    - TC1: Copy single file → File exists in artifacts/, is regular file not symlink
    - TC2: Copy with nested directories → Directory structure preserved exactly
    - TC3: Copy overwrites existing file → Existing file replaced with warehouse version
    - TC4: Source file modified between syncs → Copy reflects latest warehouse version
    - TC5: Symlink in warehouse → Copies symlink target content, not symlink itself
    - TC6: Binary file in warehouse → Copied correctly, byte-for-byte identical
    - TC7: File with special characters in name → Copied correctly
    - TC8: Large file (>100MB) → Copied successfully with progress
    - TC9: Source file deleted from warehouse → Local copy retained (cleanup separate)
    - TC10: Insufficient disk space → Raises clear error before partial copy
    - TC11: File permissions preserved → Copied file has same read/write/execute bits
    - TC12: Verify no symlinks created → `assert not os.path.islink(copied_file)` for all files
- [ ] 6.3 Add glob pattern expansion support using Python glob module
  - **Input**: `sync_engine.expand_glob("knowledge/languages/python/**/*.md", warehouse_path)`
  - **Expected Output**: List of absolute file paths matching pattern (e.g., ["/warehouse/knowledge/languages/python/fastapi.md", "/warehouse/knowledge/languages/python/pydantic.md"])
  - **Validation**: Expands ** for recursive matching, handles * for wildcards, returns empty list for no matches, validates pattern syntax
  - **TDD Test Cases (write these first):**
    - TC1: Pattern with ** → Returns all matching files recursively
    - TC2: Pattern with * → Returns files matching in single directory
    - TC3: Pattern with specific filename → Returns exact file if exists
    - TC4: Pattern matching no files → Returns empty list, no error
    - TC5: Pattern with multiple wildcards (*.py/*.md) → Returns all combinations
    - TC6: Pattern with [abc] character class → Expands correctly
    - TC7: Invalid pattern syntax (unmatched bracket) → Raises GlobPatternError
    - TC8: Pattern with escaped special chars → Handles correctly
    - TC9: Pattern matches directories → Returns only files, not directories
    - TC10: Pattern starting with / → Raises error "Patterns must be relative"
    - TC11: Pattern with .. parent reference → Raises error "Parent references not allowed"
    - TC12: Case-sensitive vs insensitive → Respects filesystem case sensitivity
- [ ] 6.4 Implement directory structure preservation during copy
  - **Input**: Copy `knowledge/languages/python/fastapi.md` from warehouse
  - **Expected Output**: File appears at `.agentic-beacon/artifacts/knowledge/languages/python/fastapi.md` with directory structure created
  - **Validation**: All parent directories created, file copied to correct location, directory structure mirrors warehouse
- [ ] 6.5 Add idempotent sync logic (detect unchanged files, skip copying)
  - **Input**: Run `sync_engine.sync()` twice with no changes to warehouse or beacon.yaml
  - **Expected Output**: First run copies files, second run detects no changes and skips all files, both exit code 0
  - **Validation**: Hash comparison used to detect changes, unchanged files not copied, log shows "N files unchanged, 0 copied"
- [ ] 6.6 Implement --preserve flag to skip files with local modifications
  - **Input**: `abc sync --preserve` after modifying local artifact
  - **Expected Output**: Modified file not overwritten, message: "Preserved 1 locally modified file. Use 'abc delta' to review changes."
  - **Validation**: Detects local modifications via hash, skips those files, other files sync normally, user warned about preserved files
- [ ] 6.7 Add --prune flag to remove artifacts no longer in beacon.yaml
  - **Input**: Remove artifact from beacon.yaml, run `abc sync --prune`
  - **Expected Output**: Removed artifact deleted from `.agentic-beacon/artifacts/`, message: "Pruned 1 artifact no longer in beacon.yaml"
  - **Validation**: Only artifacts not in beacon.yaml are deleted, artifacts in config remain, empty directories cleaned up
- [ ] 6.8 Add verbose logging showing which files were synced and which glob patterns matched
  - **Input**: `abc sync --verbose` or `sync_engine.sync(verbose=True)`
  - **Expected Output**: Detailed log: "Expanding pattern: knowledge/**/*.md → 5 matches", "Copying: knowledge/lesson.md → .agentic-beacon/artifacts/knowledge/lesson.md", "Skipped: 3 unchanged files"
  - **Validation**: Shows pattern expansion results, per-file copy operations, unchanged file count, helpful for debugging

## 7. ABC Sync Command

**Goal**: Provide declarative `abc sync` command that reads beacon.yaml and invokes SyncEngine
**Input**: Project with warehouse connected and beacon.yaml populated
**Output**: `abc sync` command that syncs artifacts according to beacon.yaml
**Validation**: Modify beacon.yaml to add/remove artifacts, run `abc sync`; artifacts directory matches beacon.yaml specification

- [ ] 7.1 Implement abc sync command (reads beacon.yaml, invokes SyncEngine)
  - **Input**: `abc sync` with beacon.yaml containing 5 artifacts
  - **Expected Output**: Progress messages showing sync status, exit code 0, "✓ Synced N artifacts"
  - **Validation**: `.agentic-beacon/artifacts/` contains exactly the artifacts specified in beacon.yaml, no extras
  - **TDD Test Cases (write these first):**
    - TC1: First sync with empty artifacts dir → All artifacts copied, exit 0
    - TC2: Second sync with no changes → No files copied (idempotent), exit 0
    - TC3: beacon.yaml has 5 artifacts → Exactly 5 artifacts in artifacts/ after sync
    - TC4: Sync with --verbose flag → Detailed output shown
    - TC5: Sync with --preserve flag → Modified files not overwritten
    - TC6: Sync with --prune flag → Removed artifacts deleted
    - TC7: Interrupted sync (Ctrl+C) → Partial state, resume works
    - TC8: beacon.yaml with globs → All matching files synced
    - TC9: Artifacts dir has extra files not in beacon.yaml → Extra files remain (unless --prune)
    - TC10: Progress shown during sync → Updates displayed, final count correct
- [ ] 7.2 Add validation that warehouse is connected before syncing
  - **Input**: `abc sync` without running `abc warehouse connect` first
  - **Expected Output**: Error: "No warehouse connected. Run 'abc warehouse connect --path <warehouse>' first.", exit code 1
  - **Validation**: Checks for config.toml existence, validates local_path is set, rejects sync with actionable error
  - **TDD Test Cases (write these first):**
    - TC1: No config.toml exists → Exit 1, error message displayed
    - TC2: config.toml exists but empty → Exit 1, error about missing connection
    - TC3: config.toml exists but no warehouse section → Exit 1, specific error
    - TC4: config.toml has warehouse but empty local_path → Exit 1, error about invalid path
    - TC5: config.toml has local_path but warehouse deleted → Exit 1, error about stale connection
    - TC6: Valid connection → Validation passes, sync proceeds
    - TC7: Error message is actionable → Includes exact command to run
    - TC8: Multiple validation errors → Shows all issues at once
    - TC9: Warehouse path is relative in config → Resolves and validates
    - TC10: Permission to read config denied → Error about permissions
- [ ] 7.3 Add validation that beacon.yaml exists before syncing
  - **Input**: `abc sync` without beacon.yaml file
  - **Expected Output**: Error: "No beacon.yaml found. Run 'abc setup' to create artifact configuration.", exit code 1
  - **Validation**: Checks for .agentic-beacon/beacon.yaml, provides actionable next step, exit code 1
- [ ] 7.4 Implement artifact path validation (warn if beacon.yaml references missing warehouse files)
  - **Input**: `abc sync` with beacon.yaml containing `knowledge/missing-file.md` not in warehouse
  - **Expected Output**: Warning: "Artifact not found in warehouse: knowledge/missing-file.md. Skipping.", other artifacts sync normally
  - **Validation**: Validates each artifact exists before copying, warns for missing, continues with available artifacts
- [ ] 7.5 Add progress output during sync operation
  - **Input**: `abc sync` with 10 artifacts to sync
  - **Expected Output**: Progress: "Syncing artifacts... [▓▓▓▓▓░░░░░] 5/10" or "Synced: knowledge/lesson.md (1/10)"
  - **Validation**: Shows incremental progress, updates during sync, final summary shows total synced
- [ ] 7.6 Handle empty beacon.yaml gracefully (no-op sync)
  - **Input**: `abc sync` with `artifacts: {knowledge: [], skills: [], contexts: []}`
  - **Expected Output**: "No artifacts configured in beacon.yaml. Nothing to sync.", exit code 0
  - **Validation**: No errors, no copy operations, friendly message, exit code 0
- [ ] 7.7 Add error handling for invalid glob patterns
  - **Input**: `abc sync` with beacon.yaml containing invalid glob: `knowledge/[invalid`
  - **Expected Output**: Error: "Invalid glob pattern in beacon.yaml: knowledge/[invalid - Unmatched bracket", exit code 1
  - **Validation**: Detects invalid patterns, reports which pattern failed, doesn't crash, exit code 1

## 8. Delta Comparison Implementation

**Goal**: Implement DeltaComparator for comparing local artifacts against warehouse
**Input**: Project with synced artifacts, some locally modified
**Output**: DeltaComparator class with hash-based comparison and git diff integration
**Validation**: Modify local artifact, run comparison; returns [Modified] status with correct file path

- [ ] 8.1 Create DeltaComparator class for comparing local vs warehouse artifacts
  - **Input**: `from beacon.core.delta import DeltaComparator; comparator = DeltaComparator(warehouse_path, artifacts_path); results = comparator.compare_all()`
  - **Expected Output**: List of comparison results with path, status, and hash info for each artifact
  - **Validation**: Class instantiates, compare_all() returns structured results, no errors on empty artifact directory
  - **TDD Test Cases (write these first):**
    - TC1: Both paths valid → Class instantiates successfully
    - TC2: Warehouse path invalid → Raises ValueError with clear message
    - TC3: Artifacts path invalid → Raises ValueError with clear message
    - TC4: Empty artifacts directory → Returns empty results list
    - TC5: compare_all() with no beacon.yaml → Compares all files in artifacts/
    - TC6: compare_all() returns structured data → Each result has path, status, hashes
    - TC7: Multiple comparisons → Results list contains all artifacts
    - TC8: Paths with trailing slashes → Normalized correctly
    - TC9: Relative paths provided → Converted to absolute
    - TC10: Call compare_all() multiple times → Consistent results (idempotent)
- [ ] 8.2 Implement hash-based comparison for summary view
  - **Input**: `comparator.compute_hash("path/to/file.md")`
  - **Expected Output**: SHA256 hash string (e.g., "a1b2c3d4...")
  - **Validation**: Consistent hash for same content, different hash for different content, handles binary and text files
  - **TDD Test Cases (write these first):**
    - TC1: Same content → Identical hashes
    - TC2: Different content → Different hashes
    - TC3: Text file → Computes hash correctly
    - TC4: Binary file → Computes hash correctly
    - TC5: Large file (>100MB) → Computes efficiently without memory issues
    - TC6: Empty file → Returns valid hash (hash of empty string)
    - TC7: File with Unicode characters → Handles correctly
    - TC8: File with different line endings (CRLF vs LF) → Detects as different
    - TC9: File not found → Raises FileNotFoundError
    - TC10: File is directory → Raises IsADirectoryError
    - TC11: Hash algorithm is SHA256 → Verify specific algorithm used
    - TC12: Symlink to file → Hashes target content not symlink itself
- [ ] 8.4 Add support for comparing only artifacts in beacon.yaml (not all files)
  - **Input**: `comparator.compare_from_config(beacon_yaml_path)` with 5 artifacts in beacon.yaml, 10 files in artifacts/
  - **Expected Output**: Comparison results for only the 5 artifacts specified in beacon.yaml, other files ignored
  - **Validation**: Reads beacon.yaml, compares only listed artifacts, doesn't compare extra local files
- [ ] 8.5 Integrate git diff --no-index for detailed file comparison
  - **Input**: `comparator.detailed_diff("knowledge/lesson.md")`
  - **Expected Output**: Unified diff format showing line-by-line changes between warehouse and local versions
  - **Validation**: Executes `git diff --no-index`, captures output, returns formatted diff, handles binary files gracefully
- [ ] 8.6 Add color output support for diff highlighting
  - **Input**: `comparator.detailed_diff("file.md", color=True)` in terminal with color support
  - **Expected Output**: Diff with ANSI color codes: green for additions (+), red for deletions (-), cyan for context
  - **Validation**: Colors applied correctly, TTY detection works, --no-color flag disables colors, colors disabled when piped

## 9. ABC Delta Command

**Goal**: Provide `abc delta` command showing summary or detailed diff
**Input**: Project with local modifications to synced artifacts
**Output**: `abc delta` showing summary, `abc delta <file>` showing detailed diff
**Validation**: Modify artifact locally, run `abc delta`; shows [Modified] status. Run `abc delta <file>`; shows unified diff

- [ ] 9.1 Implement abc delta command with optional file argument
  - **Input**: `abc delta` (no args) after modifying knowledge/lessons.md
  - **Expected Output**: Summary with `[Modified] knowledge/lessons.md` and suggestion to run `abc delta <file>` for details
  - **Validation**: Exit code 0, all modified files listed, clear status indicators
  - **TDD Test Cases (write these first):**
    - TC1: No file argument, 1 modified file → Shows summary with 1 modified entry
    - TC2: No file argument, no changes → "No differences found"
    - TC3: No file argument, multiple changes → Lists all with status indicators
    - TC4: File argument provided → Shows detailed diff for that file
    - TC5: File argument for unchanged file → "No differences found"
    - TC6: File argument for non-existent file → Error with clear message
    - TC7: File argument not in beacon.yaml → Error about not tracked
    - TC8: No warehouse connected → Error before attempting comparison
    - TC9: No beacon.yaml → Error about missing configuration
    - TC10: Invalid file path argument → Error with helpful message
    - TC11: Multiple files as arguments → Error, only one file supported
    - TC12: --help flag → Shows usage and examples
- [ ] 9.2 Add summary view when no file argument provided (all artifacts)
- [ ] 9.3 Add detailed diff view when file argument provided
  - **Input**: `abc delta knowledge/lessons.md`
  - **Expected Output**: Unified diff format showing added/removed lines with color highlighting
  - **Validation**: Diff output matches `git diff --no-index` format, shows actual line changes
- [ ] 9.4 Handle case where file not in beacon.yaml (error message)
  - **Input**: `abc delta some-random-file.md` where file not specified in beacon.yaml
  - **Expected Output**: Error: "File 'some-random-file.md' is not tracked in beacon.yaml. Only artifacts in beacon.yaml can be compared.", exit code 1
  - **Validation**: Validates file is in beacon.yaml before comparing, clear error message, suggests checking beacon.yaml
- [ ] 9.5 Handle case where no differences found (success message)
  - **Input**: `abc delta knowledge/lesson.md` where local and warehouse versions are identical
  - **Expected Output**: "No differences found. Local and warehouse versions are identical.", exit code 0
  - **Validation**: Detects identical content via hash, friendly success message, exit code 0 (not error)
- [ ] 9.6 Add clear status indicators in output ([Modified], [Added], [Missing])
  - **Input**: `abc delta` with 1 modified, 1 added (local only), 1 missing artifact
  - **Expected Output**: Color-coded status: "[Modified]" in yellow, "[Added]" in green, "[Missing]" in red
  - **Validation**: Status indicators clearly visible, colors distinguish types, brackets format consistent
- [ ] 9.7 Add suggestion to run abc sync when [Missing] artifacts found
  - **Input**: `abc delta` showing "[Missing] knowledge/required.md"
  - **Expected Output**: After status list: "💡 Tip: Run 'abc sync' to download missing artifacts from warehouse."
  - **Validation**: Suggestion appears only when missing artifacts found, helpful and actionable

## 10. Command Structure Reorganization

**Goal**: Reorganize CLI to use warehouse subcommand for warehouse operations
**Input**: Existing flat command structure with `abc init`
**Output**: Warehouse subcommand group with init moved under it, deprecated error for old command
**Validation**: Run `abc warehouse init test-warehouse`; creates warehouse. Run `abc init`; shows deprecation error suggesting new command

- [ ] 10.1 Move init command under warehouse group as warehouse init
  - **Input**: `abc warehouse init test-warehouse`
  - **Expected Output**: New warehouse created in ./test-warehouse/ with standard structure
  - **Validation**: Command works under warehouse subcommand, same behavior as old `abc init`, help text updated
- [ ] 10.2 Update help text for all warehouse subcommands
  - **Input**: `abc warehouse --help`
  - **Expected Output**: Help showing "Warehouse management commands" with init and connect subcommands described
  - **Validation**: Help text clear and comprehensive, describes each subcommand purpose, shows examples
- [ ] 10.4 Ensure warehouse connect, warehouse init are properly grouped
  - **Input**: `abc --help`
  - **Expected Output**: Top-level commands include "warehouse" group; `abc warehouse --help` shows init and connect
  - **Validation**: Both commands accessible via warehouse subcommand, no duplicate commands at top level
- [ ] 10.5 Keep sync and delta at top level (client operations)
  - **Input**: `abc --help`
  - **Expected Output**: Top-level commands include "sync", "delta", "setup" (not under warehouse)
  - **Validation**: Client commands accessible at top level, clear separation from warehouse management commands

## 11. Gitignore Management

**Goal**: Automatically manage .gitignore to exclude config.toml and artifacts/ while keeping beacon.yaml
**Input**: Project with or without existing .gitignore
**Output**: .gitignore properly configured for agentic-beacon
**Validation**: Create connection and sync; `.gitignore` contains `.agentic-beacon/config.toml` and `.agentic-beacon/artifacts/`, does NOT contain `beacon.yaml`

- [ ] 11.1 Add automatic .gitignore update to exclude .agentic-beacon/config.toml
  - **Input**: `abc warehouse connect` creates config.toml
  - **Expected Output**: .gitignore contains line `.agentic-beacon/config.toml` (added if not present)
  - **Validation**: Line added to .gitignore, no duplicates if run multiple times, file created if doesn't exist
- [ ] 11.2 Add automatic .gitignore update to exclude .agentic-beacon/artifacts/
  - **Input**: `abc sync` creates artifacts directory
  - **Expected Output**: .gitignore contains line `.agentic-beacon/artifacts/` (added if not present)
  - **Validation**: Line added to .gitignore, trailing slash present, no duplicates on repeated runs
- [ ] 11.3 Ensure .agentic-beacon/beacon.yaml is NOT in .gitignore
  - **Input**: Check .gitignore after all setup commands
  - **Expected Output**: .gitignore does NOT contain `beacon.yaml` or `.agentic-beacon/beacon.yaml`
  - **Validation**: beacon.yaml remains committable, not excluded by any gitignore pattern
- [ ] 11.4 Create .gitignore if it doesn't exist in project root
  - **Input**: Run `abc warehouse connect` in project without .gitignore
  - **Expected Output**: .gitignore file created with agentic-beacon exclusions
  - **Validation**: File created at project root, contains required exclusions, proper file permissions
- [ ] 11.5 Append to existing .gitignore without destroying user content
  - **Input**: .gitignore with existing content: "node_modules/\n*.log", then run abc commands
  - **Expected Output**: .gitignore contains original content plus agentic-beacon exclusions at end
  - **Validation**: Original content preserved, new lines appended, no content lost, proper newline separation

## 12. Error Handling and User Feedback

**Goal**: Provide clear, actionable error messages for all failure scenarios
**Input**: Various error conditions (invalid paths, missing files, etc.)
**Output**: Helpful error messages guiding users to resolution
**Validation**: Trigger each error condition; verify error message is clear and includes actionable suggestion

- [ ] 12.1 Add error handling for non-existent warehouse paths
  - **Input**: `abc warehouse connect --path /does/not/exist`
  - **Expected Output**: Error: "Path not found: /does/not/exist. Please check the path and try again.", exit code 1
  - **Validation**: Detects missing path, clear error message, suggests checking path, exit code 1
- [ ] 12.2 Add error handling for invalid warehouse structure with clear messages
  - **Input**: `abc warehouse connect --path ~/not-a-warehouse` (missing required directories)
  - **Expected Output**: Multi-line error showing all validation failures: "Invalid warehouse structure:", "✗ Missing: contexts/", "✗ Missing: knowledge/", "See examples/sample-warehouse for reference."
  - **Validation**: Lists all failures, provides reference example, actionable guidance
- [ ] 12.3 Add error handling for warehouse path that becomes invalid after connection
  - **Input**: Connect warehouse, then delete/move warehouse directory, run `abc sync`
  - **Expected Output**: Error: "Warehouse not found at /old/path. It may have been moved or deleted. Reconnect with 'abc warehouse connect'.", exit code 1
  - **Validation**: Detects stale connection, explains possible causes, suggests reconnecting
- [ ] 12.4 Add error handling for missing beacon.yaml when running sync
  - **Input**: `abc sync` without beacon.yaml
  - **Expected Output**: Error: "Configuration file not found: .agentic-beacon/beacon.yaml. Run 'abc setup' to create it.", exit code 1
  - **Validation**: Clear error about missing file, suggests setup command, exit code 1
- [ ] 12.5 Add error handling for connection not established when running sync/delta
  - **Input**: `abc sync` or `abc delta` without config.toml (no connection)
  - **Expected Output**: Error: "No warehouse connected. Run 'abc warehouse connect --path <warehouse>' first.", exit code 1
  - **Validation**: Detects missing connection, provides exact command needed, exit code 1
- [ ] 12.6 Implement clear error messages with actionable suggestions
  - **Input**: Any error condition in system
  - **Expected Output**: Error message format: "Problem description. Suggestion for resolution."
  - **Validation**: All errors follow consistent format, include actionable next step, avoid technical jargon where possible
- [ ] 12.7 Add helpful error when user tries deprecated abc init command
  - **Input**: `abc init my-warehouse`
  - **Expected Output**: Error: "Command 'abc init' has been renamed in v2.0.0. Use 'abc warehouse init my-warehouse' instead.", exit code 1
  - **Validation**: Clear deprecation message, shows new command with same arguments, exit code 1

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
  - **Input**: `pytest tests/test_beacon_parser.py -v`
  - **Expected Output**: Test cases pass: valid YAML parsing, invalid YAML rejection, unknown artifact types rejected, glob pattern validation
  - **Validation**: Exit code 0, >8 test cases covering valid/invalid structures, edge cases tested
- [ ] 13.3 Add unit tests for config.toml read/write operations
  - **Input**: `pytest tests/test_config_toml.py -v`
  - **Expected Output**: Tests pass: write config, read config, roundtrip preservation, missing file handling, invalid TOML rejection
  - **Validation**: Exit code 0, tests cover read/write/validation, data preserved through roundtrip
- [ ] 13.4 Add unit tests for SyncEngine pure copy logic
  - **Input**: `pytest tests/test_sync_engine.py -v`
  - **Expected Output**: Tests pass: files are copied not symlinked, directory structure preserved, idempotent sync, hash comparison
  - **Validation**: Exit code 0, verify no symlinks created (os.path.islink() returns False), structure matches
- [ ] 13.5 Add unit tests for glob pattern expansion
  - **Input**: `pytest tests/test_glob_expansion.py -v`
  - **Expected Output**: Tests pass: ** recursive matching, * wildcard, specific files, empty results, invalid patterns
  - **Validation**: Exit code 0, covers all glob operators, handles edge cases, validates error handling
- [ ] 13.6 Add unit tests for DeltaComparator hash comparison
  - **Input**: `pytest tests/test_delta_comparator.py -v`
  - **Expected Output**: Tests pass: identical files show no diff, modified files detected, hash consistency, categorization correct
  - **Validation**: Exit code 0, tests cover Modified/Added/Missing statuses, hash algorithm consistent
- [ ] 13.7 Add integration tests for abc warehouse connect workflow
  - **Input**: `pytest tests/integration/test_connect.py -v`
  - **Expected Output**: Test connects to sample warehouse, verifies config.toml created, validates connection persists
  - **Validation**: Exit code 0, integration test covers full connect workflow end-to-end
- [ ] 13.8 Add integration tests for abc setup with different workflows
  - **Input**: `pytest tests/integration/test_setup.py -v`
  - **Expected Output**: Tests pass for all three workflows (agent-assisted, manual, skip), beacon.yaml created correctly
  - **Validation**: Exit code 0, each workflow tested, file structure validated, flags tested
- [ ] 13.9 Add integration tests for abc sync with various beacon.yaml configurations
  - **Input**: `pytest tests/integration/test_sync.py -v`
  - **Expected Output**: Tests pass: empty config, glob patterns, specific files, --preserve flag, --prune flag, idempotent sync
  - **Validation**: Exit code 0, tests cover all sync scenarios, artifacts copied correctly, flags work
- [ ] 13.10 Add integration tests for abc delta summary and detailed views
  - **Input**: `pytest tests/integration/test_delta.py -v`
  - **Expected Output**: Tests pass: summary view shows all statuses, detailed view shows diff, file not in config error
  - **Validation**: Exit code 0, both views tested, status categorization correct, error cases handled
- [ ] 13.11 Add tests for command structure (warehouse subcommand group)
  - **Input**: `pytest tests/test_cli_structure.py -v`
  - **Expected Output**: Tests pass: warehouse group exists, init under warehouse, connect under warehouse, sync at top level
  - **Validation**: Exit code 0, command structure validated, help text correct
- [ ] 13.12 Add tests for deprecated abc init error message
  - **Input**: `pytest tests/test_deprecated_commands.py -v`
  - **Expected Output**: Test passes: abc init returns exit code 1, error message suggests abc warehouse init
  - **Validation**: Exit code 0 for test, test confirms abc init fails with helpful message
- [ ] 13.13 Add tests for gitignore management
  - **Input**: `pytest tests/test_gitignore.py -v`
  - **Expected Output**: Tests pass: .gitignore created if missing, entries added correctly, no duplicates, existing content preserved
  - **Validation**: Exit code 0, tests cover all gitignore scenarios, beacon.yaml not excluded

## 14. Documentation Updates

**Goal**: Complete documentation for all new commands and workflows
**Input**: Implemented features
**Output**: Comprehensive docs with examples, migration guide, and CHANGELOG update
**Validation**: Review all docs for accuracy, test all example commands, verify migration guide completeness

- [ ] **[MANUAL]** 14.1 Update README.md to change abc init to abc warehouse init
  - **Rationale**: Requires reviewing entire README for all occurrences and updating examples
  - **Timing**: After command implementation complete
- [ ] 14.2 Add comprehensive documentation for beacon.yaml config format
  - **Input**: Create/update docs/beacon-config-guide.md
  - **Expected Output**: Documentation explaining beacon.yaml structure, artifact types, glob patterns, examples for different project types
  - **Validation**: Doc file exists, covers all config options, includes 3+ complete examples, glob syntax explained
- [ ] 14.3 Document the three setup workflows (agent-assisted, copy, manual)
  - **Input**: Update docs with setup workflow section
  - **Expected Output**: Clear explanation of each workflow, when to use each, step-by-step instructions with examples
  - **Validation**: All three workflows documented, pros/cons listed, examples provided for each
- [ ] 14.4 Add documentation for abc warehouse connect command
  - **Input**: Update CLI docs with warehouse connect section
  - **Expected Output**: Command syntax, flags explained, interactive vs parameter mode, examples, troubleshooting common issues
  - **Validation**: Command fully documented, both modes explained, error scenarios covered
- [ ] 14.5 Add documentation for abc sync command and flags (--preserve, --prune, --verbose)
  - **Input**: Update CLI docs with sync command section
  - **Expected Output**: Command syntax, all flags explained, idempotent behavior documented, examples with different flags
  - **Validation**: All flags documented, behavior clear, examples show use cases for each flag
- [ ] 14.6 Add documentation for abc delta command (summary and detailed views)
  - **Input**: Update CLI docs with delta command section
  - **Expected Output**: Both views explained, status indicators documented, contribution workflow described
  - **Validation**: Summary and detailed views explained, examples of each, contribution workflow clear
- [ ] 14.7 Create usage guide showing complete workflow from connect to sync to delta
  - **Input**: Create docs/complete-workflow-guide.md
  - **Expected Output**: Step-by-step guide: clone warehouse → connect → setup → sync → modify → delta → contribute
  - **Validation**: Complete workflow documented, each step explained, includes expected output at each stage
- [ ] 14.8 Document glob pattern support with examples
  - **Input**: Add glob patterns section to beacon-config-guide.md
  - **Expected Output**: Glob syntax explained: *, **, specific examples (languages/**/*.md, skills/code-*), gotchas documented
  - **Validation**: Glob operators documented, 5+ examples provided, common mistakes explained
- [ ] 14.9 Add node_modules analogy explanation in documentation
  - **Input**: Update README.md introduction with analogy
  - **Expected Output**: Clear explanation comparing artifacts/ to node_modules, beacon.yaml to package.json, warehouse to npm registry
  - **Validation**: Analogy present in README, helps users understand snapshot model quickly
- [ ] 14.10 Document gitignore requirements and automatic management
  - **Input**: Add section on gitignore to setup documentation
  - **Expected Output**: Explains what must be ignored (config.toml, artifacts/), what must be committed (beacon.yaml), automatic management described
  - **Validation**: Gitignore requirements clear, automatic behavior documented, manual override explained
- [ ] 14.11 Update CHANGELOG.md with breaking change notice
  - **Input**: Update CHANGELOG.md for v2.0.0
  - **Expected Output**: Breaking changes section: abc init → abc warehouse init, config-based management introduced, migration notes
  - **Validation**: CHANGELOG updated, breaking changes clearly marked, version bump to 2.0.0, date added
- [ ] 14.13 Update CLI help text and examples throughout codebase
  - **Input**: Review all Click command definitions for help text
  - **Expected Output**: All commands have clear help text, examples included where helpful, consistent terminology
  - **Validation**: Run `abc --help`, `abc warehouse --help`, `abc sync --help` etc., verify help text quality

## 15. Example Warehouse and Project-Setup Skill

**Goal**: Provide working example warehouse and project-setup skill for testing and reference
**Input**: examples/sample-warehouse/ directory
**Output**: Valid warehouse with project-setup skill that generates catalog
**Validation**: Run `abc warehouse connect --path examples/sample-warehouse`; connection succeeds. Invoke project-setup skill; catalog generated

- [ ] 15.1 Create project-setup skill in examples/sample-warehouse/skills/
  - **Input**: Check examples/sample-warehouse/skills/project-setup/SKILL.md exists
  - **Expected Output**: Directory structure: skills/project-setup/SKILL.md with complete skill definition
  - **Validation**: Directory exists, SKILL.md has proper format, instructions clear for LLM, includes catalog generation steps
- [ ] 15.2 Implement catalog generation script in project-setup skill
  - **Input**: Skill includes script or clear instructions for generating catalog
  - **Expected Output**: Script/instructions that scan warehouse and output markdown catalog to .agentic-beacon/warehouse-catalog.md
  - **Validation**: Script executable, generates valid markdown, handles missing directories gracefully
- [ ] 15.3 Add example beacon.yaml files for different project types
  - **Input**: Create examples/sample-warehouse/examples/beacon.yaml.python, beacon.yaml.typescript, beacon.yaml.data-platform
  - **Expected Output**: Three example files showing typical artifact selections for different project types
  - **Validation**: All three files exist, contain realistic artifact selections, include helpful comments
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
  - **Input**: `validator.validate("/path/to/v1-warehouse")`
  - **Expected Output**: ValidationResult(valid=True) with no structural change requirements
  - **Validation**: Old warehouse structure matches new requirements, all required directories present
- [ ] 16.3 Ensure no breaking changes to warehouse structure itself
  - **Input**: Compare required directories between v1.x and v2.0
  - **Expected Output**: Identical requirements (contexts/, knowledge/, knowledge/global/, skills/, docs/)
  - **Validation**: No new required directories added, no existing directories removed, structure fully backward compatible
