---
name: record-skill
description: Scaffold new Beacon skills with proper frontmatter, section structure, and optional PEP 723 Python scripts.
license: MIT
compatibility: opencode
---

# SKILL: Record Skill — Scaffold New Skills

## Purpose

Create properly structured Beacon skills from an interactive prompt. Generates:

- `SKILL.md` with frontmatter (`name`, `description`, `license`, `compatibility`)
- Standard section structure (Purpose / When to Use / Invocation / Process / Examples / Checklist)
- Optional PEP 723 Python script under `scripts/`

## When to Use

- You want to create a new skill for your team or project
- You need a PEP 723-headed Python script as part of a skill
- You want consistent skill structure across your warehouse

## Scripts

| Script | Purpose |
|--------|---------|
| `${SKILL_DIR}/scripts/create_skill.py` | Interactive skill scaffolder |

## Usage

```bash
# Run the interactive scaffolder
uv run ${SKILL_DIR}/scripts/create_skill.py
```

The tool prompts for:

1. **Skill name** (auto-normalized to kebab-case)
2. **One-line description** (→ frontmatter `description`)
3. **Invocation form** (e.g. `/my-skill <args>`, defaults to `/<name>`)
4. **Include Python script?** (yes/no — generates PEP 723 inline script)

## Process

### Step 1: Run the Scaffolder

```bash
uv run ${SKILL_DIR}/scripts/create_skill.py
```

### Step 2: Fill in Generated Content

The scaffolder creates `.agentic-beacon/artifacts/skills/<name>/` with:

```
skills/<name>/
├── SKILL.md
└── scripts/
    └── <name>.py          # only if you requested a script
```

Edit `SKILL.md` to complete:
- **When to Use** — specific situations
- **Process** — step-by-step workflow
- **Examples** — concrete usage

### Step 3: Implement the Script (if included)

The generated `.py` file has a PEP 723 header:

```python
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
```

Add dependencies as you implement:

```python
# dependencies = [
#   "requests>=2.31.0",
#   "pydantic>=2.0.0",
# ]
```

Test without any `pyproject.toml`:

```bash
uv run .agentic-beacon/artifacts/skills/<name>/scripts/<name>.py
```

### Step 4: Register and Sync

Add to `beacon.yaml`:

```yaml
artifacts:
  skills:
    - skills/<name>/
```

Run `abc sync` to distribute.

## Examples

### Example 1: Markdown-Only Skill

```bash
$ uv run ${SKILL_DIR}/scripts/create_skill.py
============================================================
Beacon Skill Scaffolder
============================================================

Skill name (kebab-case): deploy-check
One-line description: Validate deployment readiness checklist
Invocation form [/deploy-check]:
Include PEP 723 Python script [y/N]: n

Scaffolding...

============================================================
✓ Created skill: deploy-check
============================================================

  Location: /path/to/project/.agentic-beacon/artifacts/skills/deploy-check
  SKILL.md: /path/to/project/.agentic-beacon/artifacts/skills/deploy-check/SKILL.md

Next steps:
  1. Edit .../SKILL.md to fill in Process and Examples
  4. Add to beacon.yaml: skills/deploy-check/
  5. Run 'abc sync' to distribute
```

### Example 2: Skill with PEP 723 Script

```bash
$ uv run ${SKILL_DIR}/scripts/create_skill.py
Skill name (kebab-case): s3-cleanup
One-line description: Clean old S3 buckets with configurable retention
Include PEP 723 Python script [y/N]: y

Scaffolding...

============================================================
✓ Created skill: s3-cleanup
============================================================

  Location: .../.agentic-beacon/artifacts/skills/s3-cleanup
  SKILL.md: .../.agentic-beacon/artifacts/skills/s3-cleanup/SKILL.md
  Script:   .../.agentic-beacon/artifacts/skills/s3-cleanup/scripts/s3-cleanup.py

Next steps:
  1. Edit .../SKILL.md to fill in Process and Examples
  2. Implement logic in .../scripts/s3-cleanup.py
  3. Test: uv run .../scripts/s3-cleanup.py
  4. Add to beacon.yaml: skills/s3-cleanup/
  5. Run 'abc sync' to distribute
```

## Checklist

- [ ] Skill name is kebab-case and descriptive
- [ ] Description is one line and clear
- [ ] SKILL.md sections are filled in (not left as stubs)
- [ ] Scripts run without errors (`uv run ...`)
- [ ] beacon.yaml entry added before syncing
- [ ] Skill tested in a real project before sharing

## PEP 723 Pattern

PEP 723 (uv inline script metadata) lets Python scripts declare their own dependencies without a `pyproject.toml`:

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

## Related

- `record-knowledge` — Capture decisions and lessons into the knowledge base
- `minio-ops` — Example of a Python PEP 723 skill
- `runner-disk-cleanup` — Example of a bash skill
