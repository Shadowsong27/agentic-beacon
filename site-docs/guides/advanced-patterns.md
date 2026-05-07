# Advanced Patterns

Glob syntax, sync flags, the warehouse status workflow, and artifact lifecycle management.

## Glob Pattern Syntax

Patterns in `beacon.yaml` are matched against the warehouse root. Only files (not directories, except skills) are matched.

### Supported Syntax

| Pattern | Matches |
|---------|---------|
| `contexts/teams/backend/AGENTS.md` | Exact file |
| `contexts/teams/*/AGENTS.md` | One `AGENTS.md` per team subdirectory |

### Practical Examples

```yaml
artifacts:
  skills:
    # Skills are declared at directory level
    - skills/code-review/
    - skills/generate-tests/

  contexts:
    - contexts/global.md
    - contexts/teams/*/AGENTS.md
```

**Knowledge is auto-derived** — not declared in `beacon.yaml`. Markdown links in contexts and skills (e.g. `[guide](knowledge/python/type-hints.md)`) are automatically resolved and synced.

### Debugging Unmatched Patterns

If a pattern matches nothing, `abc sync` warns but does not fail:

```
Warning: No files matched pattern: contexts/nonexistent.md
```

Debug by listing the warehouse directory:

```bash
ls /path/to/warehouse/contexts/
```

---

## The Warehouse Status Workflow

`abc warehouse status` shows modifications to warehouse files tracked by resolved artifacts. Since artifacts are symlinks into the warehouse clone, editing an artifact directly modifies the warehouse working tree.

### Summary View

```bash
abc warehouse status
```

```
Modified files:
  modified  knowledge/python/type-hints.md
  modified  knowledge/python/async-patterns.md
  added     knowledge/python/new-lesson.md
  untracked skills/new-skill/SKILL.md
```

**Status meanings:**

| Status | Meaning |
|--------|---------|
| `modified` | File exists in warehouse and has been changed |
| `added` | New file staged for commit |
| `deleted` | File staged for removal |
| `untracked` | New file not yet tracked by git |

### Detailed Diff

```bash
abc warehouse status knowledge/python/type-hints.md
```

Shows a line-by-line unified diff.

### Full Status

For unfiltered status including files not tracked by `beacon.yaml`:

```bash
abc warehouse status --all
```

---

## Sync Flags in Practice

### Starting fresh

```bash
abc reset
# or
abc sync --force
```

Force-overwrites all artifacts from the warehouse. Use `abc warehouse status` first if you want to review any local changes.

### Non-interactive resolve

If there are conflicts between local and warehouse files:

```bash
abc sync --contribute-local    # auto-contribute local modifications
abc sync --discard-local       # auto-discard local changes
```

### Removing stale artifacts

After removing entries from `beacon.yaml`, the old symlinks are automatically removed as orphans:

```bash
# Edit beacon.yaml to remove a skill
vim .agentic-beacon/beacon.yaml
abc sync
# → Removed: 1 orphan symlink(s) no longer in beacon.yaml
```

Or clean everything and re-sync:

```bash
abc clean           # remove entire artifacts directory
abc sync            # re-sync only what's currently declared + derived
```

---

## Keeping Artifacts Up to Date

The recommended update workflow:

```bash
# 1. Pull warehouse updates
cd ~/team-warehouse
git pull

# 2. Check what changed in warehouse working tree
cd my-project
abc warehouse status

# 3. Contribute any local changes
abc warehouse contribute -m "Update python standards for 3.12+"

# 4. Re-sync
abc sync
```

---

## Syncing Agents

Agents are wired into project-local tool directories as part of `abc sync`:

```bash
abc sync
```

Declare agents in `beacon.yaml` first (via `abc adopt` or manually), then `abc sync` wires them into `.claude/agents/` and `.opencode/agents/` inside the project root.

### Listing installed artifacts

```bash
abc list                # all synced artifacts (contexts, skills)
abc list agents         # project-scoped agents from .agentic-beacon/artifacts/agents/
abc list skills         # synced skills
abc list contexts       # synced contexts
```

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
- Skill frontmatter dependencies are satisfied

Use `--fix` to automatically migrate stale paths:

```bash
abc doctor --fix
```

---

## Next Steps

- **[beacon.yaml Reference](../reference/beacon-yaml.md)** — full schema documentation
- **[CLI Reference](../reference/cli.md)** — all commands and flags
- **[Contributing Back](contributing-back.md)** — the contribution workflow
