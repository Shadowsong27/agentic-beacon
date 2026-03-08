# Lesson: Verify Both Unit Tests and Happy Path Functionality

**Last Updated:** 2026-03-08
**Context:** Agentic Beacon project - TDD workflow validation

---

## Context

After implementing features with TDD (writing tests first, then implementation), it's critical to verify that:
1. Unit tests pass (isolated testing with fixtures)
2. Happy path works (real-world usage without mocks)

Both validations are necessary - unit tests alone don't guarantee the feature works in practice.

## Pattern

### Step 1: Run Unit Tests

```bash
cd libs/beacon
source .venv/bin/activate
uv sync --extra dev
pytest tests/ -v --tb=short
```

**Expected:** All tests pass (or skip with justification)

### Step 2: Test Happy Path

Create a simple script that exercises the real functionality:

```bash
source .venv/bin/activate
python3 -c "
import sys
sys.path.insert(0, 'src')

from beacon.warehouse import WarehouseValidator

# Test with real data
validator = WarehouseValidator()
result = validator.validate('../../examples/sample-warehouse')
print(f'Valid: {result.valid}')
print(f'Errors: {result.errors}')
"
```

**Expected:** Feature works end-to-end without import errors or unexpected failures

## Why Both Are Needed

**Unit Tests:**
- ✅ Test edge cases exhaustively
- ✅ Test error conditions
- ✅ Fast feedback loop
- ❌ May not catch integration issues
- ❌ May not catch import problems

**Happy Path:**
- ✅ Validates real-world usage
- ✅ Catches import/dependency issues
- ✅ Confirms feature actually works
- ❌ Doesn't test edge cases
- ❌ Not exhaustive

## Common Issues Caught by Happy Path

1. **Import errors:** Module not found, circular imports
2. **Virtual environment issues:** Dependencies not installed
3. **Path problems:** Incorrect sys.path or relative imports
4. **Real data validation:** Works with actual files/structures
5. **Integration issues:** Components work together correctly

## Checklist

Before marking a phase complete:

- [ ] All unit tests pass
- [ ] Happy path test script runs successfully
- [ ] No import errors when importing the module
- [ ] Feature works with real data (not just test fixtures)
- [ ] Error cases produce expected error messages
- [ ] Path resolution works correctly (tilde, relative, absolute)

## Example: Warehouse Validator

**Unit Tests (78 passing):**
```bash
pytest tests/ -v
# ======================== 78 passed, 2 skipped =========================
```

**Happy Path Test:**
```python
from beacon.warehouse import WarehouseValidator

validator = WarehouseValidator()

# Test 1: Valid warehouse
result = validator.validate('examples/sample-warehouse')
assert result.valid is True

# Test 2: Invalid warehouse
result = validator.validate('/tmp/empty')
assert result.valid is False
assert len(result.errors) > 0

# Test 3: Path resolution
resolved = validator.resolve_path('~/warehouse')
assert str(resolved).startswith('/Users/')
```

**Output:**
```
✅ Sample warehouse is valid!
✅ Empty directory: 7 validation errors
✅ Path resolution works correctly
```

## Integration with TDD

This lesson complements the TDD workflow:

1. **🔴 RED:** Write failing tests
2. **🟢 GREEN:** Implement to pass tests
3. **🔵 REFACTOR:** Improve code quality
4. **✅ VERIFY:** Run happy path test (this lesson)

The fourth step ensures the feature actually works beyond passing tests.

## Anti-Patterns to Avoid

❌ **Don't skip happy path testing:**
- "Tests pass, we're done"
- Assumption that passing tests = working feature

❌ **Don't rely only on happy path:**
- "It works for me, no need for tests"
- Missing edge cases and error conditions

✅ **Do both:**
- Comprehensive unit tests for coverage
- Happy path validation for confidence

## When to Run Happy Path Tests

**Always run after:**
- Completing a phase
- Major refactoring
- Package reorganization
- Dependency changes
- Before committing

**Include in:**
- CI/CD pipeline
- Pre-commit hooks
- Code review checklist
- Release verification
