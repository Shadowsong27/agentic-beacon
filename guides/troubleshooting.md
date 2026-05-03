# Troubleshooting Guide

Common issues and solutions when using Agentic Beacon v2.0.

## Command Errors

### "No such command: sync" or "No such command: setup"

**Problem:** Using old v1.x commands or wrong version installed.

**Solution:**
```bash
# Check version
abc --version

# Should show v2.0.0 or higher
# If not, upgrade:
pip install --upgrade agentic-beacon
```

### "No warehouse connected"

**Problem:** Running `abc sync` or `abc setup` without connecting to warehouse first.

**Solution:**
```bash
abc warehouse connect --path /path/to/warehouse
```

**Verify connection:**
```bash
cat .agentic-beacon/config.toml
```

Should contain:
```toml
[warehouse]
local_path = "/absolute/path/to/warehouse"
```

### "No beacon.yaml found"

**Problem:** Running `abc sync` before creating configuration.

**Solution:**
```bash
abc setup
# Then edit .agentic-beacon/beacon.yaml
abc sync
```

### "Invalid warehouse structure"

**Problem:** Connected warehouse missing required directories or files.

**Solution:**

Check warehouse has the four required directories and a README:
```
warehouse/
├── contexts/
├── knowledge/
├── skills/
├── docs/
└── README.md             ← Required
```

Fix missing items:
```bash
cd warehouse
mkdir -p contexts knowledge skills docs
touch README.md
```

## File Sync Issues

### Artifacts not syncing

**Problem:** `abc sync` completes but files missing from artifacts/.

**Diagnostic:**
```bash
# Check beacon.yaml
cat .agentic-beacon/beacon.yaml

# Verify paths exist in warehouse
ls /path/to/warehouse/knowledge/
```

**Solutions:**

1. **Pattern doesn't match:**
```yaml
# Wrong - no files match
knowledge:
  - languages/python/fastapi.md  # Doesn't exist

# Right - check actual warehouse structure
knowledge:
  - languages/python/fastapi/*.md  # Matches directory
```

2. **Glob pattern too restrictive:**
```yaml
# Restrictive
knowledge:
  - languages/python/file.md  # Only one file

# Broader
knowledge:
  - languages/python/**/*.md  # All markdown recursively
```

3. **Files don't exist in warehouse:**
```bash
# Verify file exists
ls -R /path/to/warehouse/knowledge/
```

### Files synced to wrong location

**Problem:** Artifacts appear in unexpected directories.

**Expected structure:**
```
.agentic-beacon/artifacts/
└── knowledge/
    └── languages/
        └── python/
            └── file.md
```

**Check:**
1. Warehouse structure mirrors what you want
2. beacon.yaml paths are relative to warehouse root

### Sync says "0 files" but should sync more

**Problem:** Second sync shows no changes but warehouse updated.

**Solution:**
```bash
# Pull warehouse updates
cd /path/to/warehouse
git pull

# Re-sync project
cd my-project
abc sync
```

## Configuration Issues

### Can't edit beacon.yaml

**Problem:** File is read-only or doesn't exist.

**Check permissions:**
```bash
ls -la .agentic-beacon/beacon.yaml
```

**Fix:**
```bash
chmod 644 .agentic-beacon/beacon.yaml
```

### Warehouse path changed

**Problem:** Warehouse was moved or deleted, connection stale.

**Solution:**
```bash
# Reconnect to new location
abc warehouse connect --path /new/path/to/warehouse

# Verify
cat .agentic-beacon/config.toml
```

### Multiple projects, different warehouses

**Problem:** Want different warehouses per project.

**Solution:** Each project maintains its own connection:

```bash
# Project A
cd project-a
abc warehouse connect --path ~/team-warehouse-a

# Project B
cd project-b
abc warehouse connect --path ~/team-warehouse-b
```

## Git Issues

### beacon.yaml not committed

**Problem:** beacon.yaml should be in git but isn't.

**Check .gitignore:**
```bash
grep beacon.yaml .gitignore
```

**Should NOT contain:**
```
# Wrong - don't ignore beacon.yaml
.agentic-beacon/beacon.yaml
```

**Should contain:**
```
# Correct - only ignore config and artifacts
.agentic-beacon/config.toml
.agentic-beacon/artifacts/
```

**Fix:**
```bash
# Remove from gitignore
vim .gitignore

# Commit beacon.yaml
git add .agentic-beacon/beacon.yaml
git commit -m "Add beacon.yaml configuration"
```

### Artifacts directory committed

**Problem:** `.agentic-beacon/artifacts/` in git (should be gitignored).

**Solution:**
```bash
# Ensure it's in .gitignore
echo ".agentic-beacon/artifacts/" >> .gitignore

# Remove from git but keep locally
git rm -r --cached .agentic-beacon/artifacts/
git commit -m "Remove artifacts from git"
```

### config.toml committed (should be gitignored)

**Problem:** `.agentic-beacon/config.toml` committed to git.

