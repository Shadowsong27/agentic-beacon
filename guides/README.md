# Practical Guides

This directory contains **practical how-to guides** for using Agentic Beacon. For **conceptual design documentation**, see the [docs/](../docs/) directory.

---

## Getting Started

**[Getting Started Guide](./getting-started.md)** — **Start here!**
- Your first experience with Agentic Beacon
- Connect to a warehouse
- Create beacon.yaml configuration
- Sync artifacts
- Understanding the config-based model

**Who should read:** Everyone new to Agentic Beacon

---

## Scenario-Based Guides

### Project Setup

**[Python Project Setup](./python-project-setup.md)**
- Setting up Python backend services
- FastAPI, pytest, and common Python patterns
- Project-specific customization
- Example configurations for different Python project types

**Who should read:** Python developers setting up projects

---

### Team & Organization

**[Team Collaboration](./team-collaboration.md)**
- Creating and sharing a team warehouse
- Coordination workflows
- Version control strategies
- Multi-repository organizations
- Measuring adoption

**Who should read:** Team leads, warehouse maintainers

**[Creating a Warehouse](./warehouse-creation.md)**
- Warehouse structure and organization
- Adding knowledge, skills, and contexts
- Best practices and patterns
- Complete example warehouse setup

**Who should read:** Warehouse creators and maintainers

**[Keeping Warehouse Docs Up to Date](./warehouse-template-upgrade.md)**
- How template checksums work
- Upgrading template-generated files with `abc warehouse template-upgrade`
- Merging `.new` sidecar files for modified docs
- `--dry-run`, `--interactive`, and `--force` options
- Handling legacy warehouses (no checksum file)

**Who should read:** Warehouse maintainers upgrading after `abc` version bumps

---

## Reference

**[beacon.yaml Reference](./beacon-yaml-reference.md)**
- Full schema documentation
- Knowledge, skills, and contexts configuration
- Glob pattern rules
- Validation and lifecycle

**Who should read:** Anyone configuring `beacon.yaml`

**[Advanced Patterns](./advanced-patterns.md)**
- Glob pattern syntax and examples
- `abc sync --dry-run` preview
- `abc warehouse status` and `abc warehouse contribute`
- Migration from the copy-based model

**Who should read:** Users who want more control over artifact management

**[Agent-Assisted Setup](./agent-assisted-setup.md)**
- Using `abc setup --agent-assisted`
- How the warehouse catalog works
- Prompting your AI agent to populate `beacon.yaml`

**Who should read:** Users new to a warehouse who want AI help choosing artifacts

**[Creating Skills](./creating-skills.md)**
- What a skill is and how agents use it
- Writing `SKILL.md`
- Adding supporting files
- Publishing skills to the warehouse

**Who should read:** Warehouse maintainers, engineers adding team workflows

---

## Troubleshooting

**[Troubleshooting Guide](./troubleshooting.md)**
- Common errors and solutions
- Configuration issues
- File sync problems
- Team collaboration issues

**Who should read:** When you encounter issues

---

## Quick Command Reference

### Essential Commands

```bash
# Connect to warehouse
abc warehouse connect --path /path/to/warehouse

# Create beacon.yaml (manual)
abc setup --manual

# Create beacon.yaml (AI-assisted)
abc setup --agent-assisted

# Sync artifacts (creates symlinks into the warehouse clone)
abc sync

# Preview what sync would do without touching the filesystem
abc sync --dry-run

# See uncommitted warehouse edits (scoped by beacon.yaml)
abc warehouse status

# Commit your edits back to the warehouse
abc warehouse contribute -m "…" --push

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

**Review and contribute warehouse edits:**
```bash
abc warehouse status              # Summary of uncommitted warehouse edits, scoped by beacon.yaml
abc warehouse status <file>       # Detailed diff for one file
abc warehouse contribute -m "…"   # Commit the edits in the warehouse
```

---

## Guide Philosophy

**Guides in this folder:**
- Step-by-step instructions
- Copy-paste command examples
- Real-world scenarios
- "How do I...?" questions
- Troubleshooting solutions

**Design Docs ([docs/](../docs/)):**
- Conceptual architecture
- Design philosophy
- "Why is it designed this way?" questions
- Decision rationale

---

## Need Help?

1. **Start with:** [Getting Started Guide](./getting-started.md)
2. **Having issues?** [Troubleshooting Guide](./troubleshooting.md)
3. **Still stuck?** Open a GitHub issue
4. **Want to understand the design?** See [docs/](../docs/)
