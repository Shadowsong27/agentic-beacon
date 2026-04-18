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
  1. Run 'abc adopt' to browse and select artifacts
  2. Run 'abc sync' to download artifacts
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
abc setup --manual
```

Creates an empty `beacon.yaml` template at `.agentic-beacon/beacon.yaml`. Edit it manually to declare which artifacts you need:

```yaml
artifacts:
  knowledge:
    - knowledge/python/**/*.md
    - knowledge/decisions/coding-standards.md

  skills:
    - skills/code-review/

  contexts:
    - contexts/global.md
```

### Option C: Agent-assisted

```bash
abc setup --agent-assisted
```

Generates a `warehouse-catalog.md` with a listing of all available artifacts. Use this with your AI agent to help populate `beacon.yaml`.

---

## Step 4: Sync

```bash
abc sync
```

Reads `beacon.yaml` and performs the full sync:

- **Knowledge** → copied to `.agentic-beacon/artifacts/knowledge/`
- **Contexts** → copied and wired into `AGENTS.md` or `opencode.json`
- **Skills** → copied and installed into each detected tool's directories
- **Agents** → installed into global tool directories

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
❌  .agentic-beacon/artifacts/       — gitignored (downloaded snapshot)
❌  .agentic-beacon/warehouse-catalog.md  — gitignored
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

Sync is idempotent — only changed files are re-copied.

---

## Verifying Your Setup

```bash
abc status
```

Shows the connected warehouse, configured artifacts, and sync state.

```bash
abc doctor
```

Validates the full setup — connection, `beacon.yaml` validity, missing artifacts. Use `--fix` to auto-migrate stale paths.

---

## Next Steps

- **[beacon.yaml Reference](../reference/beacon-yaml.md)** — full configuration schema
- **[Syncing Artifacts](syncing.md)** — sync flags and behavior
- **[Interactive Adoption](interactive-adoption.md)** — the `abc adopt` TUI
