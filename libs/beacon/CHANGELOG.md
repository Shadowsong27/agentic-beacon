# Changelog

## [2.0.0](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v1.6.0...agentic-beacon@v2.0.0) (2026-03-15)


### ⚠ BREAKING CHANGES

* redesign list operations — abc list <type> and abc warehouse list <type> ([#28](https://github.com/Shadowsong27/agentic-beacon/issues/28))

### Features

* redesign list operations — abc list &lt;type&gt; and abc warehouse list &lt;type&gt; ([#28](https://github.com/Shadowsong27/agentic-beacon/issues/28)) ([fdea11a](https://github.com/Shadowsong27/agentic-beacon/commit/fdea11a1a043418ecd8cc37c288958d6ab1c1bf7))

## [1.6.0](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v1.5.1...agentic-beacon@v1.6.0) (2026-03-15)


### Features

* abc install updates beacon.yaml for idempotent future syncs ([d89427d](https://github.com/Shadowsong27/agentic-beacon/commit/d89427d173d6aa1c5678f5a7d553769a144a1fc9))
* add abc install &lt;artifact&gt; command, remove abc skill install ([a41461a](https://github.com/Shadowsong27/agentic-beacon/commit/a41461a34fa420b38cb4f0de3adf248c5e748722))

## [1.5.1](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v1.5.0...agentic-beacon@v1.5.1) (2026-03-14)


### Bug Fixes

* onboarding clarity and sync auto-wiring ([#25](https://github.com/Shadowsong27/agentic-beacon/issues/25)) ([74d2cdd](https://github.com/Shadowsong27/agentic-beacon/commit/74d2cdd721f3fc9843e5cf39d02fd91a3a7cde84))


### Documentation

* update warehouse init README template with current CLI commands and offline install ([2f07f12](https://github.com/Shadowsong27/agentic-beacon/commit/2f07f12143ca4c559f2aac3bd2a51b4c76ad1a7a))

## [1.5.0](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v1.4.1...agentic-beacon@v1.5.0) (2026-03-13)


### Features

* allow abc warehouse init to run in an existing directory ([#20](https://github.com/Shadowsong27/agentic-beacon/issues/20)) ([c8385ba](https://github.com/Shadowsong27/agentic-beacon/commit/c8385baaa0417f70ad01a23e0252fc8f5022d7eb))

## [1.4.1](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v1.4.0...agentic-beacon@v1.4.1) (2026-03-13)


### Bug Fixes

* **delta:** show untracked local skills in abc delta output ([#18](https://github.com/Shadowsong27/agentic-beacon/issues/18)) ([3afabfd](https://github.com/Shadowsong27/agentic-beacon/commit/3afabfd39401bad33b26a9645792568daa459ae6))

## [1.4.0](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v1.3.0...agentic-beacon@v1.4.0) (2026-03-11)


### Features

* **contribute:** auto-register untracked artifacts in beacon.yaml after contribution ([d4ec6e9](https://github.com/Shadowsong27/agentic-beacon/commit/d4ec6e946076feec1ee2a325c507d453aee359c9))

## [1.3.0](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v1.2.0...agentic-beacon@v1.3.0) (2026-03-11)


### Features

* add abc contribute command and fix delta to detect locally-added files ([#16](https://github.com/Shadowsong27/agentic-beacon/issues/16)) ([d20aeae](https://github.com/Shadowsong27/agentic-beacon/commit/d20aeae55d7cb5311d7d77671e9f7d93ba7d0fce))
* add abc skill install command to register skills as agent commands ([#14](https://github.com/Shadowsong27/agentic-beacon/issues/14)) ([fc8d97a](https://github.com/Shadowsong27/agentic-beacon/commit/fc8d97a017cd9c527be0dc6878fa143b505f7604))
* bundle record-knowledge skill into every new warehouse on abc init ([#13](https://github.com/Shadowsong27/agentic-beacon/issues/13)) ([58e4aaf](https://github.com/Shadowsong27/agentic-beacon/commit/58e4aaf6e7a041e218f40d6d19bd2ecd30328771))


### Documentation

* document required context wiring step after abc sync ([bd26b4c](https://github.com/Shadowsong27/agentic-beacon/commit/bd26b4c9778c92604c07a7b283b31cbc590a3517)), closes [#9](https://github.com/Shadowsong27/agentic-beacon/issues/9)

## [1.2.0](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v1.1.0...agentic-beacon@v1.2.0) (2026-03-10)


### Features

* **beacon:** implement phase 1 configuration management with pydantic settings ([176fbb3](https://github.com/Shadowsong27/agentic-beacon/commit/176fbb31bd10fbb1f10abb85bf05f7933f731ff3))
* config-based artifact management (v2.0) ([#4](https://github.com/Shadowsong27/agentic-beacon/issues/4)) ([3968040](https://github.com/Shadowsong27/agentic-beacon/commit/3968040f4598ac9b05365cd55ad619024b261b8e))
* implement config-based artifact management (v2.0) ([a2526f2](https://github.com/Shadowsong27/agentic-beacon/commit/a2526f2a5134f43a5e997fb215ca5aa6e5dc29b7))
* implement Phase 2 warehouse validation with TDD ([c336b31](https://github.com/Shadowsong27/agentic-beacon/commit/c336b31c6f3d1185805dc1d4bdfb10f42a1a583e))


### Bug Fixes

* correct abc sync knowledge path resolution and update task tracking ([#3](https://github.com/Shadowsong27/agentic-beacon/issues/3)) ([544db47](https://github.com/Shadowsong27/agentic-beacon/commit/544db47ab14e9937f381b1cd662551ed88ee7d75))
* resolve 4 cli bugs found during e2e testing and add regression c… ([#7](https://github.com/Shadowsong27/agentic-beacon/issues/7)) ([1d24465](https://github.com/Shadowsong27/agentic-beacon/commit/1d244653142ad9a6f94cee7df98b6f4e68463424))


### Documentation

* establish project context and clean up repository structure ([d3237aa](https://github.com/Shadowsong27/agentic-beacon/commit/d3237aa0963ca02c14e6eb1e5a73c1c81f1308e5))
* update installation instructions to recommend uv tool install ([9f54c90](https://github.com/Shadowsong27/agentic-beacon/commit/9f54c900f35ee44c82965c43c458dac0b5017f2d))


### Tests

* add comprehensive TDD test suite for Phase 1 (Configuration Management) ([1b5b958](https://github.com/Shadowsong27/agentic-beacon/commit/1b5b95823bb95867fb7988cf35e6bdebb8da8dd7))


### Miscellaneous Chores

* add pre-commit hooks with ruff linting and formatting ([#8](https://github.com/Shadowsong27/agentic-beacon/issues/8)) ([d96130e](https://github.com/Shadowsong27/agentic-beacon/commit/d96130ee8af973da3c3ec08cea26b0b4a15ffb0e))
* make AGENTS.md the SSOT and tidy repo tooling ([#6](https://github.com/Shadowsong27/agentic-beacon/issues/6)) ([15e02bf](https://github.com/Shadowsong27/agentic-beacon/commit/15e02bffa1d5dfb25eb4e0d5e2a30fb26089af7f))

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
