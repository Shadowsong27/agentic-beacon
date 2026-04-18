# Syncing Artifacts

`abc sync` is the core command — it reads `beacon.yaml`, finds all matching artifacts in the warehouse, and installs them in the right places for your AI tools.

## Basic Usage

```bash
abc sync
```

Reads `.agentic-beacon/beacon.yaml` and performs the full sync. Output example:

```
✓ Sync complete
  Copied: 5 files
  Unchanged: 10 files
  Wired: 2 contexts
  Installed: 1 skill
```

---

## What Sync Does

For each artifact type, sync applies different logic:

| Artifact | Destination | Wiring |
|---|---|---|
| **Knowledge** | `.agentic-beacon/artifacts/knowledge/` | None (referenced from contexts) |
| **Contexts** | `.agentic-beacon/artifacts/contexts/` | Added to `AGENTS.md` or `opencode.json` |
| **Skills** | `.agentic-beacon/artifacts/skills/` + tool dirs | Installed as slash commands |
| **Agents** | `~/.claude/agents/` + `~/.config/opencode/agents/` | Ready in all projects |

Sync is **idempotent** — files with identical content (SHA256 comparison) are skipped. Only changed files are re-copied.

---

## Sync Flags

### `--preserve` — Protect Local Edits

```bash
abc sync --preserve
```

Skips files that exist locally and differ from the warehouse version, preserving your local edits.

```
✓ Sync complete
  Copied: 5 files
  Unchanged: 10 files
  Preserved: 2 locally modified files
```

!!! note
    `--preserve` only skips files that already exist locally. New files from the warehouse are always copied.

Use `abc delta` first to review local changes before deciding whether to preserve or overwrite:

```bash
abc delta                                     # summary of all local changes
abc delta knowledge/python/type-hints.md      # detailed diff for one file
```

### `--force` — Overwrite Everything

```bash
abc sync --force
```

Force-overwrites all artifacts, ignoring local modifications and SHA256 comparisons. Use when you want to fully reset to the current warehouse state.

!!! warning
    Any local edits to artifacts will be overwritten. Run `abc delta` first if you want to review.

### `--dry-run` — Preview Without Applying

```bash
abc sync --dry-run
```

Shows what would be copied without actually copying anything. Useful for previewing the effect of a sync.

### `--verbose` — Per-file Output

```bash
abc sync --verbose
```

Shows a line for each file processed:

```
Syncing: knowledge/python/type-hints.md → Copied
Syncing: knowledge/python/async-patterns.md → Unchanged
Syncing: knowledge/python/error-handling.md → Preserved (local changes)
```

### `--skip-git-check` — Skip Warehouse Validation

```bash
abc sync --skip-git-check
```

Bypasses the warehouse git state checks (uncommitted changes, behind remote, non-main branch). Useful in CI environments or when you know the warehouse state is acceptable.

---

## Combining Flags

```bash
# Preserve local changes + verbose output
abc sync --preserve --verbose

# Preview a full reset
abc sync --force --dry-run
```

---

## Syncing Agents Only

```bash
abc agents sync
```

Syncs agent definitions from the warehouse into global tool directories without running a full project sync. Does not require `beacon.yaml` — works in any project connected to a warehouse.

Supports the same `--force` and `--preserve` flags.

---

## Syncing a Single Artifact

```bash
abc install skills/code-review/
abc install contexts/global.md
abc install agents/reviewer.md
```

Copies and wires a single artifact, then adds it to `beacon.yaml` so future syncs remain idempotent.

---

## Resetting All Artifacts

```bash
abc reset
```

Force-overwrites all synced artifacts from the warehouse, discarding local modifications. Equivalent to `abc sync --force`.

---

## Cleaning Up

```bash
abc clean
```

Removes `.agentic-beacon/artifacts/` entirely. Run `abc sync` to re-download.

---

## Next Steps

- **[Advanced Patterns](advanced-patterns.md)** — glob patterns, `abc delta`, artifact lifecycle
- **[Day-to-Day Workflow](day-to-day-workflow.md)** — how sync fits into the recurring loop
- **[CLI Reference](../reference/cli.md)** — full flag documentation
