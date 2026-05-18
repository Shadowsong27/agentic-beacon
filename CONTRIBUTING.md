# Contributing to Agentic Beacon

Welcome — this file is the entry point for new contributors. It covers everything you need to go from a fresh clone to running tests locally. The deeper reference material (architecture, code style, testing strategy, design patterns, gotchas, etc.) is in `docs/contributing/` and is primarily there so AI coding agents working in the repo have something to grep. Human contributors generally won't need to read them end-to-end.

---

## Project Overview

**Agentic Beacon** is a Python CLI tool (published as `agentic-beacon` on PyPI, invoked as `abc`) that solves "context drift" — the problem that arises when multiple projects each maintain their own `AGENTS.md` or `CLAUDE.md` files independently, causing agent instructions to diverge over time. Agentic Beacon introduces a **warehouse** model: a single git repository that is the source of truth for shared agent artifacts (contexts, knowledge, skills, agents). Projects connect to the warehouse and receive artifacts as per-file symlinks rather than copies. Edits flow back through those symlinks into the warehouse working tree; `abc warehouse contribute` pushes them upstream to the team.

The primary consumers of this project are software engineering teams that use AI coding assistants (Claude Code, OpenCode, or compatible tools) across multiple repositories. The CLI is the sole public interface; there is no HTTP API, no library API surface, and no frontend.

The project is pure Python (requires Python 3.12+) and is distributed as a standard PyPI wheel. It uses [uv](https://github.com/astral-sh/uv) as its package and workspace manager — the package is structured as a [uv workspace](https://docs.astral.sh/uv/concepts/workspaces/) with a single workspace member at `libs/beacon/`. The entrypoint registered in `pyproject.toml` is `abc = "beacon.cli.main:main"`.

**Platform support:** macOS and Linux only. Windows is explicitly rejected at startup because symlink-based artifact sync is not reliably supported there.

---

## Environment Setup

### 1. Install Python 3.12+

```bash
# macOS with Homebrew
brew install python@3.12

# Or via pyenv
pyenv install 3.12
pyenv global 3.12
```

### 2. Install uv

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

> **Important:** never run `uv sync` inside `libs/beacon/`, and never create a separate virtualenv there. The workspace is managed from the repo root; the single `.venv` at the root is shared across all workspace members.

### 4. Install pre-commit hooks

```bash
uv run pre-commit install
```

This wires the pre-commit hooks (ruff lint, ruff format, YAML/TOML/JSON syntax checks, credential detection) to run automatically on every `git commit`.

### 5. Configure git identity

Some tests run real `git` subprocess commands and require a configured git identity:

```bash
git config --global user.email "you@example.com"
git config --global user.name "Your Name"
```

### 6. Verify the setup

```bash
.venv/bin/abc --version
uv run pytest -m "not integration" -q
```

### Environment variables

The CLI reads a small set of optional environment variables via `pydantic-settings`. All are optional with sensible defaults:

| Variable | Type | Default | Description |
|---|---|---|---|
| `ABC_GLOBAL_AGENTS_DIR` | `Path` | `~/.abc/agents` | Override the global agents directory used for agent symlink installation |
| `ABC_MAX_COMMITS_LOOKBACK` | `int` | `100` | Maximum number of git commits to scan when annotating warehouse artifacts with recency |
| `ABC_DEBUG` | `bool` | `false` | Enable debug-level logging output |
| `BEACON_OFFLINE` | `bool` | `false` | Skip integration tests that require the package index (planes, flaky networks) |

These are rarely needed in normal development.

---

## Where to Go Next

The deep reference lives in `docs/contributing/`. These files are primarily written for AI coding agents working in the repo — the most efficient way to use them is to point your agent at the directory ("read `docs/contributing/`") and let it pick what's relevant.

| File | Covers |
|---|---|
| [`commands.md`](docs/contributing/commands.md) | Build, run, test, and lint commands |
| [`project-layout.md`](docs/contributing/project-layout.md) | Annotated directory tree |
| [`architecture.md`](docs/contributing/architecture.md) | Four-layer design, five domains, data flows |
| [`configuration.md`](docs/contributing/configuration.md) | Settings, workspace config, manifest models |
| [`local-development.md`](docs/contributing/local-development.md) | Dev loop, debugging, running subsets |
| [`code-style.md`](docs/contributing/code-style.md) | Naming, imports, formatting rules |
| [`design-patterns.md`](docs/contributing/design-patterns.md) | Recurring patterns and when to use them |
| [`testing.md`](docs/contributing/testing.md) | Test layout, unit vs integration, fixtures |
| [`contribution-workflow.md`](docs/contributing/contribution-workflow.md) | Branches, PRs, CI gates, release process |
| [`documentation.md`](docs/contributing/documentation.md) | How docs are built and published |
| [`gotchas.md`](docs/contributing/gotchas.md) | Known traps and sharp corners |
| [`open-questions.md`](docs/contributing/open-questions.md) | Unresolved items |
