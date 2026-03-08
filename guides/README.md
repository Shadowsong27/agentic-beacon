# Practical Guides

This directory contains **practical how-to guides** for using Agentic Beacon v2.0. For **conceptual design documentation**, see the [docs/](../docs/) directory.

---

## Getting Started

**[🚀 Getting Started Guide](./getting-started.md)** ⭐ **Start here!**
- Your first experience with Agentic Beacon
- Connect to a warehouse
- Create beacon.yaml configuration
- Sync artifacts
- Understanding the config-based model

**Who should read:** Everyone new to Agentic Beacon v2.0

---

## Scenario-Based Guides

### Project Setup by Language/Domain

**[🐍 Python Project Setup](./python-project-setup.md)**
- Setting up Python backend services
- FastAPI, pytest, and common Python patterns
- Project-specific customization
- Example configurations for different Python project types

**Who should read:** Python developers setting up projects

---

### Team & Organization

**[👥 Team Collaboration](./team-collaboration.md)**
- Creating and sharing a team warehouse
- Coordination workflows
- Version control strategies
- Multi-repository organizations
- Measuring adoption

**Who should read:** Team leads, warehouse maintainers

**[🏗️ Creating a Warehouse](./warehouse-creation.md)**
- Warehouse structure and organization
- Adding knowledge, skills, and contexts
- Best practices and patterns
- Complete example warehouse setup

**Who should read:** Warehouse creators and maintainers

---

## Reference & Troubleshooting

**[🔧 Troubleshooting Guide](./troubleshooting.md)**
- Common errors and solutions
- Configuration issues
- File sync problems
- Team collaboration issues
- Migration from v1.x

**Who should read:** When you encounter issues

---

## Legacy Guides (v1.x)

These guides are for the older v1.x direct-distribution model:

**[CLI Quick Start (v1.x)](./cli-quick-start.md)**
- Old v1.x commands
- Direct warehouse setup
- Not applicable to v2.0

**[Warehouse Contribution Guide (v1.x)](./warehouse-contribution-guide.md)**
- Old contribution workflow
- Delta command (deprecated in v2.0)

**Status:** Kept for reference during migration period

---

## Quick Command Reference

### Essential Commands

```bash
# Connect to warehouse
abc warehouse connect --path /path/to/warehouse

# Create configuration
abc setup --manual

# Sync artifacts
abc sync

# Get help
abc --help
abc warehouse --help
abc sync --help
```

### Common Workflows

**New project setup:**
```bash
cd my-project
abc warehouse connect --path ~/team-warehouse
abc setup --manual
# Edit .agentic-beacon/beacon.yaml
abc sync
```

**Update artifacts:**
```bash
cd ~/team-warehouse && git pull
cd my-project && abc sync
```

**Team member onboarding:**
```bash
git clone git@github.com:org/warehouse.git ~/team-warehouse
cd existing-project
abc warehouse connect --path ~/team-warehouse
abc sync
```

---

## Guide Philosophy

**Guides in this folder:**
- ✅ Step-by-step instructions
- ✅ Copy-paste command examples
- ✅ Real-world scenarios
- ✅ "How do I...?" questions
- ✅ Troubleshooting solutions

**Design Docs ([docs/](../docs/)):**
- 📐 Conceptual architecture
- 📐 Design philosophy  
- 📐 "Why is it designed this way?" questions
- 📐 Decision rationale

---

## Need Help?

1. **Start with:** [Getting Started Guide](./getting-started.md)
2. **Having issues?** [Troubleshooting Guide](./troubleshooting.md)
3. **Still stuck?** Open a GitHub issue
4. **Want to understand the design?** See [docs/](../docs/)

---

## Contributing to Guides

Found something missing or unclear? Guides should be:
- **Clear:** Step-by-step with commands
- **Complete:** Cover common scenarios
- **Current:** Accurate for v2.0
- **Concise:** Get to the point quickly
- **Tested:** Commands actually work

Submit improvements via pull request!
