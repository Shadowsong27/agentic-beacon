# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Breaking Changes

- **Removed `artifacts.knowledge` from `beacon.yaml`.** Knowledge is now auto-derived from markdown links inside adopted contexts and skills. On first sync after upgrade, any existing `artifacts.knowledge` list is silently dropped and a single INFO log is emitted. To keep a knowledge file available, ensure it is referenced by a markdown link from an adopted context or skill.
- **Agents and skills must declare `requires:` YAML frontmatter.** `abc sync` will hard-error if an adopted agent or skill is missing a valid `requires` block. See [Migration Guide: Artifact Dependencies via Frontmatter](./docs/migrations/artifact-dependencies-frontmatter.md) for upgrade instructions.

### Added

- **Knowledge artifacts are now auto-derived.** `abc sync` scans markdown links inside all adopted contexts and skills, resolves them against the warehouse, and automatically symlinks any `.md` file under `knowledge/` into the project. No manual `artifacts.knowledge` entries are required.
- **Agents are now first-class adoptable artifacts.** You can adopt agents via `abc adopt` and they are tracked in `beacon.yaml` under `artifacts.agents`. Agents declared in frontmatter dependencies are pulled in transitively just like contexts and skills.

### Migration

- See [Migration Guide: Artifact Dependencies via Frontmatter](./docs/migrations/artifact-dependencies-frontmatter.md) for step-by-step instructions on adding `requires:` frontmatter to existing warehouses.
