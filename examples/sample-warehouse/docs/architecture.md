# Starter Org Warehouse Architecture

## Overview

This warehouse contains centralized knowledge, contexts, and skills for Starter Org's agentic development practices.

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
uv tool install agentic-beacon

# Connect a project to this warehouse
cd ~/my-project
abc warehouse connect --path ~/path/to/this-warehouse

# Create artifact config and sync
abc setup --manual   # then edit .agentic-beacon/beacon.yaml
abc sync

# Content is copied to .agentic-beacon/ (gitignored)
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
