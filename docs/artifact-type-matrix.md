# Artifact Type Matrix

How the four warehouse artifact types differ by scope and tool-specificity — and how those differences drive the design of every `abc` command.

**Last Updated:** 2026-04-12

---

## The Two Axes

Every artifact in a warehouse can be described by two independent questions:

**1. Project scope** — Does this artifact belong to one project, or is it useful across all projects on a machine?

**2. Tool specificity** — Is this artifact consumed in a way that is identical regardless of which AI tool reads it, or does it need to be installed in a tool-specific location to function?

Those two questions produce four cells:

|  | Tool-agnostic | Tool-specific |
|---|---|---|
| **Project-scoped** | 📄 Contexts · 🧠 Knowledge | ⚡ Skills · 🤖 Agents |
| **Global** | — | — |

The bottom-left cell (global + tool-agnostic) is intentionally empty: a globally shared, tool-agnostic artifact would be a system-wide context file with no natural home, which is not a pattern Agentic Beacon supports.

---

## Why Each Artifact Falls Where It Does

### Contexts — project-scoped, tool-agnostic

Contexts are boot instructions: coding standards, architectural constraints, team conventions. They are consumed by being *referenced* in a config file that the agent reads at session start (`opencode.json`, `AGENTS.md`, etc.).

- **Project-scoped** because the standards relevant to a data pipeline project differ from those in a mobile app. Each project controls which contexts it loads.
- **Tool-agnostic** because the content is plain markdown. The reference mechanism (an entry in `opencode.json` vs. an `@include` in `AGENTS.md`) adapts to the tool, but the file itself does not change.

### Knowledge — project-scoped, tool-agnostic

Knowledge files (decisions, lessons, facts) are atomic reference documents. They exist to be pointed at from a context file or fetched on demand.

- **Project-scoped** because a project curates which knowledge is relevant to its domain.
- **Tool-agnostic** for the same reason as contexts: plain markdown files, referenced by path.

### Skills — project-scoped, tool-specific

Skills are reusable procedures available as slash commands during a session. To function they must be physically present in a tool's live skill directory — the agent discovers them there at runtime.

- **Project-scoped** because a skill only makes sense when its project dependencies are present (e.g. a `run-migrations` skill assumes the project has a migrations setup).
- **Tool-specific** because each tool has its own installation path:
  - OpenCode: `.opencode/skills/<name>/` and `.opencode/command/<name>.md`
  - Claude Code: `.claude/skills/<name>/` and `.claude/commands/<name>.md`

  The skill directory must be present in each tool's location for the tool to discover it. Under the symlink-based sync model, this is achieved by symlinking individual skill files into the project's `.agentic-beacon/artifacts/skills/` tree and wiring each tool's live skill directory via per-tool installation.

### Agents — project-scoped, tool-specific

Agent definitions are sub-agent profiles (e.g. a "code reviewer" agent that can be invoked from the current project). They have no dependency on any one project's codebase.

- **Project-scoped** because agents are declared per-project in `beacon.yaml.artifacts.agents`.
- **Tool-specific** because each tool has its own project-local agent directory:
  - Claude Code: `.claude/agents/`
  - OpenCode: `.opencode/agents/`

---

## How the Matrix Shapes Command Design

### `abc sync`

`abc sync` handles all four types but applies different logic to each cell:

| Artifact | What sync does |
|---|---|
| Contexts | Creates symlinks at `.agentic-beacon/artifacts/contexts/<path>` pointing into the warehouse clone; adds path references to `opencode.json` / `AGENTS.md` |
| Knowledge | Creates symlinks at `.agentic-beacon/artifacts/knowledge/<path>`; no automatic wiring (referenced from contexts) |
| Skills | Creates symlinks at `.agentic-beacon/artifacts/skills/<path>`; then wires each detected tool's live skill and command directories |
| Agents | Reads `agents/` from the warehouse; creates artifact symlinks at `.agentic-beacon/artifacts/agents/<name>.md` pointing into the warehouse, then per-tool symlinks at project-local `.claude/agents/<name>.md` and `.opencode/agents/<name>.md` pointing at those artifact files |

The asymmetry between knowledge and skills is intentional: knowledge does not need to be in a tool-specific location because agents read it via a path reference in the context. Skills need to be wired into tool-specific directories because agents discover them by scanning those directories.

Agents follow a **two-hop symlink** model: the per-tool symlinks at `.claude/agents/<name>.md` and `.opencode/agents/<name>.md` point at the artifact-layer symlink under `.agentic-beacon/artifacts/agents/<name>.md`, which in turn points at the warehouse file. This indirection keeps `abc list / status / contribute` consistent across artifact types — all four cells route through `.agentic-beacon/artifacts/`.

### `abc warehouse status`

`abc warehouse status` reports uncommitted and unpushed state of the warehouse clone, scoped by the current project's `beacon.yaml`. Because symlinks collapse project-vs-warehouse duplication into a single physical file, there is no project-vs-warehouse delta to compute — the question "what did I change in this project?" becomes "what's unstaged/uncommitted in the warehouse?".

- **Contexts / Knowledge / Skills**: runs `git status` / `git diff` in the warehouse working tree, filtered to paths matched by `beacon.yaml`.
- **Agents**: surfaced by `abc warehouse status` filtering when declared in `beacon.yaml`; editing via a project symlink writes to the warehouse working tree.

### `abc warehouse contribute`

`abc warehouse contribute` commits modifications inside the warehouse clone. The matrix determines what is committed:

- **Contexts / Knowledge / Skills**: any warehouse working-tree modifications to paths matched by the project's `beacon.yaml`. The source is the warehouse file itself — editing via a project symlink is writing to the warehouse.
- **Agents**: auto-contributed when declared in `beacon.yaml`; editing via a project symlink is writing to the warehouse.

---

## Summary

The two-axis model keeps the framework internally consistent: knowing an artifact's scope and tool-specificity tells you exactly where it lives, how it is installed, where `abc warehouse status` looks for it, and what `abc warehouse contribute` commits. Adding a new artifact type only requires deciding where it sits in the matrix — the rest of the command behavior follows.
