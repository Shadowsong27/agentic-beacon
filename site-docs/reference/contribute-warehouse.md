# The `contribute-warehouse` Bundled Skill

> **Invocation:** `/contribute-warehouse`

The `contribute-warehouse` bundled skill wraps `abc warehouse contribute` with a
guided, conversational contribution flow — lint pre-flight gate, file-level intent
triage, semantic dedup scan, cohesion split into logical commits, and exactly one
atomic `git push` at the end.

This is the recommended way to commit and push warehouse changes. It catches
warehouse-wide integrity issues before any commit touches `git log`, and helps
structure your changes into a clean commit history.

---

## Quick Invocation

From an OpenCode or Claude Code session in a connected project:

```
/contribute-warehouse
```

The skill walks you through the full flow interactively.

---

## Flow Overview

The skill runs these steps in order:

1. **Resolve warehouse** — locate `.agentic-beacon/config.toml` and extract the warehouse path
2. **Lint pre-flight gate** — run `abc warehouse lint <warehouse>`; abort on any error and suggest `abc warehouse lint --fix <warehouse>` for fixable malformed cross-artifact-relative links
3. **Summarize dirty paths** — call `summarize_changes.py` to get a structured JSON view of what has changed
4. **Intent triage** — ask you which files to include or leave for later
5. **Dedup scan** (knowledge/ files only) — scan sibling files for overlapping content
6. **Cohesion check** — determine if the included files form one cohesive change or should be split
7. **Draft commit message(s)** — call `draft_commit_message.py` to produce Conventional Commits messages
8. **Commit each group** — call `abc warehouse contribute -m "<message>" --paths <file1> --paths <file2> ...` per group (no `--push`). `--paths` is a repeatable Click option: pass it once per file, not once with a space-separated list.
9. **Atomic push** — call `push_warehouse.py` exactly once after all commits land

---

## Lint Gate

Before any file is staged, the skill runs:

```bash
abc warehouse lint <warehouse-path>
```

This is a **hard gate** — if lint reports any error, the skill aborts. This applies
even to files outside your intended contribution scope. Resolve lint failures first:

- Run `abc warehouse lint --fix <warehouse-path>` when the failure is a fixable malformed cross-artifact-relative link. The rewrite is idempotent, preserves anchors, and leaves warehouse-escape or missing-target findings for manual repair.
- Fix the failing files
- Or discard them: `git -C <warehouse> checkout -- <file>`

This design follows Decision 4 in the OpenSpec design doc: strict-gate against the
full working tree is intentional, not a UX oversight.

---

## Intent Triage

The skill presents all dirty tracked paths and asks which to include:

```
Dirty tracked paths (3 files):

  1. contexts/python-standards.md   [M — 12 insertions, 3 deletions]
  2. knowledge/python/lessons/type-hints.md   [A — new file]
  3. skills/code-review/SKILL.md   [M — 2 insertions]

Which files do you want to contribute now?
(Reply with numbers, e.g. "1 2", or "all", or "none")
```

Files you mark as **leave-for-later** are listed in the final summary but are never
staged, stashed, or modified. No destructive operations happen on deferred files.

---

## Dedup Scan

For each included file under `knowledge/**`, the skill reads its sibling files in
the same `<topic>/<kind>/` directory and asks whether the new content substantially
overlaps an existing entry.

Files outside `knowledge/` (contexts, skills, agents) are not scanned.

Example flag:
```
knowledge/python/lessons/type-hints.md may duplicate:
  knowledge/python/lessons/type-annotations.md
  → Both cover Python type annotation patterns. Consider merging or renaming.
```

The dedup scan in v1 is LLM-driven, scoped to the local directory. Cross-warehouse
vectorized search is on the roadmap.

---

## Cohesion Split

After triage and dedup, the skill evaluates whether your included files form a
**single cohesive change** or **multiple independent changes**.

Single cohesion example:
```
contexts/python-standards.md + knowledge/python/lessons/type-hints.md
→ Related — one commit.
```

Split example:
```
knowledge/python/lessons/type-hints.md + knowledge/cicd/lessons/deploy-via-git.md
→ Independent topics — proposed 2-commit split:
    Commit 1: Python type hints lesson
    Commit 2: CI deployment lesson
```

You confirm the split (or adjust it) before any commit is made. Each group is then
committed with its own `--paths` list, for example:

```bash
abc warehouse contribute -m "docs(python): add type hints lesson" \
    --paths knowledge/python/lessons/type-hints.md
abc warehouse contribute -m "docs(cicd): add deploy-via-git lesson" \
    --paths knowledge/cicd/lessons/deploy-via-git.md
```

