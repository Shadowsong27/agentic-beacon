# Creating Knowledge and Contexts

Knowledge and contexts are the two tool-agnostic artifact types — plain markdown that any agent can read. They're related: **a context is, in effect, a curated collection of knowledge**. The distinction is about how the content is packaged and loaded, not about what kind of content it is.

- **Contexts** are the boot-time payload — what the agent loads on session start. A context can hold short rules and patterns inline, AND point at deeper material via links. The inline content is loaded immediately; the linked content is loaded only when the agent follows the link.
- **Knowledge files** are atomic units — one decision, one lesson, one fact — that can be referenced from one or more contexts (or from other knowledge files). They exist as standalone files so the same piece of knowledge can be composed into multiple contexts and so it can be left out of the boot-time payload when it's not needed every session.

Progressive disclosure — pulling deep detail in only when the agent needs it — is an **optimisation pattern**, not the definition of either artifact. Not all knowledge is hidden at session start; some of it lives inline in a context, on purpose.

This guide covers authoring each.

For links from a context or knowledge file to another warehouse artifact, use the
[canonical link convention](canonical-links.md). Relative cross-artifact links are not
portable under Beacon's symlinked distribution model.

---

## Knowledge

The `/record-knowledge` [bundled skill](../concepts/bundled-skills.md) is the structured path. It prompts you for a topic, type (decision / lesson / fact), and content, then writes the file at the correct warehouse path.

From an OpenCode or Claude Code session:

```
/record-knowledge
```

Or, if you'd rather drive it yourself: just tell the agent *"record this as a lesson under `python-standards`"* and let it write the file directly.

### Where Knowledge Files Live

The warehouse-lint rule is: `knowledge/[<topic>/]<type>/<name>.md` where `<type>` is one of `decisions/`, `lessons/`, or `facts/`.

```
knowledge/
├── python-standards/
│   ├── decisions/
│   │   └── pydantic-vs-dataclass.md
│   ├── lessons/
│   │   └── python-type-annotations-use-primitive-types.md
│   └── facts/
└── cicd/
    └── lessons/
        └── github-runner-setup-procedure.md
```

The `<topic>/` prefix is optional and free-form — you design the topic taxonomy that suits your warehouse. The three leaf taxonomies (`decisions`, `lessons`, `facts`) are enforced.

### What Each Type Is For

| Type | Captures | Typical shape |
|---|---|---|
| **decisions** | A choice that was made and why | Problem → options → decision → rationale |
| **lessons** | A pattern where agents commonly fail or get distracted | Agent failure mode → correct pattern → guardrail |
| **facts** | An established piece of technical information | Statement → context → usage notes |

### Knowledge Is Not Declared in `beacon.yaml`

You don't add knowledge to `beacon.yaml`. `abc sync` scans every adopted context and skill for markdown links into `knowledge/`, resolves them against the warehouse, and creates symlinks transitively. To make a new knowledge file appear in a project: add a link to it from a context or skill that the project already adopts.

If no context links to your new knowledge file yet, the file is fine in the warehouse — it just won't appear in any project's `.agentic-beacon/artifacts/knowledge/` until something points at it.

---

## Contexts

Contexts have **no bundled skill**. You author them directly — either by hand or by asking an agent to write one in the warehouse.

```
contexts/
├── python-standards.md
├── cicd-flow.md
└── teams/
    └── backend.md
```

Naming and subdirectory layout are entirely free — `abc warehouse lint` doesn't enforce a shape inside `contexts/`. Use whatever organisation suits your warehouse.

### What Goes in a Context

A context is a **scannable** boot-time document. Each entry typically:

1. States the rule or pattern in one or two sentences.
2. Links to deeper knowledge for the rationale or details.

Don't put long explanations in a context — push that into a knowledge file and link to it.

### Proactive vs. Reactive Pointers

Two link styles are used by convention, and they signal different agent behaviour:

| Style | Meaning | Use for |
|---|---|---|
| `**Read:** [link](path)` | Agent should read this immediately | Rules that affect every file the agent touches |
| `**See:** [link](path)` | Agent should read only when relevant | Troubleshooting, edge-case detail, reference material |

Example from `python-standards.md`:

```markdown
## Type Annotations

**Rule:** Use unquoted primitive types. Never import from `typing` for built-in generics.

**Read:** [Primitive types](../knowledge/python-standards/lessons/python-type-annotations-use-primitive-types.md)
```

The distinction is conventional — the agent treats both as readable links, but a context-savvy agent uses the verb to prioritise.

### Declaring a Context

Once the file exists in the warehouse, add it to `beacon.yaml`:

```yaml
artifacts:
  contexts:
    - contexts/python-standards.md
    - contexts/cicd-flow.md
```

Then `abc sync` symlinks it into `.agentic-beacon/artifacts/contexts/` and wires it into your tool's config (`CLAUDE.md`, `opencode.json`).

You can also let `abc adopt` handle the wiring — write the context, append a pending entry, accept it in the TUI.

---

## When to Extract a Knowledge File vs. Keep It Inline in a Context

The decision isn't *"is this for every session or only sometimes?"* — a context can already hold both inline rules and pointers. The useful question is whether a piece of content should be its **own file**.

Extract it as a knowledge file when:

- **It's referenced from more than one context.** A single source of truth that multiple contexts can link to.
- **It's atomic and complete on its own** — one decision, one lesson, one fact, with its own rationale. The kind of thing you'd link to from a PR description.
- **It's heavy enough that loading it inline at boot is wasteful** — long examples, lots of code, troubleshooting trees. Push it into a knowledge file and link via `**See:**` so the agent only pulls it when relevant.

Keep it inline in the context when:

- **It's short and the agent needs it on every session** — a one-line naming rule, a quick "always do X" reminder. Extracting it forces an extra link-follow for no gain.
- **It's tightly bound to the surrounding rules** in the context and doesn't make sense outside that grouping.
- **You don't yet know if it'll be reused.** Start inline; extract later if a second context wants it.

The progressive-disclosure pattern (`**Read:**` for must-load, `**See:**` for load-when-needed) only kicks in *once you've extracted*. Before that, content lives in the context and is loaded with it. See the [Philosophy](../design/philosophy.md#two-tier-information-model) page for the design rationale behind the split.

---

## See Also

- [Creating Skills](creating-skills.md) — packaged workflows, the procedural counterpart to contexts and knowledge
- [Creating an Agent](creating-agents.md) — when you need a distinct agent persona rather than just instructions
- [Bundled Skills](../concepts/bundled-skills.md) — operational reference for `/record-knowledge`
- [Philosophy](../design/philosophy.md) — why the two-tier (context + knowledge) model exists
