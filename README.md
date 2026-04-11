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
1. 🗂️ **A methodology** for managing contexts, knowledge, and skills - the core agentic engineering artifacts worthy of standardization and team-wide distribution
2. 🛠️ **CLI tooling (`abc`)** for initializing warehouses, managing connections, and distributing artifacts across projects

## The Problem

Imagine your team has 15 microservices. Each one has its own `.cursorrules` or `CLAUDE.md`. When your API naming guidelines change, you copy-paste the update into 15 repos. Miss one, and that service's agent starts giving inconsistent advice. Three months later, no one knows which version is correct.

This is **Context Drift** — and it gets worse as your team and codebase grow.

When a team starts using AI coding agents, each developer independently figures out how to prompt their agent — what context to provide, what coding standards to enforce, what patterns to follow. This knowledge lives in individual `AGENTS.md` files, system prompts, and personal configs that are never shared.

The result:

- **Reinvention at every project.** The same context files get written from scratch for each new repo, with slight variations that accumulate over time.
- **Knowledge stays siloed.** When one developer discovers the right way to phrase a Python convention, or learns that a certain agent pattern causes issues, that lesson never leaves their laptop.
- **Context drift at scale.** Copy-pasted files diverge across 5, 10, 50 repos. Projects that started identical now describe conflicting standards. No one knows which is authoritative.
- **Painful onboarding.** New team members (and new agents) start with nothing. The organization's accumulated agentic knowledge isn't anywhere they can find it.
- **No feedback loop.** When an agent session produces a better approach, there's no workflow to promote that improvement back to the rest of the team.

This is the same DRY problem that version control solved for code — except it hasn't been solved yet for agentic engineering artifacts.

## What is Agentic Beacon?

Agentic Beacon is a **framework** for collaborative AI-assisted development that solves a fundamental problem: **how to share and evolve agentic engineering practices across teams.**

### How It Works

There are two moving parts:

**Warehouse** — a single git repository owned by your team or organisation. It holds the shared source of truth: contexts, knowledge, and skills. You create one warehouse per team and commit it like any other repo.

**Beacon** — a per-project connector. When you run `abc warehouse connect` in a project, it creates a `.agentic-beacon/` directory containing:
- `beacon.yaml` — declares which warehouse artifacts this project needs (knowledge, contexts, skills, agents)
- `artifacts/` — a local snapshot of those artifacts, populated by `abc sync`

The flow is:

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

`abc sync` reads `beacon.yaml` and does the full job: copies knowledge and contexts into `.agentic-beacon/artifacts/` and wires them into your agent config, installs skills (tracked as directories — all companion files included) into your agent's skill and command folders, and installs agent definitions globally for immediate use. No live connection to the warehouse is required during coding sessions.

If an artifact was previously synced but has since been removed from `beacon.yaml`, `abc sync` detects it and prompts before deleting — preventing accidental data loss. If an artifact has local modifications, you are prompted before it is overwritten (use `--force` to bypass or `--preserve` to skip).

Skills can also be suppressed from `abc delta` and `abc contribute` using an `ignore` section in `beacon.yaml` — useful for externally-managed skills you don't want to track:

```yaml
ignore:
  skills:
    - "openspec-*"
```

**Example — after `abc sync` with OpenCode:**

`opencode.json` (auto-updated):
```json
{
  "instructions": [
    ".agentic-beacon/artifacts/contexts/global.md",
    ".agentic-beacon/artifacts/contexts/python.md"
  ]
}
```

`.opencode/command/code-review.md` (slash command stub, auto-created):
```markdown
---
description: Run a structured code review
---

Use the **skill** tool to load and execute the `code-review` skill with any provided arguments.
```

OpenCode picks up the contexts automatically on session start, and `/code-review` becomes available as a slash command immediately.

When a session produces something worth sharing — a better pattern, a new lesson — `abc contribute` copies it back to the warehouse so every project benefits next sync.

### The Framework Components

Four artifact types form the core of a warehouse:

- 📄 **Contexts** - Boot instructions and coding standards loaded at agent session start
- 🧠 **Knowledge** - Atomic decisions, lessons, and facts
- ⚡ **Skills** - Reusable workflows and procedures available as slash commands
- 🤖 **Agents** - Sub-agent definitions installed globally to all detected AI tools

The `abc` CLI handles the rest: initializing warehouses, connecting projects, syncing artifacts, and contributing improvements back. Everything is plain markdown files in Git — no infrastructure required.

> For a deeper look at the design rationale, see [Agentic Warehouse Design](./docs/agentic-warehouse-design.md).

## 🏗️ Framework Architecture

### Artifact Types

📄 **Contexts** - Instructions loaded at agent boot time
- Global standards applicable to all projects
- Language-specific conventions (Python, TypeScript, etc.)
- Any other grouping that makes sense for your team

🧠 **Knowledge** - Atomic information units
- Decisions: Technical choices and rationale
- Lessons: Learnings from agent failures and successes
- Facts: Established configurations and references

