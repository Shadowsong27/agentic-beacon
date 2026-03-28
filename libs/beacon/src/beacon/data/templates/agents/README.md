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

## Structure

```
agents/
└── agent-name.md    # Agent definition with frontmatter
```

## Installing Agents

Team members install agents from the warehouse to their machine:

```bash
# Install a specific agent globally
abc install agents/<name>.md
```

This installs the agent to the globally detected tool directories:
- OpenCode: `~/.config/opencode/agents/<name>.md`
- Claude Code: `~/.claude/agents/<name>.md`

## Notes

- Agents are **not** tracked in `beacon.yaml` (they are globally installed)
- Agents are **not** synced via `abc sync` (use `abc install` for each agent)
- View installed agents: `abc list agents`
- View available warehouse agents: `abc warehouse list agents`
