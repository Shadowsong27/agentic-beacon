<p align="center">
  <img src="agentic-beacon-banner.png" alt="Agentic Beacon" width="100%" />
</p>

<p align="center">
  <a href="https://github.com/Shadowsong27/agentic-beacon/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Shadowsong27/agentic-beacon" alt="License: MIT" /></a>
  <a href="https://pypi.org/project/agentic-beacon/"><img src="https://img.shields.io/pypi/pyversions/agentic-beacon" alt="Python Version" /></a>
  <a href="https://github.com/Shadowsong27/agentic-beacon/stargazers"><img src="https://img.shields.io/github/stars/Shadowsong27/agentic-beacon" alt="GitHub Stars" /></a>
  <a href="https://pypi.org/project/agentic-beacon/"><img src="https://img.shields.io/pypi/dm/agentic-beacon" alt="Monthly Downloads" /></a>
  <a href="https://github.com/Shadowsong27/agentic-beacon/pulls"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="PRs Welcome" /></a>
</p>

**The package manager for AI coding agents. Centrally manage and distribute contexts, knowledge, and skills across your team — with native support for Claude Code and OpenCode.**

> *Git for AI Prompts. DRY for AI Agents.*

Agentic Beacon provides:
1. 🗂️ **A methodology** for managing contexts, knowledge, and skills — the core agentic engineering artifacts worthy of standardization and team-wide distribution
2. 🛠️ **CLI tooling (`abc`)** for initializing warehouses, managing connections, and distributing artifacts across projects

## The Problem

When a team adopts AI coding agents, each project accumulates its own `AGENTS.md` or `.cursorrules`. Standards diverge. A pattern discovered in one repo never reaches the others. When guidelines change, someone copy-pastes updates into 15 repos and misses three.

This is **Context Drift** — the same DRY problem that version control solved for code, except it hasn't been solved yet for agentic engineering artifacts.

- **Reinvention at every project.** Context files get written from scratch for each new repo, with variations that accumulate over time.
- **Knowledge stays siloed.** Lessons learned in one project never leave that developer's laptop.
- **No feedback loop.** When an agent session produces a better approach, there's no workflow to share it.

## How It Works

There are two moving parts:

**Warehouse** — a single git repository owned by your team. It holds the shared source of truth: contexts, knowledge, skills, and agent definitions. Commit it like any other repo.

**Beacon** — a per-project connector. Running `abc warehouse connect` creates `.agentic-beacon/` in your project with a `beacon.yaml` that declares which warehouse artifacts this project needs.

```
Warehouse (shared git repo)                 Your project / global
────────────────────────────                ────────────────────────────────
knowledge/    ── abc sync ──►  .agentic-beacon/artifacts/knowledge/
contexts/     ── abc sync ──►  .agentic-beacon/artifacts/contexts/
                                opencode.json / AGENTS.md (wired)
skills/       ── abc sync ──►  .opencode/skills/<name>/   (all skill files)
                                .opencode/command/<name>/  (slash command)
agents/       ── abc sync ──►  ~/.claude/agents/<name>.md
                                ~/.config/opencode/agents/<name>.md
```

`abc sync` reads `beacon.yaml` and does the full job in one step: copies and wires knowledge and contexts into your agent config, installs skills into each detected tool's directories, and installs agent definitions globally. No live connection to the warehouse is needed during coding sessions.

When a session produces something worth sharing, `abc contribute` copies it back to the warehouse so every project benefits on the next sync.

> See **[Getting Started](./guides/getting-started.md)** for a full walkthrough with examples.

## Artifact Types

Four types form the core of a warehouse, each defined by two axes: **project scope** and **tool specificity**:

|  | Tool-agnostic | Tool-specific |
|---|---|---|
| **Project-scoped** | 📄 Contexts · 🧠 Knowledge | ⚡ Skills |
| **Global** | — | 🤖 Agents |

- **Contexts** — boot instructions and coding standards; wired into `opencode.json` / `AGENTS.md` automatically on sync.
- **Knowledge** — atomic decisions, lessons, and facts; copied to `.agentic-beacon/artifacts/` and referenced from contexts.
- **Skills** — reusable workflows installed as slash commands into each tool's live directories.
- **Agents** — sub-agent definitions installed once into global tool directories (`~/.claude/agents/`, `~/.config/opencode/agents/`) and available across every project.

> See **[Artifact Type Matrix](./docs/artifact-type-matrix.md)** for the full design rationale and how this drives command behaviour.

## Quickstart

