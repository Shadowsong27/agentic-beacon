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

- **`pending.yaml` tracks warehouse artifacts authored in the current project but not yet wired into `beacon.yaml`.** Every successful `record-knowledge` or `record-skill` invocation appends an entry to `.agentic-beacon/pending.yaml`. The file is gitignored automatically.
- **`.last-adopt` records the timestamp of the most recent `abc adopt` session.** Written to `.agentic-beacon/.last-adopt` in ISO-8601 UTC format. Also gitignored automatically.
- **Three-way `abc adopt` flow (accept / reject / defer).** Each pending entry can be individually accepted (wired into `beacon.yaml` + symlinked), rejected (removed from pending only), or deferred (kept in pending for a later session). A confirmation screen shows projected mutations before any filesystem writes.
- **Atomic rollback on `abc adopt` commit failure.** If any write fails mid-commit, `beacon.yaml`, `pending.yaml`, and `.last-adopt` are restored to their pre-adopt state automatically.
- **Pending artifact alert on every `abc` subcommand.** When `.agentic-beacon/pending.yaml` is non-empty, every `abc` invocation prints a one-line stderr notice: `⚠ N pending artifacts. Run 'abc adopt' to wire them.` Exit code is unaffected.

- **Removed `artifacts.knowledge` from `beacon.yaml`.** Knowledge is now auto-derived from markdown links inside adopted contexts and skills. On first sync after upgrade, any existing `artifacts.knowledge` list is silently dropped and a single INFO log is emitted. To keep a knowledge file available, ensure it is referenced by a markdown link from an adopted context or skill.
- **Agent dependencies moved from frontmatter to `agents/agents.yaml`.** `requires:` blocks in agent frontmatter are no longer supported. Agent skill dependencies must be declared in `agents/agents.yaml` instead. `abc sync` and `abc warehouse status` will hard-error if agent files contain `requires:` frontmatter or if `agents/agents.yaml` is missing/malformed. See [Migration Guide: Artifact Dependencies via Frontmatter](./docs/migrations/artifact-dependencies-frontmatter.md) for upgrade instructions.

### Added

- **Knowledge artifacts are now auto-derived.** `abc sync` scans markdown links inside all adopted contexts and skills, resolves them against the warehouse, and automatically symlinks any `.md` file under `knowledge/` into the project. No manual `artifacts.knowledge` entries are required.
- **Agents are now first-class adoptable artifacts.** You can adopt agents via `abc adopt` and they are tracked in `beacon.yaml` under `artifacts.agents`. Agents declared in frontmatter dependencies are pulled in transitively just like contexts and skills.

### Migration

- See [Migration Guide: Artifact Dependencies via Frontmatter](./docs/migrations/artifact-dependencies-frontmatter.md) for step-by-step instructions on adding `requires:` frontmatter to existing warehouses.
