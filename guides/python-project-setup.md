# Python Project Setup with Agentic Beacon

This guide shows how to set up Agentic Beacon for Python projects, with examples and best practices.

## Scenario: Python Backend Microservice

Let's set up artifact management for a FastAPI-based microservice project.

## Initial Setup

```bash
cd my-fastapi-service
abc warehouse connect --path ~/org-warehouse
abc setup --manual
```

## Configure for Python

Edit `.agentic-beacon/beacon.yaml`:

```yaml
artifacts:
  knowledge:
    # Python language fundamentals
    - languages/python/type-hints.md
    - languages/python/async-patterns.md
    - languages/python/error-handling.md
    
    # Python ecosystem
    - languages/python/fastapi/**/*.md
    - languages/python/pydantic/**/*.md
    - languages/python/sqlalchemy/**/*.md
    
    # Testing
    - languages/python/pytest/**/*.md
    - best-practices/tdd-workflow.md
    
    # Infrastructure
    - infrastructure/docker-python.md
    - infrastructure/postgres-best-practices.md
  
  skills:
    - python/generate-unit-tests
    - python/code-review
    - python/api-design
  
  contexts:
    - teams/backend/AGENTS.md
    - projects/microservices/AGENTS.md
```

## Sync Artifacts

```bash
abc sync
```

Expected output:
```
Syncing artifacts from warehouse...

✓ Sync complete
  Copied: 23 files
  Unchanged: 0 files
```

## Verify Structure

```bash
tree .agentic-beacon/artifacts/
```

```
.agentic-beacon/artifacts/
├── knowledge/
│   ├── languages/
│   │   └── python/
│   │       ├── type-hints.md
│   │       ├── async-patterns.md
│   │       ├── error-handling.md
│   │       ├── fastapi/
│   │       │   ├── routing.md
│   │       │   ├── dependencies.md
│   │       │   └── testing.md
│   │       ├── pydantic/
│   │       │   └── models.md
│   │       ├── sqlalchemy/
│   │       │   └── best-practices.md
│   │       └── pytest/
│   │           └── fixtures.md
│   ├── best-practices/
│   │   └── tdd-workflow.md
│   └── infrastructure/
│       ├── docker-python.md
│       └── postgres-best-practices.md
├── skills/
│   └── python/
│       ├── generate-unit-tests/
│       ├── code-review/
│       └── api-design/
└── contexts/
    ├── teams/
    │   └── backend/
    │       └── AGENTS.md
    └── projects/
        └── microservices/
            └── AGENTS.md
```

## Using with Your AI Agent

Your AI agent (Cursor, Copilot, etc.) will now have access to:

1. **Python-specific knowledge** - Type hints, async patterns, FastAPI best practices
2. **Testing guidance** - pytest fixtures, TDD workflow
3. **Team context** - Backend team conventions from `AGENTS.md`
4. **Project-specific skills** - Code review, test generation for Python

## Project-Specific Customization

### Add Project-Specific Knowledge

You can add project-specific knowledge alongside warehouse artifacts:

```bash
mkdir -p .agentic-beacon/local-knowledge
echo "# API Rate Limiting Strategy" > .agentic-beacon/local-knowledge/rate-limiting.md
```

This local knowledge:
- ✅ Should be committed to git
- ✅ Is project-specific
- ✅ Doesn't conflict with synced artifacts

### Selective Artifact Loading

If you only need certain Python features:

```yaml
artifacts:
  knowledge:
    # Only async-related Python knowledge
    - languages/python/async-patterns.md
    - languages/python/asyncio.md
    - languages/python/fastapi/async-routes.md
  
  skills:
    - python/async-code-review
  
  contexts: []
```

## Common Python Patterns

### Pattern 1: Full Stack Python

```yaml
artifacts:
  knowledge:
    - languages/python/**/*.md
    - languages/typescript/**/*.md  # For frontend
    - infrastructure/docker-compose.md
  
  skills:
    - python/backend-review
    - typescript/frontend-review
  
  contexts:
    - teams/fullstack/AGENTS.md
```

### Pattern 2: Data Engineering

```yaml
artifacts:
  knowledge:
    - languages/python/pandas/**/*.md
    - languages/python/pyspark/**/*.md
    - infrastructure/airflow/**/*.md
    - infrastructure/delta-lake.md
  
  skills:
    - data/pipeline-review
    - data/sql-optimization
  
  contexts:
    - teams/data-platform/AGENTS.md
```

### Pattern 3: ML/AI Development

