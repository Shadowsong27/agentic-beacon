---
name: record-knowledge
description: Systematically capture decisions, lessons, and facts into the warehouse knowledge base with optional context wiring
license: MIT
compatibility: opencode
requires:
  contexts: []
---

# Skill: Record Knowledge

---

## Purpose

Capture decisions, lessons, and facts into the connected warehouse knowledge base.
Knowledge files are written **directly to the warehouse** by the bundled
`write_knowledge.py` script — never to the project. Knowledge files are
auto-derived during `abc sync` / `abc adopt`; only optional context pointer edits
are queued in `.agentic-beacon/pending.yaml` for project wiring.

> **Important:** Do NOT write knowledge files using your editor tools directly.
> Always go through `write_knowledge.py`. The script enforces that the file
> lands inside the warehouse and refuses to write into the project's symlink
> mirror at `.agentic-beacon/artifacts/knowledge/`.

---

## When to Use

- After making a technical decision
- When learning a lesson from development
- When establishing a fact about the project
- During code reviews when patterns emerge
- At end of sessions to capture insights

---

## Invocation

```
/record-knowledge <knowledge-description>
```

**Example:**
```
/record-knowledge We decided to use Pydantic instead of dataclasses for all data carriers because it provides automatic validation and serialization
```

---

## Prerequisites

This skill requires a connected warehouse. Verify at the start:

```bash
uv run ${SKILL_DIR}/scripts/resolve_warehouse.py
```

If this command fails with `Error: no warehouse connected. Run 'abc warehouse connect <path>' first.`, stop immediately and surface the error to the user. Do not continue.

---

## Process

### Step 1: Analyze Knowledge Type

Examine the user's description and determine:

**Decision indicators:** "decided to", "chose", "selected"; comparison of alternatives; rationale for choice; trade-offs mentioned.

**Lesson indicators:** "learned", "discovered", "found out"; common mistakes or patterns; best practices or anti-patterns; gotchas or pitfalls.

**Fact indicators:** "is", "uses", "requires"; configuration information; technical specifications; process descriptions.

### Step 2: Decide Topic and Filename

**Filename** (`--name`): kebab-case, descriptive but concise.
Example: `use-pydantic-for-data-carriers`.

**Topic** (`--topic`, optional): Inspect the existing warehouse layout to
follow the established convention:

```bash
WAREHOUSE_ROOT=$(uv run ${SKILL_DIR}/scripts/resolve_warehouse.py)
ls "$WAREHOUSE_ROOT/knowledge/"
# For nested-topic warehouses, also check one level deeper:
find "$WAREHOUSE_ROOT/knowledge" -maxdepth 2 -type d
```

Rules for `--topic`:

- Each path segment must be kebab-case (`^[a-z0-9]+(?:-[a-z0-9]+)*$`).
- **Nested topics are allowed** using `/` as the separator — e.g.
  `data-platform/clickhouse`, `cicd`, `infrastructure`.
- Pick the deepest existing topic that matches the subject. If the warehouse
  already has `knowledge/data-platform/clickhouse/lessons/`, pass
  `--topic data-platform/clickhouse` — do **not** flatten it to
  `data-platform-clickhouse`, and do **not** drop to `data-platform` only.
- If no existing topic fits and the knowledge is broadly scoped, omit
  `--topic` entirely for a flat layout (`knowledge/<type>s/<name>.md`).

Examples of valid `--topic` values:

| Topic | Resulting path (for a lesson) |
|---|---|
| `infrastructure` | `knowledge/infrastructure/lessons/<name>.md` |
| `data-platform/clickhouse` | `knowledge/data-platform/clickhouse/lessons/<name>.md` |
| `python-standards` | `knowledge/python-standards/lessons/<name>.md` |
| *(omitted)* | `knowledge/lessons/<name>.md` |

### Step 3: Generate the Markdown Body

Produce the knowledge file content using the template that matches the type.

**Decisions:**

```markdown
# Decision: [Title]

**Date:** YYYY-MM-DD
**Status:** Active|Superseded|Deprecated
**Context:** [Project context]

---

## Context

[Why this decision was needed]

## Problem

[What problem we're solving]

## Decision

[What we decided]

## Implementation

[How to apply this decision]

## Consequences

**Positive:**
- [Benefits]

**Negative:**
- [Trade-offs]

## Alternatives Considered

1. [Alternative 1] - [Why not chosen]
2. [Alternative 2] - [Why not chosen]
```

**Lessons:**

```markdown
# Lesson: [Title]

**Last Updated:** YYYY-MM-DD
**Context:** [Project context]

---

## Context

[Background on the lesson]

## Pattern

[The lesson learned]

## Steps/Implementation

[How to apply this lesson]

## Common Mistakes

[What to avoid]

## Checklist

- [ ] [Action item 1]
- [ ] [Action item 2]

## Why This Matters

[Impact of following/not following this lesson]
```

**Facts:**

```markdown
# Fact: [Title]

**Last Updated:** YYYY-MM-DD
**Context:** [Project context]

---

## Overview

[Brief description]

## Details

[Detailed information]

## Usage/Application

[How to use this fact]

## Important Notes

[Critical information]
```

### Step 4: Write the File via `write_knowledge.py`

Invoke the writer with the rendered body via stdin. **This is the only way
the knowledge file is created.** Do not use your editor's write tool.

