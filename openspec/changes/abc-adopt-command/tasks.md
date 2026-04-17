# Implementation Tasks - abc-adopt-command

## Repositories & Branches

| Repo | Path | Branch | Role |
|------|------|--------|------|
| `agentic-beacon` | `~/Code/oss/agentic-beacon` | `feat/abc-adopt-command` | Code changes -- new adopt module, CLI command, sync notification, tests |

---

## TDD WORKFLOW - MANDATORY FOR ALL TASKS

**CRITICAL**: This project follows strict Test-Driven Development (TDD). Before implementing ANY task with TDD Test Cases:

### RED-GREEN-REFACTOR Cycle

1. **RED Phase - Write Failing Tests FIRST**
   - Read the task's TDD Test Cases (TC1-TCN)
   - Create test file in `tests/` directory
   - Write ALL test cases from the task BEFORE any implementation
   - Run tests - they MUST fail (import errors, missing functions, etc.)

2. **GREEN Phase - Implement Minimal Code**
   - Write ONLY enough code to make tests pass
   - Run tests after each implementation change
   - All tests must pass before marking task complete

3. **REFACTOR Phase - Improve Code Quality**
   - Clean up implementation
   - Remove duplication, improve naming
   - Tests must still pass after refactoring

### Task Completion Criteria

**A task is NOT complete until:**
- All TDD test cases are written (when specified)
- All tests pass (or are justifiably skipped with documentation)
- Implementation matches the Expected Output

### Running Tests

```bash
# From repo root
uv sync --group dev
uv run pytest libs/beacon/tests/test_adopt.py -v --tb=short
```

---

## 1. Dependencies and Module Setup

**Goal**: Set up the new dependency and module skeleton
**Input**: Existing pyproject.toml and beacon package structure
**Output**: textual installed, adopt.py with AdoptCandidate dataclass importable
**Validation**: `uv run python -c "from beacon.adopt import AdoptCandidate"` succeeds

- [x] 1.1 Add `textual>=0.80.0` to `libs/beacon/pyproject.toml` dependencies and run `uv sync --group dev`
- [x] 1.2 Create `libs/beacon/src/beacon/adopt.py` with `AdoptCandidate` dataclass (artifact_type, path, description, is_new)

## 2. Discovery Logic

**Goal**: Implement git-diff and full-scan discovery of unadopted warehouse artifacts
**Input**: Warehouse git repo path, .sync-state file, beacon.yaml with declared artifacts
**Output**: List of AdoptCandidate objects representing adoptable artifacts, plus list of updated adopted artifacts
**Validation**: `uv run pytest libs/beacon/tests/test_adopt.py -k "discover" -v` passes

- [x] 2.1 Implement `_read_sync_sha(artifacts_dir)` helper in `cli.py` that reads `.sync-state` file and returns the SHA string or None
- [x] 2.2 Implement `discover_adoptable()` in `adopt.py` -- git-diff mode: run `git diff --name-only --diff-filter=A <old_sha>..HEAD` on warehouse, filter to contexts/skills/knowledge paths, exclude paths already in beacon.yaml
  - **Input**: `discover_adoptable(warehouse_path, beacon_settings, sync_sha, show_all=False)`
  - **Expected Output**: List of `AdoptCandidate` with `is_new=True`, grouped by artifact_type
  - **Validation**: Returns only artifacts in contexts/, skills/, knowledge/ that are NOT in beacon.yaml
  - **TDD Test Cases (write these first):**
    - TC1: Warehouse has 2 new contexts since last sync, neither in beacon.yaml -> returns 2 candidates with artifact_type="contexts"
    - TC2: Warehouse has 1 new skill since last sync, already in beacon.yaml -> returns empty list
    - TC3: Warehouse has mix of new contexts and skills, some adopted -> returns only unadopted ones
    - TC4: No changes since last sync SHA -> returns empty list
    - TC5: New files outside contexts/skills/knowledge (e.g. README.md, docs/) -> filtered out, not returned
    - TC6: New skill with multiple files -> grouped into single candidate with directory path `skills/<name>/`
