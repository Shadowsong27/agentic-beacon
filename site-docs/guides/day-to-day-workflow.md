# Day-to-Day Workflow

Once your project is connected and initially synced, the recurring loop is straightforward.

## The Loop

```
1. abc sync          — pull the latest artifacts from the warehouse
2. code with agent   — agent uses synced contexts, knowledge, and skills
3. abc delta         — see what has drifted locally
4. abc contribute    — promote valuable changes back to the warehouse
5. repeat
```

---

## Step 1: Pull Warehouse Updates

When the warehouse changes (a teammate added a new knowledge file, improved a context, etc.):

```bash
# Pull warehouse updates
cd ~/my-org-warehouse && git pull

# Re-sync your project
cd my-project && abc sync
```

After sync, if new artifacts are available that you haven't adopted yet:

```
✓ Sync complete
  Copied: 2 files
  Unchanged: 8 files

1 new artifact(s) available — run abc adopt to review
```

Run `abc adopt` to open the TUI and select new artifacts interactively.

---

## Step 2: Code with Your Agent

Your AI agent now reads:

- Contexts wired into `AGENTS.md` or `opencode.json` (loaded at session start)
- Knowledge files referenced by path from contexts
- Skills available as slash commands (e.g. `/code-review`, `/generate-tests`)
- Global agents available in any project (`/reviewer`, etc.)

No extra setup needed — everything is in place after `abc sync`.

---

## Step 3: Review Local Drift

After a coding session, your agent may have improved synced artifacts. Check with:

```bash
abc delta
```

Shows all local differences from the warehouse:

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

Shows a line-by-line diff.

---

## Step 4: Contribute Back

If local changes are worth sharing:

```bash
abc contribute
```

By default, this:

1. Creates a `contrib/<timestamp>` branch in the warehouse
2. Commits the changes
3. Pushes and opens a PR via `gh`
4. Prints the PR URL

Contribute a single file:

```bash
abc contribute knowledge/python/type-hints.md
```

Preview before contributing:

```bash
abc contribute --dry-run
```

Once the PR is merged, teammates get the improvements on their next sync.

---

## Checking Project Health

```bash
abc status
```

Shows the connected warehouse, configured artifacts, and sync state:

```
Warehouse: /Users/you/my-org-warehouse

Configured Contexts
  ✓ contexts/global.md
  ✓ contexts/teams/backend/AGENTS.md

Configured Knowledge Patterns
  • knowledge/python/**/*.md

Configured Skills
  ✓ code-review
  ✓ generate-tests
```

```bash
abc doctor
```

Validates the full setup and reports any issues. Use `--fix` to auto-migrate stale paths.

---

## Listing Installed Artifacts

```bash
abc list              # list synced artifacts
abc list agents       # list globally installed agents
```

---

## Quick Reference

| Situation | Command |
|-----------|---------|
| Pull warehouse updates | `cd ~/warehouse && git pull && cd project && abc sync` |
| Discover new artifacts | `abc adopt` |
| Check local drift | `abc delta` |
| Share improvements | `abc contribute` |
| Check project health | `abc status` |
| Diagnose issues | `abc doctor` |
| Reset all artifacts | `abc reset` |

---

## Next Steps

- **[Contributing Back](contributing-back.md)** — the contribution workflow in depth
- **[Advanced Patterns](advanced-patterns.md)** — `abc delta`, sync flags, glob patterns
- **[Team Collaboration](team-collaboration.md)** — coordinating across a team
