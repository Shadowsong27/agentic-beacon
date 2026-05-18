# Local Development

This file covers the day-to-day development loop for Agentic Beacon — how to iterate on changes, debug issues, and test specific parts of the system.

---

## Inner Dev Loop

The typical inner loop for working on a feature or bug fix:

```bash
# 1. Make changes to source in libs/beacon/src/beacon/
# 2. Run the unit tests for the affected area
uv run pytest libs/beacon/tests/unit/domains/distribution/ -v

# 3. Verify the CLI entrypoint still works
uv run abc --help
uv run abc warehouse init test-wh   # smoke test

# 4. Run the full unit suite before committing
uv run pytest -m "not integration" -q

# 5. Commit — pre-commit runs ruff lint + format automatically
git commit -m "fix: ..."
```

There is no dev server to restart — `uv run abc` always picks up the latest source from the installed editable `.venv`. Changes to Python source files are reflected immediately on the next `uv run abc` invocation.

---

## Testing Against a Real Warehouse

To test CLI commands end-to-end with a real warehouse, create a throw-away warehouse and project:

```bash
# Create a test warehouse
uv run abc warehouse init /tmp/test-warehouse
cd /tmp/test-warehouse
git add . && git commit -m "init"

# Connect a test project
mkdir /tmp/test-project && cd /tmp/test-project
git init && git commit --allow-empty -m "init"
uv run abc warehouse connect --path /tmp/test-warehouse
uv run abc sync
uv run abc warehouse status
```

Clean up when done:

```bash
rm -rf /tmp/test-warehouse /tmp/test-project
```

---

## Running Specific Test Subsets

Run tests for a specific domain:
```bash
uv run pytest libs/beacon/tests/unit/domains/adoption/ -v
```

Run a single test by name:
```bash
uv run pytest -k "test_sync_failure_triggers_rollback" -v
```

Run tests matching a module:
```bash
uv run pytest libs/beacon/tests/unit/core/test_sync_engine_symlinks.py -v
```

Run integration tests (slower, creates real git repos):
```bash
uv run pytest -m integration -v
```

Run just the architecture enforcement test:
```bash
uv run pytest libs/beacon/tests/unit/test_architecture.py -v
```

---

## Debugging

### Enable debug logging

Set `ABC_DEBUG=true` to enable `DEBUG`-level loguru output on stderr:

```bash
ABC_DEBUG=true uv run abc sync
```

This shows git subprocess calls, symlink operations, and internal state transitions.

### Use `--verbose` flag

```bash
uv run abc --verbose sync
```

`--verbose` switches the loguru stderr sink from `INFO` to `DEBUG`. Equivalent to `ABC_DEBUG=true` but without the environment variable.

### Interactive debugger

Use `breakpoint()` (Python 3.7+ built-in) anywhere in source code. The pre-commit hook will catch `breakpoint()` calls and prevent committing them, so remember to remove them before committing.

```python
# In any source file temporarily
def some_function():
    breakpoint()  # drops into pdb on next invocation
    ...
```

### Inspect manifest files

During development, inspect the yaml files that commands read and write:

```bash
cat .agentic-beacon/config.toml       # warehouse connection
cat beacon.yaml                       # adopted artifacts
cat .agentic-beacon/pending.yaml      # pending (unattached) artifacts
```

---

## Working on the TUI (`abc adopt`)

The `abc adopt` TUI uses [Textual](https://textual.textualize.io/). Textual has its own development tooling:

```bash
# Run the Textual devtools (live CSS reloading, DOM inspector)
uv run textual run --dev beacon.domains.adoption.tui
```

In unit tests, the TUI is bypassed entirely — `commit_session` is tested with injectable no-op callables rather than running the actual Textual app. Integration tests replace `AdoptApp` with a `monkeypatch.setattr` mock that returns a predetermined `AdoptResult`.

---

## Pre-commit Hooks

The pre-commit suite runs automatically on `git commit`. To run it manually:

```bash
uv run pre-commit run --all-files
```

Hooks include:
- `ruff check --fix` — lint and auto-fix safe issues
- `ruff format` — format Python files
- `check-ast` — verify all Python files parse as valid AST
- `check-yaml`, `check-toml`, `check-json` — syntax validation
- `detect-aws-credentials` — credential scanning
- `debug-statements` — catch forgotten `breakpoint()` or `pdb` calls
- `trailing-whitespace`, `end-of-file-fixer`, `mixed-line-ending`

If a hook modifies files (e.g. ruff auto-fixes a lint issue), the commit is aborted and the modified files are staged for review. Re-run `git commit` after reviewing the changes.
