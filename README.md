# 🚀 Agentic Beacon

**An opinionated framework for standardizing and distributing agentic engineering artifacts across teams.**

Agentic Beacon provides:
1. 🗂️ **A methodology** for managing contexts, knowledge, and skills - the core agentic engineering artifacts worthy of standardization and team-wide distribution
2. 🛠️ **CLI tooling (`abc`)** for initializing warehouses, managing connections, and distributing artifacts across projects

> **Opinionated Framework:** Agentic Beacon takes a **specific stance** on how to organize and distribute agentic artifacts. This is not a universal standard - it's an opinionated approach based on DRY principles, file-based simplicity, and centralized collaboration. The agentic engineering landscape is rapidly evolving, and this framework provides one possible solution. Evaluate whether this approach fits your team's needs and adapt accordingly.

> **Built for OpenCode:** This design was developed with [OpenCode](https://opencode.ai) usage in mind. While we keep patterns as generic as possible, the experience with other AI coding agents may differ. The core concepts (centralized context, progressive disclosure, DRY) remain applicable across tools. If you use a different coding agent and hit limitations or have ideas for improving compatibility, [open an issue](https://github.com/Shadowsong27/agentic-beacon/issues) — contributions are very welcome.

## What is Agentic Beacon?

Agentic Beacon is a **framework** for collaborative AI-assisted development that solves a fundamental problem: **how to share and evolve agentic engineering practices across teams.**

### The Framework Components

**1. 📐 Methodology - Artifact Standardization**

Defines three core artifact types that should be centralized and distributed:

- 📄 **Contexts** - Boot instructions and coding standards loaded on agent session start
- 🧠 **Knowledge** - Atomic decisions, lessons, and facts organized by scope (global/language/domain)
- ⚡ **Skills** - Reusable workflows, procedures, and specialized instructions

These artifacts form a **warehouse** - a single source of truth for your organization's agentic practices.

**2. 💻 CLI Tooling - Warehouse Operations**

The `abc` CLI provides practical tools for:

- **Initialization** - Create new warehouses with proper structure (`abc warehouse init`)
- **Connection** - Link projects to warehouses (`abc warehouse connect`)
- **Distribution** - Sync artifacts to projects (`abc sync`)
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
- Domain-specific patterns (data platforms, web services, etc.)

🧠 **Knowledge** - Atomic information units organized hierarchically
- Decisions: Technical choices and rationale
- Lessons: Learnings from agent failures and successes
- Facts: Established configurations and references

⚡ **Skills** - Reusable procedures and workflows
- Multi-step processes agents follow
- Specialized instructions for specific tasks
- Templates and automation with usage guides

### Warehouse Structure

The framework defines three top-level directories and creates a starter structure with `abc warehouse init`. **The internal layout within each directory is not prescribed** — this is a suggested starting point. Teams should organize their knowledge, skills, and contexts in whatever way makes sense for them.

```
my-warehouse/              # Created by: abc warehouse init my-warehouse
├── contexts/              # Boot context files (loaded via opencode.json)
│   ├── global.md          # Required: Universal standards for all projects
│   ├── python.md          # Optional: Python-specific standards
│   └── data-platform.md   # Optional: Domain-specific patterns
│
├── knowledge/             # Atomic knowledge (facts, decisions, lessons)
│   ├── global/            # Universal knowledge (all projects)
│   │   ├── decisions/
│   │   ├── lessons/
│   │   └── facts/
│   ├── languages/         # Language-specific knowledge
│   │   └── python/
│   │       ├── decisions/
│   │       └── lessons/
│   └── domains/           # Domain-specific knowledge
│       └── data-platform/
│           ├── decisions/
│           ├── lessons/
│           └── facts/
│
└── skills/                # Reusable workflows and procedures
    └── README.md          # Skills catalog
```

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

```bash
# Install
uv tool install agentic-beacon

# Connect your project to a warehouse
abc warehouse connect --path ~/my-org-warehouse

# Create your artifact config and sync
abc setup --manual   # then edit .agentic-beacon/beacon.yaml
abc sync
```

See **[Getting Started](./guides/getting-started.md)** for the full walkthrough, including how to create a warehouse from scratch.

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
├── skills/               # Project-specific skills
│   └── record-knowledge/
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
5. **Stay current**: `abc update` after warehouse changes
6. **Contribute**: Use `abc delta` to find new patterns worth sharing back

## 🔧 Technical Details

- **Package Name:** `agentic-beacon`
- **CLI Command:** `abc`
- **Python Required:** `>=3.12`
- **License:** MIT
- **Dependencies:** click, rich, pyyaml, loguru

---

**Last Updated:** 2026-03-10
