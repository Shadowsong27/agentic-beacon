# Creating Skills

A skill is a packaged, reusable workflow that an agent can invoke as a slash command. In Agentic Beacon, a skill is a directory under `<warehouse>/skills/<name>/` containing a `SKILL.md` entry point (with required frontmatter) plus optional supporting files.

For cross-artifact references from a skill to a context, knowledge file, agent partial,
or another warehouse artifact, use the [canonical link convention](canonical-links.md).
Only skill-local bundled files stay relative to the skill directory.

There are two equally valid ways to author one. Pick the path that fits the situation.

---

## Path 1 — Use `/record-skill`

The `/record-skill` [bundled skill](../concepts/bundled-skills.md) is the structured path. It prompts you for the skill name, description, and initial process steps, then writes a correctly-shaped `SKILL.md` into the warehouse and appends a `pending.yaml` entry so the new skill is picked up by `abc adopt`.

From an OpenCode or Claude Code session in a connected project:

```
/record-skill
```

Use this when:

- You already know roughly what the skill should do — the conversation is about capturing it, not designing it.
- You want the frontmatter and directory layout to come out correct without thinking about it.
- You want the wiring half (`pending.yaml` → `abc adopt`) handled for you.

After the skill is written, run `abc adopt` to wire it into the project, then commit via [`/contribute-warehouse`](contributing-back.md) when you're ready to share it.

---

## Path 2 — Ask Your Agent to Author One

You can also just tell your agent: *"Write a `code-review` skill that does X, Y, Z. Put it in the warehouse."* The agent reads the existing skills in `<warehouse>/skills/` for shape, writes a new `SKILL.md` with frontmatter, and saves it.

Use this when:

- The skill needs design work — the conversation is about figuring out what the skill should do, not just transcribing it.
- You want to iterate on the SKILL.md text directly as you go.
- You want supporting files (`templates/`, `examples/`, `scripts/`) authored alongside the SKILL.md in one go.

This path skips `pending.yaml` — you'll need to add the skill to `beacon.yaml` yourself (or via `abc adopt` after manually appending a pending entry). It trades a small amount of bookkeeping for full creative control.

---

## Either Way, the Output Looks the Same

A skill on disk:

```
skills/
└── code-review/
    ├── SKILL.md           # Required — main skill definition
    ├── checklist.md       # Optional — supporting reference
    └── examples/
        └── example-pr.md  # Optional — examples for the agent
```

The skill name is the directory name. In `beacon.yaml`:

```yaml
artifacts:
  skills:
    - skills/code-review/
```

---

## SKILL.md Anatomy

`SKILL.md` is the entry point the agent reads when the skill is invoked. Write it for an AI agent to follow, not for casual human reading — be explicit about steps, inputs, and expected output.

### Minimal Template

```markdown
---
name: <name>
description: One sentence description of what this skill does.
requires:
  contexts: []
---

# Skill: <Name>

## Purpose
One sentence: what does this skill do?

## When to Use
Describe the trigger — when should a developer invoke this skill?

## Process
1. Step one
2. Step two
3. Step three

## Output
What should the agent produce or report back?
```

### Frontmatter Fields

| Field | Required | Notes |
|---|---|---|
| `name` | yes | Slash-command name agents will use to invoke |
| `description` | yes | One-sentence summary, used in skill catalogs |
| `requires.contexts` | no | List of context names (no `contexts/` prefix, no `.md`) the skill depends on; `abc sync` errors if they're not also adopted |
| `requires.skills` | no | List of other skill directory names this skill calls into |

---

## Supporting Files

For complex skills, include reference files the agent reads during execution:

```
skills/
└── api-design/
    ├── SKILL.md               # Entry point
    ├── rest-principles.md     # Reference: REST design rules
    ├── naming-conventions.md  # Reference: naming guide
    └── examples/
        ├── good-api.md        # What to aim for
        └── bad-api.md         # Common mistakes
```

Reference them explicitly inside `SKILL.md`:

```markdown
## References
- See `rest-principles.md` for REST design rules
- See `naming-conventions.md` for endpoint naming
- See `examples/` for before/after examples
```

For skills that need **deterministic execution** (file I/O, YAML manipulation, git operations), add `scripts/` containing standalone Python scripts. See the [Skills design page](../design/skills.md) for the thin-skill / fat-tools rationale, and the bundled `contribute-warehouse` skill for an in-repo example.

---

## Best Practices

- **Keep skills focused.** One skill, one job. A skill that does code review *and* generates tests is harder to invoke and maintain.
- **Write for the agent, not the human.** Be explicit about steps, inputs, and expected output format. The agent follows your instructions literally.
- **Test with real projects.** Before distributing, sync the skill and invoke it on real code. Refine based on output quality.
- **If it's heavily multi-phase with state, consider an agent instead.** Workflow-heavy skills often work better as [agents](creating-agents.md). See [Skills design](../design/skills.md#workflow-skills-probably-belong-to-agents).

---

## See Also

- [Bundled Skills](../concepts/bundled-skills.md) — operational reference for the `record-*` and `contribute-warehouse` skills
- [Skills design](../design/skills.md) — opinion on what a skill is and what it isn't
- [Creating Knowledge and Contexts](creating-knowledge-and-contexts.md) — the other tool-agnostic artifacts
- [Creating an Agent](creating-agents.md) — when a workflow is too heavy for a skill
