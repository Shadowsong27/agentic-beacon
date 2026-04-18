# Artifact Types

Agentic Beacon organizes warehouse artifacts along two independent axes — **project scope** and **tool specificity** — producing four types. Understanding this matrix explains why each command behaves the way it does.

## The Matrix

|  | Tool-agnostic | Tool-specific |
|---|---|---|
| **Project-scoped** | 📄 Contexts · 🧠 Knowledge | ⚡ Skills |
| **Global** | — | 🤖 Agents |

The bottom-left cell (global + tool-agnostic) is intentionally empty: a globally shared, tool-agnostic artifact would have no natural installation location, which is not a pattern Agentic Beacon supports.

---

## 📄 Contexts — Project-scoped, Tool-agnostic

Contexts are boot instruction files: coding standards, architectural constraints, team conventions. The agent reads them at session start.

**Project-scoped** because the standards relevant to a data pipeline differ from those in a mobile app. Each project controls which contexts it loads via `beacon.yaml`.

**Tool-agnostic** because the content is plain markdown. The wiring mechanism adapts to the tool (`opencode.json` vs. `AGENTS.md`), but the file itself is identical.

**Where they live after sync:**
```
.agentic-beacon/artifacts/contexts/global.md
```

**How they're wired:**

- Claude Code: appended as `@.agentic-beacon/artifacts/contexts/global.md` to `AGENTS.md`
- OpenCode: added as a file reference in `opencode.json`

---

## 🧠 Knowledge — Project-scoped, Tool-agnostic

Knowledge artifacts are atomic reference documents: decisions and their rationale, lessons learned, coding patterns, framework guides, security policies.

**Project-scoped** because a project curates which knowledge is relevant to its domain.

**Tool-agnostic** for the same reason as contexts: plain markdown, referenced by path from contexts.

**Where they live after sync:**
```
.agentic-beacon/artifacts/knowledge/decisions/coding-standards.md
```

Knowledge files are not wired automatically — they're referenced from context files, or the agent fetches them on demand.

---

## ⚡ Skills — Project-scoped, Tool-specific

Skills are reusable procedures available as slash commands during a session. To function they must be physically present in a tool's live skill directory.

**Project-scoped** because a skill often depends on the project's toolchain (e.g., a `run-migrations` skill assumes the project has a migrations setup).

**Tool-specific** because each tool has its own installation path:

| Tool | Skill location | Command location |
|------|---------------|-----------------|
| Claude Code | `.claude/skills/<name>/` | `.claude/commands/<name>.md` |
| OpenCode | `.opencode/skills/<name>/` | `.opencode/command/<name>.md` |

`abc sync` copies each skill directory into both locations when both tools are detected.

**Invoking a skill:**
```
/code-review src/main.py          # Claude Code or OpenCode
```

---

## 🤖 Agents — Global, Tool-specific

Agent definitions are sub-agent profiles — specialized agents that can be invoked from any project (code reviewer, test writer, PR description generator, etc.).

**Global** because a specialized agent should be available everywhere without per-project configuration. Installing it once is enough.

**Tool-specific** because each tool has its own global agent directory:

| Tool | Global agent directory |
|------|----------------------|
| Claude Code | `~/.claude/agents/` |
| OpenCode | `~/.config/opencode/agents/` |

`abc sync` installs agents from the warehouse directly into both directories.

`abc agents sync` can sync agents independently of other artifact types — no `beacon.yaml` required.

---

## How the Matrix Shapes Command Behavior

### `abc sync`

Applies different logic per type:

| Artifact | Sync behavior |
|---|---|
| Contexts | Copy to `.agentic-beacon/artifacts/contexts/`; wire into agent config |
| Knowledge | Copy to `.agentic-beacon/artifacts/knowledge/`; no wiring |
| Skills | Copy to artifacts; install into each detected tool's live directories |
| Agents | Install directly into global tool directories; no project copy |

### `abc delta`

"Local state" is different per type:

- **Contexts / Knowledge** → compare `.agentic-beacon/artifacts/` against warehouse
- **Skills** → compare the per-tool installed directories against warehouse
- **Agents** → compare global directories (`~/.claude/agents/`, `~/.config/opencode/agents/`) against warehouse; also flags project-local agents as promotion candidates

### `abc contribute`

Source depends on where the artifact was modified:

- **Contexts / Knowledge** → source is `.agentic-beacon/artifacts/`
- **Skills** → source is the live tool install directory (the installed copy is what was modified)
- **Agents** → source is the global agent directory; project-local agents are included as new warehouse entries

### `abc install <artifact>`

Applies the same type-specific logic as `abc sync` for a single artifact:

```bash
abc install contexts/python.md        # copies + wires into agent config
abc install skills/code-review/       # copies + installs into tool directories
abc install agents/reviewer.md        # installs into global agent directories
```

---

## Summary

Knowing an artifact's type tells you exactly:

- Where it lives after sync
- How `abc delta` finds it
- Where `abc contribute` reads it from
- Which commands are needed to manage it

The two-axis model keeps the framework internally consistent: the behavior follows directly from position in the matrix.
