# Agents Directory

Reusable coding agent definitions for distribution to team members.

## What Are Agents?

Agent definition files are markdown files with YAML frontmatter that configure
AI coding assistants (OpenCode, Claude Code) with specialized instructions and
roles. Unlike other artifact types, agents are **globally installed** on the
developer's machine — not scoped to a single project.

## Frontmatter Format

Agent files follow standard agent frontmatter conventions:

```markdown
---
name: agent-name
description: What this agent does and when to use it
---

# Agent Instructions

Detailed instructions for the agent go here.
```

**Important:** `requires:` must **not** appear in agent frontmatter.
Dependencies are declared in `agents/agents.yaml` instead (see below).

## Agent Dependency Manifest (`agents/agents.yaml`)

The `agents/agents.yaml` file maps each agent to the skills it depends on.

Example:

```yaml
# Beacon agent dependency manifest.
# Each top-level key maps an agent (agents/<key>.md) to its required skills.
#
# Example:
# spec-planner:
#   skills:
#     - opsx-enhance-tasks
#     - openspec-propose
#
# pipeline-developer:
#   skills: []
```

- Each top-level key must match the stem of an `.md` file under `agents/` (excluding `README.md`).
- `skills:` is a list of skill directory names under `skills/`.
- `requires:` in agent frontmatter is forbidden — move dependencies to `agents.yaml`.

## Structure

```
agents/
├── README.md
├── agents.yaml          # Agent dependency manifest
└── agent-name.md        # Agent definition with frontmatter
```

## Installing Agents

Team members install agents from the warehouse to their machine:

```bash
# Sync every agent definition from the warehouse into global tool directories
abc agents sync
```

This links agents to the globally detected tool directories:
- OpenCode: `~/.config/opencode/agents/<name>.md`
- Claude Code: `~/.claude/agents/<name>.md`

## Notes

- Agents are **not** tracked in `beacon.yaml` (they are globally installed)
- Global agent files are per-file symlinks to this warehouse, so edits land in the warehouse working tree
- View installed agents: `abc list agents`
- View available warehouse agents: `abc warehouse list agents`
