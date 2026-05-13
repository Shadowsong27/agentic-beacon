# Commands

This file is the reference for all commands you will need while developing Agentic Beacon — from running tests to building the package to verifying the CLI.

← [Back to CONTRIBUTING.md](../../CONTRIBUTING.md)

---

## Development Commands

### Install / update dependencies

```bash
uv sync --group dev
```

Run this once after cloning, and again after any change to `pyproject.toml` (either at the root or in `libs/beacon/`). This creates or refreshes `.venv` at the repo root with all workspace members and dev dependencies installed.

Never `cd libs/beacon && uv sync` — dependencies are managed from the repo root only.

### Verify the CLI is installed

```bash
.venv/bin/abc --version
```

This should print the current version (e.g. `3.2.0`). Use this after making changes to `cli/` to confirm the entrypoint is wired correctly.

### Run the CLI in development

```bash
uv run abc <command>
# Examples:
uv run abc --help
uv run abc warehouse init test-wh
uv run abc warehouse connect --path ~/test-wh
uv run abc sync
```

`uv run` executes within the managed `.venv` without needing to activate it. You can also activate the venv and use `abc` directly:

```bash
source .venv/bin/activate
abc warehouse init test-wh
```

---

## Testing Commands

### Run unit tests (default, fast)

```bash
uv run pytest -m "not integration" -q
```

This runs all tests **except** those marked `@pytest.mark.integration`. It is the test suite you run during normal development — it completes in seconds and requires no external services.

The `-q` flag (quiet) suppresses verbose output. Omit it for detailed output during debugging.

### Run unit tests from the repo root

Always run `pytest` from the repo root, not from inside `libs/beacon/`. The `testpaths` in the root `pyproject.toml` points to `libs/beacon/tests` and the `asyncio_mode = "auto"` setting applies correctly from there.

```bash
# Correct — from repo root
uv run pytest -m "not integration" -q

# Wrong — don't do this
cd libs/beacon && pytest
```

### Run integration (e2e) tests

```bash
uv run pytest -m integration -v
```

Integration tests (`@pytest.mark.integration`) are end-to-end tests that create real git repositories in `tmp_path`, execute the full CLI via Click's `CliRunner`, and create real symlinks. They are slower (a few minutes for the full suite) and require a configured git identity. They run in CI only on pull requests to `main` (not on every feature branch push).

### Run a specific test file

```bash
uv run pytest libs/beacon/tests/unit/test_architecture.py -v
```

### Run a specific test by name

```bash
uv run pytest -k "test_sync_failure_triggers_rollback" -v
```

### Run tests with coverage

```bash
uv run pytest -m "not integration" --cov=beacon --cov-report=term-missing
```

---

## Linting and Formatting Commands

The project uses [ruff](https://docs.astral.sh/ruff/) for both linting and formatting.

### Lint

```bash
uv run ruff check libs/beacon/src/
```

With auto-fix (fixes safe issues automatically):

```bash
uv run ruff check --fix libs/beacon/src/
```

### Format

```bash
uv run ruff format libs/beacon/src/
```

Check-only (no writes — used in CI):

```bash
uv run ruff format --check libs/beacon/src/
```

### Run pre-commit on all files

```bash
uv run pre-commit run --all-files
```

This runs the full pre-commit suite: trailing whitespace, AST validity, YAML/TOML/JSON syntax, credential detection, debug statement detection, end-of-file fixer, and ruff lint + format.

---

## Documentation Commands

The user-facing documentation site is built with [MkDocs Material](https://squidfunk.github.io/mkdocs-material/).

### Install documentation dependencies

```bash
uv sync --group docs
```

### Serve docs locally (live reload)

```bash
uv run mkdocs serve
```

Opens at `http://127.0.0.1:8000`. Edits to `site-docs/` are reflected immediately.

### Build docs (static output to `site/`)

```bash
uv run mkdocs build --strict
```

The `--strict` flag treats warnings as errors — matching the CI build.

---

## Release Commands

See [Contribution Workflow](contribution-workflow.md) for the full release process. Summary:

```bash
# Trigger an automated release PR (CI bot handles the rest)
git push origin main   # release-please watches main and opens a PR automatically

# After release PR is merged, push the release branch to trigger PyPI publish
git push origin refs/tags/agentic-beacon@vX.X.X:refs/heads/release/vX.X.X
```
