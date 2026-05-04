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
| `agentic-beacon` | `~/Code/oss/agentic-beacon` | `auto-pull-artifact-dependencies` | Code changes — manifest model, adoption domain, distribution orchestrator, new scanner + dependency-resolver modules, sample warehouse, tests, migration doc |
| `hl-knowledge-market` | `~/Code/knowledge/hl-knowledge-market` | `artifact-dependencies-frontmatter` | Code changes — pre-flight manual migration: add `requires:` YAML frontmatter to every agent and skill; remove knowledge references from agent bodies. Executed by a separate model via the handoff prompt before any CLI code lands. |
| `sample-warehouse (subtree in agentic-beacon)` | `~/Code/oss/agentic-beacon/examples/sample-warehouse` | `auto-pull-artifact-dependencies` | Code changes — mirror frontmatter additions so `abc warehouse init` emits a migrated warehouse out of the box |
| `PyPI / Release-Please` | `GitHub Actions release workflow` | `main` | Operational only — version bump and PyPI publish on merge; no source changes inside the release pipeline itself |
<!-- opsx:repos-table:end -->

## 1. Warehouse migration (pre-flight, human-executed)

<!-- opsx:phase-summary:1:begin -->
**Goal**: Bring the canonical personal warehouse into compliance with the new frontmatter contract BEFORE the code change lands, so that post-upgrade sync succeeds without special-casing.
**Input**: `~/Code/knowledge/hl-knowledge-market/` on main with 8 agents and ~20 skills that currently have no `requires:` frontmatter; the warehouse migration prompt drafted in the planning session; access to the `artifact-dependencies-frontmatter` branch.
**Output**: Every agent in `agents/*.md` and every skill in `skills/*/SKILL.md` carries a validated `requires:` block. All `TODO: verify` flags resolved. Changes committed with a conventional commit message. No knowledge references remain in agent bodies.
**Validation**: `grep -L 'requires:' agents/*.md skills/*/SKILL.md` returns empty (every file has the key). For every name listed in any `requires.contexts`, a matching `contexts/<name>.md` exists. For every name listed in any agent's `requires.skills`, a matching `skills/<name>/` directory exists. `git log -1 --format=%s` on the warehouse shows a conventional-commit message describing the frontmatter migration.
<!-- opsx:phase-summary:1:end -->


- [ ] 1.1 **[MANUAL]** Hand the warehouse migration prompt to a separate model and run it against `~/Code/knowledge/hl-knowledge-market/`
<!-- opsx:tdd:1.1:begin -->
  - **Input**: The warehouse migration prompt (delivered in the planning session); separate LLM session with write access to `~/Code/knowledge/hl-knowledge-market/`; branch `artifact-dependencies-frontmatter` checked out.
  - **Expected Output**: Every `agents/*.md` and every `skills/*/SKILL.md` has been modified in place to include a `requires:` YAML frontmatter block; the model's summary reports the before/after frontmatter for every file plus any `TODO: verify` flags.
  - **Validation**: `cd ~/Code/knowledge/hl-knowledge-market && git status --short` shows the expected set of modified files; `git diff agents/ skills/` reveals only frontmatter additions, no body-content edits.
  - **Note**: This task is executed by a separate model session, not by the implementation agent. The human operator is the validator.
  - **TDD Test Cases (write these first):**
    - TC1: Model run produces a summary listing every agent and every skill with its final `requires` block → Summary covers all 8 agents and ~20 skills
    - TC2: An agent that legitimately needs zero deps → Emitted block is `requires: { contexts: [], skills: [] }`, not the key being omitted
    - TC3: An agent whose prose mentions an ambiguous skill reference → Entry marked `# TODO: verify` and flagged in summary
    - TC4: A skill's body content after migration → Byte-identical to pre-migration below the frontmatter
    - TC5: A non-agent, non-SKILL file under the warehouse (e.g. `contexts/*.md`, `knowledge/**`) → Untouched by the run
<!-- opsx:tdd:1.1:end -->
- [ ] 1.2 **[MANUAL]** Review generated `requires:` frontmatter on all agents in the warehouse
<!-- opsx:tdd:1.2:begin -->
  - **Input**: The 8 modified agent files under `~/Code/knowledge/hl-knowledge-market/agents/` after task 1.1.
  - **Expected Output**: Every agent file's `requires.contexts` and `requires.skills` list reflects the operator's authoritative intent.
  - **Validation**: For each name in `requires.contexts`, `test -f contexts/<name>.md` returns 0. For each name in `requires.skills`, `test -d skills/<name>` returns 0. Operator confirms semantic accuracy by reading the agent's prose.
<!-- opsx:tdd:1.2:end -->
- [ ] 1.3 **[MANUAL]** Review generated `requires:` frontmatter on all skills in the warehouse
<!-- opsx:tdd:1.3:begin -->
  - **Input**: All `skills/*/SKILL.md` files after task 1.1.
  - **Expected Output**: Every skill file has `requires.contexts` as a list (possibly empty) and no `requires.skills` key.
  - **Validation**: `for f in skills/*/SKILL.md; do python3 -c 'import yaml, sys; d = yaml.safe_load(open(sys.argv[1]).read().split("---")[1]); assert "skills" not in d.get("requires", {}), sys.argv[1]' "$f"; done` exits 0 for every file.
<!-- opsx:tdd:1.3:end -->
- [ ] 1.4 **[MANUAL]** Resolve every `TODO: verify` flag produced by the migration pass
<!-- opsx:tdd:1.4:begin -->
  - **Input**: The summary from task 1.1 plus every file that the migration model flagged.
  - **Expected Output**: Zero `# TODO: verify` comments remain in any agent or skill frontmatter.
  - **Validation**: `rg -n 'TODO: verify' agents/ skills/` returns zero matches.
<!-- opsx:tdd:1.4:end -->
- [ ] 1.5 **[MANUAL]** Commit the warehouse frontmatter changes with a conventional commit message
- [ ] 1.6 **[MANUAL]** Confirm no knowledge references leaked into agent files; rewrite any that did
<!-- opsx:tdd:1.6:begin -->
  - **Input**: All `agents/*.md` on the `artifact-dependencies-frontmatter` branch.
  - **Expected Output**: Zero markdown links in any agent file resolve to a path under `knowledge/`.
  - **Validation**: `rg -n '\]\([^)]*knowledge[^)]*\.md\)' agents/` returns zero matches.
  - **TDD Test Cases (write these first):**
    - TC1: An agent currently contains `[x](../knowledge/foo/bar.md)` → Rewrite to reference the containing context, or move the link into that context
    - TC2: An agent contains no knowledge links → No change required
    - TC3: An agent contains a knowledge link inside a code fence (documentation example) → Preserve as-is; the scanner ignores code-fence contents under normal markdown parsing
<!-- opsx:tdd:1.6:end -->

## 2. Migration documentation

<!-- opsx:phase-summary:2:begin -->
**Goal**: Publish the authoritative migration doc and link it from the places consumers will actually look, so error messages have a stable target URL.
**Input**: `docs/migrations/artifact-dependencies-frontmatter.md` already drafted and written to disk during the planning session; existing `README.md` and `guides/beacon-yaml-reference.md`.
**Output**: Migration doc present in repo; README / docs index links to it; `beacon-yaml-reference.md` explicitly flags removal of `artifacts.knowledge`.
**Validation**: Doc path resolves; every link from the error surface (tasks 8.9, 4.x) is a live relative path. Markdown lint (if CI has one) passes.
<!-- opsx:phase-summary:2:end -->


