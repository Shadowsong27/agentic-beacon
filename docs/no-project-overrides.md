# Decision: No Project-Local Artifact Overrides

**Date:** 2026-03-14
**Status:** Accepted

## Decision

Agentic Beacon does not support project-local overrides of warehouse artifacts. There is no `overrides/` directory, no `abc override` command, and no mechanism to maintain a diverged version of a warehouse artifact within a project.

## Why

Project-local overrides promote divergence. If an artifact needs to be different for a project, that difference is almost always worth sharing with the whole team — which means it belongs in the warehouse, not hidden in a project directory.

The right workflow when a local change is discovered:

1. `abc delta` — review what changed locally
2. `abc contribute` — copy the improvement back to the warehouse
3. `abc sync` — pull the updated artifact back to all projects

This keeps the warehouse as the single source of truth and ensures improvements discovered in one project benefit all projects.

## What this means for --preserve

The `--preserve` flag (`abc sync --preserve`) remains as a narrow escape hatch for avoiding accidental overwrites during an active editing session. It is not documented as a workflow feature and should not be used as a substitute for contributing changes back.