```yaml
artifacts:
  knowledge:
    - languages/python/pytorch/**/*.md
    - languages/python/huggingface/**/*.md
    - ml/training-best-practices.md
    - ml/model-evaluation.md
  
  skills:
    - ml/model-review
    - ml/experiment-tracking
  
  contexts:
    - teams/ml-engineering/AGENTS.md
```

## Updating Dependencies

When new Python best practices are added to the warehouse:

```bash
# Update your beacon.yaml
vim .agentic-beacon/beacon.yaml

# Sync to get new artifacts
abc sync
```

The sync will:
- ✅ Copy new files
- ✅ Update changed files
- ✅ Skip unchanged files (idempotent)
- ✅ Keep local modifications (unless you explicitly want to overwrite)

## Testing Setup

Verify your agent has the right context:

1. **Ask your agent:** "What Python testing framework should I use?"
   - Should reference pytest from your artifacts

2. **Request code review:**
   - Agent should apply patterns from your knowledge artifacts

3. **Generate tests:**
   - If you have the `generate-unit-tests` skill, agent should follow that workflow

## Integration with Development Tools

### VS Code / Cursor

The artifacts are automatically available in the workspace. Your agent will:
- Read `.agentic-beacon/artifacts/` for knowledge
- Apply team conventions from `contexts/`
- Use skills when invoked

### Pre-commit Hooks

Add a pre-commit hook to ensure artifacts are synced:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: sync-beacon-artifacts
        name: Sync Beacon Artifacts
        entry: abc sync
        language: system
        pass_filenames: false
```

### CI/CD Integration

In your CI pipeline:

```yaml
# .github/workflows/ci.yml
- name: Setup Beacon Artifacts
  run: |
    pip install agentic-beacon
    abc warehouse connect --path ./warehouse
    abc sync
```

## Troubleshooting

### Python-specific artifacts not found

**Problem:** Pattern doesn't match expected files.

**Solution:** Check warehouse structure:
```bash
ls ~/org-warehouse/knowledge/languages/python/
```

Adjust your pattern:
```yaml
# Wrong - too specific
- languages/python/fastapi.md

# Right - matches directory structure
- languages/python/fastapi/*.md
```

### Too many artifacts synced

**Problem:** Glob pattern too broad, syncing unnecessary files.

**Solution:** Be more specific:
```yaml
# Before (syncs everything)
- languages/python/**/*.md

# After (syncs only needed directories)
- languages/python/type-hints.md
- languages/python/fastapi/**/*.md
- languages/python/pytest/**/*.md
```

### Conflicts with team standards

**Problem:** Local modifications to team contexts.

**Solution:** Keep team contexts read-only, create local overrides:
```bash
# Don't modify synced contexts
# .agentic-beacon/artifacts/contexts/teams/backend/AGENTS.md

# Create local project-specific context
mkdir -p .agentic-beacon/local-contexts
echo "# Project-specific overrides" > .agentic-beacon/local-contexts/PROJECT.md
```

## Best Practices

1. **Start minimal** - Add artifacts as you need them
2. **Use specific patterns** - Avoid wildcards that sync too much
3. **Separate concerns** - Different beacon.yaml per project type
4. **Document choices** - Comment your beacon.yaml selections
5. **Keep local artifacts separate** - Use `local-knowledge/` for project-specific content

## Example: Complete Python Microservice

```yaml
artifacts:
  # Core Python
  knowledge:
    - languages/python/type-hints.md
    - languages/python/async-patterns.md
    - languages/python/error-handling.md
    
    # Web framework
    - languages/python/fastapi/routing.md
    - languages/python/fastapi/dependencies.md
    - languages/python/fastapi/testing.md
    
    # Data & ORM
    - languages/python/pydantic/validation.md
    - languages/python/sqlalchemy/async-orm.md
    
    # Testing
    - languages/python/pytest/fixtures.md
    - languages/python/pytest/async-tests.md
    - best-practices/tdd-workflow.md
    
    # Infrastructure
    - infrastructure/docker-python.md
    - infrastructure/postgres-best-practices.md
    - infrastructure/redis-patterns.md
  
  # Development skills
  skills:
    - python/generate-unit-tests
    - python/code-review
    - python/api-design
    - python/async-debugging
  
  # Team & project context
  contexts:
    - teams/backend/AGENTS.md
    - projects/microservices/coding-standards.md
```

## Next Steps

- **[Team Collaboration](./team-collaboration.md)** - Share configurations across team
- **[Advanced Patterns](./advanced-patterns.md)** - Complex glob patterns, selective syncing
- **[Creating Skills](./creating-skills.md)** - Build your own Python-specific skills

---

**Related Guides:**
- [Getting Started](./getting-started.md)
- [TypeScript Project Setup](./typescript-project-setup.md)
- [Data Platform Setup](./data-platform-setup.md)