- [x] 2.3 Implement `discover_adoptable()` `--all` mode: scan warehouse with `WarehouseDistributor.list_available()`, cross-reference with beacon.yaml, return all unadopted
  - **TDD Test Cases (write these first):**
    - TC1: Warehouse has 5 artifacts, 2 in beacon.yaml -> returns 3 candidates with `is_new=False`
    - TC2: All warehouse artifacts in beacon.yaml -> returns empty list
    - TC3: beacon.yaml has glob patterns (e.g. `knowledge/**/*.md`) -> correctly matches expanded paths
    - TC4: Skills in beacon.yaml with trailing slash -> matches warehouse skill directories
- [x] 2.4 Implement description extraction: read SKILL.md frontmatter for skills (reuse `_extract_skill_description` pattern), first `# Heading` line for contexts/knowledge
  - **TDD Test Cases (write these first):**
    - TC1: SKILL.md with `---\ndescription: Generate tests\n---` -> returns "Generate tests"
    - TC2: Context file starting with `# Platform Standards` -> returns "Platform Standards"
    - TC3: Knowledge file starting with `# Python Async` -> returns "Python Async"
    - TC4: File with no heading and no frontmatter -> returns empty string
    - TC5: SKILL.md with `**description:** Generate tests` (markdown bold) -> returns "Generate tests"
- [x] 2.5 Implement updated-artifact detection: `git diff --name-only --diff-filter=M` for artifacts already in beacon.yaml, returned as informational list

## 3. Textual TUI App

**Goal**: Build interactive full-screen terminal app for artifact selection
**Input**: List of AdoptCandidate objects + list of updated artifact paths
**Output**: User's selection as list of artifact paths (or empty on cancel)
**Validation**: `uv run pytest libs/beacon/tests/test_adopt.py -k "tui" -v` passes using textual's `run_test()` harness

- [x] 3.1 Implement `AdoptApp` textual app in `adopt.py` with Header, VerticalScroll container, categorized Checkbox widgets per candidate, and Footer with keybindings
- [x] 3.2 Implement category grouping: group candidates by artifact_type (contexts, skills, knowledge), display Static label per category, only show categories that have candidates
- [x] 3.3 Implement keybindings: Enter (confirm and return selected), Escape/q (cancel), a (select all), n (select none)
  - **TDD Test Cases (write these first):**
    - TC1: Press `a` -> all checkboxes toggled on, query all Checkbox widgets `.value` is True
    - TC2: Press `n` -> all checkboxes toggled off
    - TC3: Press `Enter` with 2 of 3 checked -> `app.run()` returns exactly the 2 selected paths
    - TC4: Press `Escape` -> `app.run()` returns empty list
    - TC5: Press `q` -> `app.run()` returns empty list (same as Escape)
- [x] 3.4 Implement "Already adopted (updated)" informational section at bottom of TUI (Static, non-interactive)
- [x] 3.5 Implement `app.run()` return value: list of selected artifact paths on confirm, empty list on cancel

## 4. beacon.yaml Update and Post-Adoption Sync

**Goal**: Persist user's selection to beacon.yaml and immediately sync + wire adopted artifacts
**Input**: Selected AdoptCandidate list, beacon.yaml path, warehouse path, project root
**Output**: Updated beacon.yaml, synced artifact files in .agentic-beacon/artifacts/, wired agent configs
**Validation**: beacon.yaml contains new entries; `abc sync --dry-run` shows adopted artifacts as "Unchanged"

- [x] 4.1 Implement `apply_adoption()` in `adopt.py`: load beacon.yaml via `BeaconSettings.from_yaml()`, append selected paths to appropriate `artifacts.<type>` lists, write back via `to_yaml()`
  - **Input**: `apply_adoption(beacon_yaml_path, selections)` where selections is list of AdoptCandidate
  - **Expected Output**: beacon.yaml on disk has new entries appended to correct artifact type lists
  - **Validation**: Re-read beacon.yaml, verify new entries present under correct types, existing entries preserved
  - **TDD Test Cases (write these first):**
    - TC1: Adopt 1 context -> `artifacts.contexts` list grows by 1, other lists unchanged
    - TC2: Adopt 1 skill -> `artifacts.skills` list includes `skills/<name>/` with trailing slash
    - TC3: Adopt 1 knowledge file -> `artifacts.knowledge` list grows by 1
    - TC4: Adopt mix of 2 contexts + 1 skill + 1 knowledge -> all 3 lists updated in single write
    - TC5: Adopt artifact already in beacon.yaml (edge case) -> no duplicate entry added
    - TC6: Empty selection list -> beacon.yaml unchanged
