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
Writes knowledge files directly to the warehouse working tree. Knowledge files are
auto-derived during `abc sync` / `abc adopt`; only optional context pointer edits
are queued in `.agentic-beacon/pending.yaml` for project wiring.

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

**Decision indicators:**
- "decided to", "chose", "selected"
- Comparison of alternatives
- Rationale for choice
- Trade-offs mentioned

**Lesson indicators:**
- "learned", "discovered", "found out"
- Common mistakes or patterns
- Best practices or anti-patterns
- Gotchas or pitfalls

**Fact indicators:**
- "is", "uses", "requires"
- Configuration information
- Technical specifications
- Process descriptions

### Step 2: Resolve Warehouse

Run the warehouse resolver and capture the path:

```bash
WAREHOUSE_ROOT=$(uv run ${SKILL_DIR}/scripts/resolve_warehouse.py)
```

If the command exits non-zero, surface the stderr output to the user and stop.

### Step 3: Create Knowledge File in Warehouse

**File naming:** kebab-case, descriptive but concise.
Example: `use-pydantic-for-data-carriers.md`

**Write to (warehouse-relative paths):**
- Decisions: `$WAREHOUSE_ROOT/knowledge/decisions/<name>.md`
- Lessons: `$WAREHOUSE_ROOT/knowledge/lessons/<name>.md`
- Facts: `$WAREHOUSE_ROOT/knowledge/facts/<name>.md`

**File format — Decisions:**

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

**File format — Lessons:**

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

**File format — Facts:**

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

### Step 4: Ask User for Context Pointer Target

List the available warehouse context files:

```bash
ls $WAREHOUSE_ROOT/contexts/*.md 2>/dev/null
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

**Important constraints:**
- Only offer files found under `$WAREHOUSE_ROOT/contexts/`
- Do NOT offer any project-local files as pointer targets
- If no context files exist in the warehouse, skip this step automatically

### Step 5: Diff-Confirm Before Writing Pointer

If the user chose a context file, identify the existing section in that file where
the pointer fits best (based on topic relevance). If no section fits, ask the user
to skip or pick a section manually — never auto-create new section headings.

Show the proposed change before writing:

```
Proposed addition to contexts/<file>.md under section "## <Section>":

+ **Brief:** [One-sentence summary]
+ **Read:** [knowledge/<type>/<name>.md]

Apply this change? [y/N]:
```

Write to `$WAREHOUSE_ROOT/contexts/<file>.md` only after the user confirms.

### Step 6: Append context pointer to pending.yaml

Do **not** append the created `knowledge/<type>/<name>.md` file to
`pending.yaml`. Knowledge is auto-derived from context and skill references during
`abc sync` / `abc adopt` and does not require beacon.yaml or symlink adoption.

If the user confirmed a context pointer write in Step 5, append only that context
entry:

```bash
uv run ${SKILL_DIR}/scripts/append_pending.py \
  --path contexts/<file>.md \
  --type context \
  --action modified \
  --source record-knowledge
```

### Step 7: Confirm Completion

```
✅ Knowledge recorded successfully!

Type:            [Decision|Lesson|Fact]
Warehouse file:  $WAREHOUSE_ROOT/knowledge/<type>/<name>.md
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
1. Analyzes: this is a **decision**
2. Resolves warehouse path via `resolve_warehouse.py`
3. Creates: `$WAREHOUSE_ROOT/knowledge/decisions/no-temporary-docs.md`
4. Lists warehouse contexts → user picks `contexts/development-guidelines.md`
5. Shows diff → user confirms
6. Writes pointer under appropriate section
7. Runs `append_pending.py` once for the modified context
8. Reports with `abc adopt` reminder for the context pointer

### Example 2: Recording a Lesson (skip pointer)

**User:**
```
/record-knowledge When updating warehouse structure, always regenerate examples/sample-warehouse
```

**Agent:**
1. Analyzes: this is a **lesson**
2. Resolves warehouse path
3. Creates: `$WAREHOUSE_ROOT/knowledge/lessons/updating-warehouse-structure.md`
4. User chooses: "Skip"
5. Does not write pending.yaml (knowledge is auto-derived)
6. Reports completion with no `abc adopt` reminder

---

## Checklist for Agent

- [ ] Read user's knowledge description carefully
- [ ] Analyze and determine type (decision/lesson/fact)
- [ ] Run `resolve_warehouse.py` — STOP if it exits non-zero
- [ ] Choose appropriate filename (kebab-case)
- [ ] Write file to `$WAREHOUSE_ROOT/knowledge/<type>/` (warehouse, not the project)
- [ ] Ask user which warehouse `contexts/` file for the pointer — or skip
- [ ] Show diff before writing pointer; wait for explicit confirmation
- [ ] Do NOT run `append_pending.py` for the knowledge file
- [ ] Run `append_pending.py` for the context file if pointer was written
- [ ] Confirm completion; remind user to run `abc adopt` only if a context pointer was queued

---

**Skill Version:** 2.0.0
**Last Updated:** 2026-05-06
