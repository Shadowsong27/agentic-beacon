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

### How to Use This Template

**Step 1: Create Your Organization's Warehouse**

Click the **"Use this template"** button on GitHub to create your organization's central repository:

```bash
# Template repository (what you're looking at):
agentic-engineering-warehouse-template

# Your organization's warehouse (created from template):
your-org-agentic-engineering-warehouse
```

**Step 2: Name Your Warehouse**

When creating from template, name it without the `-template` suffix:
- ✅ Good: `acme-agentic-warehouse`, `mycompany-engineering-standards`
- ❌ Bad: `acme-agentic-warehouse-template` (confusing - template is just the starting point)

**Step 3: Customize for Your Organization**

1. Update contexts with your organization's practices
2. Add your technology stack's knowledge files
3. Create skills for your workflows
4. Set up CLI tooling for distribution (optional)

### For Organizations

1. **Use this template** to create your organization's central warehouse repository
2. **Customize** contexts, knowledge, and skills for your teams
3. **Set up CLI tooling** for installation and updates (see Implementation Guide)
4. **Establish contribution workflow** for teams to give back improvements

### For Teams

1. **Browse** available contexts, knowledge, and skills in your organization's warehouse
2. **Install** relevant components to your project using CLI tools
3. **Reference** the [design guide](./docs/agentic-warehouse-design.md) for usage patterns
4. **Contribute** improvements back via pull requests

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

## 🛠️ CLI Tooling

This template assumes you will build CLI tooling for:
- **Installation**: `agentic-setup` to select and install contexts/skills
- **Discovery**: `agentic-list skills` to browse available components
- **Updates**: `agentic-update` to sync latest changes
- **Contribution**: `agentic-contribute` to prepare pull requests

Reference implementation coming soon.

## 📋 License

[Your License Here]

---

**Template Version:** 1.0.0  
**Last Updated:** 2026-03-06
