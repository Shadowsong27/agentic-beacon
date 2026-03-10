# Lesson: Adding a New CLI Command

**Last Updated:** 2026-03-07
**Context:** Agentic Beacon Framework

---

## Pattern

Follow this systematic approach when adding new CLI commands to maintain consistency and completeness.

## Steps

1. **Add command handler** in `libs/beacon/src/beacon/cli.py`
   - Use `@click.command()` decorator
   - Define arguments and options
   - Add help text

2. **Implement logic** in appropriate module
   - Core logic goes in separate module (not in cli.py)
   - Keep CLI handler thin (just argument parsing and calling logic)

3. **Add tests**
   - Unit tests for core logic
   - Integration tests for CLI command
   - Test error cases

4. **Update `libs/beacon/README.md`**
   - Add command to command table
   - Document all arguments and options
   - Provide usage examples

5. **Update main `README.md`** (if major feature)
   - Add to feature list if significant
   - Update quick start if affects onboarding

6. **Test thoroughly**
   ```bash
   abc <command> --help
   abc <command> <test-args>
   # Test error cases
   # Test edge cases
   ```

## Example Structure

```python
# In cli.py
@click.command()
@click.argument('warehouse_path')
@click.option('--all', is_flag=True, help='Install all content')
def setup(warehouse_path: str, all: bool):
    """Install warehouse content to project."""
    from beacon.setup import SetupService
    service = SetupService(warehouse_path)
    service.run(install_all=all)
```

## Common Mistakes

- **Mistake:** Putting all logic in cli.py
  - **Fix:** Extract to separate service/module

- **Mistake:** Forgetting to update documentation
  - **Fix:** Always update both README files

- **Mistake:** Not testing edge cases
  - **Fix:** Test with invalid inputs, missing files, etc.

## Checklist

- [ ] Command handler added in cli.py
- [ ] Core logic in separate module
- [ ] Tests written and passing
- [ ] `libs/beacon/README.md` updated
- [ ] Main `README.md` updated (if needed)
- [ ] `abc <command> --help` shows correct info
- [ ] Command works as expected
- [ ] Error cases handled gracefully
