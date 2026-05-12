# Decision: No Project-Local Artifact Overrides

**Date:** 2026-03-14
**Status:** Accepted (updated 2026-05-03 to reflect the symlink-based sync model)

## Decision

Agentic Beacon does not support project-local overrides of warehouse artifacts. There is no `overrides/` directory, no `abc override` command, and no mechanism to maintain a diverged version of a warehouse artifact within a project.

## Why

Project-local overrides promote divergence. If an artifact needs to be different for a project, that difference is almost always worth sharing with the whole team — which means it belongs in the warehouse, not hidden in a project directory.

Under the current symlink-based sync model (see [`single-warehouse-write-entrypoint`](../knowledge/decisions/single-warehouse-write-entrypoint.md)), the warehouse clone **is** the single source of truth on any given machine — a project's `.agentic-beacon/artifacts/` tree is symlinks into the warehouse. "Overriding" a warehouse artifact per-project is therefore not just discouraged, it is mechanically prevented.

The right workflow when a local change is discovered:

1. `abc warehouse status` — review what changed in the warehouse working tree (scoped by `beacon.yaml`)
2. `abc warehouse contribute -m "…"` — commit the improvement in the warehouse clone
3. Push the warehouse — teammates pull and `abc sync` if new paths were added

This keeps the warehouse as the single source of truth and ensures improvements discovered in one project benefit all projects.

## Genuine per-project variation

When a team genuinely needs different harness behavior for different projects, the correct response is to **author distinct artifacts** (e.g. `skills/code-review-python/` vs `skills/code-review-ts/`) and select between them via each project's `beacon.yaml`. The artifact system supports arbitrary naming; there is no need to duplicate the same-named file with different content.

## Historical note

Earlier versions of this document described the sync-time `--preserve` flag as "a narrow escape hatch for avoiding accidental overwrites during an active editing session." Under the symlink-based sync model, `abc sync` does not overwrite files (it creates or repairs symlinks pointing at the warehouse), and the preserve flag was removed from `abc sync`.
