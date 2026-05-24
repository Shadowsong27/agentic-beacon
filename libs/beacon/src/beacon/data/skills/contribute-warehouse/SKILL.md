---
name: contribute-warehouse
description: Guided warehouse contribution flow with lint gate, intent triage, dedup scan, cohesion split, and atomic push
license: MIT
compatibility: opencode
requires:
  contexts: []
---

# SKILL: Contribute Warehouse — Guided Contribution Flow

## Purpose

Commit and push warehouse working-tree changes through a safe, intent-aware
flow. This skill wraps `abc warehouse contribute` with conversational
pre-flight: a strict lint gate, file-level intent triage, semantic dedup scan
(for `knowledge/` files), cohesion split into logical commits, and exactly one
atomic `git push` at the end.

> **Design note:** This skill never calls `git add`, `git commit`, or `git push`
> directly. All git operations are delegated to `abc warehouse contribute` (per
> commit group) and `push_warehouse.py` (exactly once at the end). The skill's
> job is the conversational layer above those primitives.

## When to Use

- After an agent session improved a context file, a skill, or a knowledge entry
  and you want to share it back to the team warehouse
- When you have multiple dirty warehouse files and want to split them into
  logically cohesive commits
- Whenever you need the lint pre-flight gate to catch warehouse-wide integrity
  issues before committing
- As the standard contribution workflow replacing bare `abc warehouse contribute`

## Invocation

```
/contribute-warehouse
```

---

## Prerequisites

This skill requires a connected warehouse. Verify at the start:

```bash
uv run ${SKILL_DIR}/scripts/resolve_warehouse.py
```

If this command fails with `Error: no warehouse connected. Run 'abc warehouse connect <path>' first.`,
stop immediately and surface the error to the user. Do not continue.

---

## Process

### Step 1: Resolve Warehouse

Capture the warehouse root path:

```bash
WAREHOUSE_ROOT=$(uv run ${SKILL_DIR}/scripts/resolve_warehouse.py)
```

If the command exits non-zero, surface the stderr output to the user and stop.

### Step 2: Lint Pre-Flight Gate

Run the warehouse linter against the full working tree:

```bash
abc warehouse lint "$WAREHOUSE_ROOT"
```

**This is a hard gate.** If lint reports any error — even for files outside the
user's intended contribution scope — abort before committing and surface the
lint output verbatim.

Tell the user:
```
Warehouse lint failed. Resolve the following issues before contributing:

<lint output>

Suggested recovery:
  - Fix the failing files and re-run /contribute-warehouse
  - Or move the failing edits to a separate branch and re-run on a clean tree
  - As a last resort, you (the user) may discard the changes with
    `git -C "$WAREHOUSE_ROOT" checkout -- <failing-file>` — the skill itself
    will NEVER run this; destructive recovery stays with you
```

Do NOT stash, do NOT skip lint, do NOT proceed on a lint failure.

### Step 3: Summarize Dirty Warehouse Paths

Run the summarizer to build a structured view of what has changed:

```bash
uv run ${SKILL_DIR}/scripts/summarize_changes.py --warehouse "$WAREHOUSE_ROOT"
```

The summarizer enumerates **every** dirty path in the warehouse working tree
(PER-202) — no `.agentic-beacon/config.toml` lookup, no `beacon.yaml` filter,
no project-context dependency. The skill works from any CWD, including a brand
new warehouse with no projects connected yet.

Parse the JSON output. Each entry in `tracked_paths` contains:
- `path` — warehouse-relative path
- `git_status` — porcelain code (e.g. `M`, `A`, `??`)
- `diff_stat` — one-line diff summary
- `last_commit_age_days` — days since last commit, or `null`
- `warehouse_area` — top-level area (`contexts`, `knowledge`, `skills`, `agents`, or `other`)

If the JSON output is empty (`{"tracked_paths": []}`), tell the user there is
nothing to contribute and stop cleanly.

### Step 4: Intent Triage

Present the dirty tracked paths to the user and ask them to classify each as:

- **include** — commit this in the current session
- **leave-for-later** — skip for now; do not stage, stash, or modify