⚡ **Skills** - Reusable procedures and workflows
- Multi-step processes agents follow
- Specialized instructions for specific tasks
- Templates and automation with usage guides

🤖 **Agents** - Sub-agent definitions (installed globally)
- Specialized agents for recurring tasks (e.g. code reviewer, test writer)
- Installed to `~/.claude/agents/` and `~/.config/opencode/agents/` on sync
- Available across all projects without per-project configuration

### Warehouse Structure

The framework defines three top-level directories (`contexts/`, `knowledge/`, `skills/`) and creates a starter structure with `abc warehouse init`. **The internal layout within each directory is entirely yours to decide** — the example below is one suggested starting point, not a prescription.

```
my-warehouse/              # Created by: abc warehouse init my-warehouse
├── agents/                # Sub-agent definitions (installed globally)
│   └── README.md          # Agents catalog
│
├── contexts/              # Boot context files (loaded via opencode.json)
│   ├── global.md          # e.g. universal standards for all projects
│   ├── python.md          # e.g. language-specific standards
│   └── data-platform.md   # e.g. any grouping that fits your team
│
├── knowledge/             # Atomic knowledge (facts, decisions, lessons)
│   ├── global/            # e.g. universal knowledge
│   │   ├── decisions/
│   │   ├── lessons/
│   │   └── facts/
│   ├── languages/         # e.g. language-specific knowledge
│   │   └── python/
│   └── domains/           # e.g. grouping by problem area — but organise
│       └── data-platform/ #     however suits your team (by service, tribe,
│                          #     tech stack, etc.)
└── skills/                # Reusable workflows and procedures
    └── README.md          # Skills catalog
```

> **On "domains":** The `domains/` grouping in the example above is one way to organise knowledge — by business or technical problem area (e.g. `data-platform`, `web-services`). It is not a required concept. Use it, rename it, or replace it entirely with whatever structure your team finds natural.

**Naming convention:**
- **Warehouse contexts:** Simple filenames (e.g., `global.md`, `python.md`)
- **Project/User level:** Single `AGENTS.md` file by convention

## Quickstart

### Installation

**Recommended: Install with uv (if you have uv installed)**
```bash
# Install once, use anywhere
uv tool install agentic-beacon

# Verify installation
abc --help
```

**Offline / private install (no PyPI access required)**

Each release ships a pre-built bundle zip for the three major platforms. The zip contains the package and all its dependencies as wheels — no internet needed on the target machine.

