# Connecting a Project

Once a warehouse exists, connect your project to it and declare which artifacts you need.

## Prerequisites

- A warehouse repository (local path)
- `abc` installed (`uv tool install agentic-beacon`)
- An existing project directory

---

## Step 1: Clone the Warehouse Locally

```bash
git clone git@github.com:your-org/warehouse.git ~/my-org-warehouse
```

The warehouse must be present locally — `abc sync` reads directly from the filesystem.

---

## Step 2: Connect Your Project

```bash
cd my-project
abc warehouse connect --path ~/my-org-warehouse
```

This creates `.agentic-beacon/config.toml` (gitignored) pointing to the warehouse:

```toml
[warehouse]
local_path = "/Users/you/my-org-warehouse"
```

Expected output:
```
✓ Warehouse structure validated
✓ Connected to warehouse
  Location: /Users/you/my-org-warehouse

Next Steps:
  1. Run 'abc setup' to configure artifacts
  2. Run 'abc sync' to sync artifacts
```

---

## Step 3: Select Artifacts

### Option A: Interactive TUI (Recommended)

```bash
abc adopt
```

Opens a TUI where you browse artifacts grouped by type. Press `Space` to select, `Enter` to confirm. Writes selections to `beacon.yaml` automatically.

→ **[Interactive Adoption](interactive-adoption.md)** for full details.

### Option B: Manual configuration

```bash
abc setup
```

Creates a `beacon.yaml` template at `.agentic-beacon/beacon.yaml`. Edit it manually to declare which contexts, skills, and agents you need:

```yaml
artifacts:
  skills:
    - skills/code-review/

  contexts:
    - contexts/global.md

  agents:
    - agents/code-reviewer.md
```

**Knowledge is auto-derived** — knowledge files referenced by markdown links in your contexts and skills are synced automatically. No manual knowledge configuration needed.

---

## Step 4: Sync

```bash
abc sync
```

Reads `beacon.yaml`, resolves skill→context dependencies via frontmatter, auto-derives knowledge from markdown links, and performs the full sync:

- **Contexts** → symlinked into `.agentic-beacon/artifacts/contexts/` and wired into `CLAUDE.md` or `opencode.json`
- **Skills** → symlinked into `.agentic-beacon/artifacts/skills/` and installed into each detected tool's directories
- **Knowledge** → auto-derived from markdown links and symlinked into `.agentic-beacon/artifacts/knowledge/`
- **Agents** → declared per-project in `beacon.yaml` and wired into project-local `.claude/agents/` and `.opencode/agents/` symlinks

---

## Step 5: Commit beacon.yaml

```bash
git add .agentic-beacon/beacon.yaml
git commit -m "chore: add beacon.yaml artifact dependencies"
```

Teammates clone the repo, run `abc warehouse connect`, and `abc sync` to get the same artifacts.

---

## What Gets Committed to Git

```
✅  .agentic-beacon/beacon.yaml       — commit this
❌  .agentic-beacon/config.toml      — gitignored (local path)
❌  .agentic-beacon/artifacts/       — gitignored (symlink tree)
```

The `.gitignore` entries are added automatically by `abc warehouse connect` and `abc sync`.

---

## Keeping Artifacts Updated

When the warehouse changes:

```bash
# Pull warehouse updates
cd ~/my-org-warehouse && git pull

# Re-sync your project
cd my-project && abc sync
```

Sync is idempotent — only changed files are updated.

---

## Verifying Your Setup

```bash
abc status
```

Shows the connected warehouse, configured contexts and skills (with ✓/✗ for synced status), and total synced file count.

```bash
abc doctor
```

Validates the full setup — connection, `beacon.yaml` validity, missing artifacts. Use `--fix` to auto-migrate stale paths.

---

## Next Steps

- **[beacon.yaml Reference](../reference/beacon-yaml.md)** — full configuration schema
- **[Syncing Artifacts](syncing.md)** — sync flags and behavior
- **[Interactive Adoption](interactive-adoption.md)** — the `abc adopt` TUI
