# How It Works

Agentic Beacon is built around two components — the **warehouse** and the **beacon** — and a simple model for distributing agent artifacts.

## The npm Analogy

| npm concept | Agentic Beacon equivalent |
|-------------|--------------------------|
| npm registry | **Warehouse** — your central repository of shared artifacts |
| `package.json` | **`beacon.yaml`** — your project's artifact dependencies |
| `node_modules/` | **`.agentic-beacon/artifacts/`** — local downloaded snapshot |
| `npm install` | **`abc sync`** — fetch and wire all artifacts |

Like npm, the warehouse is separate from the projects that consume it. Projects declare what they need; the tool does the copying and wiring. The artifacts directory is gitignored — regenerated from source on demand.

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
    ├── beacon.yaml       ← committed to git: declares which artifacts this project needs
    ├── config.toml       ← gitignored: local warehouse path
    └── artifacts/        ← gitignored: downloaded artifact snapshot
```

`beacon.yaml` is the per-project manifest. It lists paths and glob patterns for the warehouse artifacts this project wants:

```yaml
artifacts:
  knowledge:
    - knowledge/python/**/*.md
    - knowledge/decisions/coding-standards.md

  skills:
    - skills/code-review/
    - skills/generate-tests/

  contexts:
    - contexts/global.md
    - contexts/teams/backend/AGENTS.md
```

`config.toml` stores the local path to the warehouse (e.g. `~/my-org-warehouse`). It is gitignored because warehouse paths vary per machine.

---

## What `abc sync` Does

`abc sync` reads `beacon.yaml`, finds the warehouse via `config.toml`, and does the full job in one step:

| Artifact type | What sync does |
|---|---|
| **Knowledge** | Copies files into `.agentic-beacon/artifacts/knowledge/`; no further wiring (referenced from contexts) |
| **Contexts** | Copies files into `.agentic-beacon/artifacts/contexts/`; adds path references to `opencode.json` or `AGENTS.md` |
| **Skills** | Copies skill directories into `.agentic-beacon/artifacts/skills/`; installs into each detected tool's live skill + command directories |
| **Agents** | Reads `agents/` from the warehouse; installs directly into global tool directories (`~/.claude/agents/`, `~/.config/opencode/agents/`) |

No live connection to the warehouse is needed during coding sessions. The agent reads from local files.

---

## Tool Detection

`abc sync` auto-detects which AI tools are installed and wires artifacts accordingly:

| Tool | Context wiring | Skill install |
|------|---------------|---------------|
| **Claude Code** | Appends `@path` references to `AGENTS.md` | Copies to `.claude/skills/<name>/` and `.claude/commands/<name>.md` |
| **OpenCode** | Adds file references to `opencode.json` | Copies to `.opencode/skills/<name>/` and `.opencode/command/<name>.md` |

If both tools are detected, artifacts are installed for both simultaneously.

---

## The Contribution Loop

The workflow is bidirectional. When a coding session produces improvements to an artifact, `abc contribute` copies it back to the warehouse:

```
1. abc sync          ← pull from warehouse
2. code with agent   ← agent uses synced artifacts, may improve them
3. abc delta         ← review what changed locally
4. abc contribute    ← push improvements back to warehouse (creates a PR)
5. teammates sync    ← everyone benefits
```

This closes the feedback loop: improvements flow from the warehouse to projects, and from projects back to the warehouse.

---

## Git Safety Checks

Before running `abc sync` or `abc contribute`, Agentic Beacon checks that:

- The warehouse has no uncommitted changes
- The local branch is not behind its remote
- The warehouse is on `main` (not a feature branch)

These checks can be bypassed with `--skip-git-check` if needed.

---

## Next: Artifact Types

Each artifact type has distinct behavior around installation, scope, and contribution. → **[Artifact Types](artifact-types.md)**
