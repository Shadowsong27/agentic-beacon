# Agentic Beacon Sample Warehouse

A ready-to-use example warehouse mirroring the public [`agentic-beacon-starter-warehouse`](https://github.com/Shadowsong27/agentic-beacon-starter-warehouse). Used by this repository's tests and as a reference scaffolding for `abc init`.

It ships with pre-written context files for common stacks (Python, TypeScript, React, Go), a small knowledge set, and three example skills so you can exercise the full sync workflow without writing anything from scratch.

> **This is a local-only warehouse.** Clone it to your machine and connect via `abc warehouse connect --path <abs-path>`. Remote URLs (http://, git://, tarball archives) are rejected by design: `abc warehouse contribute` relies on the warehouse being a local git working tree so contributions go through normal git review.

---

## Getting Started

### 1. Install the Agentic Beacon CLI

```bash
uv tool install agentic-beacon
# or
pipx install agentic-beacon

abc --version
```

Platform support: macOS and Linux only. Windows is not supported.

### 2. Clone this warehouse locally

```bash
git clone https://github.com/Shadowsong27/agentic-beacon-starter-warehouse.git ~/agentic-beacon-starter-warehouse
```

### 3. Connect your project

```bash
cd ~/my-project
abc warehouse connect --path ~/agentic-beacon-starter-warehouse
```

### 4. Declare what you want and sync

```bash
abc setup            # creates .agentic-beacon/beacon.yaml
abc adopt            # select contexts, knowledge, and skills
abc sync             # creates symlinks into the warehouse clone and wires your agent config
```

After `abc sync`, every entry under `.agentic-beacon/artifacts/` is a symlink pointing into your warehouse clone:

```bash
find .agentic-beacon/artifacts -type l -ls | head
```

---

## What's Included

### Contexts

Pre-written boot instructions loaded by your AI agent at session start.

| File | Description |
|------|-------------|
| `contexts/global.md` | Universal engineering standards (commits, code review, DRY, testing) |
| `contexts/python.md` | Python conventions (type hints, Pydantic, ruff, uv) |
| `contexts/typescript.md` | TypeScript conventions (strict mode, Zod, no `any`) |
| `contexts/react.md` | React conventions (functional components, hooks patterns) |
| `contexts/go.md` | Go conventions (error handling, interfaces, formatting) |

### Knowledge

Example decisions, lessons, and facts covering engineering practices — ready for you to extend.

### Skills

- `skills/code-review/` — structured code-review workflow
- `skills/generate-tests/` — test scaffolding procedure
- `skills/record-knowledge/` — systematically capture decisions, lessons, and facts during agent sessions

---

## Day-to-day Workflow

Under the symlink-based sync model, the warehouse clone is the single write entrypoint for every harness artifact on your machine. Editing through a project symlink writes directly into the warehouse working tree.

```
1. abc sync                              — only needed when beacon.yaml changes or symlinks drift
2. code with agent                       — agent uses the symlinked contexts, knowledge, and skills
3. abc warehouse status                  — see what you've changed (scoped by beacon.yaml)
4. abc warehouse contribute -m "…" --push — commit and push the edits in the warehouse
```

Teammates pulling the updated warehouse see the new content through their existing project symlinks — they do not need to re-run `abc sync` on each project unless their `beacon.yaml` changed.

---

## Customising for Your Team

Fork the public starter warehouse and make it your own:

- Edit context files to reflect your team's actual standards
- Add knowledge entries as decisions and lessons accumulate
- Add skills for your team's recurring workflows
- Push to your own git host and share the clone URL with your team

See the [Agentic Beacon docs](https://github.com/Shadowsong27/agentic-beacon) and the [single-warehouse-write-entrypoint decision](../../knowledge/decisions/single-warehouse-write-entrypoint.md) for the model's full rationale.
