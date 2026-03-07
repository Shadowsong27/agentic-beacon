"""Warehouse initialization logic."""

import subprocess
from pathlib import Path
from typing import Any, Optional

from loguru import logger


class WarehouseInitializer:
    """Handles creation of new warehouse repositories."""

    def __init__(self, *, warehouse_path: Path):
        """
        Initialize warehouse initializer.

        Args:
            warehouse_path: Path where warehouse will be created
        """
        self.warehouse_path = warehouse_path

    def init(
        self,
        *,
        org_name: str = "Your Organization",
        languages: Optional[list[str]] = None,
        domains: Optional[list[str]] = None,
        init_git: bool = True,
    ) -> dict[str, Any]:
        """
        Initialize a new warehouse repository.

        Args:
            org_name: Organization name for documentation
            languages: List of primary languages (e.g., ["python", "typescript"])
            domains: List of primary domains (e.g., ["data-platform", "web-services"])
            init_git: Whether to initialize git repository

        Returns:
            Result dictionary with created paths
        """
        if self.warehouse_path.exists():
            raise ValueError(f"Directory already exists: {self.warehouse_path}")

        logger.info(f"Initializing warehouse at {self.warehouse_path}")

        # Create directory structure
        self._create_structure()

        # Create placeholder files
        self._create_contexts(org_name)
        self._create_knowledge(languages or [], domains or [])
        self._create_skills()
        self._create_docs(org_name)
        self._create_root_files(org_name)

        # Initialize git if requested
        if init_git:
            self._init_git()

        result = {
            "warehouse_path": str(self.warehouse_path),
            "git_initialized": init_git,
            "languages": languages or [],
            "domains": domains or [],
        }

        logger.info(f"Warehouse initialized successfully: {result}")
        return result

    def _create_structure(self) -> None:
        """Create basic directory structure."""
        self.warehouse_path.mkdir(parents=True)
        (self.warehouse_path / "contexts").mkdir()
        (self.warehouse_path / "knowledge" / "global" / "decisions").mkdir(parents=True)
        (self.warehouse_path / "knowledge" / "global" / "lessons").mkdir(parents=True)
        (self.warehouse_path / "knowledge" / "global" / "facts").mkdir(parents=True)
        (self.warehouse_path / "knowledge" / "languages").mkdir(parents=True)
        (self.warehouse_path / "knowledge" / "domains").mkdir(parents=True)
        (self.warehouse_path / "skills").mkdir()
        (self.warehouse_path / "docs").mkdir()

    def _create_contexts(self, org_name: str) -> None:
        """Create context files."""
        global_context = f"""# Global Context

**Organization:** {org_name}  
**Last Updated:** [Date]

---

## Purpose

This file contains universal practices and standards that apply to ALL projects in {org_name}.

---

## Commit Conventions

**Brief:** Use Conventional Commits format for all commits.

**Format:** `<type>(<scope>): <description>`

**Common types:** feat, fix, refactor, docs, test, chore

**Read:** [Full guide](../knowledge/global/decisions/commit-conventions.md)

---

## Code Review Process

**Brief:** All changes require PR review from at least one team member.

**Read:** [Review guidelines](../knowledge/global/lessons/code-review-process.md)

---

## Documentation Standards

**Brief:** Document all public APIs and complex logic.

**Read:** [Documentation guide](../knowledge/global/decisions/documentation-standards.md)

---

## Progressive Disclosure

Keep context files minimal with pointers to detailed knowledge:

- **In context files:** 1-2 sentence summary + pointer
- **In knowledge files:** Full explanation with examples

**Example:**
```markdown
## Rule Name

**Brief:** Brief statement of the rule.

**Read:** [Detailed explanation](../knowledge/.../file.md)
```

---

**Instructions:** Replace this placeholder with your organization's actual standards.
"""
        (self.warehouse_path / "contexts" / "AGENTS.global.md").write_text(global_context)

        readme = """# Contexts Directory

This directory contains AGENTS.md context files organized by scope.

## Structure

```
contexts/
├── AGENTS.global.md           # Required for all projects
├── AGENTS.<language>.md       # Language-specific contexts
└── AGENTS.<domain>.md         # Domain-specific contexts
```

## Creating New Context Files

1. **Determine scope**: Global, language, or domain-specific?
2. **Follow naming**: `AGENTS.<scope>.md` (e.g., `AGENTS.python.md`)
3. **Use progressive disclosure**: Brief summaries + pointers to knowledge files
4. **Reference knowledge**: Point to files in corresponding knowledge directory

## Usage

Teams select which contexts to install in their projects:

```bash
abc setup --context global --context python --context data-platform
```

Selected context files are copied to `.opencode/contexts/` in the project.
"""
        (self.warehouse_path / "contexts" / "README.md").write_text(readme)

    def _create_knowledge(self, languages: list[str], domains: list[str]) -> None:
        """Create knowledge structure with placeholders."""
        # Global knowledge placeholders
        decisions_placeholder = """# Placeholder - Add Your Decisions

## What Goes Here

Technical choices and their rationale that apply across all projects.

## Format

```markdown
## Decision: [Title]

**Context:** Why this decision was needed

**Options Considered:**
1. Option A - pros/cons
2. Option B - pros/cons

**Decision:** What we chose

**Rationale:** Why this is the best choice

**Consequences:** Trade-offs we accept

**Date:** YYYY-MM-DD
```

## Examples

- `commit-conventions.md` - Commit message standards
- `code-review-policy.md` - PR review requirements
- `testing-strategy.md` - Testing approach and tools

---

**Delete this file and add your actual decisions.**
"""
        (self.warehouse_path / "knowledge" / "global" / "decisions" / ".placeholder.md").write_text(
            decisions_placeholder
        )

        lessons_placeholder = """# Placeholder - Add Your Lessons

## What Goes Here

Patterns where agents commonly fail or get distracted, applicable across all projects.

## Format

```markdown
## Lesson: [Title]

**Agent Failure Mode:** How agents typically fail

**Correct Pattern:** What agents should do instead

**Guardrail:** Questions agents should ask before acting

**When this matters:** Context where this applies

**Date:** YYYY-MM-DD
```

## Examples

- `session-handoff-patterns.md` - How to hand off work between sessions
- `progressive-disclosure.md` - When to load detailed context
- `exception-handling.md` - Common exception handling mistakes

---

**Delete this file and add your actual lessons.**
"""
        (self.warehouse_path / "knowledge" / "global" / "lessons" / ".placeholder.md").write_text(
            lessons_placeholder
        )

        facts_placeholder = """# Placeholder - Add Your Facts

## What Goes Here

Established technical information and configurations that apply across all projects.

## Format

```markdown
## Fact: [Title]

**Statement:** The fact itself

**Context:** When/where this applies

**Usage Notes:** How to use this information

**Date:** YYYY-MM-DD
```

## Examples

- `infrastructure-endpoints.md` - Shared infrastructure configs
- `security-requirements.md` - Security standards
- `deployment-environments.md` - Environment names and access

---

**Delete this file and add your actual facts.**
"""
        (self.warehouse_path / "knowledge" / "global" / "facts" / ".placeholder.md").write_text(
            facts_placeholder
        )

        # Create language-specific directories
        for lang in languages:
            lang_dir = self.warehouse_path / "knowledge" / "languages" / lang
            (lang_dir / "decisions").mkdir(parents=True)
            (lang_dir / "lessons").mkdir(parents=True)
            (lang_dir / "facts").mkdir(parents=True)

            placeholder = f"""# {lang.title()} Knowledge

Add {lang}-specific knowledge here:
- Decisions: Technical choices for {lang} projects
- Lessons: Common {lang} agent failure modes
- Facts: {lang} configurations and standards
"""
            (lang_dir / "README.md").write_text(placeholder)

        # Create domain-specific directories
        for domain in domains:
            domain_dir = self.warehouse_path / "knowledge" / "domains" / domain
            (domain_dir / "decisions").mkdir(parents=True)
            (domain_dir / "lessons").mkdir(parents=True)
            (domain_dir / "facts").mkdir(parents=True)

            placeholder = f"""# {domain.replace('-', ' ').title()} Knowledge

Add {domain}-specific knowledge here:
- Decisions: Technical choices for {domain} projects
- Lessons: Common {domain} patterns and anti-patterns
- Facts: {domain} configurations and infrastructure
"""
            (domain_dir / "README.md").write_text(placeholder)

        # Knowledge README
        knowledge_readme = """# Knowledge Directory

Atomic, reusable knowledge organized by scope and type.

## Structure

```
knowledge/
├── global/              # Universal knowledge (all projects)
│   ├── decisions/
│   ├── lessons/
│   └── facts/
├── languages/          # Language-specific knowledge
│   ├── python/
│   ├── typescript/
│   └── ...
└── domains/            # Domain-specific knowledge
    ├── data-platform/
    ├── web-services/
    └── ...
```

## Knowledge Types

### Decisions
Technical choices made and their rationale.

### Lessons
Patterns where agents commonly fail or get distracted.

### Facts
Established technical information and configurations.

## Selective Installation

When projects select contexts during setup, only relevant knowledge is copied:

```bash
abc setup --context python --knowledge global --knowledge languages/python
```

This copies only global and Python-specific knowledge to the project.
"""
        (self.warehouse_path / "knowledge" / "README.md").write_text(knowledge_readme)

    def _create_skills(self) -> None:
        """Create skills structure."""
        skills_readme = """# Skills Directory

Reusable workflows and procedures for agents.

## Structure

```
skills/
└── skill-name/
    ├── SKILL.md           # Main skill instructions
    ├── templates/         # Optional: Template files
    ├── scripts/           # Optional: Helper scripts
    └── examples/          # Optional: Example usage
```

## Creating Skills

1. **Create directory:** `skills/your-skill-name/`
2. **Add SKILL.md** with instructions for agents
3. **Optional:** Add templates, scripts, or examples
4. **Test locally** before adding to warehouse

## Example Skill Structure

```markdown
# Skill: Deploy to Production

## Purpose
Guide agents through safe production deployment.

## When to Use
- Deploying new features to production
- Rolling back production deployments

## Procedure

1. **Verify tests pass**
   ```bash
   pytest tests/
   ```

2. **Create release tag**
   ```bash
   git tag -a v1.0.0 -m "Release 1.0.0"
   ```

3. **Deploy**
   ```bash
   ./scripts/deploy.sh production
   ```

## Safety Checks
- [ ] All tests passing
- [ ] No breaking changes
- [ ] Changelog updated
```

## Installation

Teams install skills to their projects:

```bash
abc setup --skill deploy-production
```
"""
        (self.warehouse_path / "skills" / "README.md").write_text(skills_readme)

    def _create_docs(self, org_name: str) -> None:
        """Create documentation files."""
        architecture_doc = f"""# {org_name} Warehouse Architecture

## Overview

This warehouse contains centralized knowledge, contexts, and skills for {org_name}'s agentic development practices.

## Structure

### Contexts (`contexts/`)
High-level guidance files loaded by agents on session start.

- **Global**: Universal practices for all projects
- **Language**: Language-specific standards (Python, TypeScript, etc.)
- **Domain**: Domain-specific patterns (data-platform, web-services, etc.)

### Knowledge (`knowledge/`)
Detailed information organized by scope and type.

- **Decisions**: Technical choices and rationale
- **Lessons**: Common failure modes and correct patterns
- **Facts**: Established configurations and standards

### Skills (`skills/`)
Reusable workflows and procedures for specific tasks.

## Distribution

Teams use Beacon CLI to distribute warehouse content to projects:

```bash
# Install beacon
pip install beacon --index-url https://your-pypi.local/simple/

# Setup in project
cd ~/my-project
abc setup --warehouse ~/warehouse --all

# Content is copied to .opencode/ (gitignored)
```

## Contribution

1. Make changes in warehouse repository
2. Test with Beacon CLI
3. Submit pull request
4. After merge, teams run `abc update` to sync

## Maintenance

- Review and update contexts quarterly
- Document new patterns as lessons
- Keep facts current with infrastructure changes
"""
        (self.warehouse_path / "docs" / "architecture.md").write_text(architecture_doc)

        contribution_guide = f"""# Contributing to {org_name} Warehouse

## How to Contribute

### 1. Find Something to Add

- New coding standard → Add to contexts
- Technical decision → Document in knowledge/decisions
- Common mistake → Document in knowledge/lessons
- Reusable workflow → Create in skills

### 2. Follow Structure

**Contexts:** Brief summary + pointer to knowledge  
**Knowledge:** Detailed explanation with examples  
**Skills:** Step-by-step procedures

### 3. Test Locally

```bash
# Test distribution
cd ~/test-project
abc setup --warehouse ~/warehouse --all
beacon status
```

### 4. Submit PR

- Clear title describing the change
- Link to related discussions or issues
- Explain why this addition is useful

## Guidelines

- **Be specific:** Vague guidance doesn't help agents
- **Be concise:** Agents have token limits
- **Include examples:** Show don't just tell
- **Keep updated:** Remove outdated information

## Questions?

Contact the platform team or open an issue.
"""
        (self.warehouse_path / "docs" / "contribution-guide.md").write_text(
            contribution_guide
        )

    def _create_root_files(self, org_name: str) -> None:
        """Create root-level files."""
        readme = f"""# {org_name} Agentic Engineering Warehouse

Centralized repository for coding standards, knowledge, and skills used by AI agents across {org_name}.

## Quick Start

### For Developers

```bash
# Install Beacon CLI
pip install beacon --index-url https://your-pypi.local/simple/

# Setup in your project
cd ~/my-project
abc setup --warehouse ~/path/to/this/repo --all

# Content is distributed to .opencode/ (gitignored)
```

### For Contributors

```bash
# Clone warehouse
git clone <this-repo-url>

# Make changes
# - Add contexts, knowledge, or skills
# - Follow contribution guide

# Submit PR
```

## Structure

- **`contexts/`** - High-level guidance loaded by agents
- **`knowledge/`** - Detailed information organized by type
- **`skills/`** - Reusable workflows and procedures
- **`docs/`** - Warehouse documentation

## Commands

| Command | Description |
|---------|-------------|
| `beacon list` | Show available content |
| `abc setup` | Install content to project |
| `beacon status` | Show what's installed |
| `beacon delta` | Compare project with warehouse |
| `abc update` | Sync from warehouse |

## Documentation

- [Architecture](./docs/architecture.md) - How the warehouse is organized
- [Contribution Guide](./docs/contribution-guide.md) - How to add content

## Maintenance

This warehouse is maintained by {org_name}'s Platform Team.

- **Review Frequency:** Quarterly
- **Questions:** Contact platform-team@example.com
- **Issues:** Open an issue in this repository
"""
        (self.warehouse_path / "README.md").write_text(readme)

        gitignore = """# Editor and IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Temporary files
*.tmp
*.bak

# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/
.venv/
venv/

# Logs
*.log
logs/
"""
        (self.warehouse_path / ".gitignore").write_text(gitignore)

    def _init_git(self) -> None:
        """Initialize git repository with initial commit."""
        try:
            subprocess.run(
                ["git", "init"],
                cwd=self.warehouse_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "add", "."],
                cwd=self.warehouse_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "feat: initialize warehouse with beacon"],
                cwd=self.warehouse_path,
                check=True,
                capture_output=True,
            )
            logger.info("Git repository initialized with initial commit")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Git initialization failed: {e}")
            raise
        except FileNotFoundError:
            logger.warning("Git not found in PATH, skipping git initialization")
