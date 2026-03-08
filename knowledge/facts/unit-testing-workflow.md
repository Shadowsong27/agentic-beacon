# Fact: Unit Testing Workflow

**Last Updated:** 2026-03-08
**Context:** Agentic Beacon project - libs/beacon/ package testing

---

## Overview

Standard workflow for running unit tests in the beacon package using UV and pytest.

## Details

The beacon package uses UV for dependency management and pytest for unit testing. Tests are located in the `tests/` directory within the package.

**Required steps for running tests:**

1. **Activate virtual environment**
   ```bash
   source .venv/bin/activate
   ```

2. **Install dev dependencies with UV**
   ```bash
   uv sync --extra dev
   ```
   This ensures pytest and other testing tools are installed.

3. **Run pytest**
   ```bash
   pytest tests/core/ -v --tb=short
   ```
   Adjust the path and flags as needed for specific test suites.

## Usage/Application

**Full command sequence:**
```bash
cd /Users/shadowsong/Code/agentic-beacon/libs/beacon
source .venv/bin/activate
uv sync --extra dev
pytest tests/core/ -v --tb=short
```

**Common pytest flags:**
- `-v` - Verbose output
- `--tb=short` - Short traceback format
- `-k <pattern>` - Run tests matching pattern
- `-x` - Stop on first failure
- `--cov` - Generate coverage report

**Test organization:**
- `tests/` - Root test directory
- `tests/core/` - Core module tests
- `tests/conftest.py` - Shared fixtures

## Important Notes

- Always activate the virtual environment before running tests
- Use `uv sync --extra dev` instead of `pip install -e ".[dev]"` in UV workspaces
- The virtual environment must exist before activation (create with `uv venv` if needed)
- Tests follow TDD principles: write tests first (RED), implement code (GREEN), refactor (REFACTOR)
