# Agentic Beacon

**An opinionated framework for standardizing and distributing agentic engineering artifacts across teams.**

Agentic Beacon provides:
1. **A methodology** for managing contexts, knowledge, and skills - the core agentic engineering artifacts worthy of standardization and team-wide distribution
2. **CLI tooling (`abc`)** for initializing warehouses, managing connections, and distributing artifacts across projects

> **⚠️ Opinionated Framework:** Agentic Beacon takes a **specific stance** on how to organize and distribute agentic artifacts. This is not a universal standard - it's an opinionated approach based on DRY principles, file-based simplicity, and centralized collaboration. The agentic engineering landscape is rapidly evolving, and this framework provides one possible solution. Evaluate whether this approach fits your team's needs and adapt accordingly.

> **Built for OpenCode:** This design was developed with [OpenCode](https://opencode.ai) usage in mind. While we keep patterns as generic as possible, the experience with other AI coding agents may differ. The core concepts (centralized context, progressive disclosure, DRY) remain applicable across tools.

## 🎯 What is Agentic Beacon?

Agentic Beacon is a **framework** for collaborative AI-assisted development that solves a fundamental problem: **how to share and evolve agentic engineering practices across teams.**

### The Framework Components

**1. Methodology - Artifact Standardization**

Defines three core artifact types that should be centralized and distributed:

- **Contexts** - Boot instructions and coding standards loaded on agent session start
- **Knowledge** - Atomic decisions, lessons, and facts organized by scope (global/language/domain)
- **Skills** - Reusable workflows, procedures, and specialized instructions

These artifacts form a **warehouse** - a single source of truth for your organization's agentic practices.

**2. CLI Tooling - Warehouse Operations**

The `abc` CLI provides practical tools for:

- **Initialization** - Create new warehouses with proper structure (`abc init`)
- **Connection** - Link projects to warehouses (`abc setup`)
- **Distribution** - Install and update artifacts across projects (`abc update`)
- **Discovery** - Find local changes that could benefit other teams (`abc delta`)
- **Management** - Track installed content and maintain sync (`abc status`, `abc clean`)

### Core Principle: Don't Repeat Yourself (DRY)

**DRY for agentic knowledge** - the fundamental philosophy behind this framework.

Instead of duplicating agent instructions, coding standards, and learned patterns across multiple projects, centralize them in a warehouse where:
- **One update propagates everywhere** - Fix a pattern once, all projects benefit
- **Teams learn collectively** - Capture lessons from one project, share with all
- **Onboarding is instant** - New developers and agents inherit organizational knowledge automatically
- **Evolution is natural** - Adapt the structure as practices evolve, without rewriting every project

## 🏗️ Framework Architecture

### Artifact Types

**Contexts** - Instructions loaded at agent boot time
- Global standards applicable to all projects
- Language-specific conventions (Python, TypeScript, etc.)
- Domain-specific patterns (data platforms, web services, etc.)

**Knowledge** - Atomic information units organized hierarchically
- Decisions: Technical choices and rationale
- Lessons: Learnings from agent failures and successes
- Facts: Established configurations and references

**Skills** - Reusable procedures and workflows
- Multi-step processes agents follow
- Specialized instructions for specific tasks
- Templates and automation with usage guides

### Warehouse Structure

The framework defines a standardized repository structure that is created by `abc init`:

```
my-warehouse/              # Created by: abc init my-warehouse
├── contexts/              # Boot context files (loaded via opencode.json)
│   ├── global.md          # Required: Universal standards for all projects
│   ├── python.md          # Optional: Python-specific standards
│   └── data-platform.md   # Optional: Domain-specific patterns
│
├── knowledge/            # Atomic knowledge (facts, decisions, lessons)
│   ├── global/          # Universal knowledge (all projects)
│   │   ├── decisions/
│   │   ├── lessons/
│   │   └── facts/
│   ├── languages/       # Language-specific knowledge
│   │   └── python/      # Configured via --languages flag
│   │       ├── decisions/
│   │       └── lessons/
│   └── domains/         # Domain-specific knowledge
│       └── data-platform/  # Configured via --domains flag
│           ├── decisions/
│           ├── lessons/
│           └── facts/
│
└── skills/              # Reusable workflows and procedures
    └── README.md        # Skills catalog
```

**Create this structure with:**
```bash
abc init my-warehouse \
  --org "Your Organization" \
  --languages python,typescript \
  --domains data-platform
```

**Naming convention:**
- **Warehouse contexts:** Simple filenames (e.g., `global.md`, `python.md`)
- **Project/User level:** Single `AGENTS.md` file by convention

## 🚀 Getting Started

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
uvx --from agentic-beacon abc init my-warehouse
```

### Quick Start with ABC Init

The **fastest way** to create your organization's warehouse is using `abc init`:

```bash
# Initialize your warehouse
abc init my-org-warehouse \
  --org "Acme Corp" \
  --languages python,typescript \
  --domains data-platform,web-services

# Result: Complete warehouse structure created instantly!
```

This creates:
- ✅ Complete directory structure (contexts, knowledge, skills, docs)
- ✅ Placeholder files with instructions
- ✅ Language and domain-specific directories
- ✅ Git repository with initial commit
- ✅ README and documentation

**Next steps:**
1. `cd my-org-warehouse`
2. Customize contexts and knowledge
3. `git remote add origin <your-repo-url>`
4. `git push -u origin main`

### What This Repository Contains

This repository is the **framework source**, containing:

```
agentic-beacon/
├── .github/workflows/    # CI/CD automation
├── docs/                 # Design documentation
├── examples/             # Sample warehouse from abc init
│   └── sample-warehouse/
├── guides/               # User guides
├── knowledge/            # Project-specific knowledge (this project only)
│   ├── decisions/        # Technical decisions for framework development
│   ├── lessons/          # Lessons learned building the framework
│   └── facts/            # Framework development facts
├── libs/beacon/          # CLI source code
├── skills/               # Project-specific skills
│   └── record-knowledge/ # Skill to capture new knowledge
├── AGENTS.md             # Project context (uses progressive disclosure)
├── opencode.json         # Context loading configuration
└── README.md             # This file
```

**Key Components:**
- **CLI source code** - The `abc` tool itself (`libs/beacon/`)
- **Design documentation** - Architecture and methodology guides (`docs/`)
- **Usage guides** - Practical instructions for teams (`guides/`)
- **Examples** - Sample warehouse generated by `abc init` (`examples/`)
- **Project knowledge** - Development decisions, lessons, and facts (`knowledge/`)
- **Project skills** - Development workflows like `record-knowledge` (`skills/`)

**Note on `knowledge/` folder:** This folder contains knowledge specific to developing the Agentic Beacon framework itself. It is NOT a warehouse and NOT meant to be distributed. This project, being the creator of the framework, cannot follow its own distribution model, so we store project-specific knowledge here for agent context.

**Note on `skills/` folder:** Contains project-specific skills for framework development (e.g., `/record-knowledge` to capture new insights). These are NOT example skills for warehouses.

**To create your own warehouse:** Use `abc init` - see `examples/sample-warehouse/` for what it generates.

### For Organizations

1. **Initialize warehouse**: Run `abc init` to create warehouse structure
2. **Customize**: Add your organization's contexts, knowledge, and skills
3. **Share**: Teams install `agentic-beacon` and use `abc setup` in projects
4. **Optional**: Host internally on private PyPI (see [private deployment guide](./libs/beacon/PRIVATE_DEPLOYMENT.md))

### For Teams

1. **Install**: `pip install agentic-beacon`
2. **Setup projects**: `abc setup --warehouse ~/warehouse --all`
3. **Stay in sync**: `abc update` to get latest changes
4. **Contribute**: Use `abc delta` to find new patterns to share

## 📚 Documentation

### Conceptual Design (docs/)
- **[Agentic Warehouse Design](./docs/agentic-warehouse-design.md)** - High-level design and architecture
- **[Boot Context Design](./docs/boot-context-design/)** - AGENTS.md architecture and patterns
  - [Three-Tier Context Model](./docs/boot-context-design/agents-md-architecture.md)
  - [Project-Level AGENTS.md Design](./docs/boot-context-design/project-level-agents-design.md)
- **[Spec-Driven Development](./docs/spec-driven-development.md)** - Structured approach to feature planning and implementation

### Practical Guides (guides/)
- **[CLI Quick Start](./guides/cli-quick-start.md)** - Installation and usage guide
- **[Warehouse Contribution Guide](./guides/warehouse-contribution-guide.md)** - How to contribute to your organization's warehouse

### Examples (examples/)
- **[Sample Warehouse](./examples/sample-warehouse/)** - Example output from `abc init` showing the complete warehouse structure with placeholders

## 🏗️ Organizing Your Warehouse

Once you create a warehouse with `abc init`, organize content using a **two-tier approach** (contexts + knowledge). See the [design guide](./docs/agentic-warehouse-design.md#understanding-the-two-tier-structure-context--knowledge) for full explanation.

### Contexts Directory
- **Global** (`global.md`): Universal practices for all projects
- **Language** (`python.md`, `typescript.md`, etc.): Language-specific standards
- **Domain** (`data-platform.md`, `web-app.md`, etc.): Team/domain-specific patterns

**Naming note:** Warehouse context files use simple names. The `opencode.json` configuration determines which files are loaded.

### Knowledge Directory
- **Decisions**: Technical choices and their rationale
- **Lessons**: Common agent failure modes and guardrails
- **Facts**: Established technical information and configurations

**Organization:** Knowledge mirrors context structure (global/, languages/, domains/) for selective import.

### Skills Directory
- **Procedural workflows**: Multi-step processes agents follow
- **Context injections**: Specialized instructions for specific tasks
- **Templates**: Structured documents or code patterns
- **Tools**: Scripts and automation with usage guides

## 🔄 Typical Workflow

Once you've created your organization's warehouse:

1. **Setup**: Teams install contexts and skills into their projects using `abc setup`
2. **Use**: Agents load contexts automatically on session start
3. **Update**: Teams sync latest changes from warehouse using `abc update`
4. **Contribute**: Teams submit improvements back via pull requests

See the [Warehouse Contribution Guide](./guides/warehouse-contribution-guide.md) for details.

## 🛠️ CLI Tooling - Agentic Beacon (abc)

This repository includes **Agentic Beacon CLI**, a Python tool for distributing contexts, knowledge, and skills to projects.

**Command:** `abc` (short for "Agentic Beacon CLI")  
**Brand:** "Guide your agents with distributed knowledge"

### Installation

```bash
# Install from PyPI
pip install agentic-beacon
```

**For development:**

```bash
# From source
git clone https://github.com/Shadowsong27/agentic-beacon.git
cd agentic-beacon/libs/beacon
pip install -e .
```

### Quick Start

```bash
# List available content in warehouse
abc list

### Quick Start

```bash
# Initialize a new warehouse
abc init my-warehouse \
  --org "Your Organization" \
  --languages python,typescript \
  --domains data-platform

# List available content in warehouse
abc list

# Setup in your project (interactive mode)
cd ~/your-project
abc setup --warehouse ~/your-warehouse --interactive

# Or install everything
abc setup --warehouse ~/your-warehouse --all

# Check what's installed
abc status

# Compare with warehouse (find local changes)
abc delta --warehouse ~/your-warehouse

# Update from warehouse
abc update --warehouse ~/your-warehouse

# Remove installation
abc clean
```

### Commands

| Command | Description |
|---------|-------------|
| `abc init` | **NEW** - Initialize a new warehouse repository |
| `abc list` | List all available warehouse content |
| `abc setup` | Install contexts/knowledge/skills to `.opencode/` |
| `abc status` | Show currently installed content |
| `abc delta` | Compare target with warehouse to find differences |
| `abc update` | Sync latest changes from warehouse |
| `abc clean` | Remove `.opencode/` directory |

### Init Command (New!)

The `abc init` command creates a complete warehouse structure:

```bash
abc init my-warehouse --org "Acme Corp" --languages python,typescript --domains data-platform
```

**Creates:**
- ✅ Complete directory structure (contexts/, knowledge/, skills/, docs/)
- ✅ Placeholder files with detailed instructions
- ✅ Language-specific directories (e.g., knowledge/languages/python/)
- ✅ Domain-specific directories (e.g., knowledge/domains/data-platform/)
- ✅ Git repository with initial commit
- ✅ README and documentation

**Interactive mode:**
```bash
abc init my-warehouse
? Organization name: Acme Corp
? Primary languages (comma-separated): python, typescript
? Primary domains (comma-separated): data-platform, web-services
? Initialize git repository? [Y/n]: y
✓ Warehouse initialized successfully!
```

### Delta Command

The `abc delta` command helps you track changes and contributions:

```bash
abc delta --warehouse ~/warehouse
```

**Shows:**
- ✅ **New files** in your project (potential contributions back to warehouse)
- ⚠️  **Modified files** in your project (local customizations)
- ℹ️  **Missing files** in your project (available in warehouse but not installed)

**Use cases:**
- Before contributing: See what new patterns you've created
- After customizing: Understand your local changes
- Regular audits: Keep your project in sync with warehouse

### Deployment

**Published on PyPI:**

```bash
pip install agentic-beacon
```

**For Organizations (Optional Private Deployment):**

If you want to host internally, see [Private Deployment Guide](./libs/beacon/PRIVATE_DEPLOYMENT.md) for instructions on publishing to your own PyPI server.

### Documentation

- **[Quick Start Guide](./libs/beacon/QUICKSTART.md)** - Get started in 5 minutes
- **[Complete README](./libs/beacon/README.md)** - Full CLI documentation
- **[Private Deployment](./libs/beacon/PRIVATE_DEPLOYMENT.md)** - Deploy to private PyPI (optional)
- **[Project Status](./libs/beacon/PROJECT_COMPLETE.md)** - Implementation details

### Technical Details

- **Package Name:** `agentic-beacon`
- **CLI Command:** `abc`
- **Python Required:** `>=3.12`
- **License:** MIT
- **Dependencies:** click, rich, pyyaml, loguru

### Workflow Example

```bash
# 1. Install agentic-beacon
pip install agentic-beacon

# 2. Initialize warehouse
abc init my-org-warehouse --org "Acme Corp"

# 3. Developers use in projects
cd ~/my-project
abc setup --warehouse ~/my-org-warehouse --all
echo ".opencode/" >> .gitignore

# 4. Check for contributions
abc delta
# Shows new files that could be contributed back

# 5. Stay in sync
abc update
```

## 📋 License

[Your License Here]

---

**Template Version:** 1.0.0  
**Last Updated:** 2026-03-07
