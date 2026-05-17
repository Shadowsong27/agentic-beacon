# Bundled Skills

> This page covers skills shipped inside `abc` itself. For user-authored warehouse skills, see [Creating Skills](../guides/creating-skills.md).

Agentic Beacon ships three skills inside the `abc` package. These **bundled skills** become available in a project after `abc sync` runs (always wires them), or after `abc adopt` (only when an adoption commit fires — see [When Wiring Happens](#when-wiring-happens) below) — no warehouse content required. Their purpose is to bootstrap content authoring: on a fresh project, before your warehouse has any skills, you can still invoke `/record-knowledge`, `/record-skill`, and `/contribute-warehouse` immediately.

---

## The Three Bundled Skills

### `record-knowledge`

Captures a decision, lesson, or fact into the warehouse's `knowledge/` directory.

**What it does:**

1. Agent prompts you for a topic, title, and content summary
2. Writes a markdown file to `<warehouse>/knowledge/<topic>/<type>s/<slug>.md` (with `--topic`), or `<warehouse>/knowledge/<type>s/<slug>.md` (without topic), where `<type>` is `decision`, `lesson`, or `fact`
3. No `pending.yaml` entry is created — but knowledge files are **not** synced automatically. They appear under `.agentic-beacon/artifacts/knowledge/` only when a context or skill already wired into your project (via `beacon.yaml`) links to the new knowledge file's path. If no such link exists yet, adopt or hand-edit a context that references the path first.

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

### `contribute-warehouse`

Wraps `abc warehouse contribute` with a guided, conversational contribution flow:
lint gate, intent triage, semantic dedup scan, cohesion split, and atomic push.

**What it does:**

1. Runs `abc warehouse lint` — aborts if the warehouse has any integrity errors
2. Summarizes dirty tracked paths via `summarize_changes.py`
3. Asks which files to include or leave for later
4. Scans for semantic dedup in `knowledge/` files
5. Checks cohesion and proposes a commit split if needed
6. Drafts Conventional Commits messages via `draft_commit_message.py`
7. Calls `abc warehouse contribute -m "<msg>" --paths <file> [<file> ...]` per commit group (no `--push`); omits `--paths` when all included files form a single cohesive group
8. Pushes all commits atomically via `push_warehouse.py`

**When to invoke:** when you want to commit and push warehouse changes through a
safe, intent-aware flow — especially when multiple files are dirty or you want the
lint gate enforced.

For full documentation, see [Contribute Warehouse Skill](../guides/contribute-warehouse.md).

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
- **`abc adopt`** — also wires bundled skills after its commit step (added in PER-151). This means the standard first-run sequence `connect → setup → adopt` leaves bundled skills fully available without a separate `abc sync`. Note: `abc adopt` only triggers bundled wiring when at least one entry is accepted in the TUI (reject-only or defer-only commits do not fire post-sync wiring). If you open `abc adopt` and exit without accepting anything, run `abc sync` to wire bundled skills.

```bash
abc warehouse connect --path ~/my-org-warehouse
abc setup          # auto-creates CLAUDE.md and opencode.json if missing
abc adopt          # select warehouse artifacts; bundled skills wired here too
# → "Wired bundled skills: record-knowledge, record-skill, contribute-warehouse"
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
    ├── record-skill/
    │   └── SKILL.md
    └── contribute-warehouse/
        ├── SKILL.md
        └── scripts/
            ├── resolve_warehouse.py
            ├── summarize_changes.py
            ├── draft_commit_message.py
            └── push_warehouse.py
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
# → "⚠ 1 pending artifacts. Run 'abc adopt' to wire them."

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
