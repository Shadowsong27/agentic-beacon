# Contributing to Agentic Beacon

Welcome to Agentic Beacon — the package manager for AI coding agents. This guide covers everything you need to go from zero to a merged pull request: environment setup, the project's architecture and conventions, how to run tests, and the contribution workflow.

## Project Overview

**Agentic Beacon** is a Python CLI tool (published as `agentic-beacon` on PyPI, invoked as `abc`) that solves "context drift" — the problem that arises when multiple projects each maintain their own `AGENTS.md` or `CLAUDE.md` files independently, causing agent instructions to diverge over time. Agentic Beacon introduces a **warehouse** model: a single git repository that is the source of truth for shared agent artifacts (contexts, knowledge, skills, agents). Projects connect to the warehouse and receive artifacts as per-file symlinks rather than copies. Edits flow back through those symlinks into the warehouse working tree; `abc warehouse contribute` pushes them upstream to the team.

The primary consumers of this project are software engineering teams that use AI coding assistants (Claude Code, OpenCode, or compatible tools) across multiple repositories. The CLI is the sole public interface; there is no HTTP API, no library API surface, and no frontend.

The project is pure Python (requires Python 3.12+) and is distributed as a standard PyPI wheel. It uses [uv](https://github.com/astral-sh/uv) as its package and workspace manager. The package is structured as a [uv workspace](https://docs.astral.sh/uv/concepts/workspaces/) with the single workspace member at `libs/beacon/`. The entrypoint registered in `pyproject.toml` is `abc = "beacon.cli.main:main"`.

Key runtime dependencies are [Click](https://click.palletsprojects.com/) (CLI framework), [Rich](https://rich.readthedocs.io/) (terminal formatting), [Textual](https://textual.textualize.io/) (TUI for `abc adopt`), [Pydantic](https://docs.pydantic.dev/) and [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) (data models and settings), [PyYAML](https://pyyaml.org/) (YAML I/O), and [Loguru](https://loguru.readthedocs.io/) (structured logging).

**Platform support:** macOS and Linux only. Windows is explicitly rejected at startup via `utils/platform.py`. The rejection reason is symlink-based artifact sync, which is not reliably supported on Windows.

## Environment Setup

### 1. Install Python 3.12+

The project requires Python 3.12 or newer. If you do not have it, install via [pyenv](https://github.com/pyenv/pyenv) (recommended) or your system package manager:

```bash
# macOS with Homebrew
brew install python@3.12

# Or via pyenv
pyenv install 3.12
pyenv global 3.12
```

### 2. Install uv

[uv](https://docs.astral.sh/uv/) is the package manager for this project. It manages the virtual environment, resolves dependencies, and runs tools.

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
# or via Homebrew
brew install uv
```

Verify: `uv --version` should print `0.5.x` or newer.

### 3. Clone and install dependencies

```bash
git clone https://github.com/Shadowsong27/agentic-beacon.git
cd agentic-beacon

# Creates .venv at the repo root and installs all workspace members + dev tools
uv sync --group dev
```

The `--group dev` flag installs test and linting dependencies (`pytest`, `pytest-cov`, `pytest-asyncio`, `pre-commit`, `ruff`). Run this once, and again any time `pyproject.toml` changes.

**Important:** Never run `uv sync` inside `libs/beacon/` and never create a separate virtualenv there. The workspace is managed from the repo root; the single `.venv` at the root is shared across all workspace members.

### 4. Install pre-commit hooks

```bash
uv run pre-commit install
```

This wires the pre-commit hooks (ruff lint, ruff format, YAML/TOML/JSON syntax checks, credential detection) to run automatically on every `git commit`.

### 5. Configure git identity

Some tests run real `git` subprocess commands and require a configured git identity. If you do not have a global git config, set one:

```bash
git config --global user.email "you@example.com"
git config --global user.name "Your Name"
```

### 6. Verify the setup

```bash
# Should print the installed version (e.g. 3.2.0)
.venv/bin/abc --version

# Run the unit test suite — all should pass
uv run pytest -m "not integration" -q
```

### Environment Variables

The CLI reads a small set of optional environment variables via `pydantic-settings`. All are optional with sensible defaults:

| Variable | Type | Default | Description |
|---|---|---|---|
| `ABC_GLOBAL_AGENTS_DIR` | `Path` | `~/.abc/agents` | Override the global agents directory used for agent symlink installation |
| `ABC_MAX_COMMITS_LOOKBACK` | `int` | `100` | Maximum number of git commits to scan when annotating warehouse artifacts with recency |
| `ABC_DEBUG` | `bool` | `false` | Enable debug-level logging output |

These are rarely needed in normal development. The most common override is `ABC_MAX_COMMITS_LOOKBACK` if you have a very deep git history in a test warehouse.

## Documentation

- [Commands](docs/contributing/commands.md) — build, run, test, and lint commands
- [Project Layout](docs/contributing/project-layout.md) — annotated directory tree and organization
- [Architecture](docs/contributing/architecture.md) — four-layer design, subsystem boundaries, data flows
- [Configuration System](docs/contributing/configuration.md) — settings, workspace config, manifest models
- [Local Development](docs/contributing/local-development.md) — dev loop, debugging, running subsets
- [Code Style & Conventions](docs/contributing/code-style.md) — naming, imports, formatting rules
- [Design Patterns & Techniques](docs/contributing/design-patterns.md) — recurring patterns and when to use them
- [Testing Strategy](docs/contributing/testing.md) — test layout, runners, unit vs integration, fixtures
- [Contribution Workflow](docs/contributing/contribution-workflow.md) — branches, PRs, CI gates, release process
- [Documentation Maintenance](docs/contributing/documentation.md) — how docs are built and published
- [Gotchas & Sharp Edges](docs/contributing/gotchas.md) — known traps, architecture debt, sharp corners
- [Open Questions](docs/contributing/open-questions.md) — unresolved items for future documentation updates
