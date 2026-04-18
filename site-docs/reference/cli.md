# CLI Reference

Complete reference for the `abc` CLI. All commands are subcommands of `abc`.

```bash
abc --help               # list all commands
abc <command> --help     # help for a specific command
abc --version            # show version
```

---

## Warehouse Commands

### `abc warehouse init`

Initialize a new warehouse repository.

```bash
abc warehouse init [NAME] [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `NAME` | Warehouse directory name (prompted if omitted) |
| `--path PATH` | Create warehouse at this path |
| `--org TEXT` | Organization name (used in generated templates) |
| `--languages TEXT` | Comma-separated languages to pre-populate |
| `--domains TEXT` | Comma-separated domains to pre-populate |
| `--no-git` | Skip `git init` |
| `--no-interactive` | Use defaults without prompting |

**Example:**
```bash
abc warehouse init my-org-warehouse
abc warehouse init my-warehouse --path ~/projects --no-interactive
```

---

### `abc warehouse connect`

Connect a project to a warehouse.

```bash
abc warehouse connect [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--path PATH` | Path to the warehouse (required) |

Creates `.agentic-beacon/config.toml` (gitignored) with the warehouse location.

**Example:**
```bash
abc warehouse connect --path ~/my-org-warehouse
```

---

### `abc warehouse list`

List warehouses or artifacts within a connected warehouse.

```bash
abc warehouse list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--artifact-type TYPE` | Filter by type: `agents`, `knowledge`, `skills`, `contexts` |

---

### `abc warehouse template-upgrade`

Upgrade warehouse template documentation to the latest version.

```bash
abc warehouse template-upgrade [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview changes without applying |
| `--interactive` | Prompt before each change |
| `--force` | Apply without confirmation |

---

## Project Setup

### `abc setup`

Create `.agentic-beacon/beacon.yaml` configuration.

```bash
abc setup [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--manual` | Create an empty template for manual editing |
| `--agent-assisted` | Create template + `warehouse-catalog.md` for AI assistance |

**Example:**
```bash
abc setup --manual
abc setup --agent-assisted
```

---

## Core Commands

### `abc adopt`

Open an interactive TUI to browse and select warehouse artifacts. Writes selections to `beacon.yaml` and syncs immediately.

```bash
abc adopt [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview available artifacts without making changes |
| `--all` | Show all artifacts, including already-adopted ones |

**Keyboard shortcuts in TUI:**

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate |
| `Space` | Toggle selection |
| `Enter` | Confirm and write to `beacon.yaml` |
| `a` / `n` | Select all / Select none |
| `t` | Toggle show-all |
| `Esc` / `q` | Cancel |

---

### `abc sync`

Sync all artifacts declared in `beacon.yaml` from the warehouse.

```bash
abc sync [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--preserve` | Skip files with local modifications |
| `--force` | Overwrite all artifacts, ignoring local changes |
| `--dry-run` | Preview what would be synced without copying |
| `--verbose` | Show per-file sync output |
| `--skip-git-check` | Skip warehouse git state validation |

**What sync does per artifact type:**

| Artifact | Action |
|---|---|
| Knowledge | Copy to `.agentic-beacon/artifacts/knowledge/` |
| Contexts | Copy + wire into `AGENTS.md` or `opencode.json` |
| Skills | Copy + install into tool-specific directories |
| Agents | Install into global tool directories |

---

### `abc install`

Sync and wire a single artifact from the warehouse.

```bash
abc install ARTIFACT [OPTIONS]
```

| Argument / Option | Description |
|---|---|
| `ARTIFACT` | Artifact path relative to warehouse root (e.g. `skills/code-review/`) |
| `--agent TYPE` | Target agent: `opencode` or `claudecode` |
| `--preserve` | Skip if local modification exists |
| `--force` | Overwrite local modifications |

**Examples:**
```bash
abc install skills/code-review/
abc install contexts/global.md
abc install agents/reviewer.md
```

Adds the artifact to `beacon.yaml` automatically.

---

### `abc agents sync`

Sync agent definitions from the warehouse into global tool directories.

```bash
abc agents sync [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--preserve` | Skip agents with local modifications |
| `--force` | Overwrite local modifications |
| `--skip-git-check` | Skip warehouse git state validation |

Does not require `beacon.yaml` — works in any project connected to a warehouse.

---

## Comparison & Contribution

### `abc delta`

Compare local artifacts with the warehouse.

```bash
abc delta [FILE] [OPTIONS]
```

| Argument / Option | Description |
|---|---|
| `FILE` | Optional: show detailed line-by-line diff for this file |
| `--no-color` | Disable color output |

**Without `FILE` — summary view:**

```
Delta Summary
──────────────────────────────────────
MODIFIED  knowledge/python/type-hints.md
ADDED     knowledge/python/new-lesson.md

  Modified: 1  Added: 1
```

**With `FILE` — detailed diff:**

```bash
abc delta knowledge/python/type-hints.md
```

**Status values:**

| Status | Meaning |
|--------|---------|
| `MODIFIED` | Exists locally and in warehouse with different content |
| `ADDED` | Exists locally but not in warehouse |
| `MISSING` | In `beacon.yaml` but not synced yet |
| `IDENTICAL` | Matches warehouse exactly |
| `STALE` | Synced from an older warehouse version |

---

### `abc contribute`

Copy local artifact changes back to the warehouse.

```bash
abc contribute [FILE] [OPTIONS]
```

| Argument / Option | Description |
|---|---|
| `FILE` | Optional: contribute only this file |
| `--dry-run` | Preview what would be contributed |
| `--skip-git-check` | Skip warehouse git state validation |
| `--manual-git` | Print manual git steps instead of auto-creating a PR |
| `--exclude-unregistered` | Skip files not in `beacon.yaml` |

**Default behavior:** creates a `contrib/<timestamp>` branch in the warehouse, commits, pushes, and opens a PR via `gh`. Falls back to printing manual steps if `gh` is not available.

---

## Status & Maintenance

### `abc status`

Show the current warehouse connection and sync state.

```bash
abc status [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--project PATH` | Check a specific project directory |

---

### `abc doctor`

Validate project health: warehouse connection, `beacon.yaml` validity, missing artifacts.

```bash
abc doctor [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--fix` | Auto-migrate stale paths to the current schema |

---

### `abc list`

List synced artifacts or globally installed agents.

```bash
abc list [ARTIFACT_TYPE]
```

| Argument | Description |
|----------|-------------|
| (none) | List all synced artifacts |
| `agents` | List globally installed agents |
| `knowledge` | List synced knowledge files |
| `skills` | List synced skills |
| `contexts` | List synced contexts |

---

### `abc clean`

Remove synced artifacts from the project.

```bash
abc clean [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--project PATH` | Clean a specific project directory |

Removes `.agentic-beacon/artifacts/` entirely. Run `abc sync` to re-download.

---

### `abc reset`

Force-overwrite all synced artifacts from the warehouse.

```bash
abc reset [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--project PATH` | Reset a specific project directory |

Equivalent to `abc sync --force`. Discards all local modifications to artifacts.

---

## Global Options

Available on all commands:

| Option | Description |
|--------|-------------|
| `--verbose` | Enable debug-level logging |
| `--version` | Show version and exit |
| `--help` | Show help and exit |

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `abc warehouse init` | Create a new warehouse |
| `abc warehouse connect` | Connect a project to a warehouse |
| `abc setup` | Create `beacon.yaml` configuration |
| `abc adopt` | Browse + select artifacts via TUI |
| `abc sync` | Sync all declared artifacts |
| `abc install <artifact>` | Sync a single artifact |
| `abc agents sync` | Sync global agent definitions |
| `abc delta` | Compare local artifacts with warehouse |
| `abc contribute` | Copy local changes back to warehouse |
| `abc status` | Show connection and sync status |
| `abc doctor` | Validate project health |
| `abc list` | List synced artifacts |
| `abc clean` | Remove synced artifacts |
| `abc reset` | Force-overwrite all artifacts |
