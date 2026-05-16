<!-- opsx:tdd-header:begin -->
## TDD WORKFLOW - MANDATORY FOR ALL TASKS

**CRITICAL**: This project follows strict Test-Driven Development (TDD). Before implementing ANY task:

### RED-GREEN-REFACTOR Cycle

1. **RED Phase - Write Failing Tests FIRST**
   - Read the task's TDD Test Cases (TC1-TCN)
   - Create test file in `tests/` directory
   - Write ALL test cases from the task BEFORE any implementation
   - Run tests - they MUST fail (import errors, missing functions, etc.)
   - If tests pass without implementation, you wrote the tests wrong!

2. **GREEN Phase - Implement Minimal Code**
   - Write ONLY enough code to make tests pass
   - Run tests after each implementation
   - All tests must pass before marking task complete

3. **REFACTOR Phase - Improve Code Quality**
   - Clean up implementation
   - Remove duplication
   - Improve naming
   - Tests must still pass after refactoring

### Task Completion Criteria

**A task is NOT complete until:**
- All TDD test cases are written
- All tests pass (or are justifiably skipped with documentation)
- Implementation matches the Expected Output
- Test results documented in tasks.md

**For skipped tests:**
- Add `@pytest.mark.skip(reason="...")` with clear justification
- Document in tasks.md under "Skipped Test Cases" section
- Explain why feature is deferred and when it will be implemented

### Test Organization

```
tests/
├── core/           # Core module tests
├── <module>/       # Module-specific tests
└── conftest.py     # Shared fixtures
```

### Running Tests

```bash
# Activate venv, install dev deps, run tests
source .venv/bin/activate
uv sync --extra dev
pytest tests/ -v --tb=short
```

**See Also:**
- Check project AGENTS.md for unit testing workflow
- Check knowledge base for TDD lessons and standards
<!-- opsx:tdd-header:end -->

<!-- opsx:repos-table:begin -->
## Repositories & Branches

| Repo | Path | Branch | Role |
|------|------|--------|------|
| `agentic-beacon` | `~/Code/oss/agentic-beacon` | `ship-bundled-skill-contribute-warehouse` | Code changes — adds the `contribute-warehouse` bundled skill, four PEP 723 helper scripts, manifest wiring in `domains/setup/initializer.py`, docstring updates, README and site-docs additions, and unit/distribution tests. |
| `hl-knowledge-market` | `~/Code/knowledge/hl-knowledge-market` | `main` | Operational only — used at end-to-end validation time as the test warehouse the skill commits into. No code changes in this repo as part of this OpenSpec change. Lint failures here would block contribute flow regardless of source. |
| `warehouse-lint-cli-for-ci (PER-114)` | `(not a repo — sibling OpenSpec change in agentic-beacon)` | `n/a` | Not involved — listed because PER-175 implementation is GATED on PER-114 shipping `abc warehouse lint` first. Verify in Task 1.1 before any other work begins. |
<!-- opsx:repos-table:end -->

## 1. Pre-flight checks

<!-- opsx:phase-summary:1:begin -->
**Goal**: Confirm the blocking dependency (PER-114 / `abc warehouse lint`) has shipped and create the feature branch before any implementation begins. This is the gate that prevents wasted work if the lint CLI is not yet available.
**Input**: Clean working tree on `agentic-beacon` `main` branch; the latest published version of `agentic-beacon` is installed locally for testing.
**Output**: Confirmation that `abc warehouse lint` exists and is invocable in the targeted release; a feature branch `ship-bundled-skill-contribute-warehouse` checked out and ready for commits.
**Validation**: `abc warehouse lint --help` exits 0 and shows the lint subcommand. `git rev-parse --abbrev-ref HEAD` returns `ship-bundled-skill-contribute-warehouse`.
<!-- opsx:phase-summary:1:end -->


- [ ] 1.1 **[MANUAL]** Confirm `warehouse-lint-cli-for-ci` (PER-114) has shipped — `abc warehouse lint <path>` exists in `main` and is published in the version of `agentic-beacon` we're targeting. If not, do not start implementation.
<!-- opsx:tdd:1.1:begin -->
  - **Input**: abc --version && abc warehouse lint --help
  - **Expected Output**: Both commands exit 0; `abc warehouse lint --help` shows usage including a `[PATH]` positional argument.
  - **Validation**: Lint subcommand is registered in the installed agentic-beacon version. If exit non-zero or 'no such command' error, STOP — do not proceed with implementation.
<!-- opsx:tdd:1.1:end -->
- [ ] 1.2 Create a feature branch in the agentic-beacon repo: `git checkout -b ship-bundled-skill-contribute-warehouse`.

## 2. Skill scaffolding

<!-- opsx:phase-summary:2:begin -->
**Goal**: Create the directory structure and `SKILL.md` for the new `contribute-warehouse` bundled skill, mirroring the established `record-skill` pattern.
**Input**: Existing bundled-skill layout under `libs/beacon/src/beacon/data/skills/record-skill/` as the reference template; the spec at `specs/contribute-warehouse-skill/spec.md` defining the required frontmatter and body sections.
**Output**: A new `libs/beacon/src/beacon/data/skills/contribute-warehouse/` directory containing a valid `SKILL.md` (frontmatter + body) and an empty `scripts/` subdirectory ready for helper scripts.
**Validation**: `parse_frontmatter` (the same function used by `abc warehouse lint`) successfully parses the new `SKILL.md` and returns `name == "contribute-warehouse"` with a non-empty description.
<!-- opsx:phase-summary:2:end -->