### Installation

```bash
# Recommended — install once, use anywhere
uv tool install agentic-beacon

# Alternatives: pipx install agentic-beacon  |  pip install agentic-beacon
# Offline / air-gapped: download a platform bundle from the GitHub Releases page
```

### Get Started

**Starting fresh (no warehouse exists yet)**

```bash
# 1. Create your team warehouse
abc warehouse init my-org-warehouse
cd my-org-warehouse
# add contexts, knowledge, skills — then push to git

# 2. Connect a project
cd ~/my-project
abc warehouse connect --path ~/my-org-warehouse

# 3. Declare what you need and sync
abc setup --manual   # creates beacon.yaml — edit to declare artifacts
abc sync             # copies artifacts, wires agent config, installs agents globally
```

**Joining a team that already has a warehouse**

```bash
git clone git@github.com:your-org/warehouse.git ~/my-org-warehouse

cd ~/my-project
abc warehouse connect --path ~/my-org-warehouse
abc setup --manual
abc sync
```

### Day-to-day Workflow

```
1. abc sync          — pull the latest artifacts from the warehouse
2. code with agent   — agent uses the synced contexts, knowledge, and skills
3. abc delta         — see what has drifted locally (agent-suggested changes)
4. abc contribute    — promote valuable local changes back to the warehouse
5. repeat            — every project stays current; improvements flow both ways
```

## Agentic Beacon vs. Similar Tools

| Tool | What it does |
|------|-------------|
| **Repomix** | Bundles your codebase into a single LLM-readable file |
| **faf-mcp** | Syncs context files locally via MCP |
| **cursorrules.com** | Static directory of community `.cursorrules` files |
| **Langfuse / LLM Ops tools** | Production observability and prompt management for LLM apps |

**Use Agentic Beacon when** you want a version-controlled, team-wide source of truth for agent instructions across multiple projects or repos.

**Not the right fit when** you need a one-off codebase bundle (use Repomix), a single solo project, or production LLM observability (use Langfuse).

## Documentation

### Conceptual Design (docs/)
- **[Artifact Type Matrix](./docs/artifact-type-matrix.md)** — Scope and tool-specificity axes; how they drive command design
- **[Agentic Warehouse Design](./docs/agentic-warehouse-design.md)** — High-level design and architecture
- **[Boot Context Design](./docs/boot-context-design/)** — AGENTS.md architecture and patterns
- **[Spec-Driven Development](./docs/spec-driven-development.md)** — Structured approach to feature planning

### Practical Guides (guides/)
- **[Getting Started](./guides/getting-started.md)** — Full onboarding walkthrough
- **[Warehouse Creation](./guides/warehouse-creation.md)** — Creating and structuring a warehouse
- **[Contributing Back](./guides/warehouse-contribution-guide.md)** — Copy agent improvements back to the warehouse
- **[beacon.yaml Reference](./guides/beacon-yaml-reference.md)** — Full configuration schema
- **[Team Collaboration](./guides/team-collaboration.md)** — Multi-team workflows
- **[Advanced Patterns](./guides/advanced-patterns.md)** — Glob patterns, sync flags, delta workflow

### Examples (examples/)
- **[Sample Warehouse](./examples/sample-warehouse/)** — Output from `abc warehouse init`

## CLI Reference

| Command | Description |
|---------|-------------|
| `abc warehouse init` | Initialize a new warehouse repository |
| `abc warehouse connect` | Connect a project to a warehouse |
| `abc setup` | Create `beacon.yaml` (manual or agent-assisted) |
| `abc sync` | Sync and wire all artifacts declared in `beacon.yaml`; includes agent global install; auto-prunes removed artifacts |
| `abc agents sync` | Sync agent definitions from warehouse into global tool directories; supports `--force` / `--preserve` |
| `abc install <artifact>` | Sync and wire a single artifact (e.g. `abc install skills/code-reviewer`) |
| `abc contribute` | Copy local artifact changes back to the warehouse |
| `abc status` | Show current connection and sync status |
| `abc delta` | Compare local artifacts with warehouse; surfaces project-scoped agents as promotion reminders |
| `abc reset` | Force-overwrite all synced artifacts from the warehouse |
| `abc list` | List synced artifacts; `abc list agents` shows globally installed agents |
| `abc clean` | Remove synced artifacts from the project |

---

If you find Agentic Beacon useful, consider [giving it a star](https://github.com/Shadowsong27/agentic-beacon) — it helps others discover the project.

**Last Updated:** 2026-04-12
