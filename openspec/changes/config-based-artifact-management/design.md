## Context

The Agentic Beacon framework currently uses `abc init` to create new warehouse structures, but lacks a robust mechanism for managing which artifacts from a warehouse are used in each project. There's no config-based "shopping list" approach (like package.json or requirements.txt) for declaring artifact dependencies, and no clear workflow for syncing snapshots from a local warehouse while enabling safe local experimentation and contribution back upstream.

**Current State:**
- `abc init <name>` creates a new warehouse in the current directory
- No way to connect a project to a local warehouse for artifact syncing
- No declarative way to specify which artifacts a project needs
- No mechanism for comparing local modifications against warehouse
- Command structure is flat with no clear grouping
- No support for local experimentation without affecting warehouse directly

**Desired State (Package Manager Model):**
- Warehouse acts as "package registry" (like npm, PyPI)
- Projects declare dependencies in config file (like package.json, requirements.txt)
- Artifacts are pure-copied snapshots (like node_modules, venv)
- Single sync command maintains project state (like npm install)
- Users can safely modify local copies and contribute improvements upstream

**Constraints:**
- Must use snapshot-based pure copy model (no symlinks) for agent compatibility
- Config file must follow package manager patterns (declarative dependencies)
- Local warehouse paths differ per user, so connection config must be gitignored
- Artifact list must be committed to enable reproducible project setup
- Both parameter-based and interactive workflows must be supported
- Users are responsible for keeping local warehouse in sync with remote (via git)
- Breaking changes (command rename) must be clearly communicated

**Stakeholders:**
- Development teams needing reproducible artifact dependencies across projects
- Warehouse creators who develop and maintain artifact repositories
- Framework developers who need to test warehouse changes locally
- Coding agents that need project setup automation via skills
- End users who consume artifacts (should benefit from improved workflow)

## Goals / Non-Goals

**Goals:**
- Implement config-based artifact management with beacon.yaml (declarative dependencies)
- Provide `abc warehouse connect` command supporting both parameter-based and interactive workflows
- Implement snapshot-based pure copy sync (like node_modules pattern)
- Replace separate install/update with single declarative `abc sync` command
- Enable three setup workflows: agent-assisted (skill-based), copy from existing, manual
- Support glob patterns in artifact specifications
- Add `abc delta` for comparing local changes and contributing upstream
- Rename `abc init` to `abc warehouse init` for better command organization
- Validate warehouse structure before accepting connection
- Persist warehouse connection at project level (gitignored config.toml)
- Persist artifact dependencies at project level (committed beacon.yaml)
- Enable safe local experimentation without affecting other projects

**Non-Goals:**
- Automatically syncing local warehouse with remote repository (users handle via git)
- Monitoring local warehouse for staleness or version checking
- Supporting multiple simultaneous warehouse connections per project
- Automatic warehouse discovery or scanning
- Building custom diff algorithm (use git diff --no-index or similar)
- Symlink-based approaches (breaks agent sandboxing)

## Decisions

### 1. Config-Based Artifact Management ("Shopping List" Pattern)

**Decision:** Introduce beacon.yaml config file that declares artifact dependencies, following package manager patterns (package.json, requirements.txt).

