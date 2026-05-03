# Decision: Single Warehouse Write Entrypoint

**Date:** 2026-05-03
**Status:** Accepted
**Context:** Agentic Beacon artifact distribution model — supersedes the copy-based per-project isolation design.

## Decision

The locally-cloned warehouse is the **single write entrypoint** for every harness artifact on a given machine. Projects are read/write **windows** into that clone via per-file symlinks under `.agentic-beacon/artifacts/`. One logical artifact = one physical file per machine.

**Consequences we explicitly accept:**

1. Editing a skill through Project A's `.agentic-beacon/artifacts/…` path is literally editing the warehouse working tree.
2. Project B's agent, reading the same artifact a second later, sees Project A's edit immediately. This is **intended**, not a bug.
3. Contribute is `git add` + `git commit` inside the warehouse clone (`abc warehouse contribute`). It is never a per-project merge.
4. No project-vs-warehouse delta exists — they share inodes. Drift questions become warehouse-vs-remote questions, surfaced by `abc warehouse status`.

## Rationale

### Empirical basis

One month of production use under the old **copy-based, per-project isolation** model surfaced a consistent regression pattern:

- An agent edits a skill or knowledge file inside Project A to improve the harness.
- Hours later, the same agent in Project B edits the same file against the same stale base.
- Both projects eventually run `abc contribute`. The second contribution silently overwrites the first.
- The regression is invisible until the artifact is exercised and the behavior quietly drifts.

The intended upside of per-project isolation — "safe local experimentation without affecting other projects" — did not materialize in practice. Concurrent harness development across projects on the same machine is **not a workflow that actually occurs**. The realized cost (last-writer-wins regressions, merge-back cycles, confusion about which copy was canonical) far exceeded the realized benefit (zero observed cases of intentional per-project harness divergence).

### Why single-entrypoint resolves the problem at the root

Two on-disk copies of one logical file is the root cause. Collapsing the duplication — one physical file per machine, referenced from any number of projects — makes the regression class mechanically impossible. Git in the warehouse clone is the single source of truth and the single conflict-detection mechanism.

### Escape valve: distinct artifacts, not duplicated files

If a team genuinely needs different harness behavior for different projects, the correct response is to **author distinct skills/agents/knowledge entries** — the artifact system already supports arbitrary naming and per-project `beacon.yaml` selection. Duplicating the same-named artifact across projects to get different behavior was always a hack that worked accidentally under the copy model; under the new model it is unsupported by design.

### One-way decision

The **sync mechanism** (symlinks vs copies) is mechanically reversible — the rollback path is documented in the proposal's migration plan. The **philosophy** (single entrypoint vs per-project isolation) is not reversible without fresh evidence that concurrent harness development is a real workflow. Any future proposal to restore isolation must reopen this decision explicitly and present empirical justification, not theoretical appeal.

## Implementation

The philosophy is enforced mechanically by the `symlink-based-artifact-sync` change:

- `abc sync` creates per-file symlinks into `.agentic-beacon/artifacts/` with absolute targets resolving into the warehouse clone.
- `abc warehouse contribute` is the only supported write path back to the warehouse; `abc contribute` is removed.
- `abc warehouse status` replaces `abc delta`; drift is a warehouse-vs-remote concept, not a project-vs-warehouse concept.
- Platform: macOS and Linux only. Windows is rejected at the CLI entrypoint.

## Cross-Project Visibility Is Intended

Agents reading this repo must internalize that per-machine cross-project visibility of harness edits is a **feature**, not a leak. Documentation and error messages are written on this assumption. Any future work that treats cross-project visibility as a bug should first re-read this decision.

## Related Artifacts

- Proposal: `openspec/changes/symlink-based-artifact-sync/proposal.md`
- Design: `openspec/changes/symlink-based-artifact-sync/design.md` (Decision 8 captures this philosophy in-situ)
- New symlink-based sync spec: `openspec/specs/symlink-based-sync/spec.md`
- Archived: `openspec/specs/snapshot-based-sync/spec.md` (copy-based sync), `openspec/specs/delta-contribution-workflow/spec.md` (per-project delta + contribute)
- Archived prose: `archive/` (see `archive/README.md`)
