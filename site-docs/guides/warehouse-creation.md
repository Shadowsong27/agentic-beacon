# Creating a Warehouse

A warehouse is a git repository that stores your team's shared knowledge, skills, and contexts. Projects connect to it and pull the artifacts they need.

## Quick Start

```bash
abc warehouse init my-warehouse
cd my-warehouse
```

---

## Required Structure

`abc warehouse init` creates the skeleton Agentic Beacon requires:

```
my-warehouse/
├── agents/
├── contexts/
├── knowledge/
├── skills/
│   └── record-knowledge/   # bundled starter skill (see Concepts → Bundled Skills)
│       └── SKILL.md
├── docs/
└── README.md
```

### What `abc warehouse connect` validates

When a project connects to a warehouse, exactly five things are checked:

- `contexts/` directory exists
- `knowledge/` directory exists
- `skills/` directory exists
- `docs/` directory exists
- A `README.md` exists at the root

That's it. No naming conventions inside those directories, no required files, no prescribed subdirectory structure.

---

## Organizing Your Content

The inner structure of `knowledge/`, `skills/`, and `contexts/` is **entirely yours to define**.

### Knowledge

Knowledge artifacts are markdown files — anything that helps an agent understand how your team works.

```
knowledge/
├── global/
│   └── anything-you-want.md
├── languages/
│   ├── python/
│   └── typescript/
└── decisions/
    └── why-we-chose-x.md
```

Common content:
- Architectural decisions and their rationale
- Coding standards and conventions
- Framework-specific patterns
- Security policies
- Onboarding notes

The structure you choose determines the glob patterns projects use in `beacon.yaml` to pull specific subsets.

### Skills

Skills are directories with a `SKILL.md` entry point:

```
skills/
└── code-review/
    ├── SKILL.md             # Required — the agent reads this
    └── checklist.md         # Optional supporting files
```

The skill name is the directory name. `abc warehouse init` pre-populates `skills/record-knowledge/` as a working example.

### Contexts

Contexts are `AGENTS.md`-style files loaded at agent session start:

```
contexts/
├── global.md           # org-wide standards
├── teams/
│   ├── backend.md      # team-specific rules
│   └── platform.md
└── projects/
    └── api-service.md  # project-specific context
```

Context files can be named anything. Projects pick which ones to load via `beacon.yaml`.

---

## Example: Building a Warehouse From Scratch

```bash
# 1. Create the structure
abc warehouse init team-warehouse
cd team-warehouse

# 2. Write your global context
cat > contexts/global.md << 'EOF'
# Acme Engineering — Agent Context

## Standards
- Python 3.12+, type hints required
- Tests are mandatory for all business logic
- Conventional commits

## Process
- TDD: tests before implementation
- PR review required before merge
EOF

# 3. Add knowledge
mkdir -p knowledge/decisions
cat > knowledge/decisions/testing-strategy.md << 'EOF'
# Testing Strategy

We use pytest for all Python testing. Business logic requires 100% coverage.
Fixtures live in conftest.py. Integration tests are separate from unit tests.
EOF

# 4. Add a skill
mkdir -p skills/code-review
cat > skills/code-review/SKILL.md << 'EOF'
---
name: code-review
description: Review code changes for correctness, style, and test coverage.
requires:
  contexts: [global]
---

# Skill: Code Review

## Purpose
Review code changes for correctness, style, and test coverage.

## Process
1. Read all changed files before commenting
2. Check correctness — does it do what it claims?
3. Check tests — are edge cases covered?
4. Check style — follows team conventions?
5. Summarize: blockers, suggestions, notes
EOF

# 5. Commit and push
git add .
git commit -m "Initial warehouse"
git remote add origin git@github.com:yourorg/team-warehouse.git
git push -u origin main
```

---

## Validating Your Warehouse

Connect to it from a test project:

```bash
abc warehouse connect --path ./team-warehouse
```

A clean output confirms the structure is valid:

```
✓ Warehouse structure validated
✓ Connected to warehouse
  Location: /Users/you/team-warehouse
```

---

## Maintenance

### Adding new content

```bash
cd team-warehouse
echo "# New guide..." > knowledge/new-topic.md
git add . && git commit -m "docs: add new topic guide"
git push
```

Team members get it on their next `git pull` + `abc sync`.

### Versioning

Use git tags to mark stable states:

```bash
git tag -a v1.0.0 -m "First stable warehouse release"
git push --tags
```

---

## Next Steps

- **[Team Collaboration](team-collaboration.md)** — share your warehouse across the team
- **[Creating Skills](creating-skills.md)** — write effective skill definitions
- **[Connecting a Project](connecting-projects.md)** — connect a project to this warehouse
