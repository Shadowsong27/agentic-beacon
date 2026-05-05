<p align="center">
  <img src="agentic-beacon-banner.png" alt="Agentic Beacon" width="100%" />
</p>

<p align="center">
  <a href="https://github.com/Shadowsong27/agentic-beacon/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Shadowsong27/agentic-beacon" alt="License: MIT" /></a>
  <a href="https://pypi.org/project/agentic-beacon/"><img src="https://img.shields.io/pypi/pyversions/agentic-beacon" alt="Python Version" /></a>
  <a href="https://github.com/Shadowsong27/agentic-beacon/stargazers"><img src="https://img.shields.io/github/stars/Shadowsong27/agentic-beacon" alt="GitHub Stars" /></a>
  <a href="https://github.com/Shadowsong27/agentic-beacon/pulls"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="PRs Welcome" /></a>
</p>

**The package manager for AI coding agents. Centrally manage and distribute contexts, knowledge, and skills across your team — with native support for Claude Code and OpenCode.**

> *Git for AI Prompts. DRY for AI Agents.*

Agentic Beacon provides:
1. 🗂️ **A methodology** for managing contexts, knowledge, and skills — the core agentic engineering artifacts worthy of standardization and team-wide distribution
2. 🛠️ **CLI tooling (`abc`)** for initializing warehouses, managing connections, and distributing artifacts across projects

> **Built for multiplayer.** Agentic Beacon is designed as a team tool first. The warehouse model is built around shared ownership, bidirectional contribution, and the compounding benefits of a growing knowledge base — value that scales with the number of people and projects contributing to it. Solo use is fully supported (many start that way), but the tool was built with multiplayer in mind.

## The Problem

When a team adopts AI coding agents, each project accumulates its own `AGENTS.md` or `CLAUDE.md`. Standards diverge. A pattern discovered in one repo never reaches the others. When guidelines change, someone copy-pastes updates into 15 repos and misses three.

This is **Context Drift** — the same DRY problem that version control solved for code, except it hasn't been solved yet for agentic engineering artifacts.

- **Reinvention at every project.** Context files get written from scratch for each new repo, with variations that accumulate over time.
- **Knowledge stays siloed.** Lessons learned in one project never leave that developer's laptop.
- **No feedback loop.** When an agent session produces a better approach, there's no workflow to share it.

## How It Works

There are two moving parts:

**Warehouse** — a single git repository owned by your team. It holds the shared source of truth: contexts, knowledge, skills, and agent definitions. Cloned locally on every developer's machine; commit it like any other repo.

**Beacon** — a per-project connector. Running `abc warehouse connect` creates `.agentic-beacon/` in your project with a `beacon.yaml` that declares which contexts and skills this project needs.

```
Warehouse clone (local git repo)              Your project / global
────────────────────────────                  ────────────────────────────────
contexts/    ── abc sync (symlink) ──►  .agentic-beacon/artifacts/contexts/
                                        opencode.json / AGENTS.md (wired)
skills/      ── abc sync (symlink) ──►  .agentic-beacon/artifacts/skills/
                                        .opencode/skills/<name>/  (wired)
                                        .claude/skills/<name>/    (wired)
knowledge/   ── auto-derived      ──►  .agentic-beacon/artifacts/knowledge/
             (from markdown links            (symlinked on demand)
              in contexts & skills)
agents/      ── abc agents sync   ──►  ~/.claude/agents/<name>.md
             (symlink)                  ~/.config/opencode/agents/<name>.md
```

`abc sync` reads `beacon.yaml` and creates per-file **symlinks** from `.agentic-beacon/artifacts/` into your local warehouse clone, then wires skills into each detected tool's live directories. One logical artifact, one physical file per machine — no duplicate copies, no merge-back cycle.

**Knowledge is auto-derived.** There is no `knowledge:` key in `beacon.yaml`. Instead, `abc sync` scans markdown links inside your adopted contexts and skills, resolves any that point to warehouse knowledge files, and symlinks them transitively. Add a knowledge file to a context — it appears on next sync. Remove the last reference — the symlink is pruned automatically.

