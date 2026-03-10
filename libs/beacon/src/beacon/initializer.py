"""Warehouse initialization logic."""

import subprocess
from pathlib import Path
from typing import Any

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
        languages: list[str] | None = None,
        domains: list[str] | None = None,
        init_git: bool = True,
    ) -> dict[str, Any]:
        """
        Initialize a new warehouse repository.

        Args:
            org_name: Organization name for documentation
            languages: Ignored — inner knowledge structure is user-defined
            domains: Ignored — inner knowledge structure is user-defined
            init_git: Whether to initialize git repository

        Returns:
            Result dictionary with created paths
        """
        if self.warehouse_path.exists():
            raise ValueError(f"Directory already exists: {self.warehouse_path}")

        logger.info(f"Initializing warehouse at {self.warehouse_path}")

        # Create directory structure
        self._create_structure()

        # Create starter files
        self._create_contexts(org_name)
        self._create_knowledge()
        self._create_skills()
        self._create_docs(org_name)
        self._create_root_files(org_name)

        # Initialize git if requested
        if init_git:
            self._init_git()

        result = {
            "warehouse_path": str(self.warehouse_path),
            "git_initialized": init_git,
        }

        logger.info(f"Warehouse initialized successfully: {result}")
        return result

    def _create_structure(self) -> None:
        """Create required directory structure."""
        self.warehouse_path.mkdir(parents=True)
        (self.warehouse_path / "contexts").mkdir()
        (self.warehouse_path / "knowledge").mkdir()
        (self.warehouse_path / "skills").mkdir()
        (self.warehouse_path / "docs").mkdir()

    def _create_contexts(self, org_name: str) -> None:
        """Create starter context file."""
        global_context = f"""# {org_name} — Agent Context

**Organization:** {org_name}
**Last Updated:** [Date]

---

## Purpose

This file contains practices and standards that apply to all projects in {org_name}.
Add your team's rules, conventions, and workflow here.

---

## Instructions

Replace this placeholder with your organization's actual standards.
See the Agentic Beacon documentation for guidance on writing effective context files.
"""
        (self.warehouse_path / "contexts" / "AGENTS.md").write_text(global_context)

    def _create_knowledge(self) -> None:
        """Create starter knowledge file."""
        placeholder = """# Knowledge

Add your team's knowledge artifacts here. The structure is entirely yours to define.

Examples of what teams put here:
- Architectural decisions and their rationale
- Coding standards and conventions
- Framework-specific patterns and best practices
- Security policies
- "Why we chose X" explanations

There are no required subdirectories or naming conventions.
Organize knowledge however makes sense for your team.
"""
        (self.warehouse_path / "knowledge" / "README.md").write_text(placeholder)

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
