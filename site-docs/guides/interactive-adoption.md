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

When you press `Enter`:

1. Selected artifacts (contexts, skills, and agents) are appended to `.agentic-beacon/beacon.yaml`
2. `abc sync` runs automatically for the newly selected artifacts
3. Contexts are wired into your agent config
4. Skills are installed into each detected tool's directories
5. Agents are wired into project-local `.claude/agents/` and `.opencode/agents/` directories

The entire workflow — select → write config → sync — happens in one step.

---

## Flags

```bash
# Preview what's available without making any changes
abc adopt --dry-run

# Show ALL warehouse artifacts, including already-adopted ones
abc adopt --all
```

### `--dry-run`

Lists available artifacts in the terminal without opening the TUI. Useful for scripting or quick inspection.

### `--all` (or `-t` toggle in the TUI)

By default, `abc adopt` only shows artifacts that are **not yet in `beacon.yaml`**. Use `--all` (or press `t` in the TUI) to also see artifacts you've already adopted — handy for reviewing your current selection.

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
