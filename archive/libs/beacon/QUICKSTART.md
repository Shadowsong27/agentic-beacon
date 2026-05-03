# Agentic Beacon Quick Start

> **Superseded by** the [root `README.md`](../../../README.md) (install + quickstart) and [`guides/getting-started.md`](../../../guides/getting-started.md). The commands below reference a pre-symlink CLI surface (`abc delta`, `abc setup --warehouse`, `abc list`) that no longer exists in this shape. Retained for historical context only.

---

## Installation

```bash
pip install agentic-beacon
```

## Verify Installation

```bash
abc --help
```

## Basic Usage

### 1. List Available Content

```bash
# From warehouse directory
cd ~/your-warehouse
abc list
```

Output shows available contexts, knowledge, and skills.

### 2. Setup in Project

```bash
# Navigate to your project
cd ~/my-project

# Install all content
abc setup --warehouse ~/your-warehouse --all

# Or selective install
abc setup --warehouse ~/your-warehouse \
  -c global \
  -c python \
  -k global \
  -k languages/python
```

### 3. Check Status

```bash
abc status
```

Shows what's currently installed in `.opencode/`.

### 4. Compare with Warehouse (Delta)

```bash
abc delta --warehouse ~/your-warehouse
```

Shows:
- **New files** in your project (potential contributions)
- **Modified files** in your project (local customizations)
- **Missing files** (available in warehouse)

### 5. Update from Warehouse

```bash
abc update --warehouse ~/your-warehouse
```

Syncs latest changes from warehouse to your project.

### 6. Clean Installation

```bash
abc clean
```

Removes `.opencode/` directory.

## Common Workflows

### Workflow 1: New Project Setup

```bash
cd ~/new-project
abc setup --warehouse ~/warehouse --all
echo ".opencode/" >> .gitignore
git add .gitignore
git commit -m "chore: add abc setup"
```

### Workflow 2: Check for Changes

```bash
# After working on your project
abc delta

# If you have new patterns, contribute back to warehouse
# Copy files from .opencode/ to warehouse and submit PR
```

### Workflow 3: Sync with Warehouse

```bash
# When warehouse is updated
cd ~/warehouse && git pull
cd ~/my-project
abc update
```

## File Structure

After setup:

```
your-project/
├── .opencode/                    # gitignored
│   ├── .warehouse-config.yml    # Tracks what's installed
│   ├── contexts/
│   ├── knowledge/
│   └── skills/
├── .gitignore                    # Contains .opencode/
└── (your project files)
```

## Tips

1. **Always gitignore `.opencode/`** - This is distributed content, not source code
2. **Use `abc delta` regularly** - Catch local customizations that should be shared
3. **Update frequently** - Stay in sync with warehouse improvements
4. **Contribute back** - If you create useful patterns, add them to the warehouse

## Troubleshooting

### Warehouse not found

```bash
# Always specify --warehouse explicitly
abc setup --warehouse ~/path/to/warehouse --all
```

### .opencode/ committed by mistake

```bash
echo ".opencode/" >> .gitignore
git rm -r --cached .opencode/
git commit -m "chore: remove .opencode from git"
```

### Want to re-install

```bash
abc clean
abc setup --warehouse ~/warehouse --all
```

## Commands Reference

| Command | What it does |
|---------|-------------|
| `abc list` | Show available warehouse content |
| `abc setup` | Install content to `.opencode/` |
| `abc status` | Show installed content |
| `abc delta` | Compare with warehouse |
| `abc update` | Sync from warehouse |
| `abc clean` | Remove `.opencode/` |

## Get Help

```bash
beacon --help
abc setup --help
abc delta --help
```

---

**For deployment guide, see:** [HOMELAB_PUBLISH.md](./HOMELAB_PUBLISH.md)
**For complete docs, see:** [README.md](./README.md)
**For project status, see:** [PROJECT_COMPLETE.md](./PROJECT_COMPLETE.md)
