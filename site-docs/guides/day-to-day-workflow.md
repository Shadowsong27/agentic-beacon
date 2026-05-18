# Day-to-Day Workflow

Once your project is connected and initially synced, the recurring loop is:

```
1. abc sync                     — pull the latest artifacts from the warehouse
2. code with agent              — agent uses synced contexts, knowledge, and skills
3. abc warehouse status         — see what changed in the warehouse working tree
4. abc warehouse contribute     — commit improvements back to the warehouse
5. repeat
```

---

## Step 1: Pull Warehouse Updates

When a teammate adds a new context or improves a skill, pull and re-sync:

```bash
cd ~/team-warehouse && git pull
cd ~/projects/my-service && abc sync
```

```
✓ Sync complete
  Updated: 1 symlink   (skills/code-review/SKILL.md)
  Created: 0 symlinks
  Up to date: 11 symlinks
```

If the warehouse has new artifacts you haven't adopted yet:

```
✓ Sync complete
  Up to date: 11 symlinks

2 new artifact(s) available — run abc adopt to review
```

Run `abc adopt` to open the TUI and selectively add them.

---

## Step 2: Code with Your Agent

Your agent reads at session start:

- **Contexts** wired into `CLAUDE.md` / `opencode.json` — loaded automatically
- **Knowledge** — markdown files symlinked into `artifacts/`
- **Skills** — available as slash commands (`/code-review`, `/generate-tests`, etc.)

No extra setup needed — everything is in place after `abc sync`.

### Example: agent improves a knowledge file mid-session

You ask the agent to document a new error handling pattern. It writes the explanation
directly into `artifacts/knowledge/python/error-handling.md`. Because that file
is a symlink into your warehouse clone, the warehouse working tree is updated immediately.

No copy step needed — the improvement is already in the warehouse.

---

## Step 3: Review Warehouse Changes

After a coding session, check what the agent touched:

```bash
abc warehouse status
```

```
Modified files in warehouse:
  modified  knowledge/python/error-handling.md
  modified  skills/code-review/SKILL.md
```

Inspect a specific file before committing:

```bash
abc warehouse status knowledge/python/error-handling.md
```

```diff
--- a/knowledge/python/error-handling.md
+++ b/knowledge/python/error-handling.md
@@ -12,6 +12,14 @@
 ## Targeted try/except

 Keep `try` blocks small and targeted — one concern per block.
+
+## Retrying with tenacity
+
+Use `@retry` from tenacity instead of manual sleep loops:
+
+```python
+@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
+def fetch_data(url: str) -> dict: ...
+```
```

---

## Step 4: Contribute Changes Back

### Contribute everything at once

```bash
abc warehouse contribute -m "docs: add tenacity retry pattern to error handling"
```

This stages all modified warehouse files tracked by `beacon.yaml`, commits them, and exits.

### Contribute and push immediately

```bash
abc warehouse contribute -m "docs: add tenacity retry pattern" --push
```

Teammates get the update on their next `git pull && abc sync`.

### Contribute only specific files

Use plain git inside the warehouse clone to stage selectively:

```bash
cd ~/team-warehouse
git add knowledge/python/error-handling.md
git commit -m "docs: add tenacity retry pattern"
git push
```

Leave `skills/code-review/SKILL.md` unstaged if you're not ready to share that change yet.

### Discard a change you don't want to keep

A common case: you ran `abc warehouse status` and find two modified files, but only one is the change you intended. The other is a stray edit from earlier in the session — perhaps the agent retitled a skill in passing. Discard it from the warehouse clone:

```bash
cd ~/team-warehouse
git checkout -- skills/code-review/SKILL.md
```

The symlink reflects the restored file immediately in your project — no further sync needed.

---

## Checking Project Health

```bash
abc status      # connected warehouse, synced artifacts, ✓/✗ per item
abc doctor      # full validation; --fix to auto-resolve stale paths
```

---

## Next Steps

- **[Contributing Back](contributing-back.md)** — contribution workflow in depth
- **[CLI Reference](../reference/cli.md)** — every flag for `sync`, `warehouse status`, `warehouse contribute`