- [x] 2.1 Verify `docs/migrations/artifact-dependencies-frontmatter.md` exists in the repo (already drafted)
<!-- opsx:tdd:2.1:begin -->
  - **Input**: The file written during the planning session.
  - **Expected Output**: File exists, is non-empty, and begins with `# Migration: Artifact Dependencies via Frontmatter`.
  - **Validation**: `test -s docs/migrations/artifact-dependencies-frontmatter.md && head -1 docs/migrations/artifact-dependencies-frontmatter.md | grep -q 'Migration: Artifact Dependencies via Frontmatter'`
<!-- opsx:tdd:2.1:end -->
- [x] 2.2 Add a link from the top-level README or docs index to the migration doc
- [x] 2.3 Add a link from `guides/beacon-yaml-reference.md` explaining that `knowledge:` has been removed

## 3. Manifest changes

<!-- opsx:phase-summary:3:begin -->
**Goal**: Update `ArtifactsConfig` to remove `knowledge` and add `agents`; wire the legacy-drop migration so old `beacon.yaml` files sync cleanly once.
**Input**: Current `libs/beacon/src/beacon/core/manifest/beacon.py` with `ArtifactsConfig.knowledge: list[str]`; loader in the same module.
**Output**: `ArtifactsConfig` has `agents` and no `knowledge`; loader strips any legacy `artifacts.knowledge` key from parsed YAML with a one-shot info log; writer never serializes the field.
**Validation**: `pytest libs/beacon/tests/unit/core/manifest/ -v` passes, including new tests for legacy drop, logging behaviour, and clean round-trip writes.
<!-- opsx:phase-summary:3:end -->


- [x] 3.1 Remove `knowledge: list[str]` from `ArtifactsConfig` in `libs/beacon/src/beacon/core/manifest/beacon.py`
<!-- opsx:tdd:3.1:begin -->
  - **Input**: `libs/beacon/src/beacon/core/manifest/beacon.py` with current `ArtifactsConfig` schema including `knowledge`.
  - **Expected Output**: `ArtifactsConfig` contains only `agents`, `contexts`, `skills` fields; `knowledge` attribute raises `AttributeError`.
  - **Validation**: `uv run python -c 'from beacon.core.manifest.beacon import ArtifactsConfig; a = ArtifactsConfig(); assert not hasattr(a, "knowledge"), "knowledge still present"; assert hasattr(a, "agents")'` exits 0.
<!-- opsx:tdd:3.1:end -->
- [x] 3.2 Add `agents: list[str]` to `ArtifactsConfig` if not already present
<!-- opsx:tdd:3.2:begin -->
  - **Input**: `ArtifactsConfig` after task 3.1.
  - **Expected Output**: `ArtifactsConfig().agents` returns an empty list by default; assigning a list persists through YAML round-trip.
  - **Validation**: Unit test: `assert ArtifactsConfig().agents == []` and round-trip with `agents: [agents/foo.md]` preserves the list.
<!-- opsx:tdd:3.2:end -->
- [x] 3.3 Add a legacy-drop migration hook in the manifest loader: on read, if the YAML contains `artifacts.knowledge`, remove it from the parsed dict before Pydantic validation and emit a one-shot info log
<!-- opsx:tdd:3.3:begin -->
  - **Input**: Legacy beacon.yaml: `artifacts:\n  knowledge: [knowledge/foo]\n  contexts: []\n  skills: []`.
  - **Expected Output**: Loader parses successfully, returns a `BeaconManifest` whose serialized form has no `knowledge` key, and emits exactly one `loguru` INFO-level record matching `artifacts.knowledge removed; knowledge is now auto-derived`.
  - **Validation**: Pytest captures the log record via the `caplog` fixture; serialized YAML has no `knowledge:` line.
  - **TDD Test Cases (write these first):**
    - TC1: Legacy YAML with populated `knowledge` list → field stripped, one log emitted, manifest valid
    - TC2: Legacy YAML with empty `knowledge: []` → field stripped, one log emitted, manifest valid
    - TC3: Modern YAML with no `knowledge` key → no log emitted, manifest valid
    - TC4: YAML missing the `artifacts` key entirely → existing error path triggers (not the migration hook); no migration log
    - TC5: Legacy YAML loaded twice in the same process → log emitted each time the loader runs against a file containing the legacy key (hook is per-load, not per-process; spec says 'one-shot' per migrated file)
    - TC6: Legacy YAML with both `knowledge` and an unexpected extra key → migration drops `knowledge`, extra key triggers the existing validation error pathway
<!-- opsx:tdd:3.3:end -->
- [x] 3.4 Ensure the manifest writer never serializes a `knowledge:` key even if it somehow sneaks into the object
<!-- opsx:tdd:3.4:begin -->
  - **Input**: A `BeaconManifest` instance; attempt to mutate with `setattr(manifest.artifacts, "knowledge", ["x"])`.
  - **Expected Output**: Pydantic rejects the attribute (extra fields forbidden) OR the writer explicitly filters the key during serialization such that the written YAML contains no `knowledge:` line.
  - **Validation**: Unit test: after write, `yaml.safe_load(open(path).read())["artifacts"]` has no `knowledge` key.
  - **TDD Test Cases (write these first):**
    - TC1: Model frozen with `extra=forbid` → setattr raises ValidationError; writer unreachable → pass
    - TC2: If model is permissive, writer filters → round-trip produces no `knowledge:` line
    - TC3: Manifest constructed with all defaults → written YAML contains `agents`, `contexts`, `skills` keys only
<!-- opsx:tdd:3.4:end -->
- [x] 3.5 Unit tests: legacy field drop, logging behaviour, round-trip write without knowledge
<!-- opsx:tdd:3.5:begin -->
  - **Input**: Test fixtures: legacy YAML file, modern YAML file, empty YAML file.
  - **Expected Output**: All tests pass; coverage reports that the legacy-drop branch is exercised.
  - **Validation**: `uv run pytest libs/beacon/tests/unit/core/manifest/ -v` → all passing, no skipped migration tests.
<!-- opsx:tdd:3.5:end -->

## 4. Frontmatter parsing and validation

<!-- opsx:phase-summary:4:begin -->
**Goal**: Introduce machine-readable `requires:` parsing for agents and skills with strict schema enforcement.
**Input**: Pydantic v2 in the project dependency tree; PyYAML already available; specs from `openspec/changes/auto-pull-artifact-dependencies/specs/artifact-dependency-resolution/spec.md`.
**Output**: `AgentFrontmatter` and `SkillFrontmatter` Pydantic models with validators; `parse_frontmatter()` and `validate_requires_against_warehouse()` callable; unit tests cover valid / missing / malformed / forbidden-key cases.
**Validation**: `pytest libs/beacon/tests/unit/core/dependencies/` (or equivalent path) returns zero failures; parser correctly rejects a skill with a forbidden `skills:` key; parser produces structured errors for malformed YAML.
<!-- opsx:phase-summary:4:end -->


