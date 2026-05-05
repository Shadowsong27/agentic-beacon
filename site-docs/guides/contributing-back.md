# Contributing Back to the Warehouse

Agentic Beacon uses a **symlink model**: `abc sync` creates symlinks from `.agentic-beacon/artifacts/` into your warehouse clone. When an agent session improves an artifact, those changes are already in the warehouse working tree — use `abc warehouse contribute` to commit and share them.

---

## The Workflow

### 1. Review what changed

```bash
abc warehouse status
```

Shows modifications to warehouse files tracked by `beacon.yaml`:

```
Modified files:
  modified  knowledge/python/type-hints.md
  modified  skills/code-review/SKILL.md
```

Inspect a specific file:

```bash
abc warehouse status knowledge/python/type-hints.md
```

Shows a line-by-line diff.

### 2. Commit changes

Commit all modified files with a message:

```bash
abc warehouse contribute -m "Improve type hints guide with Python 3.12+ patterns"
```

Push the commit immediately:

```bash
abc warehouse contribute -m "Fix typo in error handling guide" --push
```

### 3. What happens automatically

`abc warehouse contribute`:

1. Stages all files tracked by `beacon.yaml` that have uncommitted changes
2. Creates a commit with your message
3. If `--push` is used, pushes the commit to the remote

If there are no changes to commit, it prints a message and exits cleanly.

### 4. Teammates pick it up

Once your changes are in the warehouse:

```bash
cd ~/team-warehouse && git pull
cd my-project && abc sync
```

---

## Manual Git Workflow

Since artifacts are symlinks into the warehouse clone, you can also use plain git commands:

```bash
# In the warehouse clone
cd ~/team-warehouse
git add knowledge/python/type-hints.md
git commit -m "docs: improve type hints guide"
git push
```

The warehouse working tree is always up to date because symlinks write directly to it.

---

## How the Symlink Model Changes Things

| Old copy-based model (removed) | Current symlink model |
|---|---|
| Artifacts copied to `.agentic-beacon/artifacts/` | Artifacts are symlinks into the warehouse |
| `abc delta` compared copies against warehouse | `abc warehouse status` shows warehouse working tree changes |
| `abc contribute` copied files back to warehouse | `abc warehouse contribute` commits changes already in the warehouse |
| Local edits were isolated per project | Local edits go directly to the warehouse clone |

Editing a symlinked artifact file IS editing the warehouse working tree. The edit is visible to all projects that use the same artifact on the same machine.

---

## Contribution Checklist

Before committing to the warehouse:

- [ ] Tested the artifact in a real project — agent actually used it correctly
- [ ] Content is generic — no project-specific paths, credentials, or names
- [ ] No broken references or links
- [ ] Commit message describes **why** the change helps, not just what changed

---

## Next Steps

- **[Day-to-Day Workflow](day-to-day-workflow.md)** — how contributing fits into the loop
- **[Creating Skills](creating-skills.md)** — writing effective skill definitions before contributing
- **[Command Reference](../reference/cli.md)** — full `abc warehouse contribute` options
