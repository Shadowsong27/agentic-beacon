# Creating Skills

Skills are reusable agent workflows stored in your warehouse. When a project syncs a skill, the agent can invoke it by name to follow a consistent, repeatable process — like a code review checklist or a test generation workflow.

## What is a Skill?

A skill is a packaged capability — a modular unit of work defined by the **outcome it enables**, not how it's implemented. Skills range from pure reasoning instructions (cognitive) to multi-step orchestrated workflows combining prompts and tool calls.

In Agentic Beacon, skills are distributed as a directory containing a `SKILL.md` entry point plus optional supporting files. The agent reads `SKILL.md` and follows its instructions when invoked.

> For a deeper conceptual breakdown — cognitive vs. action vs. workflow skills, and why "everything is a prompt" — see [Understanding Agent Skills](../docs/understanding-agent-skills.md).

## Directory Structure

```
skills/
└── code-review/
    ├── SKILL.md           # Required — main skill definition
    ├── checklist.md       # Optional — supporting reference
    └── examples/
        └── example-pr.md  # Optional — examples for the agent
```

The skill name is the directory name (e.g., `code-review`). In `beacon.yaml`, you reference it as:

```yaml
artifacts:
  skills:
    - skills/code-review/**/*
```

## Writing SKILL.md

`SKILL.md` is the entry point the agent reads. It should be clear, structured, and written for an AI agent to follow, not for a human to read casually.

### Minimal Template

```markdown
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
# Skill: Code Review

## Purpose
Perform a structured code review of a pull request or diff, following team standards.

## When to Use
Invoke this skill when:
- Reviewing a PR before merging
- Asked to review a specific file or function
- Auditing a new contributor's code

## Inputs
- The code to review (file paths, diff, or PR description)
- Language context from synced knowledge artifacts

## Process
1. Read the code changes in full before commenting
2. Check correctness — does it do what it claims?
3. Check style — does it follow team conventions?
4. Check for tests — are all paths covered?
5. Check for security issues (auth, input validation, secrets)
6. Check documentation — are public APIs documented?
7. Summarize findings with:
   - Must fix (blockers)
   - Should fix (improvements)
   - Nice to have (suggestions)

## Checklist
See `checklist.md` for a per-line item reference.

## Output
A structured review with three sections:
- **Blockers** — Must be resolved before merge
- **Suggestions** — Recommended improvements
- **Notes** — Observations, questions, praise
```

---

## Examples: Common Skill Types

### Generate Unit Tests

````markdown
# Skill: Generate Unit Tests

## Purpose
Generate comprehensive unit tests for a given Python function or class.

## When to Use
When asked to write tests for new or existing code.

## Process
1. Read the function/class signature and docstring
2. Identify the happy path (expected inputs and outputs)
3. Identify edge cases (empty, null, boundary values)
4. Identify error conditions (invalid input, exceptions)
5. Write one test per case using pytest
6. Use fixtures for shared setup
7. Name tests descriptively: `test_<function>_<scenario>`

## Template
```python
import pytest

def test_<function>_happy_path():
    # Arrange
    ...
    # Act
    result = function(...)
    # Assert
    assert result == expected

def test_<function>_raises_on_invalid_input():
    with pytest.raises(ValueError):
        function(invalid_input)
```

## Output
A complete test file or test module, ready to run with `pytest`.
````

---

### Write PR Description

````markdown
# Skill: Write PR Description

## Purpose
Generate a clear, structured PR description from a diff or set of commits.

## When to Use
Before opening a pull request.

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

## Breaking Changes
<none or description>
```
````

---

## Adding Supporting Files

For complex skills, include reference files the agent can read during execution:

```
skills/
└── api-design/
    ├── SKILL.md               # Invocation entry point
    ├── rest-principles.md     # Reference: REST design rules
    ├── naming-conventions.md  # Reference: naming guide
    └── examples/
        ├── good-api.md        # What to aim for
        └── bad-api.md         # Common mistakes
```

In `SKILL.md`, reference these files explicitly:

```markdown
## References
- See `rest-principles.md` for REST design rules
- See `naming-conventions.md` for endpoint naming
- See `examples/` for before/after examples
```

The agent will read them when the skill is invoked (assuming they were synced as part of the skill directory).

---

## Adding a Skill to Your Warehouse

### Step 1: Create the skill directory

```bash
cd ~/team-warehouse
mkdir -p skills/generate-tests
```

### Step 2: Write SKILL.md

```bash
cat > skills/generate-tests/SKILL.md << 'EOF'
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
```

### Step 3: Commit to warehouse

```bash
cd ~/team-warehouse
git add skills/generate-tests/
git commit -m "feat: add generate-tests skill"
git push
```

### Step 4: Declare it in your project

```yaml
# .agentic-beacon/beacon.yaml
artifacts:
  skills:
    - skills/generate-tests/**/*
```

```bash
abc sync
```

---

## Invoking a Skill

Skills are invoked by asking your AI agent to use them. The exact syntax depends on your agent:

**OpenCode / Claude:**
```
/generate-tests src/services/user_service.py
```

**Cursor / Copilot:**
```
Use the generate-tests skill to write tests for UserService.create_user()
```

**General prompt:**
```
Follow the skill at .agentic-beacon/artifacts/skills/generate-tests/SKILL.md
to write tests for this function: [paste function]
```

---

## Best Practices

### Keep Skills Focused
One skill, one job. A skill that does code review *and* generates tests is harder to invoke and maintain.

### Write for the Agent, Not the Human
Skills are machine-readable instructions. Be explicit about steps, inputs, and expected output format. The agent follows your instructions literally.

### Version Skills in the Warehouse
When a skill changes significantly, commit it with a clear message:
```bash
git commit -m "feat(skills): add security checks to code-review skill"
```

### Test Skills with Real Projects
Before distributing a skill to the team, sync it to a project and invoke it on real code. Refine the instructions based on output quality.

### Include Examples
Examples in `examples/` improve agent output quality. A "good example" shows what the agent should produce; a "bad example" with annotations shows what to avoid.

---

## Next Steps

- **[Advanced Patterns](./advanced-patterns.md)** — Glob patterns for syncing skill directories
- **[Warehouse Creation](./warehouse-creation.md)** — Organizing skills in your warehouse
- **[Team Collaboration](./team-collaboration.md)** — Sharing skills across projects
