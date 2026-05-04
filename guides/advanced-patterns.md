# Advanced Patterns

This guide covers advanced usage of Agentic Beacon: glob pattern syntax, the `--dry-run` sync preview, and the `abc warehouse` command surface.

> Under the current symlink-based sync model, a project's `.agentic-beacon/artifacts/` tree is symlinks into the warehouse clone — there is no project-local copy to "preserve" or "force-overwrite". See [`single-warehouse-write-entrypoint`](../knowledge/decisions/single-warehouse-write-entrypoint.md).

## Glob Pattern Syntax

Patterns in `beacon.yaml` are matched against the warehouse root. Only files (not directories) are matched.

### Supported Syntax

| Pattern | Matches |
|---------|---------|
| `skills/code-review/**/*` | All files under a skill directory |
| `contexts/teams/*/AGENTS.md` | One `AGENTS.md` per team subdirectory |

### Practical Examples

```yaml
artifacts:
  skills:
    # Skills are typically directories; use /**/* to get all files
    - skills/code-review/**/*
    - skills/generate-tests/**/*

  contexts:
    # Global context file
    - contexts/global.md

    # Multi-level wildcard - all team contexts
    - contexts/teams/*/AGENTS.md
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

---

## `abc sync --dry-run` — Preview Before Linking

```bash
abc sync --dry-run
```

Prints the intended symlink operations (create / update / remove) without touching the filesystem:

```
Dry run — no filesystem changes will be made.

would create  .agentic-beacon/artifacts/contexts/global.md             → /Users/me/team-warehouse/contexts/global.md
would create  .agentic-beacon/artifacts/skills/code-review/SKILL.md    → /Users/me/team-warehouse/skills/code-review/SKILL.md
would remove  .agentic-beacon/artifacts/contexts/old-removed.md        (no longer in beacon.yaml)
```

Use this to confirm a `beacon.yaml` edit does what you expect before applying it.

---

## Inspecting the Current State

### Warehouse working tree (what you've edited)

```bash
abc warehouse status
```

Reports uncommitted and unpushed state of the warehouse clone, scoped by your project's `beacon.yaml`:

```
Warehouse: /Users/me/team-warehouse (branch: main, 2 ahead, 0 behind)

Modified:
  M  knowledge/python/type-hints.md
  M  skills/code-review/SKILL.md
```

Scope flags:

```bash
abc warehouse status knowledge/python/type-hints.md   # unified diff for one file
abc warehouse status --all                            # entire warehouse working tree, unfiltered
```

### Confirming a project's symlinks

```bash
find .agentic-beacon/artifacts -type l | wc -l       # count symlinks
find .agentic-beacon/artifacts -type f -not -type l  # any stray regular files?
```

A healthy post-sync tree has every `beacon.yaml`-matched path as a symlink and zero regular files at leaf positions.

---

## Contributing Changes Back

```bash
abc warehouse contribute -m "python: clarify Optional vs None"
abc warehouse contribute -m "…" --push                 # commit and push in one step
```

Because edits through `.agentic-beacon/artifacts/<path>` land directly in the warehouse working tree, there is no manual copy step. The commit's scope is automatic — `beacon.yaml`-matched modifications in the warehouse working tree become the staged set.

See [Contributing Back to the Warehouse](./warehouse-contribution-guide.md) for the full workflow.

---

## Migration from the Copy Model

If you had a project created under the previous copy-based CLI version, the first `abc sync` on the new version will detect regular files under `.agentic-beacon/artifacts/` and run a migration pass:

- Identical files (byte-equal to the warehouse) are silently replaced with symlinks.
- Modified files trigger an interactive prompt per file, showing a unified diff and offering:
  - `c` — contribute the local content into the warehouse working tree, then replace with a symlink
  - `d` — discard local content, symlink to warehouse
  - `s` — skip for now (resume on the next `abc sync`)

Non-interactive bulk resolution:

```bash
abc sync --contribute-local   # contribute every modified file, no prompts
abc sync --discard-local      # discard every modified file, no prompts
```

In a non-TTY environment (CI, scripted upgrade) without either flag, `abc sync` refuses to proceed and lists the files that need resolution.

---

## Next Steps

- **[beacon.yaml Reference](./beacon-yaml-reference.md)** — All configuration options
- **[Creating Skills](./creating-skills.md)** — Build your own skills
- **[Team Collaboration](./team-collaboration.md)** — Share configurations across teams
- **[Contributing Back](./warehouse-contribution-guide.md)** — Full contribute workflow
