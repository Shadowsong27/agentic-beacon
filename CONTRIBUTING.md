# Contributing to Agentic Beacon

Welcome — this file is the entry point for new contributors. It covers everything you need to go from a fresh clone to running tests locally. The deeper guides (architecture, code style, testing strategy, design patterns, gotchas, etc.) live on the documentation site:

📚 **<https://shadowsong27.github.io/agentic-beacon/contributing/>**

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

The rest of the contributor reference is on the documentation site. Bookmark the [Contributing section](https://shadowsong27.github.io/agentic-beacon/contributing/) and dip in by topic:

- [Commands](https://shadowsong27.github.io/agentic-beacon/contributing/commands/) — build, run, test, and lint commands
- [Project Layout](https://shadowsong27.github.io/agentic-beacon/contributing/project-layout/) — annotated directory tree
- [Architecture](https://shadowsong27.github.io/agentic-beacon/contributing/architecture/) — four-layer design, five domains, data flows
- [Configuration](https://shadowsong27.github.io/agentic-beacon/contributing/configuration/) — settings, workspace config, manifest models
- [Local Development](https://shadowsong27.github.io/agentic-beacon/contributing/local-development/) — dev loop, debugging, running subsets
- [Code Style](https://shadowsong27.github.io/agentic-beacon/contributing/code-style/) — naming, imports, formatting rules
- [Design Patterns](https://shadowsong27.github.io/agentic-beacon/contributing/design-patterns/) — recurring patterns and when to use them
- [Testing](https://shadowsong27.github.io/agentic-beacon/contributing/testing/) — test layout, unit vs integration, fixtures
- [Contribution Workflow](https://shadowsong27.github.io/agentic-beacon/contributing/contribution-workflow/) — branches, PRs, CI gates, release process
- [Documentation](https://shadowsong27.github.io/agentic-beacon/contributing/documentation/) — how docs are built and published
- [Gotchas](https://shadowsong27.github.io/agentic-beacon/contributing/gotchas/) — known traps and sharp corners
- [Open Questions](https://shadowsong27.github.io/agentic-beacon/contributing/open-questions/) — unresolved items

If the live site is ever unreachable, the same content is in `site-docs/contributing/` in this repo.
