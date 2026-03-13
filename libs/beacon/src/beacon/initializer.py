"""Warehouse initialization logic."""

import subprocess
from pathlib import Path
from typing import Any

from loguru import logger

_DATA_DIR = Path(__file__).parent / "data"


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

        When the target directory already exists (e.g. a freshly cloned empty
        repo), initialization proceeds in-place: existing files are left
        untouched and only missing files are created.

        Args:
            org_name: Organization name for documentation
            languages: Ignored — inner knowledge structure is user-defined
            domains: Ignored — inner knowledge structure is user-defined
            init_git: Whether to initialize git repository

        Returns:
            Result dictionary with created paths and ``in_place`` flag
        """
        in_place = self.warehouse_path.exists()

        logger.info(
            f"Initializing warehouse at {self.warehouse_path} "
            f"({'in-place' if in_place else 'new directory'})"
        )

        # Create directory structure
        self._create_structure()

        # Create starter files
        self._create_contexts(org_name)
        self._create_knowledge()
        self._create_skills()
        self._create_docs(org_name)
        self._create_root_files(org_name)
        self._install_bundled_skills()

        # Initialize git if requested
        if init_git:
            self._init_git()

        result = {
            "warehouse_path": str(self.warehouse_path),
            "git_initialized": init_git,
            "in_place": in_place,
        }

        logger.info(f"Warehouse initialized successfully: {result}")
        return result

    def _create_structure(self) -> None:
        """Create required directory structure (skips dirs that already exist)."""
        self.warehouse_path.mkdir(parents=True, exist_ok=True)
        (self.warehouse_path / "contexts").mkdir(exist_ok=True)
        (self.warehouse_path / "knowledge").mkdir(exist_ok=True)
        (self.warehouse_path / "skills").mkdir(exist_ok=True)
        (self.warehouse_path / "docs").mkdir(exist_ok=True)

    def _write_if_missing(self, path: Path, content: str) -> None:
        """Write *content* to *path* only when the file does not already exist."""
        if not path.exists():
            path.write_text(content)
        else:
            logger.debug(f"Skipping existing file: {path}")

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
        self._write_if_missing(
            self.warehouse_path / "contexts" / "AGENTS.md", global_context
        )

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
        self._write_if_missing(
            self.warehouse_path / "knowledge" / "README.md", placeholder
        )

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
        self._write_if_missing(
            self.warehouse_path / "skills" / "README.md", skills_readme
        )

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
        self._write_if_missing(
            self.warehouse_path / "docs" / "architecture.md", architecture_doc
        )

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
        self._write_if_missing(
            self.warehouse_path / "docs" / "contribution-guide.md", contribution_guide
        )

    def _create_root_files(self, org_name: str) -> None:
        """Create root-level files."""
        readme = f"""# {org_name} Agentic Engineering Warehouse

Centralized repository for coding standards, knowledge, and skills used by AI agents across {org_name}.

## Quick Start

### For Developers

```bash
# 1. Install the Agentic Beacon CLI (once per machine)
uv tool install agentic-beacon

# 2. In your project, connect to this warehouse
cd ~/my-project
abc warehouse connect --path ~/path/to/this-warehouse

# 3. Create your artifact config and sync
abc setup --manual   # then edit .agentic-beacon/beacon.yaml
abc sync

# 4. (Optional) Register skills as agent slash commands
abc skill install --all
```

### For Contributors

```bash
# Clone warehouse
git clone <this-repo-url>

# Make changes
# - Add contexts, knowledge, or skills
# - Follow the contribution guide in docs/

# Submit PR

# After your changes are merged, teammates can pull them in with:
abc update
```

### Offline / Private Install

Download the bundle zip for your platform from the [Releases page](<releases-url>):

```bash
unzip agentic_beacon-X.Y.Z-bundle-<platform>.zip -d abc-bundle
uv tool install agentic-beacon --no-index --find-links ./abc-bundle/
```

## Structure

- **`contexts/`** - Boot instructions loaded by agents at session start
- **`knowledge/`** - Atomic decisions, lessons, and facts organized by scope
- **`skills/`** - Reusable workflows and procedures (agent slash commands)
- **`docs/`** - Warehouse documentation and contribution guides

## CLI Reference

| Command | Description |
|---------|-------------|
| `abc warehouse connect` | Connect a project to this warehouse |
| `abc setup` | Create `beacon.yaml` for a project |
| `abc sync` | Sync declared artifacts to the project |
| `abc skill install` | Register synced skills as agent slash commands |
| `abc list` | Show available content in the warehouse |
| `abc status` | Show connection and sync status |
| `abc delta` | Find local changes not yet contributed back |
| `abc contribute` | Copy local improvements back to the warehouse |
| `abc update` | Re-sync and overwrite local artifacts from warehouse |
| `abc clean` | Remove synced artifacts from the project |

## Documentation

- [Contribution Guide](./docs/contribution-guide.md) - How to add content

## Maintenance

This warehouse is maintained by {org_name}'s Platform Team.

- **Review Frequency:** Quarterly
- **Questions:** Contact platform-team@example.com
- **Issues:** Open an issue in this repository
"""
        self._write_if_missing(self.warehouse_path / "README.md", readme)

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
        self._write_if_missing(self.warehouse_path / ".gitignore", gitignore)

    def _install_bundled_skills(self) -> None:
        """Add abc-provided skills to the warehouse skills directory (skips existing)."""
        bundled_skills_dir = _DATA_DIR / "skills"
        for skill_dir in bundled_skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            content = skill_md.read_text(encoding="utf-8")
            dest_dir = self.warehouse_path / "skills" / skill_dir.name
            dest_dir.mkdir(parents=True, exist_ok=True)
            self._write_if_missing(dest_dir / "SKILL.md", content)

        logger.info("Bundled skills installed")

    def _init_git(self) -> None:
        """Initialize git repository with initial commit.

        Skips ``git init`` when the directory already has a ``.git`` folder
        (e.g. a freshly cloned empty repo), but still stages and commits any
        newly created files.
        """
        try:
            if not (self.warehouse_path / ".git").exists():
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
