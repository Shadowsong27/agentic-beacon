# GitHub Actions CI

Wire `abc warehouse lint` into your warehouse's CI so every PR is validated before merge. The warehouse is the single write entrypoint for every harness artifact on a machine — a bad merge to `main` poisons every project's next `abc sync`. Catching frontmatter mistakes and broken `requires:` references at PR time is much cheaper than discovering them downstream.

## When to use

- **Always**, for any warehouse pushed to GitHub. CI is the canonical enforcement point — pre-commit hooks are an optimisation on top, not a replacement.
- Pair with a branch-protection rule on `main` that requires the lint check, so a contributor cannot bypass it.

---

## Drop-in workflow

Create `.github/workflows/lint.yml` in your warehouse:

```yaml
name: Warehouse Lint

on:
  pull_request:
    branches:
      - main
  push:
    branches:
      - main

concurrency:
  group: warehouse-lint-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    name: Warehouse Lint
    runs-on: ubuntu-latest
    timeout-minutes: 5

    steps:
      - name: Checkout warehouse
        uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          version: "0.5.18"

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install agentic-beacon
        run: uv tool install agentic-beacon

      - name: Show abc version
        run: abc --version

      - name: Run warehouse lint
        run: abc warehouse lint .

      - name: Publish summary
        if: always()
        run: |
          echo "## Warehouse Lint" >> $GITHUB_STEP_SUMMARY
          echo "**Status**: ${{ job.status }}" >> $GITHUB_STEP_SUMMARY
```

That's it. The workflow:

- Runs on every PR to `main` and every push to `main`.
- Uses `ubuntu-latest` because warehouse lint has zero external dependencies (no DB, no internal registry).
- Pins Python `3.12` — the lower bound of `agentic-beacon`'s declared `requires-python = ">=3.12"`. One supported version is enough for a lint job; no need to matrix.
- Installs the CLI via `uv tool install` (no editable / no venv pollution).

---

## Design choices, explained

### Why `uv tool install agentic-beacon` instead of `pip install`

Per the project's [Python standards](../../concepts/how-it-works.md) and AGENTS.md, `uv` is the canonical Python toolchain. `uv tool install` creates an isolated environment for the CLI and exposes `abc` on `PATH` — same shape as `pipx install`, but inside the `uv` ecosystem the runner is already set up for.

### Why no version pin in `uv tool install agentic-beacon`

Floating to the latest published version is intentional: it keeps your warehouse lint in lockstep with what `abc sync` enforces downstream, so the two cannot drift. If you ever need a deterministic build, pin via `uv tool install "agentic-beacon==3.4.0"` — but expect to bump it whenever a new validation rule lands.

### Why `concurrency: cancel-in-progress: true`

Cheap optimisation: when you force-push or amend a PR, the older runs are cancelled instead of racing. Standard pattern across the homelab CI fleet.

### Why `timeout-minutes: 5`

Generous ceiling. A real lint run is sub-second; the bulk of the 30-90 seconds is `uv tool install` cold-cache. The timeout exists as a safety net against a future regression that hangs.

---

## Branch protection

Workflow alone is not enough — a contributor with `Settings > Branches > Allow administrators to bypass` enabled can still merge a red PR. Lock it down:

1. GitHub repo → **Settings** → **Branches** → **Add rule** for `main`.
2. Tick **Require status checks to pass before merging**.
3. In the search box, add `Warehouse Lint` (the job name, not the workflow name).
4. Tick **Do not allow bypassing the above settings**.

Without this, the CI is advisory only.

---

## Verifying the workflow on your warehouse

Before opening the PR with the workflow, run the lint locally to make sure the warehouse is currently green:

```bash
abc warehouse lint .
```

If it fails on a current artifact, fix it first — landing the workflow against a broken tree blocks every future PR until someone unblocks `main`.

---

## Troubleshooting

### `Error: No such command 'lint'`

The PyPI version of `agentic-beacon` you installed predates the `warehouse lint` command. Either pin to `>=3.4.0` explicitly, or wait for `uv tool install agentic-beacon` to resolve a newer release.

### `Skill 'foo' frontmatter error: File has no YAML frontmatter`

Working as intended — that's the rule the workflow is catching. Add `---` frontmatter to the offending file. See [Bundled Skills](../../concepts/bundled-skills.md) for the schema.

### Lint passes locally but fails in CI

Your local `abc` is likely installed editable from a working copy newer than what's on PyPI. Reinstall from PyPI (`uv tool install --reinstall agentic-beacon`) to reproduce the CI environment locally.

---

## Pair with a pre-commit hook

CI catches everything but only after you push. For local fast-feedback on the same rules, layer a [pre-commit hook](pre-commit.md) on top — same logic, sub-second, runs before you even commit.
