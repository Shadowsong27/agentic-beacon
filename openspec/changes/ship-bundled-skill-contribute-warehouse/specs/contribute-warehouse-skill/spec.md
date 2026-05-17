## ADDED Requirements

### Requirement: Bundled `contribute-warehouse` skill ships with every install
The system SHALL distribute a bundled skill named `contribute-warehouse` alongside the existing `record-knowledge` and `record-skill` bundled skills. The skill SHALL be installed into every connected project's per-agent skill directory by `abc warehouse init`, `abc setup`, `abc sync`, and `abc adopt` — using the same wiring path that installs the other two bundled skills.

#### Scenario: Fresh `abc warehouse init` installs the skill
- **WHEN** a user runs `abc warehouse init <warehouse-path>` in a fresh directory and connects a project
- **THEN** the project's per-agent skill directories (e.g. `.opencode/skills/`, `.claude/skills/`) contain a `contribute-warehouse/SKILL.md` file alongside `record-knowledge/SKILL.md` and `record-skill/SKILL.md`
- **AND** an OpenCode command stub at `.opencode/command/contribute-warehouse.md` exists, generated from the skill's frontmatter

#### Scenario: Skill is included in the bundled-skill manifest
- **WHEN** the agentic-beacon Python package is built and inspected
- **THEN** the `_BUNDLED_SKILL_FILES` tuple in `domains/setup/initializer.py` references `skills/contribute-warehouse/SKILL.md`
- **AND** a distribution test asserts this membership and fails the build if the entry is removed

### Requirement: Skill SKILL.md declares its invocation and dependencies
The system SHALL ship a `SKILL.md` for `contribute-warehouse` whose YAML frontmatter declares `name: contribute-warehouse`, a non-empty `description`, and `compatibility: opencode` (matching the format used by `record-knowledge` and `record-skill`). The skill body SHALL document its slash-command invocation, the four helper scripts it ships, and the conversational flow.

#### Scenario: Frontmatter parses cleanly
- **WHEN** `parse_frontmatter` (the same function `abc warehouse lint` uses) is invoked on the bundled `SKILL.md`
- **THEN** parsing succeeds and the resulting `SkillFrontmatter` has `name == "contribute-warehouse"` and a non-empty description

#### Scenario: Skill exposes the documented invocation
- **WHEN** the skill body is rendered in an LLM context
- **THEN** the body documents `/contribute-warehouse` as the invocation form, names each of the four helper scripts (`resolve_warehouse.py`, `summarize_changes.py`, `draft_commit_message.py`, `push_warehouse.py`), and describes the steps in order

### Requirement: Skill ships four helper scripts under `scripts/`
The system SHALL ship four PEP 723 helper scripts inside `libs/beacon/src/beacon/data/skills/contribute-warehouse/scripts/`:
- `resolve_warehouse.py` — resolves the connected warehouse path from `.agentic-beacon/config.toml`; identical contract to the existing copies in `record-knowledge` and `record-skill`.
- `summarize_changes.py` — emits a single JSON document on stdout describing the warehouse working tree restricted to beacon.yaml-tracked paths.
- `draft_commit_message.py` — given a list of relative paths and an LLM-supplied subject, prints a Conventional Commits-formatted message with a deterministic scope derived from the path prefixes.
- `push_warehouse.py` — wraps `git -C <warehouse> push`. On success exits 0. On failure exits non-zero, prints the exact recovery command to stdout, and leaves the local commits untouched.

Each script SHALL be runnable via `uv run scripts/<name>.py …` and SHALL declare its dependencies via PEP 723 inline metadata (no separate `pyproject.toml` per skill).

#### Scenario: `summarize_changes.py` JSON shape
- **WHEN** `uv run scripts/summarize_changes.py --warehouse <path>` is invoked against a warehouse with N tracked dirty files
- **THEN** stdout contains a JSON object with a top-level `tracked_paths` array; each entry has `path` (warehouse-relative), `git_status` (porcelain code, e.g. `M`, `A`, `??`), `diff_stat` (one-line summary, e.g. `+12 -3`), and `last_commit_age_days` (integer; `null` for files never committed)
- **AND** files outside `beacon.yaml` tracked patterns do not appear in the output

