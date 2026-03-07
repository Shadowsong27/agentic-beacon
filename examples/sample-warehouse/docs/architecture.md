# Example Corp Warehouse Architecture

## Overview

This warehouse contains centralized knowledge, contexts, and skills for Example Corp's agentic development practices.

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
