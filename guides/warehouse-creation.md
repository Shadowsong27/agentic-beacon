# Creating a Warehouse

This guide walks you through creating and organizing a warehouse for your team or organization.

## What is a Warehouse?

A warehouse is a structured repository containing:
- **Knowledge artifacts** - Documentation, best practices, standards
- **Skills** - Reusable agent workflows and capabilities
- **Contexts** - Team and project-specific configurations

Think of it as your organization's knowledge base for AI agents.

## Quick Start

```bash
# Create new warehouse
abc warehouse init my-warehouse

# Navigate to it
cd my-warehouse
```

## Warehouse Structure

The `abc warehouse init` command creates this structure:

```
my-warehouse/
├── contexts/           # Agent configurations
│   ├── AGENTS.global.md
│   └── README.md
├── knowledge/          # Documentation and guides
│   ├── global/
│   │   └── README.md
│   └── README.md
├── skills/             # Reusable agent workflows
│   └── README.md
├── docs/              # Warehouse documentation
│   └── README.md
├── README.md          # Warehouse overview
└── .git/              # Version control (optional)
```

### Required Structure

For a valid warehouse, you **must** have:
- ✅ `contexts/` directory
- ✅ `knowledge/` directory  
- ✅ `knowledge/global/` directory
- ✅ `skills/` directory
- ✅ `docs/` directory
- ✅ `contexts/AGENTS.global.md` file
- ✅ `README.md` file

## Organizing Knowledge

### By Language

```
knowledge/
├── languages/
│   ├── python/
│   │   ├── type-hints.md
│   │   ├── async-patterns.md
│   │   ├── fastapi/
│   │   │   ├── routing.md
│   │   │   └── dependencies.md
│   │   └── pytest/
│   │       └── fixtures.md
│   ├── typescript/
│   │   ├── types.md
│   │   └── react/
│   │       └── hooks.md
│   └── go/
│       └── concurrency.md
```

### By Domain

```
knowledge/
├── infrastructure/
│   ├── docker-best-practices.md
│   ├── kubernetes/
│   │   └── deployment-patterns.md
│   └── terraform/
│       └── modules.md
├── databases/
│   ├── postgres-tuning.md
│   └── redis-patterns.md
└── security/
    ├── auth-patterns.md
    └── secrets-management.md
```

### By Best Practice

```
knowledge/
├── best-practices/
│   ├── code-review.md
│   ├── tdd-workflow.md
│   ├── api-design.md
│   ├── error-handling.md
│   └── logging-standards.md
```

## Organizing Skills

Skills are agent workflows stored as directories:

```
skills/
├── code-review/
│   ├── SKILL.md              # Main skill definition
│   ├── checklist.md          # Review checklist
│   └── examples.md           # Example reviews
├── generate-unit-tests/
│   ├── SKILL.md
│   └── templates/
│       ├── pytest-template.md
│       └── unittest-template.md
└── api-design/
    ├── SKILL.md
    └── rest-api-checklist.md
```

**SKILL.md format:**
```markdown
# Skill: Code Review

## Purpose
Perform thorough code reviews following team standards.

## When to Use
When reviewing pull requests or code changes.

## Process
1. Check code formatting and style
2. Review logic and algorithms
3. Verify tests are present
4. Check for security issues
5. Provide constructive feedback

## Checklist
- [ ] Code follows style guide
- [ ] Tests included and passing
- [ ] No security vulnerabilities
- [ ] Documentation updated
- [ ] Performance considerations addressed
```

## Organizing Contexts

Contexts provide team and project-specific configurations:

```
contexts/
├── AGENTS.global.md           # Organization-wide defaults
├── teams/
│   ├── backend/
│   │   └── AGENTS.md         # Backend team standards
│   ├── frontend/
│   │   └── AGENTS.md         # Frontend team standards
│   └── platform/
│       └── AGENTS.md         # Platform team standards
└── projects/
    ├── customer-portal/
    │   └── AGENTS.md         # Project-specific context
    └── api-gateway/
        └── AGENTS.md
```

