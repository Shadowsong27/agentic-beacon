# Quick Start Guide: Agentic Warehouse CLI

## For Warehouse Administrators

### 1. Install the CLI in your warehouse

```bash
# From your warehouse repository root
pip install -e libs/agentic_warehouse_cli
```

### 2. Verify installation

```bash
agentic --help
```

### 3. Test distribution (from warehouse root)

```bash
# List available content
agentic list

# Expected output:
# - Contexts: global, python, example-domain
# - Knowledge: global, languages/python, domains/example-domain
# - Skills: example-skill
```

## For Project Users

### 1. Setup in your project

```bash
# Navigate to your project
cd ~/your-project

# Interactive setup (recommended)
agentic setup --warehouse ~/path/to/warehouse --interactive

# Or specify content directly
agentic setup --warehouse ~/path/to/warehouse \
  --context global \
  --context python \
  --knowledge global \
  --knowledge languages/python
```

### 2. Verify installation

```bash
# Check status
agentic status

# Verify .opencode directory
ls -la .opencode/
```

### 3. Add to .gitignore

```bash
# Ensure .opencode is gitignored
echo ".opencode/" >> .gitignore
```

## Common Workflows

### Workflow 1: Full Setup (Everything)

```bash
cd ~/my-project
agentic setup --warehouse ~/warehouse --all
agentic status
```

### Workflow 2: Selective Setup (Python only)

```bash
cd ~/my-python-project
agentic setup --warehouse ~/warehouse \
  --context global \
  --context python \
  --knowledge global \
  --knowledge languages/python
```

### Workflow 3: Update After Warehouse Changes

```bash
# Update warehouse
cd ~/warehouse
git pull origin main

# Update project
cd ~/my-project
agentic update --warehouse ~/warehouse
```

### Workflow 4: Clean and Reinstall

```bash
cd ~/my-project
agentic clean
agentic setup --warehouse ~/warehouse --all
```

## Directory Structure After Setup

```
your-project/
├── .opencode/                       # Created by CLI (gitignored)
│   ├── .warehouse-config.yml       # Tracks installation
│   ├── contexts/
│   │   ├── AGENTS.global.md
│   │   └── AGENTS.python.md
│   ├── knowledge/
│   │   ├── global/
│   │   │   ├── decisions/
│   │   │   └── lessons/
│   │   └── languages/
│   │       └── python/
│   └── skills/
│       └── example-skill/
├── .gitignore                       # Contains .opencode/
└── (your project files)
```

## Troubleshooting

### Issue: Command not found

```bash
# Reinstall
cd ~/warehouse
pip install -e libs/agentic_warehouse_cli --force-reinstall
```

### Issue: Warehouse not detected

```bash
# Always specify --warehouse explicitly
agentic list --warehouse ~/warehouse
agentic setup --warehouse ~/warehouse --all
```

### Issue: .opencode not in .gitignore

```bash
# Add it manually
echo ".opencode/" >> .gitignore
git add .gitignore
git commit -m "chore: ignore .opencode directory"
```

## Next Steps

1. **Customize warehouse**: Add your organization's contexts, knowledge, and skills
2. **Distribute to teams**: Share warehouse repository with team members
3. **Keep updated**: Regularly pull warehouse updates and run `agentic update`
