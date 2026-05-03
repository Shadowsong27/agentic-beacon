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

  The skill directory must be present in each tool's location for the tool to discover it. Under the symlink-based sync model, this is achieved by symlinking individual skill files into the project's `.agentic-beacon/artifacts/skills/` tree and wiring each tool's live skill directory via per-tool installation.

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
| Contexts | Creates symlinks at `.agentic-beacon/artifacts/contexts/<path>` pointing into the warehouse clone; adds path references to `opencode.json` / `AGENTS.md` |
| Knowledge | Creates symlinks at `.agentic-beacon/artifacts/knowledge/<path>`; no automatic wiring (referenced from contexts) |
| Skills | Creates symlinks at `.agentic-beacon/artifacts/skills/<path>`; then wires each detected tool's live skill and command directories |
| Agents | Reads `agents/` from the warehouse; installs real files directly into global tool directories (copies, not symlinks — see note below); no project artifact entry created |

The asymmetry between knowledge and skills is intentional: knowledge does not need to be in a tool-specific location because agents read it via a path reference in the context. Skills need to be wired into tool-specific directories because agents discover them by scanning those directories.

**Why agents are still copied, not symlinked:** global agent directories (`~/.claude/agents/`, `~/.config/opencode/agents/`) live **outside** the warehouse tree. Symlinks into those locations would cross the warehouse boundary in a way that would also leak every non-agent warehouse file onto the user's machine-wide agent path. Agents therefore remain file-copy installs tracked by `~/.config/agentic-beacon/sync-state.json`.

### `abc agents sync`

Because agents are **project-agnostic**, syncing them does not require `beacon.yaml`. Any project with a warehouse connection can run `abc agents sync` to pull the latest agent definitions from the warehouse into the global directories — independently of which knowledge or skills that project has declared.

This command exists separately from `abc sync` precisely because the global install has no project-scoped configuration to gate it.

### `abc warehouse status`

`abc warehouse status` reports uncommitted and unpushed state of the warehouse clone, scoped by the current project's `beacon.yaml`. Because symlinks collapse project-vs-warehouse duplication into a single physical file, there is no project-vs-warehouse delta to compute — the question "what did I change in this project?" becomes "what's unstaged/uncommitted in the warehouse?".

- **Contexts / Knowledge / Skills**: runs `git status` / `git diff` in the warehouse working tree, filtered to paths matched by `beacon.yaml`.
- **Agents (global)**: NOT surfaced by `abc warehouse status` — agents live outside the warehouse tree. Divergence between global agent directories and the warehouse is a separate concern handled by `abc install` conflict detection (see [`install-flags`](../openspec/specs/install-flags/spec.md) and [`sync-soft-block`](../openspec/specs/sync-soft-block/spec.md)).

### `abc warehouse contribute`

`abc warehouse contribute` commits modifications inside the warehouse clone. The matrix determines what is committed:

- **Contexts / Knowledge / Skills**: any warehouse working-tree modifications to paths matched by the project's `beacon.yaml`. The source is the warehouse file itself — editing via a project symlink is writing to the warehouse.
- **Agents**: NOT auto-contributed by this command. Agents live outside the warehouse tree. To contribute an agent edit, edit the file inside the warehouse clone directly (e.g. `~/team-warehouse/agents/reviewer.md`) and commit it.

### `abc install <artifact>`

`abc install` handles a single artifact path and applies the same type-specific logic as `abc sync`:

- `abc install contexts/python.md` — creates symlink and wires into agent config.
- `abc install skills/code-review/` — creates symlinks and wires each detected tool directory.
- `abc install agents/reviewer.md` — installs real file directly into global agent directories (respects `--force` / `--preserve`).

---

## Summary

The two-axis model keeps the framework internally consistent: knowing an artifact's scope and tool-specificity tells you exactly where it lives, how it is installed, where `abc warehouse status` looks for it, and what `abc warehouse contribute` commits. Adding a new artifact type only requires deciding where it sits in the matrix — the rest of the command behavior follows.