- [x] 4.1 Create `libs/beacon/src/beacon/core/dependencies/` module (or `core/frontmatter/` — pick based on neighbouring conventions)
- [x] 4.2 Implement `parse_frontmatter(path: Path) -> FrontmatterResult` returning parsed YAML or a structured error
<!-- opsx:tdd:4.2:begin -->
  - **Input**: Markdown file with `---\n<yaml>\n---\n<body>\n` structure.
  - **Expected Output**: `FrontmatterResult` containing parsed dict on success, or a structured error naming the file and parse problem on failure. Body content is discarded (not required for dep resolution).
  - **Validation**: Unit tests cover each branch of `FrontmatterResult`.
  - **TDD Test Cases (write these first):**
    - TC1: Well-formed frontmatter with scalar keys → returns parsed dict with those keys
    - TC2: No frontmatter at all → returns structured error `missing-frontmatter`
    - TC3: Frontmatter present but malformed YAML (tab indent) → returns error with YAML parse diagnostic
    - TC4: Frontmatter opened with `---` but never closed → returns error `unterminated-frontmatter`
    - TC5: File starts with BOM or leading whitespace → parser tolerates, extracts frontmatter correctly
    - TC6: Frontmatter with nested `requires` block → nested structure preserved in output dict
    - TC7: File does not exist → parser raises (or returns error) `file-not-found` with the path
<!-- opsx:tdd:4.2:end -->
- [x] 4.3 Define `AgentFrontmatter` and `SkillFrontmatter` Pydantic models with `requires` validation rules from spec
<!-- opsx:tdd:4.3:begin -->
  - **Input**: Parsed frontmatter dicts for agents (with `requires.contexts` and `requires.skills`) and skills (with `requires.contexts`).
  - **Expected Output**: `AgentFrontmatter.model_validate(dict)` succeeds for valid shapes and fails with clear errors for invalid ones. Same for `SkillFrontmatter`.
  - **Validation**: Pydantic ValidationError raised on missing keys, wrong types, forbidden keys.
  - **TDD Test Cases (write these first):**
    - TC1: Agent with `requires: { contexts: [foo], skills: [bar] }` → validates
    - TC2: Agent with `requires: { contexts: [], skills: [] }` → validates
    - TC3: Agent missing `requires` entirely → ValidationError identifying the missing key
    - TC4: Agent with `requires: { contexts: [foo] }` missing `skills` → ValidationError identifying `skills` as required
    - TC5: Skill with `requires: { contexts: [foo] }` → validates
    - TC6: Skill with `requires: { contexts: [], skills: [] }` → ValidationError: `skills` not permitted on skills
    - TC7: Skill missing `requires` entirely → ValidationError identifying missing key
    - TC8: Agent with `requires.contexts: 'foo'` (string not list) → ValidationError
    - TC9: Agent with duplicate entries `requires.contexts: [foo, foo]` → either deduplicated silently or validated; decide per spec, test asserts chosen behaviour
<!-- opsx:tdd:4.3:end -->
- [x] 4.4 Reject `requires.skills` on `SkillFrontmatter` at parse time (spec requirement)
<!-- opsx:tdd:4.4:begin -->
  - **Input**: Skill YAML containing `requires: { contexts: [], skills: [foo] }`.
  - **Expected Output**: ValidationError with message explaining skill-to-skill deps are not supported and pointing to the migration doc.
  - **Validation**: Error message contains both 'skill' and the migration-doc path.
<!-- opsx:tdd:4.4:end -->
- [x] 4.5 Implement `validate_requires_against_warehouse(frontmatter, warehouse_path)` — each name must resolve to an existing warehouse file
<!-- opsx:tdd:4.5:begin -->
  - **Input**: Parsed frontmatter object + `Path` to a warehouse clone.
  - **Expected Output**: `list[ValidationError]` — empty on success, one entry per missing target on failure. Each error includes the referring artifact, the missing name, and the expected warehouse path.
  - **Validation**: Fixture warehouse with known contents; assert validator returns expected error list.
  - **TDD Test Cases (write these first):**
    - TC1: Agent `requires.contexts: [python-standards]`, warehouse has `contexts/python-standards.md` → empty error list
    - TC2: Agent `requires.contexts: [missing]`, warehouse lacks `contexts/missing.md` → one error naming 'missing' and the expected path
    - TC3: Agent `requires.skills: [record-knowledge]`, warehouse has `skills/record-knowledge/` but no SKILL.md inside → error naming the missing SKILL.md
    - TC4: Skill `requires.contexts: [python-standards, testing]`, warehouse has first but not second → single error for `testing`
    - TC5: Empty requires.contexts / requires.skills → empty error list (not an error)
<!-- opsx:tdd:4.5:end -->
- [x] 4.6 Unit tests: valid agent, valid skill, missing `requires`, malformed YAML, skill with forbidden `skills` key, dangling reference
<!-- opsx:tdd:4.6:begin -->
  - **Input**: Fixture directory tree for a minimal warehouse + fixture markdown files for each scenario.
  - **Expected Output**: All unit tests in the module pass; coverage of `FrontmatterResult` branches, Pydantic model validators, and `validate_requires_against_warehouse` branches is complete.
  - **Validation**: `uv run pytest libs/beacon/tests/unit/core/dependencies/ -v --cov=beacon.core.dependencies --cov-fail-under=90` (or equivalent) → pass.
<!-- opsx:tdd:4.6:end -->

## 5. Knowledge reference scanner

<!-- opsx:phase-summary:5:begin -->
**Goal**: Build the scanner that converts context/skill markdown links into a derived knowledge set, using pathlib resolution and the four-part classifier.
**Input**: Adopted contexts and skill SKILL.md files from the warehouse clone; `WarehouseSettings` providing the warehouse root.
**Output**: Scanner module with `extract_markdown_links`, `resolve_link`, `classify_knowledge_ref`, `scan_file_for_knowledge`, `scan_adopted_artifacts`. Missing-target warnings emitted but non-fatal.
**Validation**: `pytest libs/beacon/tests/unit/core/scanner/` passes all classifier edge-case tests; given the real `contexts/python-standards.md` the scanner returns exactly the 12+ knowledge paths referenced in its body.
<!-- opsx:phase-summary:5:end -->


- [ ] 5.1 Create `libs/beacon/src/beacon/core/scanner/` module
- [ ] 5.2 Implement `extract_markdown_links(file_content: str) -> list[LinkRef]` that extracts every `[text](target)` link
<!-- opsx:tdd:5.2:begin -->
  - **Input**: Raw markdown string with a mix of inline links, reference-style links, and non-link brackets.
  - **Expected Output**: `list[LinkRef]` with `(text, target)` for each inline link; reference-style links either skipped or resolved against the reference definitions (document choice in code comment).
  - **Validation**: Unit tests compare returned list against hand-crafted expected list.
  - **TDD Test Cases (write these first):**
    - TC1: `[foo](bar.md)` → one LinkRef(text='foo', target='bar.md')
    - TC2: Text with no links → empty list
    - TC3: Link with spaces in text: `[foo bar](baz.md)` → correctly extracted
    - TC4: Link with parens in target: `[x](foo(y).md)` → respects Markdown escaping rules (test the chosen behaviour)
    - TC5: Image link `![alt](img.png)` → extracted as a link OR skipped (choose per design; test asserts chosen behaviour)
    - TC6: Link inside a code fence ``` `[x](y)` ``` → NOT extracted (code fences are data, not links)
    - TC7: Link inside inline code `` `[x](y)` `` → NOT extracted
    - TC8: Reference-style `[x][ref]` with `[ref]: url` → either skipped or resolved (document choice)
    - TC9: Escaped brackets `\[x\](y)` → NOT extracted
    - TC10: Multiple links on one line → all extracted in document order
