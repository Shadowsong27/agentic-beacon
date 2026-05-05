# CLI Reference

**Platform support:** macOS and Linux only.

## Warehouse Commands

| Command | Description |
|---------|-------------|
| `abc warehouse init <dir>` | Initialize a new warehouse repository |
| `abc warehouse connect --path <path>` | Connect a project to a local warehouse clone |
| `abc warehouse status [<path>] [--all]` | Show uncommitted warehouse edits (scoped by `beacon.yaml` unless `--all`) |
| `abc warehouse contribute -m "…" [--push]` | Commit warehouse edits, optionally push |
| `abc warehouse list` | List artifacts available in the connected warehouse |
| `abc warehouse template-upgrade` | Upgrade template-generated files in an existing warehouse |

## Project Commands

| Command | Description |
|---------|-------------|
| `abc adopt` | Interactively browse and select warehouse artifacts via TUI; writes to `beacon.yaml` |
| `abc sync` | Create/repair symlinks for all artifacts declared in `beacon.yaml`; wires agent config |
| `abc sync --dry-run` | Preview the symlink operations without touching the filesystem |
| `abc sync --contribute-local` / `--discard-local` | Non-interactive migration from a copy-based tree |
| `abc doctor` | Validate project health: warehouse connection, `beacon.yaml` validity, broken symlinks |
| `abc reset` | Force-rebuild all symlinks from the warehouse |
| `abc list` | List synced artifacts; `abc list agents` shows globally installed agents |
| `abc status` | Show current warehouse connection and project sync status |
| `abc clean` | Remove synced artifacts from the project |

## Agent Commands

| Command | Description |
|---------|-------------|
| `abc agents sync` | Symlink all warehouse agent definitions into global tool directories (`--force` to overwrite conflicts) |
