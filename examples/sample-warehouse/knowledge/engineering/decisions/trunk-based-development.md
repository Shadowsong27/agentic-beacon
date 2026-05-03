# Decision: Trunk-Based Development

**Date:** 2026-01-01
**Status:** Active

---

## Context

Teams often debate between long-lived feature branches and short-lived branches merged frequently to main.

## Decision

Use trunk-based development: all engineers commit directly to `main` (or merge short-lived branches within 1–2 days).

## Implementation

- Feature flags for incomplete features in production
- All commits pass CI before merging
- Rebase rather than merge commits for linear history

## Consequences

**Positive:**
- Eliminates long-lived merge conflicts
- Forces small, reviewable changes
- Continuous integration is genuinely continuous

**Negative:**
- Requires discipline with feature flags
- Cannot use branch age as a proxy for maturity
