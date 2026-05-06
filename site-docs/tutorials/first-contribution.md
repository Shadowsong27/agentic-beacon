# Tutorial: Your First Contribution

This tutorial walks through a realistic day using Agentic Beacon — from pulling the morning's warehouse updates to contributing an improvement back to your team.

**What you'll do:**

1. Pull warehouse updates and sync your project
2. Run a coding session where the agent improves an artifact
3. Review what changed
4. Contribute the improvement back
5. Verify your teammates can pick it up

**Prerequisites:** You've already [connected your project](../guides/connecting-projects.md) and run `abc sync` at least once.

---

## Setup

In this tutorial you're working on `payments-service`. Your team warehouse lives at `~/team-warehouse`.

```
~/team-warehouse/        ← shared warehouse (git repo)
~/projects/payments-service/   ← your project (connected via beacon.yaml)
```

---

## Step 1: Pull the Morning's Updates

A teammate added a new SQL review skill overnight. Pull it into the warehouse and sync:

```bash
cd ~/team-warehouse && git pull
```

```
remote: Enumerating objects: 6, done.
Updating abc1234..def5678
 skills/sql-review/SKILL.md | 47 ++++++++++++++++++++++++++++++++++++
 1 file changed, 47 insertions(+)
```

```bash
cd ~/projects/payments-service && abc sync
```

```
✓ Sync complete
  Updated: 1 symlink   (skills/sql-review/SKILL.md)
  Up to date: 11 symlinks
```

The SQL review skill is now available to your agent as `/sql-review`.

---

## Step 2: Code with Your Agent

You open your editor, start a Claude Code session, and ask it to review a new migration file.

The agent runs `/sql-review` and flags a decimal precision issue. You fix the migration together, then ask the agent to document the pattern for the team:

> *"Add a note to our error-handling knowledge file about using `NUMERIC(19,4)` for financial amounts."*

The agent opens `.agentic-beacon/artifacts/contexts/knowledge/error-handling.md` and adds the section. Because that file is a **symlink into the warehouse**, the warehouse working tree is updated immediately — no copy step.

---

## Step 3: Review What Changed

After the session, check the warehouse:

```bash
abc warehouse status
```

```
Modified files in warehouse:
  modified  knowledge/python/error-handling.md
  modified  skills/sql-review/SKILL.md
```

Two files changed. You only authored the `error-handling.md` addition — the `sql-review` change must be a stray edit from earlier in the session.

Inspect each one:

```bash
abc warehouse status knowledge/python/error-handling.md
```

```diff
--- a/knowledge/python/error-handling.md
+++ b/knowledge/python/error-handling.md
@@ -38,3 +38,12 @@
 ## Connection timeouts

 Always set an explicit timeout on httpx clients. Default is `None` (blocks forever).
+
+## Financial amounts
+
+Always use `NUMERIC(19,4)` (or Python `Decimal`) for monetary values.
+Never use `FLOAT` or `DOUBLE` — binary floating point cannot represent
+decimal fractions exactly, which causes rounding errors in summations.
+
+```python
+from decimal import Decimal
+total = Decimal("0.00")
+```
```

Looks good. Now check the SQL review skill:

```bash
abc warehouse status skills/sql-review/SKILL.md
```

```diff
--- a/skills/sql-review/SKILL.md
+++ b/skills/sql-review/SKILL.md
@@ -1,4 +1,4 @@
-# SQL Review
+# SQL Review Skill
```

Just a title casing change — not worth a commit on its own. Discard it:

```bash
cd ~/team-warehouse
git checkout -- skills/sql-review/SKILL.md
```

---

## Step 4: Contribute the Improvement

Commit just the `error-handling.md` change:

```bash
cd ~/team-warehouse
git add knowledge/python/error-handling.md
git commit -m "docs: document NUMERIC(19,4) rule for financial amounts"
git push
```

```
[main 9f3c21a] docs: document NUMERIC(19,4) rule for financial amounts
 1 file changed, 11 insertions(+)
```

Alternatively, use `abc warehouse contribute` to stage-and-commit everything tracked by `beacon.yaml` in one step:

```bash
abc warehouse contribute -m "docs: document NUMERIC(19,4) rule for financial amounts" --push
```

Both produce the same result. Use whichever fits your flow — plain git gives you more granular control; `abc warehouse contribute` is faster when you want to ship everything at once.

---

## Step 5: Verify Your Teammates Can Pick It Up

Anyone on the team can now get your change:

```bash
cd ~/team-warehouse && git pull
cd my-project && abc sync
```

```
✓ Sync complete
  Updated: 1 symlink   (knowledge/python/error-handling.md)
  Up to date: 11 symlinks
```

Their agent picks up the new financial amounts rule on the next session — no manual steps.

---

## What You Learned

- `abc sync` updates symlinks when the warehouse changes — re-run it after every `git pull`
- Editing a synced artifact **is** editing the warehouse; no copy step needed
- `abc warehouse status` scopes to files tracked by `beacon.yaml`, not the entire warehouse
- Use plain git inside the warehouse for selective commits; use `abc warehouse contribute` for convenience
- Discarding an unwanted change is just `git checkout -- <file>` in the warehouse

---

## Next Steps

- **[Contributing Back](../guides/contributing-back.md)** — reference guide for the full contribute workflow
- **[Day-to-Day Workflow](../guides/day-to-day-workflow.md)** — the loop in summary form
- **[Creating Skills](../guides/creating-skills.md)** — write a new skill and contribute it to the warehouse
