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
├── contexts/
├── knowledge/
├── skills/
│   └── record-knowledge/   # bundled starter skill
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

This writes your selections to `.agentic-beacon/beacon.yaml`.

### 6. Sync

```bash
abc sync
```

Artifacts are symlinked into `.agentic-beacon/artifacts/`, wired into your agent config, and skills installed as slash commands. Knowledge files referenced by markdown links in your contexts and skills are auto-derived and synced automatically.

---

## Scenario B: Joining a Team (Warehouse Exists)

```bash
# 1. Clone the warehouse
git clone git@github.com:your-org/warehouse.git ~/my-org-warehouse

# 2. Connect your project
cd ~/my-project
abc warehouse connect --path ~/my-org-warehouse

# 3. Browse and select artifacts
abc adopt

# 4. Sync
abc sync
```

Done. Your agent now has the team's contexts, knowledge, and skills loaded.

---

## Day-to-Day Workflow

Once set up, the recurring loop is:

```
1. abc sync                     — pull the latest from the warehouse
2. code with agent              — agent uses synced contexts, knowledge, and skills
3. abc warehouse status         — see what has changed in the warehouse working tree
4. abc warehouse contribute     — commit improvements back to the warehouse
5. repeat
```

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

- **[Concepts: How It Works](concepts/how-it-works.md)** — understand the warehouse model
- **[Creating a Warehouse](guides/warehouse-creation.md)** — full warehouse setup walkthrough
- **[beacon.yaml Reference](reference/beacon-yaml.md)** — configure exactly which artifacts you need
- **[Interactive Adoption](guides/interactive-adoption.md)** — the `abc adopt` TUI in depth
