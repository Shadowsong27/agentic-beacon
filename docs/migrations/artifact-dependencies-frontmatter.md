# Migration: Artifact Dependencies via Frontmatter

**Applies to:** Warehouses used with `agentic-beacon >= X.Y.0`
(version will be filled in when the feature ships).

**Time estimate:** 30–60 minutes for a warehouse with ~10 agents and ~20
skills. Scales linearly.

---

## Why this migration exists

Before this change, a warehouse expressed artifact relationships implicitly:

- Agents talked about contexts and skills in prose. The CLI never verified
  that the context an agent mentioned was actually adopted.
- Knowledge was adopted manually via `beacon.yaml.knowledge`, but nobody
  ever used it in isolation — it was always referenced from a context or
  skill. Manual adoption produced drift: `beacon.yaml.knowledge` and the
  actual markdown links went out of sync silently.

The new model makes every cross-artifact dependency **explicit and
machine-readable**:

| Edge | Expressed as |
|---|---|
| Agent → Context or Skill | YAML frontmatter `requires:` on the agent |
| Skill → Context | YAML frontmatter `requires:` on the skill |
| Context / Skill → Knowledge | Markdown links in the body (unchanged) |

At `abc sync`, the CLI:

1. Reads `requires:` from every adopted agent and skill.
2. Errors if a required context/skill is not adopted.
3. Scans markdown links in every adopted context and skill to find
   knowledge references.
4. Transitively pulls referenced knowledge. Prunes knowledge symlinks when
   the last referrer is unadopted.

`beacon.yaml.artifacts.knowledge` no longer exists — knowledge is derived.

---

## Why the CLI sent you here

Your CLI emitted an error like:

```
error: agent 'python-reviewer' has no `requires` frontmatter.
Under the current dependency model, every agent must declare the
contexts and skills it depends on. See:
  https://github.com/shadowsong27/agentic-beacon/blob/main/docs/migrations/artifact-dependencies-frontmatter.md
```

or a similar error on a skill file. This means the warehouse you are syncing
from hasn't been migrated yet.

If you are the **warehouse maintainer**: follow the steps below.

If you are a **warehouse consumer**: contact the warehouse maintainer. You
cannot fix this from your project — the fix lives in the warehouse files.

---

## What you need to change

### Agents

Every file under `agents/*.md` must have a `requires:` block in its YAML
frontmatter. Example:

```markdown
---
name: python-reviewer
description: Reviews Python code against project standards.
requires:
  contexts: [python-standards]
  skills: [record-knowledge]
---

# Python Reviewer

(body content unchanged)
```

- `contexts:` is a list of context stems — filenames under `contexts/`
  without the `.md` extension. `python-standards` maps to
  `contexts/python-standards.md`.
- `skills:` is a list of skill directory names — directories under
  `skills/`. `record-knowledge` maps to `skills/record-knowledge/SKILL.md`.
- If the agent has no context dependencies, use `contexts: []`.
- If it has no skill dependencies, use `skills: []`.
- The `requires:` block is mandatory even when both lists are empty.

### Skills

Every `skills/<name>/SKILL.md` must have a `requires:` block. Same schema
as agents, but typically only the `contexts:` key is populated. Skills
should not declare dependencies on other skills in the current version —
if you find a case where you think that's needed, open an issue; we'll
revisit the restriction case-by-case.

```markdown
---
name: python-refactor
description: Refactors Python code.
requires:
  contexts: [python-standards]
---

# Python Refactor

(body content unchanged)
```

### Contexts

**Do not add `requires:` to context files.** Contexts reference knowledge
via markdown links in the body (unchanged), not frontmatter.

### Knowledge

**Do not touch knowledge files.** Knowledge has no dependencies of its
own.

---

## Step-by-step

### 1. Inventory

From your warehouse root:

```bash
ls agents/*.md
ls skills/*/SKILL.md
```

You'll need to edit each of these files.

### 2. For each agent file

Decide by reading the prose: which contexts does it rely on? Which skills
does it invoke?

- "Use the python-standards context" → `contexts: [python-standards]`
- "Use the record-knowledge skill to capture decisions" →
  `skills: [record-knowledge]`

Add the `requires:` block at the top of the frontmatter. If the file has
no frontmatter at all, add one. Preserve all existing frontmatter keys.

### 3. For each skill file

Same treatment. Most skills depend on zero or one context.

### 4. Validate

For every file you edited, confirm:

- The YAML at the top parses cleanly (no tab characters, no unquoted
  colons, no broken indentation).
- The body below the frontmatter is unchanged.
- Every name in `requires.contexts` corresponds to an existing file under
  `contexts/`.
- Every name in `requires.skills` corresponds to an existing directory
  under `skills/`.

### 5. Commit

From the warehouse root:

```bash
git add agents/ skills/
git commit -m "chore: declare artifact dependencies via frontmatter"
```

### 6. Re-run `abc sync` in any consuming project

If the migration is complete, `abc sync` succeeds. If it errors on a
specific agent or skill, that file's `requires:` block is incomplete or
incorrect.

---

## FAQ

**What about knowledge references in my agent's prose?**

Remove them or rewrite them. Agents reference contexts and skills, not
knowledge. If an agent currently links to a knowledge file, that's a
leak through the abstraction. Pick a context that covers the knowledge,
or move the reference into a context and have the agent depend on the
context.

**Can I declare a context-to-context dependency?**

No. Contexts are leaves above knowledge. If context A and context B share
content, extract the shared content into a third context C that both
reference via prose — or, more likely, into a knowledge file that both
reference via markdown links.

**Can I still manually pin a knowledge node?**

No. `beacon.yaml.artifacts.knowledge` has been removed. Knowledge is
always derived from the adopted contexts and skills. If you want a
knowledge node to be available in a project, adopt a context or skill
that references it — or add a context that references it, if none exists.

**What happens to my existing `beacon.yaml.artifacts.knowledge` list?**

On first `abc sync` after upgrading, the field is silently dropped. The
change is visible in `git diff`. Any knowledge symlinks that are no
longer referenced by an adopted artifact are pruned. If you notice a
knowledge node you wanted to keep has disappeared, adopt the context or
skill that references it.

**My agent genuinely has no dependencies. What do I write?**

```yaml
requires:
  contexts: []
  skills: []
```

The empty block is required. Absence of `requires:` is the error
condition.

**I'm getting an error like "context 'X' required by agent 'Y' is not
adopted".**

That's the other half of the new model working as intended. Run
`abc adopt` and select context X. Or, if the agent shouldn't depend on
X, remove X from the agent's `requires.contexts`.

---

## Compatibility

There is **no legacy mode**. Warehouses with missing `requires:` blocks
will fail `abc sync` with a pointer to this document. This is deliberate:
the entire purpose of the change is to eliminate silent drift between
declared and actual dependencies. A legacy mode would reintroduce exactly
that drift.

If you maintain a warehouse used by multiple projects, coordinate the
migration with your consumers: land the frontmatter changes in the
warehouse on the same day the consumers upgrade their `agentic-beacon`
CLI. Until both sides move, consumers on the new CLI will error against
the old warehouse.