<!-- opsx:tdd:5.2:end -->
- [ ] 5.3 Strip URL fragments (`#section`) and URL-decode link targets
<!-- opsx:tdd:5.3:begin -->
  - **Input**: Link targets containing `#anchor` suffixes and/or `%20`-encoded characters.
  - **Expected Output**: Fragment removed; `%XX` sequences decoded to original characters.
  - **Validation**: Unit test: `normalize("foo%20bar.md#section")` == `"foo bar.md"`.
  - **TDD Test Cases (write these first):**
    - TC1: `foo.md#anchor` → `foo.md`
    - TC2: `foo%20bar.md` → `foo bar.md`
    - TC3: `foo.md` (no fragment, no encoding) → unchanged
    - TC4: `#just-a-fragment` → empty string (fragment-only link)
    - TC5: `foo.md#anchor#another` → `foo.md` (first `#` splits)
<!-- opsx:tdd:5.3:end -->
- [ ] 5.4 Skip absolute URLs (`http://`, `https://`, `mailto:`, etc.)
<!-- opsx:tdd:5.4:begin -->
  - **Input**: Link targets with various URL schemes.
  - **Expected Output**: Function returns `None` (or equivalent skip marker) for any target with a URL scheme.
  - **Validation**: Unit test: `is_absolute_url("https://example.com")` is True; `is_absolute_url("../foo.md")` is False.
  - **TDD Test Cases (write these first):**
    - TC1: `https://example.com/foo` → skip
    - TC2: `http://example.com` → skip
    - TC3: `mailto:x@y.com` → skip
    - TC4: `ftp://host/path` → skip
    - TC5: `file:///local/path` → skip (absolute file URI)
    - TC6: `../foo.md` → not skipped (relative)
    - TC7: `/absolute/path.md` → not skipped at this layer (left to resolve_link; implementation may choose skip or treat as warehouse-absolute)
<!-- opsx:tdd:5.4:end -->
- [ ] 5.5 Implement `resolve_link(scanned_file: Path, link: str, warehouse_root: Path) -> ResolvedLink | None` — returns None for out-of-warehouse or absolute-URL links
<!-- opsx:tdd:5.5:begin -->
  - **Input**: Absolute path to a scanned file, a relative link string, the warehouse root.
  - **Expected Output**: `ResolvedLink` with the warehouse-relative resolved path on success; `None` if resolution lands outside the warehouse or the link is absolute.
  - **Validation**: Unit tests compare resolution against expected warehouse-relative paths.
  - **TDD Test Cases (write these first):**
    - TC1: scanned=`/wh/contexts/python-standards.md`, link=`../knowledge/foo/bar.md`, wh=`/wh` → ResolvedLink(`knowledge/foo/bar.md`)
    - TC2: scanned=`/wh/skills/s/SKILL.md`, link=`../../knowledge/foo/bar.md`, wh=`/wh` → ResolvedLink(`knowledge/foo/bar.md`)
    - TC3: scanned=`/wh/contexts/a.md`, link=`../../../other/repo/x.md`, wh=`/wh` → None (out of warehouse)
    - TC4: scanned=`/wh/contexts/a.md`, link=`https://example.com`, wh=`/wh` → None (absolute URL)
    - TC5: scanned=`/wh/contexts/a.md`, link=`./b.md`, wh=`/wh` → ResolvedLink(`contexts/b.md`) (same-dir sibling)
    - TC6: scanned=`/wh/contexts/nested/a.md`, link=`../../knowledge/x.md`, wh=`/wh` → ResolvedLink(`knowledge/x.md`) (deep nesting)
    - TC7: scanned=`/wh/contexts/a.md`, link=`../knowledge/`, wh=`/wh` → ResolvedLink(`knowledge/`) or None if classifier requires `.md` ending (defer to classifier)
    - TC8: Symlinks in path → resolved against realpath? Test documents the chosen behaviour
<!-- opsx:tdd:5.5:end -->
- [ ] 5.6 Implement `classify_knowledge_ref(resolved: Path, warehouse_root: Path) -> bool` — the four-part classifier from spec
<!-- opsx:tdd:5.6:begin -->
  - **Input**: A warehouse-resolved path + warehouse root.
  - **Expected Output**: True iff the warehouse-relative path starts with `knowledge/` AND ends with `.md`.
  - **Validation**: Classifier returns True only for paths matching both conditions.
  - **TDD Test Cases (write these first):**
    - TC1: `knowledge/python-standards/lessons/foo.md` → True
    - TC2: `contexts/other.md` → False (not under knowledge/)
    - TC3: `knowledge/diagram.png` → False (not .md)
    - TC4: `knowledge/README.md` → True (any .md under knowledge counts)
    - TC5: `knowledge.md` (top-level, not a dir prefix) → False
    - TC6: `foo/knowledge/x.md` (knowledge is a subdir, not top-level) → False
    - TC7: `knowledge/` (directory, not a file) → False
<!-- opsx:tdd:5.6:end -->
- [ ] 5.7 Implement `scan_file_for_knowledge(path, warehouse_root) -> set[warehouse_relative_path]`
<!-- opsx:tdd:5.7:begin -->
  - **Input**: Path to a context or skill SKILL.md file; warehouse root.
  - **Expected Output**: Set of unique warehouse-relative paths classified as knowledge refs.
  - **Validation**: Compose extract + normalize + resolve + classify; assert set matches hand-computed expected set.
  - **TDD Test Cases (write these first):**
    - TC1: File with 12 knowledge links (real `python-standards.md`) → set has exactly the 12 unique targets
    - TC2: File with duplicate knowledge links to same target → set has one entry (deduplicated)
    - TC3: File with mixed knowledge and non-knowledge links → only knowledge links in the returned set
    - TC4: File with broken YAML frontmatter but valid body → body still scanned; frontmatter parse error ignored by scanner
    - TC5: Empty file → empty set
<!-- opsx:tdd:5.7:end -->
- [ ] 5.8 Implement `scan_adopted_artifacts(beacon, warehouse_root) -> set[warehouse_relative_path]` — iterates adopted contexts and skill SKILL.md files
<!-- opsx:tdd:5.8:begin -->
  - **Input**: A `BeaconManifest` with known contexts/skills adopted; warehouse root with fixture files.
  - **Expected Output**: Union of knowledge refs across every adopted context and skill SKILL.md.
  - **Validation**: Fixture test: assert returned set matches the known ground truth.
  - **TDD Test Cases (write these first):**
    - TC1: Two contexts sharing a knowledge link → set has one entry for the shared target
    - TC2: A skill's SKILL.md with its own knowledge links → included in the union
    - TC3: A skill adopted but its SKILL.md doesn't exist in warehouse → error surfaces here OR deferred to validator (document choice)
    - TC4: No adopted contexts or skills → empty set
    - TC5: Adopted context with no knowledge links → contributes zero to the set
