# Migration: Pending Artifacts Flow & Record-* Revamp

**Applies to:** Projects and warehouses used with `agentic-beacon >= X.Y.0`
(version will be filled in when the feature ships).

**Breaking changes:** Yes — `record-knowledge` and `record-skill` now write
to the warehouse, not the project. Both skills hard-error outside a connected
project. See [Breaking Changes](#breaking-changes) below.

---

## What Changed and Why

Previously, `record-knowledge` wrote directly into `.agentic-beacon/artifacts/knowledge/`
and updated `AGENTS.md` in the current project. `record-skill` invoked
`create_skill.py` to scaffold a skill into the project-local artifacts
directory. Neither skill touched the warehouse, so the authored content was
invisible to other projects and never distributed through `abc adopt`.

This release establishes a **warehouse-write model**:

1. Authoring skills (`record-knowledge`, `record-skill`) write to the warehouse
   working tree, not the project.
2. A new file — `.agentic-beacon/pending.yaml` — tracks authored artifacts
   waiting to be wired into the project.
3. `abc adopt` gained a **three-way action model** (accept / reject / defer)
   and a confirm screen before any filesystem mutation.
4. A `.last-adopt` marker enables `abc adopt` to detect hand-edited warehouse
   files even when no authoring skill was used.

---

## `pending.yaml` — What It Is

`.agentic-beacon/pending.yaml` is a project-local, gitignored file that
records artifacts authored in the warehouse from within this project but not
yet wired into `beacon.yaml`:

```yaml
pending:
  - path: knowledge/lessons/debugging-pydantic.md
    type: knowledge
    action: created
    source: record-knowledge
    created_at: 2026-05-06T14:22:00+00:00

  - path: contexts/python-standards.md
    type: context
    action: modified
    source: record-knowledge
    created_at: 2026-05-06T14:22:01+00:00
```

**Entry fields:**

| Field | Description |
|---|---|
| `path` | Warehouse-relative path to the artifact |
| `type` | One of `knowledge`, `skill`, `context`, `agent` |
| `action` | `created` (new artifact) or `modified` (existing file edited) |
| `source` | Authoring skill that produced the entry (free-form string) |
| `created_at` | ISO-8601 UTC timestamp when the entry was appended |

The file is absent (or `pending: []`) when no artifacts are pending. Both
states are equivalent. After a successful `abc adopt` session, entries are
removed — accepted and rejected entries are cleared; deferred entries stay.

**The file is gitignored by default.** It represents per-developer
working state, not shared project config. Do not commit it.

---

## How Authoring Skills Changed

### `record-knowledge`

| Before | After |
|---|---|
| Wrote knowledge file to `.agentic-beacon/artifacts/knowledge/` | Writes knowledge file to `<warehouse>/knowledge/<type>/<name>.md` |
| Updated `AGENTS.md` with pointer | Offers to insert pointer into a warehouse context file only (not `AGENTS.md`) |
| No pending.yaml interaction | Appends entries to `.agentic-beacon/pending.yaml` |
| No warehouse required | Hard-errors if no warehouse is connected |

**Context pointer behaviour:** When offering a pointer target, only files
under `<warehouse>/contexts/*.md` are listed. `AGENTS.md` is never a target.
The proposed diff is shown before writing; declining leaves the context file
untouched (only the knowledge entry is appended to `pending.yaml`).

### `record-skill`

| Before | After |
|---|---|
| Used `create_skill.py` to scaffold skill in project artifacts directory | LLM-driven scaffold; writes directly to `<warehouse>/skills/<name>/` |
| No `requires.contexts` suggestion | Scans warehouse contexts and proposes a `requires.contexts` list with rationale |
| No pending.yaml interaction | Appends one entry to `.agentic-beacon/pending.yaml` |
| No warehouse required | Hard-errors if no warehouse is connected |

`create_skill.py` has been deleted. If you had custom automation calling it
directly, replace those calls with the new skill flow or write to the warehouse
directly.

---

## How `abc adopt` Changed

### Three-Way Per-Entry Actions

The TUI now offers three choices per artifact:

| Key | Action | Effect at commit |
|---|---|---|
| `a` | **Accept** | Add to `beacon.yaml`, create symlink, remove from `pending.yaml` |
| `r` | **Reject** | Remove from `pending.yaml` only; warehouse file untouched |
| `d` | **Defer** (default) | Keep in `pending.yaml`; no beacon.yaml change |

Unmarked entries are treated as deferred.

### Confirm Screen

After pressing Apply, a confirm screen summarises:
- N accepted → wiring in `beacon.yaml` + syncing symlinks
- N rejected → removing from `pending.yaml`
- N deferred → keeping in `pending.yaml`

No filesystem mutation happens until you confirm.

### Atomic Commit with Rollback

The commit applies all choices as a single logical transaction. On any failure
mid-commit (e.g. a symlink sync error), the system restores `beacon.yaml`,
`pending.yaml`, and `.last-adopt` to their pre-commit state and surfaces a
clear error identifying the failing entry.

### `.last-adopt` Marker

`abc adopt` now maintains `.agentic-beacon/.last-adopt` — a single-line
ISO-8601 UTC timestamp recording when the last successful adopt session
committed. This enables discovery of hand-edited warehouse files that were
never tracked in `pending.yaml`. Files modified in the warehouse after
`.last-adopt` appear in the TUI alongside `pending.yaml` entries, annotated
as `warehouse-modified`.

### Pending Alert

Every `abc` subcommand run inside a project prints a one-line notice on
stderr when `pending.yaml` is non-empty:

```
⚠ N pending artifacts. Run 'abc adopt' to wire them.
```

This notice does not block the command and does not affect the exit code.

---

## Breaking Changes

### 1. `record-knowledge` no longer writes to `.agentic-beacon/artifacts/knowledge/`

**Before:** Knowledge files were written into the project-local artifact
tree. No warehouse was required.

**After:** Knowledge files are written to the warehouse. Running
`record-knowledge` outside a connected project (no `.agentic-beacon/config.toml`
in the cwd-walk chain) hard-errors with:

```
Error: no warehouse connected. Run 'abc warehouse connect <path>' first.
```

**Migration:** Connect your project to a warehouse with `abc warehouse connect
--path <path>` before running `record-knowledge`. Existing knowledge files in
`.agentic-beacon/artifacts/knowledge/` should be moved to the warehouse
manually.

### 2. `record-knowledge` no longer updates `AGENTS.md`

Pointer inserts now target warehouse context files only. `AGENTS.md` is not
offered as a pointer target.

### 3. `record-skill` no longer uses `create_skill.py`

`create_skill.py` is deleted. Running `record-skill` now requires a connected
warehouse. The skill directory is created directly in the warehouse.

### 4. `abc adopt` requires explicit confirm before mutating files

Previously, `abc adopt` wrote choices immediately. Now an Apply → Confirm
flow is required. Automated scripts that accepted `abc adopt` output
non-interactively will need to be updated.

---

## Rollback Path

If you need to undo pending artifacts after an adopt session fails or you
want to clean up:

1. **Reject in `abc adopt`:** Mark unwanted entries as reject; they are
   removed from `pending.yaml` without touching the warehouse file.

2. **Manual cleanup:** Delete entries from `.agentic-beacon/pending.yaml`
   directly (it is a plain YAML file). Delete the warehouse file if
   desired via `abc warehouse contribute` or a direct git revert in the
   warehouse repo.

3. **Undo a committed adopt:** Restore `beacon.yaml` to its pre-adopt state
   (use `git diff` in your project), remove the symlinks from
   `.agentic-beacon/artifacts/`, and reset `.last-adopt` to its previous
   value (or delete it).
