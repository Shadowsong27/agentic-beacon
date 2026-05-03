# Advanced Patterns

> **Superseded by** the new [`guides/advanced-patterns.md`](../../guides/advanced-patterns.md). The sections below describe pre-symlink flags and commands (`abc sync --preserve`, `abc sync --prune`, `abc update`, `abc clean`, `abc delta`, project-to-warehouse manual file copy) that no longer exist. Retained for historical context. For current guidance see [`single-warehouse-write-entrypoint`](../../knowledge/decisions/single-warehouse-write-entrypoint.md) and [`guides/warehouse-contribution-guide.md`](../../guides/warehouse-contribution-guide.md).

---

# Advanced Patterns (historical)

This guide covers advanced usage of Agentic Beacon: glob pattern syntax, sync flags, the delta workflow, and artifact lifecycle management.

## Glob Pattern Syntax

Patterns in `beacon.yaml` are matched against the warehouse root. Only files (not directories) are matched.

### Supported Syntax

| Pattern | Matches |
|---------|---------|
| `knowledge/python/type-hints.md` | Exact file |
| `knowledge/python/*.md` | All `.md` files in one directory |
| `knowledge/python/**/*.md` | All `.md` files recursively under `python/` |
| `skills/code-review/**/*` | All files under a skill directory |
| `contexts/teams/*/AGENTS.md` | One `AGENTS.md` per team subdirectory |

### Practical Examples

```yaml
artifacts:
  knowledge:
    # Exact file - very specific, won't pick up new files
    - knowledge/global/decisions/coding-standards.md

    # Directory wildcard - all files one level deep
    - knowledge/languages/python/*.md

    # Recursive wildcard - all markdown under python/
    - knowledge/languages/python/**/*.md

    # Multi-level wildcard - all team contexts
    - contexts/teams/*/AGENTS.md

  skills:
    # Skills are typically directories; use /** /* to get all files
    - skills/code-review/**/*
    - skills/generate-tests/**/*

  contexts:
    # Global context file
    - contexts/global.md
```

### Pattern Doesn't Match?

If a pattern matches nothing, `abc sync` will warn but not fail:

```
Warning: No files matched pattern: knowledge/python/fastapi.md
```

Debug it by listing the warehouse:

```bash
ls /path/to/warehouse/knowledge/python/
# or
find /path/to/warehouse/knowledge/python/ -name "*.md"
```

Then adjust your pattern to match the actual structure.

---

## Sync Flags

### Default Sync (No Flags)

```bash
abc sync
```

- Copies new and changed files from warehouse
- **Overwrites** local modifications (SHA256 comparison — same content = skip, different = overwrite)
- Does not remove artifacts that were removed from `beacon.yaml`

### `--preserve` — Protect Local Changes

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

Use `abc delta` to see what you've changed before deciding whether to preserve or overwrite:

```bash
abc delta                           # Summary of all local changes
abc delta knowledge/python/type-hints.md  # Detailed diff for one file
```

**Note:** `--preserve` only skips files that already exist locally. New files from the warehouse are always copied.

### `--prune` — Remove Stale Artifacts

```bash
abc sync --prune
```

After syncing, removes any file in `.agentic-beacon/artifacts/` that is no longer listed in `beacon.yaml`. Also removes empty directories.

```
✓ Sync complete
  Copied: 3 files
  Unchanged: 8 files
  Pruned: 4 artifacts no longer in beacon.yaml
```

Use this when you've removed entries from `beacon.yaml` and want to clean up.

### `--verbose` — Per-File Output

```bash
abc sync --verbose
```

Shows a line for each file processed:

```
Syncing: knowledge/python/type-hints.md
Copied: knowledge/python/type-hints.md
Syncing: knowledge/python/async-patterns.md
Unchanged: knowledge/python/async-patterns.md
Preserved (local changes): knowledge/python/error-handling.md
```

### Combining Flags

```bash
# Preserve local changes and remove stale files
abc sync --preserve --prune

# Full verbose output with pruning
abc sync --prune --verbose
```

---

## The Delta Workflow

`abc delta` compares your local artifacts against the current warehouse versions. This is useful when:

- You've edited a synced artifact and want to review your changes
- You want to contribute a local change back to the warehouse
- You're diagnosing why a sync is behaving unexpectedly

