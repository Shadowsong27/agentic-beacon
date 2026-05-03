---
name: generate-tests
description: Generate comprehensive unit and integration tests for a given function, module, or feature
license: MIT
compatibility: opencode, claude-code
---

# Skill: Generate Tests

---

## Purpose

Generate well-structured, meaningful tests that:
1. Cover the happy path and critical edge cases
2. Follow the project's existing test style and framework
3. Assert behavior, not implementation details
4. Are easy to read and maintain

---

## When to Use

- After writing new functions or modules
- When increasing coverage on untested legacy code
- When a bug is fixed — add a regression test
- During TDD — write tests before implementation

---

## Invocation

```
/generate-tests [function, file, or description]
```

**Examples:**
```
/generate-tests parse_date() in utils/dates.py
/generate-tests the checkout flow in cart.py
/generate-tests add regression test for the null user bug
```

---

## Process

### Step 1: Analyze What Needs Testing

- Identify the function/class signature and return type
- List all code paths (conditionals, loops, error branches)
- Identify external dependencies (DB, API, filesystem) that need mocking
- Note any existing tests to match the style

### Step 2: Identify Test Cases

For each unit of behavior, generate cases for:

| Category | What to test |
|----------|-------------|
| Happy path | Normal input, expected output |
| Edge cases | Empty, null, zero, max values |
| Error cases | Invalid input, missing required fields |
| Boundary | Off-by-one, type boundaries |
| Concurrent | Race conditions (if applicable) |

### Step 3: Write Tests

Follow the project's test framework (pytest, unittest, jest, etc.).

**Test naming convention:** `test_<function>_<scenario>`

**Structure (AAA pattern):**
```python
def test_parse_date_returns_datetime_for_valid_iso_string():
    # Arrange
    date_str = "2026-01-15"

    # Act
    result = parse_date(date_str)

    # Assert
    assert result == datetime(2026, 1, 15)
```

### Step 4: Mock at System Boundaries Only

- Mock external I/O (HTTP calls, DB queries, file reads)
- Do NOT mock internal code — test the real behavior
- Use fixtures for shared setup, not class-level state

### Step 5: Verify Tests Are Meaningful

Before presenting, check:
- [ ] Each test can fail independently
- [ ] Tests don't depend on each other's order
- [ ] Assertions are specific, not just `assert result is not None`
- [ ] Test names describe what failure means

---

## Output Format

Present tests as a complete, runnable file:

```python
# tests/test_<module>.py

import pytest
from <module> import <function>


class Test<Function>:
    def test_happy_path(self):
        ...

    def test_edge_case_empty_input(self):
        ...

    def test_raises_on_invalid_input(self):
        with pytest.raises(ValueError):
            ...
```

---

**Skill Version:** 1.0.0
**Last Updated:** 2026-04-17