**AGENTS.md format:**
```markdown
# Backend Team - Agent Context

## Team Information
- **Team:** Backend Engineering
- **Tech Stack:** Python, FastAPI, PostgreSQL
- **Practices:** TDD, Code Review, CI/CD

## Coding Standards
- Use type hints for all functions
- Follow PEP 8 style guide
- 100% test coverage for business logic
- Document all public APIs

## Development Workflow
1. Create feature branch
2. Write tests first (TDD)
3. Implement feature
4. Create PR with description
5. Address review feedback
6. Merge after approval

## Tools
- **Testing:** pytest
- **Linting:** ruff, mypy
- **Formatting:** black
- **CI/CD:** GitHub Actions
```

## Example: Python Team Warehouse

Let's build a complete Python-focused warehouse:

### Step 1: Create Structure

```bash
abc warehouse init python-team-warehouse
cd python-team-warehouse
```

### Step 2: Add Python Knowledge

```bash
# Create language-specific knowledge
mkdir -p knowledge/languages/python/{basics,frameworks,testing,tools}

# Basics
cat > knowledge/languages/python/basics/type-hints.md << 'EOF'
# Python Type Hints

## Purpose
Type hints improve code quality and IDE support.

## Basic Usage
```python
def greet(name: str) -> str:
    return f"Hello, {name}"
```

## Best Practices
- Always use type hints for function signatures
- Use Optional for nullable values
- Use Union for multiple types
- Import from `typing` module
EOF

# Frameworks
cat > knowledge/languages/python/frameworks/fastapi.md << 'EOF'
# FastAPI Best Practices

## Routing
- Use APIRouter for modular routes
- Group related endpoints
- Use path parameters for IDs

## Example
```python
from fastapi import APIRouter

router = APIRouter(prefix="/users")

