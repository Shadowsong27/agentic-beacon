# Contributing Back to the Warehouse

When your agent improves a synced artifact — a context file, a knowledge document, or a skill — those improvements live in `.agentic-beacon/artifacts/` and are gitignored by default. Use `abc contribute` to copy them back to the warehouse so the whole team benefits.

---

## The Workflow

### 1. Review what changed

```bash
abc delta
```

Shows all differences between your local artifacts and the warehouse:

```
Delta Summary
──────────────────────────────────────
MODIFIED  knowledge/python/type-hints.md
MODIFIED  skills/code-review/SKILL.md
ADDED     knowledge/python/new-lesson.md

  Modified: 2  Added: 1
```

Inspect a specific file:

```bash
abc delta knowledge/python/type-hints.md
```

### 2. Contribute changes

Contribute everything at once:

```bash
abc contribute
```

Contribute a single file:

```bash
abc contribute knowledge/python/type-hints.md
```

Preview without applying:

```bash
abc contribute --dry-run
```

### 3. What happens automatically

By default, `abc contribute`:

1. Creates a `contrib/<timestamp>` branch in the warehouse
2. Commits the changes with a descriptive message
3. Pushes the branch and opens a PR via `gh`
4. Prints the PR URL

If `gh` is not installed or the warehouse has no GitHub remote, it falls back to printing the manual git steps.

### 4. Teammates pick it up

Once the PR is merged:

```bash
cd ~/team-warehouse && git pull
cd my-project && abc sync
```

---

## Manual Git Workflow

If you prefer to manage the git steps yourself, or if you're using GitLab or Bitbucket:

```bash
abc contribute --manual-git
```

Prints the manual steps instead of creating the PR automatically.

You can also skip the auto-PR and handle git manually:

```bash
# 1. See what changed
abc delta knowledge/python/type-hints.md

# 2. Copy to warehouse
cp .agentic-beacon/artifacts/knowledge/python/type-hints.md \
   ~/team-warehouse/knowledge/python/type-hints.md

# 3. Commit in the warehouse
cd ~/team-warehouse
git checkout -b contrib/improve-type-hints
git add knowledge/python/type-hints.md
git commit -m "docs: improve type hints guide with Python 3.12+ patterns"
git push -u origin contrib/improve-type-hints
# Open a PR on your platform
```

---

## Contribution Types

### Improving an existing artifact

Most common — your agent refines a context, knowledge file, or skill during a session.

```bash
abc delta                                      # see what changed
abc contribute knowledge/python/type-hints.md  # contribute one file
```

### Adding a new artifact

If your agent created a new file that should live in the warehouse:

```bash
# The file is ADDED status in abc delta
abc contribute                                 # picks up both MODIFIED and ADDED files
```

Or contribute a specific new file:

```bash
abc contribute knowledge/python/new-lesson.md
```

### Excluding unregistered artifacts

To skip files that aren't registered in `beacon.yaml`:

```bash
abc contribute --exclude-unregistered
```

---

## Contribution Checklist

Before contributing to the warehouse:

- [ ] Tested the artifact in a real project — agent actually used it correctly
- [ ] Content is generic — no project-specific paths, credentials, or names
- [ ] No broken references or links
- [ ] Commit message describes **why** the change helps, not just what changed

---

## What Gets Contributed

`abc contribute` includes:

| Status | Included by default |
|--------|-------------------|
| `MODIFIED` (you edited an existing artifact) | ✅ |
| `ADDED` (you created a new file locally) | ✅ |
| `MISSING` (in beacon.yaml but not synced) | ❌ |
| `IDENTICAL` (no changes) | ❌ |

---

## Next Steps

- **[Advanced Patterns](advanced-patterns.md)** — `abc delta` in depth
- **[Day-to-Day Workflow](day-to-day-workflow.md)** — how contributing fits into the loop
- **[Creating Skills](creating-skills.md)** — writing effective skill definitions before contributing
