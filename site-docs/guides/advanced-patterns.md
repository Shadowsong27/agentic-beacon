# Advanced Patterns

Glob syntax, sync flags, the delta workflow, and artifact lifecycle management.

## Glob Pattern Syntax

Patterns in `beacon.yaml` are matched against the warehouse root. Only files (not directories) are matched.

### Supported Syntax

| Pattern | Matches |
|---------|---------|
| `knowledge/python/type-hints.md` | Exact file |
| `knowledge/python/*.md` | All `.md` files in one directory |
| `knowledge/python/**/*.md` | All `.md` files recursively under `python/` |
| `contexts/teams/*/AGENTS.md` | One `AGENTS.md` per team subdirectory |

### Practical Examples

```yaml
artifacts:
  knowledge:
    # Exact file — stable, won't pick up new files automatically
    - knowledge/global/decisions/coding-standards.md

    # Directory wildcard — all files one level deep
    - knowledge/languages/python/*.md

    # Recursive wildcard — all markdown under python/
    - knowledge/languages/python/**/*.md

    # Multi-level wildcard — one context per team
    - contexts/teams/*/AGENTS.md

  skills:
    # Skills are declared at directory level
    - skills/code-review/
    - skills/generate-tests/

  contexts:
    - contexts/global.md
```

### Debugging Unmatched Patterns

If a pattern matches nothing, `abc sync` warns but does not fail:

```
Warning: No files matched pattern: knowledge/python/fastapi.md
```

Debug by listing the warehouse directory:

```bash
ls /path/to/warehouse/knowledge/python/
find /path/to/warehouse/knowledge/python/ -name "*.md"
```

---

## The Delta Workflow

`abc delta` compares your local artifacts against the current warehouse versions.

### Summary View

```bash
abc delta
```

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

| Status | Meaning |
|--------|---------|
| `MODIFIED` | File exists locally and in warehouse, but content differs |
| `ADDED` | File exists locally but not in the warehouse (you created it) |
| `MISSING` | File is in `beacon.yaml` but has not been synced yet |
| `IDENTICAL` | File matches warehouse exactly |
| `STALE` | File was synced from an older warehouse version |

### Detailed Diff

```bash
abc delta knowledge/python/type-hints.md
```

Shows a line-by-line diff:

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

Suppress colors (for piping or logging):

```bash
abc delta knowledge/python/type-hints.md --no-color
```

---

## Sync Flags in Practice

### Protecting local edits while accepting warehouse updates

```bash
abc sync --preserve
```

Skips files that exist locally and differ from the warehouse. New warehouse files are still copied.

Use this when you've made intentional local edits you want to keep:

```bash
abc delta           # review local changes first
abc sync --preserve # sync new content, keep local edits
```

### Starting fresh

```bash
abc reset
# or
abc sync --force
```

Force-overwrites all artifacts from the warehouse. Run `abc delta` first if you want to save any local changes.

### Removing stale artifacts

After removing entries from `beacon.yaml`, the old artifact files remain until you clean them up:

```bash
abc clean           # remove entire artifacts directory
abc sync            # re-download only what's in beacon.yaml
```

---

## Keeping Artifacts Up to Date

The recommended update workflow:

```bash
# 1. Pull warehouse updates
cd ~/team-warehouse
git pull

# 2. Check what changed
cd my-project
abc delta

# 3. Sync (preserving local edits if needed)
abc sync               # default: overwrites changed files
abc sync --preserve    # protect local edits
```

---

## Agent-Specific Patterns

### Installing a single artifact

```bash
# Install one skill
abc install skills/code-review/

# Install one context (wired into agent config automatically)
abc install contexts/global.md

# Install one agent globally
abc install agents/reviewer.md
```

`abc install` adds the artifact to `beacon.yaml` so future syncs are idempotent.

### Syncing only agents

```bash
abc agents sync
```

Installs agent definitions from the warehouse into global tool directories without touching project artifacts. No `beacon.yaml` required.

### Listing installed artifacts

```bash
abc list                # all synced artifacts
abc list agents         # globally installed agents
abc list knowledge      # synced knowledge files
abc list skills         # synced skills
abc list contexts       # synced contexts
```

---

## `ignore` in beacon.yaml

Suppress skills from appearing in `abc delta` and `abc contribute`. Useful for skills installed by external tools (e.g., OpenSpec) that you don't manage through the warehouse:

```yaml
ignore:
  skills:
    - "openspec-*"
    - "opsx-*"
```

Patterns use [`fnmatch`](https://docs.python.org/3/library/fnmatch.html) syntax matched against the skill directory name (without the `skills/` prefix).

---

## Validate Your Setup

```bash
abc doctor
```

Checks:
- Warehouse connection is valid
- `beacon.yaml` is well-formed
- All declared artifacts exist in the warehouse
- No stale paths from old schema versions

Use `--fix` to automatically migrate stale paths:

```bash
abc doctor --fix
```

---

## Next Steps

- **[beacon.yaml Reference](../reference/beacon-yaml.md)** — full schema documentation
- **[CLI Reference](../reference/cli.md)** — all commands and flags
- **[Contributing Back](contributing-back.md)** — the contribution workflow