- [x] 4.2 Implement skill path normalization: ensure skills are stored as `skills/<name>/` (directory form with trailing slash) in beacon.yaml
- [x] 4.3 Implement post-adoption sync: after beacon.yaml update, run targeted sync using `SyncEngine.sync_all()` for newly adopted artifact paths only
- [x] 4.4 Implement post-adoption wiring: call `_wire_contexts_opencode()`, `_wire_contexts_claudecode()`, and `_wire_skills_post_sync()` for adopted artifacts

## 5. CLI Command

**Goal**: Wire everything together as an `abc adopt` click command with flags and error handling
**Input**: User runs `abc adopt [--all] [--dry-run]` in a project with warehouse connected
**Output**: Interactive adoption flow or dry-run output
**Validation**: `abc adopt --dry-run` prints table of candidates; `abc adopt --help` shows correct flags

- [x] 5.1 Add `abc adopt` click command in `cli.py` with `--all`, `--dry-run` flags
- [x] 5.2 Implement prerequisite checks: warehouse connected, beacon.yaml exists, sync-state exists (error with hint to run `abc sync` first)
- [x] 5.3 Implement dry-run path: print rich table of candidates grouped by type, then exit
- [x] 5.4 Implement non-interactive fallback: detect via `_is_interactive()`, print list with manual edit instructions
- [x] 5.5 Implement main flow: discover -> TUI -> apply_adoption -> sync -> wire -> print summary
- [x] 5.6 Handle "all adopted" case: print message and exit cleanly when no candidates found

## 6. Sync Notification

**Goal**: Add passive discovery notification at the end of `abc sync`
**Input**: Old sync SHA (captured before overwrite), current warehouse HEAD, beacon.yaml
**Output**: One-liner notification printed after sync summary when unadopted artifacts exist
**Validation**: Run `abc sync` after adding new artifact to warehouse -> notification line appears

- [x] 6.1 Capture old sync SHA before `_write_sync_state()` in the sync command (around line 1494) using `_read_sync_sha()`
- [x] 6.2 Implement `_count_unadopted_since()` lightweight helper: git-diff + beacon.yaml path comparison, returns count only (no description extraction)
  - **TDD Test Cases (write these first):**
    - TC1: 3 new artifact paths in diff, none in beacon.yaml -> returns 3
    - TC2: 3 new artifact paths in diff, 2 in beacon.yaml -> returns 1
    - TC3: No new artifact paths in diff -> returns 0
    - TC4: New paths outside contexts/skills/knowledge -> returns 0 (filtered out)
- [x] 6.3 Add notification print at end of sync command (after wiring, before return): "N new artifact(s) available -- run abc adopt to review"
- [x] 6.4 Skip notification on dry-run and when no previous sync state exists

## 7. Tests

**Goal**: Comprehensive test coverage for all adopt functionality
**Input**: Test fixtures with mock warehouse git repos, beacon.yaml configs, artifact files
**Output**: All tests passing with good coverage of happy paths and edge cases
**Validation**: `uv run pytest libs/beacon/tests/test_adopt.py -v --tb=short` exits 0

- [x] 7.1 Unit tests for `discover_adoptable()`: git-diff mode with new/adopted/mixed artifacts, --all mode, no sync state error
- [x] 7.2 Unit tests for `apply_adoption()`: contexts, skills (directory normalization), knowledge, multiple types at once
- [x] 7.3 Unit tests for description extraction: SKILL.md frontmatter, markdown heading, missing description fallback
- [x] 7.4 TUI tests using textual's `run_test()` harness: checkbox rendering, select-all/none, enter returns selection, escape returns empty
- [x] 7.5 Integration test for `abc adopt --dry-run`: mock warehouse + beacon.yaml, verify output
- [x] 7.6 Unit test for `_count_unadopted_since()` and sync notification logic