```bash
WRITTEN_PATH=$(uv run ${SKILL_DIR}/scripts/write_knowledge.py \
  --type {decision|lesson|fact} \
  --name <kebab-name> \
  [--topic <topic>] <<'KNOWLEDGE_EOF'
<rendered markdown body from Step 3>
KNOWLEDGE_EOF
)
```

The script:
- Resolves the warehouse from `.agentic-beacon/config.toml`.
- Refuses to write outside `<warehouse>/knowledge/`.
- Refuses to overwrite an existing file unless `--overwrite` is passed.
- Prints the warehouse-relative path on stdout (e.g. `knowledge/infrastructure/lessons/foo.md`).

If the script exits non-zero, surface the stderr to the user and stop.

### Step 5: Ask User for Context Pointer Target

List the available warehouse context files:

```bash
ls "$WAREHOUSE_ROOT/contexts/"*.md 2>/dev/null
```

Present options to the user — **only warehouse context files plus "skip"**:

```
Where should I add a pointer to this knowledge?

Options:
1. contexts/development-guidelines.md
2. contexts/architecture.md
...
N. Skip — don't add a pointer yet

Default: Skip
```

**Constraints:**
- Only offer files found under `$WAREHOUSE_ROOT/contexts/`.
- Do NOT offer any project-local files as pointer targets.
- If no context files exist in the warehouse, skip this step automatically.

### Step 6: Diff-Confirm Before Writing Pointer

If the user chose a context file, identify the existing section in that file
where the pointer fits best (based on topic relevance). If no section fits,
ask the user to skip or pick a section manually — never auto-create new
section headings.

Show the proposed change before writing:

```
Proposed addition to contexts/<file>.md under section "## <Section>":

+ **Brief:** [One-sentence summary]
+ **Read:** [knowledge/<type>/<name>.md]

Apply this change? [y/N]:
```

Write to `$WAREHOUSE_ROOT/contexts/<file>.md` only after the user confirms.
This edit is a normal in-place modification of an existing warehouse context;
your editor's edit tool is fine here because the path is fully qualified to
`$WAREHOUSE_ROOT`.

### Step 7: Append context pointer to pending.yaml

Do **not** append the created knowledge file to `pending.yaml`. Knowledge is
auto-derived from context and skill references during `abc sync` / `abc adopt`
and does not require beacon.yaml or symlink adoption.

If the user confirmed a context pointer write in Step 6, append only that
context entry:

```bash
uv run ${SKILL_DIR}/scripts/append_pending.py \
  --path contexts/<file>.md \
  --type context \
  --action modified \
  --source record-knowledge
```

### Step 8: Confirm Completion

```
✅ Knowledge recorded successfully!

Type:            [Decision|Lesson|Fact]
Warehouse file:  $WAREHOUSE_ROOT/<written-path>
Context pointer: [contexts/<file>.md | Skipped]
Pending entries: [1 if context pointer written, otherwise 0]

Run 'abc adopt' to wire the context pointer if one was queued.
```

---

## Examples

### Example 1: Recording a Decision (with pointer)

**User:**
```
/record-knowledge We decided not to commit temporary handoff docs because they clutter the repo
```

**Agent:**
1. Analyzes: this is a **decision**.
2. Resolves warehouse path; sees existing `knowledge/agent-practices/` group.
3. Renders the decision markdown body.
4. Calls `write_knowledge.py --type decision --topic agent-practices --name no-temporary-docs` with the body via stdin → script writes `knowledge/agent-practices/decisions/no-temporary-docs.md` in the warehouse.
5. Lists warehouse contexts → user picks `contexts/development-guidelines.md`.
6. Shows diff → user confirms.
7. Edits the warehouse context file under the appropriate section.
8. Runs `append_pending.py` once for the modified context.
9. Reports with `abc adopt` reminder for the context pointer.

### Example 2: Recording a Lesson (skip pointer, flat layout)

**User:**
```
/record-knowledge When updating warehouse structure, always run abc warehouse init to verify output
```

**Agent:**
1. Analyzes: this is a **lesson**.
2. Resolves warehouse; sees no obvious topic match → omit `--topic`.
3. Renders the lesson body.
4. Calls `write_knowledge.py --type lesson --name updating-warehouse-structure` with the body via stdin → script writes `knowledge/lessons/updating-warehouse-structure.md`.
5. User chooses: "Skip".
6. Does not call `append_pending.py` (knowledge is auto-derived).
7. Reports completion with no `abc adopt` reminder.

---

## Checklist for Agent

- [ ] Read user's knowledge description carefully
- [ ] Analyze and determine type (decision / lesson / fact)
- [ ] Run `resolve_warehouse.py` — STOP if it exits non-zero
- [ ] Inspect `$WAREHOUSE_ROOT/knowledge/` to pick a topic that matches existing convention (or omit for flat layout)
- [ ] Render the markdown body using the type-specific template
- [ ] Write the file by piping the body into `write_knowledge.py` — do NOT write the file with your editor's write tool
- [ ] Ask user which warehouse `contexts/` file for the pointer — or skip
- [ ] Show diff before writing the pointer; wait for explicit confirmation
- [ ] Do NOT run `append_pending.py` for the knowledge file
- [ ] Run `append_pending.py` for the context file if a pointer was written
- [ ] Confirm completion; remind user to run `abc adopt` only if a context pointer was queued

---

**Skill Version:** 2.1.0
**Last Updated:** 2026-05-07
