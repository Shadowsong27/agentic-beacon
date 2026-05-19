# Agents Directory

Reusable coding agent definitions for distribution to team members.

## What Are Agents?

Agent definition files are markdown files with YAML frontmatter that configure
AI coding assistants (OpenCode, Claude Code) with specialized instructions and
roles. Agents are declared per-project in `beacon.yaml.artifacts.agents` and
wired into project-local tool directories by `abc sync` or `abc adopt`.

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
├── agent-name.md        # Agent definition with frontmatter
└── _partials/           # (Optional) shared fragments — see below
    └── shared-fragment.md
```

## Shared Fragments (`agents/_partials/`)

Files under `agents/_partials/` are **fragments, not agents.** They let
multiple agents reference a shared checklist or boilerplate block via a
relative markdown link (e.g. `[checklist](_partials/deep-review.md)`).

Conventions:

- Partials are **not** registered in `agents.yaml` and are skipped by
  `abc warehouse list agents` and `abc warehouse lint` agent checks.
- Whenever any agent is declared in a project's `beacon.yaml`, every file
  under `agents/_partials/` is **co-distributed** alongside it so relative
  links inside agent files resolve at tool runtime
  (`.claude/agents/_partials/` and `.opencode/agents/_partials/`).
- The filter recognises **`_partials/` only.** Other leading-underscore
  directories (`_internal/`, `_drafts/`) are treated as agents and will
  fail lint.

## Wiring Agents

Agents are project-scoped and wired via `abc adopt` or `abc sync`:

```bash
# Interactively select agents to wire into this project
abc adopt

# Or, after adding agents to beacon.yaml directly, sync to wire them
abc sync
```

After wiring, agents are available in:
- Claude Code: `.claude/agents/<name>.md` (project-local)
- OpenCode: `.opencode/agents/<name>.md` (project-local)

## Notes

- Agents are declared per-project in `beacon.yaml.artifacts.agents`
- Project-local agent symlinks are gitignored (per-machine state)
- The team-shared SSOT is `beacon.yaml.artifacts.agents` — `abc sync` recreates symlinks anywhere
- View wired agents: `abc list agents`
- View available warehouse agents: `abc warehouse list agents`