Example presentation:
```
Dirty tracked paths (3 files):

  1. contexts/python-standards.md   [M — 12 insertions, 3 deletions]
  2. knowledge/python/lessons/type-hints.md   [A — new file]
  3. skills/code-review/SKILL.md   [M — 2 insertions]

Which files do you want to contribute now?
(Reply with numbers, e.g. "1 2", or "all", or "none")
```

Leave-for-later files are noted in the final summary but are not touched.

### Step 5: Semantic Dedup Scan (knowledge/ files only)

For each **included** file under `knowledge/**`:

1. Identify the `<topic>/<kind>/` parent directory (e.g. `knowledge/python/lessons/`)
2. Read all sibling files in that directory
3. Ask yourself: does the new file substantially overlap an existing sibling?
   - If yes, flag it: "This file may duplicate `<sibling>` — compare and merge or rename before contributing."
   - If no, proceed

Files outside `knowledge/` (contexts, skills, agents) are not scanned for dedup.

### Step 6: Cohesion Check

Examine the included file set and determine whether it represents a single
cohesive change or multiple independent changes.

**Single cohesive change** (e.g. one new lesson + its supporting context update):
→ One commit.

**Multiple independent changes** (e.g. a Python standards update AND a CI
lesson unrelated to it):
→ Propose a split. Present the groups to the user:

```
The included files span 2 independent changes. Proposed split:

  Commit 1: Python standards update
    - contexts/python-standards.md
    - knowledge/python/lessons/type-hints.md

  Commit 2: CI workflow improvement
    - knowledge/cicd/lessons/deploy-via-git.md

Confirm this split? (yes / edit)
```

The user may accept the proposed split or adjust the groupings.

### Step 7: Draft Commit Message(s)

For each commit group, extract the per-path `git_status` codes from the
`summarize_changes.py` output, then call:

```bash
uv run ${SKILL_DIR}/scripts/draft_commit_message.py \
  --paths <space-separated warehouse-relative paths in this group> \
  --git-statuses <per-path status codes in the same order as --paths> \
  --subject "<LLM-drafted one-line subject>"
```

Example — two paths with known statuses:

```bash
uv run ${SKILL_DIR}/scripts/draft_commit_message.py \
  --paths skills/foo/SKILL.md skills/bar/SKILL.md \
  --git-statuses " M" "A " \
  --subject "fix bar invocation example"
```

The `--git-statuses` argument takes one code per path (two-character porcelain
format, e.g. `" M"` for working-tree modified, `"A "` for staged new file).
Without `--git-statuses`, skills and agents paths default to `feat` regardless
of whether they are new or modified — always pass the statuses when available.

The script derives the `<type>` and `<scope>` deterministically from the paths
and statuses. You supply the `<subject>` based on the diff content and the
user's intent.

Present the drafted message(s) to the user for confirmation or editing before
proceeding.

### Step 8: Commit Each Group

For each confirmed commit group (in order), pass the group's paths explicitly
using the `--paths` flag so only those files are committed:

```bash
abc warehouse contribute -m "<type>(<scope>): <subject>" \
  --paths <path1> --paths <path2> ...
```

**Important:** Do NOT pass `--push` here. All commits land locally first.
Using `--paths` ensures only the files in this group are staged and committed —
files classified as leave-for-later remain untouched in the working tree.
If `abc warehouse contribute` exits non-zero, surface the error and stop.

### Step 9: Atomic Push

After all commits land successfully:

```bash
uv run ${SKILL_DIR}/scripts/push_warehouse.py --warehouse "$WAREHOUSE_ROOT"
```

**Success (exit 0):** Report the committed SHAs and confirm the push.

**Failure (exit non-zero):**
- The script prints the recovery command on stdout:
  `git -C <warehouse> push origin <branch>`
- Surface the error and the recovery command to the user:
  ```
  Push failed. Your commits are safe locally. When network is restored, run:

    git -C "$WAREHOUSE_ROOT" push origin <branch>
  ```
- Do NOT retry automatically. Do NOT attempt any destructive git ops.

---

## Final Summary

After the flow completes, report:

```
Contribution summary:

  Committed:
    <sha1> — <type>(<scope>): <subject>
    <sha2> — <type>(<scope>): <subject>

  Push status: [pushed | failed — recovery command above]

  Left for later:
    - <path>  (reason: user deferred)
```

---

## Examples

### Example 1: Single-File Happy Path

**User:** `/contribute-warehouse`