**Always pass `--paths`** when the skill flow excluded any dirty file as
*leave-for-later*. Omitting `--paths` causes `abc warehouse contribute` to
stage every dirty tracked file in the working tree, which would sweep
deferred files into the commit and break the skill's "leave-for-later files
are never modified" contract. The only safe case for omitting `--paths` is
when there is exactly one cohesive group AND no files were excluded from
the contribution — in practice the skill always passes `--paths` to stay
unambiguously safe.

---

## Commit Messages

The skill drafts Conventional Commits messages using `draft_commit_message.py`:

```
docs(contexts): add loguru section to python standards
docs(python): add type hints lesson
```

The `type` and `scope` are derived deterministically from the file paths.
The `subject` is drafted by the LLM based on the diff content and confirmed by you.

Scope derivation rules:
- `contexts/` files → scope `contexts`
- `skills/` files → scope `skills`
- `agents/` files → scope `agents`
- `knowledge/<topic>/` same topic → scope `<topic>`
- `knowledge/` mixed topics → scope `knowledge`
- Mixed top-level dirs → scope `general`

Type derivation rules:
- `contexts/` or `knowledge/` → `docs`
- `skills/` or `agents/` new files → `feat`
- `skills/` or `agents/` modifications → `fix`
- Mixed or unclassifiable → `chore`

---

## Atomic Push

After all commits land locally, the skill calls `push_warehouse.py` exactly once:

```bash
uv run ${SKILL_DIR}/scripts/push_warehouse.py --warehouse <path>
```

**On success:** reports the committed SHAs and confirms the push.

**On failure:** the script prints a ready-to-paste recovery command to stdout:
```
git -C /path/to/warehouse push origin main
```

The skill surfaces this command and stops. Your local commits are safe. Run the
recovery command once network is restored.

---

## Airgap Recovery

If push fails due to network issues:

1. All commits already landed locally — nothing is lost
2. The skill prints the recovery command
3. Once network is restored, copy-paste the command:
   ```bash
   git -C /path/to/warehouse push origin <branch>
   ```
4. Re-run `/contribute-warehouse` is not needed — just push manually

The skill never auto-retries and never performs any destructive git operations
(`reset`, `--force`, `--amend`, `push -f`).

---

## Example Transcript

```
User: /contribute-warehouse

Agent: Resolving warehouse... found at /home/user/my-warehouse

Agent: Running warehouse lint...
       ✓ Lint passed (0 errors)

Agent: Scanning dirty tracked paths...
       Found 2 modified files:
         1. contexts/python-standards.md  [M — 12 insertions, 3 deletions]
         2. knowledge/python/lessons/type-hints.md  [A — new file]

Agent: Which files do you want to contribute?
       (Enter numbers, "all", or "none")

User: all

Agent: Checking for dedup in knowledge/python/lessons/...
       Scanned 4 siblings — no significant overlap found.

Agent: Cohesion check: contexts update + its matching knowledge lesson.
       These are related — proposing a single commit.

Agent: Drafted commit message:
       docs(python): add type hints lesson and update python standards

       Confirm? (yes/edit)

User: yes

Agent: Committing... abc warehouse contribute -m "docs(python): add type hints lesson and update python standards"
       ✓ Committed: a1b2c3d

Agent: Pushing... (push_warehouse.py)
       ✓ Pushed to origin/main

Agent: Contribution summary:
       Committed: a1b2c3d — docs(python): add type hints lesson and update python standards
       Push status: pushed
       Left for later: (none)
```

---

## Helper Scripts

The skill ships four PEP 723 helper scripts in its `scripts/` directory:

| Script | Dependencies | Purpose |
|---|---|---|
| `resolve_warehouse.py` | stdlib only | Resolve warehouse path from `.agentic-beacon/config.toml` |
| `summarize_changes.py` | `pyyaml>=6.0` | Build structured JSON view of dirty tracked paths |
| `draft_commit_message.py` | stdlib only | Derive deterministic Conventional Commits message |
| `push_warehouse.py` | stdlib only | Atomic push with recovery-command output on failure |

---

## Related

- [Contributing Back](../guides/contributing-back.md) — manual `abc warehouse contribute` workflow
- [Bundled Skills](../concepts/bundled-skills.md) — how bundled skills work
- [Creating Skills](../guides/creating-skills.md) — authoring warehouse skills manually
