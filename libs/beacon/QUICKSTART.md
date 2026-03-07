# Beacon Quick Start

## Installation (Homelab)

```bash
pip install beacon --index-url https://your-homelab-pypi.local/simple/
```

## Verify Installation

```bash
beacon --help
```

## Basic Usage

### 1. List Available Content

```bash
# From warehouse directory
cd ~/your-warehouse
beacon list
```

Output shows available contexts, knowledge, and skills.

### 2. Setup in Project

```bash
# Navigate to your project
cd ~/my-project

# Install all content
beacon setup --warehouse ~/your-warehouse --all

# Or selective install
beacon setup --warehouse ~/your-warehouse \
  -c global \
  -c python \
  -k global \
  -k languages/python
```

### 3. Check Status

```bash
beacon status
```

Shows what's currently installed in `.opencode/`.

### 4. Compare with Warehouse (Delta)

```bash
beacon delta --warehouse ~/your-warehouse
```

Shows:
- **New files** in your project (potential contributions)
- **Modified files** in your project (local customizations)
- **Missing files** (available in warehouse)

### 5. Update from Warehouse

```bash
beacon update --warehouse ~/your-warehouse
```

Syncs latest changes from warehouse to your project.

### 6. Clean Installation

```bash
beacon clean
```

Removes `.opencode/` directory.

## Common Workflows

### Workflow 1: New Project Setup

```bash
cd ~/new-project
beacon setup --warehouse ~/warehouse --all
echo ".opencode/" >> .gitignore
git add .gitignore
git commit -m "chore: add beacon setup"
```

### Workflow 2: Check for Changes

```bash
# After working on your project
beacon delta

# If you have new patterns, contribute back to warehouse
# Copy files from .opencode/ to warehouse and submit PR
```

### Workflow 3: Sync with Warehouse

```bash
# When warehouse is updated
cd ~/warehouse && git pull
cd ~/my-project
beacon update
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
2. **Use `beacon delta` regularly** - Catch local customizations that should be shared
3. **Update frequently** - Stay in sync with warehouse improvements
4. **Contribute back** - If you create useful patterns, add them to the warehouse

## Troubleshooting

### Warehouse not found

```bash
# Always specify --warehouse explicitly
beacon setup --warehouse ~/path/to/warehouse --all
```

### .opencode/ committed by mistake

```bash
echo ".opencode/" >> .gitignore
git rm -r --cached .opencode/
git commit -m "chore: remove .opencode from git"
```

### Want to re-install

```bash
beacon clean
beacon setup --warehouse ~/warehouse --all
```

## Commands Reference

| Command | What it does |
|---------|-------------|
| `beacon list` | Show available warehouse content |
| `beacon setup` | Install content to `.opencode/` |
| `beacon status` | Show installed content |
| `beacon delta` | Compare with warehouse |
| `beacon update` | Sync from warehouse |
| `beacon clean` | Remove `.opencode/` |

## Get Help

```bash
beacon --help
beacon setup --help
beacon delta --help
```

---

**For deployment guide, see:** [HOMELAB_PUBLISH.md](./HOMELAB_PUBLISH.md)  
**For complete docs, see:** [README.md](./README.md)  
**For project status, see:** [PROJECT_COMPLETE.md](./PROJECT_COMPLETE.md)