**Rationale:**
- **Reproducibility**: Any team member can clone project, run `abc sync`, and get exact same artifacts
- **Precision**: Projects only get artifacts they need (UI project doesn't need DB knowledge)
- **Traceability**: Clear visibility into which artifacts influence agent behavior
- **Version Control**: Config file is committed, enabling dependency tracking over time
- **Familiar Pattern**: Mirrors npm, pip, cargo - developers already understand this model

**beacon.yaml Structure:**
```yaml
# Location: .agentic-beacon/beacon.yaml (committed to git)
artifacts:
  knowledge:
    - languages/python/**/*.md          # Supports glob patterns
    - infrastructure/docker-standards.md
    - company-guidelines/git-commit-style.md

  skills:
    - code-review
    - generate-unit-tests

  contexts:
    - backend-microservice
```

**Key Properties:**
- Committed to git (shared across team)
- Grouped by artifact type (knowledge, skills, contexts)
- Supports glob patterns for flexible selection
- Relative paths from warehouse root

**Alternatives Considered:**
- No config file, always copy everything: Rejected due to bloat and lack of precision
- Store list in gitignored config: Rejected because dependencies should be shared
- Separate files per artifact type: Rejected due to unnecessary complexity

### 2. Snapshot-Based Pure Copy Model (Not Symlinks)

**Decision:** Always perform pure copy from warehouse to project. Never use symlinks.

**Rationale:**
- **Agent Sandboxing**: Many agents (Docker-based, remote environments) can't follow symlinks outside project root
- **Project Stability**: Changes to warehouse don't instantly break all projects; explicit sync required
- **Safe Experimentation**: Developers can modify local copies to test improvements without affecting warehouse
- **Cross-Platform**: Symlinks problematic on Windows; pure copy is universal
- **Versioning**: Each project gets snapshot at point in time, like node_modules or venv

**The Three-Tier Model:**
```
Remote Warehouse (GitHub)
       ↓ git pull
Local Warehouse Clone (~/org-warehouse)
       ↓ abc sync (PURE COPY)
Project Artifacts (.agentic-beacon/artifacts/)
       ↓ abc delta
Back to Warehouse (manual contribution)
```

**Alternatives Considered:**
- Symlinks: Rejected due to agent compatibility issues and lack of isolation
- Hard links: Rejected due to no isolation between projects
- Remote-only fetch: Rejected due to latency and offline workflow issues

### 3. Command Structure Reorganization

**Decision:** Use `warehouse` subcommand group for warehouse operations; client operations at top level.

**Rationale:**
- Clear separation of concerns: warehouse management vs. artifact consumption
- Scalable structure as more operations are added
- Follows CLI best practices (e.g., `git remote`, `npm config`)

**Structure:**
```bash
# Warehouse operations (warehouse management)
abc warehouse init <name>           # Create new warehouse
abc warehouse connect [--path]      # Connect project to warehouse

# Client operations (artifact consumption)
abc setup                            # Initialize project with beacon.yaml
abc sync                             # Sync artifacts per beacon.yaml
abc delta [file]                     # Compare local vs warehouse
```

**Alternatives Considered:**
- Keep flat structure: Rejected due to lack of scalability
- All under warehouse subcommand: Rejected because sync/delta are frequent operations

### 4. Single Declarative Sync Command

**Decision:** Replace separate install/update commands with single `abc sync` that reads beacon.yaml.

**Rationale:**
- **Idempotent**: Can run anytime to ensure project matches declared state
- **Declarative**: State defined in config, not in command history
- **Familiar**: Mirrors `npm install`, `pip install -r requirements.txt`
- **Simpler Mental Model**: One command for "make project match config"

**Behavior:**
```bash
abc sync
# Reads .agentic-beacon/beacon.yaml
# Compares with .agentic-beacon/artifacts/
# Copies missing/changed files from warehouse
# Removes artifacts no longer in beacon.yaml (optional --prune flag)
```

**Alternatives Considered:**
- Separate `install` and `update`: Rejected because difference is unclear
- Always require explicit file arguments: Rejected due to poor UX for initial setup

**Rationale:**
- Clear separation of concerns: warehouse management vs. artifact consumption
- Scalable structure as more warehouse operations are added
- Follows CLI best practices (e.g., `git remote`, `npm config`)

**Structure:**
```
abc warehouse init <name>     # Create new warehouse
abc warehouse connect         # Connect to existing local warehouse
abc warehouse disconnect      # Disconnect from local warehouse (future)
abc warehouse status          # Show current warehouse connection (future)

abc download <artifact>       # Client operations at top level
abc list
abc search
```

**Alternatives Considered:**
- Separate `install` and `update`: Rejected because difference is unclear
- Always require explicit file arguments: Rejected due to poor UX for initial setup

### 5. Configuration Storage Split (Connection vs Dependencies)

**Decision:** Split configuration into two files:
- `.agentic-beacon/config.toml` (gitignored) - warehouse connection with local_path
- `.agentic-beacon/beacon.yaml` (committed) - artifact dependencies

**Rationale:**
- **local_path differs per user**: Alice has `~/warehouse`, Bob has `/Users/bob/my-warehouse`
- **Dependencies are shared**: All team members need same artifacts
- **Like VSCode settings**: `.vscode/settings.json` can be user-specific or shared
- **Security**: Prevents leaking local filesystem structure in shared repos

**config.toml (gitignored):**
```toml
[warehouse]
local_path = "/Users/alice/org-warehouse"
connected_at = "2026-03-08T10:30:00Z"
```

**beacon.yaml (committed):**
```yaml
artifacts:
  knowledge:
    - languages/python/**/*.md
  skills:
    - code-review
  contexts:
    - backend-microservice
```

**Gitignore Requirements:**
```gitignore
.agentic-beacon/config.toml
.agentic-beacon/artifacts/
```

**Alternatives Considered:**
- Single file for both: Rejected because local_path shouldn't be committed
- All in gitignored file: Rejected because dependencies should be shared
- Environment variables: Rejected due to poor persistence

### 6. Three Setup Workflows for Adoption

**Decision:** Support three distinct workflows for populating beacon.yaml to maximize adoption.

**Rationale:**
- Different users have different preferences and contexts
- Agent-assisted workflow leverages user's existing AI tools
- Copy workflow enables quick project scaffolding
- Manual workflow for precise control
- Providing options removes friction to adoption

**Workflow A: Agent-Assisted (Recommended for First-Time)**
```bash
abc warehouse connect --path ~/org-warehouse
abc setup
# CLI installs "project-setup" skill
# User invokes skill: generates warehouse catalog
# Agent reads catalog + analyzes project files
# Agent populates beacon.yaml with relevant artifacts
abc sync
```

**Key Insight:** Use user's own agent (Cursor, Copilot, etc.) rather than building LLM into CLI. The "project-setup" skill generates a text catalog of available warehouse artifacts. The user's agent reads this catalog, analyzes the current project (package.json, requirements.txt, etc.), and intelligently populates beacon.yaml.

**Workflow B: Copy from Existing Project**
```bash
abc warehouse connect --path ~/org-warehouse
cp ../similar-project/.agentic-beacon/beacon.yaml .agentic-beacon/
abc sync
```

**Workflow C: Manual Crafting**
```bash
abc warehouse connect --path ~/org-warehouse
abc setup  # Creates empty beacon.yaml template
# User hand-edits beacon.yaml
abc sync
```

**Alternatives Considered:**
- Only agent-assisted: Rejected because not all users have AI agents
- Only interactive CLI prompts: Rejected as tedious for many artifacts
- Only manual: Rejected as high friction for first-time users

### 7. Delta Comparison Workflow

**Decision:** `abc delta` compares all artifacts in beacon.yaml by default; `abc delta <file>` shows detailed diff for specific file.

**Rationale:**
- Summary view helps identify what changed across entire project
- Detailed view shows actual line-by-line changes for review
- beacon.yaml-aware: only compares artifacts project actually uses
- Enables contribution workflow: review local changes before pushing to warehouse

**Summary View (No Arguments):**
```bash
$ abc delta
🔍 Checking artifacts defined in beacon.yaml...

[Modified] knowledge/languages/python/fastapi-rules.md
[Added]    knowledge/testing/pytest-standards.md
[Missing]  skills/code-review/SKILL.md

Run 'abc delta <file>' to see detailed changes.
```

**Implementation:**
- Read beacon.yaml to get artifact list
- For each artifact: compare hash of local vs warehouse file
- Categorize: [Modified], [Added] (local only), [Missing] (in config but not local)

**Detailed View (With File Argument):**
```bash
$ abc delta knowledge/languages/python/fastapi-rules.md
--- warehouse: ~/org-warehouse/knowledge/languages/python/fastapi-rules.md
+++ local:     .agentic-beacon/artifacts/knowledge/languages/python/fastapi-rules.md
@@ -15,0 +16,3 @@
+ ## New Guardrail
+ Always use Pydantic models for request validation.
```

**Implementation:**
- Use `git diff --no-index <warehouse-path> <local-path>` for specific file
- No custom diff algorithm needed (leverage existing tools)

**Alternatives Considered:**
- Always show full diff: Rejected as overwhelming for many files
- Build custom diff algorithm: Rejected as unnecessary complexity
- No summary view: Rejected as users need overview of all changes

### 8. Command Rename Strategy

**Decision:** Direct breaking change - `abc init` becomes `abc warehouse init` with no transition period.

**Rationale:**
- Framework is early stage with limited adoption
- Clean break is clearer than deprecation period
- Version bump to 2.0.0 signals breaking change clearly

**Migration Support:**
- Update all documentation and examples in the repository
- Include migration note in CHANGELOG.md
- Update error message if users try `abc init` (suggest `abc warehouse init`)

**Alternatives Considered:**
- Keep `abc init` as alias: Rejected due to maintenance burden
- Add deprecation warning: Rejected as unnecessary for early-stage tool

## Impacted Modules & Systems

**Repository Branch Strategy:**
- Repository to be modified: `agentic-beacon`
- Feature branch name: `config-based-artifact-management`
- Base branch: `main`
- Note: Create feature branch before implementation using `git checkout -b config-based-artifact-management`

**Code Changes:**
- `libs/beacon/src/beacon/cli.py` - Add warehouse command group, implement connect/setup/sync/delta commands, move init to warehouse subcommand
- `libs/beacon/src/beacon/core/warehouse.py` - Add WarehouseValidator class, warehouse structure validation logic
- `libs/beacon/src/beacon/core/config.py` - Add beacon.yaml and config.toml parsers/writers, configuration management
- `libs/beacon/src/beacon/core/sync.py` - New module: SyncEngine class for snapshot-based artifact copying with glob support
- `libs/beacon/src/beacon/core/delta.py` - New module: DeltaComparator class for hash-based comparison and git diff integration
- `libs/beacon/src/beacon/initializer.py` - Update references if init logic needs changes for warehouse subcommand

**Configuration Changes:**
- `.agentic-beacon/config.toml` (gitignored) - New project-level warehouse connection config
- `.agentic-beacon/beacon.yaml` (committed) - New project-level artifact dependency declaration
- `.gitignore` - Automatic updates to exclude config.toml and artifacts/

**Documentation Changes:**
- `README.md` - Update all `abc init` references to `abc warehouse init`, add beacon.yaml examples
- `docs/local-warehouse-workflow.md` - Already created with workflow guide
- `docs/specs-vs-artifacts.md` - Already created with conceptual distinction
- `docs/beacon-config-guide.md` - To be created during implementation with beacon.yaml specification
- `CHANGELOG.md` - Breaking change notice for v2.0.0

**Example/Sample Changes:**
- `examples/sample-warehouse/skills/project-setup/` - New skill for agent-assisted setup with catalog generation
- `examples/sample-warehouse/` - Verify structure is valid for connection
- Example beacon.yaml files for different project types (Python, TypeScript, data platform)

## Risks / Trade-offs

**[Risk] Users with scripts using `abc init` will break**
→ **Mitigation:** Clear communication in release notes, version bump to 2.0.0, helpful error message suggesting new command

**[Risk] Local warehouse path becomes invalid (moved/deleted)**
→ **Mitigation:** Validate path when running `abc sync`, show clear error with suggestion to reconnect

**[Risk] Local warehouse becomes out of sync with remote**
→ **Mitigation:** Document that users manage sync via git pull, no automatic staleness detection

**[Risk] Users don't understand snapshot model**
→ **Mitigation:** Clear documentation comparing to node_modules, emphasize that changes require explicit `abc sync`

**[Risk] beacon.yaml gets out of sync with actual artifacts**
→ **Mitigation:** `abc sync` removes artifacts no longer in config (with --prune flag), `abc delta` shows discrepancies

**[Risk] Glob patterns too complex for users**
→ **Mitigation:** Provide examples in documentation, support both specific files and globs, validate patterns during sync

**[Risk] Agent-assisted setup skill is complex to build**
→ **Mitigation:** Keep skill simple (just generate catalog), let user's agent do the heavy lifting

**[Trade-off] Config-based approach requires more setup than "copy everything"**
→ **Resolution:** Accept trade-off for benefits of precision and reproducibility; three setup workflows ease adoption

**[Trade-off] Snapshot model means projects can drift from warehouse**
→ **Resolution:** This is intended - enables safe experimentation; `abc delta` facilitates contribution workflow

**[Trade-off] Split config files (config.toml vs beacon.yaml) adds complexity**
→ **Resolution:** Necessary for gitignore model; mirrors industry patterns (like .vscode/settings.json being optional to commit)

## Migration Plan

**Pre-release:**
1. Update all internal examples and documentation to use `abc warehouse init`
2. Update `examples/sample-warehouse/` generation scripts
3. Implement "project-setup" skill for agent-assisted beacon.yaml population
4. Test three setup workflows (agent-assisted, copy, manual) on multiple platforms
5. Create comprehensive documentation on config-based artifact management

**Release (2.0.0):**
1. Publish with clear breaking change notice in CHANGELOG
2. Update GitHub README with package manager analogy (node_modules pattern)
3. Add migration guide showing how to adopt beacon.yaml
4. Document snapshot-based sync model and delta contribution workflow
5. Reference docs/local-warehouse-workflow.md for detailed workflow guide

**Documentation Requirements:**
- Explain config-based artifact management (beacon.yaml as "shopping list")
- Document snapshot-based pure copy model (not symlinks)
- Show all three setup workflows with examples
- Explain `abc sync` declarative behavior
- Document `abc delta` for reviewing local changes and contributing upstream
- Clarify split config model (config.toml gitignored, beacon.yaml committed)
- Provide node_modules/package.json analogy throughout
- Show complete example workflow from warehouse clone to contribution

**Post-release:**
1. Monitor user feedback on config-based approach and setup workflows
2. Consider adding `abc add <artifact>` helper to update beacon.yaml
3. Evaluate `abc warehouse status` to show connection and artifact sync state
4. Consider `abc sync --check` to validate without copying (like npm ci vs npm install)

## Open Questions

None - all design decisions have been made.
