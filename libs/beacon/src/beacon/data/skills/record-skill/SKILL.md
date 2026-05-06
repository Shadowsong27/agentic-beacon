---
name: record-skill
description: Scaffold new Beacon skills in the warehouse with LLM-driven content generation and pending-based wiring
license: MIT
compatibility: opencode
requires:
  contexts: []
---

# SKILL: Record Skill — Scaffold New Skills

## Purpose

Create properly structured Beacon skills in the connected warehouse. Generates a skill
directory at `<warehouse>/skills/<name>/` with `SKILL.md` and an optional PEP 723
script, then queues it in `.agentic-beacon/pending.yaml` for adoption via `abc adopt`.

## When to Use

- You want to create a new skill for your team or project
- You need a skill stored in the warehouse and distributed to all connected projects
- You want consistent skill structure across your warehouse

## Invocation

```
/record-skill
```

Or with context:

```
/record-skill <brief description of the skill to create>
```

---

## Prerequisites

This skill requires a connected warehouse. Verify at the start:

```bash
uv run ${SKILL_DIR}/scripts/resolve_warehouse.py
```

If this command fails with `Error: no warehouse connected. Run 'abc warehouse connect <path>' first.`, stop immediately and surface the error to the user. Do not continue.

---

## Process

### Step 1: Gather Skill Information

Ask the user for (or infer from context if already provided):

1. **Skill name** — kebab-case, e.g. `deploy-check`
2. **One-line description** — becomes frontmatter `description:`
3. **Invocation form** — e.g. `/deploy-check` (defaults to `/<name>`)
4. **Include Python script?** — yes/no — whether to generate a `scripts/<name>.py` PEP 723 scaffold

### Step 2: Resolve Warehouse

Run the warehouse resolver and capture the path:

```bash
WAREHOUSE_ROOT=$(uv run ${SKILL_DIR}/scripts/resolve_warehouse.py)
```

If the command exits non-zero, surface the stderr output to the user and stop.

### Step 3: Suggest `requires.contexts` from Warehouse Scan

Read all context files under `$WAREHOUSE_ROOT/contexts/*.md` (if any exist). Based on
the skill's name and description, identify which context files are relevant.

Present the suggestion to the user:

```
Suggested requires.contexts for "<skill-name>":

  - contexts/python-standards.md
    Reason: skill relates to Python code patterns

  - contexts/testing.md
    Reason: skill validates test quality

Options:
  1. Accept as-is
  2. Edit the list
  3. Skip (use empty list)
```

If no warehouse contexts exist or none are relevant, inform the user and use an empty
list without prompting further.

### Step 4: Write Skill to Warehouse

Create the skill directory and files at `$WAREHOUSE_ROOT/skills/<name>/`.

**`$WAREHOUSE_ROOT/skills/<name>/SKILL.md`:**

```
---
name: <name>
description: <description>
license: MIT
compatibility: opencode
requires:
  contexts: [<accepted-list-or-empty>]
---

# SKILL: <Title>

## Purpose

<description>

## When to Use

<!-- Describe the specific situations where this skill applies -->

## Invocation

/<name>

## Process

<!-- Step-by-step workflow -->

## Examples

<!-- Concrete usage examples -->

## Checklist

- [ ] Skill files are complete and tested
- [ ] Documentation is accurate and up-to-date
- [ ] Skill has been validated in a real project
```

If the user requested a Python script, also create:

**`$WAREHOUSE_ROOT/skills/<name>/scripts/<name>.py`:**

```python
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""<description>"""

import sys


def main() -> None:
    """Main entry point for <name>."""
    print(f"Running <name>...")
    # TODO: Implement your skill logic here


if __name__ == "__main__":
    main()
```

### Step 5: Append to pending.yaml

```bash
uv run ${SKILL_DIR}/scripts/append_pending.py \
  --path skills/<name>/ \
  --type skill \
  --action created \
  --source record-skill
```

### Step 6: Confirm Completion

```
✅ Skill scaffolded successfully!

Name:             <name>
Warehouse path:   $WAREHOUSE_ROOT/skills/<name>/
Script:           [created | not included]
requires.contexts: [list or empty]
Pending entry:    added to .agentic-beacon/pending.yaml

Next steps:
  1. Edit $WAREHOUSE_ROOT/skills/<name>/SKILL.md to fill in Process and Examples
  2. Run 'abc adopt' to wire this skill into your project
```

---

## Examples

### Example 1: Markdown-Only Skill

**User:**
```
/record-skill
```

**Agent:**
1. Asks: name=`deploy-check`, description="Validate deployment readiness", invocation=`/deploy-check`, no script
2. Resolves warehouse path via `resolve_warehouse.py`
3. Scans contexts — no relevant matches → user skips
4. Writes `$WAREHOUSE_ROOT/skills/deploy-check/SKILL.md`
5. Runs `append_pending.py` with `type: skill action: created source: record-skill`
6. Reports: "✅ Skill scaffolded! Run `abc adopt` to wire it."

### Example 2: Skill with Script and Context Suggestion

**User:**
```
/record-skill Create a skill that validates Python type annotations
```

**Agent:**
1. Infers: name=`validate-types`, description="Validate Python type annotations", invocation=`/validate-types`, yes script
2. Resolves warehouse path
3. Scans contexts → suggests `contexts/python-standards.md` → user accepts
4. Writes `$WAREHOUSE_ROOT/skills/validate-types/SKILL.md` with `requires.contexts: [contexts/python-standards.md]`
5. Writes `$WAREHOUSE_ROOT/skills/validate-types/scripts/validate-types.py` (PEP 723 scaffold)
6. Runs `append_pending.py`
7. Reports: "✅ Skill scaffolded! Run `abc adopt` to wire it."

---

## Checklist for Agent

- [ ] Gather skill name, description, invocation, include-script preference
- [ ] Run `resolve_warehouse.py` — STOP if it exits non-zero
- [ ] Scan warehouse contexts and propose `requires.contexts` (accept / edit / skip)
- [ ] Write `SKILL.md` to `$WAREHOUSE_ROOT/skills/<name>/` (warehouse, not the project)
- [ ] Write PEP 723 script scaffold if requested
- [ ] Run `append_pending.py` with `type: skill action: created source: record-skill`
- [ ] Confirm completion and remind user to run `abc adopt`

---

## PEP 723 Pattern

PEP 723 lets Python scripts declare their own dependencies without a `pyproject.toml`:

```python
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests>=2.31.0",
# ]
# ///
```

**Benefits:**
- No `venv/` or `pyproject.toml` needed per skill
- Dependencies are version-pinned and explicit
- Scripts are self-contained and portable
- Runs with `uv run script.py` anywhere

**Reference:** [PEP 723 – Inline script metadata](https://peps.python.org/pep-0723/)

---

## Related

- `record-knowledge` — Capture decisions and lessons into the knowledge base

---

**Skill Version:** 2.0.0
**Last Updated:** 2026-05-06
