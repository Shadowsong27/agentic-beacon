# AGENTS.md Architecture: Three-Tier Context Model

A guide to understanding when and how to use AGENTS.md files at different organizational levels.

**Last Updated:** 2026-03-10

---

## Overview

AGENTS.md files serve as **boot context** - the knowledge agents see immediately on session start. This guide clarifies the three-tier architecture and helps you decide what content belongs at each level.

---

## The Three-Tier Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Warehouse Level (Global + Optional Contexts)           │
│  Purpose: Shared organizational knowledge                │
│  Audience: All projects across organization              │
│  Distribution: Via CLI from central warehouse            │
└─────────────────────────────────────────────────────────┘
                          ↓
                ┌─────────────────────┐
                │  User Level         │
                │  Purpose: Personal  │
                │  Audience: You      │
                │  Location: ~/.config/opencode/AGENTS.md │
                └─────────────────────┘
                          ↓
                ┌─────────────────────┐
                │  Project Level      │
                │  Purpose: Project-specific │
                │  Audience: This codebase   │
                 │  Location: <project>/AGENTS.md │
                 └─────────────────────┘
```

---

## Tier 1: Warehouse Level (Shared Organizational Knowledge)

**Location:** Central warehouse repository → Distributed to `.agentic-beacon/artifacts/` in each project

**Components:**
- `global.md` (required for all projects)
- Language-specific files (optional: e.g. `python.md`, `typescript.md`, `java.md`)
- Domain-specific files (optional: e.g. `data-platform.md`, `web-app.md`, `ml-ai.md`)

### What Goes Here:

#### Global Context (`global.md`)
- **Technical standards** applicable to all projects
  - Commit conventions (Conventional Commits)
  - Git workflow patterns
  - Code review standards
  - Documentation requirements

- **Universal coding patterns**
  - Session handoff patterns
  - Error handling conventions
  - Logging standards

- **Organizational policies**
  - Security requirements
  - Compliance guidelines
  - Tool usage policies

**Example:**
```markdown
# In global.md
## Commit Conventions

**Rule:** Use Conventional Commits format for all commits.

**Format:** `<type>(<scope>): <description>`

**Read:** [Conventional commits guide](.agentic-beacon/artifacts/knowledge/global/decisions/conventional-commits.md)
```

#### Language Contexts (`python.md`, etc.)
- **Language-specific technical standards**
  - Type annotation rules
  - Import patterns
  - Naming conventions
  - Language idioms and best practices

- **Common language pitfalls**
  - Agent failure modes specific to this language
  - Performance anti-patterns
  - Security considerations

**Example:**
```markdown
# In python.md
## Type Annotations

**Rule:** Use primitive types when available (`list` not `List`).

**Rule:** Only quote types for forward references or circular imports.

**Read:** [Type annotation patterns](.agentic-beacon/artifacts/knowledge/languages/python/lessons/quoted-type-annotations.md)
```

#### Domain Contexts (`data-platform.md`, etc.)
- **Domain-specific patterns**
  - Technology stack standards (e.g., PostgreSQL over SQLite)
  - Architectural patterns (e.g., microservices, event-driven)
  - Infrastructure patterns (e.g., containerization, CI/CD)

- **Tool-specific conventions**
  - Airflow DAG patterns
  - API design standards
  - Database schema conventions

**Example:**
```markdown
# In data-platform.md
## Airflow Development

**Rule:** Use two-workflow approach (venv for parsing, Docker for execution).

**Rationale:** [See decision doc](.agentic-beacon/artifacts/knowledge/domains/data-platform/decisions/two-workflow-approach.md)

**Troubleshooting:** [Debugging checklist](.agentic-beacon/artifacts/knowledge/domains/data-platform/lessons/airflow-debugging-checklist.md)
```

### What Does NOT Go Here:

❌ **Personal preferences** - "I prefer verbose logging"
❌ **Project-specific architecture** - "Our user service connects to auth service via gRPC"
❌ **Local machine paths** - "My projects are in ~/Code"
❌ **Experimental patterns** - "Testing a new approach to error handling"

### Distribution:

Warehouse contexts are distributed via CLI:
```bash
# Connect to your warehouse and declare which contexts to use
abc warehouse connect --path ~/your-warehouse
abc setup --manual
# Edit .agentic-beacon/beacon.yaml to list contexts/skills/knowledge
abc sync

