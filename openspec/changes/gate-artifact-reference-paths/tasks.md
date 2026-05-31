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
| `agentic-beacon` | `~/Code/oss/agentic-beacon` | `gate-artifact-reference-paths` | Code changes — scanner resolver/classifier/slugifier, lint link-integrity rule + --fix, partial-distribution surgery, contribute-skill gate, unit + integration tests, docs, release |
| `hl-knowledge-market` | `~/Code/knowledge/hl-knowledge-market` | `gate-artifact-reference-paths` | Operational only — one-time warehouse migration (move agents/_partials/ → agent-partials/, run lint --fix, hand-fix escapes); existing lint.yml enforces after release |
<!-- opsx:repos-table:end -->

## 1. Resolver, classifier, slugifier (core/scanner)

<!-- opsx:phase-summary:1:begin -->
**Goal**: Build the path/anchor primitives that every downstream consumer (lint, --fix, integration test) relies on: canonical resolution, the four-way link classifier, and a GitHub-exact heading slugifier.
**Input**: Existing core/scanner/scanner.py with directory-relative resolve_link + knowledge classifier; design.md §D1–D3.
**Output**: slugify_heading(), resolve_canonical_link(), classify_link() (5 categories), to_canonical(), plus a covering unit-test suite.
**Validation**: pytest tests/unit on the new scanner functions passes; slugifier table matches GitHub output for real warehouse anchors.
<!-- opsx:phase-summary:1:end -->


- [ ] 1.1 Add `slugify_heading()` (GitHub-exact: lowercase, strip non-alnum/space/hyphen, spaces→hyphen, preserve punctuation double-hyphens, dedup `-1/-2`) and a heading-extractor for a markdown file
<!-- opsx:tdd:1.1:begin -->
  - **Input**: pytest tests/unit/test_scanner_slugify.py -v
  - **Expected Output**: All slugify cases pass; slugs match GitHub for ASCII, emoji, em-dash, and duplicate-heading inputs
  - **Validation**: Zero failed tests; dedup counter resets per file; extractor returns headings in document order
  - **TDD Test Cases (write these first):**
    - TC1: `## Setup` → slug `setup`
    - TC2: `## ✨ ClickhouseS3Ingestor — DLT ingestion design` → slug `-clickhouses3ingestor--dlt-ingestion-design`
    - TC3: two `## Setup` headings → `setup`, then `setup-1`
    - TC4: `## Multi-Repository Workspace - CRITICAL` → `multi-repository-workspace---critical`
    - TC5: heading with trailing/leading whitespace → trimmed before slugify
    - TC6: heading with inline code `## Use `foo()`` → backticks stripped, slug `use-foo`
    - TC7: non-heading lines and fenced ``` blocks → not extracted as headings
<!-- opsx:tdd:1.1:end -->
- [ ] 1.2 Add `CANONICAL_PREFIX = ".agentic-beacon/artifacts/"` and `resolve_canonical_link()` (strip prefix → warehouse-root path; optional anchor)
<!-- opsx:tdd:1.2:begin -->
  - **Input**: pytest tests/unit/test_scanner_resolve.py -v
  - **Expected Output**: Canonical links resolve to <warehouse>/<rel>; anchor split out; non-canonical input returns None/unresolved
  - **Validation**: Existing target → resolved path; missing target → resolvable path but exists()==False; anchor preserved separately
  - **TDD Test Cases (write these first):**
    - TC1: `.agentic-beacon/artifacts/contexts/cicd-flow.md` → `<wh>/contexts/cicd-flow.md`
    - TC2: `.agentic-beacon/artifacts/contexts/cicd-flow.md#section` → path + anchor `section`
    - TC3: target missing in warehouse → returns path, caller sees exists()==False
    - TC4: input without the canonical prefix → not treated as canonical
    - TC5: URL-encoded anchor (`#%EF%B8%8F-...`) → decoded before comparison
