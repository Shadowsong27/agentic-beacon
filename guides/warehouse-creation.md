# Creating a Warehouse

A warehouse is a git repository that stores your team's shared knowledge, skills, and contexts. Projects connect to it and pull the artifacts they need.

## Quick Start

```bash
abc warehouse init my-warehouse
cd my-warehouse
```

---

## Required Structure

The `abc warehouse init` command creates the skeleton that Agentic Beacon requires, plus bundles in the `record-knowledge` skill as a ready-to-use starting point:

```
my-warehouse/
├── contexts/
├── knowledge/
├── skills/
│   └── record-knowledge/   # Bundled by abc — ready to sync to projects
│       └── SKILL.md
├── docs/
└── README.md
```

### What `abc warehouse connect` validates

When a project connects to a warehouse, it checks exactly five things:

- `contexts/` directory exists
- `knowledge/` directory exists
- `skills/` directory exists
- `docs/` directory exists
- A `README.md` (or `README` / `README.txt`) file exists at the root

That's it. No naming conventions inside any of those directories, no required files within them, no prescribed subdirectory structure. Everything inside is yours to define.

---

## Organizing Your Content

The inner structure of `knowledge/`, `skills/`, and `contexts/` is **entirely yours to define**. Agentic Beacon imposes no naming conventions, no required subdirectories, and no categorization scheme.

Organize artifacts however your team thinks about them. Some teams organize by topic, some by team, some by project. All of these are valid.

### Knowledge

Knowledge artifacts are markdown files — any content that helps an agent understand how your team works.

```
knowledge/
├── global/
│   └── anything-you-want.md
├── your-own-structure/
│   └── more-files.md
└── flat-file.md
```

Examples of what teams put here:
- Architectural decisions and their rationale
- Coding standards and conventions
- Framework-specific patterns
- Security policies
- Onboarding notes for the codebase
- "Why we chose X" explanations

There is no required depth, naming pattern, or subdirectory scheme. The structure you choose determines the glob patterns projects use in `beacon.yaml` to pull specific subsets.

### Skills

Skills are directories with a `SKILL.md` entry point. Each skill is a reusable agent workflow.

```
skills/
└── your-skill-name/
    ├── SKILL.md             # Required — the agent reads this
    └── any-supporting-files
```

The skill name is the directory name. Projects reference it with a glob pattern like `skills/your-skill-name/**/*`.

`abc warehouse init` pre-populates `skills/record-knowledge/` — a skill for capturing decisions, lessons, and facts into the knowledge base. Projects that sync it can use `/record-knowledge` to record knowledge directly from the agent.

See [Creating Skills](./creating-skills.md) for how to write effective `SKILL.md` files.

### Contexts

Contexts are `AGENTS.md`-style files the agent loads at session start.

```
contexts/
├── global.md         # Convention — name this whatever makes sense
└── python.md         # Add as many context files as you need
```

Context files can be named anything — `global.md`, `python.md`, `backend-team.md`, whatever reflects their purpose. Projects pick which ones to pull in `beacon.yaml`. `abc warehouse init` creates a starter file called `AGENTS.md` as a starting point.

---

## Writing Your First Context File

`abc warehouse init` creates a starter file at `contexts/AGENTS.md`. Rename it or add more files alongside it — the filename is not enforced by any tooling, so use whatever makes sense for your team (e.g. `global.md`, `python.md`, `backend-team.md`).

```markdown
# <Org> — Agent Context

## About This Organization
Brief description of your org, team, or project.

## Core Principles
- <What matters most to how you work>
- <Your key engineering values>

## Standards
- <Language/tooling decisions>
- <Process requirements>

## Workflow
<How features get built and shipped>
```

Keep it focused on what applies everywhere. Project-specific rules belong in separate context files that projects opt into via `beacon.yaml`.

---

## Example: Building a Warehouse From Scratch

```bash
# 1. Create the structure
abc warehouse init team-warehouse
cd team-warehouse

# 2. Write your global context
# abc warehouse init already created contexts/AGENTS.md — edit it, or rename it
cat > contexts/AGENTS.md << 'EOF'
# Acme Engineering — Agent Context

## Standards
- Python 3.12+, type hints required
- Tests are mandatory for all business logic
- Conventional commits

## Process
- TDD — tests before implementation
- PR review required before merge
EOF

# 3. Add knowledge
mkdir -p knowledge/global/decisions
cat > knowledge/global/decisions/testing-strategy.md << 'EOF'
# Testing Strategy

We use pytest for all Python testing. Business logic requires 100% coverage.
Fixtures live in conftest.py. Integration tests are separate from unit tests.
EOF

# 4. Add a skill
mkdir -p skills/code-review
cat > skills/code-review/SKILL.md << 'EOF'
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

# 5. Commit
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

A clean output means the structure is valid:

```
✓ Warehouse structure validated
✓ Connected to warehouse
```

---

## Maintenance

### Adding new content

```bash
cd team-warehouse
# Add a file wherever makes sense
echo "# New guide..." > knowledge/global/new-topic.md
git add . && git commit -m "docs: add new topic guide"
git push
```

Team members get it on their next `git pull` + `abc sync`.

### Pruning outdated content

Remove files that are no longer relevant. Projects that referenced them via `abc sync --prune` will have the stale files removed on next sync.

### Versioning

Use git tags to mark stable states:

```bash
git tag -a v1.0.0 -m "First stable warehouse release"
git push --tags
```

---

## Next Steps

- **[Team Collaboration](./team-collaboration.md)** — Share your warehouse with the team
- **[Creating Skills](./creating-skills.md)** — Write effective skill definitions
- **[Getting Started](./getting-started.md)** — Connect a project to this warehouse
