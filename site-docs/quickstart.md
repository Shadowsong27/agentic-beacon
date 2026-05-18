# Quick Start

Get Agentic Beacon running in under 5 minutes. This guide covers two scenarios: starting fresh and joining a team that already has a warehouse.

## Prerequisites

- [Install `abc`](installation.md) — `uv tool install agentic-beacon`
- Python 3.12+

---

## Scenario A: Starting Fresh (No Warehouse Yet)

### 1. Create your warehouse

```bash
abc warehouse init my-org-warehouse
cd my-org-warehouse
```

This creates the required structure:

```
my-org-warehouse/
├── agents/
├── contexts/
├── knowledge/
├── skills/
│   ├── record-knowledge/   # bundled starter skill (see Concepts → Bundled Skills)
│   └── record-skill/       # bundled starter skill
├── docs/
└── README.md
```

### 2. Populate it

Add your team's shared content — any structure you like:

```bash
# Add a global context
echo "# Org Standards\n## Conventions\n- Python 3.12+, type hints required" > contexts/global.md

# Add a knowledge file
mkdir -p knowledge/decisions
echo "# Why We Use Pydantic\n..." > knowledge/decisions/pydantic.md

# Reference the knowledge file from your context
echo "See [Pydantic rationale](knowledge/decisions/pydantic.md) for details." >> contexts/global.md
```

### 3. Commit and push

```bash
git add .
git commit -m "Initial warehouse"
git remote add origin git@github.com:your-org/warehouse.git
git push -u origin main
```

### 4. Connect a project

```bash
cd ~/my-project
abc warehouse connect --path ~/my-org-warehouse
```

### 5. Browse and select artifacts

```bash
abc adopt          # opens interactive TUI — Space to select, Enter to confirm
```

When you press Enter inside the TUI, `abc adopt` writes your selections to `beacon.yaml` (clearing matching entries from `pending.yaml`) **and** syncs them immediately — symlinks are created, agent config is wired, and skills are installed as slash commands.

> If you edit `beacon.yaml` manually instead of going through the TUI, run `abc sync` yourself to apply the changes.

---

## Scenario B: Joining a Team (Warehouse Exists)

```bash
# 1. Clone the warehouse
git clone git@github.com:your-org/warehouse.git ~/my-org-warehouse

# 2. Connect your project
cd ~/my-project
abc warehouse connect --path ~/my-org-warehouse

# 3. Browse and select artifacts (the TUI syncs on apply)
abc adopt
```

Done. Your agent now has the team's contexts, knowledge, and skills loaded.

---

## What Gets Committed to Git

```
✅  .agentic-beacon/beacon.yaml    — your artifact dependencies (commit this)
❌  .agentic-beacon/config.toml   — gitignored (local warehouse path)
❌  .agentic-beacon/artifacts/    — gitignored (symlink tree)
```

Teammates run `abc warehouse connect` + `abc sync` to get the same artifacts on their machines.

---

## Next Steps

- **[How It Works](concepts/how-it-works.md)** — the warehouse + symlink model in depth
- **[Day-to-Day Workflow](guides/day-to-day-workflow.md)** — the recurring sync / status / contribute loop
- **[Adopting Artifacts](guides/adopting-artifacts.md)** — the `abc adopt` TUI and declarative `beacon.yaml` flow
