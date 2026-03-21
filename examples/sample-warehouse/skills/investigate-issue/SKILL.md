---
name: investigate-issue
description: Investigate a GitHub issue by fetching its details, locating relevant code, and explaining the root cause without making any changes
license: MIT
compatibility: opencode
---

# Skill: Investigate Issue

---

## Purpose

Systematically investigate a GitHub issue by:
1. Fetching issue details from GitHub
2. Locating relevant code in the codebase
3. Tracing the root cause through the code
4. Explaining the problem clearly — without fixing it

---

## When to Use

- Before starting work on a bug or feature issue
- When a stakeholder wants to understand what's broken and why
- When triaging or estimating effort for an issue
- When you want to explain an issue to a teammate

---

## Invocation

```
/investigate-issue <issue-number>
```

**Example:**
```
/investigate-issue 64
```

---

## Process

### Step 1: Fetch the Issue

Run:
```bash
gh issue view <issue-number> --repo <owner>/<repo>
```

If the repo cannot be inferred from context (e.g. no `gh` remote configured), ask the user for the full `owner/repo` slug before proceeding.

Extract from the issue:
- **Title** — the one-line description of the problem
- **Problem statement** — what behavior is observed
- **Expected behavior** — what should happen instead
- **Notes / hints** — any implementation hints the author included

### Step 2: Locate Relevant Code

Based on the issue content, search the codebase for the affected area:

- Use **Grep** to find functions, classes, or strings mentioned in the issue
- Use **Glob** to find candidate files by name or path pattern
- Use **Read** to read relevant sections in full

Focus on:
- The code path that produces the observed behavior
- The data structures or return values involved
- Any conditional logic that gates the correct behavior

### Step 3: Trace the Root Cause

Follow the call chain from the CLI entry point (or API surface) down to where the behavior diverges from what's expected. Identify:

- **Where** in the code the issue originates (file + line)
- **Why** the current code behaves this way (logic, missing branch, wrong condition, etc.)
- **What** data or state is available at that point (and what is missing)

### Step 4: Present the Investigation

Structure your response as follows:

```
## Issue Summary
[One-paragraph description of the problem in plain language]

## Root Cause
[Precise explanation of what the code does and why it causes the issue.
Reference specific files and line numbers.]

## Code Walkthrough
[Trace the relevant code path, quoting key lines with file:line references]

## Gap
[Describe exactly what is missing or wrong — the delta between current and correct behavior]

## Fix Direction (no code)
[High-level description of what would need to change to resolve the issue,
without writing any implementation]
```

Do **not** write any fix code or make any file edits. Investigation only.

---

## Examples

### Example 1

**User:**
```
/investigate-issue 64
```

**Agent:**
1. Runs `gh issue view 64 --repo <owner>/<repo>`
2. Reads the issue: sync error count shown but not which files failed
3. Greps for `SyncSummary`, `log_fn`, `Errors:` in the codebase
4. Reads `sync.py` and `cli.py` to trace the call path
5. Identifies that `log_fn=None` is passed in non-verbose mode, silencing per-file error messages
6. Presents structured investigation output with file:line references

---

## Important Notes

- **Read before concluding** — always read the full relevant code section, not just grep hits
- **Cite line numbers** — every claim about code behavior should reference `file:line`
- **No fixes** — this skill is for understanding, not implementation
- **Follow hints** — if the issue author included implementation notes, validate them against the code
- **One issue at a time** — investigate the specified issue only, don't expand scope

---

## Checklist for Agent

When executing this skill:

- [ ] Fetch the issue with `gh issue view`
- [ ] Extract problem, expected behavior, and any author hints
- [ ] Grep/Glob for relevant code using terms from the issue
- [ ] Read the relevant files in full (not just grep snippets)
- [ ] Trace the call path from entry point to root cause
- [ ] Identify the exact file and line where the behavior diverges
- [ ] Present structured output: Summary → Root Cause → Code Walkthrough → Gap → Fix Direction
- [ ] Make no code changes

---

**Skill Version:** 1.0.0
**Last Updated:** 2026-03-21
