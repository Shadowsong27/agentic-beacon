# Lesson: Complete Test Resolution Before Marking Tasks Done

**Last Updated:** 2026-03-08
**Context:** Agentic Beacon project - TDD workflow enforcement

---

## Context

When implementing tasks with TDD test cases, there's a temptation to mark tasks complete when "most" tests pass. This lesson establishes the standard that ALL tests must be properly resolved before task completion.

## Pattern

**Never mark a task complete until ALL its test cases are resolved through one of these paths:**

1. **Fixed properly** - Test passes with correct implementation
2. **Removed with justification** - Test is no longer valid, with audit trail in tasks.md explaining why
3. **Marked as skipped with explanation** - Test is valid but implementation is deferred, with clear reason documented

## Steps/Implementation

### Before Marking Task Complete

1. **Run all tests for the task**
   ```bash
   pytest tests/core/test_<task_module>.py -v
   ```

2. **For each failing test, choose ONE path:**

   **Path A: Fix the implementation**
   - Understand what the test expects
   - Fix the code to make the test pass
   - Verify the fix doesn't break other tests

   **Path B: Remove invalid test**
   - Justify why the test is no longer valid
   - Document in tasks.md:
     ```markdown
     - [x] Task 1.X Description
       - **Removed test cases:**
         - TC3: Reason this test case is no longer applicable
         - TC7: Explanation of why requirements changed
     ```
   - Remove the test from the test file
   - Leave audit trail in git commit message

   **Path C: Skip with justification**
   - Use `@pytest.mark.skip(reason="...")` 
   - Document in tasks.md:
     ```markdown
     - [x] Task 1.X Description
       - **Skipped test cases:**
         - TC5: Skipped because feature depends on Phase 2 implementation
         - TC8: Skipped - requires external service not available in test env
     ```
   - Ensure reason is clear and specific

3. **Verify 100% resolution**
   - All tests pass, OR
   - All failures are documented with justification

4. **Only then mark task complete**

### Red Flags

❌ **Don't do this:**
- "93% pass rate is good enough"
- "These are just edge cases, we can ignore them"
- "The important tests pass"
- "We'll fix these later"

✅ **Do this instead:**
- Investigate each failure
- Make a conscious decision for each test
- Document your reasoning
- Maintain accountability through audit trails

## Common Mistakes

### Mistake 1: Assuming Edge Cases Don't Matter
**Problem:** Skipping tests for subdirectory lookup or symlink handling because they seem like edge cases.

**Solution:** Either implement proper support OR explicitly document that these scenarios are not supported with clear reasoning in tasks.md.

### Mistake 2: Leaving Tests Failing Without Documentation
**Problem:** Moving on with 4 failing tests without any record of why they're failing or plans to address them.

**Solution:** Add a section in tasks.md for each task documenting test resolution status.

### Mistake 3: Marking Tasks Complete Prematurely
**Problem:** Marking task 1.1-1.6 complete when tests haven't all passed.

**Solution:** Keep tasks unchecked until ALL tests are resolved through one of the three paths.

## Checklist

Before marking a task complete:

- [ ] Run ALL test cases for the task
- [ ] Document pass/fail status for each test case
- [ ] For each failing test, choose: Fix / Remove / Skip
- [ ] Add justification in tasks.md for removed/skipped tests
- [ ] Re-run tests to verify 100% resolution
- [ ] Commit audit trail for any removed tests
- [ ] THEN mark task as complete

## Why This Matters

**Quality:**
- Ensures no silent failures
- Maintains test suite integrity
- Catches bugs early

**Accountability:**
- Clear audit trail of decisions
- Future developers understand intent
- No hidden technical debt

**Discipline:**
- Enforces thoroughness
- Prevents "good enough" mindset
- Maintains TDD rigor

**Team Collaboration:**
- Others can trust completed tasks
- Clear communication of scope
- No surprises later
