# Troubleshooting

Common issues and solutions for Agentic Beacon.

## Quick Reference

| Problem | Quick Fix |
|---------|-----------|
| No warehouse connected | `abc warehouse connect --path <path>` |
| No `beacon.yaml` | `abc setup --manual` |
| Files not syncing | Check paths in `beacon.yaml` match warehouse |
| Wrong version | `pip install --upgrade agentic-beacon` |
| Warehouse moved | `abc warehouse connect --path <new-path>` |
| Artifacts in git | Add to `.gitignore` and `git rm --cached` |
| Team out of sync | `cd warehouse && git pull && cd project && abc sync` |

---

## Command Errors

### "No such command"

**Problem:** Using old v1.x commands or wrong version installed.

```bash
abc --version    # check current version
```

Upgrade:

```bash
uv tool upgrade agentic-beacon
# or: pip install --upgrade agentic-beacon
```

### "No warehouse connected"

**Problem:** Running `abc sync` or `abc setup` without connecting to a warehouse.

```bash
abc warehouse connect --path /path/to/warehouse
```

Verify the connection:

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

```bash
abc setup --manual
# Edit .agentic-beacon/beacon.yaml
abc sync
```

### "Invalid warehouse structure"

**Problem:** Connected warehouse is missing required directories or README.

Required structure:
```
warehouse/
├── contexts/
├── knowledge/
├── skills/
├── docs/
└── README.md   ← required
```

Fix missing items:
```bash
cd warehouse
mkdir -p contexts knowledge skills docs
touch README.md
```

### "Warehouse has uncommitted changes"

**Problem:** `abc sync` or `abc contribute` blocked because the warehouse has uncommitted changes.

```bash
cd ~/my-org-warehouse
git status      # see what's changed
git stash       # or commit the changes
```

Or bypass with:
```bash
abc sync --skip-git-check
```

### "Warehouse is behind its remote"

**Problem:** Warehouse is behind remote by N commits.

```bash
cd ~/my-org-warehouse
git pull
```

---

## File Sync Issues

### Artifacts not appearing after sync

**Problem:** `abc sync` completes but expected files are missing.

**Diagnostic:**
```bash
cat .agentic-beacon/beacon.yaml      # check declared paths
ls /path/to/warehouse/knowledge/     # verify paths exist in warehouse
abc status                           # check sync state
```

**Common causes:**

1. **Pattern doesn't match any files:**

```yaml
# Wrong — path doesn't exist
knowledge:
  - languages/python/fastapi.md

# Right — check the actual warehouse structure
knowledge:
  - languages/python/fastapi/*.md
```

2. **Glob too narrow:**

```yaml
# Narrow — only one file
knowledge:
  - languages/python/type-hints.md

# Broader — all markdown under python/
knowledge:
  - languages/python/**/*.md
```

### "0 files" on re-sync despite warehouse updates

**Problem:** Sync shows no changes but warehouse was updated.

```bash
# Pull warehouse updates
cd /path/to/warehouse && git pull

# Re-sync
cd my-project && abc sync
```

---

## Configuration Issues

### Warehouse path changed

```bash
abc warehouse connect --path /new/path/to/warehouse
```

### Multiple projects, different warehouses

Each project maintains its own connection:

```bash
cd project-a && abc warehouse connect --path ~/warehouse-a
cd project-b && abc warehouse connect --path ~/warehouse-b
```

---

## Git Issues

### `beacon.yaml` not committed

`beacon.yaml` should be in git; `config.toml` and `artifacts/` should not.

Check `.gitignore`:
```bash
cat .gitignore | grep beacon
```

Should **not** contain `.agentic-beacon/beacon.yaml`. Should contain:
```
.agentic-beacon/config.toml
.agentic-beacon/artifacts/
```

Commit `beacon.yaml`:
```bash
git add .agentic-beacon/beacon.yaml
git commit -m "chore: add artifact dependencies"
```

### Artifacts directory accidentally committed

```bash
echo ".agentic-beacon/artifacts/" >> .gitignore
git rm -r --cached .agentic-beacon/artifacts/
git commit -m "chore: remove artifacts from git"
```

### `config.toml` accidentally committed

```bash
echo ".agentic-beacon/config.toml" >> .gitignore
git rm --cached .agentic-beacon/config.toml
git commit -m "chore: remove config.toml from git"

# Recreate locally
abc warehouse connect --path /path/to/warehouse
```

---

## Team Issues

### New team member can't sync

Checklist:
```bash
# 1. Correct version installed
abc --version

# 2. Warehouse cloned
ls ~/team-warehouse

# 3. Connected to warehouse
abc warehouse connect --path ~/team-warehouse

# 4. beacon.yaml present (from git)
cat .agentic-beacon/beacon.yaml

# 5. Sync
abc sync
```

### Team out of sync with warehouse

```bash
# Everyone: update warehouse and re-sync
cd ~/team-warehouse && git pull
cd my-project && abc sync
```

---

## AI Agent Issues

### Agent not using synced contexts

1. Verify artifacts exist:
```bash
ls .agentic-beacon/artifacts/contexts/
```

2. Verify wiring:
```bash
# Claude Code
cat AGENTS.md | grep agentic-beacon

# OpenCode
cat opencode.json | grep agentic-beacon
```

3. Re-run sync if wiring is missing:
```bash
abc sync
```

### Agent gives outdated information despite syncing

```bash
# Verify sync ran
abc sync --verbose

# Check artifact content
cat .agentic-beacon/artifacts/knowledge/python/type-hints.md

# If content is correct, restart your agent session
```

---

## Getting Help

### Enable verbose output

```bash
abc sync --verbose
abc doctor
```

### Collect diagnostic info

```bash
abc --version
cat .agentic-beacon/config.toml
cat .agentic-beacon/beacon.yaml
abc status
```

### Report an issue

When reporting, include:

1. `abc --version`
2. The exact command that failed
3. The full error output
4. Your `beacon.yaml`
5. Warehouse structure: `ls -R /path/to/warehouse | head -40`

**GitHub Issues:** [github.com/Shadowsong27/agentic-beacon/issues](https://github.com/Shadowsong27/agentic-beacon/issues)
