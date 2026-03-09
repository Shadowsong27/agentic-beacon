# Project Setup Skill

**description:** Help configure beacon.yaml by analyzing project files and warehouse catalog

## Purpose

This skill guides an AI agent through the process of setting up a project's `beacon.yaml`
configuration by analyzing the project's technology stack and matching it against available
warehouse artifacts.

## Instructions

When invoked, follow these steps:

### Step 1: Read the Warehouse Catalog

Read the file `.agentic-beacon/warehouse-catalog.md` in the project root.
This file contains a complete listing of all available artifacts in the connected warehouse,
organized by type (knowledge, skills, contexts).

### Step 2: Analyze the Project

Examine the project to understand its technology stack:

- **Language detection**: Look for `package.json` (JavaScript/TypeScript), `requirements.txt` or
  `pyproject.toml` (Python), `go.mod` (Go), `Cargo.toml` (Rust), `pom.xml` (Java)
- **Framework detection**: Look for framework-specific config files (`next.config.js`, `django`,
  `fastapi`, `express`, etc.)
- **Infrastructure**: Look for `Dockerfile`, `docker-compose.yml`, `terraform/`, `.github/workflows/`
- **Domain**: Examine directory structure and README for project domain context

### Step 3: Match Artifacts

Based on the project analysis and warehouse catalog:

1. **Knowledge**: Select language-specific knowledge (e.g., `languages/python/**/*.md` for Python
   projects), infrastructure knowledge, and domain-specific knowledge
2. **Skills**: Select relevant skills (code review, testing, deployment, etc.)
3. **Contexts**: Select the global context (`AGENTS.global.md`) and any team/domain contexts

### Step 4: Populate beacon.yaml

Edit `.agentic-beacon/beacon.yaml` to include the matched artifacts:

```yaml
artifacts:
  knowledge:
    - languages/python/**/*.md           # For Python projects
    - infrastructure/docker-standards.md  # If Docker is used
  skills:
    - code-review/SKILL.md               # For code review workflow
  contexts:
    - AGENTS.global.md                    # Always include global context
```

### Step 5: Verify

After populating, instruct the user to run:

```bash
abc sync
```

This will download the selected artifacts from the warehouse.

## Selection Guidelines

- **Always include** `AGENTS.global.md` in contexts
- **Match languages** to the project's primary and secondary languages
- **Match frameworks** to specific framework knowledge if available
- **Include global knowledge** like `knowledge/global/**/*.md` for organization-wide decisions
- **Prefer glob patterns** over individual files when a whole directory is relevant
- **Be conservative** - only include artifacts that are clearly relevant to the project
