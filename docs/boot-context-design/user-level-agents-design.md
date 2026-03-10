# User-Level AGENTS.md Design

How to use `~/.config/opencode/AGENTS.md` effectively — and why keeping it minimal is the right default.

**Last Updated:** 2026-03-11

---

## What This File Is For

The user-level AGENTS.md at `~/.config/opencode/AGENTS.md` is loaded by OpenCode on every session, across every project. It sits between the warehouse contexts (shared, domain-specific knowledge) and the project-level AGENTS.md (codebase-specific).

Its purpose is narrow: **personal behavioral preferences that apply to how agents interact with you**, regardless of which project you're in.

This is NOT the place for:
- Technical standards → those live in the warehouse (`~/Code/hl-knowledge-market/contexts/`)
- Project architecture → that lives in the project's own `AGENTS.md`
- Domain knowledge → that lives in the warehouse knowledge files

---

## The Minimal-by-Design Principle

The file should feel almost empty most of the time. That's a feature, not a gap.

Every rule you add here competes for context window space on every session. If a rule belongs to a language standard or domain pattern, it should be in the warehouse — where it can be versioned, reviewed, and shared across projects automatically.

**A bloated user-level AGENTS.md is a sign that content hasn't been promoted to the right place.**

---

## What Belongs Here

### Personal behavioral preferences

How you want the agent to work with you — communication style, workflow habits, tool choices that are yours specifically:

```markdown
## Workflow Preferences

- Ask before running destructive commands (rm, force push, hard reset)
- Show git diff before committing
- Create todo lists for tasks with 3+ steps
```

### Local environment specifics

Machine-specific config that no project file should need to know:

```markdown
## Local Environment

**Python:** /opt/homebrew/bin/python3.11
**Node:** /opt/homebrew/bin/node
```

### Experimental patterns (short-term only)

Testing a new pattern before deciding whether to promote it to the warehouse:

```markdown
## Experimental (Added 2026-03-11 — validate by 2026-03-25)

**Pattern:** Return `Result[T, E]` types instead of raising exceptions for recoverable errors.
**Testing in:** hl-sandbox-pipelines, project-dot
**Next:** PR to warehouse python-standards context if effective
```

Experimental entries have a time limit. After ~2 weeks: either promote to the warehouse or delete.

---

## What Does NOT Belong Here

| Content type | Where it belongs |
|---|---|
| Python type annotation rules | `hl-knowledge-market/contexts/python-standards.md` |
| Airflow development patterns | `hl-knowledge-market/contexts/airflow-development.md` |
| Homelab infra topology | `hl-knowledge-market/contexts/infra-topology.md` |
| Project module structure | `<project>/AGENTS.md` |
| Project troubleshooting guides | `<project>/AGENTS.md` |
| Knowledge warehouse layout | Just use `abc list` |

---

## How It Differs from Project-Level AGENTS.md

| Dimension | User-level | Project-level |
|---|---|---|
| **Scope** | All projects, all sessions | This codebase only |
| **Content** | Personal preferences, local env | Architecture, modules, troubleshooting |
| **Audience** | You | Any agent working in this repo |
| **Size** | Should stay tiny | Can be more detailed |
| **Changes** | Rare — mainly staging/promoting | Updated as the project evolves |

The key distinction: user-level is about **how** the agent works with you. Project-level is about **what** the agent needs to know about the codebase.

---

## The Staging/Promote Lifecycle

The user-level file is the staging area for patterns that might eventually become organizational standards.

```
1. Discover a useful pattern while working on a project
       ↓
2. Add it to ~/.config/opencode/AGENTS.md under "Experimental"
   with a date and target promotion deadline
       ↓
3. Test it across 2–3 projects over ~2 weeks
       ↓
4a. It works consistently → PR to hl-knowledge-market
    (add to the appropriate context file)
       ↓
    Remove from user-level AGENTS.md (now redundant with warehouse)

4b. It doesn't work / not worth it → Delete from user-level AGENTS.md
```

This keeps the user-level file honest: nothing should sit here indefinitely. Either a pattern earns its place in the warehouse, or it gets dropped.

---

## Load Order and Precedence

When OpenCode starts a session, context is loaded in this order:

```
1. Warehouse contexts (from .agentic-beacon/artifacts/contexts/)
   e.g. python-standards.md, airflow-development.md, infra-topology.md

2. User-level preferences (~/.config/opencode/AGENTS.md)   ← this file

3. Project-level context (<project>/AGENTS.md)
```

Later contexts override earlier ones. User-level can override warehouse defaults for your personal preferences (e.g. log level, verbosity). Project-level can override both.

---

## Related Documentation

- [Three-tier architecture overview](./agents-md-architecture.md) — full decision framework for what goes where
- [Project-level AGENTS.md guide](./project-level-agents-design.md) — how to write effective project context
- [Agentic warehouse design](../agentic-warehouse-design.md) — the overall warehouse philosophy