@router.get("/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id}
```
EOF

# Testing
cat > knowledge/languages/python/testing/pytest-fixtures.md << 'EOF'
# Pytest Fixtures

## Purpose
Fixtures provide reusable test setup.

## Example
```python
import pytest

@pytest.fixture
def db_session():
    session = create_session()
    yield session
    session.close()

def test_user_creation(db_session):
    user = User(name="Alice")
    db_session.add(user)
    db_session.commit()
    assert user.id is not None
```
EOF
```

### Step 3: Add Skills

```bash
mkdir -p skills/python/{code-review,test-generation,api-design}

cat > skills/python/code-review/SKILL.md << 'EOF'
# Skill: Python Code Review

## Purpose
Review Python code for quality, correctness, and best practices.

## Checklist
- [ ] Type hints present for all functions
- [ ] Following PEP 8 style guide
- [ ] Tests included (pytest)
- [ ] Docstrings for public functions
- [ ] No security vulnerabilities
- [ ] Async patterns used correctly
- [ ] Error handling appropriate
- [ ] Performance considerations

## Common Issues
1. Missing type hints
2. Bare except clauses
3. Mutable default arguments
4. Missing async/await
5. SQL injection vulnerabilities
EOF

cat > skills/python/test-generation/SKILL.md << 'EOF'
# Skill: Generate Python Unit Tests

## Purpose
Generate comprehensive unit tests using pytest.

## Process
1. Identify function to test
2. Determine edge cases
3. Create pytest test cases
4. Use fixtures for setup
5. Assert expected behavior

## Template
```python
import pytest

def test_function_name_happy_path():
    # Arrange
    input_data = ...
    
    # Act
    result = function_name(input_data)
    
    # Assert
    assert result == expected
```
EOF
```

### Step 4: Add Team Context

```bash
mkdir -p contexts/teams/backend

cat > contexts/teams/backend/AGENTS.md << 'EOF'
# Backend Team - Agent Context

## Tech Stack
- Python 3.11+
- FastAPI
- PostgreSQL
- Redis
- Docker

## Standards
- Type hints mandatory
- 100% test coverage for business logic
- Async/await for I/O operations
- Pydantic models for validation
- SQLAlchemy for ORM

## Workflow
1. TDD - Tests first
2. PR review required
3. CI must pass
4. Deploy via CD pipeline
EOF
```

### Step 5: Create Example Configurations

```bash
mkdir -p examples

cat > examples/beacon.yaml.api-service << 'EOF'
# Example beacon.yaml for Python API services

artifacts:
  knowledge:
    - languages/python/basics/type-hints.md
    - languages/python/frameworks/fastapi.md
    - languages/python/testing/pytest-fixtures.md
  
  skills:
    - python/code-review
    - python/test-generation
  
  contexts:
    - teams/backend/AGENTS.md
EOF

cat > examples/beacon.yaml.data-pipeline << 'EOF'
# Example beacon.yaml for data pipelines

artifacts:
  knowledge:
    - languages/python/basics/type-hints.md
    - languages/python/libraries/pandas.md
    - languages/python/testing/pytest-fixtures.md
  
  skills:
    - python/code-review
    - data/pipeline-testing
  
  contexts:
    - teams/data-platform/AGENTS.md
EOF
```

### Step 6: Document the Warehouse

```bash
cat > README.md << 'EOF'
# Python Team Warehouse

Shared knowledge, skills, and contexts for the Python engineering team.

## Contents

- **Knowledge:** Python best practices, framework guides, testing patterns
- **Skills:** Code review, test generation, API design
- **Contexts:** Team standards and workflows

## Usage

1. Connect to warehouse:
   ```bash
   abc warehouse connect --path /path/to/python-team-warehouse
   ```

2. Create beacon.yaml for your project type:
   - API Service: `examples/beacon.yaml.api-service`
   - Data Pipeline: `examples/beacon.yaml.data-pipeline`

3. Sync artifacts:
   ```bash
   abc sync
   ```

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for how to add new artifacts.

## Maintenance

- **Owner:** Python Guild
- **Last Updated:** 2026-03-09
- **Version:** 1.0.0
EOF
```

### Step 7: Version Control

```bash
git init
git add .
git commit -m "Initial Python team warehouse"
git remote add origin git@github.com:yourorg/python-team-warehouse.git
git push -u origin main
```

## Warehouse Validation

Validate your warehouse structure:

```bash
abc warehouse connect --path ./python-team-warehouse
```

Should output:
```
✓ Warehouse structure validated
✓ Connected to warehouse
```

If validation fails, check:
- All required directories exist
- `contexts/AGENTS.global.md` present
- `README.md` at root

## Maintenance Best Practices

### 1. Regular Updates

- **Weekly:** Review and merge PRs
- **Monthly:** Prune outdated content
- **Quarterly:** Major version releases

### 2. Ownership

Assign owners to sections:
```
knowledge/languages/python/  → Python Guild
knowledge/infrastructure/    → Platform Team
contexts/teams/backend/      → Backend Lead
```

### 3. Documentation

Every artifact should have:
- Clear title and purpose
- Code examples
- Last updated date
- Links to related content

### 4. Testing

Test artifacts with real projects before merging:
1. Create test beacon.yaml
2. Sync to test project
3. Verify with AI agent
4. Merge if working

### 5. Versioning

Use git tags for versions:
```bash
git tag -a v1.0.0 -m "First stable release"
git push --tags
```

## Common Patterns

### Multi-Language Warehouse

```
knowledge/
├── languages/
│   ├── python/
│   ├── typescript/
│   ├── go/
│   └── rust/
├── infrastructure/
└── best-practices/
```

### Domain-Specific Warehouse

```
knowledge/
├── data-engineering/
│   ├── airflow/
│   ├── spark/
│   └── dbt/
├── ml-engineering/
│   ├── pytorch/
│   ├── transformers/
│   └── mlflow/
└── platform-engineering/
    ├── kubernetes/
    └── terraform/
```

### Monorepo Organization Warehouse

```
knowledge/
├── shared/              # Shared across all teams
├── services/
│   ├── api-gateway/
│   ├── auth-service/
│   └── user-service/
└── libraries/
    ├── common-utils/
    └── logging-lib/
```

## Troubleshooting

### Warehouse validation fails

**Check required structure:**
```bash
tree -L 2 my-warehouse
```

Must have all required directories and files.

### Team can't connect

**Ensure consistent location:**
```bash
# Document in team README
git clone git@github.com:org/warehouse.git ~/team-warehouse
```

### Artifacts not syncing

**Check warehouse path:**
```bash
cat .agentic-beacon/config.toml
```

Path must be valid and accessible.

## Next Steps

- **[Team Collaboration](./team-collaboration.md)** - Share warehouse with team
- **[Warehouse Contribution](./warehouse-contribution-guide.md)** - Add new content
- **[Advanced Organization](./advanced-warehouse-patterns.md)** - Complex structures

---

**Related Guides:**
- [Getting Started](./getting-started.md)
- [Python Project Setup](./python-project-setup.md)
- [Team Collaboration](./team-collaboration.md)