# Result: Artifacts copied to .agentic-beacon/artifacts/
# - contexts/global.md (always)
# - contexts/python.md (if declared)
# - contexts/data-platform.md (if declared)
```

---

## Tier 2: User Level (Personal Behavioral Preferences)

**Location:** `~/.config/opencode/AGENTS.md`

**Purpose:** Personal preferences and behavioral instructions for how agents interact with YOU specifically.

### What Goes Here:

#### Personal Behavioral Preferences
How you want agents to work with you across all projects:

**Communication style:**
- "Always show me git diffs before committing"
- "Use verbose logging during development"
- "Explain your reasoning before making architectural changes"

**Workflow preferences:**
- "Create detailed todo lists for multi-step tasks"
- "Ask before running destructive commands"
- "Provide progress updates for long-running operations"

**Tool preferences:**
- "Use pytest for all Python testing"
- "Prefer ripgrep over grep for searching"
- "Always run type checking before committing"

#### Local Environment Specifics
Machine-specific configuration:

- Local tool paths: `export MY_TOOL_PATH=/opt/custom/bin`
- Development environment setup
- Personal shortcuts and aliases

#### Experimental Overrides (Short-term)
Testing patterns before promoting to warehouse:

**Workflow:**
1. Discover new pattern → Add to user-level AGENTS.md
2. Test across multiple projects
3. Validate effectiveness
4. **Promote to warehouse** via pull request
5. Remove from user-level (now redundant with warehouse)

**Example:**
```markdown
# Testing new error handling pattern (temporary)
## Experimental: Structured Error Returns

**Status:** Testing across projects before warehouse PR

**Pattern:** Return Result[T, E] types instead of raising exceptions

**Rationale:** Improves error handling visibility and reduces try-catch blocks

**TODO:** After validation, PR to warehouse python.md
```

### What Does NOT Go Here:

❌ **Coding standards** - Belongs in warehouse (global/language/domain contexts)
❌ **Project-specific knowledge** - Belongs in project-level AGENTS.md
❌ **Team conventions** - Belongs in warehouse (so whole team benefits)
❌ **Long-term validated patterns** - Promote to warehouse immediately

### Key Principle:

**User-level AGENTS.md should be intentionally minimal.**

If you find yourself keeping technical standards here long-term, that's a sign they should be promoted to the warehouse where:
- The whole team benefits
- Updates propagate to all projects
- Standards are versioned and reviewed

### Example User-Level AGENTS.md:

```markdown
# Personal Agent Preferences

## Communication Style

- Always show me git diffs before committing
- Explain reasoning for architectural decisions
- Provide progress updates for tasks taking >30 seconds

## Development Workflow

- Create detailed todo lists for tasks with 3+ steps
- Run type checking and tests before committing
- Ask before running destructive operations (rm, force push)

## Local Environment

**Python:** Use system Python 3.11 at /opt/homebrew/bin/python3.11
**Editor:** VS Code with Ruff extension

## Experimental Patterns (Remove after validation)

### Testing: Result[T, E] Pattern (2026-03-07)
- Return structured results instead of exceptions
- Status: Testing in 3 projects
- Next: PR to warehouse if effective after 2 weeks
```

---

## Tier 3: Project Level (Project-Specific Knowledge)

**Location:** `<project-root>/AGENTS.md`

**Purpose:** Knowledge specific to THIS codebase that doesn't apply elsewhere.

### What Goes Here:

#### Project Architecture
- Service topology and communication patterns
- Module organization and dependencies
- Database schema overview
- API endpoint patterns

**Example:**
```markdown
## Architecture Overview

**Service Map:** See `docs/architecture/service-map.md`

**Communication:**
- User Service ↔ Auth Service: gRPC
- Frontend ↔ API Gateway: REST + WebSocket
- Services ↔ Database: PostgreSQL via SQLAlchemy

**Module Structure:**
- `src/services/` - Business logic services
- `src/models/` - Database models (SQLAlchemy)
- `src/api/` - API endpoints (FastAPI)
```

#### Project-Specific Patterns
- Custom abstractions unique to this project
- Project-specific naming conventions
- Special testing requirements

**Example:**
```markdown
## Testing Requirements

**E2E Tests:** Must use `dot_e2e_test` database (NOT production schemas)

**Cleanup:** All tests must clean up resources in teardown

**Mocking:** Avoid mocking internal business logic - mock external APIs only
```

#### Troubleshooting Guides
- Common issues specific to this codebase
- Debugging workflows for this project
- Known quirks and workarounds

**Example:**
```markdown
## Troubleshooting

### DAG Parsing Failures

1. Check `.env` file exists: `ls .env`
2. Verify Airflow home: `echo $AIRFLOW_HOME`
3. Check database connection: `psql $DATABASE_URL -c "SELECT 1;"`

**Full checklist:** `docs/troubleshooting/airflow-debugging.md`
```

#### Module Documentation
- Key modules and their purposes
- Complex algorithms or business logic explanations
- Integration points with external systems

**Example:**
```markdown
## Key Modules

