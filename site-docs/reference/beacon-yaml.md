# beacon.yaml Reference

`beacon.yaml` is the configuration file that declares which artifacts your project pulls from the warehouse. It lives at `.agentic-beacon/beacon.yaml` and must be committed to git.

## File Location

```
my-project/
└── .agentic-beacon/
    ├── beacon.yaml     # ✅ Commit this
    ├── config.toml     # ❌ Gitignored (local warehouse path)
    └── artifacts/      # ❌ Gitignored (downloaded files)
```

---

## Full Schema

```yaml
artifacts:
  knowledge:
    - <pattern-or-path>

  skills:
    - skills/<name>/      # directory-level entry (canonical form)

  contexts:
    - <pattern-or-path>

# Optional — suppress skills from abc delta and abc contribute
ignore:
  skills:
    - "openspec-*"        # fnmatch glob patterns
```

All three `artifacts` keys are required (can be empty lists). The file is validated on `abc sync` and `abc setup`.

---

## `artifacts.knowledge`

Knowledge artifacts are markdown files — best practices, standards, framework guides, team decisions.

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

---

## `artifacts.skills`

Skills are tracked at the **directory level** — a skill is a directory with a `SKILL.md` entry point plus optional supporting files.

```yaml
artifacts:
  skills:
    # Canonical form — directory path
    - skills/code-review/
    - skills/generate-tests/
    - skills/api-design/
```

!!! warning
    Skills must be declared as directories. File-level entries (e.g. `skills/code-review/SKILL.md`) are rejected by `abc sync` with an error.

---

## `artifacts.contexts`

Contexts are `AGENTS.md`-style files that load as boot context when the agent starts.

```yaml
artifacts:
  contexts:
    # Global org context
    - contexts/global.md

    # Team context
    - contexts/teams/backend/AGENTS.md

    # Multiple contexts — all are loaded (they stack, not override)
    - contexts/teams/backend/AGENTS.md
    - contexts/projects/my-service/AGENTS.md
```

**How contexts are wired:**

- **Claude Code** — path appended to `AGENTS.md` as `@.agentic-beacon/artifacts/contexts/...`
- **OpenCode** — path added as a file reference in `opencode.json`

---

## `ignore`

Suppress specific skills from appearing in `abc delta` and `abc contribute`. Useful for skills installed by external tools (e.g., OpenSpec) that you don't want to track through the warehouse.

```yaml
ignore:
  skills:
    - "openspec-*"
    - "opsx-*"
```

Patterns use [`fnmatch`](https://docs.python.org/3/library/fnmatch.html) syntax, matched against the skill directory name (without the `skills/` prefix).

---

## Complete Example

```yaml
# .agentic-beacon/beacon.yaml

artifacts:
  knowledge:
    # Python standards
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

ignore:
  skills:
    - "opsx-*"
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
| `abc setup --agent-assisted` | Creates template + `warehouse-catalog.md` for AI assistance |
| `abc adopt` | Appends selected artifact paths |
| `abc install <artifact>` | Adds one artifact path |
| `abc sync` | Reads `beacon.yaml`, copies and wires all matching artifacts |
| `abc delta` | Reads `beacon.yaml` to determine which files to compare |

---

## Validation Rules

`abc sync` validates `beacon.yaml` before proceeding. It errors if:

- The file does not exist → run `abc setup --manual`
- The YAML is malformed (syntax error)
- The `artifacts` key is missing
- Any of `knowledge`, `skills`, or `contexts` is not a list
- A skill entry is a file path rather than a directory path

Warnings (not errors) for:

- Patterns that match no files in the warehouse

---

## What Gets Committed

```bash
# Commit
git add .agentic-beacon/beacon.yaml

# Already gitignored by abc
# .agentic-beacon/config.toml
# .agentic-beacon/artifacts/
# .agentic-beacon/warehouse-catalog.md
```

The `.gitignore` entries are added automatically when you run `abc warehouse connect` and `abc sync`.

---

## Related Commands

```bash
# Create beacon.yaml
abc setup --manual

# Populate it interactively
abc adopt

# Apply the configuration
abc sync

# Preview differences between local and warehouse
abc delta

# Check what's configured and synced
abc status
```
