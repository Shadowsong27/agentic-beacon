# How It Works

Agentic Beacon is built around two components — the **warehouse** and the **beacon** — and a simple model for distributing agent artifacts.

## The npm Analogy

| npm concept | Agentic Beacon equivalent |
|-------------|--------------------------|
| npm registry | **Warehouse** — your central repository of shared artifacts |
| `package.json` | **`beacon.yaml`** — your project's artifact dependencies |
| `node_modules/` | **`.agentic-beacon/artifacts/`** — local symlink tree |
| `npm install` | **`abc sync`** — resolve, sync, and wire all artifacts |

Like npm, the warehouse is separate from the projects that consume it. Projects declare what they need; the tool resolves dependencies, creates symlinks, and wires artifacts. The artifacts directory is gitignored — regenerated from source on demand.

---

## The Warehouse

A warehouse is a plain git repository. It stores your team's shared agent artifacts in four directories:

```
my-org-warehouse/
├── contexts/       # boot instruction files
├── knowledge/      # decisions, lessons, facts
├── skills/         # reusable agent workflows
├── agents/         # global sub-agent definitions
└── docs/           # warehouse documentation
```

The internal structure of each directory is **entirely yours to define**. No naming conventions are enforced — organize artifacts in whatever way makes sense for your team.

The warehouse lives on a git host (GitHub, GitLab, Bitbucket, etc.) and is shared across your team. Team members clone it locally.

---

## The Beacon

Each project that consumes warehouse artifacts has a `.agentic-beacon/` directory:

```
my-project/
└── .agentic-beacon/
    ├── beacon.yaml       ← committed to git: declares which contexts, skills, and agents this project needs
    ├── config.toml       ← gitignored: local warehouse path
    ├── pending.yaml      ← gitignored: artifacts authored but not yet wired (managed by abc adopt)
    ├── .last-adopt       ← gitignored: timestamp of last successful abc adopt commit
    └── artifacts/        ← gitignored: symlink tree into warehouse
```

`beacon.yaml` declares three types of artifacts:

```yaml
artifacts:
  skills:
    - skills/code-review/
    - skills/generate-tests/

  contexts:
    - contexts/global.md
    - contexts/teams/backend/AGENTS.md

  agents:
    - agents/spec-planner.md
```

`config.toml` stores the local path to the warehouse (e.g. `~/my-org-warehouse`). It is gitignored because warehouse paths vary per machine.

`pending.yaml` records project-wired artifacts (contexts, skills, agents) written to the warehouse by authoring skills that have not yet been wired into `beacon.yaml`. Knowledge files are auto-derived during sync/adopt and are not tracked here. It is absent or `pending: []` when nothing is pending. Use `abc adopt` to accept, reject, or defer each entry. The file is gitignored — it represents per-developer working state. See [Pending & Adoption](pending-and-adoption.md) for the full lifecycle.

`.last-adopt` is a single-line ISO-8601 UTC timestamp recording when `abc adopt` last committed successfully. It enables `abc adopt` to detect hand-edited warehouse files (files modified after `.last-adopt` but not tracked in `pending.yaml`). The file is gitignored.

---

## What `abc sync` Does

`abc sync` runs a multi-phase pipeline:

1. **Read `beacon.yaml`** — loads the declared contexts, skills, and agents
2. **Resolve dependencies** — reads `requires:` frontmatter from each skill's `SKILL.md` and agent dependencies from `agents/agents.yaml` to compute the full set of required artifacts
3. **Auto-derive knowledge** — scans every adopted context and skill for markdown links to `knowledge/` paths and adds them to the sync set
4. **Create symlinks** — creates per-file symlinks under `.agentic-beacon/artifacts/` pointing into the warehouse clone
5. **Wire artifacts** — adds context references to `CLAUDE.md` or `opencode.json`, installs skills into tool directories, wires agents into project-local `.claude/agents/` and `.opencode/agents/`
6. **Prune orphans** — removes symlinks for artifacts no longer referenced

| Artifact type | How it's configured | What sync does |
|---|---|---|
| **Contexts** | Declared in `beacon.yaml` | Symlinks + wiring into agent config |
| **Skills** | Declared in `beacon.yaml` | Symlinks + install into tool directories |
| **Knowledge** | Auto-derived from markdown links in contexts/skills | Symlinks only (referenced from contexts) |
| **Agents** | Declared in `beacon.yaml` | Symlinks + wire into project-local tool directories |

---

## Frontmatter Dependencies

Skills declare their context dependencies in YAML frontmatter. Every skill's `SKILL.md` must include:

```yaml
---
requires:
  contexts:
    - global.md
    - teams/backend/AGENTS.md
---
```

Missing or malformed frontmatter on any adopted skill causes `abc sync` to fail with a hard error. This ensures all required contexts are present before the agent starts.

---

## Knowledge Auto-Derivation

Knowledge files are NOT declared in `beacon.yaml`. When a context or skill contains a markdown link to a `knowledge/` path:

```markdown
See the [Python type hints guide](knowledge/python/type-hints.md) for details.
```

The dependency resolver finds that reference and adds it to the sync set automatically. No manual configuration needed.

---

## Symlink Model

`abc sync` creates **symlinks**, not copies. `.agentic-beacon/artifacts/` is a tree of symlinks pointing into the warehouse clone. This means:

- **One physical file per machine.** No duplicate copies to drift out of sync.
- **Edits go directly to the warehouse.** Editing a symlinked file edits the warehouse working tree.
- **Cross-project visibility.** If two projects share the same artifact, editing it in Project A makes the change visible in Project B immediately.

---

## Tool Detection

`abc sync` auto-detects which AI tools are installed and wires artifacts accordingly:

| Tool | Context wiring | Skill install |
|------|---------------|---------------|
| **Claude Code** | Appends `@path` references to `CLAUDE.md` | Symlinks to `.claude/skills/<name>/` and `.claude/commands/<name>.md` |
| **OpenCode** | Adds file references to `opencode.json` | Symlinks to `.opencode/skills/<name>/` and `.opencode/command/<name>.md` |

If both tools are detected, artifacts are installed for both simultaneously.

---

## The Contribution Loop

The workflow is bidirectional. With symlinks, editing an artifact directly modifies the warehouse working tree. To share improvements:

```
1. abc sync                     ← sync from warehouse (creates symlinks)
2. code with agent              ← agent uses synced artifacts, may improve them
3. abc warehouse status         ← review what changed in the warehouse working tree
4. abc warehouse contribute -m "msg"  ← commit changes and push back
5. teammates sync               ← everyone benefits
```

---

## Git Safety Checks

Before running `abc sync`, Agentic Beacon checks that:

- The warehouse has no uncommitted changes
- The local branch is not behind its remote
- The warehouse is on `main` (not a feature branch)

These checks can be bypassed with `--skip-git-check` if needed. The main-branch check is configurable via `abc warehouse connect --main-branch <name>`.

---

## Next: Artifact Types

Each artifact type has distinct behavior around installation, scope, and contribution. → **[Artifact Types](artifact-types.md)**
