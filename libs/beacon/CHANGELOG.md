# Changelog

## [2.4.0](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v2.3.0...agentic-beacon@v2.4.0) (2026-04-07)


### Features

* auto-prune sync, agent contribute, and dedicated agents delta section ([53490d2](https://github.com/Shadowsong27/agentic-beacon/commit/53490d26526f32869c19befdfe9ab8a86335d059))


### Bug Fixes

* always wire skills to agent dirs regardless of agent config (PER-56) ([#81](https://github.com/Shadowsong27/agentic-beacon/issues/81)) ([5657ef1](https://github.com/Shadowsong27/agentic-beacon/commit/5657ef13b6e862e0dfd4f624b754045f38a595bd))

## [2.3.0](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v2.2.0...agentic-beacon@v2.3.0) (2026-03-30)


### Features

* contribute/delta/sync UX improvements ([c6a7893](https://github.com/Shadowsong27/agentic-beacon/commit/c6a7893f9b32690ff560cf611f5b284b727ea658))


### Bug Fixes

* force release for agentic-beacon ([48dc721](https://github.com/Shadowsong27/agentic-beacon/commit/48dc72175729c5dc78ea7ca4a2fb2a1d5893e35f))

## [2.2.0](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v2.1.3...agentic-beacon@v2.2.0) (2026-03-28)


### Features

* add agents/ as first-class warehouse artifact type with global install ([#76](https://github.com/Shadowsong27/agentic-beacon/issues/76)) ([967be37](https://github.com/Shadowsong27/agentic-beacon/commit/967be37c4d875388eeba02e0a7710e76938475a6))


### Bug Fixes

* decouple bundled skill installation from warehouse sync (PER-43) ([#75](https://github.com/Shadowsong27/agentic-beacon/issues/75)) ([ef54410](https://github.com/Shadowsong27/agentic-beacon/commit/ef54410a9bf04d9230fe6ca0f189efc49048fbf2))


### Tests

* fix branch-switch integration test for CI git default branch ([#72](https://github.com/Shadowsong27/agentic-beacon/issues/72)) ([3813d1a](https://github.com/Shadowsong27/agentic-beacon/commit/3813d1aa2e8c06ac1753a56b48295ce93c89cf70))

## [2.1.3](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v2.1.2...agentic-beacon@v2.1.3) (2026-03-24)


### Bug Fixes

* add agent skill dirs to .gitignore template and detect claudecode via CLAUDE.md ([#71](https://github.com/Shadowsong27/agentic-beacon/issues/71)) ([ade1d54](https://github.com/Shadowsong27/agentic-beacon/commit/ade1d543607254dc7b926404fb935180ae2e48ac))
* prevent infinite delta cycle after abc contribute for multi-agent skills ([#69](https://github.com/Shadowsong27/agentic-beacon/issues/69)) ([d5dd086](https://github.com/Shadowsong27/agentic-beacon/commit/d5dd086079c6675720f01ef8d959a45c085b9a6a))

## [2.1.2](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v2.1.1...agentic-beacon@v2.1.2) (2026-03-22)


### Bug Fixes

* gitignore synced skill dirs in agent subdirectories ([#61](https://github.com/Shadowsong27/agentic-beacon/issues/61)) ([75999da](https://github.com/Shadowsong27/agentic-beacon/commit/75999daceb555fde583490b9e3c6d5d39fe583be))
* preserve bundled skills in agent-assisted setup and warn when missing ([#66](https://github.com/Shadowsong27/agentic-beacon/issues/66)) ([2239621](https://github.com/Shadowsong27/agentic-beacon/commit/2239621688288a67a37144d34be91d6bd6011bd3))
* remove auto-registration of artifacts in beacon.yaml from abc contribute ([#67](https://github.com/Shadowsong27/agentic-beacon/issues/67)) ([020f44a](https://github.com/Shadowsong27/agentic-beacon/commit/020f44a5864905aace81dc7d0e29652c5205371d)), closes [#56](https://github.com/Shadowsong27/agentic-beacon/issues/56)
* show failed file details in sync error summary ([#65](https://github.com/Shadowsong27/agentic-beacon/issues/65)) ([76daa39](https://github.com/Shadowsong27/agentic-beacon/commit/76daa394a202fa0afa12899c82aa6cc4c41d613f))
* surface no-agent-config prompt for skill wiring during abc sync ([#68](https://github.com/Shadowsong27/agentic-beacon/issues/68)) ([4f5c6b5](https://github.com/Shadowsong27/agentic-beacon/commit/4f5c6b56b4401b8b42e2afb228686dddc61cd518)), closes [#54](https://github.com/Shadowsong27/agentic-beacon/issues/54)

## [2.1.1](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v2.1.0...agentic-beacon@v2.1.1) (2026-03-19)


### Bug Fixes

* skip skill wiring when files are already up-to-date ([#59](https://github.com/Shadowsong27/agentic-beacon/issues/59)) ([7ce1a6a](https://github.com/Shadowsong27/agentic-beacon/commit/7ce1a6a8586db6a9e0cf2121b113ef6cab0aa5f2))

## [2.1.0](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v2.0.2...agentic-beacon@v2.1.0) (2026-03-19)


### Features

* auto git commit, push, and PR creation after abc contribute ([#44](https://github.com/Shadowsong27/agentic-beacon/issues/44)) ([#58](https://github.com/Shadowsong27/agentic-beacon/issues/58)) ([5b6b2fc](https://github.com/Shadowsong27/agentic-beacon/commit/5b6b2fc57bcc6fb4ac289ef08989fd13ab4228a0))
* block abc sync and abc contribute if warehouse has uncommitted changes ([#48](https://github.com/Shadowsong27/agentic-beacon/issues/48)) ([de97a10](https://github.com/Shadowsong27/agentic-beacon/commit/de97a10ad57d3016ad1f6e2a8c68f48b7317bdfd))
* extract warehouse init templates to files and add regression test ([#37](https://github.com/Shadowsong27/agentic-beacon/issues/37)) ([1b2edf9](https://github.com/Shadowsong27/agentic-beacon/commit/1b2edf99e7f515f42979a7e5388b0e5812a8e21c))
* integrate bundled skills into warehouse template lifecycle ([#57](https://github.com/Shadowsong27/agentic-beacon/issues/57)) ([1175c06](https://github.com/Shadowsong27/agentic-beacon/commit/1175c06d90f0f9ee1a1ff0b7672aabcb2bf157bd)), closes [#45](https://github.com/Shadowsong27/agentic-beacon/issues/45)
* marketing improvements to README and add starter warehouse staleness test ([#40](https://github.com/Shadowsong27/agentic-beacon/issues/40)) ([aeba1f3](https://github.com/Shadowsong27/agentic-beacon/commit/aeba1f30e361716a8c03eb3938fa8fd14f636918))
* prompt to initialise agent config during abc sync when none detected ([#43](https://github.com/Shadowsong27/agentic-beacon/issues/43)) ([736a610](https://github.com/Shadowsong27/agentic-beacon/commit/736a610e5bbb6f2fa30eb35d49ffc3242cd3cbcf))


### Bug Fixes

* fixed record-knowledge skill file write location ([#35](https://github.com/Shadowsong27/agentic-beacon/issues/35)) ([d57d8a5](https://github.com/Shadowsong27/agentic-beacon/commit/d57d8a53d4b825a755b013b215822e02db2ea96b))
* show full multi-agent skill diffs in abc delta ([#53](https://github.com/Shadowsong27/agentic-beacon/issues/53)) ([e23cbcc](https://github.com/Shadowsong27/agentic-beacon/commit/e23cbcc87d6941557f2a7df93900c02e5fd354c9))

## [2.0.2](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v2.0.1...agentic-beacon@v2.0.2) (2026-03-16)


### Bug Fixes

* abc contribute reads skills from live agent dirs not artifact snapshot ([#32](https://github.com/Shadowsong27/agentic-beacon/issues/32)) ([4480e1f](https://github.com/Shadowsong27/agentic-beacon/commit/4480e1ff16c940399ed1458a9f56ecc49ff10b53))

## [2.0.1](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v2.0.0...agentic-beacon@v2.0.1) (2026-03-16)


### Bug Fixes

* abc delta compares skills against live agent dirs not artifact snapshot ([eda5344](https://github.com/Shadowsong27/agentic-beacon/commit/eda53447eb13ececd6b98d939f7d605f3a53a61e))

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
