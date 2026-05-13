# Bundled Skills

> This page covers skills shipped inside `abc` itself. For user-authored warehouse skills, see [Creating Skills](../guides/creating-skills.md).

Agentic Beacon ships two skills inside the `abc` package. These **bundled skills** are available in every project the moment you run `abc adopt` — no warehouse content required. Their purpose is to bootstrap content authoring: on a fresh project, before your warehouse has any skills, you can still invoke `/record-knowledge` and `/record-skill` to start building it.

---

## The Two Bundled Skills

### `record-knowledge`

Captures a decision, lesson, or fact into the warehouse's `knowledge/` directory and appends a `pending.yaml` entry in your project.

**What it does:**

1. Agent prompts you for a topic, title, and content summary
2. Writes a markdown file to `<warehouse>/knowledge/<topic>/<slug>.md`
3. Calls `scripts/append_pending.py` to append a `context` entry to `.agentic-beacon/pending.yaml`
4. You run `abc adopt` to wire the knowledge file into your project

**When to invoke:** after a notable decision, a hard-won lesson, or a fact worth sharing across teams.

---

### `record-skill`

Scaffolds a new skill in the warehouse's `skills/<name>/` directory and appends a `pending.yaml` entry.

**What it does:**

1. Agent prompts you for a skill name, description, and initial process steps
2. Writes `<warehouse>/skills/<name>/SKILL.md` with the correct frontmatter
3. Calls `scripts/append_pending.py` to append a `skill` entry to `.agentic-beacon/pending.yaml`
4. You run `abc adopt` to wire the new skill into your project

**When to invoke:** when you want to formalize a repeatable agent workflow and share it via the warehouse.

---

## Where Skills Are Wired

After `abc adopt` (or `abc sync`) runs, each bundled skill appears in three locations in your project:

```
my-project/
├── .claude/
│   ├── commands/record-knowledge.md   # Claude Code slash-command stub
│   └── skills/record-knowledge/
│       └── SKILL.md
└── .opencode/
    ├── command/record-knowledge.md    # OpenCode slash-command stub
    └── skills/record-knowledge/
        └── SKILL.md
```

Both tools discover skills identically — a file at `skills/<name>/SKILL.md` under their config directory. You do not need separate configuration for each tool.

---

## When Wiring Happens

Two commands wire bundled skills:

- **`abc sync`** — wires bundled skills as part of its normal artifact-sync flow.
- **`abc adopt`** — also wires bundled skills after its commit step (added in PER-151). This means the standard first-run sequence `connect → setup → adopt` leaves bundled skills fully available without a separate `abc sync`.

```bash
abc warehouse connect --path ~/my-org-warehouse
abc setup          # auto-creates CLAUDE.md and opencode.json if missing
abc adopt          # select warehouse artifacts; bundled skills wired here too
# → "Wired bundled skills: record-knowledge, record-skill"
```

---

## How Bundled Skills Differ from Warehouse Skills

| | Bundled skills | Warehouse skills |
|---|---|---|
| **Source** | Shipped inside the `abc` package | Authored in `<warehouse>/skills/` |
| **Versioning** | Locked to the `abc` CLI release | Evolves with your warehouse git history |
| **Declared in `beacon.yaml`?** | No — always available | Yes — must be explicitly adopted |
| **Editable by your team?** | No | Yes |
| **How discovered by agents** | Same: `skills/<name>/SKILL.md` in tool directories | Same |

Warehouse skills are distributed to teammates via `abc sync`. Bundled skills follow the developer — wherever `abc` is installed, those two skills are available.

---

## Self-Contained Scripts (PER-150)

The `scripts/append_pending.py` script inside each bundled skill has **no dependency on the `beacon` package**. It declares `pyyaml>=6.0` in a PEP 723 inline header and inlines all the YAML read-merge-write logic it needs.

This means the `record-* → pending.yaml → abc adopt` loop works for any `abc` installation — pipx, pip, or uv tool install. You do not need to be working inside the agentic-beacon source checkout.

---

## Full Walkthrough: `record-skill`

This walkthrough assumes you have already run `abc warehouse connect`, `abc setup`, and `abc adopt` at least once.

```bash
# 1. In your project, invoke the bundled skill
#    (inside a Claude Code or OpenCode session)
/record-skill

# Agent prompts you:
#   Skill name?      → python-type-hints
#   Description?     → Enforce Python type annotation standards in new code.
#   Initial steps?   → (you describe the workflow)

# Agent writes the warehouse file:
#   <warehouse>/skills/python-type-hints/SKILL.md

# Agent appends to project:
#   .agentic-beacon/pending.yaml

# 2. Back in your shell — notice the pending alert:
abc warehouse status
# → "[yellow]Pending:[/yellow] 1 unadopted artifact (run 'abc adopt')"

# 3. Review and accept the pending entry
abc adopt
# TUI opens, shows "python-type-hints" as a pending skill entry
# Press Space to select, Enter to confirm
# → Confirm screen shows: "+ skills/python-type-hints/ → beacon.yaml"
# → Press Enter to commit

# 4. The skill is now wired:
#   .agentic-beacon/beacon.yaml updated
#   .claude/skills/python-type-hints/SKILL.md   (symlink)
#   .opencode/skills/python-type-hints/SKILL.md (symlink)
#   .agentic-beacon/pending.yaml cleared

# 5. Invoke the new skill immediately:
/python-type-hints
```

For the storage model behind step 2 and 3 (`pending.yaml` lifecycle, confirm screen, atomic rollback), see [Pending & Adoption](pending-and-adoption.md).

---

## Next Steps

- **[Pending & Adoption](pending-and-adoption.md)** — the full `pending.yaml` lifecycle
- **[Creating Skills](../guides/creating-skills.md)** — authoring warehouse skills manually
- **[Interactive Adoption](../guides/interactive-adoption.md)** — the `abc adopt` TUI in depth
