# beacon.yaml Reference

`beacon.yaml` is the configuration file that declares which artifacts your project pulls from the warehouse. It lives at `.agentic-beacon/beacon.yaml` and should be committed to git.

## File Location

```
my-project/
└── .agentic-beacon/
    ├── beacon.yaml     # ✅ Commit this
    ├── config.toml     # ❌ Gitignored (local warehouse path)
    └── artifacts/      # ❌ Gitignored (downloaded files)
```

## Full Schema

```yaml
artifacts:
  knowledge:
    - <pattern-or-path>
    - <pattern-or-path>

  skills:
    - <pattern-or-path>

  contexts:
    - <pattern-or-path>
```

All three keys are required (can be empty lists). The file is validated on `abc sync` and `abc setup`.

---

## `artifacts.knowledge`

Knowledge artifacts are markdown files — best practices, standards, framework guides, team decisions. They inform the agent's approach when answering questions or writing code.

```yaml
artifacts:
  knowledge:
    # Exact file path (relative to warehouse root)
    - knowledge/decisions/coding-standards.md

    # Directory wildcard — all files one level deep
    - knowledge/testing/*.md

    # Recursive wildcard — all .md files under a subtree
    - knowledge/python/**/*.md

    # Any path your warehouse uses
    - knowledge/global/**/*.md
```

**Path rules:**
- Paths are relative to the warehouse root
- Only files are matched (not directories)
- Patterns with `*`, `**`, or `?` are expanded as globs
- Unmatched patterns warn but do not cause errors
- The inner structure of `knowledge/` is defined by your warehouse — there are no required subdirectories

---

## `artifacts.skills`

Skills are directory-based — a skill is a directory with a `SKILL.md` entry point plus optional supporting files.

```yaml
artifacts:
  skills:
    # Sync all files in a skill directory
    - skills/code-review/**/*

    # Multiple skills
    - skills/generate-tests/**/*
    - skills/api-design/**/*

    # All skills under a category
    - skills/python/**/*
```

**Note:** Skills need `/**/*` (or at minimum `/**`) to match the files inside them. A pattern like `skills/code-review` matches nothing — the path resolves to a directory, not files.

---

## `artifacts.contexts`

Contexts are `AGENTS.md`-style files that load as boot context when the agent starts. They carry team standards, project conventions, and workflow rules.

```yaml
artifacts:
  contexts:
    # Global org context
    - contexts/global.md

    # Team context
    - contexts/teams/backend/AGENTS.md

    # Multiple contexts — all are loaded
    - contexts/teams/backend/AGENTS.md
    - contexts/projects/my-service/AGENTS.md
```

**How contexts are used:** AI agents read `AGENTS.md` files from the project root and `.agentic-beacon/artifacts/contexts/` at session start. Multiple contexts are all loaded — they stack rather than override.

---

## Complete Example

```yaml
# .agentic-beacon/beacon.yaml

artifacts:
  knowledge:
    # Team-wide Python standards
    - knowledge/languages/python/type-hints.md
    - knowledge/languages/python/async-patterns.md
    - knowledge/languages/python/error-handling.md

    # Framework-specific
    - knowledge/languages/python/fastapi/**/*.md
    - knowledge/languages/python/pydantic/**/*.md

    # Testing
    - knowledge/languages/python/pytest/**/*.md
    - knowledge/best-practices/tdd-workflow.md

    # Infrastructure
    - knowledge/infrastructure/docker-python.md

  skills:
    - skills/code-review/**/*
    - skills/generate-tests/**/*

  contexts:
    - contexts/global.md
    - contexts/teams/backend/AGENTS.md
```

---

## Minimal Example

```yaml
artifacts:
  knowledge: []
  skills: []
  contexts:
    - contexts/global.md
```

An empty `knowledge` or `skills` list is valid — those artifact types simply won't be synced.

---

## File Lifecycle

| Command | Effect on `beacon.yaml` |
|---------|------------------------|
| `abc setup --manual` | Creates an empty template |
| `abc setup --agent-assisted` | Creates template + `warehouse-catalog.md` to help fill it |
| `abc install <artifact>` | Copies and wires one artifact, then adds it to `beacon.yaml` |
| `abc sync` | Reads `beacon.yaml`, copies and wires all matching artifacts |
| `abc sync --prune` | Reads `beacon.yaml`, removes files no longer listed |
| `abc delta` | Reads `beacon.yaml` to determine which files to compare |
| `abc update` | Reads `beacon.yaml`, force-overwrites all files |

---

## Validation Rules

`abc sync` validates `beacon.yaml` before proceeding. It will error if:

- The file does not exist → run `abc setup --manual`
- The YAML is malformed (syntax error)
- The `artifacts` key is missing
- Any of `knowledge`, `skills`, or `contexts` is not a list

A warning (not an error) is shown for:
- Patterns that match no files in the warehouse

---

## What Gets Committed

**Commit:**
```
.agentic-beacon/beacon.yaml
```

**Do not commit (automatically gitignored):**
```
.agentic-beacon/config.toml
.agentic-beacon/artifacts/
.agentic-beacon/warehouse-catalog.md
```

The `.gitignore` entries are added automatically when you run `abc warehouse connect` and `abc sync`.

---

## Related Commands

```bash
# Create beacon.yaml
abc setup --manual

# Populate it with agent assistance
abc setup --agent-assisted

# Apply the configuration
abc sync

# Preview differences between local and warehouse
abc delta

# Check what's configured and synced
abc status
```

---

## Next Steps

- **[Advanced Patterns](./advanced-patterns.md)** — Glob syntax, sync flags, delta workflow
- **[Agent-Assisted Setup](./agent-assisted-setup.md)** — Let an AI agent help fill in `beacon.yaml`
- **[Creating Skills](./creating-skills.md)** — Build and add skills to your warehouse