**Pipeline Generator** (`src/pipeline_generator/`)
- Entry point: `PipelineGenerator.generate()`
- Converts YAML configs into Airflow DAGs
- See `docs/pipeline-generator.md` for architecture

**Metadata Parser** (`src/metadata/`)
- Parses Unity Catalog metadata
- Resolves table dependencies
- Used by: Pipeline Generator, Lineage Tracker
```

### What Does NOT Go Here:

❌ **Language standards** - Belongs in warehouse (`python.md`)
❌ **Personal preferences** - Belongs in user-level AGENTS.md
❌ **Organizational policies** - Belongs in warehouse (`global.md`)
❌ **Generic patterns** - If it applies to multiple projects, promote to warehouse

### Example Project-Level AGENTS.md:

```markdown
# Project: Data Pipeline Orchestrator

## Architecture

**Service Type:** Airflow-based data pipeline generator

**Key Components:**
- Pipeline Generator: Converts YAML → Airflow DAGs
- Metadata Parser: Unity Catalog integration
- Config Manager: Database-backed configuration

**See:** `docs/architecture.md` for detailed service map

## Development Workflow

**Local Development:**
1. Use venv workflow for DAG parsing/testing: `./scripts/test-dag-parsing.sh`
2. Use Docker workflow for full execution: `docker-compose up`

**Testing:**
- All E2E tests use `dot_e2e_test` database
- Clean database before each test run: `./scripts/clean-test-db.sh`

## Key Modules

**PipelineGenerator** (`src/pipeline_generator/generator.py`)
- Main entry point: `generate(workspace: str, pipeline_name: str)`
- Loads config from database
- Generates Airflow DAG files

**MetadataResolver** (`src/metadata/resolver.py`)
- Resolves Unity Catalog table metadata
- Handles catalog/schema/table hierarchy
- Used by: PipelineGenerator, LineageTracker

## Troubleshooting

### DAG Parsing Fails

**Quick checks:**
- Environment loaded: `source .env && echo $AIRFLOW_HOME`
- Database accessible: `psql $DATABASE_URL -c "\dt"`
- Config exists: `SELECT * FROM pipeline_configs WHERE workspace='your_workspace';`

**Full guide:** `docs/troubleshooting/dag-parsing.md`

### Docker Build Fails

**Common cause:** Missing Airflow provider packages

**Fix:** Add to `requirements.txt` and rebuild:
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up
```
```

---

## Decision Framework: What Goes Where?

Use this decision tree to determine the appropriate level for any knowledge:

```
Is this knowledge UNIVERSAL across all projects?
├─ YES → Warehouse: global.md
└─ NO ↓

Is this a LANGUAGE-SPECIFIC standard?
├─ YES → Warehouse: language context file (e.g. python.md, typescript.md)
└─ NO ↓

Is this a DOMAIN-SPECIFIC pattern used by multiple projects?
├─ YES → Warehouse: domain context file (e.g. data-platform.md, web-app.md)
└─ NO ↓

Is this a PERSONAL PREFERENCE for how agents work with you?
├─ YES → User Level: ~/.config/opencode/AGENTS.md
└─ NO ↓

Is this SPECIFIC TO THIS CODEBASE?
├─ YES → Project Level: <project>/AGENTS.md
└─ NO → Consider if it needs to be documented at all
```

### Quick Reference Table

| Type of Knowledge | Warehouse Global | Warehouse Language | Warehouse Domain | User Level | Project Level |
|-------------------|------------------|-------------------|------------------|------------|---------------|
| Commit conventions | ✅ | ❌ | ❌ | ❌ | ❌ |
| Type annotation rules | ❌ | ✅ | ❌ | ❌ | ❌ |
| Airflow patterns | ❌ | ❌ | ✅ | ❌ | ❌ |
| "Show me diffs before commit" | ❌ | ❌ | ❌ | ✅ | ❌ |
| "Use verbose logging" | ❌ | ❌ | ❌ | ✅ | ❌ |
| Experimental pattern (testing) | ❌ | ❌ | ❌ | ✅ (temporary) | ❌ |
| Service architecture | ❌ | ❌ | ❌ | ❌ | ✅ |
| Module documentation | ❌ | ❌ | ❌ | ❌ | ✅ |
| Project-specific troubleshooting | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## Common Anti-Patterns

### ❌ Anti-Pattern 1: Duplicating Warehouse Content in User/Project Levels

**Problem:**
```markdown
# In user-level AGENTS.md
## Python Type Annotations
Use primitive types when available (list not List).
Only quote for forward references.
```

**Why it's wrong:** This is a technical standard that belongs in warehouse `python.md`. Duplicating it means:
- Updates don't propagate automatically
- Maintenance burden increases
- Standards diverge across projects

