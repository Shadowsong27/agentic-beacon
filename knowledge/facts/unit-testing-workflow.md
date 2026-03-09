# Fact: Unit Testing Workflow

**Last Updated:** 2026-03-10
**Context:** Agentic Beacon project - uv workspace testing

---

## Overview

The project uses a **uv workspace** with a single `.venv` at the repo root. `libs/beacon` is a workspace member — no separate venv is created there.

## Details

**Required steps for running tests:**

1. **Sync dependencies (one-time / after dependency changes)**
   ```bash
   uv sync --group dev
   ```
   Creates/updates `.venv` at repo root with `agentic-beacon` (editable from workspace) and all dev tools.

2. **Run pytest from repo root**
   ```bash
   pytest
   ```
   pytest is configured in root `pyproject.toml` (`testpaths = ["libs/beacon/tests"]`).

   Or activate the venv first:
   ```bash
   source .venv/bin/activate
   pytest
   ```

## Full Command Sequence

```bash
# From repo root
uv sync --group dev
pytest -v --tb=short
```

## Common pytest Flags

- `-v` - Verbose output
- `--tb=short` - Short traceback format
- `-k <pattern>` - Run tests matching pattern
- `-x` - Stop on first failure
- `--cov` - Generate coverage report

## Workspace Structure

- Root `pyproject.toml` — workspace definition, dev dependency group, pytest config
- `libs/beacon/pyproject.toml` — workspace member (publishable package)
- `.venv/` — single root venv (DO NOT create venvs inside `libs/beacon/`)

## Important Notes

- Always run from the **repo root**, not from `libs/beacon/`
- `uv sync --group dev` replaces the old `uv sync --extra dev` workflow
- No `cd libs/beacon` required anymore
- The `libs/beacon/pyproject.toml` retains `[optional-dependencies] dev` for standalone PyPI installs only