- [ ] 2.1 Create directory `libs/beacon/src/beacon/data/skills/contribute-warehouse/`.
- [ ] 2.2 Create directory `libs/beacon/src/beacon/data/skills/contribute-warehouse/scripts/`.
- [ ] 2.3 Write `libs/beacon/src/beacon/data/skills/contribute-warehouse/SKILL.md` with frontmatter (`name`, `description`, `license`, `compatibility: opencode`, `requires.contexts: []`) and a body that documents the slash-command invocation, the four helper scripts, and the conversational flow (lint gate → triage → dedup → cohesion → commit per group → atomic push). Mirror the structure of `record-skill/SKILL.md`.
<!-- opsx:tdd:2.3:begin -->
  - **Input**: Read `libs/beacon/src/beacon/data/skills/record-skill/SKILL.md` for structure; author SKILL.md with frontmatter and body sections (Purpose, When to Use, Invocation, Process steps 1-9 mirroring design.md flow, Examples, Checklist).
  - **Expected Output**: A SKILL.md file 200-300 lines long with valid YAML frontmatter and prose body documenting the full flow.
  - **Validation**: File exists, has `---` opening, frontmatter has `name: contribute-warehouse`, non-empty `description`, `compatibility: opencode`, and `requires: { contexts: [] }`. Body references all four helper scripts by name.
  - **TDD Test Cases (write these first):**
    - TC1: Frontmatter parses cleanly via `parse_frontmatter` → returns valid SkillFrontmatter
    - TC2: `name` field equals `contribute-warehouse` exactly
    - TC3: `description` field is non-empty and ≤200 chars
    - TC4: `compatibility` field equals `opencode`
    - TC5: `requires.contexts` is an empty list
    - TC6: Body contains the literal strings `resolve_warehouse.py`, `summarize_changes.py`, `draft_commit_message.py`, `push_warehouse.py`
    - TC7: Body documents `/contribute-warehouse` as the slash invocation
    - TC8: Body length is between 100 and 400 lines (lean per design risk-mitigation)
<!-- opsx:tdd:2.3:end -->
- [ ] 2.4 Verify the SKILL.md frontmatter parses cleanly via `parse_frontmatter` (the same function used by lint).
<!-- opsx:tdd:2.4:begin -->
  - **Input**: uv run python -c "from beacon.core.frontmatter import parse_frontmatter; from pathlib import Path; print(parse_frontmatter(Path('libs/beacon/src/beacon/data/skills/contribute-warehouse/SKILL.md').read_text()))"
  - **Expected Output**: Prints a SkillFrontmatter object (or dict) with `name='contribute-warehouse'` and a non-empty `description`. Exits 0.
  - **Validation**: No frontmatter parse error; resulting object's `name` and `description` fields are populated correctly.
<!-- opsx:tdd:2.4:end -->

## 3. Helper script: `resolve_warehouse.py`

<!-- opsx:phase-summary:3:begin -->
**Goal**: Provide warehouse-path resolution to the new skill by mirroring the boilerplate already used by `record-knowledge` and `record-skill`.
**Input**: Existing `resolve_warehouse.py` from the `record-skill` skill; a connected project with `.agentic-beacon/config.toml` for smoke-testing.
**Output**: A working `scripts/resolve_warehouse.py` inside the new skill directory that resolves the warehouse path identically to the existing copies.
**Validation**: `uv run libs/beacon/src/beacon/data/skills/contribute-warehouse/scripts/resolve_warehouse.py` from a connected project prints the warehouse absolute path and exits 0.
<!-- opsx:phase-summary:3:end -->


- [ ] 3.1 Copy `libs/beacon/src/beacon/data/skills/record-skill/scripts/resolve_warehouse.py` to `libs/beacon/src/beacon/data/skills/contribute-warehouse/scripts/resolve_warehouse.py`. (No new logic — established pattern.)
- [ ] 3.2 **[MANUAL]** Smoke-run: `uv run libs/beacon/src/beacon/data/skills/contribute-warehouse/scripts/resolve_warehouse.py` from a connected project resolves correctly.
<!-- opsx:tdd:3.2:begin -->
  - **Input**: cd <connected-project> && uv run <abs path>/scripts/resolve_warehouse.py
  - **Expected Output**: Prints the absolute warehouse path on stdout. Exit code 0.
  - **Validation**: Output matches `cat .agentic-beacon/config.toml | grep warehouse_path`. Exit 0 confirms the script's resolver logic still works after the copy.
<!-- opsx:tdd:3.2:end -->

## 4. Helper script: `summarize_changes.py`

<!-- opsx:phase-summary:4:begin -->
**Goal**: Produce a deterministic, structured JSON summary of the warehouse working-tree restricted to beacon.yaml-tracked dirty paths, so the LLM has a clean view of what's changed.
**Input**: A connected warehouse with mixed dirty/clean/untracked tracked files; `beacon.domains.warehouse._tracked_paths.get_tracked_paths` importable.
**Output**: A `scripts/summarize_changes.py` PEP 723 script that prints a single JSON object with a `tracked_paths` array (path, git_status, diff_stat, last_commit_age_days). Filters out clean files; respects beacon.yaml tracking patterns.
**Validation**: Running the script against a fixture warehouse produces JSON whose schema matches `{"tracked_paths": [{"path": str, "git_status": str, "diff_stat": str, "last_commit_age_days": int|null}, ...]}` and contains only dirty tracked paths.
<!-- opsx:phase-summary:4:end -->


- [ ] 4.1 Implement `summarize_changes.py` with PEP 723 metadata (`requires-python = ">=3.11"`, dependencies on the local `agentic-beacon` package so it can import `beacon.domains.warehouse._tracked_paths.get_tracked_paths`).
<!-- opsx:tdd:4.1:begin -->
  - **Input**: Author the script's PEP 723 header block: `# /// script\n# requires-python = ">=3.11"\n# dependencies = ["agentic-beacon"]\n# ///`
  - **Expected Output**: Header parses correctly; `uv run scripts/summarize_changes.py --help` exits 0 and the import of `get_tracked_paths` succeeds inside the script.
  - **Validation**: PEP 723 header is structurally valid; `uv run` resolves the agentic-beacon dependency without error.
<!-- opsx:tdd:4.1:end -->
- [ ] 4.2 Accept `--warehouse <path>` and `--beacon-yaml <path>` flags (default the latter to `<warehouse>/.agentic-beacon/beacon.yaml`).
<!-- opsx:tdd:4.2:begin -->
  - **Input**: uv run scripts/summarize_changes.py --warehouse /tmp/test-warehouse
  - **Expected Output**: Script accepts the flag and uses `/tmp/test-warehouse/.agentic-beacon/beacon.yaml` as the default beacon.yaml path. `--help` shows both flags.
  - **Validation**: argparse setup includes both flags; default for `--beacon-yaml` is computed from `--warehouse`; missing `--warehouse` produces a non-zero exit with a helpful message.