**Frontmatter dependencies.** Agents and skills can declare `requires:` in YAML frontmatter to express cross-artifact dependencies. `abc sync` validates that every required context or skill is adopted and errors early if any are missing.

**Agents are symlinked.** Like other artifacts, global agent files are per-file symlinks into the warehouse clone, not copies. Edits made in `~/.claude/agents/` or `~/.config/opencode/agents/` land directly in the warehouse working tree. Install them with `abc agents sync` (all at once) or `abc install agents/<name>.md` (one at a time).

When a session produces something worth sharing, you edit the file in place — the edit lands directly in the warehouse working tree through the symlink — and commit it with `abc warehouse contribute -m "…"`. Teammates pull the warehouse and the new content is visible through their existing project symlinks with no per-project resync.

> **Read:** [Decision — Single Warehouse Write Entrypoint](./knowledge/decisions/single-warehouse-write-entrypoint.md) for why the model works this way.

> **Platform support:** macOS and Linux only. Windows is not supported by `abc sync`.

> See **[Getting Started](./guides/getting-started.md)** for a full walkthrough with examples.

## Artifact Types

Four types form the core of a warehouse, each defined by two axes: **project scope** and **tool specificity**:

|  | Tool-agnostic | Tool-specific |
|---|---|---|
| **Project-scoped** | 📄 Contexts · 🧠 Knowledge | ⚡ Skills |
| **Global** | — | 🤖 Agents |

- **Contexts** — boot instructions and coding standards; wired into `opencode.json` / `AGENTS.md` automatically on sync.
- **Knowledge** — atomic decisions, lessons, and facts; symlinked under `.agentic-beacon/artifacts/` and referenced from contexts.
- **Skills** — reusable workflows wired as slash commands into each tool's live directories.
- **Agents** — sub-agent definitions installed as symlinks into global tool directories (`~/.claude/agents/`, `~/.config/opencode/agents/`) and available across every project. Edits flow back to the warehouse through the symlink — same write model as other artifact types.

> See **[Artifact Type Matrix](./docs/artifact-type-matrix.md)** for the full design rationale and how this drives command behaviour.

## Interactive Artifact Adoption

`abc adopt` opens an interactive TUI to browse and select warehouse artifacts. Scroll through contexts, skills, and agents — press `Space` to select, `Enter` to confirm. `beacon.yaml` is updated with your selections; knowledge is derived automatically on the next `abc sync` based on markdown links inside the adopted artifacts.

<p align="center">
  <img src="docs/screenshots/adopt-tui.png" alt="abc adopt TUI" width="100%" />
</p>

**Keyboard shortcuts:**

| Key | Action |
|-----|--------|
| `Space` | Toggle selection |
| `Enter` | Confirm and write to beacon.yaml |
| `a` / `n` | Select all / Select none |
| `t` | Toggle show-all (view already-adopted artifacts) |
| `Esc` / `q` | Cancel |

## Quickstart

### Installation

```bash
# Recommended — install once, use anywhere
uv tool install agentic-beacon

# Alternatives: pipx install agentic-beacon  |  pip install agentic-beacon
# Offline / air-gapped: download a platform bundle from the GitHub Releases page
```

### Get Started

**Starting fresh (no warehouse exists yet)**

```bash
# 1. Create your team warehouse
abc warehouse init my-org-warehouse
cd my-org-warehouse
# add contexts, knowledge, skills — then push to git

# 2. Connect a project (warehouse must be a local clone)
cd ~/my-project
abc warehouse connect --path ~/my-org-warehouse

# 3. Adopt artifacts interactively, then sync
abc adopt            # browse + select artifacts via TUI, writes beacon.yaml
abc sync             # creates symlinks into the warehouse clone, wires agent config
```

**Joining a team that already has a warehouse**

```bash
git clone git@github.com:your-org/warehouse.git ~/my-org-warehouse

cd ~/my-project
abc warehouse connect --path ~/my-org-warehouse
abc adopt
abc sync
```

### Day-to-day Workflow

```
1. code with agent                          — agent uses the symlinked contexts, knowledge, and skills
2. abc warehouse status                     — see warehouse edits you've made (scoped by beacon.yaml)
3. abc warehouse contribute -m "…" --push   — commit and push the edits in the warehouse
4. teammates git pull                       — updated content visible through their existing symlinks immediately
```

