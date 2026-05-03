# Contributing Back to the Warehouse

> **Superseded by** [`guides/warehouse-contribution-guide.md`](../../guides/warehouse-contribution-guide.md) (new version) and the [`single-warehouse-write-entrypoint`](../../knowledge/decisions/single-warehouse-write-entrypoint.md) decision. The workflow below is the **pre-symlink copy-based contribute flow** — retained for historical context only. The commands shown here (`abc contribute`, `abc delta`) no longer exist; use `abc warehouse contribute` and `abc warehouse status` instead.

---

When your agent improves a synced artifact — a context file, a knowledge document, or a skill — those improvements live in `.agentic-beacon/artifacts/` and are gitignored by default. Use `abc contribute` to copy them back to the warehouse so the whole team benefits.

---

## The Contribution Workflow

### 1. Your agent edits a synced artifact

Agents often edit artifacts in place during a session. For example:

```
.agentic-beacon/artifacts/knowledge/python/type-hints.md   ← agent improved this
.agentic-beacon/artifacts/skills/code-review/SKILL.md       ← agent refined this
```

These changes are local-only. To share them, you need to contribute them back.

### 2. Review what changed

```bash
abc delta
```

Shows a summary of all differences between your local artifacts and the warehouse:

```
Delta Summary
──────────────────────────────────────
MODIFIED  knowledge/python/type-hints.md
MODIFIED  skills/code-review/SKILL.md
ADDED     knowledge/python/new-lesson.md
```

Inspect a specific file:

```bash
abc delta knowledge/python/type-hints.md
```

### 3. Contribute changes back

Contribute everything that changed at once (default):

```bash
abc contribute
```

Or contribute a single file:

```bash
abc contribute knowledge/python/type-hints.md
```

Preview before contributing:

```bash
abc contribute --dry-run
```

By default `abc contribute` automatically:
1. Creates a `contrib/<timestamp>` branch in the warehouse
2. Commits the changes
3. Pushes and opens a PR via `gh`
4. Prints the PR URL

If `gh` is not installed or the warehouse has no remote, it falls back to printing the manual git steps. You can also opt out of the auto workflow explicitly:

```bash
abc contribute --manual-git
```

### 4. Teammates pick it up

Once the PR is merged:

```bash
cd ~/team-warehouse && git pull
cd my-project && abc sync
```

---

## Contribution Types

### Improving an existing artifact

The most common case — your agent refines a context, knowledge file, or skill during a session.

```bash
abc delta                                      # See what changed
abc contribute knowledge/python/type-hints.md  # Contribute the change (auto PR)
```

### Adding a new artifact

If your agent created a new file that should live in the warehouse:

1. Add it to `beacon.yaml` so it's tracked
2. Run `abc sync` (to register it)
3. Run `abc contribute knowledge/python/new-lesson.md`

Or just run `abc contribute` (no file argument) which picks up both `MODIFIED` and `ADDED` files.

### Adding a new skill

```bash
# 1. Create the skill directory in the warehouse
mkdir -p ~/team-warehouse/skills/generate-tests
# Write SKILL.md into the warehouse directly — no need to contribute

# 2. Declare it in beacon.yaml
# artifacts:
#   skills:
#     - skills/generate-tests/**/*

# 3. Sync (wires skills automatically)
abc sync
# Or to install a single skill: abc install skills/generate-tests
```

---

## Contribution Checklist

Before committing to the warehouse:

- [ ] Tested the artifact in a real project — agent actually used it correctly
- [ ] Content is generic — no project-specific paths, credentials, or names
- [ ] No broken references or links
- [ ] Commit message describes **why** the change helps (not just what changed)

---

## Pull Request Workflow

`abc contribute` creates a PR automatically when the warehouse has a GitHub remote and `gh` is installed. The generated PR body lists each contributed file and its status:

```markdown
## Contributed artifacts

- `knowledge/python/type-hints.md` (modified)
- `knowledge/python/new-lesson.md` (added)
```

**Opting out:** pass `--manual-git` to skip the auto workflow and get the manual git steps printed instead — useful for GitLab, Bitbucket, or any non-GitHub remote:

```bash
abc contribute --manual-git
```

---

## Next Steps

- **[Getting Started](./getting-started.md)** — Sync workflow overview
- **[Advanced Patterns](./advanced-patterns.md)** — `abc delta` in depth
- **[Creating Skills](./creating-skills.md)** — Writing effective SKILL.md files