<!-- opsx:tdd:4.2:end -->
- [ ] 4.3 Call `get_tracked_paths()` to enumerate tracked paths.
<!-- opsx:tdd:4.3:begin -->
  - **Input**: From inside the script: `tracked = get_tracked_paths(Path(args.warehouse), Path(args.beacon_yaml))`
  - **Expected Output**: Returns a list of warehouse-relative path strings respecting the beacon.yaml `artifacts.skills` and `artifacts.contexts` patterns.
  - **Validation**: Returned paths exactly match what `abc warehouse contribute` would stage; no untracked/ignored files leak through.
<!-- opsx:tdd:4.3:end -->
- [ ] 4.4 For each tracked path, run `git -C <warehouse> status --porcelain -- <path>` and parse the porcelain code; run `git diff --stat -- <path>` and extract the one-line summary; run `git log -1 --format=%cI -- <path>` and compute days-since-last-commit (or `null` if never committed).
<!-- opsx:tdd:4.4:begin -->
  - **Input**: For each tracked_path, subprocess.run(["git", "-C", warehouse, "status", "--porcelain", "--", path]) plus the diff-stat and log-1 commands.
  - **Expected Output**: git_status is a 1-2 char porcelain code (e.g. ` M`, `A `, `??`, `MM`); diff_stat is a single-line summary like `1 file changed, 12 insertions(+), 3 deletions(-)`; last_commit_age_days is an integer (days between now and the ISO timestamp) or null.
  - **Validation**: Subprocess timeouts set; non-zero exit codes for git surfaced cleanly (not silently dropped); ISO date parsing handles timezone correctly.
  - **TDD Test Cases (write these first):**
    - TC1: Modified tracked file → git_status `M`, diff_stat non-empty, last_commit_age_days is a positive int
    - TC2: Newly added (staged) file → git_status `A`, last_commit_age_days is null
    - TC3: Untracked-but-beacon.yaml-tracked file → git_status `??`, last_commit_age_days is null
    - TC4: File modified in both index and working tree → git_status `MM`
    - TC5: File never committed in git history → last_commit_age_days is null (not a number)
    - TC6: File committed yesterday → last_commit_age_days == 1 (or 0 if same calendar day, document the rule)
    - TC7: Subprocess failure (e.g. not a git repo) → script exits non-zero with informative error
    - TC8: Path containing spaces or unicode → handled correctly by the `--` separator pattern
<!-- opsx:tdd:4.4:end -->
- [ ] 4.5 Emit a single JSON object on stdout with shape `{"tracked_paths": [{"path": ..., "git_status": ..., "diff_stat": ..., "last_commit_age_days": ...}, ...]}`.
<!-- opsx:tdd:4.5:begin -->
  - **Input**: uv run scripts/summarize_changes.py --warehouse <fixture> | python -c 'import json,sys; print(json.load(sys.stdin))'
  - **Expected Output**: JSON parses without error; top-level key is `tracked_paths`; each entry has the four required fields with expected types.
  - **Validation**: Output is exactly one JSON object (no surrounding text, no log lines on stdout). Use `json.dumps(..., indent=2)` for readability.
  - **TDD Test Cases (write these first):**
    - TC1: Empty warehouse (no dirty tracked files) → `{"tracked_paths": []}`
    - TC2: One modified file → `tracked_paths` has exactly one entry with all four fields populated
    - TC3: Multiple files → entries appear in deterministic order (sort by path)
    - TC4: Output is valid JSON (`json.loads` succeeds)
    - TC5: No log output, no debug prints, no stderr leakage to stdout
<!-- opsx:tdd:4.5:end -->
- [ ] 4.6 Filter out clean (un-modified) paths — only dirty tracked paths appear in the output.
<!-- opsx:tdd:4.6:begin -->
  - **Input**: Fixture warehouse with 5 tracked paths total: 2 modified, 3 clean.
  - **Expected Output**: `tracked_paths` array has exactly 2 entries (the modified ones).
  - **Validation**: Clean files (porcelain output empty for that path) are filtered out before adding to the output array.
<!-- opsx:tdd:4.6:end -->

## 5. Helper script: `draft_commit_message.py`

