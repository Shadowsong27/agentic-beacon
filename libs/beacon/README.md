# Agentic Beacon CLI

CLI tool for distributing agentic engineering contexts, knowledge, and skills from a warehouse repository to project `.opencode` directories.

## Overview

This tool enables the **DRY (Don't Repeat Yourself)** principle for agentic knowledge management:

- **Centralized warehouse**: Store all contexts, knowledge, and skills in one place
- **Fork workflow**: Fork the warehouse template to create your organization's warehouse
- **Local distribution**: Use the CLI to distribute content to gitignored `.opencode` folders in projects
- **Easy updates**: Sync latest changes from the warehouse with one command

## Installation

### Recommended: Install with uv (if you have uv installed)

The best way to install `abc` is using `uv tool install`, which installs it in an isolated environment:

```bash
# Install once, use anywhere
uv tool install agentic-beacon

# Verify installation
abc --help

# Update to latest version
uv tool upgrade agentic-beacon

# Uninstall
uv tool uninstall agentic-beacon
```

### Alternative Installation Methods

```bash
# Using pipx (similar to uv tool, isolated environment)
pipx install agentic-beacon

# Using pip (global Python environment)
pip install agentic-beacon

# One-off execution without installation
uvx --from agentic-beacon abc init my-warehouse
```

## Usage

All examples below use the `abc` command directly (after installation).

### 1. List Available Content

```bash
# List all available contexts, knowledge, and skills
abc list

# From a specific warehouse location
abc list --warehouse /path/to/warehouse
```

### 2. Setup (First Time)

```bash
# Interactive mode (recommended for first time)
abc setup --interactive

# Install specific content
abc setup \
  --context global \
  --context python \
  --knowledge global \
  --knowledge languages/python \
  --skill example-skill

# Install everything
abc setup --all

# Specify warehouse and project locations
abc setup --all \
  --warehouse /path/to/warehouse \
  --project /path/to/project
```

**What it does:**
- Creates `.opencode/` directory in your project (gitignored)
- Copies selected contexts to `.opencode/contexts/`
- Copies selected knowledge to `.opencode/knowledge/`
- Copies selected skills to `.opencode/skills/`
- Saves configuration for future updates

### 3. Update Existing Installation

```bash
# Update all installed content from warehouse
agentic update

# From a specific warehouse location
agentic update --warehouse /path/to/warehouse
```

**What it does:**
- Reads existing `.opencode/.warehouse-config.yml`
- Re-copies all previously selected content
- Overwrites with latest versions from warehouse

### 4. Check Installation Status

```bash
# Show what's currently installed
agentic status

# For a specific project
agentic status --project /path/to/project
```

### 5. Clean Installation

```bash
# Remove .opencode directory
agentic clean

# Will prompt for confirmation
```

## Workflow

### For Organization Admins

1. **Create warehouse**: Fork the template repository
   ```bash
   # Use GitHub's "Use this template" button
   # Name it: your-org-agentic-warehouse
   ```

2. **Customize content**: Add your organization's contexts, knowledge, and skills
   ```
   your-org-agentic-warehouse/
   ├── contexts/
   │   ├── AGENTS.global.md
   │   ├── AGENTS.python.md
   │   └── AGENTS.your-domain.md
   ├── knowledge/
   │   ├── global/
   │   ├── languages/python/
   │   └── domains/your-domain/
   └── skills/
       └── your-skill/
   ```

3. **Distribute to teams**: Team members clone and install

### For Team Members

1. **Clone warehouse** (one time):
   ```bash
   git clone https://github.com/your-org/agentic-warehouse.git ~/agentic-warehouse
   cd ~/agentic-warehouse
   pip install -e libs/agentic_warehouse_cli
   ```

2. **Setup in project** (per project):
   ```bash
   cd ~/your-project
   agentic setup --warehouse ~/agentic-warehouse --interactive
   ```

3. **Update when needed**:
   ```bash
   cd ~/your-project
   agentic update --warehouse ~/agentic-warehouse
   ```

4. **Add to .gitignore**:
   ```
   # Add to your project's .gitignore
   .opencode/
   ```

## Directory Structure

### Warehouse Structure
```
your-org-agentic-warehouse/
├── contexts/
│   ├── AGENTS.global.md
│   ├── AGENTS.python.md
│   └── AGENTS.data-platform.md
├── knowledge/
│   ├── global/
│   │   ├── decisions/
│   │   ├── lessons/
│   │   └── facts/
│   ├── languages/
│   │   └── python/
│   └── domains/
│       └── data-platform/
├── skills/
│   └── example-skill/
│       └── SKILL.md
└── libs/
    └── agentic_warehouse_cli/  # This CLI tool
```

### Project Structure (After Setup)
```
your-project/
├── .opencode/                    # gitignored
│   ├── .warehouse-config.yml    # Tracks what's installed
│   ├── contexts/
│   │   ├── AGENTS.global.md
│   │   └── AGENTS.python.md
│   ├── knowledge/
│   │   ├── global/
│   │   └── languages/
│   │       └── python/
│   └── skills/
│       └── example-skill/
├── .gitignore                    # Contains .opencode/
└── ...
```

## Configuration

The CLI auto-saves configuration to `.opencode/.warehouse-config.yml`:

```yaml
contexts:
  - global
  - python
knowledge_scopes:
  - global
  - languages/python
skills:
  - example-skill
```

This configuration is used by the `update` command to know what to refresh.

## Auto-Detection

The CLI automatically detects:

- **Warehouse root**: Looks for directories containing `contexts/`, `knowledge/`, and `skills/`
- **Project root**: Looks for `.git` directory or uses current directory

You can override with `--warehouse` and `--project` options.

## Examples

### Example 1: Setup Python Project

```bash
cd ~/my-python-project

# Interactive setup
agentic setup --interactive

# Select:
#   Contexts: global, python
#   Knowledge: global, languages/python
#   Skills: none

# Result: .opencode/ created with selected content
```

### Example 2: Setup Data Platform Project

```bash
cd ~/data-platform-project

# Non-interactive setup
agentic setup \
  --context global \
  --context python \
  --context data-platform \
  --knowledge global \
  --knowledge languages/python \
  --knowledge domains/data-platform \
  --skill deploy-airflow

# Result: Full data platform context installed
```

### Example 3: Update After Warehouse Changes

```bash
cd ~/my-project

# Warehouse maintainers updated content
# Pull latest warehouse changes
cd ~/agentic-warehouse
git pull origin main

# Update project installation
cd ~/my-project
agentic update

# Result: Latest content synced to .opencode/
```

### Example 4: Check What's Installed

```bash
cd ~/my-project
agentic status

# Output:
# Installation: /Users/you/my-project/.opencode
# 
# Installed Contexts
# ┌─────────┐
# │ Context │
# ├─────────┤
# │ global  │
# │ python  │
# └─────────┘
```

## Development

### Running Tests

```bash
cd libs/agentic_warehouse_cli
pytest
```

### Building Package

```bash
pip install build
python -m build
```

## Troubleshooting

### CLI not found after installation

```bash
# Make sure you're in the right environment
which agentic

# Reinstall
pip install -e libs/agentic_warehouse_cli --force-reinstall
```

### Warehouse not auto-detected

```bash
# Explicitly specify warehouse path
agentic setup --warehouse /path/to/warehouse
```

### .opencode not in .gitignore

```bash
# Add to .gitignore
echo ".opencode/" >> .gitignore
```

## License

MIT
