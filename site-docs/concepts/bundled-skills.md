# Bundled Skills

> This page covers skills shipped inside `abc` itself. For user-authored warehouse skills, see [Creating Skills](../guides/creating-skills.md).

Agentic Beacon ships two skills inside the `abc` package. These **bundled skills** are available in every project the moment you run `abc adopt` — no warehouse content required. Their purpose is to bootstrap content authoring: on a fresh project, before your warehouse has any skills, you can still invoke `/record-knowledge` and `/record-skill` to start building it.

---

## The Two Bundled Skills

### `record-knowledge`

Captures a decision, lesson, or fact into the warehouse's `knowledge/` directory.

**What it does:**

1. Agent prompts you for a topic, title, and content summary
2. Writes a markdown file to `<warehouse>/knowledge/<topic>/<slug>.md`
3. Knowledge files are auto-derived during `abc sync` / `abc adopt` — no `pending.yaml` entry is created and no explicit accept step is required

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

After `abc adopt` (or `abc sync`) runs, each bundled skill appears in these locations in your project:

```
my-project/
├── .claude/
│   └── skills/record-knowledge/
│       └── SKILL.md
└── .opencode/
    ├── command/record-knowledge.md    # OpenCode slash-command stub
    └── skills/record-knowledge/
        └── SKILL.md
```

- `.opencode/command/<skill>.md` — OpenCode slash-command stub
- `.opencode/skills/<skill>/SKILL.md` — OpenCode skill copy
- `.claude/skills/<skill>/SKILL.md` — Claude Code skill copy

Claude Code discovers skills directly from `.claude/skills/` — there's no equivalent of the `.opencode/command/` stub file.

---

## When Wiring Happens

Two commands wire bundled skills:

- **`abc sync`** — wires bundled skills as part of its normal artifact-sync flow.
- **`abc adopt`** — also wires bundled skills after its commit step (added in PER-151). This means the standard first-run sequence `connect → setup → adopt` leaves bundled skills fully available without a separate `abc sync`. Note: `abc adopt` only triggers bundled wiring when at least one entry is committed in the TUI. If you open `abc adopt` and exit without any accept/reject changes, the commit doesn't fire and bundled skills won't be wired — run `abc sync` instead in that case.

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

> **Note:** `abc warehouse init` copies each bundled skill into the new warehouse's `skills/` directory as a starting-point template. This means a freshly initialised warehouse will contain `skills/record-knowledge/` and `skills/record-skill/` entries that look like ordinary warehouse skills — but the canonical version used for project wiring is always the one inside the `abc` package. See [Bundled Skills in the Warehouse Template](#bundled-skills-in-the-warehouse-template) below.

---

## Bundled Skills in the Warehouse Template

When you run `abc warehouse init`, the initializer copies each bundled skill from the `abc` package into the new warehouse's `skills/` directory (via `_install_bundled_skills`). This produces real files — not symlinks — at paths like:

```
my-warehouse/
└── skills/
    ├── record-knowledge/
    │   └── SKILL.md
    └── record-skill/
        └── SKILL.md
```

These copies exist so teams have a visible, editable starting point. You can modify `<warehouse>/skills/record-knowledge/SKILL.md` to adjust the workflow for your organisation and commit that change into the warehouse.

However, **the copies are not automatically used for project wiring**. When `abc sync` or `abc adopt` wires bundled skills into a project, it always reads from the `abc` package source — the warehouse copy is informational unless you explicitly adopt it as a regular warehouse skill via `beacon.yaml`. There is currently no automatic override mechanism that promotes a customised warehouse copy back into the wiring pipeline.

In practice this means: a fresh warehouse visually contains bundled skills alongside other warehouse content, but teams that want to distribute a customised variant should treat it as a new warehouse skill (with a different name) rather than expecting the warehouse copy to shadow the bundled version.

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
