# Agentic Beacon

**The package manager for AI coding agents.**

Centrally manage and distribute contexts, knowledge, and skills across your team — with native support for Claude Code and OpenCode. Beacon also handles **agent config wiring**: it bootstraps and maintains your agent's config files (`opencode.json`, `CLAUDE.md`) so synced artifacts are picked up without hand-editing.

> *Git for AI Prompts. DRY for AI Agents.*

!!! tip "Built for multiplayer"
    Agentic Beacon is designed as a team tool first. The warehouse model is built around shared ownership, bidirectional contribution, and the compounding benefits of a growing knowledge base — value that scales with the number of people and projects contributing to it. Solo use is fully supported (many start that way), but the tool was built with multiplayer in mind.

---

## The Problem: Context Drift

When a team adopts AI coding agents, each project accumulates its own context file. Standards diverge. A pattern discovered in one repo never reaches the others. When guidelines change, someone copy-pastes updates into 15 repos and misses three.

This is **Context Drift** — the same DRY problem that version control solved for code, unsolved for agentic engineering artifacts.

- **Reinvention at every project.** Context files get written from scratch for each new repo.
- **Knowledge stays siloed.** Lessons learned in one project never leave that developer's laptop.
- **No feedback loop.** When an agent session produces a better approach, there's no workflow to share it.

---

## How It Works

Two moving parts:

**Warehouse** — a single git repository owned by your team. It holds the shared source of truth: contexts, knowledge, skills, and agent definitions.

**Beacon** — a per-project connector. Running `abc warehouse connect` creates `.agentic-beacon/` in your project with a `beacon.yaml` that declares which contexts, skills, and agents this project needs. Knowledge files are auto-derived from markdown links in contexts and skills.

```
Warehouse (shared git repo)                 Your project
────────────────────────────                ────────────────────────────────
contexts/     ── abc sync ──►  .agentic-beacon/artifacts/contexts/
                                 opencode.json / CLAUDE.md (wired)
knowledge/    ── auto-derive ─► .agentic-beacon/artifacts/knowledge/
skills/       ── abc sync ──►  .opencode/skills/<name>/
agents/       ── abc sync ──►  .claude/agents/<name>.md
                                 .opencode/agents/<name>.md
```

`abc sync` reads `beacon.yaml`, resolves skill→context dependencies via frontmatter, auto-derives knowledge from markdown links, and creates symlinks into the warehouse for all resolved artifacts.

When a session produces something worth sharing, `abc warehouse contribute -m "message"` commits changes in the warehouse working tree so every project benefits on the next sync.

---

## Artifact Types

Four types form the core of a warehouse, organized by two axes: **project scope** and **tool specificity**:

|  | Tool-agnostic | Tool-specific |
|---|---|---|
| **Project-scoped** | 📄 Contexts · 🧠 Knowledge | ⚡ Skills · 🤖 Agents |
| **Global** | — | — |

- **Contexts** — boot instructions and coding standards; declared in `beacon.yaml`. Beacon performs **agent config wiring** — it creates `opencode.json` / `CLAUDE.md` if missing and writes synced context references into them on every `abc sync`.
- **Knowledge** — decisions, lessons, and facts; auto-derived from markdown links in contexts and skills — no manual configuration needed
- **Skills** — reusable workflows with frontmatter `requires:` dependencies; installed as slash commands
- **Agents** — sub-agent definitions declared per-project in `beacon.yaml`; wired into project-local `.claude/agents/` and `.opencode/agents/` on sync

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
| **Shared wiki / prompt library** | A team-maintained document store agents are told to read |
| **Langfuse / LLM Ops** | Production observability and prompt management |

**Use Agentic Beacon when** you want a version-controlled, team-wide source of truth for agent instructions across multiple projects or repos.

### Why not a shared wiki or prompt library?

A shared wiki is **read-only by design** — someone curates it, everyone else consumes it. There is no path from a coding session back to the wiki. Improvements stay on the developer's machine.

Agentic Beacon is **bidirectional**. When an agent session produces a better approach, `abc warehouse contribute -m "message"` commits it back to the warehouse. Once merged, every project gets the improvement on the next `abc sync`. The warehouse gets smarter over time because the whole team is contributing to it, not just reading from it. That compounding loop is what the tool was built around.
