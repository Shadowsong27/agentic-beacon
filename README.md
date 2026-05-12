<p align="center">
  <img src="agentic-beacon-banner.png?v=2" alt="Agentic Beacon" width="100%" />
</p>

<p align="center">
  <a href="https://github.com/Shadowsong27/agentic-beacon/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Shadowsong27/agentic-beacon" alt="License: MIT" /></a>
  <a href="https://pypi.org/project/agentic-beacon/"><img src="https://img.shields.io/pypi/pyversions/agentic-beacon" alt="Python Version" /></a>
  <a href="https://github.com/Shadowsong27/agentic-beacon/stargazers"><img src="https://img.shields.io/github/stars/Shadowsong27/agentic-beacon" alt="GitHub Stars" /></a>
  <a href="https://github.com/Shadowsong27/agentic-beacon/pulls"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="PRs Welcome" /></a>
  <a href="https://shadowsong27.github.io/agentic-beacon/"><img src="https://img.shields.io/badge/docs-online-blue.svg" alt="Documentation" /></a>
</p>

**The package manager for AI coding agents. Centrally manage and distribute contexts, knowledge, and skills across your team — with native support for Claude Code and OpenCode.**

> *Git for AI Prompts. DRY for AI Agents.*

## Quickstart

### Installation

```bash
uv tool install agentic-beacon
```

> Air-gapped? Download the wheel from the [Releases page](https://github.com/Shadowsong27/agentic-beacon/releases) and run `uv tool install ./agentic-beacon-*.whl`.

### First-time Setup

**Starting fresh (no warehouse exists yet)**

```bash
# 1. Create your team warehouse — a git repo that holds shared agent artifacts
abc warehouse init my-org-warehouse
cd my-org-warehouse
# add contexts, knowledge, skills — then push to git

# 2. Connect a project to the warehouse
cd ~/my-project
abc warehouse connect --path ~/my-org-warehouse

# 3. Pick artifacts and sync
abc adopt   # interactive TUI — browse and select contexts, skills, agents
abc sync    # creates per-file symlinks, wires contexts into Claude Code / OpenCode
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
abc adopt                               — pick up new artifacts from the warehouse
abc sync                                — repair symlinks after beacon.yaml changes

code with agent                         — agent reads symlinked contexts, knowledge, and skills

abc warehouse status                    — see warehouse edits you've made this session
abc warehouse contribute -m "…" --push  — commit and push back to the warehouse
teammates git pull                      — they get the update immediately, no resync needed
```

`abc sync` is only needed when your `beacon.yaml` changes or symlinks drift — not on every warehouse pull.

## Interactive Artifact Adoption

`abc adopt` opens an interactive TUI to browse warehouse artifacts. Press `Space` to select, `Enter` to confirm. `beacon.yaml` is updated with your selections; knowledge files referenced inside contexts and skills are pulled in automatically on the next `abc sync`.

<p align="center">
  <img src="docs/screenshots/adopt-tui.png" alt="abc adopt TUI" width="100%" />
</p>

| Key | Action |
|-----|--------|
| `Space` | Toggle selection |
| `Enter` | Confirm and write to beacon.yaml |
| `a` / `n` | Select all / Select none |
| `t` | Toggle show-all (view already-adopted artifacts) |
| `Esc` / `q` | Cancel |

## The Problem

When a team adopts AI coding agents, each project accumulates its own `AGENTS.md` or `CLAUDE.md`. Standards diverge. A pattern discovered in one repo never reaches the others. When guidelines change, someone copy-pastes updates into 15 repos and misses three.

This is **Context Drift** — the same DRY problem that version control solved for code, except it hasn't been solved for agentic engineering artifacts yet.

## How It Works

There are two moving parts:

**Warehouse** — a single git repository owned by your team. It holds the shared source of truth: contexts, knowledge, skills, and agent definitions. Cloned locally on every developer's machine; commit it like any other repo.

**Beacon** — a per-project connector. Running `abc warehouse connect` creates `.agentic-beacon/` in your project with a `beacon.yaml` that declares which contexts, skills, and agents this project needs.

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
agents/      ── abc sync (symlink) ──►  .claude/agents/<name>.md
                                         .opencode/agents/<name>.md
```

Everything is a per-file **symlink** into the warehouse clone — one physical file per artifact per machine, no duplicate copies. Edits made through any symlink (project artifacts or global agent files) land directly in the warehouse working tree. Commit with `abc warehouse contribute` and teammates get it through their existing symlinks on the next `git pull` — no per-project resync.

**Knowledge is auto-derived.** There is no `knowledge:` key in `beacon.yaml`. `abc sync` scans markdown links inside adopted contexts and skills, resolves warehouse knowledge references, and symlinks them transitively. Add a reference — it appears. Remove the last one — the symlink is pruned.

**Frontmatter dependencies.** Skills declare `requires:` in YAML frontmatter; agents declare dependencies in `agents/agents.yaml`. `abc sync` validates all declared dependencies are adopted and errors early if any are missing.

> **Read:** [Decision — Single Warehouse Write Entrypoint](docs/no-project-overrides.md) for the full design rationale.

> **Platform support:** macOS and Linux only.

## Artifact Types

|  | Tool-agnostic | Tool-specific |
|---|---|---|
| **Project-scoped** | 📄 Contexts · 🧠 Knowledge | ⚡ Skills · 🤖 Agents |
| **Global** | — | — |

- **Contexts** — boot instructions and coding standards; wired into `opencode.json` / `AGENTS.md` automatically on sync.
- **Knowledge** — atomic decisions, lessons, and facts; auto-derived from markdown links in contexts and skills.
- **Skills** — reusable workflows wired as slash commands into each tool's live directories.
- **Agents** — sub-agent definitions declared per-project in `beacon.yaml` and symlinked into project-local `.claude/agents/` and `.opencode/agents/`; edits flow back to the warehouse through the symlink.

> See **[Artifact Type Matrix](./docs/artifact-type-matrix.md)** for the full design rationale.

## When to Use Agentic Beacon

| Use it when… | Skip it when… |
|---|---|
| You have multiple projects that should share the same agent instructions | You have a single project with no plans to standardize across repos |
| Your team keeps rewriting the same contexts and skills from scratch in each repo | You need a one-off codebase bundle to feed into a chat session |
| Knowledge from one coding session should compound across the whole team | You need production observability for LLM calls in a deployed app |
| You want agent edits from any session to flow back into a shared, version-controlled source | Your team has no shared git workflow or a central warehouse makes no sense for your setup |
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
- **[CLI Reference](./docs/cli-reference.md)** — Full command reference

### Examples (examples/)
- **[Beacon Configs](./examples/beacon-configs/)** — Example `beacon.yaml` configurations for common project setups

---

If you find Agentic Beacon useful, consider [giving it a star](https://github.com/Shadowsong27/agentic-beacon) — it helps others discover the project.

**Last Updated:** 2026-05-05