<!-- opsx:tdd:1.2:end -->
- [ ] 1.3 Add `classify_link()` returning one of: absolute-url / canonical / own-skill-folder / cross-artifact-relative / warehouse-escape (own-folder applies only to skills)
<!-- opsx:tdd:1.3:begin -->
  - **Input**: pytest tests/unit/test_scanner_classify.py -v
  - **Expected Output**: Each link classified into exactly one of the five categories given the linking file path + warehouse root
  - **Validation**: Own-folder only fires for skills/<name>/ subtrees; agents/contexts/knowledge never own-folder
  - **TDD Test Cases (write these first):**
    - TC1: `https://x.com` from any file → absolute-url
    - TC2: `mailto:a@b.com` → absolute-url
    - TC3: `.agentic-beacon/artifacts/contexts/a.md` → canonical
    - TC4: `references/api.md` from skills/foo/SKILL.md (file exists) → own-skill-folder
    - TC5: `../../contexts/bar.md` from skills/foo/SKILL.md → cross-artifact-relative
    - TC6: `_partials/x.md` from agents/sup.md → cross-artifact-relative (agents are not directory artifacts)
    - TC7: `../../../apps/backtest/docs/schema.md` resolving outside warehouse → warehouse-escape
    - TC8: `references/api.md` from contexts/foo.md → cross-artifact-relative (own-folder is skills-only)
<!-- opsx:tdd:1.3:end -->
- [ ] 1.4 Add `to_canonical()` helper: given a cross-artifact relative link + linking file, compute the canonical form (preserve anchor) — shared by lint and `--fix`
<!-- opsx:tdd:1.4:begin -->
  - **Input**: pytest tests/unit/test_scanner_to_canonical.py -v
  - **Expected Output**: Cross-artifact relative link rewritten to `.agentic-beacon/artifacts/<warehouse-rel>` with anchor preserved
  - **Validation**: Output round-trips: classify_link(to_canonical(x)) == canonical and resolves to the same file
  - **TDD Test Cases (write these first):**
    - TC1: `../../contexts/bar.md` from skills/foo/SKILL.md → `.agentic-beacon/artifacts/contexts/bar.md`
    - TC2: `../../contexts/bar.md#multi-repo` → `.agentic-beacon/artifacts/contexts/bar.md#multi-repo`
    - TC3: `_partials/deep-review-checklist.md` from agents/sup.md → `.agentic-beacon/artifacts/agents/_partials/deep-review-checklist.md` (pre-move) round-trips
    - TC4: idempotency — passing an already-canonical link is a no-op
<!-- opsx:tdd:1.4:end -->
- [ ] 1.5 Unit tests: slugifier table seeded from real warehouse anchors (emoji, `---`, dup headings); classifier table covering all five categories; resolver happy/missing/anchor cases
<!-- opsx:tdd:1.5:begin -->
  - **Input**: pytest tests/unit -k 'scanner' -v
  - **Expected Output**: All scanner unit tests pass with real-anchor-seeded slugifier table
  - **Validation**: Zero failed tests; coverage includes all five classifier categories and emoji/dup-heading slugs
<!-- opsx:tdd:1.5:end -->

## 2. Lint link-integrity rule (domains/warehouse/lint.py)

<!-- opsx:phase-summary:2:begin -->
**Goal**: Broaden the lint from knowledge-only link checking to full artifact-link integrity using the Phase 1 primitives, emitting distinct error findings per failure category.
**Input**: Phase 1 primitives; existing lint_warehouse() with _lint_knowledge_links rule 6.
**Output**: _lint_artifact_links replacing _lint_knowledge_links; distinct finding messages for malformed/missing/anchor/escape; same-file anchor checks; scan_file_for_knowledge untouched.
**Validation**: pytest tests/unit lint tests assert each finding type, clean-pass, and exit codes; abc sync behaviour unchanged.
<!-- opsx:phase-summary:2:end -->


- [ ] 2.1 Replace `_lint_knowledge_links` with `_lint_artifact_links` scanning `contexts/*.md`, `skills/*/SKILL.md`, `agents/*.md`, `knowledge/**/*.md`
<!-- opsx:tdd:2.1:begin -->
  - **Input**: pytest tests/unit/test_lint.py -k artifact_links -v
  - **Expected Output**: All four artifact families scanned; findings sorted stably by (artifact_path, message)
  - **Validation**: Each family contributes findings; ordering deterministic cross-platform
<!-- opsx:tdd:2.1:end -->
- [ ] 2.2 Emit distinct error findings: malformed-cross-artifact, missing-target, unresolved-anchor, warehouse-escape; allow own-folder + absolute-url
<!-- opsx:tdd:2.2:begin -->
  - **Input**: pytest tests/unit/test_lint.py -k findings -v
  - **Expected Output**: One LintFinding per defect with a category-specific message scoped to the artifact path
  - **Validation**: Own-folder and absolute-url produce no finding; each error category produces its distinct message
  - **TDD Test Cases (write these first):**
    - TC1: cross-artifact relative link → malformed-link error scoped to source file, exit 1
    - TC2: canonical link to missing target → missing-target error, exit 1
    - TC3: canonical link with bad anchor → unresolved-anchor error, exit 1
    - TC4: relative link escaping warehouse → warehouse-escape error, exit 1
    - TC5: own-folder asset link in a skill → no finding
    - TC6: absolute URL → no finding
    - TC7: valid canonical link with valid anchor → no finding
