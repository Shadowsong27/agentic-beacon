# Agentic Engineering Warehouse Template

A template repository for teams to establish standardized agentic coding practices with centralized context, knowledge, and skills management.

## 🎯 Purpose

This template provides a "warehouse" structure where teams can:
- **Store** reusable agent contexts, knowledge, and skills
- **Share** proven patterns across projects and teams
- **Maintain** consistency in how AI agents collaborate with developers
- **Evolve** practices together through versioned changes

## 📁 Repository Structure

```
agentic-engineering-warehouse-template/
├── contexts/              # AGENTS.md files (global, language, domain)
│   ├── AGENTS.global.md
│   ├── AGENTS.python.md
│   └── AGENTS.data-platform.md
│
├── knowledge/            # Atomic knowledge (facts, decisions, lessons)
│   ├── global/          # Universal knowledge (all projects)
│   │   ├── decisions/
│   │   ├── lessons/
│   │   └── facts/
│   ├── languages/       # Language-specific knowledge
│   │   └── python/
│   │       ├── decisions/
│   │       └── lessons/
│   └── domains/         # Domain-specific knowledge
│       └── data-platform/
│           ├── decisions/
│           ├── lessons/
│           └── facts/
│
└── skills/              # Reusable workflows and procedures
    ├── README.md        # Skills catalog (agent-maintained)
    └── example-skill/
        └── SKILL.md
```

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
3. **Reference** the [Agentic Engineering Guide](./docs/agentic-engineering-guide.md) for usage patterns
4. **Contribute** improvements back via pull requests

## 📚 Documentation

- **[Agentic Engineering Guide](./docs/agentic-engineering-guide.md)** - Complete guide to using this system
- **[Implementation Guide](./docs/implementation-guide.md)** - How to build CLI tools and workflows _(coming soon)_

## 🏗️ What Goes Where?

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

1. **Setup**: Install contexts and skills into project
2. **Use**: Agents load contexts automatically on session start
3. **Update**: Sync latest changes from central repository
4. **Contribute**: Submit improvements via pull requests

## 🤝 Contributing

1. **Test locally** in your project
2. **Create pull request** with changes
3. **Document** what changed and why
4. **CI validates** (if testing infrastructure exists)
5. **Merge** makes available to all teams

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
