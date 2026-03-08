# Agentic Beacon Project Context

Project-level instructions for AI agents working on the Agentic Beacon framework.

---

## Project Overview

**Agentic Beacon** is an opinionated framework for standardizing and distributing agentic engineering artifacts across teams.

**Repository Purpose:**
- Framework source code (CLI tool in `libs/beacon/`)
- Design documentation (`docs/`)
- Usage guides (`guides/`)
- Example warehouse (`examples/sample-warehouse/`)

**This is NOT a warehouse** - it's the framework itself. Users create warehouses with `abc init`.

**Read:** [Repository Structure](knowledge/facts/repository-structure.md)

---

## Development Guidelines

### Configuration Management Patterns

**Decision:** Use Pydantic Settings patterns with consistent terminology

- Module name: `settings.py` (not `config.py`)
- Class names: `WarehouseSettings`, `BeaconSettings`, `SettingsReader`, `SettingsWriter`
- Terminology: Use "settings" consistently throughout (not "config" or "configuration")
- Exceptions: Separate into `exceptions.py` module
- Pattern: Pydantic BaseSettings with TOML support
- Custom structures: Manual parsing with Pydantic validation (beacon.yaml)

**Read:**
- [Decision: Settings Module Structure](knowledge/decisions/settings-module-structure.md)
- [Decision: Pydantic Settings Patterns](knowledge/decisions/pydantic-settings-patterns.md)

## Development Guidelines

### Temporary Documentation Pattern

**Rule:** Do NOT commit temporary handoff documentation created during agentic coding sessions.

**Examples:** Session handoff docs, implementation checklists, agent-to-agent context files, one-off decision documents.

**Read:** [Decision: No Temporary Docs in Repository](knowledge/decisions/no-temporary-docs.md)

### Working with the CLI Package

**Location:** `libs/beacon/`

**Quick commands:**
```bash
cd libs/beacon && pip install -e .  # Install editable
abc --version                        # Test CLI
abc init test-warehouse              # Test command
```

**Read:** [CLI Development Workflow](knowledge/facts/cli-development-workflow.md)

### Unit Testing Workflow

**Brief:** Standard workflow for running unit tests: activate venv → uv sync --extra dev → run pytest

**Read:** [Fact: Unit Testing Workflow](knowledge/facts/unit-testing-workflow.md)

**Rule:** ALL tests must be resolved before marking tasks complete - either fixed, removed with justification, or skipped with documented reason.

**Read:** [Lesson: Complete Test Resolution Before Marking Tasks Done](knowledge/lessons/complete-test-resolution.md)

**Rule:** After unit tests pass, verify happy path functionality with real-world usage to ensure the feature actually works.

**Read:** [Lesson: Verify Both Unit Tests and Happy Path Functionality](knowledge/lessons/verify-unit-tests-and-happy-path.md)

### Release Process

**Workflow:** Conventional commits → Release-Please PR → Merge → Create release branch → Auto-publish to PyPI

**Read:** [Release Workflow](knowledge/facts/release-workflow.md)

---

## Project Standards

### Python Standards

Follow the global Python standards from the user's AGENTS.md context:
- Type annotations without quotes (unless forward references)
- Use primitive types (list, dict) over typing module types
- Pydantic BaseModel for data carriers
- Dataclass for service classes only
- Conventional commits for all changes

**Read:** [Decision: Follow Global Python Standards](knowledge/decisions/follow-global-python-standards.md)

### Documentation Standards

- Keep docs current with code changes
- Use examples from `abc init` output
- Link to proper documentation, don't duplicate
- Update both README and package-specific docs when needed

---

## Common Patterns

### Adding a New CLI Command

**Brief:** Add handler in cli.py → Implement logic → Add tests → Update docs → Test thoroughly

**Read:** [Lesson: Adding CLI Command](knowledge/lessons/adding-cli-command.md)

### Updating Warehouse Structure

**Brief:** Update initializer.py → Regenerate examples/sample-warehouse/ → Update docs → Test abc init and setup

**Read:** [Lesson: Updating Warehouse Structure](knowledge/lessons/updating-warehouse-structure.md)

---

## Project Skills

### Recording Knowledge

**Brief:** Use `/record-knowledge` to capture decisions, lessons, and facts into the knowledge base.

**How it works:**
1. Analyzes your description to determine type (decision/lesson/fact)
2. Creates properly formatted knowledge file
3. Asks where to add pointer (defaults to AGENTS.md)
4. Updates context file with reference

**Example:** `/record-knowledge We use Release-Please for automated versioning based on conventional commits`

**Read:** [Skill: Record Knowledge](skills/record-knowledge/SKILL.md)

---

## Critical Safeguards

- **Never commit secrets** - PyPI tokens, API keys stay in GitHub Secrets
- **Keep examples updated** - `examples/sample-warehouse/` must match `abc init` output
- **Test before release** - Always test CLI commands locally before pushing
- **Document breaking changes** - Use `feat!:` or `fix!:` commits for breaking changes

**Read:** [Lesson: Critical Project Safeguards](knowledge/lessons/critical-safeguards.md)

---

**Last Updated:** 2026-03-07