**Solution:**
```bash
# Add to gitignore
echo ".agentic-beacon/config.toml" >> .gitignore

# Remove from git
git rm --cached .agentic-beacon/config.toml
git commit -m "Remove config.toml from git"

# Recreate locally
abc warehouse connect --path /path/to/warehouse
```

## Team Collaboration Issues

### Team member can't sync

**Problem:** New team member gets errors when running `abc sync`.

**Checklist:**
```bash
# 1. Installed correct version
abc --version  # Should be v2.0.0+

# 2. Cloned warehouse to correct location
ls ~/team-warehouse  # Should exist

# 3. Connected to warehouse
abc warehouse connect --path ~/team-warehouse

# 4. Has beacon.yaml (from git)
cat .agentic-beacon/beacon.yaml

# 5. Can sync
abc sync
```

### Warehouse out of sync across team

**Problem:** Different team members have different warehouse versions.

**Solution:**
```bash
# Everyone update warehouse
cd ~/team-warehouse
git pull

# Everyone re-sync projects
cd my-project
abc sync
```

**Prevention:** Add to team workflow:
```bash
# Weekly sync script
cd ~/team-warehouse && git pull
cd ~/project-a && abc sync
cd ~/project-b && abc sync
```

## Performance Issues

### Sync is slow

**Problem:** `abc sync` takes long time.

**Causes:**
1. **Too many artifacts:**
```yaml
# Too broad
knowledge:
  - **/*.md  # Syncs entire warehouse

# Better
knowledge:
  - languages/python/**/*.md  # Only Python
```

2. **Large files:**
```bash
# Check artifact sizes
du -sh .agentic-beacon/artifacts/*
```

**Solutions:**
- Use more specific glob patterns
- Split large markdown files
- Remove unnecessary artifacts from beacon.yaml

### Disk space issues

**Problem:** `.agentic-beacon/artifacts/` using too much space.

**Check usage:**
```bash
du -sh .agentic-beacon/artifacts/
```

**Solutions:**

1. **Remove unused artifacts:**
```yaml
# Remove from beacon.yaml
artifacts:
  knowledge:
    # Remove this line if not needed
    # - large-dataset/**/*.md
```

```bash
abc sync  # Doesn't auto-remove
```

2. **Manual cleanup:**
```bash
rm -rf .agentic-beacon/artifacts/
abc sync  # Re-download only needed ones
```

## AI Agent Issues

### Agent not using artifacts

**Problem:** AI agent doesn't seem to reference synced artifacts.

**Verify:**

1. **Artifacts exist:**
```bash
ls .agentic-beacon/artifacts/
```

2. **Agent configured to read artifacts:**
   - Check your IDE/agent configuration
   - Ensure it's looking at `.agentic-beacon/artifacts/`

3. **Test with direct question:**
   - Ask agent about specific content from an artifact
   - Should reference the artifact if reading it

### Agent gives outdated information

**Problem:** Agent using old patterns despite syncing new artifacts.

**Solution:**
```bash
# Verify you synced
abc sync

# Check artifact content
cat .agentic-beacon/artifacts/knowledge/languages/python/type-hints.md

# If correct, restart agent/IDE
```

## Getting Help

### Enable verbose logging

```bash
abc sync --verbose
```

### Check debug information

```bash
# Version
abc --version

# Connection
cat .agentic-beacon/config.toml

# Configuration
cat .agentic-beacon/beacon.yaml

# Synced files
find .agentic-beacon/artifacts/ -type f
```

### Report an issue

When reporting issues, include:
1. Beacon version: `abc --version`
2. Command that failed: `abc sync`
3. Error message (full output)
4. Your beacon.yaml (redacted if needed)
5. Warehouse structure: `tree -L 2 warehouse/`

**GitHub Issues:** https://github.com/Shadowsong27/agentic-beacon/issues

## Quick Fixes Reference

| Problem | Quick Fix |
|---------|-----------|
| No warehouse connected | `abc warehouse connect --path <warehouse>` |
| No beacon.yaml | `abc setup` |
| Files not syncing | Check paths in beacon.yaml match warehouse |
| Slow sync | Use more specific glob patterns |
| Wrong version | `pip install --upgrade agentic-beacon` |
| Warehouse moved | Reconnect: `abc warehouse connect --path <new-path>` |
| Artifacts in git | Add to .gitignore and `git rm --cached` |
| Team out of sync | `cd warehouse && git pull && cd project && abc sync` |

## Still Stuck?

1. **Read the guides:**
   - [Getting Started](./getting-started.md)
   - [Python Project Setup](./python-project-setup.md)
   - [Team Collaboration](./team-collaboration.md)

2. **Check examples:**
   - Look in `examples/sample-warehouse/` for reference

3. **Ask for help:**
   - GitHub Discussions
   - Team chat if internal warehouse

---

**Related Guides:**
- [Getting Started](./getting-started.md)
- [Team Collaboration](./team-collaboration.md)
- [Warehouse Creation](./warehouse-creation.md)
