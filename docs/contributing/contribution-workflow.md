# Contribution Workflow

How to contribute a change — from branch to merged PR.

---

## Before You Start

1. Check [open issues](https://github.com/Shadowsong27/agentic-beacon/issues) for context.
2. For non-trivial changes, open or comment on an issue first to align on approach.
3. Make sure your environment is set up: see [CONTRIBUTING.md](../../CONTRIBUTING.md).

---

## Branch Strategy

| Branch type | Naming | Triggers |
|---|---|---|
| Feature / fix | `feat/short-description` or `fix/short-description` | Unit CI on push |
| Release | `release/vX.X.X` | Full CI + PyPI publish |
| Main | `main` | Docs deploy; release-please PR management |

Do **not** push directly to `main` or `release/vX.X.X`. Open a PR from a feature branch.

---

## Development Loop

```bash
# 1. Create a branch
git checkout -b feat/my-feature

# 2. Make changes; run tests after each logical unit
pytest -m "not integration" -x          # fast feedback
pytest -m "not integration" -k "my_area"

# 3. Pre-commit runs on commit (or run manually)
pre-commit run --all-files

# 4. Verify the CLI still works
.venv/bin/abc --version
.venv/bin/abc --help
```

---

## Conventional Commits

This project uses [Conventional Commits](https://www.conventionalcommits.org/) for automated
changelog generation via release-please.

| Prefix | When to use |
|---|---|
| `feat:` | New feature visible to end users |
| `fix:` | Bug fix visible to end users |
| `docs:` | Documentation changes only |
| `test:` | Test additions or fixes |
| `refactor:` | Code change with no user-visible effect |
| `chore:` | Maintenance (deps, CI, tooling) |
| `feat!:` or `fix!:` | Breaking change (adds major version bump) |

Example:

```
feat: add --dry-run flag to abc adopt

Allow users to preview adoption changes without writing to disk.
Resolves #42.
```

---

## Pre-PR Checklist

Before opening a PR, verify:

- [ ] `pytest -m "not integration"` passes with no new failures
- [ ] `pre-commit run --all-files` passes
- [ ] Architecture tests pass: `pytest tests/unit/test_architecture.py`
- [ ] If adding a new CLI command: handler follows the thin-handler pattern (see
  [Architecture](architecture.md#cli-layer-rules))
- [ ] If adding a new domain module: placed in the correct domain; not in `core/` unless
  multiple domains share it
- [ ] If adding dependencies: update `libs/beacon/pyproject.toml`; run `uv sync --group dev`

---

## Opening a PR

- Use a descriptive title following the Conventional Commits format.
- Link the related issue in the PR description.
- The CI bot (`opencode-review.yml`) will post an automated code review. Address its findings
  before requesting human review.
- Integration tests run automatically on PRs targeting `main`.

---

## Changing the OpenCode Review Bot Model

```bash
# Override the default model for the review bot
gh variable set OPENCODE_REVIEW_MODEL \
  -R Shadowsong27/agentic-beacon \
  --body "anthropic/claude-3-7-sonnet"

# Revert to workflow default
gh variable delete OPENCODE_REVIEW_MODEL -R Shadowsong27/agentic-beacon
```

---

## Release Process

Releases are fully automated via release-please. **You do not cut releases manually** unless
specifically authorized.

1. Merge PRs to `main` with conventional commit messages.
2. Release-please opens an automated release PR when enough changes accumulate.
3. Merging the release PR pushes to `main` and creates a git tag
   `agentic-beacon@vX.X.X`.
4. A release engineer pushes a `release/vX.X.X` branch to trigger PyPI publishing:

```bash
git fetch origin
git push origin refs/tags/agentic-beacon@vX.X.X:refs/heads/release/vX.X.X
```

Manual version bumps are available via `workflow_dispatch` on `release-please.yml`.
