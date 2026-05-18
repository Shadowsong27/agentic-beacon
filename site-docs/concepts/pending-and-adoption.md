# Pending & Adoption

`pending.yaml` is the staging area between authoring a warehouse artifact and wiring it into your project. This page explains the file format, who writes to it, and how `abc adopt` processes it.

---

## What `pending.yaml` Is

`.agentic-beacon/pending.yaml` is a gitignored per-project file that buffers artifacts written to the warehouse (by the `record-*` bundled skills) that have not yet been wired into `beacon.yaml`.

It exists because authoring and adopting are separate steps. You write a skill into the warehouse with `/record-skill`, but you choose when and whether to pull it into the current project via `abc adopt`.

The file is absent or contains `pending: []` when nothing is pending. It is regenerated on writes and pruned on adopt.

---

## YAML Shape

```yaml
pending:
  - path: skills/python-type-hints/
    type: skill
    action: created
    source: record-skill
    created_at: '2026-05-13T14:32:07Z'
```

| Field | Values | Meaning |
|---|---|---|
| `path` | warehouse-relative path | The artifact written to the warehouse |
| `type` | `skill`, `context`, `agent` | Artifact category (determines adopt behavior) |
| `action` | `created`, `modified` | Whether this is a new file or an edit |
| `source` | skill name | Which bundled skill wrote the entry |
| `created_at` | `YYYY-MM-DDTHH:MM:SSZ` (UTC) | When the entry was appended |

Knowledge files are **not** tracked in `pending.yaml`. The knowledge resolver scans contexts and skills that are already wired into your project for markdown links into `knowledge/`; only reachable files are synced.

---

## The Author → Pending Pipeline

`record-skill` writes to two places in a single agent action (future bundled skills may add `/record-context` and `/record-agent` to author contexts and agents directly; for now, contexts and agents are authored by hand and added to `pending.yaml` manually):

```
/record-skill
     │
     ├── writes  <warehouse>/skills/<name>/SKILL.md
     │
     └── calls   scripts/append_pending.py
                     │
                     └── appends to  .agentic-beacon/pending.yaml
```

`scripts/append_pending.py` is a self-contained script with no dependency on the `beacon` package — it only requires `pyyaml>=6.0`. This makes the pipeline work for any `abc` installation (pipx, pip, uv tool install) without needing the agentic-beacon source checkout.

The script walks up the directory tree from the calling agent's working directory to find the project root (the nearest ancestor containing `.agentic-beacon/config.toml`), then appends a `PendingEntry` to `pending.yaml` after validating field types and enum values. Duplicate entries are not detected — if the same artifact path is recorded twice, both entries will land in the file.

**Knowledge files are a special case.** `record-knowledge` writes to `<warehouse>/knowledge/` but does **not** append to `pending.yaml`. Knowledge files are also **not** synced automatically. The knowledge resolver scans contexts and skills that are already wired into your project (via `beacon.yaml`) and follows their markdown links into `<warehouse>/knowledge/`. Only knowledge files reachable from an adopted context or skill appear under `.agentic-beacon/artifacts/knowledge/` after `abc sync` / `abc adopt`.

So in practice: if `record-knowledge` writes a new lesson and a context already adopted in your project links to that lesson's path, the lesson will sync automatically on the next `abc sync`. If no adopted context or skill links to it yet, you'll need to author or adopt a context first (or hand-edit an existing one) that references the new knowledge path.

---

## Pending Alert

Every `abc` subcommand prints a one-line notice to stderr when `pending.yaml` is non-empty:

```
⚠ 2 pending artifacts. Run 'abc adopt' to wire them.
```

This does not affect the subcommand's exit code. It fires on every command — `abc sync`, `abc warehouse status`, `abc doctor` — until you run `abc adopt` and clear the entries.

---

## Three-Way Adopt Actions

`abc adopt` opens the TUI. Pending entries appear alongside warehouse artifacts you have not yet adopted. For each pending entry you can choose one of three actions:

