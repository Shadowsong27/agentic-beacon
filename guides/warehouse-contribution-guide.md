# Contributing Back to the Warehouse

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

Copy a single file back to the warehouse:

```bash
abc contribute knowledge/python/type-hints.md
```

Or contribute everything that changed at once:

```bash
abc contribute --all
```

Preview before committing:

```bash
abc contribute --all --dry-run
```

`abc contribute` copies the files and prints the exact git commands to run next.

### 4. Commit in the warehouse

```bash
cd ~/team-warehouse
git diff                    # Review what changed
git add .
git commit -m "feat(python): improve type hints guide with 3.10+ syntax"
git push
```

### 5. Teammates pick it up

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
abc contribute knowledge/python/type-hints.md  # Contribute the change
cd ~/team-warehouse
git commit -m "docs(python): clarify type hint guidance"
```

### Adding a new artifact

If your agent created a new file that should live in the warehouse:

1. Add it to `beacon.yaml` so it's tracked
2. Run `abc sync` (to register it)
3. Run `abc contribute knowledge/python/new-lesson.md`

Or just use `--all` which picks up both `MODIFIED` and `ADDED` files.

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

## Pull Request Workflow (for team warehouses)

If your warehouse uses PRs rather than direct push:

```bash
cd ~/team-warehouse
git checkout -b improve-python-type-hints
git add .
git commit -m "feat(python): add str | None guidance for Python 3.10+"
git push -u origin improve-python-type-hints
# Open PR on GitHub/GitLab
```

**PR description template:**

```markdown
## Summary
<What changed and why it helps agents>

## Testing
- Tested in [project name] for [duration]
- Agents now correctly [specific behavior]

## Impacted Files
- knowledge/python/type-hints.md
```

---

## Next Steps

- **[Getting Started](./getting-started.md)** — Sync workflow overview
- **[Advanced Patterns](./advanced-patterns.md)** — `abc delta` in depth
- **[Creating Skills](./creating-skills.md)** — Writing effective SKILL.md files
