# Decision: Project Override Model

**Date:** 2026-03-14
**Status:** Accepted — pending implementation

## Decision

Project-local overrides are explicit files in `.agentic-beacon/overrides/`, mirroring the `artifacts/` structure. `abc sync` always owns `artifacts/` and never touches `overrides/`. The `--preserve` flag is removed.

## Why

`--preserve` conflates accidental modifications with intentional overrides, is easy to forget, and provides no visibility to teammates. Explicit override files are committed to git, visible, and unambiguous.

## Key rules

- `artifacts/` = warehouse-owned, always overwritten by `abc sync`
- `overrides/` = project-owned, never touched by `abc sync`
- `abc delta` distinguishes `MODIFIED` (accidental) from `OVERRIDDEN` (intentional)
- Agent wiring prefers override path over artifact path when both exist
- `abc contribute` skips overrides by default

## Read

[Override Model Design](../../docs/override-model-design.md)
