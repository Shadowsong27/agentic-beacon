# Agentic Engineering Warehouse Template

A template repository for teams to establish standardized agentic coding practices with centralized context, knowledge, and skills management.

> **Note:** This is an **opinionated and simple take** on agentic engineering. The landscape is rapidly evolving, and this template provides one possible approach focused on DRY principles and centralized collaboration. Adapt it to your team's needs.

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

## 📁 Repository Structure

```
agentic-engineering-warehouse-template/
├── contexts/              # AGENTS.md files (global, language, domain)
│   ├── AGENTS.global.md
│   ├── AGENTS.python.md         # Example: Replace with your languages
│   └── AGENTS.data-platform.md  # Example: Replace with your domains
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

**Note:** `python`, `data-platform`, and `example-skill` are examples only. Replace with your organization's actual languages, domains, and skills.

## 🚀 Getting Started

### Quick Start with Beacon Init

The **fastest way** to create your organization's warehouse is using `beacon init`:

```bash
# Install beacon
pip install beacon --index-url https://your-homelab-pypi.local/simple/

# Or for public PyPI (when available):
# pip install beacon

# Initialize your warehouse
beacon init my-org-warehouse \
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

You can also fork this repository if you prefer, though `beacon init` is the recommended approach.

### For Organizations

1. **Initialize warehouse**: Run `beacon init` to create warehouse structure
2. **Customize**: Add your organization's contexts, knowledge, and skills
3. **Deploy Beacon**: Publish to your homelab PyPI (see [deployment guide](./libs/beacon/HOMELAB_PUBLISH.md))
4. **Distribute**: Teams install Beacon and use `beacon setup` in projects

### For Teams

1. **Install Beacon**: `pip install beacon --index-url https://your-pypi.local/simple/`
2. **Setup projects**: `beacon setup --warehouse ~/warehouse --all`
3. **Stay in sync**: `beacon update` to get latest changes
4. **Contribute**: Use `beacon delta` to find new patterns to share

## 📚 Documentation

- **[Agentic Warehouse Design](./docs/agentic-warehouse-design.md)** - High-level design and architecture
- **[Spec-Driven Development](./docs/spec-driven-development.md)** - Structured approach to feature planning and implementation
- **[Warehouse Contribution Guide](./docs/warehouse-contribution-guide.md)** - How to contribute to your organization's warehouse
- **[Implementation Guide](./docs/implementation-guide.md)** - How to build CLI tools and workflows _(coming soon)_

## 🏗️ What Goes Where?

This template uses a **two-tier approach** (contexts + knowledge) to manage agent information efficiently. See the [design guide](./docs/agentic-warehouse-design.md#understanding-the-two-tier-structure-context--knowledge) for full explanation.

### Contexts (`contexts/`)
- **Global** (`AGENTS.global.md`): Universal practices for all projects
- **Language** (`AGENTS.python.md`): Language-specific standards
- **Domain** (`AGENTS.data-platform.md`): Team/domain-specific patterns
- **Project** (not stored here): Project-specific context lives in each project

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

## 🛠️ CLI Tooling - Beacon

This template includes **Beacon**, a Python CLI tool for distributing contexts, knowledge, and skills to projects.

**Brand:** "Guide your agents with distributed knowledge"

### Installation

#### Option 1: From Homelab PyPI (Recommended)

```bash
# Install from your organization's private PyPI
pip install beacon --index-url https://your-homelab-pypi.local/simple/
```

#### Option 2: From Source (Development)

```bash
# From your forked warehouse repository
cd your-org-warehouse/libs/beacon
pip install -e .
```

### Quick Start

```bash
# List available content in warehouse
beacon list

### Quick Start

```bash
# Initialize a new warehouse
beacon init my-warehouse \
  --org "Your Organization" \
  --languages python,typescript \
  --domains data-platform

# List available content in warehouse
beacon list

# Setup in your project (interactive mode)
cd ~/your-project
beacon setup --warehouse ~/your-warehouse --interactive

# Or install everything
beacon setup --warehouse ~/your-warehouse --all

# Check what's installed
beacon status

# Compare with warehouse (find local changes)
beacon delta --warehouse ~/your-warehouse

# Update from warehouse
beacon update --warehouse ~/your-warehouse

# Remove installation
beacon clean
```

### Commands

| Command | Description |
|---------|-------------|
| `beacon init` | **NEW** - Initialize a new warehouse repository |
| `beacon list` | List all available warehouse content |
| `beacon setup` | Install contexts/knowledge/skills to `.opencode/` |
| `beacon status` | Show currently installed content |
| `beacon delta` | Compare target with warehouse to find differences |
| `beacon update` | Sync latest changes from warehouse |
| `beacon clean` | Remove `.opencode/` directory |

### Init Command (New!)

The `beacon init` command creates a complete warehouse structure:

```bash
beacon init my-warehouse --org "Acme Corp" --languages python,typescript --domains data-platform
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
beacon init my-warehouse
? Organization name: Acme Corp
? Primary languages (comma-separated): python, typescript
? Primary domains (comma-separated): data-platform, web-services
? Initialize git repository? [Y/n]: y
✓ Warehouse initialized successfully!
```

### Delta Command

The `beacon delta` command helps you track changes and contributions:

```bash
beacon delta --warehouse ~/warehouse
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

**For Warehouse Maintainers:**

```bash
# Build the package
cd libs/beacon
uv build

# Publish to your homelab PyPI
uv publish \
  --publish-url https://your-homelab-pypi.local/simple/ \
  --token your-api-token
```

**For Public PyPI (when ready):**

```bash
cd libs/beacon
uv build
uv publish  # Publishes to PyPI.org
```

### Documentation

- **[Quick Start Guide](./libs/beacon/QUICKSTART.md)** - Get started in 5 minutes
- **[Homelab Deployment](./libs/beacon/HOMELAB_PUBLISH.md)** - Deploy to private PyPI
- **[Complete README](./libs/beacon/README.md)** - Full CLI documentation
- **[Project Status](./libs/beacon/PROJECT_COMPLETE.md)** - Implementation details

### Technical Details

- **Package Name:** `beacon`
- **CLI Command:** `beacon`
- **Python Required:** `>=3.12`
- **License:** MIT
- **Dependencies:** click, rich, pyyaml, loguru

### Workflow Example

```bash
# 1. Organization deploys beacon to homelab PyPI
cd warehouse/libs/beacon
uv build && uv publish --publish-url https://pypi.homelab.local/simple/ --token xxx

# 2. Developers install beacon
pip install beacon --index-url https://pypi.homelab.local/simple/

# 3. Developers use in projects
cd ~/my-project
beacon setup --warehouse ~/warehouse --all
echo ".opencode/" >> .gitignore

# 4. Check for contributions
beacon delta
# Shows new files that could be contributed back

# 5. Stay in sync
beacon update
```

## 📋 License

[Your License Here]

---

**Template Version:** 1.0.0  
**Last Updated:** 2026-03-07
