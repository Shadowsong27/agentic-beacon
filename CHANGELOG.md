# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Breaking Changes

- **`record-knowledge` no longer writes to `.agentic-beacon/artifacts/knowledge/` in the project.** All knowledge artifacts are written directly to the connected warehouse. Running `record-knowledge` without a connected warehouse hard-errors immediately. Existing project-local knowledge files under `.agentic-beacon/artifacts/knowledge/` are not removed, but new invocations will not create files there.
- **`record-skill` no longer invokes `create_skill.py`.** The `create_skill.py` helper script is retired. Skill scaffolding is now handled entirely by the warehouse-aware domain layer. Running `record-skill` without a connected warehouse hard-errors immediately.
- **Both `record-knowledge` and `record-skill` require a connected warehouse (hard error without one).** Projects that previously had no `beacon.yaml` / `config.toml` must run `abc warehouse connect <path>` before invoking either skill.

### Added

- **`pending.yaml` tracks project-wired warehouse artifacts authored in the current project but not yet wired into `beacon.yaml`.** Contexts, skills, and agents can be queued for `abc adopt`; knowledge files are auto-derived during sync/adopt and are not tracked in `pending.yaml`. The file is gitignored automatically.
- **`.last-adopt` records the timestamp of the most recent `abc adopt` session.** Written to `.agentic-beacon/.last-adopt` in ISO-8601 UTC format. Also gitignored automatically.
- **Three-way `abc adopt` flow (accept / reject / defer).** Each pending entry can be individually accepted (wired into `beacon.yaml` + symlinked), rejected (removed from pending only), or deferred (kept in pending for a later session). A confirmation screen shows projected mutations before any filesystem writes.
- **Atomic rollback on `abc adopt` commit failure.** If any write fails mid-commit, `beacon.yaml`, `pending.yaml`, and `.last-adopt` are restored to their pre-adopt state automatically.
- **Pending artifact alert on every `abc` subcommand.** When `.agentic-beacon/pending.yaml` is non-empty, every `abc` invocation prints a one-line stderr notice: `⚠ N pending artifacts. Run 'abc adopt' to wire them.` Exit code is unaffected.

- **Removed `artifacts.knowledge` from `beacon.yaml`.** Knowledge is now auto-derived from markdown links inside adopted contexts and skills. On first sync after upgrade, any existing `artifacts.knowledge` list is silently dropped and a single INFO log is emitted. To keep a knowledge file available, ensure it is referenced by a markdown link from an adopted context or skill.
- **Agent dependencies moved from frontmatter to `agents/agents.yaml`.** `requires:` blocks in agent frontmatter are no longer supported. Agent skill dependencies must be declared in `agents/agents.yaml` instead. `abc sync` and `abc warehouse status` will hard-error if agent files contain `requires:` frontmatter or if `agents/agents.yaml` is missing/malformed. See [Migration Guide: Artifact Dependencies via Frontmatter](./docs/archive/migrations/artifact-dependencies-frontmatter.md) for upgrade instructions.

### Added

- **Knowledge artifacts are now auto-derived.** `abc sync` scans markdown links inside all adopted contexts and skills, resolves them against the warehouse, and automatically symlinks any `.md` file under `knowledge/` into the project. No manual `artifacts.knowledge` entries are required.
- **Agents are now first-class adoptable artifacts.** You can adopt agents via `abc adopt` and they are tracked in `beacon.yaml` under `artifacts.agents`. Agents declared in frontmatter dependencies are pulled in transitively just like contexts and skills.

### Migration

- See [Migration Guide: Artifact Dependencies via Frontmatter](./docs/archive/migrations/artifact-dependencies-frontmatter.md) for step-by-step instructions on adding `requires:` frontmatter to existing warehouses.

### Breaking Changes (PER-113 — unify-agent-distribution)

- **`abc agents sync` command removed.** Agents are now wired into project-local `.claude/agents/` and `.opencode/agents/` directories by `abc sync`, not into global `~/.claude/agents/` or `~/.config/opencode/agents/`. Remove any references to `abc agents sync` from scripts or documentation.
- **Agent symlinks are project-scoped.** Each project independently declares agents in `beacon.yaml` and `abc sync` creates project-local symlinks. Global agent symlinks from previous versions are cleaned up automatically on the first `abc sync` run (a one-time migration notice is printed).

### Migration (PER-113)

- Run `abc sync` once in each project to migrate: legacy global agent symlinks pointing into the warehouse will be removed and project-local symlinks will be created for declared agents.
- If you previously relied on globally-installed agents visible across all projects, declare each agent explicitly in the relevant project's `beacon.yaml`.
