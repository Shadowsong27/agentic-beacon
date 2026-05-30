# Changelog

## [3.5.1](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v3.5.0...agentic-beacon@v3.5.1) (2026-05-30)


### Bug Fixes

* **setup:** wrap agent partials with disable: true frontmatter (PER-238) ([#157](https://github.com/Shadowsong27/agentic-beacon/issues/157)) ([7289a80](https://github.com/Shadowsong27/agentic-beacon/commit/7289a80e1df662e83de7dab7a93041490eb50aa1))

## [3.5.0](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v3.4.0...agentic-beacon@v3.5.0) (2026-05-24)


### Features

* **doctor:** project-side symlink + [@path](https://github.com/path) integrity checks (PER-193) ([#155](https://github.com/Shadowsong27/agentic-beacon/issues/155)) ([ebb826c](https://github.com/Shadowsong27/agentic-beacon/commit/ebb826cd29924da177eac17762e83c1b9d330d05))


### Bug Fixes

* **adopt:** dedupe pending.yaml entries on write + read (PER-188) ([#154](https://github.com/Shadowsong27/agentic-beacon/issues/154)) ([4eac908](https://github.com/Shadowsong27/agentic-beacon/commit/4eac908f36e94f3de7dbf8da17b94d759c670c1e))
* **skills:** handle compound git porcelain status codes in draft_commit_message.py ([#152](https://github.com/Shadowsong27/agentic-beacon/issues/152)) ([34b7218](https://github.com/Shadowsong27/agentic-beacon/commit/34b7218b8b51ab630fcf60b0440311e9ef5901a8))
* **warehouse:** include tracked deleted files in summary + tracked-paths expansion (PER-186) ([#153](https://github.com/Shadowsong27/agentic-beacon/issues/153)) ([5765915](https://github.com/Shadowsong27/agentic-beacon/commit/5765915e63ae7d520935d6d02dd4895d756fc5ca))
* **warehouse:** make contribute + summarize warehouse-scoped (PER-202, PER-203) ([#156](https://github.com/Shadowsong27/agentic-beacon/issues/156)) ([6ad58c8](https://github.com/Shadowsong27/agentic-beacon/commit/6ad58c84c7e33d77de55f483cef68f7553e89fd0))
* **warehouse:** normalize --paths input before tracked-set membership check (PER-184) ([#151](https://github.com/Shadowsong27/agentic-beacon/issues/151)) ([daac8e0](https://github.com/Shadowsong27/agentic-beacon/commit/daac8e0ff6ff1fd7e4454672038f11e590533758))
* **warehouse:** surface out-of-scope dirty file count in status/contribute ([#148](https://github.com/Shadowsong27/agentic-beacon/issues/148)) ([96ce01c](https://github.com/Shadowsong27/agentic-beacon/commit/96ce01c97e1e5247c94890409e54145b1b88bca2))


### Documentation

* **agents:** document _partials convention + record detect_agent_targets gating decision ([8f6b0c6](https://github.com/Shadowsong27/agentic-beacon/commit/8f6b0c613b45e663fd98a943f7ef526a45529317))
* consolidate docs/ into mkdocs site (PER-190) ([#150](https://github.com/Shadowsong27/agentic-beacon/issues/150)) ([83b1fbf](https://github.com/Shadowsong27/agentic-beacon/commit/83b1fbf86adba0b2c902ff34838f5ad15454049b))


### Miscellaneous Chores

* **ci:** refresh agents/README.md template hashes after docs sync ([048b36e](https://github.com/Shadowsong27/agentic-beacon/commit/048b36ee3c2815a0332dcf66f16560264f7b1c43))

## [3.4.0](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v3.3.0...agentic-beacon@v3.4.0) (2026-05-17)


### Features

* **beacon:** canonicalize shared bundled-skill scripts under _shared/ ([#139](https://github.com/Shadowsong27/agentic-beacon/issues/139)) ([3259e41](https://github.com/Shadowsong27/agentic-beacon/commit/3259e415ee953c08fdb67369a01497feb45cf037))
* **beacon:** offline-aware skipif for bundled-skill integration tests ([#141](https://github.com/Shadowsong27/agentic-beacon/issues/141)) ([2b41d46](https://github.com/Shadowsong27/agentic-beacon/commit/2b41d46e2828c6026c11fa3dced06d3219d4aa59))
* **skills:** add contribute-warehouse bundled skill ([#146](https://github.com/Shadowsong27/agentic-beacon/issues/146)) ([552aded](https://github.com/Shadowsong27/agentic-beacon/commit/552aded2b084e43e7b2ae6ced0f4ac4801730256))
* **warehouse:** add abc warehouse lint command ([#144](https://github.com/Shadowsong27/agentic-beacon/issues/144)) ([817d60b](https://github.com/Shadowsong27/agentic-beacon/commit/817d60bbe58578856ae1503fbdab5e4ccd466349))


### Bug Fixes

* **distribution:** skip _partials/ in agent listings and co-distribute alongside wired agents ([#143](https://github.com/Shadowsong27/agentic-beacon/issues/143)) ([23e967d](https://github.com/Shadowsong27/agentic-beacon/commit/23e967dcd912dbd78d02bf435710c1dd09935f39))
* **warehouse:** include artifacts.agents in get_tracked_paths (PER-183) ([#147](https://github.com/Shadowsong27/agentic-beacon/issues/147)) ([c992725](https://github.com/Shadowsong27/agentic-beacon/commit/c99272594c9378a96b36f8c4f425dfe0550839ab))

## [3.3.0](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v3.2.0...agentic-beacon@v3.3.0) (2026-05-13)


### Features

* add more gitignore file natively to abc ([#132](https://github.com/Shadowsong27/agentic-beacon/issues/132)) ([72cfcdb](https://github.com/Shadowsong27/agentic-beacon/commit/72cfcdbb3ea081b1021591aefb969cfeaaa1d674))
* **setup:** auto-init agent config + wire bundled skills on adopt (PER-151) ([#137](https://github.com/Shadowsong27/agentic-beacon/issues/137)) ([5fe42cc](https://github.com/Shadowsong27/agentic-beacon/commit/5fe42ccbbb39c6fc27509af861267cefc0fd06e8))


### Bug Fixes

* **skills:** self-contained append_pending.py for record-* skills (PER-150) ([#136](https://github.com/Shadowsong27/agentic-beacon/issues/136)) ([388b724](https://github.com/Shadowsong27/agentic-beacon/commit/388b7247d33863d64040192c5675afb029e7c548))

## [3.2.0](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v3.1.0...agentic-beacon@v3.2.0) (2026-05-11)


### Features

* **warehouse:** make sync's main-branch check configurable ([#131](https://github.com/Shadowsong27/agentic-beacon/issues/131)) ([4d86b87](https://github.com/Shadowsong27/agentic-beacon/commit/4d86b873052e4f5b2d973f0798f5e50bc434aec0))


### Bug Fixes

* **record-knowledge:** allow nested kebab-case topics like data-platform/clickhouse ([6f238ba](https://github.com/Shadowsong27/agentic-beacon/commit/6f238bac4d22b70e272b2629b749e20db08a4607))

## [3.1.0](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v3.0.0...agentic-beacon@v3.1.0) (2026-05-10)


### Features

* **beacon:** wiring note when agents declared but no tool dirs (PER-121) ([#123](https://github.com/Shadowsong27/agentic-beacon/issues/123)) ([489801c](https://github.com/Shadowsong27/agentic-beacon/commit/489801c51c11db4fe2299042a194a834189bf986))


### Bug Fixes

* configure git identity in release e2e tests ([c767d6b](https://github.com/Shadowsong27/agentic-beacon/commit/c767d6b76e081b000e6f65bc78db81e414c84b7c))


### Code Refactoring

* **adoption:** filter agents from cleanup_unadopted_artifacts (PER-122) ([#125](https://github.com/Shadowsong27/agentic-beacon/issues/125)) ([5ee4137](https://github.com/Shadowsong27/agentic-beacon/commit/5ee4137740d8c311a969fce636e0ac4281339cfe))
* **beacon:** decouple abc list from SyncEngine via free function (PER-129) ([#124](https://github.com/Shadowsong27/agentic-beacon/issues/124)) ([8337383](https://github.com/Shadowsong27/agentic-beacon/commit/83373837ace18103f76950a9ac1f882de45a226c))
* **beacon:** one-domain-call-per-handler + AST architecture test (PER-120) ([#126](https://github.com/Shadowsong27/agentic-beacon/issues/126)) ([67a0996](https://github.com/Shadowsong27/agentic-beacon/commit/67a0996f9af5bec5d6c5496be585dc73e3f2373d))


### Tests

* **beacon:** audit deleted agent-sync edge cases (PER-126) ([#120](https://github.com/Shadowsong27/agentic-beacon/issues/120)) ([3948fea](https://github.com/Shadowsong27/agentic-beacon/commit/3948fea183a32bce29ad6782e709a8ede5566ea1))
* **integration:** tighten legacy cleanup notice assertions (PER-128) ([6659beb](https://github.com/Shadowsong27/agentic-beacon/commit/6659beb7bc0a54bb033667117d0f3a3a53a02925))
* unskip TC7 reject-rollback (PER-124) + fix latent rollback gap ([#122](https://github.com/Shadowsong27/agentic-beacon/issues/122)) ([1187968](https://github.com/Shadowsong27/agentic-beacon/commit/1187968fc9bec8e6edd3aee344876aba8cfd9147))

## [3.0.0](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v2.7.1...agentic-beacon@v3.0.0) (2026-05-09)


### ⚠ BREAKING CHANGES

* auto-pull artifact dependencies via frontmatter ([#102](https://github.com/Shadowsong27/agentic-beacon/issues/102))
*

### Features

* archive previous specs ([f756264](https://github.com/Shadowsong27/agentic-beacon/commit/f75626466bf6c2ee630968033b5014091545ab57))
* auto-pull artifact dependencies via frontmatter ([#102](https://github.com/Shadowsong27/agentic-beacon/issues/102)) ([e38c162](https://github.com/Shadowsong27/agentic-beacon/commit/e38c1620aabf0517a2b189781b46b3f698dab8c5))
* **beacon:** project-scoped agents — beacon.yaml.artifacts.agents + abc adopt integration ([#104](https://github.com/Shadowsong27/agentic-beacon/issues/104)) ([4e442ab](https://github.com/Shadowsong27/agentic-beacon/commit/4e442ab574656db394c750cf81bc1c384f8fb2a4))
* **beacon:** structured regular-file-conflict UX for agent wiring (PER-127) ([#114](https://github.com/Shadowsong27/agentic-beacon/issues/114)) ([d82a8a3](https://github.com/Shadowsong27/agentic-beacon/commit/d82a8a32e0678a7465452c372d00f0b7f0b599c0))
* **beacon:** unify agent distribution (PER-113) ([#109](https://github.com/Shadowsong27/agentic-beacon/issues/109)) ([9720215](https://github.com/Shadowsong27/agentic-beacon/commit/97202158b0cfbbad384de031d9c545ece93a8c4e))
* move agent requires from frontmatter to warehouse manifest ([#103](https://github.com/Shadowsong27/agentic-beacon/issues/103)) ([1b7e014](https://github.com/Shadowsong27/agentic-beacon/commit/1b7e014901050134a08ee82a8136f9ba10d44ff3))
* pending-artifacts flow + record-* skill revamp ([98c3746](https://github.com/Shadowsong27/agentic-beacon/commit/98c3746886910e0e5184922feeb122df76c82a7c))
* symlink-based artifact sync, single-warehouse-write-entrypoint ([#101](https://github.com/Shadowsong27/agentic-beacon/issues/101)) ([e324cf7](https://github.com/Shadowsong27/agentic-beacon/commit/e324cf782762a6c857c69a8a7e5cf589682fc7b4))


### Bug Fixes

* **beacon:** add transactional rollback to abc sync agent wiring (PER-131) ([#112](https://github.com/Shadowsong27/agentic-beacon/issues/112)) ([6d6c9a0](https://github.com/Shadowsong27/agentic-beacon/commit/6d6c9a0d782f4fa4fab27d3f0109e34d75e205b9))
* **beacon:** agents sync fallback on fresh machine (PER-112) ([#107](https://github.com/Shadowsong27/agentic-beacon/issues/107)) ([4acb916](https://github.com/Shadowsong27/agentic-beacon/commit/4acb91643cbebee3cbd338c58d4686b2185bee10))
* **beacon:** unwire only Beacon-owned tool symlinks; preserve user symlinks (PER-132) ([#117](https://github.com/Shadowsong27/agentic-beacon/issues/117)) ([037360d](https://github.com/Shadowsong27/agentic-beacon/commit/037360d2c521227dcbc03605ecc14f929410bc31))
* **beacon:** wire_agent_* compares resolved canonical paths, not raw readlink (PER-134) ([#119](https://github.com/Shadowsong27/agentic-beacon/issues/119)) ([1751e7e](https://github.com/Shadowsong27/agentic-beacon/commit/1751e7e798fc9079728c1871e26f8898fc500f3e))
* **beacon:** write per-tool .gitignore skills/ entry on dir existence (PER-136) ([#110](https://github.com/Shadowsong27/agentic-beacon/issues/110)) ([0f6cc34](https://github.com/Shadowsong27/agentic-beacon/commit/0f6cc3483f6e3757d9d927a33a7127fd14f5d9b5))
* **skill:** ignore OS litter during skill operations ([4440103](https://github.com/Shadowsong27/agentic-beacon/commit/444010341098acfd69c38000674f8b781d01eea6))
* **skill:** migrate legacy copy-based skills instead of silently skipping ([b78d22d](https://github.com/Shadowsong27/agentic-beacon/commit/b78d22d33788033bb660b031e508f616e3a0ecc2))
* **skill:** symlink live skill files to warehouse instead of copying ([8dae5c1](https://github.com/Shadowsong27/agentic-beacon/commit/8dae5c1c4564f7ef5e0109343867567af1f77a8d))


### Code Refactoring

* **beacon:** drop dead AgentFrontmatter / AgentRequires code (PER-117) ([#111](https://github.com/Shadowsong27/agentic-beacon/issues/111)) ([9c713ad](https://github.com/Shadowsong27/agentic-beacon/commit/9c713ad5234240f7b0a87dd011c68d412d4cdad4))
* **beacon:** drop examples/sample-warehouse, rely on abc warehouse init (PER-116) ([#115](https://github.com/Shadowsong27/agentic-beacon/issues/115)) ([c6d0120](https://github.com/Shadowsong27/agentic-beacon/commit/c6d01204a6af9eb1b28d0dda9a4079b3e1ac748f))
* **beacon:** drop tombstone commands and dead artifact helpers ([#108](https://github.com/Shadowsong27/agentic-beacon/issues/108)) ([2a96562](https://github.com/Shadowsong27/agentic-beacon/commit/2a965627f7707f25dcb5066273332115b25abf40))
* **beacon:** drop unused validate_requires_against_warehouse helper (PER-139) ([#116](https://github.com/Shadowsong27/agentic-beacon/issues/116)) ([c1842ae](https://github.com/Shadowsong27/agentic-beacon/commit/c1842aefba0b298617496629863dce2ad55315e1))
* **beacon:** use GitignoreManager for agent-dir entries + prune when empty (PER-130) ([#113](https://github.com/Shadowsong27/agentic-beacon/issues/113)) ([404e7e6](https://github.com/Shadowsong27/agentic-beacon/commit/404e7e67c1f9e1bac4009c61e8a722d0dbb46a76))
* **sync:** rename 'Skipped' to 'Up to date' in sync output ([520e8fb](https://github.com/Shadowsong27/agentic-beacon/commit/520e8fbf11b4eddd0783cf048b236006d811b27d))


### Miscellaneous Chores

* gitignore pending.yaml in warehouse init seed and repo root ([7b4a501](https://github.com/Shadowsong27/agentic-beacon/commit/7b4a5011bcc4c93bcb5135a7af8ab64a3aea173e))


### Performance

* **beacon:** one-shot marker for legacy global-agent cleanup (PER-133) ([#118](https://github.com/Shadowsong27/agentic-beacon/issues/118)) ([9384f97](https://github.com/Shadowsong27/agentic-beacon/commit/9384f972e06009191448f32d8e7d9472200850e5))

## [2.7.1](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v2.7.0...agentic-beacon@v2.7.1) (2026-04-28)


### Bug Fixes

* **skill:** remove abc- prefix from bundled skill command stubs ([8f89827](https://github.com/Shadowsong27/agentic-beacon/commit/8f8982718e2af4c2ba04ef9b90e213434d2380a0))

## [2.7.0](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v2.6.4...agentic-beacon@v2.7.0) (2026-04-24)


### Features

* bundled skills with abc- prefixed command stubs and record-skill ([#98](https://github.com/Shadowsong27/agentic-beacon/issues/98)) ([88f4a5b](https://github.com/Shadowsong27/agentic-beacon/commit/88f4a5be3c7768f26cb2274ee4d3c669fa729ea9))


### Bug Fixes

* **delta:** show pending status for skill files not yet distributed ([21b9f02](https://github.com/Shadowsong27/agentic-beacon/commit/21b9f0240b46c956498a3e713e8f60832327046e))

## [2.6.4](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v2.6.3...agentic-beacon@v2.6.4) (2026-04-24)


### Bug Fixes

* **delta:** show added skill files as added, not missing ([447a8d2](https://github.com/Shadowsong27/agentic-beacon/commit/447a8d2698b0020152f71cc9451741fa36e0addf)), closes [#96](https://github.com/Shadowsong27/agentic-beacon/issues/96)
* force release for agentic-beacon ([69a2b82](https://github.com/Shadowsong27/agentic-beacon/commit/69a2b82134c2829b8f7abeedf210344b909f8378))

## [2.6.3](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v2.6.2...agentic-beacon@v2.6.3) (2026-04-23)


### Bug Fixes

* **delta:** group untracked skills as single entries ([46a7c61](https://github.com/Shadowsong27/agentic-beacon/commit/46a7c61ac477d7f12e47bc2b769b6516ba3f512a)), closes [#95](https://github.com/Shadowsong27/agentic-beacon/issues/95)
* force release for agentic-beacon ([45d6ca1](https://github.com/Shadowsong27/agentic-beacon/commit/45d6ca13cd190e86778878bfa04c515e556fbf9e))

## [2.6.2](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v2.6.1...agentic-beacon@v2.6.2) (2026-04-23)


### Bug Fixes

* **delta:** group skill files as single entries in output ([7bd48c4](https://github.com/Shadowsong27/agentic-beacon/commit/7bd48c4f10d77f34ca66704bbe102a7341b635ce)), closes [#94](https://github.com/Shadowsong27/agentic-beacon/issues/94)
* force release for agentic-beacon ([53fd832](https://github.com/Shadowsong27/agentic-beacon/commit/53fd832774f7b0349204319e5a9e444cd04b4faf))

## [2.6.1](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v2.6.0...agentic-beacon@v2.6.1) (2026-04-22)


### Bug Fixes

* **adopt:** unadopting a skill also removes live agent copies ([32864f8](https://github.com/Shadowsong27/agentic-beacon/commit/32864f879b1c3790d70aeb83c832caca668631b2))

## [2.6.0](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v2.5.0...agentic-beacon@v2.6.0) (2026-04-20)


### Features

* **adopt+doctor:** knowledge node TUI, abc doctor command, and README with screenshot ([18ba254](https://github.com/Shadowsong27/agentic-beacon/commit/18ba254bbfc6502643287bb116f0099d5ab3795c))
* **adopt:** implement abc adopt command with TUI and sync notification ([db8c22f](https://github.com/Shadowsong27/agentic-beacon/commit/db8c22f6c42bb1f9f307b7974518d5c82a4cca8e))
* **adopt:** redesign TUI with collapsible tree, description panel, and per-type icons ([fd127a1](https://github.com/Shadowsong27/agentic-beacon/commit/fd127a1ab2e4b5510fd53fa20573a1bdcfa0d323))
* **delta+adopt:** stale status detection and abc adopt command ([#90](https://github.com/Shadowsong27/agentic-beacon/issues/90)) ([bfa73d4](https://github.com/Shadowsong27/agentic-beacon/commit/bfa73d4105b3a92df0b6e52cd0fb4eec54c52c51))


### Bug Fixes

* **tests:** update imports to use beacon.utils.* modules ([414c9b1](https://github.com/Shadowsong27/agentic-beacon/commit/414c9b17d7d6234fb3204de71e2320a707caf633))
* update agent sync-state HEAD even when content is unchanged ([2874ef9](https://github.com/Shadowsong27/agentic-beacon/commit/2874ef9072231baa59fa912acbcb04b3976988cc))
* update agent sync-state HEAD even when content is unchanged ([#89](https://github.com/Shadowsong27/agentic-beacon/issues/89)) ([3d8cce7](https://github.com/Shadowsong27/agentic-beacon/commit/3d8cce7ca6ce0c766e949d048f3a9352ee0a7651))


### Code Refactoring

* extract cli.py utils into beacon/utils/ package ([fba4c63](https://github.com/Shadowsong27/agentic-beacon/commit/fba4c6376f55a370b2df8895e6d9760e7353a7d0))
* extract manifest models into core/manifest/ package ([7ce5a9b](https://github.com/Shadowsong27/agentic-beacon/commit/7ce5a9bbb1212feb8d8b7fca30833b6d3b54f160))
* introduce domain layer (artifact + warehouse) ([#91](https://github.com/Shadowsong27/agentic-beacon/issues/91)) ([856b117](https://github.com/Shadowsong27/agentic-beacon/commit/856b117dc104ec410cf6805d80f688ddb44d184c))
* split cli into core/cli package, enforce absolute imports and clean __init__.py ([4c1f3c7](https://github.com/Shadowsong27/agentic-beacon/commit/4c1f3c72d94ebdd015136057c8151853f1a4b605))


### Miscellaneous Chores

* merge from remote main ([b833a97](https://github.com/Shadowsong27/agentic-beacon/commit/b833a9712c264cbbb5cdc339d379f5dcbf9d4c66))

## [2.5.0](https://github.com/Shadowsong27/agentic-beacon/compare/agentic-beacon@v2.4.0...agentic-beacon@v2.5.0) (2026-04-11)


### Features

* add abc agents sync command and include agents in abc sync ([#85](https://github.com/Shadowsong27/agentic-beacon/issues/85)) ([b1d551d](https://github.com/Shadowsong27/agentic-beacon/commit/b1d551d4acef0758c73587baf2857830fc281495))
* delta/contribute improvements — directory-level skills, project agents reminder, ignore patterns ([#84](https://github.com/Shadowsong27/agentic-beacon/issues/84)) ([7a5d140](https://github.com/Shadowsong27/agentic-beacon/commit/7a5d140f3787801222e2e977baf88ce96c51de9a))
* enforce directory-level skill entries as a hard boundary ([db958c5](https://github.com/Shadowsong27/agentic-beacon/commit/db958c57e079880969d1dd00e7f6a614f4cdd14a))
* show project-scoped agents in abc delta as promotion reminder ([3a4e615](https://github.com/Shadowsong27/agentic-beacon/commit/3a4e61523158bfb0ceb0b7f8f0f8bc94f150ea6f))


### Tests

* comprehensive coverage for skill entry directory boundary ([7f5ca0d](https://github.com/Shadowsong27/agentic-beacon/commit/7f5ca0d55263b1637fb9ba2cc16a99ea4511c410))

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
