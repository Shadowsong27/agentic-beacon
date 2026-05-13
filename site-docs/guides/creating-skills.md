# Creating Skills

> This guide covers user-authored **warehouse skills**. For the `record-*` skills shipped with `abc`, see [Bundled Skills](../concepts/bundled-skills.md).

Skills are reusable agent workflows stored in your warehouse. When a project syncs a skill, the agent can invoke it as a slash command to follow a consistent, repeatable process.

## What Is a Skill?

A skill is a packaged capability — a modular unit of work defined by the outcome it enables. Skills range from pure reasoning instructions (cognitive) to multi-step workflows combining prompts and tool calls.

In Agentic Beacon, a skill is a directory containing a `SKILL.md` entry point plus optional supporting files. The agent reads `SKILL.md` when the skill is invoked.

---

## Directory Structure

```
skills/
└── code-review/
    ├── SKILL.md           # Required — main skill definition
    ├── checklist.md       # Optional — supporting reference
    └── examples/
        └── example-pr.md  # Optional — examples for the agent
```

The skill name is the directory name (`code-review`). In `beacon.yaml`:

```yaml
artifacts:
  skills:
    - skills/code-review/
```

---

## Writing SKILL.md

`SKILL.md` is the entry point the agent reads. Write it for an AI agent to follow, not for casual human reading — be explicit about steps, inputs, and expected output.

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

### Full Template

```markdown
---
name: code-review
description: Perform a structured code review of a PR or diff, following team standards.
requires:
  contexts: [python-standards]
---

# Skill: Code Review

## Purpose
Perform a structured code review of a PR or diff, following team standards.

## When to Use
Invoke when:
- Reviewing a PR before merging
- Reviewing a specific file or function
- Auditing a new contributor's code

## Inputs
- The code to review (file paths, diff, or PR description)
- Language context from synced knowledge artifacts

## Process
1. Read all changed files in full before commenting
2. Check correctness — does it do what it claims?
3. Check style — does it follow team conventions?
4. Check tests — are all paths covered?
5. Check for security issues (auth, input validation, secrets)
6. Summarize with three sections:
   - Must fix (blockers)
   - Should fix (improvements)
   - Nice to have (suggestions)

## Output
A structured review with:
- **Blockers** — must be resolved before merge
- **Suggestions** — recommended improvements
- **Notes** — observations, questions, praise
```

---

## Examples: Common Skill Types

### Generate Unit Tests

````markdown
---
name: generate-tests
description: Generate comprehensive unit tests for a given Python function or class.
requires:
  contexts: [python-standards]
---

# Skill: Generate Unit Tests

## Purpose
Generate comprehensive unit tests for a given Python function or class.

## Process
1. Read the function/class signature and docstring
2. Identify the happy path (expected inputs and outputs)
3. Identify edge cases (empty, null, boundary values)
4. Identify error conditions (invalid input, exceptions)
5. Write one test per case using pytest
6. Name tests descriptively: `test_<function>_<scenario>`

## Output
A complete test file ready to run with `pytest`.
````

### Write PR Description

````markdown
---
name: write-pr-description
description: Generate a clear, structured PR description from a diff or set of commits.
requires:
  contexts: []
---

# Skill: Write PR Description

## Purpose
Generate a clear, structured PR description from a diff or set of commits.

## Process
1. Read the diff or list of commits
2. Summarize what changed (not how — that's in the code)
3. Explain why the change was made
4. List any breaking changes or side effects
5. Note testing performed

## Output Format
```
## Summary
<1-3 sentences describing the change>

## Changes
- <bullet point per significant change>

## Testing
- <how you verified this works>
```
````

---

## Adding Supporting Files

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

Reference them explicitly in `SKILL.md`:

```markdown
## References
- See `rest-principles.md` for REST design rules
- See `naming-conventions.md` for endpoint naming
- See `examples/` for before/after examples
```

---

## Adding a Skill to Your Warehouse

```bash
# 1. Create the skill directory
cd ~/team-warehouse
mkdir -p skills/generate-tests

# 2. Write SKILL.md
cat > skills/generate-tests/SKILL.md << 'EOF'
---
name: generate-tests
description: Generate pytest unit tests for a given function or class.
requires:
  contexts: [python-standards]
---

# Skill: Generate Unit Tests

## Purpose
Generate pytest unit tests for a given function or class.

## Process
1. Identify function signature and return type
2. Determine test cases: happy path, edge cases, errors
3. Write tests using pytest, one test per case
4. Name each test: test_<function>_<scenario>

## Output
A complete pytest test file ready to run.
EOF

# 3. Commit to warehouse
git add skills/generate-tests/
git commit -m "feat: add generate-tests skill"
git push

# 4. Declare in your project
# Edit .agentic-beacon/beacon.yaml:
# artifacts:
#   skills:
#     - skills/generate-tests/

# 5. Sync
abc sync
```

---

## Invoking a Skill

After syncing, the skill is available as a slash command:

```
/generate-tests src/services/user_service.py
/code-review src/api/routes.py
```

---

## Best Practices

**Keep skills focused.** One skill, one job. A skill that does code review *and* generates tests is harder to invoke and maintain.

**Write for the agent, not the human.** Be explicit about steps, inputs, and expected output format. The agent follows your instructions literally.

**Test with real projects.** Before distributing to the team, sync the skill to a project and invoke it on real code. Refine based on output quality.

**Include examples.** Examples in `examples/` improve agent output quality. A "good example" shows what the agent should produce; a "bad example" with annotations shows what to avoid.

**Version in the warehouse.** When a skill changes significantly:

```bash
git commit -m "feat(skills): add security checks to code-review skill"
```

---

## Next Steps

- **[Syncing Artifacts](syncing.md)** — install skills into your project
- **[Warehouse Creation](warehouse-creation.md)** — organizing skills in the warehouse
- **[Contributing Back](contributing-back.md)** — share skill improvements with the team
