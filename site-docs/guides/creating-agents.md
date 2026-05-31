# Creating an Agent

An **agent** is a distinct AI persona with its own scoped responsibility, instructions, and (optionally) a set of skills it can invoke. In Agentic Beacon, agents live as individual markdown files under `<warehouse>/agents/` and are registered in `<warehouse>/agents/agents.yaml`.

There is **no bundled skill** for authoring an agent — you write the markdown directly. Either by hand or by asking your current agent to author one for you. Both are fine.

For links from an agent to any other warehouse artifact, use the
[canonical link convention](canonical-links.md). This is mandatory for agent-to-partial
references because agents are wired outside `.agentic-beacon/artifacts/`.

> Why an agent instead of a skill? Skills are best for cognitive or low-state procedures (a code review checklist, a templated transformation). Agents are better when the work has multiple phases, decision points, or wants its own context and tool surface. See [Skills design — Workflow Skills Probably Belong to Agents](../design/skills.md#workflow-skills-probably-belong-to-agents) for the line of reasoning.

---

## File Layout

```
agents/
├── README.md
├── agents.yaml          # Required: agent dependency manifest
├── code-reviewer.md     # An agent
└── spec-planner.md      # Another agent
```

Each `<name>.md` must have a matching top-level key in `agents.yaml`. Both directions are enforced by `abc warehouse lint`.

---

## Authoring the Agent File

### Frontmatter

```markdown
---
name: code-reviewer
description: Reviews PRs against team standards. Use for end-to-end PR review before merge.
---
```

| Field | Required | Notes |
|---|---|---|
| `name` | yes | Becomes the agent's invocation name |
| `description` | yes | One sentence; tool surfaces use this to pick the right agent for a task |

> **Important:** do not put `requires:` in agent frontmatter. Skill dependencies belong in `agents.yaml` (see below). `abc warehouse lint` hard-errors if `requires:` appears here.

### Body

After the frontmatter, write the agent's instructions. Treat it the way you'd write a system prompt: scope, persona, tools, expected behaviour. Be explicit about decision points and what the agent should escalate.

```markdown
---
name: code-reviewer
description: Reviews PRs against team standards. Use for end-to-end PR review before merge.
---

# Code Reviewer

You review pull requests for correctness, style, test coverage, and security.

## Scope
- One PR at a time, end-to-end.
- You produce a structured review with three sections: Blockers, Suggestions, Notes.
- You do not merge or close PRs — leave that to the human.

## Process
1. Read all changed files in full before commenting.
2. ...

## Tools You'll Use
- `/code-review` skill for the per-file checklist
- The shared `python-standards.md` context for language conventions
```

---

## Registering the Agent in `agents.yaml`

Every agent file needs an entry in `agents/agents.yaml` — even if it has no skill dependencies.

```yaml
# agents/agents.yaml

code-reviewer:
  skills:
    - code-review
    - generate-tests

spec-planner:
  skills:
    - opsx-propose
    - opsx-enhance

pipeline-developer:
  skills: []          # an agent with no skill dependencies still needs an entry
```

Rules:

- Top-level key must equal the stem of an `agents/<key>.md` file.
- `skills:` is a list of skill directory names (no `skills/` prefix, no trailing `/`).
- Every listed skill must exist in the warehouse and must be adopted by any project that uses this agent — `abc sync` errors otherwise.
- `contexts:` is **not** allowed at the agent entry level.

---

## Declaring the Agent in a Project's `beacon.yaml`

Agents are **project-scoped**. Each project that wants an agent declares it explicitly:

```yaml
artifacts:
  agents:
    - agents/code-reviewer.md
```

After `abc sync` (or `abc adopt`), the agent is wired into the project's tool directories:

- Claude Code: `.claude/agents/code-reviewer.md` (symlink)
- OpenCode: `.opencode/agents/code-reviewer.md` (symlink)

Both directories are gitignored — they're per-machine state. The shared source of truth is `beacon.yaml.artifacts.agents`.

> See [Artifact Types — Agents](../concepts/artifact-types.md) for the rationale behind per-project agent wiring.

---

## Sharing Fragments Between Agents — `agent-partials/`

When several agents share a long checklist, decision table, or boilerplate block, extract it into a fragment under `agent-partials/` and reference it from each agent's markdown via a canonical link. Beacon mirrors partials into `.agentic-beacon/artifacts/agent-partials/` when at least one agent is declared, but it does not wire them into `.claude/agents/` or `.opencode/agents/`.

```
agents/
├── agents.yaml
├── code-reviewer.md
└── spec-planner.md

agent-partials/
└── deep-review-checklist.md
```

Inside an agent file:

```markdown
For the full per-file checklist, see [deep review checklist](.agentic-beacon/artifacts/agent-partials/deep-review-checklist.md).
```

**Convention rules:**

- Files under `agent-partials/` are **fragments, not agents.** They do not need entries in `agents.yaml` and are not listed by `abc warehouse list agents`.
- When any agent is declared in a project's `beacon.yaml`, every file under `agent-partials/` is mirrored into `.agentic-beacon/artifacts/agent-partials/`.
- Agents must point at partials via canonical `.agentic-beacon/artifacts/agent-partials/...` links, not relative links.

> Partials live outside the `agents/` tree so they cannot be mistaken for standalone agents by discovery or tool wiring.

---

## Two Authoring Paths

Just like skills, you can take either path:

**Direct edit / by hand:** the simplest path for a small agent. Write the markdown, register in `agents.yaml`, add to `beacon.yaml`, sync.

**Ask your agent to write one:** describe the responsibility and tool surface in conversation. Your agent inspects existing agents in `<warehouse>/agents/` for shape, writes the new `.md`, updates `agents.yaml`, and (if you ask) appends a pending entry so `abc adopt` can wire it for you.

The second path is what you reach for when designing the agent's behaviour is the harder part of the work, and you want to iterate on the prose in conversation.

---

## When You're Done

Commit the new agent through [`/contribute-warehouse`](contributing-back.md) like any other warehouse change. The skill's lint gate runs `abc warehouse lint`, which checks both that the agent file has the required frontmatter and that the bidirectional `agents.yaml` correspondence holds.

---

## See Also

- [Creating Skills](creating-skills.md) — the procedural artifact most often paired with an agent
- [Creating Knowledge and Contexts](creating-knowledge-and-contexts.md) — what an agent reads on session start
- [Skills design — Workflow Skills Probably Belong to Agents](../design/skills.md#workflow-skills-probably-belong-to-agents) — when to reach for an agent over a skill
- [Artifact Types](../concepts/artifact-types.md) — how agents fit in the wider artifact matrix