**Agent:**
1. Resolves warehouse → `/home/user/my-warehouse`
2. Runs `abc warehouse lint` → clean, proceeds
3. Summarizes changes → 1 dirty file: `contexts/python-standards.md`
4. Asks user: "Include this file?" → yes
5. No `knowledge/` files → skips dedup scan
6. Cohesion check: single file → one commit
7. Drafts message: `docs(contexts): add loguru section to python standards`
8. Calls `abc warehouse contribute -m "docs(contexts): add loguru section to python standards" --paths contexts/python-standards.md`
9. Calls `push_warehouse.py` → push succeeds
10. Reports: "Committed `a1b2c3d` — `docs(contexts): add loguru section`. Pushed."

---

### Example 2: Multi-File Cohesion Split

**User:** `/contribute-warehouse`

**Agent:**
1. Resolves warehouse → `/home/user/my-warehouse`
2. Lint passes
3. Summarizes → 3 dirty files: `contexts/python-standards.md`, `knowledge/python/lessons/type-hints.md`, `knowledge/cicd/lessons/deploy-via-git.md`
4. User includes all 3
5. Dedup scan: `knowledge/python/lessons/type-hints.md` — no overlaps with siblings; `knowledge/cicd/lessons/deploy-via-git.md` — no overlaps
6. Cohesion check: python files are cohesive (group 1), CI lesson is independent (group 2)
7. Proposes 2-commit split; user confirms
8. Drafts `docs(python-standards): add type hints lesson` and `docs(cicd): add deploy-via-git lesson`
9. Calls `abc warehouse contribute -m "docs(python-standards): add type hints lesson" --paths contexts/python-standards.md --paths knowledge/python/lessons/type-hints.md`
   then `abc warehouse contribute -m "docs(cicd): add deploy-via-git lesson" --paths knowledge/cicd/lessons/deploy-via-git.md`
10. Calls `push_warehouse.py` once → success
11. Reports: "Committed 2 changes. Pushed."

---

### Example 3: Lint Failure Abort

**User:** `/contribute-warehouse`

**Agent:**
1. Resolves warehouse
2. `abc warehouse lint` returns non-zero — skill `broken-skill/SKILL.md` has no frontmatter
3. Surfaces lint output and stops: "Warehouse lint failed. Fix `skills/broken-skill/SKILL.md` before contributing."

---

### Example 4: Airgap Push Failure

**User:** `/contribute-warehouse`

**Agent:**
1–8. Normal flow; all commits land locally
9. `push_warehouse.py` fails (no network)
10. Reports:
    ```
    Push failed (no network). Your 2 commits are safe locally.
    When network is restored, run:

      git -C /home/user/my-warehouse push origin main
    ```

---

## Checklist for Agent

- [ ] Run `resolve_warehouse.py` — STOP if exits non-zero
- [ ] Run `abc warehouse lint <warehouse>` — STOP and surface errors if non-zero
- [ ] Run `summarize_changes.py` — STOP if no dirty tracked paths
- [ ] Triage dirty files with the user (include / leave-for-later)
- [ ] Dedup scan for `knowledge/` files — flag overlaps before proceeding
- [ ] Cohesion check — propose split if multiple independent changes
- [ ] Draft commit message(s) via `draft_commit_message.py` (pass `--git-statuses`) — confirm with user
- [ ] Call `abc warehouse contribute -m "<msg>" --paths <p1> --paths <p2> ...` per group — NO `--push` flag
- [ ] Call `push_warehouse.py --warehouse <path>` exactly once
- [ ] Report committed SHAs, push status, and any left-for-later files

---

## Helper Scripts

| Script | Purpose | Dependencies |
|---|---|---|
| `resolve_warehouse.py` | Resolve warehouse path from `.agentic-beacon/config.toml` | stdlib only |
| `summarize_changes.py` | Build structured JSON view of every dirty warehouse path | `pyyaml` (PEP 723) |
| `draft_commit_message.py` | Derive deterministic Conventional Commits message | stdlib only |
| `push_warehouse.py` | Atomic push with recovery-command output on failure | stdlib only |

---

## Related

- `record-knowledge` — Capture decisions and lessons into the warehouse knowledge base
- `record-skill` — Scaffold new Beacon skills in the warehouse

---

**Skill Version:** 1.0.0
**Last Updated:** 2026-05-17
