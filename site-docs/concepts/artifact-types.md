# Artifact Types

Agentic Beacon organizes warehouse artifacts along two independent axes — **project scope** and **tool specificity** — producing four types. Understanding this matrix explains why each command behaves the way it does.

## The Matrix

|  | Tool-agnostic | Tool-specific |
|---|---|---|
| **Project-scoped** | 📄 Contexts · 🧠 Knowledge · 🤖 Agents | ⚡ Skills |
| **Global** | — | — |

The bottom-left cell (global + tool-agnostic) is intentionally empty: a globally shared, tool-agnostic artifact would have no natural installation location, which is not a pattern Agentic Beacon supports.

---

## 📄 Contexts — Project-scoped, Tool-agnostic

Contexts are boot instruction files: coding standards, architectural constraints, team conventions. The agent reads them at session start.

**Project-scoped** because the standards relevant to a data pipeline differ from those in a mobile app. Each project controls which contexts it loads via `beacon.yaml`.

**Tool-agnostic** because the content is plain markdown. The wiring mechanism adapts to the tool (`opencode.json` vs. `CLAUDE.md`), but the file itself is identical.

**Declared in `beacon.yaml`:**
```yaml
contexts:
  - contexts/global.md
  - contexts/teams/backend/AGENTS.md
```

**Where they live after sync:**
```
.agentic-beacon/artifacts/contexts/global.md  →  symlink to warehouse
```

**How they're wired:**
- Claude Code: appended as `@.agentic-beacon/artifacts/contexts/global.md` to `CLAUDE.md`
- OpenCode: added as a file reference in `opencode.json`

---

## 🧠 Knowledge — Project-scoped, Tool-agnostic

Knowledge artifacts are atomic reference documents: decisions and their rationale, lessons learned, coding patterns, framework guides.

**Project-scoped** because each project's contexts reference different knowledge files.

**Tool-agnostic** — plain markdown, referenced by path from contexts and skills.

**NOT declared in `beacon.yaml`.** Knowledge files are auto-derived from markdown links in adopted contexts and skills. When a context says:

```markdown
See the [Python type hints guide](knowledge/python/type-hints.md).
```

The dependency resolver finds `knowledge/python/type-hints.md` and syncs it automatically. No manual configuration needed.

**Where they live after sync:**
```
.agentic-beacon/artifacts/knowledge/decisions/coding-standards.md  →  symlink to warehouse
```

---

## ⚡ Skills — Project-scoped, Tool-specific

Skills are reusable procedures available as slash commands during a session. To function they must be physically present in a tool's live skill directory.

**Project-scoped** because a skill often depends on the project's toolchain (e.g., a `run-migrations` skill assumes the project has a migrations setup).

**Tool-specific** because each tool has its own installation path:

| Tool | Skill location | Command location |
|------|---------------|-----------------|
| Claude Code | `.claude/skills/<name>/` | `.claude/commands/<name>.md` |
| OpenCode | `.opencode/skills/<name>/` | `.opencode/command/<name>.md` |

**Declared in `beacon.yaml` as directory-level entries:**
```yaml
skills:
  - skills/code-review/
  - skills/generate-tests/
```

**Must include frontmatter `requires:` in `SKILL.md`:**
```yaml
---
requires:
  contexts:
    - global.md
    - teams/backend/AGENTS.md
---
```

Missing frontmatter causes sync to fail with a hard error — all required contexts must be available.

---

## 🤖 Agents — Project-scoped, Tool-specific

Agent definitions are sub-agent profiles — specialized agents that can be invoked from any project (code reviewer, test writer, PR description generator, etc.).

**Project-scoped** because agents are declared per-project in `beacon.yaml.artifacts.agents`.

**Tool-specific** because each tool has its own project-local agent directory. Declared agents are symlinked into:

| Tool | Project-local agent directory |
|------|------------------------------|
| Claude Code | `.claude/agents/` (inside the project root) |
| OpenCode | `.opencode/agents/` (inside the project root) |

Agent symlinks are project-scoped, so each project controls which agents are available without sharing state across projects on the same machine.

**Declared in `beacon.yaml`:**
```yaml
agents:
  - agents/code-reviewer.md
  - agents/spec-planner.md
```

`abc sync` wires declared agents into the project-local tool directories. Use `abc adopt` to browse and select agents interactively.

---

## How the Matrix Shapes Command Behavior

### `abc sync`

Applies different logic per type:

| Artifact | Sync behavior |
|---|---|
| Contexts | Symlink to `.agentic-beacon/artifacts/contexts/`; wire into agent config |
| Skills | Symlink to artifacts; install into each detected tool's live directories |
| Knowledge | Auto-derived from markdown links; symlink to `.agentic-beacon/artifacts/knowledge/` |
| Agents | Symlink to `.agentic-beacon/artifacts/agents/`; wire into project-local `.claude/agents/` and `.opencode/agents/` |

### `abc warehouse status`

Shows modifications to warehouse files tracked by resolved artifacts. With symlinks, editing an artifact directly modifies the warehouse working tree:

```bash
abc warehouse status                                   # summary of modified files
abc warehouse status knowledge/python/type-hints.md    # diff for a single file
```

### `abc warehouse contribute`

Commits changes in the warehouse working tree. Since symlinks write directly to the warehouse, you edit an artifact, then commit:

```bash
abc warehouse contribute -m "Update type hints guide with Python 3.12+ patterns"
```

---

## Summary

Knowing an artifact's type tells you exactly:

- Where it lives after sync
- How it's declared (or auto-derived)
- How it's wired or installed
- Which commands manage it

The two-axis model keeps the framework internally consistent: the behavior follows directly from position in the matrix.