<!-- opsx:tdd:2.2:end -->
- [ ] 2.3 Validate same-file bare anchors (`#section`) against the file's own headings
<!-- opsx:tdd:2.3:begin -->
  - **Input**: pytest tests/unit/test_lint.py -k same_file_anchor -v
  - **Expected Output**: Bare `#slug` resolves against the linking file's own headings
  - **Validation**: Matching heading → no finding; non-matching → unresolved-anchor error
  - **TDD Test Cases (write these first):**
    - TC1: `#existing-heading` present in same file → no finding
    - TC2: `#missing-heading` absent in same file → unresolved-anchor error
    - TC3: `#setup-1` resolves to the second duplicate `## Setup`
<!-- opsx:tdd:2.3:end -->
- [ ] 2.4 Keep `scan_file_for_knowledge` untouched (sync stays warning-only)
<!-- opsx:tdd:2.4:begin -->
  - **Input**: pytest tests/unit -k 'scan_file_for_knowledge or sync_warning' -v
  - **Expected Output**: scan_file_for_knowledge signature/behaviour unchanged; abc sync logs warning and exits 0 on a broken link
  - **Validation**: No regression in the warning-only sync path; lint errors do not leak into sync
  - **Note**: Guard task: the lint-side error promotion must NOT modify scan_file_for_knowledge — verify by diff and by the sync-unchanged scenario.
<!-- opsx:tdd:2.4:end -->
- [ ] 2.5 Unit tests: fixture warehouses asserting each finding type + clean-pass + exit codes
<!-- opsx:tdd:2.5:begin -->
  - **Input**: pytest tests/unit/test_lint.py -v
  - **Expected Output**: All lint finding-type tests pass; clean warehouse exits 0; any defect exits 1
  - **Validation**: Zero failed tests; exit-code scenarios covered
<!-- opsx:tdd:2.5:end -->

## 3. `lint --fix` autofix (cli/warehouse.py + lint.py)

<!-- opsx:phase-summary:3:begin -->
**Goal**: Add the in-place auto-migration that rewrites fixable cross-artifact links to canonical form, leaving warehouse-escape links as errors for a human.
**Input**: Phase 1 to_canonical(); Phase 2 classifier-backed lint; existing cli/warehouse.py lint handler.
**Output**: --fix flag (read-only by default), deterministic idempotent rewriter, rewritten-count reporting, escape links still erroring.
**Validation**: pytest tests/unit fix tests: rewrites fixable, leaves escape, idempotent second run, read-only without --fix.
<!-- opsx:phase-summary:3:end -->


- [ ] 3.1 Add `--fix` flag to `abc warehouse lint`; default remains read-only
- [ ] 3.2 Implement in-place rewrite of cross-artifact-relative links via `to_canonical()`, preserving anchors; never touch own-folder/absolute/canonical/warehouse-escape links
<!-- opsx:tdd:3.2:begin -->
  - **Input**: pytest tests/unit/test_lint_fix.py -k rewrite -v
  - **Expected Output**: Only cross-artifact-relative links rewritten in place; anchors preserved; other categories untouched byte-for-byte
  - **Validation**: File content outside matched links unchanged; rewritten links classify as canonical
  - **TDD Test Cases (write these first):**
    - TC1: `[ctx](../../contexts/bar.md#multi-repo)` → `[ctx](.agentic-beacon/artifacts/contexts/bar.md#multi-repo)`
    - TC2: own-folder `[api](references/api.md)` → unchanged
    - TC3: absolute URL → unchanged
    - TC4: already-canonical link → unchanged
    - TC5: warehouse-escape link → unchanged (not rewritten)
    - TC6: multiple links on one line → each rewritten independently, surrounding prose intact
<!-- opsx:tdd:3.2:end -->
- [ ] 3.3 Report rewritten-count + files touched; warehouse-escape links remain errors (exit 1)
<!-- opsx:tdd:3.3:begin -->
  - **Input**: abc warehouse lint --fix <fixture-warehouse>
  - **Expected Output**: Summary lists N rewritten links across M files; remaining warehouse-escape errors printed; exit 1 if any error remains, else 0
  - **Validation**: Exit code reflects residual errors; counts match actual file edits