`abc sync` is only needed again when your `beacon.yaml` changes (new artifacts declared) or when symlinks drift (missing/broken targets) — not per warehouse update.

## When to Use Agentic Beacon

| Use it when… | Skip it when… |
|---|---|
| You have multiple projects that should share the same agent instructions | You have a single project with no plans to standardize across repos |
| Your team keeps rewriting the same contexts and skills from scratch in each repo | You need a one-off codebase bundle to feed into a chat session |
| Knowledge from one coding session should compound across the whole team | You need production observability for LLM calls in a deployed app |
| You want agent edits from any session to flow back into a shared, version-controlled source | Your team has no shared git workflow or central warehouse makes no sense for your setup |
| You're running multiple AI tools (Claude Code, OpenCode) and want one source of truth for all of them | |

## Documentation

### Conceptual Design (docs/)
- **[Artifact Type Matrix](./docs/artifact-type-matrix.md)** — Scope and tool-specificity axes; how they drive command design
- **[Agentic Warehouse Design](./docs/agentic-warehouse-design.md)** — High-level design and architecture
- **[Boot Context Design](./docs/boot-context-design/)** — AGENTS.md architecture and patterns
- **[Spec-Driven Development](./docs/spec-driven-development.md)** — Structured approach to feature planning
- **[Migration: Artifact Dependencies via Frontmatter](./docs/migrations/artifact-dependencies-frontmatter.md)** — Migrate warehouses to auto-derived knowledge and `requires:` frontmatter

### Practical Guides (guides/)
- **[Getting Started](./guides/getting-started.md)** — Full onboarding walkthrough
- **[Warehouse Creation](./guides/warehouse-creation.md)** — Creating and structuring a warehouse
- **[Contributing Back](./guides/warehouse-contribution-guide.md)** — Commit agent improvements back to the warehouse
- **[beacon.yaml Reference](./guides/beacon-yaml-reference.md)** — Full configuration schema
- **[Team Collaboration](./guides/team-collaboration.md)** — Multi-team workflows
- **[Advanced Patterns](./guides/advanced-patterns.md)** — Glob patterns, dry-run, warehouse commands, migration

### Examples (examples/)
- **[Sample Warehouse](./examples/sample-warehouse/)** — Mirror of the public starter warehouse

## CLI Reference

| Command | Description |
|---------|-------------|
| `abc warehouse init <dir>` | Initialize a new warehouse repository |
| `abc warehouse connect --path <path>` | Connect a project to a local warehouse clone |
| `abc warehouse status [<path>] [--all]` | Show uncommitted warehouse edits (scoped by `beacon.yaml` unless `--all`) |
| `abc warehouse contribute -m "…" [--push]` | Commit warehouse edits, optionally push |
| `abc warehouse list` | List artifacts available in the connected warehouse |
| `abc warehouse template-upgrade` | Upgrade template-generated files in an existing warehouse |
| `abc adopt` | Interactively browse and select warehouse artifacts via TUI; writes to `beacon.yaml` |
| `abc sync` | Create/repair symlinks for all artifacts declared in `beacon.yaml`; wires agent config |
| `abc sync --dry-run` | Preview the symlink operations without touching the filesystem |
| `abc sync --contribute-local` / `--discard-local` | Non-interactive migration from a copy-based tree |
| `abc doctor` | Validate project health: warehouse connection, `beacon.yaml` validity, broken symlinks |
| `abc agents sync` | Symlink all warehouse agent definitions into global tool directories (`--force` to overwrite conflicts) |
| `abc reset` | Force-rebuild all symlinks from the warehouse |
| `abc list` | List synced artifacts; `abc list agents` shows globally installed agents |
| `abc status` | Show current warehouse connection and project sync status |
| `abc clean` | Remove synced artifacts from the project |

**Platform support:** macOS and Linux only.

---

If you find Agentic Beacon useful, consider [giving it a star](https://github.com/Shadowsong27/agentic-beacon) — it helps others discover the project.

**Last Updated:** 2026-05-05