1. Go to the [GitHub Releases page](https://github.com/Shadowsong27/agentic-beacon/releases) and download the bundle zip matching your OS:
   - `agentic_beacon-X.Y.Z-bundle-linux-x86_64.zip`
   - `agentic_beacon-X.Y.Z-bundle-macos-arm64.zip`
   - `agentic_beacon-X.Y.Z-bundle-windows-x86_64.zip`

2. Unzip and install:
```bash
unzip agentic_beacon-X.Y.Z-bundle-<platform>.zip -d abc-bundle
uv tool install agentic-beacon --no-index --find-links ./abc-bundle/

# Verify
abc --version
```

**Alternative methods:**
```bash
# Using pipx (isolated environment)
pipx install agentic-beacon

# Using pip (global Python environment)
pip install agentic-beacon

# One-off execution without installation (using uvx)
uvx --from agentic-beacon abc warehouse init my-warehouse
```

### Get Started

**Scenario A — Starting fresh (no warehouse exists yet)**

```bash
uv tool install agentic-beacon

# 1. Create your team warehouse
abc warehouse init my-org-warehouse
cd my-org-warehouse
# add your contexts, knowledge, and skills, then push to git

# 2. In each project, connect to the warehouse
cd ~/my-project
abc warehouse connect --path ~/my-org-warehouse

# 3. Declare what you need and sync
abc setup --manual   # creates .agentic-beacon/beacon.yaml — edit to declare artifacts
abc sync             # copies artifacts into the project, wires agent config, installs agents globally
```

**Scenario B — Warehouse already exists (joining your team's setup)**

```bash
uv tool install agentic-beacon

# 1. Clone the warehouse locally
git clone git@github.com:your-org/warehouse.git ~/my-org-warehouse

# 2. In your project, connect and sync
cd ~/my-project
abc warehouse connect --path ~/my-org-warehouse
abc setup --manual   # edit .agentic-beacon/beacon.yaml to declare what you need
abc sync
```

See **[Getting Started](./guides/getting-started.md)** for the full walkthrough.

### Day-to-day Workflow

After initial setup, the ongoing loop is straightforward:

```
1. abc sync          — pull the latest artifacts from the warehouse into your project
2. code with agent   — agent uses the synced contexts, knowledge, and skills
3. abc delta         — see what has drifted locally (agent-suggested changes, improvements)
4. abc contribute    — promote valuable local changes back to the warehouse
5. repeat            — every project stays current; improvements flow in both directions
```

Add new knowledge, skills, or contexts directly to the warehouse repo and commit — the next `abc sync` in any connected project picks them up.

### What This Repository Contains

This repository is the **framework source**, not a warehouse:

```
agentic-beacon/
├── .github/workflows/    # CI/CD automation
├── docs/                 # Design documentation
├── examples/             # Sample warehouse from abc warehouse init
│   └── sample-warehouse/
├── guides/               # User guides
├── knowledge/            # Project-specific knowledge (this project only)
│   ├── decisions/
│   ├── lessons/
│   └── facts/
├── libs/beacon/          # CLI source code
├── skills/               # Project-specific skills (README only)
├── AGENTS.md             # Project context (uses progressive disclosure)
├── opencode.json         # Context loading configuration
└── README.md             # This file
```

**To create your own warehouse:** Use `abc warehouse init` — see `examples/sample-warehouse/` for what it generates.

> **Note on `knowledge/` and `skills/`:** These folders contain artifacts specific to developing the Agentic Beacon framework itself. They are **not** a warehouse and not meant to be distributed to other projects.

## Agentic Beacon vs. Similar Tools

The AI context management space is growing. Here's how Agentic Beacon compares:

| Tool | What it does |
|------|-------------|
| **Repomix** | Bundles your codebase into a single LLM-readable file |
| **faf-mcp** | Syncs context files locally via MCP |
| **cursorrules.com** | Static directory of community `.cursorrules` files |
| **Langfuse / LLM Ops tools** | Production observability and prompt management for LLM apps |

**Use Agentic Beacon when:**
- You want a version-controlled, team-wide source of truth for agent instructions
- You're managing context files across multiple projects or repos
- You want automation to keep every project's agent instructions in sync

**Agentic Beacon is not the right fit when:**
- You need to bundle your codebase for a one-off LLM query (use Repomix)
- You're setting up a single project for yourself with no team sharing needs
- You need production LLM observability or prompt management (use Langfuse)

## 📚 Documentation

### Conceptual Design (docs/)
- **[Agentic Warehouse Design](./docs/agentic-warehouse-design.md)** - High-level design and architecture
- **[Boot Context Design](./docs/boot-context-design/)** - AGENTS.md architecture and patterns
  - [Three-Tier Context Model](./docs/boot-context-design/agents-md-architecture.md)
  - [Project-Level AGENTS.md Design](./docs/boot-context-design/project-level-agents-design.md)
- **[Spec-Driven Development](./docs/spec-driven-development.md)** - Structured approach to feature planning

### Practical Guides (guides/)
- **[Getting Started](./guides/getting-started.md)** - Full onboarding walkthrough
- **[Warehouse Creation](./guides/warehouse-creation.md)** - Creating and structuring a warehouse
- **[Contributing Back](./guides/warehouse-contribution-guide.md)** - Copy agent improvements back to the warehouse
- **[beacon.yaml Reference](./guides/beacon-yaml-reference.md)** - Full configuration schema
- **[Team Collaboration](./guides/team-collaboration.md)** - Multi-team workflows
- **[Advanced Patterns](./guides/advanced-patterns.md)** - Glob patterns, sync flags, delta workflow

### Examples (examples/)
- **[Sample Warehouse](./examples/sample-warehouse/)** - Example output from `abc warehouse init`

## ⌨️ CLI Reference

### Commands

| Command | Description |
|---------|-------------|
| `abc warehouse init` | Initialize a new warehouse repository |
| `abc warehouse connect` | Connect a project to a warehouse |
| `abc setup` | Create `beacon.yaml` (manual or agent-assisted) |
| `abc sync` | Sync and wire all artifacts declared in `beacon.yaml` (knowledge, contexts, skills, agents); includes agent global install; auto-prunes removed artifacts |
| `abc agents sync` | Sync all agent definitions from warehouse into global tool directories (`~/.claude/agents/`, `~/.config/opencode/agents/`); supports `--force` / `--preserve` |
| `abc install <artifact>` | Sync and wire a single artifact (e.g. `abc install skills/code-reviewer`, `abc install agents/reviewer.md`) |
| `abc contribute` | Copy local artifact changes back to the warehouse (supports agents, `--exclude-unregistered`) |
| `abc status` | Show current connection and sync status |
| `abc delta` | Compare synced artifacts with warehouse; dedicated agents section shows MISSING/IDENTICAL/MODIFIED/STALE per tool; surfaces project-scoped agents as promotion reminders |
| `abc reset` | Force-overwrite all synced artifacts from the warehouse (replaces `abc update`) |
| `abc list` | List synced artifacts; `abc list agents` shows globally installed agents |
| `abc clean` | Remove synced artifacts from the project |

---

If you find Agentic Beacon useful, consider [giving it a star](https://github.com/Shadowsong27/agentic-beacon) — it helps others discover the project.

**Last Updated:** 2026-04-12
