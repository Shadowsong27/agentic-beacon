# Lesson: Updating Warehouse Structure

**Last Updated:** 2026-03-07  
**Context:** Agentic Beacon Framework

---

## Context

When `abc init` output changes, multiple files and examples must be updated to stay consistent.

## Pattern

If `abc init` output changes, follow this systematic update process:

## Steps

1. **Update the init logic**
   - File: `libs/beacon/src/beacon/initializer.py`
   - Modify template generation
   - Update directory structure creation
   - Test: `abc init test-warehouse` works correctly

2. **Regenerate example warehouse**
   - Delete: `examples/sample-warehouse/`
   - Regenerate: `cd examples && abc init sample-warehouse ...`
   - Verify structure matches new output

3. **Update documentation**
   - Main `README.md` - Warehouse structure diagram
   - `libs/beacon/README.md` - Command documentation
   - `guides/` - Any affected guides
   - `docs/` - Design docs if structure changed

4. **Test the complete flow**
   ```bash
   # Test init
   abc init test-warehouse --org "Test" --languages python
   
   # Test setup
   cd test-project
   abc setup --warehouse test-warehouse --all
   
   # Verify structure is correct
   ls -la .opencode/
   ```

## Common Changes That Trigger Updates

- Adding/removing directories in warehouse structure
- Changing placeholder file content
- Modifying context file naming
- Updating knowledge organization
- Adding new `abc init` flags

## Checklist

- [ ] `libs/beacon/src/beacon/initializer.py` updated
- [ ] `examples/sample-warehouse/` regenerated
- [ ] Main `README.md` structure diagram updated
- [ ] `libs/beacon/README.md` updated
- [ ] Relevant guides updated
- [ ] `abc init` tested successfully
- [ ] `abc setup` tested with new structure
- [ ] Documentation matches actual output

## Why This Matters

- Example warehouse must match `abc init` output exactly
- Users rely on examples to understand structure
- Documentation must reflect actual behavior
- Inconsistency causes confusion and support issues
