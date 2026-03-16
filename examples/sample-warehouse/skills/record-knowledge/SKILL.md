---
name: record-knowledge
description: Systematically capture decisions, lessons, and facts into the project knowledge base with automatic categorization and context updates
license: MIT
compatibility: opencode
---

# Skill: Record Knowledge

---

## Purpose

Streamline the process of recording knowledge by:
1. Analyzing context to determine knowledge type (decision/lesson/fact)
2. Creating properly formatted atomic knowledge files
3. Updating context files with pointers to new knowledge

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

### Step 2: Create Knowledge File

**File naming:**
- Use kebab-case
- Be descriptive but concise
- Example: `use-pydantic-for-data-carriers.md`

**File location (on disk in an Agentic Beacon project):**
- Decisions: `.agentic-beacon/artifacts/knowledge/decisions/<name>.md`
- Lessons: `.agentic-beacon/artifacts/knowledge/lessons/<name>.md`
- Facts: `.agentic-beacon/artifacts/knowledge/facts/<name>.md`

**Warehouse-relative reference (for context pointers):**
- `knowledge/decisions/<name>.md`
- `knowledge/lessons/<name>.md`
- `knowledge/facts/<name>.md`

**File format:**

**For Decisions:**
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

**For Lessons:**
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

**For Facts:**
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

### Step 3: Ask User for Context File

First, infer the most likely context file from the current session:
- If an `AGENTS.md` (or similar context file) is already loaded in the session, default to that file
- If multiple context files are loaded, prefer the most specific one (project-level over global)
- If none can be inferred, fall back to `AGENTS.md`

**Question to user:**
```
Where should I add a pointer to this knowledge?

Options:
1. [Inferred file from current context] (default)
2. Skip - don't add to any context file yet
3. Custom path - specify another file

Default: [inferred file, or AGENTS.md if none detected]
```

### Step 4: Update Context File

If user chooses a context file, add a pointer in the appropriate section:

**Format:**
```markdown
**Brief:** [One-sentence summary]

**Read:** [Relative path to knowledge file]
```

**Example in AGENTS.md:**
```markdown
### Data Modeling

**Brief:** Use Pydantic BaseModel for all data carriers to get automatic validation.

**Read:** [Decision: Use Pydantic for Data Carriers](knowledge/decisions/use-pydantic-for-data-carriers.md)
```

### Step 5: Confirm Completion

Report to user:
```
✅ Knowledge recorded successfully!

Type: [Decision|Lesson|Fact]
File: .agentic-beacon/artifacts/knowledge/[type]/[filename].md
Context updated: [Yes - AGENTS.md | No | Custom file]

You can now reference this knowledge with:
**Read:** [knowledge/[type]/[filename].md]
```

---

## Examples

### Example 1: Recording a Decision

**User:**
```
/record-knowledge We decided not to commit temporary handoff docs because they clutter the repo and duplicate proper documentation
```

**Agent:**
1. Analyzes: This is a **decision** (key phrase: "decided not to")
2. Creates: `.agentic-beacon/artifacts/knowledge/decisions/no-temporary-docs.md`
3. Asks: "Where should I add a pointer?" → User: "AGENTS.md"
4. Updates: Adds pointer in AGENTS.md under "Development Guidelines"
5. Confirms: "✅ Knowledge recorded successfully!"

### Example 2: Recording a Lesson

**User:**
```
/record-knowledge When updating warehouse structure, always regenerate examples/sample-warehouse to keep it in sync
```

**Agent:**
1. Analyzes: This is a **lesson** (key phrase: "always", pattern description)
2. Creates: `.agentic-beacon/artifacts/knowledge/lessons/updating-warehouse-structure.md`
3. Asks: "Where should I add a pointer?" → User: "AGENTS.md"
4. Updates: Adds pointer in AGENTS.md under "Common Patterns"
5. Confirms: "✅ Knowledge recorded successfully!"

### Example 3: Recording a Fact

**User:**
```
/record-knowledge The CLI package is located in libs/beacon/ and uses uv for building
```

**Agent:**
1. Analyzes: This is a **fact** (key phrase: "is located", descriptive)
2. Creates: `.agentic-beacon/artifacts/knowledge/facts/cli-development-workflow.md`
3. Asks: "Where should I add a pointer?" → User: "Skip"
4. Skips context update
5. Confirms: "✅ Knowledge recorded successfully! (No context update)"

---

## Important Notes

- **Analyze carefully** - Read the full context to determine type
- **Use proper formatting** - Follow the templates exactly
- **Be atomic** - One knowledge item per file
- **Always ask** - Don't assume which context file to update
- **Default to AGENTS.md** - Most common choice for project knowledge
- **Date everything** - Use current date in YYYY-MM-DD format

---

## Checklist for Agent

When executing this skill:

- [ ] Read user's knowledge description carefully
- [ ] Analyze and determine type (decision/lesson/fact)
- [ ] Choose appropriate filename (kebab-case)
- [ ] Create file in correct location
- [ ] Use correct template format
- [ ] Fill in all required sections
- [ ] Ask user where to add pointer
- [ ] Update context file if requested
- [ ] Confirm completion with summary

---

**Skill Version:** 1.0.0
**Last Updated:** 2026-03-07
