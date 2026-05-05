# Troubleshooting

Common issues and solutions for Agentic Beacon.

## Quick Reference

| Problem | Quick Fix |
|---------|-----------|
| No warehouse connected | `abc warehouse connect --path <path>` |
| No `beacon.yaml` | `abc setup` |
| Files not syncing | Check paths in `beacon.yaml` match warehouse |
| Wrong version | `pip install --upgrade agentic-beacon` |
| Warehouse moved | `abc warehouse connect --path <new-path>` |
| Artifacts in git | Add to `.gitignore` and `git rm --cached` |
| Team out of sync | `cd warehouse && git pull && cd project && abc sync` |
| Skill frontmatter missing | Add `requires:` block to skill's `SKILL.md` |

---

## Command Errors

### "No such command"

**Problem:** Using old v1.x or v2.x commands that have been removed.

```bash
abc --version    # check current version
```

Removed commands and their replacements:

| Removed | Use instead |
|---------|-------------|
| `abc delta` | `abc warehouse status` |
| `abc contribute` | `abc warehouse contribute -m "message"` |
| `abc install <artifact>` | Edit `beacon.yaml`, then `abc sync` |
| `abc sync --preserve` | `abc sync --contribute-local` or `--discard-local` |
| `abc setup --manual` | `abc setup` (no flags needed) |
| `abc setup --agent-assisted` | `abc setup` (no flags needed) |

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
abc setup
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

**Problem:** `abc sync` blocked because the warehouse has uncommitted changes.

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

### "Skill frontmatter missing or invalid"

**Problem:** `abc sync` fails because an adopted skill is missing `requires:` frontmatter.

Every skill's `SKILL.md` must include:

```yaml
---
requires:
  contexts:
    - global.md
    - teams/backend/AGENTS.md
---
```

Add the missing frontmatter block to the skill's `SKILL.md` in the warehouse, then re-sync.

---

## File Sync Issues

### Artifacts not appearing after sync

**Problem:** `abc sync` completes but expected files are missing.

**Diagnostic:**
```bash
cat .agentic-beacon/beacon.yaml      # check declared paths
ls /path/to/warehouse/contexts/      # verify paths exist in warehouse
abc status                           # check sync status
```

**Common causes:**

1. **Pattern doesn't match any files:** Check the actual warehouse directory structure
2. **Knowledge not auto-derived:** Knowledge files are only synced when referenced by a markdown link from an adopted context or skill. Add a link like `[guide](knowledge/path/file.md)` to your context file.
3. **Skill dependency not satisfied:** Skills won't sync if their `requires:` context dependencies aren't available in the warehouse

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
cat CLAUDE.md | grep agentic-beacon

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
