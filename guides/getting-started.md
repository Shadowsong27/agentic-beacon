# Getting Started with Agentic Beacon v2.0

This guide walks you through your first experience with Agentic Beacon's config-based artifact management system.

## What is Agentic Beacon?

Agentic Beacon is a framework for managing and distributing AI agent configurations across projects. Think of it like npm for AI agent artifacts:

- **Warehouse** = npm registry (stores shared artifacts)
- **beacon.yaml** = package.json (declares dependencies)
- **artifacts/** = node_modules (local snapshot)

## Prerequisites

- Python 3.11 or higher
- pip or uv package manager
- Access to a warehouse (or use the example warehouse)

## Installation

```bash
pip install agentic-beacon
```

Or with uv:

```bash
uv pip install agentic-beacon
```

Verify installation:

```bash
abc --version
```

## Your First Project Setup

### Step 1: Connect to a Warehouse

First, you need to connect your project to a warehouse. A warehouse is a repository containing shared agent configurations.

Using the example warehouse:

```bash
cd my-project
abc warehouse connect --path /path/to/warehouse

# Or let it prompt you interactively
abc warehouse connect
```

**What this does:**
- Validates the warehouse structure
- Creates `.agentic-beacon/` directory in your project
- Saves connection in `.agentic-beacon/config.toml` (gitignored)

**Expected output:**
```
Validating: /path/to/warehouse
✓ Warehouse structure validated
✓ Connection saved

✓ Connected to warehouse
  Location: /path/to/warehouse

Next Steps:
  1. Run 'abc setup' to configure artifacts
  2. Run 'abc sync' to download artifacts
```

### Step 2: Configure Your Artifacts

Create a `beacon.yaml` file that declares which artifacts your project needs:

```bash
abc setup --manual
```

**What this does:**
- Creates `.agentic-beacon/beacon.yaml` with empty template
- Provides commented examples for guidance

**The beacon.yaml file:**
```yaml
artifacts:
  knowledge: []
    # Examples:
    # - languages/python/**/*.md
    # - infrastructure/docker-standards.md
    
  skills: []
    # Examples:
    # - code-review
    # - generate-unit-tests
    
  contexts: []
    # Examples:
    # - backend-microservice
    # - data-platform
```

### Step 3: Declare Your Dependencies

Edit `.agentic-beacon/beacon.yaml` to specify what artifacts you need:

```yaml
artifacts:
  knowledge:
    - languages/python/**/*.md
    - best-practices/testing.md
  
  skills:
    - code-review
  
  contexts:
    - backend-team/AGENTS.md
```

**Glob patterns supported:**
- `**/*.md` - All .md files recursively
- `languages/*` - All items in languages/ directory
- `specific-file.md` - Exact file match

### Step 4: Sync Artifacts

Download the artifacts from the warehouse:

```bash
abc sync
```

**What this does:**
- Reads your `beacon.yaml`
- Expands glob patterns
- Copies matching files from warehouse to `.agentic-beacon/artifacts/`
- Preserves directory structure
- Uses pure copies (no symlinks for agent compatibility)

**Expected output:**
```
Syncing artifacts from warehouse...

✓ Sync complete
  Copied: 12 files
  Unchanged: 0 files
```

### Step 5: Verify Your Setup

Check what was synced:

```bash
ls -R .agentic-beacon/artifacts/
```

You should see:
```
.agentic-beacon/artifacts/
├── knowledge/
│   ├── languages/
│   │   └── python/
│   │       ├── type-hints.md
│   │       └── async-patterns.md
│   └── best-practices/
│       └── testing.md
├── skills/
│   └── code-review/
│       └── SKILL.md
└── contexts/
    └── backend-team/
        └── AGENTS.md
```

## What Gets Committed to Git?

**✅ Commit these:**
- `.agentic-beacon/beacon.yaml` - Your artifact dependencies (like package.json)

**❌ Don't commit these (automatically gitignored):**
- `.agentic-beacon/config.toml` - Your local warehouse connection
- `.agentic-beacon/artifacts/` - Downloaded artifacts (like node_modules)

The `.gitignore` is automatically updated when you run `abc warehouse connect` and `abc sync`.

## Keeping Artifacts Updated

To update artifacts when the warehouse changes:

```bash
abc sync
```

The sync is idempotent - it only copies files that have changed.

## Next Steps

- **[Python Projects](./python-project-setup.md)** - Specific setup for Python projects
- **[Team Collaboration](./team-collaboration.md)** - Sharing configurations across teams
- **[Creating a Warehouse](./warehouse-creation.md)** - Set up your own warehouse
- **[Advanced Patterns](./advanced-patterns.md)** - Glob patterns, selective syncing

## Common Issues

### "No warehouse connected" error

**Problem:** Running `abc sync` or `abc setup` without connecting first.

**Solution:**
```bash
abc warehouse connect --path /path/to/warehouse
```

### "No beacon.yaml found" error

**Problem:** Running `abc sync` without configuration.

**Solution:**
```bash
abc setup --manual
# Then edit .agentic-beacon/beacon.yaml
```

### Warehouse moved or deleted

**Problem:** Connected warehouse path is no longer valid.

**Solution:**
```bash
abc warehouse connect --path /new/path/to/warehouse
```

## Quick Reference

```bash
# Connect to warehouse
abc warehouse connect --path <warehouse-path>

# Create beacon.yaml
abc setup --manual

# Sync artifacts
abc sync

# Check connection status
cat .agentic-beacon/config.toml

# View beacon.yaml
cat .agentic-beacon/beacon.yaml

# List synced artifacts
ls -R .agentic-beacon/artifacts/
```

## Help & Support

```bash
# General help
abc --help

# Command-specific help
abc warehouse --help
abc warehouse connect --help
abc setup --help
abc sync --help
```

---

**Related Guides:**
- [Python Project Setup](./python-project-setup.md)
- [TypeScript Project Setup](./typescript-project-setup.md)
- [Team Collaboration](./team-collaboration.md)
- [Warehouse Creation Guide](./warehouse-creation.md)