**Solution:** Remove from user/project level, ensure it's in warehouse.

---

### ❌ Anti-Pattern 2: Personal Preferences in Warehouse

**Problem:**
```markdown
# In global.md (warehouse)
## Agent Behavior
Always show me detailed progress updates for tasks taking >10 seconds.
Use verbose logging by default.
```

**Why it's wrong:** These are behavioral preferences, not technical standards. Different developers have different preferences.

**Solution:** Move to user-level AGENTS.md where each developer can customize.

---

### ❌ Anti-Pattern 3: Project-Specific Knowledge in Warehouse

**Problem:**
```markdown
# In data-platform.md (warehouse)
## Service Architecture
Our user service communicates with auth service via gRPC on port 50051.
Database connection pooling uses max 20 connections.
```

**Why it's wrong:** This is specific to ONE project, not all data platform projects.

**Solution:** Move to project-level AGENTS.md.

---

### ❌ Anti-Pattern 4: Long-term Experimental Patterns at User Level

**Problem:**
```markdown
# In user-level AGENTS.md (added 6 months ago)
## Experimental: Result Type Pattern
Testing structured error returns...
```

**Why it's wrong:** After 6 months, it's no longer experimental. Either:
- It works → Promote to warehouse
- It doesn't work → Delete it

**Solution:** Establish a policy: Experimental patterns have a 2-week validation period, then promote or remove.

---

## Workflow: From Discovery to Standardization

### Typical Lifecycle of a Pattern

**Week 1: Discovery**
```markdown
# User-level AGENTS.md
## Experimental: JSON Schema Validation Pattern
Testing automatic validation of API payloads using JSON Schema.
Status: Added 2026-03-07, testing in project-alpha
```

**Week 2-3: Validation**
- Test in multiple projects
- Refine based on real usage
- Document edge cases and benefits

**Week 4: Promotion**
```bash
# Create PR to warehouse
git checkout -b feature/json-schema-validation-standard
# Move pattern to appropriate warehouse context
# Remove from user-level AGENTS.md (now redundant)
git commit -m "feat: add JSON schema validation standard to Python context"
```

**Post-merge:**
```bash
# Update projects to get new standard
cd project-alpha && abc update
cd project-beta && abc update
```

**Result:** Pattern is now organizational standard, benefits all projects, user-level AGENTS.md stays minimal.

---

## Load Order and Precedence

When an agent starts a session, contexts are loaded in this order:

```
1. Warehouse contexts (.agentic-beacon/artifacts/contexts/)
   ├─ global.md (always loaded)
   ├─ language context file (e.g. python.md, if declared in beacon.yaml)
   └─ domain context file (e.g. data-platform.md, if declared in beacon.yaml)

2. User-level preferences (~/.config/opencode/AGENTS.md)

3. Project-level context (<project>/AGENTS.md)
```

**Precedence:** Later loaded contexts can override earlier ones.

**Example:**
```markdown
# Warehouse global.md
## Logging
Default log level: INFO

# User-level AGENTS.md
## Logging (Override)
Default log level: DEBUG  # I prefer verbose logging
```

**Result:** Agent uses DEBUG log level for this user's projects.

**When to use overrides:**
- Personal preferences (behavioral differences)
- Temporary experimentation (testing new approaches)
- Project-specific exceptions (rare edge cases)

**When NOT to use overrides:**
- Disagreeing with organizational standards (propose change to warehouse instead)
- Project-specific patterns that should be permanent (add to project AGENTS.md, not override)

---

## Summary

### Warehouse Level: Shared Organizational Knowledge
- **Purpose:** Technical standards, coding patterns, best practices
- **Scope:** All projects (global), language-specific, or domain-specific
- **Distribution:** Via CLI from central repository
- **Maintenance:** Team contributes improvements via PRs

### User Level: Personal Behavioral Preferences
- **Purpose:** How agents interact with YOU
- **Scope:** Your personal preferences across all projects
- **Distribution:** Not shared (stays local)
- **Maintenance:** Keep minimal - promote patterns to warehouse

### Project Level: Project-Specific Knowledge
- **Purpose:** Architecture, modules, troubleshooting for THIS codebase
- **Scope:** Single project only
- **Distribution:** Lives in project repository
- **Maintenance:** Project team maintains

**Golden Rule:** If you discover something useful, share it. Promote validated patterns from user-level to warehouse so the whole team benefits.

---

**Related Documentation:**
- [Agentic Warehouse Design](./agentic-warehouse-design.md) - Full architecture details
- [Warehouse Contribution Guide](./warehouse-contribution-guide.md) - How to contribute improvements
- [Getting Started](../../guides/getting-started.md) - Installing and syncing artifacts
