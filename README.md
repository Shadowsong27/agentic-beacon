# Agentic Beacon

**Agentic Beacon CLI (abc)** - A tool for distributing knowledge contexts, skills, and standards across AI-assisted development teams.

> **Note:** This is an **opinionated and simple take** on agentic engineering. The landscape is rapidly evolving, and this approach provides one possible solution focused on DRY principles and centralized collaboration. Adapt it to your team's needs.

> **Built for OpenCode:** This design was developed with [OpenCode](https://opencode.ai) usage in mind. While we keep patterns as generic as possible, the experience with other AI coding agents may differ. The core concepts (centralized context, progressive disclosure, DRY) remain applicable across tools.

## 🎯 Purpose

**Agentic engineering is rapidly evolving.** Vibe coding practices, AI agent capabilities, and collaboration paradigms shift weekly. Rather than prescribing rigid methodologies that quickly become outdated, this template provides a **minimal, flexible structure** for teams to collaborate effectively.

**The core principle: Don't Repeat Yourself (DRY) for agentic knowledge.**

Instead of duplicating agent instructions, coding standards, and learned patterns across multiple projects, centralize them in a warehouse where:
- **One update propagates everywhere** - Fix a pattern once, all projects benefit
- **Teams learn collectively** - Capture lessons from one project, share with all
- **Onboarding is instant** - New developers and agents inherit organizational knowledge automatically
- **Evolution is natural** - Adapt the structure as practices evolve, without rewriting every project

This template provides just enough structure to enable collaboration without constraining how your team works with AI agents.

### Why Simple File-Based Distribution?

**Agentic coding doesn't need RAG complexity.** Unlike production systems requiring millisecond context retrieval, agents in development environments can afford simple file reads. Our approach:

**Simple and adoptable:**
- Plain markdown files (no vector databases)
- Standard file operations (no embedding pipelines)
- Git-based versioning (familiar workflow)
- Zero infrastructure overhead

**Fast enough for the use case:**
- Boot context loads in milliseconds (AGENTS.md files)
- Knowledge files accessed on-demand via pointers
- Progressive disclosure reduces cognitive load
- Agents already spend time reading code - context files add negligible overhead

**Right-sized for organizational standards:**
- Warehouse stores curated knowledge (~100s of KB, not GBs)
- Content is explicitly structured, not semantically searched
- Updates are infrequent (standards evolve slowly)
- Human-readable for review and contribution

**RAG would be overkill** for this use case:
- Complex setup (vector DB, embeddings, indexing)
- Higher maintenance burden
- Adoption barrier for teams
- Unnecessary for small, curated content sets

When you need RAG (we don't): Semantic search across massive, rapidly-changing content where explicit pointers don't scale. For organizational standards distribution, simple beats complex.

## 📁 Repository Structure

```
agentic-engineering-warehouse-template/
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
│   │   └── python/      # Example: Replace with your languages
│   │       ├── decisions/
│   │       └── lessons/
│   └── domains/         # Domain-specific knowledge
│       └── data-platform/  # Example: Replace with your domains
│           ├── decisions/
│           ├── lessons/
│           └── facts/
│
└── skills/              # Reusable workflows and procedures
    ├── README.md        # Skills catalog (agent-maintained)
    └── example-skill/   # Example: Replace with your skills
        └── SKILL.md
```

**Naming convention:**
- **Warehouse contexts:** Simple filenames (e.g., `global.md`, `python.md`). Names are flexible - what matters is the `opencode.json` configuration.
- **Project/User level:** Single `AGENTS.md` file by convention (`<project>/.opencode/AGENTS.md` or `~/.config/opencode/AGENTS.md`)

**Note:** `python`, `data-platform`, and `example-skill` are examples only. Replace with your organization's actual languages, domains, and skills.

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

### Alternative: Use This Repository as Reference

This repository serves as:
- **Reference documentation** - Examples of warehouse structure
- **Beacon source code** - The CLI tool itself (`libs/beacon/`)
- **Design guides** - Architecture and contribution patterns

You can also fork this repository if you prefer, though `abc init` is the recommended approach.

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
- **[CLI Implementation Summary](./docs/cli-implementation-summary.md)** - CLI design and architecture

### Practical Guides (guides/)
- **[CLI Quick Start](./guides/cli-quick-start.md)** - Installation and usage guide
- **[Warehouse Contribution Guide](./guides/warehouse-contribution-guide.md)** - How to contribute to your organization's warehouse

## 🏗️ What Goes Where?

This template uses a **two-tier approach** (contexts + knowledge) to manage agent information efficiently. See the [design guide](./docs/agentic-warehouse-design.md#understanding-the-two-tier-structure-context--knowledge) for full explanation.

### Contexts (`contexts/`)
- **Global** (`global.md`): Universal practices for all projects
- **Language** (`python.md`, `typescript.md`, etc.): Language-specific standards
- **Domain** (`data-platform.md`, `web-app.md`, etc.): Team/domain-specific patterns
- **Project** (not stored in warehouse): Single `AGENTS.md` file in project `.opencode/` directory
- **User** (not stored in warehouse): Single `AGENTS.md` file in `~/.config/opencode/`

**Naming note:** Warehouse context files use simple names. The `opencode.json` configuration determines which files are loaded. Project and user levels use the convention `AGENTS.md` for easy identification.

### Knowledge (`knowledge/`)
- **Decisions**: Technical choices and their rationale
- **Lessons**: Common agent failure modes and guardrails
- **Facts**: Established technical information and configurations

**Organization:** Knowledge mirrors context structure (global/, languages/, domains/) for selective import.

### Skills (`skills/`)
- **Procedural workflows**: Multi-step processes agents follow
- **Context injections**: Specialized instructions for specific tasks
- **Templates**: Structured documents or code patterns
- **Tools**: Scripts and automation with usage guides

## 🔄 Workflow

Once you've created your organization's warehouse from this template:

1. **Setup**: Teams install contexts and skills into their projects
2. **Use**: Agents load contexts automatically on session start
3. **Update**: Teams sync latest changes from warehouse
4. **Contribute**: Teams submit improvements back via pull requests

See the [Warehouse Contribution Guide](./docs/warehouse-contribution-guide.md) for details.

## 📖 Examples

See the `examples/` directory for:
- Sample context files
- Example knowledge files
- Reference skill structures

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
