# Fact: CLI Development Workflow

**Last Updated:** 2026-03-10
**Context:** Agentic Beacon Framework - uv workspace

---

## Package Location

`libs/beacon/` — Contains the CLI package source code (uv workspace member)

## Development Setup

```bash
# From repo root — installs agentic-beacon editable + dev tools into root .venv
uv sync --group dev

# Run tests
pytest

# Test CLI
.venv/bin/abc --version
# OR with activated venv:
source .venv/bin/activate
abc --version
abc init test-warehouse

# Build package (for PyPI release, run from libs/beacon)
cd libs/beacon && uv build
```

## uv Workspace Rules

- **Single `.venv` at repo root** — never create a venv inside `libs/beacon/`
- Run `uv sync --group dev` from repo root (NOT `uv sync --extra dev` from `libs/beacon/`)
- `agentic-beacon` is installed as an editable workspace member automatically
- `libs/beacon/pyproject.toml` retains its own `[optional-dependencies] dev` for standalone PyPI installs

## Testing Checklist

Before committing changes:
- [ ] Run `abc --version` - Verify CLI is installed
- [ ] Run `abc init test-warehouse` - Test warehouse generation
- [ ] Run `abc setup --warehouse test-warehouse --all` - Test setup
- [ ] Run `abc list --warehouse test-warehouse` - Test list command
- [ ] Run `pytest` from repo root - All unit tests pass
- [ ] Check all commands complete without errors

## Common Development Tasks

**Add new CLI command:**
1. Edit `libs/beacon/src/beacon/cli.py`
2. Implement command logic
3. Add tests in `libs/beacon/tests/`
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