<!-- opsx:tdd:5.8:end -->
- [ ] 5.9 Emit a warning when a classified knowledge reference resolves to a warehouse path that doesn't exist on disk
<!-- opsx:tdd:5.9:begin -->
  - **Input**: Fixture context that links to `knowledge/missing.md` which doesn't exist.
  - **Expected Output**: Scanner includes `knowledge/missing.md` in its output set (scanner doesn't drop refs) AND emits one loguru WARNING record naming the referrer and the missing file.
  - **Validation**: `caplog` captures exactly one warning; set contains the entry (downstream decides what to do).
<!-- opsx:tdd:5.9:end -->
- [ ] 5.10 Unit tests: classifier edge cases, URL handling, fragment stripping, out-of-warehouse links, non-md links under knowledge/, deep nesting
<!-- opsx:tdd:5.10:begin -->
  - **Input**: The aggregated test suite for the scanner module.
  - **Expected Output**: All scanner unit tests pass; coverage ≥ 90% on the scanner module.
  - **Validation**: `uv run pytest libs/beacon/tests/unit/core/scanner/ -v --cov=beacon.core.scanner --cov-fail-under=90` → pass.
<!-- opsx:tdd:5.10:end -->

## 6. Dependency resolution

<!-- opsx:phase-summary:6:begin -->
**Goal**: Compose frontmatter parsing and scanning into a single `EffectiveSet` computation that yields explicit + transitive contexts, skills, and derived knowledge, plus collected errors for unadopted deps.
**Input**: Loaded `BeaconManifest`, connected warehouse; outputs of frontmatter parser and scanner.
**Output**: `compute_effective_set(beacon, warehouse) -> EffectiveSet` deterministic and pure; `is_transitively_required(...)` helper; structured failure type listing all missing deps collected in a single pass.
**Validation**: Unit tests pass for empty manifest, single-hop, multi-hop (agent→skill→context), diamond (two artifacts share a knowledge file), missing-context-in-warehouse, missing-context-in-adoption. Running `compute_effective_set` twice with identical inputs returns equal results.
<!-- opsx:phase-summary:6:end -->


- [ ] 6.1 Create `libs/beacon/src/beacon/core/dependencies/resolver.py`
- [ ] 6.2 Implement `compute_effective_set(beacon, warehouse) -> EffectiveSet` where `EffectiveSet` contains explicit + transitive contexts, skills, and derived knowledge
<!-- opsx:tdd:6.2:begin -->
  - **Input**: A `BeaconManifest` and a connected warehouse fixture.
  - **Expected Output**: `EffectiveSet(contexts, skills, knowledge)` where each field is a frozenset of warehouse-relative paths.
  - **Validation**: Idempotent: calling twice yields equal sets. Deterministic: two runs on the same fixture produce the same serialized output.
  - **TDD Test Cases (write these first):**
    - TC1: Empty manifest → all three sets empty
    - TC2: One explicit context, no agent, no skill → contexts={that}, skills=∅, knowledge=(whatever that context refs)
    - TC3: One agent requiring one context → contexts contain the context even though not explicitly adopted
    - TC4: Chained agent→skill→context → all three tiers populated
    - TC5: Two contexts sharing a knowledge file → knowledge set has one entry, not two
    - TC6: Explicit context plus an agent that requires the same context → contexts contain it once; provenance marked `explicit`
    - TC7: Explicit skill unreferenced by any agent → skills contain it, contexts it requires are transitively included
    - TC8: Agent requiring non-existent context → EffectiveSet returns structured failure, not partial state
<!-- opsx:tdd:6.2:end -->
- [ ] 6.3 Walk agents' `requires` first (yields required contexts and skills)
- [ ] 6.4 Walk adopted and transitively-required skills' `requires.contexts` next
- [ ] 6.5 Run the scanner over all contexts and skills in the effective set to derive knowledge
- [ ] 6.6 Collect missing-dependency errors into a list; return structured failure when non-empty
<!-- opsx:tdd:6.6:begin -->
  - **Input**: Manifest with one agent requiring three contexts, two of which are missing.
  - **Expected Output**: Resolver returns structured failure containing both missing-dep errors in one list (not short-circuit on first).
  - **Validation**: Assert `len(failure.errors) == 2` and each error names the correct missing context.
  - **TDD Test Cases (write these first):**
    - TC1: Single missing context → failure with 1 error
    - TC2: Two missing contexts in same agent → failure with 2 errors, collected in one pass
    - TC3: Missing context and missing skill in same agent → failure with 2 errors covering both kinds
    - TC4: Missing context required by a transitively-pulled skill → failure with 1 error, path chain in message
<!-- opsx:tdd:6.6:end -->
- [ ] 6.7 Provide a pure function `is_transitively_required(artifact, effective_set) -> bool` for use in pruning decisions
<!-- opsx:tdd:6.7:begin -->
  - **Input**: An artifact name + the resolver's `EffectiveSet` (including provenance).
  - **Expected Output**: True iff the artifact is in the effective set but not in the explicit adoption list.
  - **Validation**: Unit tests cover explicit-only, transitive-only, both, neither.
  - **TDD Test Cases (write these first):**
    - TC1: Context in explicit list → False
    - TC2: Context in effective set but not explicit list → True
    - TC3: Context in both (explicit + required by agent) → False (explicit wins)
    - TC4: Context in neither → False (nothing to prune)
<!-- opsx:tdd:6.7:end -->
- [ ] 6.8 Unit tests: empty manifest, single agent with one context dep, chained agent→skill→context, multiple referrers sharing a knowledge file, missing context in warehouse, missing context in adoption
<!-- opsx:tdd:6.8:begin -->
  - **Input**: Fixtures for each scenario.
  - **Expected Output**: All resolver unit tests pass; coverage ≥ 90%.
  - **Validation**: `uv run pytest libs/beacon/tests/unit/core/dependencies/ -v --cov=beacon.core.dependencies.resolver --cov-fail-under=90` → pass.
<!-- opsx:tdd:6.8:end -->

## 7. Adoption domain changes

<!-- opsx:phase-summary:7:begin -->
**Goal**: Remove knowledge from discovery/TUI, add agents as a first-class selectable category, and add the dependency-confirmation prompt.
**Input**: Current `libs/beacon/src/beacon/domains/adoption/` with knowledge as a tier in discovery, TUI, and apply.
**Output**: Knowledge references purged from adoption; agent category present; TUI prompts for unadopted transitive deps after initial selection; decline path emits the spec-mandated warning.
**Validation**: Unit tests + integration test harness for TUI in non-interactive mode return expected dependency sets; the removed `KNOWLEDGE_SUBTYPES` constant (or equivalent) has zero remaining references via `rg KNOWLEDGE_SUBTYPES libs/beacon/src`.
<!-- opsx:phase-summary:7:end -->


- [ ] 7.1 Remove knowledge from `KNOWLEDGE_SUBTYPES` usage in discovery (or delete the constant entirely)
<!-- opsx:tdd:7.1:begin -->
  - **Input**: Current `libs/beacon/src/beacon/domains/adoption/models.py:9` defining `KNOWLEDGE_SUBTYPES`.
  - **Expected Output**: Either the constant is deleted and all references removed, or it remains but is no longer wired into discovery/TUI.
  - **Validation**: `rg -n KNOWLEDGE_SUBTYPES libs/beacon/src/` returns zero matches (preferred) or matches only in deprecated/deleted modules.
<!-- opsx:tdd:7.1:end -->
- [ ] 7.2 Remove `_build_knowledge_subtree` closure and the knowledge section from the TUI
<!-- opsx:tdd:7.2:begin -->
  - **Input**: Current `libs/beacon/src/beacon/domains/adoption/tui.py:293-400`.
  - **Expected Output**: TUI renders three sections (Contexts, Skills, Agents); no knowledge section or tree widget appears.
  - **Validation**: Snapshot test or direct widget introspection: top-level tree has exactly three roots, none named 'Knowledge'.
<!-- opsx:tdd:7.2:end -->
- [ ] 7.3 Add agents as a first-class discovery category if not already (check current state of adoption domain)
<!-- opsx:tdd:7.3:begin -->
  - **Input**: A warehouse fixture containing `agents/foo.md` with valid frontmatter.
  - **Expected Output**: `discover_all()` (or equivalent) returns the agent as an adoption candidate alongside contexts and skills.
  - **Validation**: Unit test: assert the agent appears in the discovery output with the expected path and description.
<!-- opsx:tdd:7.3:end -->
- [ ] 7.4 Implement `collect_required_dependencies(selected, warehouse) -> list[RequiredDep]` that inspects selected agents' and skills' frontmatter
<!-- opsx:tdd:7.4:begin -->
  - **Input**: A set of 'selected' adoption candidates + warehouse reference.
  - **Expected Output**: List of `RequiredDep(referrer, target_type, target_name, already_adopted)` — one per frontmatter requirement, deduplicated across selections.
  - **Validation**: Unit tests cover deduplication, already-adopted filtering, skill-context chains.
  - **TDD Test Cases (write these first):**
    - TC1: Select agent with `requires.contexts=[foo]`, `foo` not adopted → one RequiredDep(foo, already_adopted=False)
    - TC2: Select agent with `requires.contexts=[foo]`, `foo` already in beacon.yaml → one RequiredDep(foo, already_adopted=True)
    - TC3: Select two agents both requiring `foo` → one RequiredDep for `foo` (deduplicated)
    - TC4: Select agent requiring skill `bar` which itself requires context `baz` → two RequiredDeps (bar, baz)
    - TC5: Select a context (no frontmatter deps) → empty list
<!-- opsx:tdd:7.4:end -->
- [ ] 7.5 Add a dependency-confirmation prompt to the TUI flow after initial selection
<!-- opsx:tdd:7.5:begin -->
  - **Input**: TUI run with a selection that triggers at least one RequiredDep with `already_adopted=False`.
  - **Expected Output**: After user confirms initial selection, TUI shows a prompt listing the transitive deps with a yes/no; accepting adds them to the adoption set.
  - **Validation**: Non-interactive TUI harness: simulate selection → confirm → dep-prompt-accept; assert final adoption set includes transitive deps.
<!-- opsx:tdd:7.5:end -->
- [ ] 7.6 On user confirmation, append required contexts/skills to the adoption set
- [ ] 7.7 On user decline, print the warning from the spec ("agent X will fail sync until Y is adopted")
<!-- opsx:tdd:7.7:begin -->
  - **Input**: TUI run where user declines the dependency prompt.
  - **Expected Output**: Adoption of the primary agent proceeds; stderr or a loguru WARNING record contains the exact message format 'agent X will fail sync until Y is adopted' (or close variant per spec).
  - **Validation**: Assert captured warning text matches spec requirement.
<!-- opsx:tdd:7.7:end -->
- [ ] 7.8 Unit tests: adopt with no deps, adopt with all deps already in beacon.yaml, adopt with unadopted deps confirmed, adopt with unadopted deps declined
<!-- opsx:tdd:7.8:begin -->
  - **Input**: Fixture manifests + fixture warehouses for each scenario.
  - **Expected Output**: All four scenarios pass; beacon.yaml final state matches expected for each.
  - **Validation**: `uv run pytest libs/beacon/tests/unit/domains/adoption/ -v` → pass.
<!-- opsx:tdd:7.8:end -->
- [ ] 7.9 Integration test: run the TUI in a non-interactive harness, verify dependency set is correctly reported
<!-- opsx:tdd:7.9:begin -->
  - **Input**: Real Textual TUI driven via its test pilot in non-interactive mode; fixture warehouse with known dependency graph.
  - **Expected Output**: Simulated keystrokes (select, confirm, accept deps) produce the expected final adoption set.
  - **Validation**: `uv run pytest libs/beacon/tests/integration/adoption/ -v -k tui` → pass.
<!-- opsx:tdd:7.9:end -->

## 8. Distribution / sync orchestrator changes

<!-- opsx:phase-summary:8:begin -->
**Goal**: Make `abc sync` a two-phase operation: dependency resolution (plan) first, then file operations (execute), with orphan pruning and migration-doc-linked errors.
**Input**: Existing `run_sync()` in `libs/beacon/src/beacon/domains/distribution/orchestrator.py` that does per-list glob expansion and symlink creation with simple orphan pruning.
**Output**: Sync halts pre-file-operations on any dependency failure; single expansion over `EffectiveSet`; knowledge symlinks pruned on orphaning; empty parent directories cleaned up; every error carries the migration-doc URL.
**Validation**: Integration test against a fixture warehouse exercising agents, skills (explicit + transitive), contexts (explicit + transitive), and knowledge (derived); post-sync tree matches expected symlink set exactly; running sync twice produces an idempotent tree; provoked missing-dep error contains the migration-doc path.
<!-- opsx:phase-summary:8:end -->


- [ ] 8.1 Insert dependency-resolution step at the top of `run_sync()` before any file operations
<!-- opsx:tdd:8.1:begin -->
  - **Input**: Existing `run_sync()` in `libs/beacon/src/beacon/domains/distribution/orchestrator.py`.
  - **Expected Output**: First operation in `run_sync()` is `compute_effective_set()`; no file I/O occurs before it completes successfully.
  - **Validation**: Mock the file-operations step; assert it is NOT called when resolver returns a failure. Static inspection + behavioural test.
<!-- opsx:tdd:8.1:end -->
- [ ] 8.2 Exit with structured error (non-zero, loguru at ERROR level) if dependency resolution returns failures
<!-- opsx:tdd:8.2:begin -->
  - **Input**: Manifest with an unresolvable dep; run `abc sync`.
  - **Expected Output**: Process exits non-zero; one loguru ERROR record emitted containing the migration-doc URL and the referrer/target names.
  - **Validation**: CliRunner or subprocess harness: `exit_code != 0`; `assert 'docs/migrations/artifact-dependencies-frontmatter.md' in captured_stderr`.
<!-- opsx:tdd:8.2:end -->
- [ ] 8.3 Replace the three separate list expansions with a single expansion over the `EffectiveSet`
- [ ] 8.4 Run the knowledge scanner as part of computing the effective set; collect derived knowledge paths
- [ ] 8.5 Create symlinks for the effective set (agents + contexts + skills + derived knowledge)
<!-- opsx:tdd:8.5:begin -->
  - **Input**: A fixture warehouse with known effective set; a fresh empty project directory.
  - **Expected Output**: After sync, `.agentic-beacon/artifacts/<type>/...` contains one symlink per path in the effective set. Every symlink's target is an absolute path into the warehouse clone.
  - **Validation**: Walk the artifacts tree; compare symlink set to effective set; assert every target file exists at the pointed-to location.
<!-- opsx:tdd:8.5:end -->
- [ ] 8.6 Prune orphaned knowledge symlinks: compare existing symlinks under `.agentic-beacon/artifacts/knowledge/` against the derived set; remove mismatches
<!-- opsx:tdd:8.6:begin -->
  - **Input**: Project with pre-existing knowledge symlinks; new sync where derived set has shrunk.
  - **Expected Output**: Orphaned symlinks are removed; derived-set symlinks are preserved.
  - **Validation**: Before: N symlinks; unadopt last referrer of K of them; after sync: N−K symlinks remaining.
  - **TDD Test Cases (write these first):**
    - TC1: Remove last referrer of one knowledge file → that one symlink removed, others preserved
    - TC2: Remove referrers of all knowledge files → every knowledge symlink removed
    - TC3: No referrers removed → no pruning occurs; all symlinks preserved
    - TC4: Add a new referrer of a previously-derived knowledge file → no pruning; symlink preserved
    - TC5: Add a referrer to a brand-new knowledge file → new symlink created, no others pruned
<!-- opsx:tdd:8.6:end -->
- [ ] 8.7 Prune empty parent directories after knowledge pruning
<!-- opsx:tdd:8.7:begin -->
  - **Input**: A knowledge tree like `.agentic-beacon/artifacts/knowledge/python-standards/lessons/` containing one symlink.
  - **Expected Output**: After pruning the last symlink, both `lessons/` and `python-standards/` directories are removed; the top-level `knowledge/` directory is also removed if it becomes empty.
  - **Validation**: Walk the tree post-sync; assert directories with zero children do not exist.
<!-- opsx:tdd:8.7:end -->
- [ ] 8.8 Prune transitively-pulled contexts and skills when they drop out of the effective set
<!-- opsx:tdd:8.8:begin -->
  - **Input**: Fixture: agent A requires context C (C not explicitly adopted). Unadopt A.
  - **Expected Output**: Next sync removes the `contexts/C.md` symlink because it was only transitively pulled.
  - **Validation**: Symlink removed post-sync; `beacon.yaml.contexts` never contained C (still doesn't after unadoption).
  - **TDD Test Cases (write these first):**
    - TC1: Explicit context survives referrer unadoption → still present
    - TC2: Transitive-only context → removed on sync
    - TC3: Transitive context that becomes explicitly adopted mid-cycle → promoted; survives future referrer unadoption
    - TC4: Two transitive referrers, unadopt one → context preserved
    - TC5: Two transitive referrers, unadopt both → context pruned
<!-- opsx:tdd:8.8:end -->
- [ ] 8.9 Ensure every error message includes a URL to `docs/migrations/artifact-dependencies-frontmatter.md`
<!-- opsx:tdd:8.9:begin -->
  - **Input**: All error-path tests in tasks 8.2 and 4.x.
  - **Expected Output**: Every captured error record or stderr blob contains the substring `docs/migrations/artifact-dependencies-frontmatter.md`.
  - **Validation**: Grep-style assertions across the error-path test suite: zero failures would pass without this substring present.
<!-- opsx:tdd:8.9:end -->
- [ ] 8.10 Integration test: full sync against a fixture warehouse exercising all three tiers; verify correct symlinks and no orphans
<!-- opsx:tdd:8.10:begin -->
  - **Input**: Comprehensive fixture warehouse with agents (explicit adoption), skills (explicit + transitive), contexts (explicit + transitive), knowledge (derived-only).
  - **Expected Output**: Post-sync tree exactly matches the hand-computed expected tree; second sync is a no-op.
  - **Validation**: `uv run pytest libs/beacon/tests/integration/distribution/test_full_sync.py -v` → pass; artifact tree diff against golden snapshot is empty.
<!-- opsx:tdd:8.10:end -->

## 9. Sample warehouse and examples

<!-- opsx:phase-summary:9:begin -->
**Goal**: Ensure `abc warehouse init` produces a warehouse that already conforms to the new contract so new users never hit the migration error.
**Input**: `examples/sample-warehouse/` and any scaffold templates under `libs/beacon/src/beacon/data/`.
**Output**: Every scaffolded agent and skill carries `requires:` frontmatter; no `knowledge:` list appears in the scaffolded `beacon.yaml` template.
**Validation**: `abc warehouse init test-warehouse` in a temp dir produces a tree that passes `abc warehouse validate` (or the in-CLI equivalent) without frontmatter errors.
<!-- opsx:phase-summary:9:end -->


- [ ] 9.1 Add `requires:` frontmatter to every agent under `examples/sample-warehouse/agents/`
<!-- opsx:tdd:9.1:begin -->
  - **Input**: Every file under `examples/sample-warehouse/agents/`.
  - **Expected Output**: Each file parses as `AgentFrontmatter` without errors; each `requires.contexts` and `requires.skills` resolves to a sample-warehouse file.
  - **Validation**: `for f in examples/sample-warehouse/agents/*.md; do uv run python -m beacon.core.dependencies.parse_frontmatter "$f"; done` exits 0 for every file.
<!-- opsx:tdd:9.1:end -->
- [ ] 9.2 Add `requires:` frontmatter to every skill under `examples/sample-warehouse/skills/`
<!-- opsx:tdd:9.2:begin -->
  - **Input**: Every `SKILL.md` under `examples/sample-warehouse/skills/`.
  - **Expected Output**: Each parses as `SkillFrontmatter`; no forbidden `skills:` key present.
  - **Validation**: Same as 9.1 using `SkillFrontmatter`.
<!-- opsx:tdd:9.2:end -->
- [ ] 9.3 Remove any `knowledge: [...]` entries from the sample `beacon.yaml` template
<!-- opsx:tdd:9.3:begin -->
  - **Input**: Sample `beacon.yaml` template file (location per scaffold).
  - **Expected Output**: Template does not contain `knowledge:` key under `artifacts:`.
  - **Validation**: `rg -n '^\s*knowledge:' examples/ libs/beacon/src/beacon/data/` returns zero matches.
<!-- opsx:tdd:9.3:end -->
- [ ] 9.4 Update `libs/beacon/src/beacon/data/` templates (warehouse scaffolding) to match
- [ ] 9.5 Verify `abc warehouse init test-warehouse` still produces a valid, migrated warehouse
<!-- opsx:tdd:9.5:begin -->
  - **Input**: Fresh temp directory; run `abc warehouse init test-warehouse`.
  - **Expected Output**: Scaffolded warehouse has `requires:` frontmatter on every agent and skill; `beacon.yaml` has no `knowledge:` key; `abc warehouse validate` (or equivalent) passes.
  - **Validation**: Integration test runs the init command and asserts the resulting tree.
<!-- opsx:tdd:9.5:end -->

## 10. CLI-level tests and verification

<!-- opsx:phase-summary:10:begin -->
**Goal**: Prove end-to-end that adoption, sync, unadoption-prune, legacy migration, and error-surface flows work under realistic conditions.
**Input**: Completed Phases 1–9; working `abc` CLI from the virtual env; access to the personal warehouse for the happy-path manual test.
**Output**: Green end-to-end test matrix; manual happy-path verified against real `contexts/python-standards` with its 12+ referenced knowledge files.
**Validation**: `uv run pytest` passes at the repo root; manual test shows 12+ knowledge symlinks appearing after adoption, and all of them vanishing after the referencing context is unadopted and synced.
<!-- opsx:phase-summary:10:end -->


- [ ] 10.1 End-to-end test: `abc warehouse init` → `abc adopt` → `abc sync` against a fresh warehouse, verify derived knowledge symlinks appear and unadopted knowledge is not created
<!-- opsx:tdd:10.1:begin -->
  - **Input**: Fresh temp project; scaffolded warehouse from 9.5; scripted adoption selecting one context that references two knowledge files.
  - **Expected Output**: Post-sync: two knowledge symlinks present under `.agentic-beacon/artifacts/knowledge/`; no additional knowledge symlinks appear for unadopted contexts.
  - **Validation**: Integration test compares `find .agentic-beacon/artifacts/knowledge -type l` to expected set.
<!-- opsx:tdd:10.1:end -->
- [ ] 10.2 End-to-end test: unadopt the last referrer of a knowledge file, run sync, verify symlink is pruned
<!-- opsx:tdd:10.2:begin -->
  - **Input**: State from 10.1. Edit `beacon.yaml` to remove the context. Run `abc sync`.
  - **Expected Output**: Both knowledge symlinks are gone; the knowledge directory tree is fully pruned.
  - **Validation**: Post-sync: `.agentic-beacon/artifacts/knowledge/` does not exist, or exists and is empty.
<!-- opsx:tdd:10.2:end -->
- [ ] 10.3 End-to-end test: upgrade path — start with a `beacon.yaml` containing `knowledge:` list, run sync, verify silent drop log and correct final state
<!-- opsx:tdd:10.3:begin -->
  - **Input**: Hand-crafted legacy `beacon.yaml` with `artifacts.knowledge: [knowledge/python-standards]` and at least one adopted context.
  - **Expected Output**: Post-sync: `beacon.yaml` rewritten without `knowledge:` key; one loguru INFO record emitted about the migration; knowledge symlinks reflect the derived set (which may or may not include the formerly-pinned knowledge, depending on whether any adopted artifact references it).
  - **Validation**: Assert file diff shows `knowledge:` removed; capture exactly one INFO record; assert final artifact tree matches spec.
<!-- opsx:tdd:10.3:end -->
- [ ] 10.4 End-to-end test: adopted agent with unadopted dependency produces non-zero exit with migration-doc URL in stderr
<!-- opsx:tdd:10.4:begin -->
  - **Input**: Hand-crafted `beacon.yaml` where an agent is adopted but its `requires.contexts` is not.
  - **Expected Output**: `abc sync` exits non-zero; stderr contains the agent name, the missing context name, and the migration-doc URL.
  - **Validation**: Subprocess runner: `exit_code != 0`; assertions on captured stderr.
<!-- opsx:tdd:10.4:end -->
- [ ] 10.5 Run full pytest suite and ensure all existing tests still pass
<!-- opsx:tdd:10.5:begin -->
  - **Input**: Clean checkout of the feature branch post-implementation.
  - **Expected Output**: `uv run pytest` at repo root returns exit code 0 with no skipped tests unrelated to platform.
  - **Validation**: CI equivalent: `uv sync --group dev && uv run pytest`.
<!-- opsx:tdd:10.5:end -->
- [ ] 10.6 **[MANUAL]** Happy-path manual test in this repo: re-adopt `contexts/python-standards` through new flow, verify the 12+ knowledge files it references appear as symlinks under `.agentic-beacon/artifacts/knowledge/`
<!-- opsx:tdd:10.6:begin -->
  - **Input**: This very repo (`~/Code/oss/agentic-beacon`) with its current `beacon.yaml` (`knowledge: []`, contexts includes `python-standards`).
  - **Expected Output**: After running `abc sync` on the new CLI, `.agentic-beacon/artifacts/knowledge/python-standards/` contains the 12+ knowledge symlinks referenced by `python-standards.md`, and (if any cross-pack refs exist) `knowledge/cicd/` is also populated accordingly.
  - **Validation**: `find .agentic-beacon/artifacts/knowledge -type l | wc -l` returns ≥12; every file referenced by grep output of line 23, 34, 62, 77, 102, 118, 126, 134, 142, 164, 174, 193 in `python-standards.md` exists as a valid symlink.
<!-- opsx:tdd:10.6:end -->

## 11. Documentation and release

<!-- opsx:phase-summary:11:begin -->
**Goal**: Update user-facing and contributor-facing docs to match the new model, then ship via the existing Release-Please workflow.
**Input**: Existing `guides/`, `AGENTS.md`, `README.md`, `docs/agentic-warehouse-design.md`, and the Release-Please GitHub workflow.
**Output**: Every doc location that references knowledge adoption reflects the new derived model; CHANGELOG entry describes the breaking changes; all commits follow conventional-commit format for clean version bumping.
**Validation**: `rg -i 'adopt.*knowledge|knowledge.*adopt' docs/ guides/ README.md AGENTS.md` returns only descriptions of the removal / transition; Release-Please preview branch shows expected version bump.
<!-- opsx:phase-summary:11:end -->


- [ ] 11.1 Update `guides/` to reflect the new adoption model (no more knowledge selection)
- [ ] 11.2 Update `AGENTS.md` and `README.md` sections that mention knowledge adoption
- [ ] 11.3 Update `docs/agentic-warehouse-design.md` sections that describe knowledge as an independently-adoptable artifact
- [ ] 11.4 Add a CHANGELOG entry documenting the breaking changes
- [ ] 11.5 **[MANUAL]** Verify conventional commits throughout the PR for Release-Please version bump
<!-- opsx:tdd:11.5:begin -->
  - **Input**: `git log --oneline <base>..HEAD` on the feature branch.
  - **Expected Output**: Every subject line matches the conventional-commit format `<type>(<scope>)?: <description>`, with at least one `feat!:` or `fix!:` recording the breaking change.
  - **Validation**: `git log --format=%s <base>..HEAD | grep -vE '^(feat|fix|chore|refactor|docs|test|build|ci)(\(.+\))?!?: ' | wc -l` returns 0.
<!-- opsx:tdd:11.5:end -->
- [ ] 11.6 **[MANUAL]** Mark the change complete; prepare for `/opsx-archive` post-merge

<!-- opsx:metadata:begin -->
---

## Enhancement Metadata

**Enhanced**: 2026-05-04
**Methodology**: Spec-Driven Development + TDD
**Enhancements Applied**:
- TDD Workflow Header
- Repositories & Branches table
- Phase summaries (Goal/Input/Output/Validation)
- Task-level TDD criteria on 56 task(s)
- 116 test case(s) across complex tasks
- 9 task(s) flagged [MANUAL]

**Status**: Ready for implementation via `/opsx-apply <name>`.
<!-- opsx:metadata:end -->
