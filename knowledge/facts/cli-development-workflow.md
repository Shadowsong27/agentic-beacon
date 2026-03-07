# Fact: CLI Development Workflow

**Last Updated:** 2026-03-07  
**Context:** Agentic Beacon Framework

---

## Package Location

`libs/beacon/` - Contains the CLI package source code

## Development Setup

```bash
# Install in editable mode
cd libs/beacon
pip install -e .

# Run tests
pytest

# Build package
uv build

# Test locally before release
abc --version
abc init test-warehouse
```

## Testing Checklist

Before committing changes:
- [ ] Run `abc --version` - Verify CLI is installed
- [ ] Run `abc init test-warehouse` - Test warehouse generation
- [ ] Run `abc setup --warehouse test-warehouse --all` - Test setup
- [ ] Run `abc list --warehouse test-warehouse` - Test list command
- [ ] Check all commands complete without errors

## Common Development Tasks

**Add new CLI command:**
1. Edit `libs/beacon/src/beacon/cli.py`
2. Implement command logic
3. Add tests
4. Update documentation

**Modify warehouse structure:**
1. Edit `libs/beacon/src/beacon/initializer.py`
2. Regenerate `examples/sample-warehouse/`
3. Update docs
4. Test with `abc init` and `abc setup`

## Package Information

- **Package name:** `agentic-beacon` (PyPI distribution name)
- **CLI command:** `abc`
- **Import name:** `beacon`
- **Python required:** `>=3.12`
- **Build tool:** `uv`
