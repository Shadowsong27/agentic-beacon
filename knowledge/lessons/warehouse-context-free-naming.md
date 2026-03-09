# Lesson: Context Files in Warehouses Use Free Naming — Not AGENTS.* Convention

**Last Updated:** 2026-03-10
**Context:** Agentic Beacon framework — warehouse artifact organization

---

## Context

The `AGENTS.md` naming convention applies at the **project level** (a single file at the project root) and **user level** (`~/.config/opencode/AGENTS.md`). It does not extend into warehouse context files.

## Pattern

Warehouse context files (inside `contexts/`) should use **free, descriptive names** that reflect their purpose — not the `AGENTS.*` prefix pattern.

**Correct:**
```
contexts/
├── global.md
├── python.md
├── backend-team.md
└── data-platform.md
```

**Incorrect — do not do this:**
```
contexts/
├── AGENTS.global.md
├── AGENTS.python.md
└── AGENTS.data-platform.md
```

## Why This Matters

- The `AGENTS.*` prefix convention is meaningful at project/user level where agents look for a single file by convention
- In a warehouse, context files are explicitly declared in `beacon.yaml` — the name has no special meaning to any tool, so it should be human-readable and descriptive
- Using `AGENTS.*` in a warehouse creates confusion about which `AGENTS.md` a reader is looking at (project root vs. warehouse artifact)
- Free naming also reinforces the principle that **the inner structure of warehouse folders is not prescribed** by the framework

## Application

Whenever writing documentation, examples, or code that references warehouse context files, use plain descriptive names:

```yaml
# beacon.yaml — correct
artifacts:
  contexts:
    - contexts/global.md
    - contexts/python.md
```

Update any existing docs or sample warehouses that use `AGENTS.global.md`, `AGENTS.python.md` etc. to use plain names instead.
