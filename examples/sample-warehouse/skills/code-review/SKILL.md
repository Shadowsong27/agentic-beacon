---
name: code-review
description: Perform a structured code review covering correctness, readability, security, and test coverage
license: MIT
compatibility: opencode, claude-code
---

# Skill: Code Review

---

## Purpose

Guide a thorough, structured code review that covers:
1. Correctness and logic errors
2. Readability and maintainability
3. Security concerns
4. Test coverage gaps
5. Performance considerations

---

## When to Use

- Before merging a pull request
- During pair programming sessions
- After writing a significant feature
- When onboarding to unfamiliar code

---

## Invocation

```
/code-review [file or description]
```

**Examples:**
```
/code-review src/auth/login.py
/code-review the changes I just made to the payment flow
```

---

## Process

### Step 1: Understand the Context

Before reviewing, establish:
- What is this code supposed to do?
- What changed vs. what existed before?
- Are there any known constraints or trade-offs?

### Step 2: Correctness Check

- Does the code do what it claims?
- Are all edge cases handled (null, empty, overflow, concurrent)?
- Is error handling appropriate — not too broad, not too narrow?
- Are all return paths explicit and correct?

### Step 3: Readability Check

- Are names self-documenting?
- Is the code complexity proportional to the problem?
- Would a new team member understand this in 5 minutes?
- Are comments explaining *why*, not *what*?

### Step 4: Security Check

- Is user input validated and sanitized?
- Are secrets hardcoded anywhere?
- Is authentication/authorization enforced at the right layer?
- Are there injection risks (SQL, shell, template)?

### Step 5: Test Coverage Check

- Are happy path and edge cases both tested?
- Do tests assert behavior, not implementation?
- Is there a test for each bug/regression this code fixes?

### Step 6: Performance (if applicable)

- Are there obvious N+1 queries or loops?
- Is expensive work cached or deferred appropriately?
- Are resources (connections, file handles) released?

---

## Output Format

Provide a structured review:

```
## Code Review Summary

### ✅ Looks Good
- [Things done well]

### ⚠️ Suggestions
- [Non-blocking improvements]

### ❌ Issues (requires change)
- [Blocking issues with explanation]

### 🧪 Test Gaps
- [Missing test cases]
```

---

**Skill Version:** 1.0.0
**Last Updated:** 2026-04-17
