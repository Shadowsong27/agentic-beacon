# Syncing Artifacts

`abc sync` is the core command — it reads `beacon.yaml`, resolves dependencies via frontmatter, auto-derives knowledge from markdown links, and installs everything in the right places for your AI tools.

## Basic Usage

```bash
abc sync
```

Reads `.agentic-beacon/beacon.yaml` and performs the full sync. Output example:

```
✓ Sync complete
  Created: 5 symlinks
  Up to date: 10 symlinks
  ✓ Wired 2 context(s) into CLAUDE.md
  ✓ Installed 1 skill(s) (code-review)
```

---

## What Sync Does

`abc sync` runs a multi-phase pipeline:

1. **Read `beacon.yaml`** — loads declared contexts, skills, and agents
2. **Resolve dependencies** — reads `requires:` frontmatter from each skill's `SKILL.md` and agent dependencies from `agents/agents.yaml` to compute transitive dependencies
3. **Auto-derive knowledge** — scans all adopted contexts and skills for markdown links to `knowledge/` paths
4. **Create symlinks** — creates per-file symlinks under `.agentic-beacon/artifacts/` pointing into the warehouse
5. **Wire artifacts** — adds context references to `CLAUDE.md`/`opencode.json`, installs skills into tool directories, installs agents globally
6. **Prune orphans** — removes symlinks for artifacts no longer referenced

| Artifact | Destination | Wiring |
|---|---|---|
| **Contexts** | `.agentic-beacon/artifacts/contexts/` (symlinks) | Added to `CLAUDE.md` or `opencode.json` |
| **Skills** | `.agentic-beacon/artifacts/skills/` (symlinks) + tool dirs | Installed as slash commands |
| **Knowledge** | `.agentic-beacon/artifacts/knowledge/` (symlinks) | Auto-derived from markdown links; no wiring needed |
| **Agents** | `.agentic-beacon/artifacts/agents/` (symlinks) + `~/.claude/agents/` + `~/.config/opencode/agents/` | Ready in all projects |

---

## Sync Flags

### `--force` — Overwrite Everything

```bash
abc sync --force
```

Force-overwrites all conflicting files, ignoring any local modifications. Use when you want to fully reset to the current warehouse state.

### `--dry-run` — Preview Without Applying

```bash
abc sync --dry-run
```

Shows what would be synced without making changes:

```
Would create: 5 symlinks
Up to date: 10 symlinks
```

### `--verbose` — Per-file Output

```bash
abc sync --verbose
```

Shows detailed output for each file processed.

### `--skip-git-check` — Skip Warehouse Validation

```bash
abc sync --skip-git-check
```

Bypasses the warehouse git state checks (uncommitted changes, behind remote, non-main branch). Useful in CI environments.

### `--contribute-local` — Auto-contribute Modified Files

```bash
abc sync --contribute-local
```

Non-interactive: automatically contributes all locally modified files back to the warehouse during sync.

### `--discard-local` — Auto-discard Local Changes

```bash
abc sync --discard-local
```

Non-interactive: discards all locally modified files and replaces them with fresh symlinks from the warehouse.

---

## Combining Flags

```bash
# Preview a full reset
abc sync --force --dry-run
```

---

## Syncing Agents

Agents declared in `beacon.yaml` are wired into project-local tool directories during `abc sync`:

```bash
abc sync
```

`abc sync` creates:
- `.agentic-beacon/artifacts/agents/<name>.md` — artifact symlink into the warehouse
- `.claude/agents/<name>.md` — project-local symlink (when `.claude/` exists)
- `.opencode/agents/<name>.md` — project-local symlink (when `.opencode/` exists)

Agents are project-scoped. Use `abc adopt` to select which agents to declare in `beacon.yaml`.

---

## Resetting All Artifacts

```bash
abc reset
```

Force-overwrites all synced artifacts from the warehouse, discarding any local modifications.

---

## Cleaning Up

```bash
abc clean
```

Removes `.agentic-beacon/artifacts/` entirely. Run `abc sync` to re-sync.

---

## Next Steps

- **[Advanced Patterns](advanced-patterns.md)** — glob patterns and artifact lifecycle
- **[Day-to-Day Workflow](day-to-day-workflow.md)** — how sync fits into the recurring loop
- **[CLI Reference](../reference/cli.md)** — full flag documentation
