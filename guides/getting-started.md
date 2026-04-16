# Getting Started with Agentic Beacon

**An opinionated framework for standardizing and distributing agentic engineering artifacts across teams.**

Agentic Beacon provides:
1. **A methodology** for managing contexts, knowledge, and skills — the core agentic engineering artifacts worthy of standardization and team-wide distribution
2. **CLI tooling (`abc`)** for initializing warehouses, managing connections, and distributing artifacts across projects

Think of it like npm for agentic artifacts:

| npm analogy | Agentic Beacon |
|-------------|----------------|
| npm registry | **Warehouse** — your central repository of shared artifacts |
| `package.json` | **`beacon.yaml`** — your project's artifact dependencies |
| `node_modules/` | **`.agentic-beacon/artifacts/`** — local downloaded snapshot |
| `npm install` | **`abc sync`** — fetch and update artifacts |

## The Three Artifact Types

**Knowledge** — Markdown files containing standards, decisions, best practices, and guides. Agents read these to inform how they work.

**Skills** — Reusable workflows. A `SKILL.md` tells the agent how to perform a repeatable task (code review, test generation, etc.).

**Contexts** — Boot instruction files loaded at agent session start. These carry the rules and conventions that apply to every interaction.

---

## Prerequisites

- Python 3.12 or higher
- uv or pipx (recommended) — or pip

---

## Installation

**Recommended: Install with uv**
```bash
uv tool install agentic-beacon
```

**Alternative: pipx (isolated environment)**
```bash
pipx install agentic-beacon
```

**Alternative: pip**
```bash
pip install agentic-beacon
```

Verify:

```bash
abc --version
```

---

## The Two Workflows

There are two distinct workflows in Agentic Beacon. **You need both.**

| Workflow | Who does it | What it produces |
|----------|-------------|-----------------|
| **Set up a warehouse** | Once per team/org | A central repository of shared artifacts |
| **Configure a project** | Once per project | A `beacon.yaml` that pulls from the warehouse |