<!-- opsx:tdd:3.3:end -->
- [ ] 3.4 Unit tests: fix rewrites fixable link, leaves escape link, idempotency (second run no-ops), read-only without `--fix`
<!-- opsx:tdd:3.4:begin -->
  - **Input**: pytest tests/unit/test_lint_fix.py -v
  - **Expected Output**: All fix tests pass including idempotency and read-only guarantees
  - **Validation**: Second --fix run produces byte-identical file; no --fix run modifies nothing
  - **TDD Test Cases (write these first):**
    - TC1: run --fix once → fixable links rewritten; run again → byte-identical (idempotent)
    - TC2: warehouse-escape link present → not rewritten, exit 1
    - TC3: lint without --fix on fixable warehouse → no file modified, errors reported
    - TC4: --fix on already-clean warehouse → no edits, exit 0
<!-- opsx:tdd:3.4:end -->

## 4. Agent partials restructure (absorbs PER-238)

<!-- opsx:phase-summary:4:begin -->
**Goal**: Move partials out of the agents/ tree, keep distributing them into the .agentic-beacon/artifacts/agent-partials/ mirror, stop wiring them into tool dirs, and remove the disable:true stopgap.
**Input**: design.md §D7; orchestrator.py partial glob, distributor.py is_partial_path, delta.py stale handling, setup/wiring.py stopgap.
**Output**: Retargeted glob agent-partials/**, updated is_partial_path + delta prune, removed co-distribution + stopgap wrapper, stale tool-dir partials pruned.
**Validation**: pytest tests/unit: partial in mirror, absent from tool dirs, stale pruned, no-op without declared agents.
<!-- opsx:phase-summary:4:end -->


- [ ] 4.1 Retarget partial dependency glob `agents/_partials/**` → `agent-partials/**` in `orchestrator.py` (still gated on ≥1 declared agent)
<!-- opsx:tdd:4.1:begin -->
  - **Input**: pytest tests/unit -k 'orchestrator and partial' -v
  - **Expected Output**: Partials pulled from agent-partials/** only when ≥1 agent declared; mirrored to .agentic-beacon/artifacts/agent-partials/**
  - **Validation**: No agents declared → no partials pulled; agents declared → agent-partials/ files in artifact_paths
<!-- opsx:tdd:4.1:end -->
- [ ] 4.2 Update `is_partial_path()` in `distributor.py` and stale-partial handling in `delta.py` for the new `agent-partials/` location
<!-- opsx:tdd:4.2:begin -->
  - **Input**: pytest tests/unit -k 'is_partial_path or delta' -v
  - **Expected Output**: is_partial_path matches agent-partials/ paths; delta prunes stale agent-partials and legacy _partials symlinks
  - **Validation**: Both warehouse-relative and artifacts-relative inputs classified correctly; stale legacy partials detected for prune
  - **TDD Test Cases (write these first):**
    - TC1: `agent-partials/deep-review-checklist.md` → is_partial_path True
    - TC2: `agents/spec-planner.md` → is_partial_path False
    - TC3: legacy `agents/_partials/x.md` → recognized as stale for prune
    - TC4: nested `agent-partials/sub/x.md` → is_partial_path True
<!-- opsx:tdd:4.2:end -->
- [ ] 4.3 Remove partial co-distribution + `disable: true` stopgap wrapper in `setup/wiring.py`; prune stale Beacon-owned tool-dir partials on sync
<!-- opsx:tdd:4.3:begin -->
  - **Input**: pytest tests/unit -k 'wiring and partial' -v
  - **Expected Output**: No partial wrapper emitted into .claude/.opencode; Beacon-owned stale tool-dir partials pruned; user-owned files preserved
  - **Validation**: Wrapper-builder removed; prune only targets Beacon-owned symlinks/wrappers
  - **TDD Test Cases (write these first):**
    - TC1: sync with declared agent → no file/symlink under .opencode/agents/_partials or .claude/agents/_partials
    - TC2: pre-existing Beacon-owned .opencode/agents/_partials/deep-review-checklist.md → pruned, not recreated
    - TC3: user-created file at the partial path → preserved with warning
    - TC4: disable:true wrapper builder no longer invoked anywhere
<!-- opsx:tdd:4.3:end -->
- [ ] 4.4 Unit tests: partial materialized at `.agentic-beacon/artifacts/agent-partials/`, absent from `.claude/`/`.opencode/`, stale tool-dir partial pruned, no-op when no agents declared
<!-- opsx:tdd:4.4:begin -->
  - **Input**: pytest tests/unit -k 'partial' -v
  - **Expected Output**: All partial-restructure unit tests pass
  - **Validation**: Mirror-present, tool-dir-absent, stale-pruned, and no-agents-no-op all asserted
<!-- opsx:tdd:4.4:end -->

## 5. Contribute-warehouse skill gate

<!-- opsx:phase-summary:5:begin -->
**Goal**: Gate warehouse contributions on a clean lint run inside the contribute-warehouse bundled skill.
**Input**: Phase 2/3 lint + --fix; data/skills/contribute-warehouse/SKILL.md.
**Output**: Pre-commit lint step in the skill that blocks on error findings and suggests --fix.
**Validation**: End-to-end run against a dirty fixture warehouse: skill blocks on a planted bad link and proceeds once clean.
<!-- opsx:phase-summary:5:end -->


- [ ] 5.1 Add a pre-commit step to `data/skills/contribute-warehouse/SKILL.md`: run `abc warehouse lint`, block on error findings, suggest `--fix`
- [ ] 5.2 Verify the gate flow end-to-end against a dirty fixture warehouse
<!-- opsx:tdd:5.2:begin -->
  - **Input**: Follow the contribute-warehouse skill against a fixture warehouse containing one planted cross-artifact-relative link, then re-run after `abc warehouse lint --fix`
  - **Expected Output**: First run blocks at the lint gate citing the malformed link; after --fix the gate passes and contribute proceeds
  - **Validation**: Gate blocks on error findings, unblocks once lint is clean
<!-- opsx:tdd:5.2:end -->

## 6. Integration test (synthetic distribution)

<!-- opsx:phase-summary:6:begin -->
**Goal**: Prove end-to-end that every canonical link resolves from the project root after a real abc sync over real symlinks, and that broken links are caught.
**Input**: Phases 1–4 shipped; abc sync; tests/integration harness + conftest.
**Output**: Hermetic synthetic-fixture warehouse + tmp project, sync materialization, link-resolution walk, negative fixture, CI-marked.
**Validation**: pytest tests/integration green; negative fixture makes abc warehouse lint exit 1; runs in CI.
<!-- opsx:phase-summary:6:end -->


- [ ] 6.1 Build a synthetic fixture warehouse (context→knowledge, skill→context, skill own-folder asset, agent→partial, knowledge→knowledge) + a negative fixture with a broken link
<!-- opsx:tdd:6.1:begin -->
  - **Input**: Construct tmp warehouse dirs/files in a pytest fixture under tests/integration
  - **Expected Output**: Fixture warehouse with all canonical link kinds plus one negative-fixture broken link
  - **Validation**: Fixture builds deterministically; positive links canonical, negative link malformed
  - **Note**: Coverage mix must include: context→knowledge, skill→context, skill own-folder asset, agent→agent-partial, knowledge→knowledge.
<!-- opsx:tdd:6.1:end -->
- [ ] 6.2 Stand up tmp project, connect, declare artifacts, run real `abc sync` (real symlinks)
<!-- opsx:tdd:6.2:begin -->
  - **Input**: abc connect + beacon.yaml declaring the fixture artifacts, then abc sync against the synthetic warehouse
  - **Expected Output**: Real symlink tree under .agentic-beacon/artifacts/ plus agent symlinks under .claude/.opencode; agent-partials mirrored
  - **Validation**: Symlinks resolve to warehouse files; sync exits 0; agent-partials present in mirror, absent from tool dirs
<!-- opsx:tdd:6.2:end -->
- [ ] 6.3 Walk every distributed artifact under `.agentic-beacon/artifacts/` and the agent files in `.claude/agents/`/`.opencode/agents/`; assert each canonical link resolves as `(project_root / target).exists()` + anchor resolves
<!-- opsx:tdd:6.3:begin -->
  - **Input**: pytest tests/integration/test_link_resolution.py -v
  - **Expected Output**: Every canonical link in every distributed artifact resolves via (project_root / target).exists(); anchors match a heading slug
  - **Validation**: Zero unresolved canonical links across the synthetic distribution
  - **TDD Test Cases (write these first):**
    - TC1: skill→context canonical link → (project_root / target) exists
    - TC2: context→knowledge canonical link → exists
    - TC3: agent→agent-partial canonical link from .claude/agents/ file → exists
    - TC4: knowledge→knowledge canonical link → exists
    - TC5: canonical link with anchor → anchor matches a heading slug in the target
    - TC6: skill own-folder asset link → resolves relative to the skill dir (not flagged)
<!-- opsx:tdd:6.3:end -->
- [ ] 6.4 Assert the negative fixture is caught by `abc warehouse lint` (exit 1, correct finding)
<!-- opsx:tdd:6.4:begin -->
  - **Input**: abc warehouse lint <synthetic-warehouse-with-negative-fixture>
  - **Expected Output**: Exit code 1 with a finding scoped to the negative-fixture file naming the malformed/broken link
  - **Validation**: Lint fails closed on the planted defect; finding category matches the defect
  - **TDD Test Cases (write these first):**
    - TC1: negative fixture with cross-artifact relative link → exit 1, malformed-link finding
    - TC2: negative fixture with canonical link to missing target → exit 1, missing-target finding
    - TC3: after lint --fix on the fixable defect → exit 0
<!-- opsx:tdd:6.4:end -->
- [ ] 6.5 Mark integration test appropriately (`tests/integration/`, its own conftest) so it runs in CI

## 7. Docs

<!-- opsx:phase-summary:7:begin -->
**Goal**: Document the canonical-link convention, resolution rule, and lint/--fix/contribute-gate workflow for authors.
**Input**: Finalized behavior from Phases 1–5; CONTRIBUTING.md + authoring guide.
**Output**: Updated CONTRIBUTING.md and authoring guide sections.
**Validation**: Docs review; examples match shipped behavior; internal links resolve under the new convention.
<!-- opsx:phase-summary:7:end -->


- [ ] 7.1 Document the canonical-link convention + resolution rule in `CONTRIBUTING.md` and the authoring guide
- [ ] 7.2 Document the `abc warehouse lint` / `--fix` workflow and the contribute-time gate

## 8. Release & warehouse migration (post-merge)

<!-- opsx:phase-summary:8:begin -->
**Goal**: Release the new rules and migrate the live warehouse so its existing lint.yml gate enforces canonical links.
**Input**: Merged agentic-beacon change; release-please; hl-knowledge-market warehouse repo.
**Output**: New agentic-beacon release; migrated warehouse (partials moved, links canonicalized); PER-238 closed.
**Validation**: Warehouse lint.yml goes red on a planted bad link and green after --fix; PER-238 closed.
<!-- opsx:phase-summary:8:end -->


- [ ] 8.1 Release a new `agentic-beacon` version so the warehouse `lint.yml` enforces the new rules
- [x] 8.2 In `hl-knowledge-market` (branch `gate-artifact-reference-paths`): move `agents/_partials/` → `agent-partials/`, run `abc warehouse lint --fix`, hand-resolve warehouse-escape links, rewrite supervisor links, open PR
<!-- opsx:cross-repo-block:8.2:begin -->
  - **Target repo**: `hl-knowledge-market`
  - **Why cross-repo**: warehouse artifact migration executes in the warehouse repo, not the CLI source repo
  - **Done ref**: deferred until agentic-beacon release ships (post-merge warehouse PR; conscious deferral, not yet executed)
<!-- opsx:cross-repo-block:8.2:end -->
- [x] 8.3 Verify warehouse `lint.yml` goes red on a planted bad link and green after `--fix`; close PER-238
<!-- opsx:cross-repo-block:8.3:begin -->
  - **Target repo**: `hl-knowledge-market`
  - **Why cross-repo**: the lint.yml CI gate runs in the warehouse repo; PER-238 closure depends on that repo's migration landing
  - **Done ref**: deferred until 8.2 lands (warehouse migration PR merged + agentic-beacon release live); conscious deferral, not yet executed
<!-- opsx:cross-repo-block:8.3:end -->

<!-- opsx:metadata:begin -->
---

## Enhancement Metadata

**Enhanced**: 2026-05-31
**Methodology**: Spec-Driven Development + TDD
**Enhancements Applied**:
- TDD Workflow Header
- Repositories & Branches table
- Phase summaries (Goal/Input/Output/Validation)
- Task-level TDD criteria on 22 task(s)
- 61 test case(s) across complex tasks
- 0 task(s) flagged [HITL]
- 2 task(s) routed to Cross-Repo Follow-ups

**Status**: Ready for implementation via `/opsx-apply <name>`.
<!-- opsx:metadata:end -->
