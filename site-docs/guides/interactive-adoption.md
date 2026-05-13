# Interactive Adoption

`abc adopt` opens a terminal UI to browse your warehouse and select which artifacts to pull into your project. It's the fastest way to populate `beacon.yaml` without manually writing YAML paths.

## When to Use It

- **First setup** — when connecting a project to a warehouse for the first time
- **Discovering new artifacts** — after a teammate adds artifacts to the warehouse
- **Reviewing options** — to see what's available before committing to a sync

---

## Starting the TUI

```bash
abc adopt
```

The TUI opens in your terminal, showing all warehouse artifacts grouped by type that are not yet in your `beacon.yaml`.

![abc adopt TUI](../assets/adopt-tui.png)

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate the list |
| `Space` | Toggle selection (select / deselect) |
| `Enter` | Confirm selections and write to `beacon.yaml` |
| `a` | Select all visible artifacts |
| `n` | Deselect all visible artifacts |
| `t` | Toggle show-all (include already-adopted artifacts) |
| `Esc` / `q` | Cancel without making changes |

---

## What Happens After You Confirm

When you press `Enter`, `abc adopt` runs a single session-atomic commit:

1. Selected artifacts (contexts, skills, and agents) are appended to `.agentic-beacon/beacon.yaml`
2. Matching entries are removed from `.agentic-beacon/pending.yaml`
3. The newly-adopted artifacts are immediately synced — symlinks are created under `.agentic-beacon/artifacts/`
4. Contexts are wired into your agent config (`CLAUDE.md` / `opencode.json`)
5. Skills are installed into each detected tool's directories
6. Agents are wired into project-local `.claude/agents/` and `.opencode/agents/` directories

The entire workflow — select → write config → sync → wire — happens in one step. If anything fails mid-commit, the manifests are restored to their pre-commit state.

For the underlying storage model (`pending.yaml`, `.last-adopt`, atomic rollback), see [Pending & Adoption](../concepts/pending-and-adoption.md).

> Editing `beacon.yaml` manually instead of going through the TUI? Run `abc sync` yourself afterward — the auto-sync described above only fires from the TUI confirm path.

---

## Flags

```bash
# Preview what's available without making any changes
abc adopt --dry-run
```

### `--dry-run`

Lists available artifacts in the terminal without opening the TUI. Useful for scripting or quick inspection.

### Show already-adopted artifacts

By default the TUI hides artifacts you've already added to `beacon.yaml`. To review your current selection (or unadopt entries), press `t` inside the TUI to toggle the show-all view. There is no `--all` CLI flag — the toggle is in-TUI only.

---

## Discovering New Artifacts

After a teammate adds artifacts to the warehouse, `abc sync` will notify you:

```
✓ Sync complete
  Copied: 0 files
  Unchanged: 3 files

1 new artifact(s) available — run abc adopt to review
```

Run `abc adopt` to open the TUI showing the new artifacts. Select the ones you want and press `Enter`.

---

## Relationship to beacon.yaml

`abc adopt` is a graphical front-end for editing `beacon.yaml`. It:
- Reads the warehouse to find available artifacts
- Reads your current `beacon.yaml` to know what's already adopted
- Writes new entries to `beacon.yaml` when you confirm

You can always edit `beacon.yaml` directly if you prefer — `abc adopt` just makes it easier.

---

## Next Steps

- **[Syncing Artifacts](syncing.md)** — `abc sync` flags and behavior
- **[beacon.yaml Reference](../reference/beacon-yaml.md)** — direct editing reference
- **[Day-to-Day Workflow](day-to-day-workflow.md)** — the full recurring loop
