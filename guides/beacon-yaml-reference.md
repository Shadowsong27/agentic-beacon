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
  agents:
    - <pattern-or-path>

  skills:
    - skills/<name>/      # directory-level entry (canonical form)

  contexts:
    - <pattern-or-path>

# Optional — suppress skills from warehouse-scoped status reports
ignore:
  skills:
    - "openspec-*"        # fnmatch glob patterns
```

> **Note:** `artifacts.knowledge` was removed in a recent version. Knowledge is now auto-derived from markdown links inside adopted contexts and skills. See [Migration: Artifact Dependencies via Frontmatter](../docs/migrations/artifact-dependencies-frontmatter.md) for details.

All three `artifacts` keys are required (can be empty lists). The file is validated on `abc sync` and `abc setup`.

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

Skills are tracked at the **directory level** — a skill is a directory with a `SKILL.md` entry point plus optional supporting files (scripts, config, etc.). All files in the directory are synced together.

```yaml
artifacts:
  skills:
    # Canonical form — directory path with trailing slash
    - skills/code-review/
    - skills/generate-tests/
    - skills/api-design/
```

**Note:** Skills must be declared as directories. File-level entries (e.g. `skills/code-review/SKILL.md`) are rejected by `abc sync` with an error.

---

## `ignore`

Suppress skills from appearing in warehouse-scoped status reports (e.g. `abc warehouse status`) and from contribute-path selection. Useful for skills installed by external tools (e.g. OpenSpec) that you don't want to track through the warehouse.

```yaml
ignore:
  skills:
    - "openspec-*"
    - "opsx-*"
```

Patterns use [`fnmatch`](https://docs.python.org/3/library/fnmatch.html) glob syntax and are matched against the skill name (the directory name, without the `skills/` prefix).

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
    - skills/code-review/
    - skills/generate-tests/

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
| `abc setup` | Creates an empty commented template |
| `abc adopt` | Lets you select warehouse artifacts and adds them to `beacon.yaml` |
| `abc sync` | Reads `beacon.yaml`, creates symlinks into the warehouse clone for every matching artifact |
| `abc sync --dry-run` | Reads `beacon.yaml`, prints the symlink operations that would be performed |
| `abc warehouse status` | Reads `beacon.yaml` to scope its git-status/diff report to declared paths |
| `abc warehouse contribute` | Reads `beacon.yaml` to scope the commit's staged paths |

---

## Validation Rules

`abc sync` validates `beacon.yaml` before proceeding. It will error if:

- The file does not exist → run `abc setup`
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
```

The `.gitignore` entries are added automatically when you run `abc warehouse connect` and `abc sync`.

---

## Related Commands

```bash
# Create beacon.yaml
abc setup

# Add artifacts from the warehouse
abc adopt

# Apply the configuration
abc sync

# See uncommitted warehouse edits (scoped by beacon.yaml)
abc warehouse status

# Commit edits back to the warehouse
abc warehouse contribute -m "…" --push
```

---

## Next Steps

- **[Advanced Patterns](./advanced-patterns.md)** — Glob syntax, sync flags, delta workflow
- **[Creating Skills](./creating-skills.md)** — Build and add skills to your warehouse