#### Scenario: `draft_commit_message.py` derives scope from paths
- **WHEN** the script is invoked with `--paths contexts/python-standards.md knowledge/python-standards/lessons/foo.md --subject "add loguru guidance"`
- **THEN** stdout contains a Conventional Commits message whose scope reflects the common path prefix (e.g. `docs(python-standards): add loguru guidance` or `feat(contexts): add loguru guidance` per the deterministic mapping rule)
- **AND** the same inputs always produce the same scope (deterministic, no randomness, no LLM call inside the script)

#### Scenario: `push_warehouse.py` emits a recovery command on failure
- **WHEN** `uv run scripts/push_warehouse.py --warehouse <path>` is invoked but `git push` fails (e.g. no network, no remote configured, auth failure)
- **THEN** the script exits non-zero
- **AND** stdout contains an exact, copy-pasteable command of the form `git -C <warehouse> push origin <branch>` for the user to retry later
- **AND** any commits that were created earlier in the contribute flow remain in the local branch (the script never resets, amends, or force-pushes)

### Requirement: Skill enforces an `abc warehouse lint` pre-flight gate
The skill SHALL invoke `abc warehouse lint <warehouse-root>` exactly once at the start of the contribute flow, before any commit or stage operation. If lint exits non-zero, the skill SHALL abort, surface the lint errors to the user, and SHALL NOT call `abc warehouse contribute`. The skill SHALL NOT run lint per commit in a multi-commit split.

#### Scenario: Lint clean — flow proceeds
- **WHEN** the user invokes `/contribute-warehouse` and `abc warehouse lint` exits 0
- **THEN** the skill proceeds to intent triage (Step 4) without further lint invocations

#### Scenario: Lint fails — flow aborts before any commit
- **WHEN** the user invokes `/contribute-warehouse` and `abc warehouse lint` exits non-zero
- **THEN** the skill prints the lint error output (or a summary linking to the full report) and stops
- **AND** the warehouse working tree is left exactly as the user set it (no `git add`, no `git stash`, no `git commit`, no `git push`)
- **AND** the skill instructs the user to resolve the lint findings (commit-fix, revert, or remove the offending files) and re-run

#### Scenario: Multi-commit split runs lint only once
- **WHEN** the cohesion check (Step 6) splits the contribution into N ≥ 2 commits
- **THEN** `abc warehouse lint` is invoked exactly once for the whole flow, before commit 1
- **AND** subsequent commits do not re-invoke lint

### Requirement: Skill performs intent-first triage of dirty files
The skill SHALL ask the user (or infer from the invocation argument) the *intent* of the contribution, then map that intent onto the set of dirty tracked files reported by `summarize_changes.py`. Each dirty file SHALL be classified as either *include* or *leave-for-later*. Files classified as leave-for-later SHALL NOT be staged, stashed, or modified — they remain in the working tree as-is, and the skill SHALL clearly tell the user which files were left.

#### Scenario: Mixed intent vs incidental changes
- **WHEN** the warehouse has 3 dirty tracked files and the user states "I want to ship the python-standards updates"
- **THEN** the skill proposes which files match the stated intent (include) and which look incidental (leave-for-later)
- **AND** the user confirms or edits the per-file classification before any commit

#### Scenario: Leave-for-later files are not modified
- **WHEN** the user classifies file X as leave-for-later
- **THEN** the skill does not stage X, does not stash X, does not modify X
- **AND** after the contribute flow completes, X remains dirty in the working tree exactly as it was
- **AND** the final summary names X as a deferred file the user can address in a later contribution

### Requirement: Skill performs semantic dedup scan for knowledge files only
For any included file under `knowledge/**`, the skill SHALL read its peer files in the same `knowledge/<topic>/<kind>/` subdirectory and surface any that semantically overlap with the included content. The skill SHALL NOT perform this scan for files under `contexts/`, `skills/`, `agents/`, or other warehouse subtrees. The user decides per overlap whether to merge, supersede, or proceed.

#### Scenario: New knowledge lesson with semantic overlap
- **WHEN** an included file is `knowledge/python-standards/lessons/use-loguru.md` and a peer file `knowledge/python-standards/lessons/python-logging-use-loguru.md` already exists with overlapping content
- **THEN** the skill surfaces the peer to the user with both titles and brief excerpts
- **AND** offers options: merge into peer, mark new file as superseding peer, or proceed with both

#### Scenario: Context file is not scanned for semantic dedup
- **WHEN** an included file is `contexts/python-standards.md`
- **THEN** the skill does not perform a semantic dedup scan against other context files
- **AND** the flow proceeds directly to the cohesion check

