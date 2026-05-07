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
| `--path PATH` | Path to the warehouse (prompted if omitted) |

Creates `.agentic-beacon/config.toml` (gitignored) with the warehouse location.

**Example:**
```bash
abc warehouse connect --path ~/my-org-warehouse
```

---

### `abc warehouse list`

List artifacts available in the connected warehouse.

```bash
abc warehouse list [ARTIFACT_TYPE]
```

| Argument | Description |
|----------|-------------|
| (none) | List all artifact types |
| `agents` | List available agents |
| `knowledge` | List available knowledge |
| `skills` | List available skills |
| `contexts` | List available contexts |

---

### `abc warehouse contribute`

Commit changes in the warehouse working tree back to the warehouse repository.

```bash
abc warehouse contribute -m MESSAGE [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-m, --message TEXT` | Commit message (required) |
| `--push` | Push the commit to the remote after committing |

Stages and commits files tracked by `beacon.yaml` that have uncommitted changes in the warehouse clone.

**Example:**
```bash
abc warehouse contribute -m "Update python standards"
abc warehouse contribute -m "Fix typo" --push
```

---

### `abc warehouse status`

Show warehouse working tree status.

```bash
abc warehouse status [PATH] [OPTIONS]
```

| Argument / Option | Description |
|---|---|
| `PATH` | Optional: show unified diff for this specific file |
| `--all` | Show unfiltered warehouse working-tree status |

**Example:**
```bash
abc warehouse status
abc warehouse status knowledge/python/standards.md
abc warehouse status --all
```

---

### `abc warehouse template-upgrade`

Upgrade warehouse template documentation to the latest version.

```bash
abc warehouse template-upgrade [WAREHOUSE_PATH] [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `WAREHOUSE_PATH` | Path to warehouse (defaults to current directory) |
| `--dry-run` | Preview changes without applying |
| `--interactive` | Prompt before each change |
| `--force` | Apply without confirmation |

---

## Project Setup

### `abc setup`

Create `.agentic-beacon/beacon.yaml` configuration.

```bash
abc setup
```

Creates a `beacon.yaml` template that declares which artifacts this project uses. Must be run after `abc warehouse connect`.

**Example:**
```bash
abc setup
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
| `--force` | Overwrite all conflicting files without prompting |
| `--dry-run` | Preview what would be synced without making changes |
| `--verbose` | Show per-file sync output |
| `--skip-git-check` | Skip warehouse git state validation |
| `--contribute-local` | Non-interactive: contribute all modified local files to warehouse |
| `--discard-local` | Non-interactive: discard all modified local files and replace with symlinks |

**What sync does per artifact type:**

| Artifact | Action |
|---|---|
| Knowledge | Create symlinks in `.agentic-beacon/artifacts/knowledge/` |
| Contexts | Create symlinks + wire into `CLAUDE.md` or `opencode.json` |
| Skills | Create symlinks + install into tool-specific directories |
| Agents | Create artifact symlinks + wire into project-local `.claude/agents/` and `.opencode/agents/` |

---

## Status & Maintenance

### `abc status`

Show the current warehouse connection and configuration status.

```bash
abc status [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--project PATH` | Check a specific project directory |

Displays the connected warehouse path, configured contexts/skills (with ✓/✗ for synced status), bundled skills status, and total synced file count.

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

Removes `.agentic-beacon/artifacts/` entirely. Run `abc sync` to re-sync.

---

### `abc reset`

Force-overwrite all synced artifacts from the warehouse.

```bash
abc reset [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--project PATH` | Reset a specific project directory |

Overwrites all symlinks from the warehouse, discarding any local modifications.

---

## Removed Commands

The following commands have been removed. If you are upgrading from a pre-v3
release, replace any scripted invocations with the modern equivalents below:

| Removed | Replacement |
|---------|-------------|
| `abc delta` | `abc warehouse status` |
| `abc contribute` | `abc warehouse contribute -m "message"` |
| `abc install <artifact>` | Edit `beacon.yaml`, then `abc sync` |
| `abc update` | `abc sync` (or `abc reset` to force-overwrite) |

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
| `abc warehouse list` | List available artifacts in warehouse |
| `abc warehouse status` | Show warehouse working tree changes |
| `abc warehouse contribute -m MESSAGE` | Commit warehouse changes back |
| `abc warehouse template-upgrade` | Upgrade warehouse template docs |
| `abc setup` | Create `beacon.yaml` configuration |
| `abc adopt` | Browse + select artifacts via TUI |
| `abc sync` | Sync all declared artifacts (contexts, skills, agents) |
| `abc status` | Show connection and sync status |
| `abc doctor` | Validate project health |
| `abc list` | List synced artifacts |
| `abc clean` | Remove synced artifacts |
| `abc reset` | Force-overwrite all artifacts |
