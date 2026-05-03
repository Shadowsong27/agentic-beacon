# {org_name} Warehouse Architecture

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

1. Make changes in the warehouse repository (edit directly, or edit via any project's `.agentic-beacon/artifacts/` symlinks — they write through to the warehouse working tree)
2. Test with Beacon CLI
3. Commit the changes (`abc warehouse contribute -m "…" --push` or via plain `git` inside the warehouse clone)
4. After merge, teammates pull the warehouse — updated content is visible through existing project symlinks immediately (no per-project re-sync required unless `beacon.yaml` itself changed)

## Maintenance

- Review and update contexts quarterly
- Document new patterns as lessons
- Keep facts current with infrastructure changes
