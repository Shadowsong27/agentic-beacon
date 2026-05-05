# Day-to-Day Workflow

Once your project is connected and initially synced, the recurring loop is straightforward.

## The Loop

```
1. abc sync                     — pull the latest artifacts from the warehouse
2. code with agent              — agent uses synced contexts, knowledge, and skills
3. abc warehouse status         — see what has changed in the warehouse working tree
4. abc warehouse contribute     — commit improvements back to the warehouse
5. repeat
```

---

## Step 1: Pull Warehouse Updates

When the warehouse changes (a teammate added a new context, improved a skill, etc.):

```bash
# Pull warehouse updates
cd ~/my-org-warehouse && git pull

# Re-sync your project
cd my-project && abc sync
```

After sync, if new artifacts are available that you haven't adopted yet:

```
✓ Sync complete
  Created: 2 symlinks
  Up to date: 8 symlinks

1 new artifact(s) available — run abc adopt to review
```

Run `abc adopt` to open the TUI and select new artifacts interactively.

---

## Step 2: Code with Your Agent

Your AI agent now reads:

- Contexts wired into `CLAUDE.md` or `opencode.json` (loaded at session start)
- Knowledge files auto-derived from markdown links and symlinked into `artifacts/`
- Skills available as slash commands (e.g. `/code-review`, `/generate-tests`)
- Global agents available in any project (`/reviewer`, etc.)

No extra setup needed — everything is in place after `abc sync`.

---

## Step 3: Review Warehouse Working Tree Changes

After a coding session, your agent may have improved synced artifacts. Since artifacts are symlinks into the warehouse, check with:

```bash
abc warehouse status
```

Shows modifications to warehouse files tracked by resolved artifacts:

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

---

## Step 4: Commit Changes Back

If improvements are worth sharing:

```bash
abc warehouse contribute -m "Improve type hints guide with Python 3.12+ patterns"
```

This stages and commits all files tracked by resolved artifacts that have uncommitted changes in the warehouse.

Push immediately:

```bash
abc warehouse contribute -m "Fix typo in error handling" --push
```

Once in the warehouse, teammates get the improvements on their next sync.

---

## Checking Project Health

```bash
abc status
```

Shows the connected warehouse, configured contexts and skills (with ✓/✗ for synced status), and total synced file count.

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
| Check warehouse tree changes | `abc warehouse status` |
| Share improvements | `abc warehouse contribute -m "message"` |
| Check project health | `abc status` |
| Diagnose issues | `abc doctor` |
| Reset all artifacts | `abc reset` |

---

## Next Steps

- **[Contributing Back](contributing-back.md)** — the contribution workflow in depth
- **[Advanced Patterns](advanced-patterns.md)** — glob patterns and advanced configuration
- **[Team Collaboration](team-collaboration.md)** — coordinating across a team
