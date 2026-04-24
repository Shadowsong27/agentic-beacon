---
name: record-skill
description: Pattern for extracting operational scripts from hosts/ into dedicated skills. Use when you encounter scripts embedded in infrastructure directories that should be reusable, atomic skill operations.
---

# SKILL: Record Skill — Extract Scripts into Dedicated Skills

## Philosophy

Operational scripts belong in **skills**, not in `hosts/<host>/services/<service>/scripts/`. Skills are:

- **Atomic** — one concern per skill
- **Reusable** — callable from any context without coupling to a specific host
- **Self-contained** — dependencies declared inline (PEP 723 for Python) or clearly documented
- **Versioned with intent** — the skill captures the *operation*, not the *location*

## When to Apply This Pattern

Apply when you find scripts in these locations:

- `hosts/<host>/services/<service>/scripts/`
- `hosts/<host>/scripts/`
- Ad-hoc scripts committed next to docker-compose files

**Do NOT extract:**
- One-time migration scripts
- Host-specific configuration files (SSH keys, systemd units)
- Scripts that are literally part of the service image build

## Decision Tree

```
Script found in hosts/
    |
    +-- Is it an operational tool? (create bucket, clean disk, manage user)
    |       +-- YES → Extract to skill
    |       +-- NO  → Leave in place
    |
    +-- Is it coupled to a specific host path?
    |       +-- YES → Parameterize it, then extract
    |       +-- NO  → Extract as-is
    |
    +-- Does it need to run as part of service startup?
            +-- YES → Leave in hosts/ or move to image
            +-- NO  → Extract to skill
```

## Workflow

### Step 1: Identify the Script(s)

```bash
find hosts/ -name "*.sh" -o -name "*.py" | grep -E "scripts/|bin/"
```

### Step 2: Choose Skill Location

| Scope | Location | Example |
|-------|----------|---------|
| Project-specific | `.opencode/skills/<skill-name>/` | `minio-ops`, `runner-disk-cleanup` |
| Global (cross-project) | `~/.config/opencode/skills/<skill-name>/` | `record-knowledge` |

Use **project-specific** when the script targets project infrastructure (e.g., homelab MinIO). Use **global** when the pattern itself is reusable.

### Step 3: Create Skill Structure

```bash
mkdir -p <skill-dir>/scripts
touch <skill-dir>/SKILL.md
```

For **Python scripts** — convert to PEP 723 inline scripts:

```python
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "minio>=7.2.0",
#   "click>=8.1.0",
#   "loguru>=0.7.0",
# ]
# ///
```

For **bash scripts** — keep as `.sh` with clear headers:

```bash
#!/bin/bash
# Script: <name>
# Purpose: <one-line description>
# Host: <target host>
# Usage: <how to invoke>
```

### Step 4: Move and Adapt

1. Copy script to `<skill-dir>/scripts/`
2. Remove host-specific hardcoding (URLs, paths) if possible
3. Parameterize via CLI flags or environment variables
4. Update comments to reference `${SKILL_DIR}` instead of hard paths

### Step 5: Write SKILL.md

Template:

```markdown
---
name: <skill-name>
description: <one-line purpose>
---

# SKILL: <Skill Name>

## Role & Purpose

<what this skill does>

## Scripts

| Script | Purpose |
|--------|---------|
| `${SKILL_DIR}/scripts/<script>` | <description> |

## Usage

```bash
<command examples using ${SKILL_DIR}>
```

## Prerequisites

<env vars, ssh access, etc.>

## Important Notes

<critical warnings>
```

### Step 6: Update References

Remove script from `hosts/` and update all references:

```bash
# Find references
grep -r "hosts/.*/scripts/<script>" .

# Update docs, READMEs, other skills
grep -r "<old-path>" . --include="*.md" --include="*.sh"
```

### Step 7: Test

For Python (PEP 723):
```bash
uv run ${SKILL_DIR}/scripts/script.py --help
```

For bash:
```bash
bash -n ${SKILL_DIR}/scripts/script.sh
ssh root@<host> "bash -s" < ${SKILL_DIR}/scripts/script.sh
```

## Examples

### Example 1: MinIO Operations (Python)

**Before:** `hosts/truenas/services/minio/scripts/minio_admin.py`

**After:** `.opencode/skills/minio-ops/scripts/minio_admin.py` (PEP 723 inline)

**Usage change:**
```bash
# Before
uv run --with "minio>=7.2.0,..." python hosts/truenas/services/minio/scripts/minio_admin.py ...

# After
uv run ${SKILL_DIR}/scripts/minio_admin.py ...
```

### Example 2: Runner Disk Cleanup (Bash)

**Before:** `hosts/prod-github-runner/scripts/disk-cleanup.sh`

**After:** `.opencode/skills/runner-disk-cleanup/scripts/disk-cleanup.sh`

**Usage change:**
```bash
# Before
ssh root@192.168.88.7 "bash -s" < hosts/prod-github-runner/scripts/setup-cleanup-cron.sh

# After
ssh root@192.168.88.7 "cat > /usr/local/bin/runner-disk-cleanup.sh" < ${SKILL_DIR}/scripts/disk-cleanup.sh
ssh root@192.168.88.7 "bash -s" < ${SKILL_DIR}/scripts/setup-cleanup-cron.sh
```

## Anti-Patterns

❌ **Leaving scripts in hosts/ because "that's where they run"** — Skills can target any host; the skill is the operation, the host is the parameter.

❌ **Bundling unrelated operations into one skill** — Disk cleanup and runner setup are orthogonal; they deserve separate skills.

❌ **Duplicating requirements.txt** — Use PEP 723 inline metadata for Python scripts instead.

❌ **Hardcoding host paths in skills** — Use CLI args or env vars; document defaults in SKILL.md.

## Related

- `minio-ops` — Example of a Python PEP 723 skill
- `runner-disk-cleanup` — Example of a bash skill
- `record-knowledge` — Global skill for capturing decisions and lessons
