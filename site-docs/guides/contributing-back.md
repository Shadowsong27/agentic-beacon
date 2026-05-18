# Contributing Back to the Warehouse

Contributing back has two phases:

1. **Author the artifact** — create or improve a skill, knowledge file, context, or agent in the warehouse working tree.
2. **Commit and push** — share it with teammates via the bundled `/contribute-warehouse` skill (or the lower-level CLI).

This page covers the commit-and-push half. The sub-pages cover authoring each artifact type:

- [Creating Skills](creating-skills.md) — via `/record-skill` or by asking an agent to write one
- [Creating Knowledge and Contexts](creating-knowledge-and-contexts.md) — via `/record-knowledge` or direct edit
- [Creating an Agent](creating-agents.md) — direct edit (no bundled skill)

> Agentic Beacon uses a **symlink model**: `abc sync` creates symlinks from `.agentic-beacon/artifacts/` into your warehouse clone. When you author or improve an artifact through any of the paths above, the change is already in the warehouse working tree — you just need to commit and push it.

---

## The Recommended Path: `/contribute-warehouse`

From an OpenCode or Claude Code session inside a connected project:

```
/contribute-warehouse
```

The skill walks you through the contribution interactively:

1. **Resolves the warehouse** from `.agentic-beacon/config.toml`.
2. **Runs `abc warehouse lint`** as a hard gate — aborts if the warehouse has any integrity errors.
3. **Summarises dirty paths** and asks you which to include and which to leave for later.
4. **Scans `knowledge/` files for semantic duplicates** so you don't ship the same lesson twice under different names.
5. **Splits the included files into cohesive commits** with drafted Conventional Commits messages.
6. **Pushes all commits atomically** at the end — one push, all-or-nothing.

This is the path you should reach for almost every time. It catches problems the raw CLI doesn't, and it produces a tidy commit history without you having to think about it.

> For the full design and flag reference, see [`contribute-warehouse` Skill Reference](../reference/contribute-warehouse.md).

---

## The Lower-Level Primitive: `abc warehouse contribute`

The raw `abc warehouse contribute` CLI is what the skill wraps. You can use it directly for one-off commits that don't need the full guided flow:

```bash
abc warehouse status                                    # review dirty files
abc warehouse contribute -m "<message>" --paths <file>  # commit specific files
abc warehouse contribute -m "<message>" --push          # commit + push in one step
```

The `--paths` option is repeatable — pass it once per file. Omitting it stages every dirty tracked file in the warehouse, which is rarely what you want when you've been editing across several artifacts.

> **Heads up:** raw `abc warehouse contribute` is currently less reliable than the bundled skill in some environments. If it misbehaves, reach for `/contribute-warehouse` instead.

---

## Manual Git, If You Prefer

Because artifacts are symlinks into the warehouse clone, the warehouse working tree is always up to date. You can also just use plain git:

```bash
cd ~/team-warehouse
git add knowledge/python/type-hints.md
git commit -m "docs: improve type hints guide"
git push
```

This bypasses the lint gate and the cohesion split — fine for trivial edits, but for anything substantive, prefer the bundled skill.

---

## Teammates Pick It Up

Once the commit is on the remote, teammates pull and resync:

```bash
cd ~/team-warehouse && git pull
cd my-project && abc sync
```

Their existing symlinks pick up the new content immediately; `abc sync` only needs to run if `beacon.yaml` references new paths or if symlinks have drifted.

---

## Contribution Checklist

Whichever path you use, before you push:

- [ ] Tested the artifact in a real session — the agent actually used it correctly.
- [ ] Content is generic — no project-specific paths, credentials, or names.
- [ ] No broken references or links.
- [ ] Commit message describes **why** the change helps, not just what changed.

---

## See Also

- [`contribute-warehouse` Skill Reference](../reference/contribute-warehouse.md) — full flow, flags, and design notes
- [Day-to-Day Workflow](day-to-day-workflow.md) — how contributing fits into the broader loop
- [CLI Reference](../reference/cli.md) — every `abc warehouse contribute` option
