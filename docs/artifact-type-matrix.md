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
| **Project-scoped** | 📄 Contexts · 🧠 Knowledge | ⚡ Skills |
| **Global** | — | 🤖 Agents |

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

  The skill directory must be copied into each tool's location for the tool to discover it.

### Agents — global, tool-specific

Agent definitions are sub-agent profiles (e.g. a "code reviewer" agent that can be invoked from any project). They have no dependency on any one project's codebase.

- **Global** because a specialized agent (test writer, PR reviewer) should be available everywhere without per-project configuration. Installing it once in a machine-level directory is enough.
- **Tool-specific** because each tool has its own global agent directory:
  - Claude Code: `~/.claude/agents/`
  - OpenCode: `~/.config/opencode/agents/`

---

## How the Matrix Shapes Command Design

### `abc sync`

`abc sync` handles all four types but applies different logic to each cell:

| Artifact | What sync does |
|---|---|
| Contexts | Copies files into `.agentic-beacon/artifacts/contexts/`; adds path references to `opencode.json` / `AGENTS.md` |
| Knowledge | Copies files into `.agentic-beacon/artifacts/knowledge/`; no automatic wiring (referenced from contexts) |
| Skills | Copies skill directories into `.agentic-beacon/artifacts/skills/`; then installs into each detected tool's live skill and command directories |
| Agents | Reads `agents/` from the warehouse; installs directly into global tool directories; no project artifact copy needed |

The asymmetry between knowledge and skills is intentional: knowledge does not need to be in a tool-specific location because agents read it via a path reference in the context. Skills need to be installed because agents discover them by scanning a directory.

### `abc agents sync`

Because agents are **project-agnostic**, syncing them does not require `beacon.yaml`. Any project with a warehouse connection can run `abc agents sync` to pull the latest agent definitions from the warehouse into the global directories — independently of which knowledge or skills that project has declared.

This command exists separately from `abc sync` precisely because the global install has no project-scoped configuration to gate it.

### `abc delta`

`abc delta` compares local state against the warehouse. The matrix determines what "local" means for each type:

- **Contexts / Knowledge**: compare `.agentic-beacon/artifacts/` against the warehouse source.
- **Skills**: compare the per-tool installed directories against the warehouse source (since the live install is the canonical local copy).
- **Agents (global)**: compare `~/.claude/agents/` and `~/.config/opencode/agents/` against the warehouse. A separate section flags agents found only in the project-local agent directories (`.claude/agents/` or `.opencode/agents/` at the project root) as candidates to promote — because project-local agent files should live in the global directory.

### `abc contribute`

`abc contribute` copies a local artifact back to the warehouse. The matrix determines where the source is found:

- **Contexts / Knowledge**: source is `.agentic-beacon/artifacts/`.
- **Skills**: source is the live tool install directory (the installed copy is what was modified during a session). After contributing, the updated skill is re-propagated to all detected tool directories.
- **Agents**: source is the global agent directory (`~/.claude/agents/` or `~/.config/opencode/agents/`), not a project-local path. An agent that exists only in a project-local directory (ADDED status, never contributed before) is also included — it is contributed as a new warehouse entry.

### `abc install <artifact>`

`abc install` handles a single artifact path and applies the same type-specific logic as `abc sync`:

- `abc install contexts/python.md` — copies and wires into agent config.
- `abc install skills/code-review/` — copies and installs into tool directories.
- `abc install agents/reviewer.md` — installs directly into global agent directories.

---

## Summary

The two-axis model keeps the framework internally consistent: knowing an artifact's scope and tool-specificity tells you exactly where it lives, how it is installed, where `abc delta` looks for it, and where `abc contribute` reads it from. Adding a new artifact type only requires deciding where it sits in the matrix — the rest of the command behavior follows.
