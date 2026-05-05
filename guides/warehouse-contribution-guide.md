# Contributing Back to the Warehouse

When your agent improves a synced artifact — a context file, a knowledge document, or a skill — you're editing the warehouse file directly through a project symlink. Contributing is simply `git add` + `git commit` inside the warehouse, wrapped for you by `abc warehouse contribute`.

> **Read first:** [Decision — Single Warehouse Write Entrypoint](../knowledge/decisions/single-warehouse-write-entrypoint.md). Under the current sync model, every project's `.agentic-beacon/artifacts/<path>` is a symlink to `<warehouse>/<path>`. There is no project-local copy to "push back" — the edit already landed in the warehouse working tree.

---

## The Contribution Workflow

### 1. Your agent edits a synced artifact

Agents edit artifacts in place during a session. Because each file under `.agentic-beacon/artifacts/` is a symlink into the warehouse clone, the edit lands in the warehouse working tree the moment the save completes:

```
project/.agentic-beacon/artifacts/knowledge/python/type-hints.md
  └── symlink → /Users/me/Code/team-warehouse/knowledge/python/type-hints.md
                (this file is what gets written)
```

### 2. Review the warehouse state

```bash
abc warehouse status
```

Output — restricted to paths declared in your project's `beacon.yaml`:

```
Warehouse: /Users/me/Code/team-warehouse (branch: main, 0 ahead, 0 behind)

Modified:
  M  knowledge/python/type-hints.md
  M  skills/code-review/SKILL.md
```

Inspect a specific file:

```bash
abc warehouse status knowledge/python/type-hints.md
# prints unified diff for that file
```

Or widen to the full warehouse working tree (ignores `beacon.yaml` scoping):

```bash
abc warehouse status --all
```

### 3. Commit the changes

```bash
abc warehouse contribute -m "knowledge: clarify Optional vs None in type-hints"
```

This runs `git add` on the beacon.yaml-scoped modified files, then `git commit` with your message inside the warehouse clone. If you want to push immediately:

```bash
abc warehouse contribute -m "…" --push
```

On push failure the commit is still created locally — re-push with plain `git push` from the warehouse when the remote is reachable.

### 4. Teammates pick it up

Once the commit is pushed (and merged if you use PR review):

```bash
cd ~/team-warehouse && git pull
# No `abc sync` needed per-project: every project on this machine already
# reads the file through a symlink, so the updated warehouse content is
# visible immediately.
```

`abc sync` is only needed when `beacon.yaml` changes (new artifacts declared) or when your warehouse symlinks drift (missing / broken / stale targets).

---

## Common Patterns

### Improving an existing artifact

The typical case. Edit via any project symlink, then:

```bash
abc warehouse status                                              # See what changed
abc warehouse contribute -m "python: add generics guidance" --push
```

### Adding a new artifact

A new warehouse file is not visible to a project until its path is matched by that project's `beacon.yaml`.

1. Create the file directly in the warehouse clone:
   ```bash
   cd ~/team-warehouse
   $EDITOR contexts/new-context.md
   ```
2. Declare it in your project's `beacon.yaml`:
   ```yaml
   artifacts:
     contexts:
       - contexts/new-context.md
   ```
3. Sync the project so the symlink is created:
   ```bash
   abc sync
   ```
4. Commit the warehouse changes:
   ```bash
   abc warehouse contribute -m "contexts: add new-context" --push
   ```
2. Declare it in your project's `beacon.yaml`:
   ```yaml
   artifacts:
     contexts:
       - contexts/python.md
   ```
3. Sync the project so the symlink is created:
   ```bash
   abc sync
   ```
4. Commit the warehouse addition:
   ```bash
   abc warehouse contribute -m "knowledge: add python/new-lesson" --push
   ```

### Adding a new skill

Skills are directories. Create them in the warehouse, declare them in `beacon.yaml`, sync, commit:

```bash
cd ~/team-warehouse
mkdir -p skills/generate-tests
$EDITOR skills/generate-tests/SKILL.md

# In your project's beacon.yaml:
# artifacts:
#   skills:
#     - skills/generate-tests/**/*

cd ~/my-project
abc sync
abc warehouse contribute -m "skills: add generate-tests" --push
```

---

## Checklist Before Committing

- [ ] The edit is generic — no project-specific paths, credentials, or names
- [ ] Tested in a real project — the agent actually used the change correctly
- [ ] No broken markdown links or stale cross-references
- [ ] Commit message explains **why** the change helps, not just what changed

---

## When Commits Need Review

`abc warehouse contribute` creates a commit on the warehouse's current branch. For teams using PR review, two patterns work:

**Branch in the warehouse before editing:**

```bash
cd ~/team-warehouse
git checkout -b feat/python-generics-guidance
# ... edit via project symlinks ...
abc warehouse contribute -m "python: generics guidance" --push
gh pr create --fill
```

**Commit on main, then branch:**

```bash
abc warehouse contribute -m "python: generics guidance"   # commit on current branch
cd ~/team-warehouse
git checkout -b feat/python-generics-guidance HEAD~1      # branch off previous tip
git cherry-pick main                                      # bring the commit along
git push -u origin feat/python-generics-guidance
gh pr create --fill
```

The tool deliberately does not automate PR creation — warehouse git workflow is the user's choice (direct push, PR, fork-and-PR, etc.).

---

## Next Steps

- **[Getting Started](./getting-started.md)** — Sync workflow overview
- **[beacon.yaml Reference](./beacon-yaml-reference.md)** — Declaring artifacts for a project
- **[Creating Skills](./creating-skills.md)** — Writing effective SKILL.md files
- **[Decision: Single Warehouse Write Entrypoint](../knowledge/decisions/single-warehouse-write-entrypoint.md)** — Why the model works this way
