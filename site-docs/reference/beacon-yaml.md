# beacon.yaml Reference

`beacon.yaml` is the configuration file that declares which artifacts your project pulls from the warehouse. It lives at `.agentic-beacon/beacon.yaml` and must be committed to git.

## File Location

```
my-project/
└── .agentic-beacon/
    ├── beacon.yaml     # ✅ Commit this
    ├── config.toml     # ❌ Gitignored (local warehouse path)
    └── artifacts/      # ❌ Gitignored (symlink tree into warehouse)
```

---

## Full Schema

```yaml
artifacts:
  skills:
    - skills/<name>/      # directory-level entry (canonical form)

  contexts:
    - <pattern-or-path>

  agents:
    - agents/<name>.md    # per-project agent declaration
```

Three artifact types are declared in `beacon.yaml`:

- **Skills** — declared at directory level (trailing `/`), must have `requires: { contexts: [...] }` frontmatter in their `SKILL.md`
- **Contexts** — file or glob patterns, wired into agent config on sync
- **Agents** — declared per-project; `abc sync` wires them into project-local `.claude/agents/` and `.opencode/agents/`

**Knowledge files are NOT declared in beacon.yaml.** They are auto-derived from markdown links (`[text](knowledge/...)`) found in adopted contexts and skills. The dependency resolver scans all adopted artifacts and syncs every referenced knowledge file automatically.

---

## `artifacts.agents`

Agents are declared per-project in `beacon.yaml`. `abc sync` wires them into project-local tool directories.

```yaml
artifacts:
  agents:
    - agents/spec-planner.md
    - agents/registra-developer.md
```

!!! info "Agent Dependency Manifest"
    Agent dependencies are declared in `agents/agents.yaml` (not in agent frontmatter). `abc sync`
    loads this manifest to validate that required skills are adopted. If a declared agent requires
    a skill not in `beacon.yaml.artifacts.skills`, `abc sync` prompts:
    ```
    Agent '<name>' (declared in beacon.yaml) requires skill '<skill>',
    which is not declared in this project.
    Add 'skills/<skill>/' to beacon.yaml and sync it? [y/N]
    ```
    Answer Y to auto-append the skill and proceed, or pass `--yes` for non-interactive acceptance.

---

## `artifacts.skills`

Skills are tracked at the **directory level** — a skill is a directory with a `SKILL.md` entry point plus optional supporting files.

```yaml
artifacts:
  skills:
    - skills/code-review/
    - skills/generate-tests/
    - skills/api-design/
```

!!! info "Required: Frontmatter Dependencies"
    Every skill's `SKILL.md` must include a YAML frontmatter block declaring which contexts it needs:

    ```yaml
    ---
    requires:
      contexts:
        - global
        - teams/backend/AGENTS
    ---
    ```

    Entries are **bare context names** (without the `.md` extension) — the resolver appends `.md` and looks under `<warehouse>/contexts/<name>.md`. Using `.md`-suffixed names would resolve to `<name>.md.md` and fail.

    Missing or malformed frontmatter on any adopted skill causes `abc sync` to fail with a hard error.

!!! warning
    Skills must be declared as directories. File-level entries (e.g. `skills/code-review/SKILL.md`) are rejected by `abc sync` with an error.

---

## `artifacts.contexts`

Contexts are boot instruction files that load when the agent starts.

```yaml
artifacts:
  contexts:
    # Global org context
    - contexts/global.md

    # Team context
    - contexts/teams/backend/AGENTS.md

    # Project context
    - contexts/projects/my-service/AGENTS.md
```

**How contexts are wired:**

- **Claude Code** — path appended to `CLAUDE.md` as `@.agentic-beacon/artifacts/contexts/...`
- **OpenCode** — path added as a file reference in `opencode.json`

---

## How Knowledge Works

Knowledge is NOT declared in `beacon.yaml`. There is no `artifacts.knowledge` key. Knowledge files are:

1. **Auto-derived** — `abc sync` scans all adopted contexts and skills for markdown links to `knowledge/` paths
2. **Synced automatically** — referenced knowledge files are symlinked into `.agentic-beacon/artifacts/knowledge/`
3. **Pruned automatically** — knowledge files no longer referenced by any adopted artifact are removed as orphans

**Example:** If your adopted context contains:
```markdown
See the [Python standards](knowledge/python/standards.md) for details.
```

Then `knowledge/python/standards.md` is automatically synced — no manual configuration needed.

---

## Path Rules

- Paths are relative to the warehouse root
- Only files are matched (not directories, except skills which are directory-level)
- Patterns with `*`, `**`, or `?` are expanded as globs
- Unmatched patterns warn but do not cause errors

---

## Complete Example

```yaml
# .agentic-beacon/beacon.yaml

artifacts:
  skills:
    - skills/code-review/
    - skills/generate-tests/

  contexts:
    - contexts/global.md
    - contexts/teams/frontend/AGENTS.md

  agents:
    - agents/spec-planner.md
```

Knowledge files referenced by those contexts and skills will be auto-derived and synced automatically.

---

## Minimal Example

```yaml
artifacts:
  skills: []
  contexts:
    - contexts/global.md
  agents: []
```

An empty `skills` list is valid — skills simply won't be synced.

---

## File Lifecycle

| Command | Effect on `beacon.yaml` |
|---------|------------------------|
| `abc setup` | Creates a template you can edit |
| `abc adopt` | Appends selected artifact paths |
| `abc sync` | Reads `beacon.yaml`, resolves dependencies via frontmatter, derives knowledge, creates symlinks |
| `abc warehouse status` | Reads `beacon.yaml` to determine which warehouse files to check |

---

## Validation Rules

`abc sync` validates `beacon.yaml` before proceeding. It errors if:

- The file does not exist → run `abc setup`
- The YAML is malformed (syntax error)
- The `artifacts` key is missing
- Any of `skills`, `contexts`, or `agents` is not a list
- A skill entry is a file path rather than a directory path
- Any adopted skill is missing required `requires:` frontmatter
- Any required context does not exist in the warehouse

Warnings (not errors) for:

- Patterns that match no files in the warehouse
- Knowledge files referenced by links but not found in the warehouse

---

## What Gets Committed

```bash
# Commit
git add .agentic-beacon/beacon.yaml

# Already gitignored by abc
# .agentic-beacon/config.toml
# .agentic-beacon/artifacts/
```

The `.gitignore` entries are added automatically when you run `abc warehouse connect` and `abc sync`.

---

## Related Commands

```bash
# Create beacon.yaml
abc setup

# Populate it interactively
abc adopt

# Apply the configuration
abc sync

# Preview warehouse working tree changes
abc warehouse status

# Check what's configured and synced
abc status
```
