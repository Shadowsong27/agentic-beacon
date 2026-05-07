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

Create properly structured Beacon skills in the connected warehouse. The bundled
`write_skill.py` script generates a skill directory at
`<warehouse>/skills/<name>/` with `SKILL.md` and an optional PEP 723 script,
then `append_pending.py` queues it for adoption via `abc adopt`.

> **Important:** Do NOT write the skill files using your editor tools directly.
> Always go through `write_skill.py`. The script enforces that the directory
> lands inside the warehouse and refuses to write into the project's symlink
> mirror at `.agentic-beacon/artifacts/skills/`.

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

Read all context files under `$WAREHOUSE_ROOT/contexts/*.md` (if any exist).
Based on the skill's name and description, identify which context files are
relevant.

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

If no warehouse contexts exist or none are relevant, inform the user and use an
empty list without prompting further.

### Step 4: Scaffold the Skill via `write_skill.py`

Invoke the writer to generate the skill directory in the warehouse. **This is
the only way the SKILL.md and (optional) script are created.** Do not use your
editor's write tool.

```bash
WRITTEN_DIR=$(uv run ${SKILL_DIR}/scripts/write_skill.py \
  --name <kebab-name> \
  --description "<one-line description>" \
  [--invocation "/<name>"] \
  [--include-script] \
  [--requires-context contexts/<file>.md ...] \
)
```

The script:
- Resolves the warehouse from `.agentic-beacon/config.toml`.
- Refuses to write outside `<warehouse>/skills/`.
- Refuses to overwrite an existing skill directory unless `--overwrite` is passed.
- Creates `SKILL.md` (with `## Purpose`, `## When to Use`, `## Invocation`,
  `## Process`, `## Examples`, `## Checklist` placeholders) using the requested
  frontmatter.
- If `--include-script` is set, also creates `scripts/<name>.py` as a PEP 723
  scaffold.
- Prints the warehouse-relative skill directory on stdout (e.g.
  `skills/deploy-check/`).

If the script exits non-zero, surface the stderr to the user and stop.

### Step 5: Optionally Fill in Body Sections

The scaffolded `SKILL.md` has `<!-- ... -->` placeholders for the
`When to Use`, `Process`, and `Examples` sections. If the user gave you enough
context to draft these, edit `$WAREHOUSE_ROOT/skills/<name>/SKILL.md` directly
to replace the placeholders. This is a normal in-place edit on a fully-qualified
warehouse path; your editor's edit tool is fine here.

If the user prefers to fill the body themselves, leave the placeholders as-is
and surface that in the completion message.

### Step 6: Append to pending.yaml

```bash
uv run ${SKILL_DIR}/scripts/append_pending.py \
  --path skills/<name>/ \
  --type skill \
  --action created \
  --source record-skill
```

### Step 7: Confirm Completion

```
✅ Skill scaffolded successfully!

Name:              <name>
Warehouse path:    $WAREHOUSE_ROOT/<written-dir>
Script:            [created | not included]
requires.contexts: [list or empty]
Pending entry:     added to .agentic-beacon/pending.yaml

Next steps:
  1. Edit $WAREHOUSE_ROOT/skills/<name>/SKILL.md to fill in Process and Examples
     (if you didn't draft them in Step 5)
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
1. Asks: name=`deploy-check`, description="Validate deployment readiness", invocation=`/deploy-check`, no script.
2. Runs `resolve_warehouse.py`.
3. Scans contexts — no relevant matches → user skips.
4. Calls `write_skill.py --name deploy-check --description "Validate deployment readiness"` → script writes `skills/deploy-check/SKILL.md` to the warehouse.
5. User chose to fill the body themselves → leave placeholders.
6. Runs `append_pending.py --path skills/deploy-check/ --type skill --action created --source record-skill`.
7. Reports: "✅ Skill scaffolded! Run `abc adopt` to wire it."

### Example 2: Skill with Script and Context Suggestion

**User:**
```
/record-skill Create a skill that validates Python type annotations
```

**Agent:**
1. Infers: name=`validate-types`, description="Validate Python type annotations", invocation=`/validate-types`, yes script.
2. Runs `resolve_warehouse.py`.
3. Scans contexts → suggests `contexts/python-standards.md` → user accepts.
4. Calls `write_skill.py --name validate-types --description "Validate Python type annotations" --include-script --requires-context contexts/python-standards.md` → script writes `skills/validate-types/SKILL.md` and `skills/validate-types/scripts/validate-types.py`.
5. Drafts a brief Process section based on the user's description and edits `SKILL.md` directly in the warehouse.
6. Runs `append_pending.py`.
7. Reports: "✅ Skill scaffolded! Run `abc adopt` to wire it."

---

## Checklist for Agent

- [ ] Gather skill name, description, invocation, include-script preference
- [ ] Run `resolve_warehouse.py` — STOP if it exits non-zero
- [ ] Scan warehouse contexts and propose `requires.contexts` (accept / edit / skip)
- [ ] Call `write_skill.py` with the appropriate flags — do NOT write `SKILL.md` or the script with your editor's write tool
- [ ] Optionally fill `When to Use`, `Process`, `Examples` placeholders by editing the warehouse `SKILL.md` in place
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

**Skill Version:** 2.1.0
**Last Updated:** 2026-05-07
