# Changelog

## [2.0.0] (Unreleased)

### ⚠ BREAKING CHANGES

* `abc init` has been moved to `abc warehouse init`
* New config-based artifact management replaces direct file copying

### Features

* **config**: Add beacon.yaml for declarative artifact dependency management
* **config**: Add config.toml for warehouse connection persistence
* **sync**: Implement `abc sync` command with pure copy (no symlinks) from warehouse
* **sync**: Add `--preserve` flag to skip locally modified files during sync
* **sync**: Add `--prune` flag to remove artifacts no longer in beacon.yaml
* **sync**: Add `--verbose` flag for detailed sync output
* **delta**: Implement `abc delta` command with hash-based summary comparison
* **delta**: Add detailed `abc delta <file>` with git diff --no-index integration
* **delta**: Add color output and `--no-color` flag for diffs
* **setup**: Implement `abc setup` command with three workflows (agent-assisted, manual, skip)
* **setup**: Add agent-assisted workflow with warehouse catalog generation
* **warehouse**: Add `abc warehouse connect` command for warehouse connection
* **gitignore**: Automatic .gitignore management (exclude config.toml, artifacts/)
* **skill**: Add project-setup skill for AI-agent-assisted beacon.yaml population

### Code Refactoring

* Move `abc init` to `abc warehouse init` with deprecation error for old command
* Separate warehouse management commands under `abc warehouse` subgroup
* Keep client operations (sync, delta, setup) at top level

## [1.1.0](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v1.0.0...agentic-beacon@v1.1.0) (2026-03-07)


### Features

* add Beacon CLI tool for warehouse distribution ([48c9dae](https://github.com/Shadowsong27/agentic-beacon/commit/48c9daeaa2b967f55ab461c713ab6fdd5b1c0802))
* add beacon init command to bootstrap warehouses ([3cf5a52](https://github.com/Shadowsong27/agentic-beacon/commit/3cf5a52387b63dcf9fd1ee0fde383d847e3e395e))


### Bug Fixes

* force release for agentic-beacon ([7d92917](https://github.com/Shadowsong27/agentic-beacon/commit/7d929170e01c172843e68a8d937e9f78896d2c03))


### Code Refactoring

* rename to Agentic Beacon with abc CLI command ([b2e6ab9](https://github.com/Shadowsong27/agentic-beacon/commit/b2e6ab9b331990ce01436278e103d4e8e4c9b3bc))


### Miscellaneous Chores

* prepare for public PyPI release ([8fe4a68](https://github.com/Shadowsong27/agentic-beacon/commit/8fe4a68c44df27a9b219a1bba25869f13e76cb1c))


### CI/CD

* add GitHub Actions workflows for PyPI publishing ([87e15a4](https://github.com/Shadowsong27/agentic-beacon/commit/87e15a4f5821b8e5d02ae8e7c2824346f523fb25))
