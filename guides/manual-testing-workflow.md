# Manual Testing Workflow

How to test `abc` CLI changes locally without publishing a release to PyPI.

---

## Install from Local Source (Global Tool)

Use `uv tool install` with the `--editable` flag to install `abc` globally from your local checkout:

```bash
uv tool install --editable ./libs/beacon
```

This makes `abc` available system-wide and picks up any local source changes immediately — no reinstall needed between edits.

**Verify:**
```bash
abc --version
```

---

## Re-install After Branch Switches or Dependency Changes

If you switch branches or change `libs/beacon/pyproject.toml`, reinstall to pick up the new state:

```bash
uv tool install --editable ./libs/beacon --reinstall
```

---

## Uninstall

```bash
uv tool uninstall agentic-beacon
```

---

## Comparison: Global Tool vs Dev Venv

| | `uv tool install --editable` | `uv sync --group dev` |
|---|---|---|
| `abc` available | System-wide (no activation) | Inside `.venv` only |
| Reflects edits | Yes (editable) | Yes (editable) |
| Use case | End-to-end manual testing | Running `pytest`, IDE tooling |
| Install location | `~/.local/share/uv/tools/` | `<repo>/.venv/` |

For day-to-day development and running tests, prefer the dev venv (`uv sync --group dev`). Use the global tool install when you want to test `abc` exactly as an end-user would — in a real project directory outside the repo.

---

## End-to-End Test Checklist

After installing, run through the core commands in a scratch directory:

```bash
mkdir /tmp/test-project && cd /tmp/test-project

# Initialise a warehouse
abc init /tmp/test-warehouse

# Connect and set up
abc warehouse connect --path /tmp/test-warehouse
abc setup --manual       # or --agent-assisted

# Edit beacon.yaml, then sync
abc sync

# Check status
abc status
abc delta
```