<!-- opsx:phase-summary:5:begin -->
**Goal**: Produce a deterministic Conventional Commits message from a list of changed paths plus an LLM-supplied subject, with no randomness or LLM dependency inside the script itself.
**Input**: A list of warehouse-relative paths and a free-text subject string supplied via CLI flags.
**Output**: A `scripts/draft_commit_message.py` PEP 723 script (stdlib only) that emits `<type>(<scope>): <subject>` to stdout based on a documented mapping table.
**Validation**: Repeated invocations with identical `--paths` and `--subject` produce byte-identical output. Mapping rules (skills/* → feat, contexts|knowledge → docs, mixed → chore; scope = longest common prefix or topic) are documented inline and unit-tested in Phase 9.
<!-- opsx:phase-summary:5:end -->


- [ ] 5.1 Implement `draft_commit_message.py` with PEP 723 metadata. No external dependencies needed (pure stdlib).
<!-- opsx:tdd:5.1:begin -->
  - **Input**: PEP 723 header: `# /// script\n# requires-python = ">=3.11"\n# dependencies = []\n# ///`
  - **Expected Output**: `uv run scripts/draft_commit_message.py --help` exits 0 with no dependency resolution required.
  - **Validation**: Empty `dependencies = []` list confirmed; script imports only from stdlib (no `import beacon`, no `import yaml`, etc.).
<!-- opsx:tdd:5.1:end -->
- [ ] 5.2 Accept `--paths <p1> <p2> ...` and `--subject <text>` flags.
<!-- opsx:tdd:5.2:begin -->
  - **Input**: uv run scripts/draft_commit_message.py --paths a/b.md c/d.md --subject "add foo"
  - **Expected Output**: Both flags parse; `paths` is a list of 2; `subject` is `add foo`. `--help` shows both.
  - **Validation**: argparse `nargs='+'` for paths; `required=True` for both flags; missing either flag produces clear error and exit non-zero.
<!-- opsx:tdd:5.2:end -->
- [ ] 5.3 Implement deterministic scope derivation: Find the longest common path prefix across `paths`. If the prefix is exactly one of `contexts/`, `skills/`, `agents/`, `knowledge/<topic>/`: use that as the scope (e.g. `python-standards` for `knowledge/python-standards/...`). Otherwise fall back to the top-level dir.
<!-- opsx:tdd:5.3:begin -->
  - **Input**: Function `derive_scope(paths: list[str]) -> str`. Test inputs across the documented prefix table.
  - **Expected Output**: Returns the topic name for `knowledge/<topic>/...`; returns the top-level dir name otherwise; never returns an empty string.
  - **Validation**: Function is pure (no side effects, no I/O), deterministic, unit-tested across all branches of the mapping table.
  - **TDD Test Cases (write these first):**
    - TC1: `["contexts/python-standards.md"]` → scope `contexts`
    - TC2: `["skills/foo/SKILL.md"]` → scope `skills`
    - TC3: `["agents/bar.md"]` → scope `agents`
    - TC4: `["knowledge/python-standards/lessons/x.md", "knowledge/python-standards/decisions/y.md"]` → scope `python-standards` (topic-aware)
    - TC5: `["knowledge/python-standards/lessons/x.md", "knowledge/cicd/lessons/y.md"]` → scope `knowledge` (mixed topics, fallback)
    - TC6: `["contexts/a.md", "knowledge/x/lessons/y.md"]` → scope is mixed/general (document the rule, e.g. fallback to common ancestor or 'general')
    - TC7: `["single-file.md"]` (root-level path) → scope is the filename stem or a fallback constant
    - TC8: Empty paths list → raises ValueError or similar
<!-- opsx:tdd:5.3:end -->
  - Find the longest common path prefix across `paths`.
  - If the prefix is exactly one of `contexts/`, `skills/`, `agents/`, `knowledge/<topic>/`: use that as the scope (e.g. `python-standards` for `knowledge/python-standards/...`).
  - Otherwise fall back to the top-level dir.
- [ ] 5.4 Implement deterministic type prefix: All paths under `skills/` and the change adds new files → `feat`. Paths under `contexts/` or `knowledge/` → `docs`. Mixed or unclassifiable → `chore`. (Document the full mapping table inline in the script as a comment.)
<!-- opsx:tdd:5.4:begin -->
  - **Input**: Function `derive_type(paths: list[str], git_statuses: list[str] | None = None) -> str`. (git_statuses optional — needed for the `feat` vs other distinction if relevant.)
  - **Expected Output**: Returns one of `feat`, `fix`, `docs`, `chore` per the documented table.
  - **Validation**: Function is pure; mapping table appears as a comment block at the top of the script for reference.
  - **TDD Test Cases (write these first):**
    - TC1: All paths under `skills/` with new files → `feat`
    - TC2: All paths under `contexts/` → `docs`
    - TC3: All paths under `knowledge/` → `docs`
    - TC4: Mixed `skills/` + `contexts/` → `chore`
    - TC5: Modifying existing `skills/` file (not new) → `fix` or `feat` per the documented rule
    - TC6: Path under `agents/` → document the rule (probably `feat` for new, `fix` for modification)
<!-- opsx:tdd:5.4:end -->
  - All paths under `skills/` and the change adds new files → `feat`.
  - Paths under `contexts/` or `knowledge/` → `docs`.
  - Mixed or unclassifiable → `chore`.
  - (Document the full mapping table inline in the script as a comment.)
- [ ] 5.5 Print the formatted Conventional Commits message to stdout: `<type>(<scope>): <subject>`.
<!-- opsx:tdd:5.5:begin -->
  - **Input**: uv run scripts/draft_commit_message.py --paths contexts/python-standards.md --subject "add loguru section"
  - **Expected Output**: Stdout: `docs(contexts): add loguru section\n` exactly. Exit 0.
  - **Validation**: Output matches Conventional Commits regex `^(feat|fix|docs|chore|refactor|test)(\([a-z0-9-]+\))?: .+$`. No trailing whitespace on the subject.
<!-- opsx:tdd:5.5:end -->
- [ ] 5.6 Verify same inputs produce same output (deterministic, no time/random sources).
<!-- opsx:tdd:5.6:begin -->
  - **Input**: Run the script 10 times in a loop with identical args.
  - **Expected Output**: All 10 invocations produce byte-identical stdout.
  - **Validation**: Diff across invocations is empty. No `datetime.now()`, no `random`, no env-var-dependent behaviour in the code.
<!-- opsx:tdd:5.6:end -->

## 6. Helper script: `push_warehouse.py`

<!-- opsx:phase-summary:6:begin -->
**Goal**: Provide an atomic, airgap-safe push wrapper that on success exits 0 and on failure prints a copy-paste recovery command without performing any destructive git op.
**Input**: A warehouse with one or more local commits ahead of `origin`; current branch detectable via `git rev-parse --abbrev-ref HEAD`.
**Output**: A `scripts/push_warehouse.py` PEP 723 script (stdlib only) that wraps `git push` with structured failure reporting. Never invokes `git reset`, `git push --force`, or `git commit --amend`.
**Validation**: On a warehouse with network available, script exits 0. On a simulated network failure (no remote / DNS blocked), script exits non-zero, stdout contains exactly `git -C <warehouse> push origin <branch>`, and `git log` shows the local commits remain intact.
<!-- opsx:phase-summary:6:end -->


- [ ] 6.1 Implement `push_warehouse.py` with PEP 723 metadata (stdlib only).
<!-- opsx:tdd:6.1:begin -->
  - **Input**: PEP 723 header with `dependencies = []`; script imports only stdlib.
  - **Expected Output**: `uv run scripts/push_warehouse.py --help` exits 0 with no dependency resolution.
  - **Validation**: No third-party imports; subprocess module used for git invocation.
<!-- opsx:tdd:6.1:end -->
- [ ] 6.2 Accept `--warehouse <path>` flag.
<!-- opsx:tdd:6.2:begin -->
  - **Input**: uv run scripts/push_warehouse.py --warehouse /tmp/test-warehouse
  - **Expected Output**: Flag parses; required=True; missing flag → exit non-zero with usage message.
  - **Validation**: argparse setup verified; `--help` shows the flag.
<!-- opsx:tdd:6.2:end -->
- [ ] 6.3 Run `git -C <warehouse> rev-parse --abbrev-ref HEAD` to capture the current branch name.
<!-- opsx:tdd:6.3:begin -->
  - **Input**: subprocess.run(["git", "-C", warehouse, "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True)
  - **Expected Output**: Returns the current branch name (e.g. `main`, `feature/foo`); detached HEAD returns `HEAD`.
  - **Validation**: Branch name captured to a local variable for use in the recovery command if push fails. Subprocess timeout set.
<!-- opsx:tdd:6.3:end -->
- [ ] 6.4 Run `git -C <warehouse> push`. If exit 0, exit 0.
<!-- opsx:tdd:6.4:begin -->
  - **Input**: subprocess.run(["git", "-C", warehouse, "push"], capture_output=True, text=True)
  - **Expected Output**: On success (push completed): script exits 0 with no output to stderr (or quiet success message to stdout).
  - **Validation**: Successful push case: warehouse `git log origin/<branch>` includes the new commits.
<!-- opsx:tdd:6.4:end -->
- [ ] 6.5 If push fails: capture stderr, print a structured error to stderr, print the exact recovery command `git -C <warehouse> push origin <branch>` to stdout, and exit non-zero.
<!-- opsx:tdd:6.5:begin -->
  - **Input**: Simulate failure: warehouse with no remote configured, or with offline DNS. Run the script.
  - **Expected Output**: Stdout contains exactly `git -C <warehouse> push origin <branch>` (substituting real values). Stderr contains a structured error block including the original git stderr. Script exit code is non-zero.
  - **Validation**: Recovery command on stdout is copy-pasteable and works once network is restored. Local commits remain intact (verified via `git log` after the failed push).
  - **TDD Test Cases (write these first):**
    - TC1: No `origin` remote configured → script fails, recovery command shown, local commits intact
    - TC2: Network disabled mid-push → script fails, structured error names the network failure
    - TC3: Auth failure (bad credentials) → script fails, recovery command preserved exactly
    - TC4: Push rejected (non-fast-forward) → script fails, error message mentions the rejection (no force-push attempt)
    - TC5: Successful push after recovery command is run manually → confirms the recovery command works
<!-- opsx:tdd:6.5:end -->
- [ ] 6.6 Never run `git reset`, `git push --force`, `git commit --amend`, or any other destructive op.
<!-- opsx:tdd:6.6:begin -->
  - **Input**: grep -E '(reset|--force|--amend|push -f)' libs/beacon/src/beacon/data/skills/contribute-warehouse/scripts/push_warehouse.py
  - **Expected Output**: No matches.
  - **Validation**: Static check passes; code review confirms the only git operations performed are `rev-parse --abbrev-ref HEAD` and `push` (no flags). Add a unit test that asserts these strings are absent from the script source.
<!-- opsx:tdd:6.6:end -->

## 7. Bundled-skill manifest wiring

<!-- opsx:phase-summary:7:begin -->
**Goal**: Register the new skill in `_BUNDLED_SKILL_FILES` so it is installed alongside `record-knowledge` and `record-skill` by `abc warehouse init`, `abc setup`, `abc sync`, and `abc adopt`.
**Input**: `libs/beacon/src/beacon/domains/setup/initializer.py` containing the existing `_BUNDLED_SKILL_FILES` tuple; an understanding of whether the existing wiring path copies per-file or per-directory.
**Output**: Updated `initializer.py` with the new skill's `SKILL.md` (and helper scripts as appropriate) registered. End-to-end install path produces the new skill in `<project>/.opencode/skills/contribute-warehouse/`.
**Validation**: `abc warehouse init <fresh-dir>` followed by connecting a project produces `<project>/.opencode/skills/contribute-warehouse/SKILL.md` plus the four helper scripts. An OpenCode command stub exists at `<project>/.opencode/command/contribute-warehouse.md`.
<!-- opsx:phase-summary:7:end -->


- [ ] 7.1 Open `libs/beacon/src/beacon/domains/setup/initializer.py` and add `"skills/contribute-warehouse/SKILL.md"` to `_BUNDLED_SKILL_FILES`.
<!-- opsx:tdd:7.1:begin -->
  - **Input**: Modify `_BUNDLED_SKILL_FILES` tuple to include the new entry.
  - **Expected Output**: Tuple now contains 3 (or more) entries: `record-knowledge`, `record-skill`, `contribute-warehouse`.
  - **Validation**: Unit test in test_initializer.py asserts membership: `assert "skills/contribute-warehouse/SKILL.md" in _BUNDLED_SKILL_FILES`.
<!-- opsx:tdd:7.1:end -->
- [ ] 7.2 If `_BUNDLED_SKILL_FILES` is per-file (not per-directory), add entries for the four scripts as well; otherwise rely on the directory-copy logic that already handles `record-skill`'s scripts.
<!-- opsx:tdd:7.2:begin -->
  - **Input**: Inspect `_install_bundled_skills` and `wire_bundled_skills_per_project` to determine whether they iterate per-file or per-directory.
  - **Expected Output**: Either: (a) directory-iteration confirmed, no further changes; OR (b) per-file mode, four script entries added.
  - **Validation**: End-to-end smoke test (Task 7.3) confirms the four scripts land in the project's per-agent skill dir alongside SKILL.md.
<!-- opsx:tdd:7.2:end -->
- [ ] 7.3 **[MANUAL]** Verify `abc warehouse init <fresh-dir>` followed by connecting a project produces `<project>/.opencode/skills/contribute-warehouse/SKILL.md` and the four scripts.
<!-- opsx:tdd:7.3:begin -->
  - **Input**: rm -rf /tmp/test-wh /tmp/test-proj && uv run abc warehouse init /tmp/test-wh && cd /tmp/test-proj && uv run abc warehouse connect /tmp/test-wh && ls -la .opencode/skills/contribute-warehouse/
  - **Expected Output**: Directory contains `SKILL.md` plus a `scripts/` subdir with `resolve_warehouse.py`, `summarize_changes.py`, `draft_commit_message.py`, `push_warehouse.py`. An OpenCode command stub exists at `.opencode/command/contribute-warehouse.md`.
  - **Validation**: All five files (SKILL.md + 4 scripts) and the command stub are present and readable.
<!-- opsx:tdd:7.3:end -->

## 8. Documentation references

<!-- opsx:phase-summary:8:begin -->
**Goal**: Surface the new skill to users via the CLI docstring, README, and site-docs so they can discover and learn the `/contribute-warehouse` flow.
**Input**: Existing docstring listing in `libs/beacon/src/beacon/cli/adoption.py`; `libs/beacon/README.md` bundled-skills section; site-docs structure for the existing two skills.
**Output**: Updated CLI docstring listing the three bundled skills; new README entry for `contribute-warehouse`; new site-docs page (or section) covering invocation, lint gate, intent triage, dedup scan, cohesion split, atomic push, and airgap recovery.
**Validation**: `grep -r 'contribute-warehouse' libs/beacon/src/beacon/cli/adoption.py libs/beacon/README.md site-docs/` returns matches in all three locations. Site-docs renders cleanly in a local mkdocs preview.
<!-- opsx:phase-summary:8:end -->


- [ ] 8.1 Update `libs/beacon/src/beacon/cli/adoption.py` docstring listing of bundled skills to include `contribute-warehouse` alongside the existing two.
- [ ] 8.2 Update `libs/beacon/README.md` bundled-skills section to list `contribute-warehouse` with a one-line description.
- [ ] 8.3 Add a section or page to `site-docs/` documenting `/contribute-warehouse`: invocation, the lint pre-flight gate, intent triage, dedup scan, cohesion split, atomic push behaviour, airgap recovery. Include a short example transcript.
<!-- opsx:tdd:8.3:begin -->
  - **Input**: Author site-docs page; cross-link from existing bundled-skills index.
  - **Expected Output**: Page renders cleanly in `mkdocs serve` with no broken links; covers all six topic areas (invocation, lint gate, triage, dedup, cohesion, airgap).
  - **Validation**: `mkdocs build --strict` exits 0 (no warnings about missing pages or broken anchors).
<!-- opsx:tdd:8.3:end -->

## 9. Tests

<!-- opsx:phase-summary:9:begin -->
**Goal**: Achieve verification of the deterministic helper scripts and the distribution contract; intentionally do NOT test the conversational LLM logic.
**Input**: The four implemented scripts; `_BUNDLED_SKILL_FILES` updated; existing test infrastructure under `libs/beacon/tests/unit/` and `tests/integration/`.
**Output**: New unit tests for `summarize_changes.py` and `draft_commit_message.py`; an extended distribution test asserting `contribute-warehouse` membership; a SKILL.md frontmatter parse test. All tests pass under `pytest`.
**Validation**: `pytest` exits 0 with no failures, no errors, no import failures, and shows the four new test files contributing test cases. Distribution test fails the build if `_BUNDLED_SKILL_FILES` regresses.
<!-- opsx:phase-summary:9:end -->


- [ ] 9.1 Add `libs/beacon/tests/unit/data/skills/contribute_warehouse/test_summarize_changes.py` covering: tracked-path filtering against a fixture warehouse with mixed dirty/clean/untracked files; JSON output shape; age computation including the "never committed" case.
<!-- opsx:tdd:9.1:begin -->
  - **Input**: pytest libs/beacon/tests/unit/data/skills/contribute_warehouse/test_summarize_changes.py -v
  - **Expected Output**: All test cases pass; no skipped tests; covers the test_cases enumerated in Task 4.4 and 4.5.
  - **Validation**: Coverage report shows summarize_changes.py is exercised across all branches (filter, status parsing, age computation, JSON shape). Fixture setup uses tmp_path and `git init` for hermetic execution.
  - **TDD Test Cases (write these first):**
    - TC1: Modified tracked file produces correct git_status, diff_stat, and last_commit_age_days
    - TC2: Newly added (staged) file → last_commit_age_days is null
    - TC3: Untracked file ignored by beacon.yaml is excluded from output
    - TC4: Untracked file matched by beacon.yaml patterns appears with `??` status
    - TC5: Clean tracked file is excluded from output (filter logic in Task 4.6)
    - TC6: JSON output is valid and matches the documented schema
    - TC7: Output is deterministic across repeated runs (sorted by path)
    - TC8: Subprocess failure produces a clear error and non-zero exit
<!-- opsx:tdd:9.1:end -->
- [ ] 9.2 Add `libs/beacon/tests/unit/data/skills/contribute_warehouse/test_draft_commit_message.py` covering: scope derivation across the mapping table (contexts-only, knowledge-topic, skills-only, mixed); type-prefix derivation; deterministic output for identical inputs.
<!-- opsx:tdd:9.2:begin -->
  - **Input**: pytest libs/beacon/tests/unit/data/skills/contribute_warehouse/test_draft_commit_message.py -v
  - **Expected Output**: All test cases pass; covers Task 5.3 and 5.4 test cases plus the 'same inputs → same output' invariant from 5.6.
  - **Validation**: Coverage of `derive_scope` and `derive_type` is 100%; determinism test runs 10 iterations and asserts byte-equality.
  - **TDD Test Cases (write these first):**
    - TC1: contexts-only paths → scope `contexts`, type `docs`
    - TC2: knowledge same-topic paths → scope `<topic>`, type `docs`
    - TC3: knowledge mixed-topic paths → scope `knowledge`, type `docs`
    - TC4: skills-only new file → scope `skills`, type `feat`
    - TC5: skills-only existing file → scope `skills`, type `fix` (or as-documented)
    - TC6: mixed contexts + skills → scope `general` or fallback, type `chore`
    - TC7: agents-only path → scope `agents`, type per the rule
    - TC8: empty paths list → ValueError
    - TC9: 10 invocations with identical args produce byte-identical output
<!-- opsx:tdd:9.2:end -->
- [ ] 9.3 Extend the bundled-skill distribution test (or add a new one) that asserts `skills/contribute-warehouse/SKILL.md` is in `_BUNDLED_SKILL_FILES` and that the on-disk skill directory contains the four expected scripts.
<!-- opsx:tdd:9.3:begin -->
  - **Input**: pytest libs/beacon/tests/unit/domains/setup/test_initializer.py -v
  - **Expected Output**: Distribution test asserts membership of `skills/contribute-warehouse/SKILL.md` in `_BUNDLED_SKILL_FILES` and existence of the four script files on disk.
  - **Validation**: Removing the entry from `_BUNDLED_SKILL_FILES` causes the test to fail, proving it actually catches regressions.
  - **TDD Test Cases (write these first):**
    - TC1: `_BUNDLED_SKILL_FILES` contains the new entry
    - TC2: SKILL.md file exists on disk at the expected path
    - TC3: All four scripts exist on disk under `scripts/`
    - TC4: All four scripts have the executable bit set (or are runnable via uv run)
    - TC5: Removing the manifest entry → test FAILS (negative test for catch-fidelity)
<!-- opsx:tdd:9.3:end -->
- [ ] 9.4 Add a SKILL.md frontmatter test that runs `parse_frontmatter` on the bundled `SKILL.md` and asserts `name == "contribute-warehouse"` plus a non-empty `description`.
<!-- opsx:tdd:9.4:begin -->
  - **Input**: pytest libs/beacon/tests/unit/data/skills/contribute_warehouse/test_skill_md.py::test_frontmatter -v
  - **Expected Output**: Test imports `parse_frontmatter`, reads the bundled SKILL.md, asserts `name == 'contribute-warehouse'` and `len(description) > 0`.
  - **Validation**: Test passes against the actual bundled SKILL.md; corrupting the frontmatter (e.g. removing the `name` field) → test FAILS.
<!-- opsx:tdd:9.4:end -->
- [ ] 9.5 Run full test suite: `pytest` (unit + integration). All green before continuing.
<!-- opsx:tdd:9.5:begin -->
  - **Input**: pytest
  - **Expected Output**: Exit code 0; summary line shows `N passed, 0 failed, 0 errors` (skipped is acceptable for offline integration tests if BEACON_OFFLINE=1).
  - **Validation**: Full suite green on the feature branch. CI on the PR also green before merge (re-validated in Task 11.2).
<!-- opsx:tdd:9.5:end -->

## 10. End-to-end validation

<!-- opsx:phase-summary:10:begin -->
**Goal**: Confirm the skill works in a real `abc`-installed project across the full flow, including airgap and lint-failure failure modes. This is the manual happy-path + failure-path validation step required before merging.
**Input**: A locally-built version of `agentic-beacon` from this branch; a fresh test project; a connected warehouse for staging; ability to disable network for the airgap test.
**Output**: Confirmed working flow for: (a) single-commit happy path with successful push; (b) multi-commit cohesion split; (c) lint-failure abort; (d) airgap push failure with correct recovery command. All cases exercised end-to-end through OpenCode.
**Validation**: All four scenarios produce the documented behaviour: scenario (a) exits with one new commit pushed to origin; (b) produces N local commits then exactly one push; (c) aborts before any commit and surfaces lint output; (d) leaves N commits local and prints the recovery command.
<!-- opsx:phase-summary:10:end -->


- [ ] 10.1 **[MANUAL]** Build `agentic-beacon` from this branch and install it into a fresh test project: `uv tool install --reinstall <local path>`.
<!-- opsx:tdd:10.1:begin -->
  - **Input**: cd <agentic-beacon-repo> && uv build && uv tool install --reinstall ./dist/agentic_beacon-*.whl && abc --version
  - **Expected Output**: `abc --version` prints the local development version; `which abc` points at the uv tool install path.
  - **Validation**: The locally-built wheel is installed and resolvable as `abc`; subsequent commands invoke this build, not a stale PyPI install.
<!-- opsx:tdd:10.1:end -->
- [ ] 10.2 **[MANUAL]** In the test project, edit a tracked context file in the warehouse working tree.
<!-- opsx:tdd:10.2:begin -->
  - **Input**: cd <test-project>; echo '## Test edit' >> $(uv run python -c 'from pathlib import Path; import tomllib; cfg = tomllib.loads(Path(".agentic-beacon/config.toml").read_text()); print(cfg["warehouse"]["path"])')/contexts/python-standards.md; cd <warehouse>; git status
  - **Expected Output**: `git status` in the warehouse shows `contexts/python-standards.md` as modified.
  - **Validation**: Working tree is dirty in exactly the expected file; no other accidental changes.
<!-- opsx:tdd:10.2:end -->
- [ ] 10.3 **[MANUAL]** Invoke `/contribute-warehouse` from an OpenCode session and walk the full flow: lint passes → intent confirmed → no dedup overlaps → single cohesive commit → message drafted → confirmed → committed → pushed (or `push_failed` if airgapped).
<!-- opsx:tdd:10.3:begin -->
  - **Input**: From an OpenCode session in the test project, type `/contribute-warehouse`. Confirm each prompt with affirmative responses.
  - **Expected Output**: Skill walks all 8 steps: lint → triage → dedup → cohesion → message draft → contribute → push → final summary. One new commit lands in the warehouse and is pushed to origin.
  - **Validation**: `git -C <warehouse> log -1` shows the new commit with the drafted Conventional Commits message. `git status` clean. Origin has the new commit.
  - **TDD Test Cases (write these first):**
    - TC1: Lint passes; flow proceeds without abort
    - TC2: Intent triage classifies the dirty file as include
    - TC3: Dedup scan returns no overlaps for a contexts/ file
    - TC4: Cohesion check returns 'single cohesive change'
    - TC5: Drafted commit message follows the `<type>(<scope>): <subject>` format
    - TC6: `abc warehouse contribute -m "<msg>"` is invoked WITHOUT `--push`
    - TC7: `push_warehouse.py` is invoked exactly once after the commit
    - TC8: Final summary lists the committed SHA and push status
<!-- opsx:tdd:10.3:end -->
- [ ] 10.4 **[MANUAL]** Repeat with a multi-commit case (two unrelated edits) and verify the cohesion check splits them into two commits and pushes once at the end.
<!-- opsx:tdd:10.4:begin -->
  - **Input**: Edit two unrelated files (e.g. `contexts/python-standards.md` AND `contexts/cicd-flow.md`). Invoke `/contribute-warehouse` and confirm the proposed split.
  - **Expected Output**: Skill proposes 2 commits with separate messages. `abc warehouse contribute` is called twice. `push_warehouse.py` is called once at the end.
  - **Validation**: `git log -2` shows two distinct commits with different messages. `origin/<branch>` advanced by exactly 2 commits in one push.
<!-- opsx:tdd:10.4:end -->
- [ ] 10.5 **[MANUAL]** Repeat with a lint-failing case (introduce a frontmatter-less skill into the warehouse) and verify the skill aborts before any commit.
<!-- opsx:tdd:10.5:begin -->
  - **Input**: mkdir -p <warehouse>/skills/broken-skill && echo '# No frontmatter' > <warehouse>/skills/broken-skill/SKILL.md. Invoke `/contribute-warehouse`.
  - **Expected Output**: Skill runs `abc warehouse lint`, sees the broken skill, aborts before any commit. Surfaces the lint errors. Working tree untouched.
  - **Validation**: `git status` after the abort shows the same dirty state as before. No new commits in `git log`. Lint output mentions `broken-skill`.
<!-- opsx:tdd:10.5:end -->
- [ ] 10.6 **[MANUAL]** Repeat with an airgapped case (disable network) and verify all commits land locally and the recovery command is printed.
<!-- opsx:tdd:10.6:begin -->
  - **Input**: Disable network (e.g. unplug ethernet, disable WiFi, or block via firewall). Edit a tracked file. Invoke `/contribute-warehouse`. Confirm the flow.
  - **Expected Output**: Lint passes (no network needed for local lint). All N commits land locally. `push_warehouse.py` reports failure and prints the recovery command. Skill exits non-zero with a clear summary.
  - **Validation**: `git log <branch>` shows the new commits ahead of `origin/<branch>` by N. The recovery command printed to stdout, when copy-pasted after restoring network, successfully pushes the commits.
<!-- opsx:tdd:10.6:end -->

## 11. Release & rollout

<!-- opsx:phase-summary:11:begin -->
**Goal**: Ship the skill to users via the standard release-please flow on `agentic-beacon`'s public PyPI release branch, and close the Linear ticket.
**Input**: All previous phases complete and tests passing; CI green on the feature branch; PER-175 still in Todo state in Linear.
**Output**: Merged PR on `main`; release-please opens version-bump PR; merging that PR triggers the release workflow; new version of `agentic-beacon` on PyPI containing the bundled skill; PER-175 marked Done with cross-links.
**Validation**: The new agentic-beacon version is installable via `uv tool install --upgrade agentic-beacon` and `abc warehouse init` in a fresh project produces the new bundled skill. PER-175 status in Linear is `Done` with the PR URL and release tag attached.
<!-- opsx:phase-summary:11:end -->


- [ ] 11.1 **[MANUAL]** Open PR against `agentic-beacon` `main` with a clear description linking PER-175.
- [ ] 11.2 **[MANUAL]** Address review comments; ensure CI is green.
<!-- opsx:tdd:11.2:begin -->
  - **Input**: Monitor PR checks: `gh pr checks <pr-number>`
  - **Expected Output**: All required checks pass (build, lint, unit tests, integration tests). Reviewer comments addressed and re-requested where applicable.
  - **Validation**: PR shows green checkmark on all required statuses; at least one approving review.
<!-- opsx:tdd:11.2:end -->
- [ ] 11.3 **[MANUAL]** Merge via GitHub UI (per project convention — never merge locally).
- [ ] 11.4 **[MANUAL]** Confirm release-please opens a version-bump PR; merge it to trigger the release.
<!-- opsx:tdd:11.4:begin -->
  - **Input**: After merge to main, watch for the auto-opened release-please PR (title typically `chore(main): release agentic-beacon X.Y.Z`).
  - **Expected Output**: PR appears within ~5 minutes of merge; CHANGELOG.md updated with the new feat entry referencing PER-175.
  - **Validation**: Merging the release-please PR triggers `release/v*` branch push and the publish workflow runs.
<!-- opsx:tdd:11.4:end -->
- [ ] 11.5 **[MANUAL]** Verify the new version of `agentic-beacon` is on PyPI and includes the new bundled skill.
<!-- opsx:tdd:11.5:begin -->
  - **Input**: uv tool install --reinstall agentic-beacon@<new-version> && uv tool run abc --version && uv tool run abc warehouse init /tmp/post-release-test && ls /tmp/post-release-test/skills/
  - **Expected Output**: `abc --version` prints the new version. `abc warehouse init` produces a warehouse and the bundled skills install path includes `contribute-warehouse/`.
  - **Validation**: PyPI page shows the new version; `pip download agentic-beacon==<v>` succeeds; sample install end-to-end works.
<!-- opsx:tdd:11.5:end -->
- [ ] 11.6 **[MANUAL]** Mark PER-175 as Done in Linear; cross-link the PR and the release tag.

## 12. Archive

<!-- opsx:phase-summary:12:begin -->
**Goal**: Close out the OpenSpec change by promoting its specs into the active spec library and removing it from `openspec/changes/`.
**Input**: All tasks marked complete; release shipped; PER-175 closed.
**Output**: Archived OpenSpec change; `contribute-warehouse-skill` spec promoted into `openspec/specs/`.
**Validation**: `openspec list` no longer shows `ship-bundled-skill-contribute-warehouse` as an active change; `openspec/specs/contribute-warehouse-skill/spec.md` exists; no diff in `openspec/changes/ship-bundled-skill-contribute-warehouse/`.
<!-- opsx:phase-summary:12:end -->


- [ ] 12.1 **[MANUAL]** Run `/opsx-archive ship-bundled-skill-contribute-warehouse` to archive the OpenSpec change once the release ships.
<!-- opsx:tdd:12.1:begin -->
  - **Input**: /opsx-archive ship-bundled-skill-contribute-warehouse
  - **Expected Output**: OpenSpec change archived: `openspec/specs/contribute-warehouse-skill/spec.md` exists; `openspec/changes/ship-bundled-skill-contribute-warehouse/` removed (or marked archived).
  - **Validation**: `openspec list` no longer shows the change as active. `openspec validate` on `contribute-warehouse-skill` spec passes.
<!-- opsx:tdd:12.1:end -->

<!-- opsx:metadata:begin -->
---

## Enhancement Metadata

**Enhanced**: 2026-05-17
**Methodology**: Spec-Driven Development + TDD
**Enhancements Applied**:
- TDD Workflow Header
- Repositories & Branches table
- Phase summaries (Goal/Input/Output/Validation)
- Task-level TDD criteria on 41 task(s)
- 70 test case(s) across complex tasks
- 16 task(s) flagged [MANUAL]

**Status**: Ready for implementation via `/opsx-apply <name>`.
<!-- opsx:metadata:end -->