### Requirement: Skill performs cohesion check and may split into multiple commits
After triage and dedup, the skill SHALL evaluate whether the included files form one logical change or multiple. If multiple, the skill SHALL propose a split into N cohesive groups, and SHALL produce one `abc warehouse contribute -m "<msg>"` call per group. The user SHALL confirm the split before any commit lands.

#### Scenario: Single cohesive change
- **WHEN** all included files share one logical purpose (e.g. add a brief and the lesson it links to)
- **THEN** the skill proposes one commit and one commit message
- **AND** runs `abc warehouse contribute -m "<msg>"` exactly once

#### Scenario: Multiple logical changes
- **WHEN** included files cover two unrelated concerns (e.g. a python-standards update and a cicd-flow fix)
- **THEN** the skill proposes a split into 2 groups with one commit message per group
- **AND** runs `abc warehouse contribute -m "<msg>"` once per group, in order

### Requirement: Skill commits without `--push` and pushes once atomically
The skill SHALL invoke `abc warehouse contribute -m "<msg>"` *without* the `--push` flag for every commit. After all N commits in the contribution have landed locally, the skill SHALL run `push_warehouse.py` exactly once to push them in a single network round-trip.

#### Scenario: Single-commit contribution pushes once at the end
- **WHEN** the contribution resolves to one commit
- **THEN** the skill runs `abc warehouse contribute -m "<msg>"` (no `--push`), then `push_warehouse.py`
- **AND** never invokes `abc warehouse contribute --push`

#### Scenario: Multi-commit contribution pushes once after all commits land
- **WHEN** the contribution resolves to 3 commits
- **THEN** the skill runs `abc warehouse contribute -m "<msg>"` 3 times in sequence (no `--push` on any), then `push_warehouse.py` exactly once
- **AND** if any of the 3 commits fails, the skill stops and does not attempt the push

#### Scenario: Push fails — commits remain local
- **WHEN** all N commits succeed but the final push fails (e.g. airgapped, no network, auth)
- **THEN** the skill surfaces the push failure with the exact recovery command from `push_warehouse.py`
- **AND** the N commits remain in the local warehouse branch ready to push later
- **AND** the skill exits cleanly (non-zero) without amending, resetting, or force-pushing

### Requirement: CLI dependency — `abc warehouse contribute` supports per-path scoping
The `abc warehouse contribute` CLI SHALL accept a repeatable `--paths` option that restricts the staged-and-committed set to the specified warehouse-relative paths. Every path supplied via `--paths` MUST be a member of the beacon.yaml-tracked set; paths outside that set SHALL cause the command to exit non-zero with a clear error message naming the offending path(s). Omitting `--paths` preserves the existing behaviour (commit all dirty tracked paths).

The skill relies on this flag to deliver its leave-for-later and multi-commit split promises: without per-path scoping, a multi-group contribution would incorrectly commit all dirty files in every `abc warehouse contribute` call.

#### Scenario: `--paths` restricts commit to specified tracked paths
- **WHEN** `abc warehouse contribute -m "msg" --paths contexts/a.md` is called while `contexts/a.md` and `contexts/b.md` are both dirty and tracked
- **THEN** only `contexts/a.md` appears in the resulting commit
- **AND** `contexts/b.md` remains dirty in the warehouse working tree

#### Scenario: `--paths` rejects paths outside beacon.yaml-tracked set
- **WHEN** `abc warehouse contribute -m "msg" --paths untracked/file.md` is called and `untracked/file.md` is not in the beacon.yaml-tracked set
- **THEN** the command exits non-zero
- **AND** the error message names `untracked/file.md` as the offending path

### Requirement: Skill is documented in user-facing docs
The system SHALL document the `contribute-warehouse` skill in `libs/beacon/README.md` and in `site-docs/`, alongside the existing `record-knowledge` and `record-skill` entries. Documentation SHALL describe the slash-command invocation, the lint-gate behaviour, the airgap-safe push contract, and a brief mention of the helper scripts.

#### Scenario: README lists the skill
- **WHEN** a reader opens `libs/beacon/README.md`
- **THEN** the bundled-skills section lists `contribute-warehouse` alongside `record-knowledge` and `record-skill`

#### Scenario: site-docs describes the flow
- **WHEN** a reader navigates to the bundled-skills section of `site-docs/`
- **THEN** there is a page or section for `/contribute-warehouse` covering invocation, the lint pre-flight gate, intent triage, the airgap-safe push behaviour, and a summary of the four helper scripts
