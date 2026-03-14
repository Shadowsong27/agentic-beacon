# 🚀 Agentic Beacon

**An opinionated framework for standardizing and distributing agentic engineering artifacts across teams.**

Agentic Beacon provides:
1. 🗂️ **A methodology** for managing contexts, knowledge, and skills - the core agentic engineering artifacts worthy of standardization and team-wide distribution
2. 🛠️ **CLI tooling (`abc`)** for initializing warehouses, managing connections, and distributing artifacts across projects

> **Opinionated Framework:** Agentic Beacon takes a **specific stance** on how to organize and distribute agentic artifacts. This is not a universal standard - it's an opinionated approach based on DRY principles, file-based simplicity, and centralized collaboration. The agentic engineering landscape is rapidly evolving, and this framework provides one possible solution. Evaluate whether this approach fits your team's needs and adapt accordingly.

> **Built for OpenCode:** This design was developed with [OpenCode](https://opencode.ai) usage in mind. While we keep patterns as generic as possible, the experience with other AI coding agents may differ. The core concepts (centralized context, progressive disclosure, DRY) remain applicable across tools. If you use a different coding agent and hit limitations or have ideas for improving compatibility, [open an issue](https://github.com/Shadowsong27/agentic-beacon/issues) — contributions are very welcome.

## The Problem

When a team starts using AI coding agents, each developer independently figures out how to prompt their agent — what context to provide, what coding standards to enforce, what patterns to follow. This knowledge lives in individual `AGENTS.md` files, system prompts, and personal configs that are never shared.

The result:

- **Reinvention at every project.** The same context files get written from scratch for each new repo, with slight variations that accumulate over time.
- **Knowledge stays siloed.** When one developer discovers the right way to phrase a Python convention, or learns that a certain agent pattern causes issues, that lesson never leaves their laptop.
- **Context drift.** Copy-pasted `AGENTS.md` files diverge. Projects that started identical now describe conflicting standards. No one knows which is authoritative.
- **Painful onboarding.** New team members (and new agents) start with nothing. The organization's accumulated agentic knowledge isn't anywhere they can find it.
- **No feedback loop.** When an agent session produces a better approach, there's no workflow to promote that improvement back to the rest of the team.

This is the same DRY problem that version control solved for code — except it hasn't been solved yet for agentic engineering artifacts.

## What is Agentic Beacon?

Agentic Beacon is a **framework** for collaborative AI-assisted development that solves a fundamental problem: **how to share and evolve agentic engineering practices across teams.**

### How It Works

There are two moving parts:

**Warehouse** — a single git repository owned by your team or organisation. It holds the shared source of truth: contexts, knowledge, and skills. You create one warehouse per team and commit it like any other repo.

**Beacon** — a per-project connector. When you run `abc warehouse connect` in a project, it creates a `.agentic-beacon/` directory containing:
- `beacon.yaml` — declares which warehouse artifacts this project needs
- `artifacts/` — a local snapshot of those artifacts, populated by `abc sync`

The flow is:

```
Warehouse (shared git repo)                 Your project
────────────────────────────                ────────────────────────────────
contexts/                   ── abc sync ──► .agentic-beacon/artifacts/
knowledge/                                  opencode.json / AGENTS.md (wired)
skills/
```

`abc sync` reads `beacon.yaml`, copies the declared artifacts into `.agentic-beacon/artifacts/`, and wires contexts and skills into your agent config automatically. Your agent reads from the local snapshot — no live connection to the warehouse required during coding sessions.

When a session produces something worth sharing — a better pattern, a new lesson — `abc contribute` copies it back to the warehouse so every project benefits next sync.

### The Framework Components

**1. 📐 Methodology - Artifact Standardization**

Defines three core artifact types that should be centralized and distributed:

- 📄 **Contexts** - Boot instructions and coding standards loaded on agent session start
- 🧠 **Knowledge** - Atomic decisions, lessons, and facts
- ⚡ **Skills** - Reusable workflows, procedures, and specialized instructions

These artifacts form a **warehouse** - a single source of truth for your organization's agentic practices.

**2. 💻 CLI Tooling - Warehouse Operations**

The `abc` CLI provides practical tools for:

- **Initialization** - Create new warehouses with proper structure (`abc warehouse init`)
- **Connection** - Link projects to warehouses (`abc warehouse connect`)
- **Distribution** - Sync artifacts to projects (`abc sync`)
- **Skill Installation** - Register synced skills as slash commands in your agent (`abc skill install`)
- **Contribution** - Copy agent-improved artifacts back to the warehouse (`abc contribute`)
- **Discovery** - Find local changes that could benefit other teams (`abc delta`)
- **Management** - Track installed content and maintain sync (`abc status`, `abc update`, `abc clean`)

### 🔁 Core Principle: Don't Repeat Yourself (DRY)

**DRY for agentic knowledge** - the fundamental philosophy behind this framework.

Instead of duplicating agent instructions, coding standards, and learned patterns across multiple projects, centralize them in a warehouse where:
- **One update propagates everywhere** - Fix a pattern once, all projects benefit
- **Teams learn collectively** - Capture lessons from one project, share with all
- **Onboarding is instant** - New developers and agents inherit organizational knowledge automatically
- **Evolution is natural** - Adapt the structure as practices evolve, without rewriting every project

### 🪶 Design Philosophy: Intentionally Lightweight

**Why markdown files and Git instead of a database or RAG system?**

Organizational coding standards are curated, structured, and small — typically hundreds of KB, not gigabytes. Agents don't need to search for relevant knowledge; context files tell them explicitly what to read and when. Plain files and Git are sufficient, easier to adopt, and require no infrastructure.

**Why keep the framework itself minimal?**

The agentic engineering landscape is shifting rapidly. What's best practice today may be superseded in months — by new agent capabilities, new tool conventions, or new paradigms entirely. Agentic Beacon is deliberately lightweight so that:
- Teams can adopt it without committing to heavy infrastructure
- If something better comes along, the exit cost is low — it's just markdown files
- The inner structure of your warehouse is yours to decide; the framework only prescribes three top-level directories

> For the full reasoning, see [Why This Exists: Three Questions](./docs/agentic-warehouse-design.md#why-this-exists-three-questions) in the design docs.

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

### Warehouse Structure

The framework defines three top-level directories (`contexts/`, `knowledge/`, `skills/`) and creates a starter structure with `abc warehouse init`. **The internal layout within each directory is entirely yours to decide** — the example below is one suggested starting point, not a prescription.

```
my-warehouse/              # Created by: abc warehouse init my-warehouse
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

## 🚦 Getting Started

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

### Quick Start

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
abc sync             # copies artifacts into the project and wires your agent config
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
| `abc sync` | Sync artifacts declared in `beacon.yaml` to the project |
| `abc skill install` | Register synced skills as slash commands for your agent |
| `abc contribute` | Copy local artifact changes back to the warehouse |
| `abc status` | Show current connection and sync status |
| `abc delta` | Compare synced artifacts with warehouse (find local changes) |
| `abc update` | Re-sync and overwrite local artifacts from warehouse |
| `abc list` | List available content in the connected warehouse |
| `abc clean` | Remove synced artifacts from the project |

## 🏢 For Organizations

1. **Initialize warehouse**: `abc warehouse init` to create structure
2. **Customize**: Add your organization's contexts, knowledge, and skills
3. **Share**: Teams install `agentic-beacon` and use `abc warehouse connect` in projects
4. **Optional**: Host internally on private PyPI (see [Private Deployment Guide](./libs/beacon/PRIVATE_DEPLOYMENT.md))

## 👥 For Teams

1. **Install**: `uv tool install agentic-beacon`
2. **Connect**: `abc warehouse connect --path ~/your-warehouse`
3. **Configure**: `abc setup --manual` then edit `beacon.yaml`
4. **Sync**: `abc sync`
5. **Install skills**: `abc skill install --all` to register skills as agent slash commands
6. **Contribute**: `abc contribute --all` to share agent improvements back to the warehouse
7. **Stay current**: `abc update` after warehouse changes

## 🔧 Technical Details

- **Package Name:** `agentic-beacon`
- **CLI Command:** `abc`
- **Python Required:** `>=3.12`
- **License:** MIT
- **Dependencies:** click, rich, pyyaml, loguru

---

**Last Updated:** 2026-03-10