### Summary View

```bash
abc delta
```

Shows all files that differ from the warehouse:

```
Delta Summary
──────────────────────────────────────
MODIFIED  knowledge/python/type-hints.md
MODIFIED  knowledge/python/async-patterns.md
ADDED     knowledge/python/local-experiments.md
MISSING   skills/new-skill/SKILL.md

  Modified: 2  Added: 1  Missing: 1
```

**Status meanings:**
- `MODIFIED` — File exists locally and in warehouse, but content differs
- `ADDED` — File exists locally but is not in the warehouse (you created it)
- `MISSING` — File is in `beacon.yaml` but has not been synced yet

### Detailed Diff

```bash
abc delta knowledge/python/type-hints.md
```

Shows a line-by-line diff using `git diff`:

```diff
--- warehouse/knowledge/python/type-hints.md
+++ local/.agentic-beacon/artifacts/knowledge/python/type-hints.md
@@ -12,6 +12,10 @@
 ## Best Practices
 - Always use type hints for function signatures
+- Prefer `str | None` over `Optional[str]` in Python 3.10+
+- Use `list[str]` not `List[str]`
 - Use Union for multiple types
```

To suppress colors (useful for piping or logging):

```bash
abc delta knowledge/python/type-hints.md --no-color
```

### Contribute Changes Back to Warehouse

If you've improved an artifact locally and want to share it:

```bash
# 1. Review your changes
abc delta knowledge/python/type-hints.md

# 2. Copy your version back to the warehouse
cp .agentic-beacon/artifacts/knowledge/python/type-hints.md \
   /path/to/warehouse/knowledge/python/type-hints.md

# 3. Commit it in the warehouse
cd /path/to/warehouse
git add knowledge/python/type-hints.md
git commit -m "docs: improve type hints guide with Python 3.10+ syntax"
git push

# 4. Re-sync your project
cd -
abc sync
```

---

## `abc status` — Inspect Your Setup

```bash
abc status
```

Shows a quick health check of your current project:

```
Warehouse: /Users/you/team-warehouse

Configured Contexts
  ✓ teams/backend/AGENTS.md
  ✗ teams/frontend/AGENTS.md (not synced)

Configured Knowledge Patterns
  • knowledge/languages/python/**/*.md
  • knowledge/best-practices/testing.md

Configured Skills
  ✓ code-review
  ✗ generate-tests (not synced)

Artifacts: .agentic-beacon/artifacts/ (34 files)
```

The `✓`/`✗` marks show whether a context or skill directory actually exists in your local artifacts folder. Use this to verify a sync worked as expected.

---

## `abc update` — Force Overwrite All Artifacts

```bash
abc update
```

Unlike `abc sync` (which skips unchanged files), `abc update` **deletes and re-copies every artifact**, ignoring local modifications and SHA256 comparisons.

Use this when:
- The warehouse had in-place edits to files without content changes (e.g., metadata only)
- You want to fully reset all artifacts to the current warehouse state
- You suspect a sync got into a bad state

**Warning:** Any local edits to artifacts will be overwritten. Run `abc delta` first if you want to review local changes before losing them.

---

## `abc clean` — Remove All Artifacts

```bash
abc clean
```

Prompts for confirmation, then removes `.agentic-beacon/artifacts/` entirely.

```
Are you sure you want to remove synced artifacts? [y/N]: y
✓ Cleaned .agentic-beacon/artifacts/
```

After cleaning, run `abc sync` to re-download from the warehouse.

Use this to start fresh or free up disk space.

---

## Keeping Artifacts Up to Date

The recommended workflow for staying current with a team warehouse:

```bash
# 1. Pull warehouse updates
cd ~/team-warehouse
git pull

# 2. Sync your project
cd ~/my-project
abc sync
```

If you want to check what changed before syncing:

```bash
abc delta              # Preview differences
abc sync               # Apply updates (won't touch modified files by default)
abc sync --preserve    # Apply updates, protecting local edits
```

---

## Next Steps

- **[beacon.yaml Reference](./beacon-yaml-reference.md)** — All configuration options
- **[Creating Skills](./creating-skills.md)** — Build your own skills
- **[Team Collaboration](./team-collaboration.md)** — Share configurations across teams
