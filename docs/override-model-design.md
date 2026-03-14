# Override Model Design

How project-local artifact overrides work in Agentic Beacon.

**Status:** Accepted — pending implementation
**Last Updated:** 2026-03-14

---

## Problem

Projects sometimes need a different version of a warehouse artifact. The current `--preserve` flag is the only mechanism, and it has three problems:

1. **Opt-in per command** — easy to forget; one `abc sync` without `--preserve` silently overwrites local changes
2. **No signal of intent** — a preserved file and an accidentally modified file look identical to `abc delta` (both show as `MODIFIED`)
3. **Fragile** — relies on the user remembering the flag rather than making the override an explicit artifact in the project

---

## Design

### Core principle

Warehouse artifacts are always warehouse-owned. `abc sync` always overwrites them. If a project needs a different version of an artifact, it creates an explicit **override file** in a separate location. The override is a first-class project artifact — committed to git, visible to teammates.

### Directory structure

```
.agentic-beacon/
  artifacts/        # warehouse-owned — always overwritten by abc sync
    knowledge/
    contexts/
    skills/
  overrides/        # project-owned — never touched by abc sync
    knowledge/      # mirrors artifacts/ structure exactly
    contexts/
    skills/
```

Override paths mirror artifact paths. An override for `knowledge/decisions/coding-standards.md` lives at `.agentic-beacon/overrides/knowledge/decisions/coding-standards.md`.

### abc sync

- Copies warehouse → `artifacts/` as always
- **Never touches `overrides/`**
- After sync, if any overrides exist, prints:
  `"N artifact(s) have project overrides — run abc delta to review"`
- `--preserve` flag is **removed**

### abc delta

Gains a new status:

| Status | Meaning |
|--------|---------|
| `IDENTICAL` | Local artifact matches warehouse |
| `MODIFIED` | Local artifact differs from warehouse — **accidental**, no override file |
| `OVERRIDDEN` | Override file exists — intentional, project-local version |
| `MISSING` | In beacon.yaml but not yet synced |
| `ADDED` | Exists locally, not in warehouse |

`MODIFIED` is now unambiguously a warning: something changed that shouldn't have. The fix is either `abc sync` (to restore) or `abc override create` (to formalise the intent).

`OVERRIDDEN` is informational: the project has an explicit local version. Not a problem.

### abc override (new command group)

```bash
# Create an override starting from the current synced artifact
abc override create knowledge/decisions/coding-standards.md

# List all project overrides
abc override list

# Remove an override (project reverts to warehouse version on next sync)
abc override remove knowledge/decisions/coding-standards.md
```

`abc override create` copies `.agentic-beacon/artifacts/<path>` → `.agentic-beacon/overrides/<path>` as a starting point, then the user edits the override file. If no synced artifact exists, it creates an empty file.

### Agent wiring

When `abc sync` wires contexts into `opencode.json` / `CLAUDE.md`, it checks for overrides first:

- If an override exists for a context → wire the **override path** (`.agentic-beacon/overrides/contexts/<name>.md`)
- Otherwise → wire the artifact path (`.agentic-beacon/artifacts/contexts/<name>.md`)

The agent only sees one version — the most specific one. Override takes precedence.

Skills follow the same rule: if `.agentic-beacon/overrides/skills/<name>/SKILL.md` exists, install from there instead of `artifacts/`.

### abc contribute interaction

`abc contribute` scans for `MODIFIED` artifacts to offer for contribution back to the warehouse.

- `MODIFIED` artifacts are offered as usual
- `OVERRIDDEN` artifacts are **not offered** by default — they're intentional project customisations
- `abc contribute --include-overrides` can optionally promote an override to the warehouse (for when a project-level improvement is worth sharing)

---

## Migration

Users currently using `--preserve`:
1. Run `abc delta` to find all `MODIFIED` artifacts
2. For each intentional local change, run `abc override create <path>`
3. Edit the override file with the desired content
4. Run `abc sync` — warehouse artifacts are restored, overrides remain untouched

`--preserve` is removed with a deprecation warning if passed, pointing to `abc override create`.

---

## What is not changing

- `abc delta` for non-override use cases (ADDED, MISSING, MODIFIED) works exactly as today
- The `artifacts/` directory layout is unchanged
- `beacon.yaml` is unchanged — overrides do not need to be declared
- `abc contribute` for MODIFIED artifacts is unchanged
