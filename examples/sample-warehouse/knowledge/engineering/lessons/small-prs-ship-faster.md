# Lesson: Small PRs Ship Faster

**Last Updated:** 2026-01-01

---

## Pattern

PRs under 300 lines get reviewed and merged within hours. PRs over 800 lines sit for days and accumulate stale conflicts.

## Steps/Implementation

- Split features into logical units: data model, business logic, API layer, tests — each as its own PR
- If a PR touches more than 3 files that are conceptually unrelated, consider splitting
- Use stacked PRs (each builds on the previous) for sequential work

## Common Mistakes

- Bundling refactoring with feature work
- Including unrelated "while I was in here" fixes
- Waiting to open a PR until the feature is "done"

## Why This Matters

Review throughput is a leading indicator of team velocity. Large PRs are a bottleneck multiplier.
