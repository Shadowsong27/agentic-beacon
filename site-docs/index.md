# Agentic Beacon

**The package manager for AI coding agents.**

Centrally manage and distribute contexts, knowledge, and skills across your team — with native support for Claude Code and OpenCode.

> *Git for AI Prompts. DRY for AI Agents.*

---

## The Problem: Context Drift

When a team adopts AI coding agents, each project accumulates its own `AGENTS.md` or context file. Standards diverge. A pattern discovered in one repo never reaches the others. When guidelines change, someone copy-pastes updates into 15 repos and misses three.

This is **Context Drift** — the same DRY problem that version control solved for code, unsolved for agentic engineering artifacts.

- **Reinvention at every project.** Context files get written from scratch for each new repo.
- **Knowledge stays siloed.** Lessons learned in one project never leave that developer's laptop.
- **No feedback loop.** When an agent session produces a better approach, there's no workflow to share it.

---

## How It Works

Two moving parts:

**Warehouse** — a single git repository owned by your team. It holds the shared source of truth: contexts, knowledge, skills, and agent definitions.

**Beacon** — a per-project connector. Running `abc warehouse connect` creates `.agentic-beacon/` in your project with a `beacon.yaml` that declares which warehouse artifacts this project needs.

```
Warehouse (shared git repo)                 Your project / global
────────────────────────────                ────────────────────────────────
knowledge/    ── abc sync ──►  .agentic-beacon/artifacts/knowledge/
contexts/     ── abc sync ──►  .agentic-beacon/artifacts/contexts/
                                opencode.json / AGENTS.md (wired)
skills/       ── abc sync ──►  .opencode/skills/<name>/
agents/       ── abc sync ──►  ~/.claude/agents/<name>.md
```

`abc sync` reads `beacon.yaml` and does the full job in one step: copies and wires knowledge and contexts into your agent config, installs skills into each detected tool's directories, and installs agent definitions globally.

When a session produces something worth sharing, `abc contribute` copies it back to the warehouse so every project benefits on the next sync.

---

## Artifact Types

Four types form the core of a warehouse, organized by two axes: **project scope** and **tool specificity**:

|  | Tool-agnostic | Tool-specific |
|---|---|---|
| **Project-scoped** | 📄 Contexts · 🧠 Knowledge | ⚡ Skills |
| **Global** | — | 🤖 Agents |

- **Contexts** — boot instructions and coding standards; wired into `opencode.json` / `AGENTS.md` automatically on sync
- **Knowledge** — atomic decisions, lessons, and facts; copied to `.agentic-beacon/artifacts/` and referenced from contexts
- **Skills** — reusable workflows installed as slash commands into each tool's live directories
- **Agents** — sub-agent definitions installed once into global tool directories (`~/.claude/agents/`, `~/.config/opencode/agents/`)

---

## Get Started

```bash
# Install
uv tool install agentic-beacon

# Create a warehouse
abc warehouse init my-org-warehouse

# Connect a project
abc warehouse connect --path ~/my-org-warehouse

# Browse + select artifacts via TUI, then sync
abc adopt
abc sync
```

→ **[Quick Start](quickstart.md)** for a full walkthrough.

---

## Compared to Similar Tools

| Tool | What it does |
|------|-------------|
| **Repomix** | Bundles your codebase into a single LLM-readable file |
| **faf-mcp** | Syncs context files locally via MCP |
| **cursorrules.com** | Static directory of community `.cursorrules` files |
| **Langfuse / LLM Ops** | Production observability and prompt management |

**Use Agentic Beacon when** you want a version-controlled, team-wide source of truth for agent instructions across multiple projects or repos.