| Action | Effect on `pending.yaml` | Effect on `beacon.yaml` | Warehouse file |
|---|---|---|---|
| **accept** | Entry removed | Path appended, symlinks created | Untouched |
| **reject** | Entry removed | No change | Untouched |
| **defer** (default) | Entry kept | No change | Untouched |

Rejecting an entry only removes it from `pending.yaml`. The warehouse file remains — it was written by the skill and is part of the warehouse working tree. If you want to delete the warehouse file, do so manually and commit via `abc warehouse contribute`.

---

## Confirm Screen

After you mark all entries in the TUI, a projected-mutations summary appears before any filesystem writes:

```
Proposed changes
────────────────────────────────────────
  Accepting:
    + skills/python-type-hints/  → beacon.yaml
    + .agentic-beacon/pending.yaml (1 entry removed)

  Rejecting:
    ~ (nothing)

  Deferring:
    ~ (nothing)

Enter to proceed  Escape to cancel
```

Press `Enter` to commit. Press `Escape` or `q` to return to the TUI without writing anything.

---

## Atomic Commit with Rollback

The write step is atomic. If the commit raises an unhandled exception mid-write — disk full, permission error, malformed `beacon.yaml` after the change — the rollback restores `beacon.yaml`, `pending.yaml`, and `.last-adopt` to their pre-commit state. **Limit:** rollback handles caught Python exceptions only. A hard process kill (`SIGKILL`, system crash, or Ctrl-C delivered to an unprotected operation) could leave the commit half-applied. Re-running `abc adopt` is safe and the inconsistency is usually limited to `pending.yaml` vs `beacon.yaml` drift.

---

## `.last-adopt`

`.agentic-beacon/.last-adopt` is a single-line ISO-8601 UTC timestamp written after each successful `abc adopt` commit:

```
2026-05-13T14:55:00Z
```

It is gitignored. Future `abc adopt` invocations use it to detect hand-edited warehouse files: any warehouse file modified after the `.last-adopt` timestamp but not tracked in `pending.yaml` is flagged in the TUI as a potential untracked edit.

---

## Full Walkthrough

```bash
# 1. Author a new skill via the bundled skill
#    (inside a Claude Code or OpenCode agent session)
/record-skill
# Agent prompts: skill name, description, initial process steps
# Agent writes:
#   <warehouse>/skills/python-type-hints/SKILL.md
#   .agentic-beacon/pending.yaml  (appended with type: skill)

# 2. Pending alert appears on every abc command from now on:
abc warehouse status
# → "⚠ 1 pending artifacts. Run 'abc adopt' to wire them."

# 3. Inspect the pending file directly if you like:
cat .agentic-beacon/pending.yaml
# pending:
# - path: skills/python-type-hints/
#   type: skill
#   action: created
#   source: record-skill
#   created_at: '2026-05-13T14:32:07Z'

# 4. Run adopt — TUI opens, pending entry shown alongside warehouse artifacts
abc adopt
# → mark the entry as: accept / reject / defer (↑↓ to navigate, Space to select)
# → confirm screen shows projected mutations
# → press Enter to commit

# After commit (accept path):
#   .agentic-beacon/beacon.yaml   ← skills/python-type-hints/ added
#   .agentic-beacon/pending.yaml  ← entry removed (or empty)
#   .agentic-beacon/.last-adopt   ← timestamp updated
#   .agentic-beacon/artifacts/skills/python-type-hints/SKILL.md  ← symlink
```

For details on how bundled skills are wired into your project after `abc adopt`, see [Bundled Skills](bundled-skills.md).

---

## Next Steps

- **[Bundled Skills](bundled-skills.md)** — the `record-*` skills that write to `pending.yaml`
- **[Adopting Artifacts](../guides/adopting-artifacts.md)** — full `abc adopt` TUI reference
- **[beacon.yaml Reference](../reference/beacon-yaml.md)** — structure of the committed artifact config