If your team already has a warehouse, skip to [Configure a Project](#workflow-2-configure-a-project).

If you're starting fresh, begin with the warehouse.

---

## Workflow 1: Set Up a Warehouse

A warehouse is a git repository that stores your shared knowledge, skills, and contexts. It's the source of truth your projects pull from.

### Create the warehouse

```bash
abc warehouse init my-warehouse
cd my-warehouse
```

This creates the required directory structure:

```
my-warehouse/
├── contexts/
│   ├── global.md          # e.g. org-wide standards
│   ├── python.md          # e.g. language-specific rules
│   └── backend-team.md    # e.g. team or domain standards
├── knowledge/
├── skills/
├── docs/
└── README.md
```

The inner structure of `knowledge/`, `skills/`, and `contexts/` is **entirely up to you**. Organize it however makes sense for your team. See [Creating a Warehouse](./warehouse-creation.md) for guidance.

### Populate it

Add your team's knowledge, skills, and contexts. Each file you create here becomes available to any project that connects to this warehouse.

```bash
# Examples — the paths and names are yours to choose
mkdir -p knowledge/decisions
echo "# Our coding standards..." > knowledge/decisions/coding-standards.md

mkdir -p skills/code-review
echo "# Skill: Code Review..." > skills/code-review/SKILL.md

echo "# Team context..." > contexts/global.md
```

### Commit it

```bash
git init
git add .
git commit -m "Initial warehouse"
git remote add origin git@github.com:yourorg/warehouse.git
git push -u origin main
```

The warehouse is now ready. See [Creating a Warehouse](./warehouse-creation.md) for a full walkthrough.

---

## Workflow 2: Configure a Project

Once a warehouse exists (yours or your team's), connect your project to it and declare which artifacts you need.

### Step 1: Clone the warehouse locally

```bash
git clone git@github.com:yourorg/warehouse.git ~/team-warehouse
```

### Step 2: Connect your project

```bash
cd my-project
abc warehouse connect --path ~/team-warehouse
```

This creates `.agentic-beacon/config.toml` (gitignored) with the warehouse path.

**Expected output:**
```
✓ Warehouse structure validated
✓ Connected to warehouse
  Location: /Users/you/team-warehouse

Next Steps:
  1. Run 'abc setup' to configure artifacts
  2. Run 'abc sync' to download artifacts
```

### Step 3: Create your artifact configuration

```bash
abc setup --manual
```

This creates `.agentic-beacon/beacon.yaml` — an empty template.

Or use agent-assisted mode to let your AI agent help pick artifacts:

```bash
abc setup --agent-assisted
```

See [Agent-Assisted Setup](./agent-assisted-setup.md) for how this works.

### Step 4: Declare which artifacts you need

Edit `.agentic-beacon/beacon.yaml`:

```yaml
artifacts:
  knowledge:
    - knowledge/decisions/coding-standards.md
    - knowledge/testing/**/*.md

  skills:
    - skills/code-review/

  contexts:
    - contexts/global.md
```

Paths are relative to the warehouse root. Glob patterns are supported. See [beacon.yaml Reference](./beacon-yaml-reference.md) for the full schema.

### Step 5: Sync

```bash
abc sync
```

Artifacts are copied into `.agentic-beacon/artifacts/` and wired into your agent config automatically.

`abc sync` does the full job in one step:
- **Contexts** — appended to `opencode.json` instructions or `CLAUDE.md` (whichever exists)
- **Skills** — installed into `.opencode/skills/` + `.opencode/command/` (or `.claude/skills/`)
- **Knowledge** — copied to artifacts, no further wiring needed

> **First run on a new project?** If you don't have an `opencode.json` or `CLAUDE.md` yet, create one first — even an empty `opencode.json` (`{}`) is enough for sync to wire contexts into it automatically.

### Step 6: Invoke skills

After syncing, any skill declared in `beacon.yaml` is available as a slash command immediately. To install a single skill without a full sync:

```bash
abc install skills/code-review
```

This copies the skill from the warehouse, wires it for your agent, and adds it to `beacon.yaml` so future syncs stay idempotent.

### Step 7: Commit your config changes

Commit these changes so teammates get the same contexts automatically after running `abc sync`.

### What gets committed to git

```
✅  .agentic-beacon/beacon.yaml    — your artifact dependencies
❌  .agentic-beacon/config.toml   — gitignored (local warehouse path)
❌  .agentic-beacon/artifacts/    — gitignored (downloaded snapshot)
```

Your teammates run `abc warehouse connect` + `abc sync` to get the same artifacts on their machines.

---

## Keeping Artifacts Updated

When the warehouse changes:

```bash
# Pull warehouse updates
cd ~/team-warehouse && git pull

# Re-sync your project
cd my-project && abc sync
```

The sync is idempotent — only files that changed are re-copied.

### Discovering new artifacts

After `abc sync`, if a teammate contributed new artifacts to the warehouse since your last sync, you'll see a notification:

```
✓ Sync complete
  Copied: 0 files
  Unchanged: 3 files

1 new artifact(s) available -- run abc adopt to review
```

Run `abc adopt` to open an interactive selector and add them to your `beacon.yaml`:

```bash
abc adopt
```

This opens a TUI where you can browse new artifacts grouped by type (contexts, skills, knowledge), check the ones you want, and press **Enter** to confirm. Selected artifacts are added to `beacon.yaml` and immediately synced and wired into your agent config.

**Flags:**

| Flag | Effect |
|------|--------|
| `--all` | Show every warehouse artifact not yet in `beacon.yaml` (not just since last sync) |
| `--dry-run` | Preview what's available without making any changes |

```bash
# Preview available artifacts
abc adopt --dry-run

# See everything in the warehouse you haven't adopted yet
abc adopt --all
```

---

## Common Issues

### "No warehouse connected"

```bash
abc warehouse connect --path /path/to/warehouse
```

### "No beacon.yaml found"

```bash
abc setup --manual
# Then edit .agentic-beacon/beacon.yaml
```

### Warehouse moved or deleted

```bash
abc warehouse connect --path /new/path/to/warehouse
```

---

## Next Steps

- **[Creating a Warehouse](./warehouse-creation.md)** — Full warehouse setup walkthrough
- **[beacon.yaml Reference](./beacon-yaml-reference.md)** — Full configuration reference
- **[Advanced Patterns](./advanced-patterns.md)** — Glob patterns, sync flags, delta workflow
- **[Agent-Assisted Setup](./agent-assisted-setup.md)** — Let AI help populate `beacon.yaml`
- **[Team Collaboration](./team-collaboration.md)** — Sharing across projects and teams

---

**Related Guides:**
- [Creating a Warehouse](./warehouse-creation.md)
- [Python Project Setup](./python-project-setup.md)
- [Team Collaboration](./team-collaboration.md)
