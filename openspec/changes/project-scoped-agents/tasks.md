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
| `agentic-beacon` | `~/Code/oss/agentic-beacon` | `project-scoped-agents` | Code changes — beacon.yaml schema, dependency resolver, adopt TUI, sync repair flow, sample warehouse, docs |
<!-- opsx:repos-table:end -->

## 1. beacon.yaml schema extension

<!-- opsx:phase-summary:1:begin -->
**Goal**: Extend `ArtifactsConfig` with a new `agents: list[str]` field, ensure round-trip YAML serialisation preserves it in the right slot, and have `abc setup` emit it in the scaffold.
**Input**: Predecessor change `move-agent-requires-to-warehouse-manifest` merged; warehouse `agents.yaml` exists; current `BeaconManifest` model with `contexts` and `skills` only.
**Output**: `BeaconManifest.artifacts.agents: list[str]` parses, defaults to `[]`, round-trips through `to_yaml()` ordered after `contexts:` and `skills:`; `abc setup` scaffold writes the new key.
**Validation**: `pytest libs/beacon/tests/unit/core/manifest/ -k beacon -v` passes; `abc warehouse init /tmp/wh-test && grep -A3 'artifacts:' /tmp/wh-test/.agentic-beacon/beacon.yaml` shows `agents: []`.
<!-- opsx:phase-summary:1:end -->


- [ ] 1.1 Add `agents: list[str]` field to `ArtifactsConfig` in `libs/beacon/src/beacon/core/manifest/beacon.py`. Default `[]`. Include in schema serialisation.
<!-- opsx:tdd:1.1:begin -->
  - **Input**: Edit `libs/beacon/src/beacon/core/manifest/beacon.py`; add `agents: list[str] = Field(default_factory=list)` to `ArtifactsConfig`. Run `pytest libs/beacon/tests/unit/core/manifest/ -v`.
  - **Expected Output**: All existing manifest tests pass; new instances of `ArtifactsConfig()` expose `.agents == []`; loading a `beacon.yaml` lacking the key still parses (defaulting to `[]`).
  - **Validation**: Pytest exit 0; `python -c "from beacon.core.manifest.beacon import ArtifactsConfig; print(ArtifactsConfig().agents)"` prints `[]`.
  - **TDD Test Cases (write these first):**
    - TC1: `beacon.yaml` with `artifacts.agents: []` → parses, `agents == []`
    - TC2: `beacon.yaml` with `artifacts.agents: [agents/spec-planner.md]` → parses, `agents == ['agents/spec-planner.md']`
    - TC3: `beacon.yaml` with no `agents` key → parses, `agents == []` (default)
    - TC4: `beacon.yaml` with `artifacts.agents: null` → parses as `[]` or raises clear validation error (document chosen behaviour)
    - TC5: `beacon.yaml` with `artifacts.agents: 'not-a-list'` → Pydantic ValidationError with field name in message
<!-- opsx:tdd:1.1:end -->
- [ ] 1.2 Update `BeaconManifest.to_yaml()` to emit the `agents:` key in the grouped `artifacts:` section, ordered after `contexts:` and `skills:`.
<!-- opsx:tdd:1.2:begin -->
  - **Input**: Run `pytest libs/beacon/tests/unit/core/manifest/ -k to_yaml -v` after editing the serialiser.
  - **Expected Output**: Serialised YAML for a populated manifest contains lines in order: `contexts:` → `skills:` → `agents:` under `artifacts:`.
  - **Validation**: Snapshot/regex test asserts `artifacts:` block ordering; round-trip (`from_yaml(to_yaml(m)) == m`) holds.
  - **TDD Test Cases (write these first):**
    - TC1: Manifest with all three lists populated → YAML emits contexts, skills, agents in that order
    - TC2: Manifest with only `agents` populated → YAML still emits empty `contexts: []` and `skills: []` before `agents:` (or whatever the existing convention is — match it)
    - TC3: Round-trip: `from_yaml(to_yaml(m))` equals `m` for a manifest with mixed agent paths
    - TC4: Existing manifests without agents still serialise identically to today plus a trailing `agents: []`
<!-- opsx:tdd:1.2:end -->
- [ ] 1.3 Unit tests for `BeaconManifest` round-trip with and without `agents:` (absence is valid, empty list is valid, populated list is valid).
<!-- opsx:tdd:1.3:begin -->
  - **Input**: Add tests in `libs/beacon/tests/unit/core/manifest/test_beacon.py`; run `pytest libs/beacon/tests/unit/core/manifest/test_beacon.py -v`.
  - **Expected Output**: Three new test cases pass covering absent / empty / populated `agents` round-trips.
  - **Validation**: Pytest exit 0; coverage report shows the new branches in `BeaconManifest` are exercised.
  - **TDD Test Cases (write these first):**
    - TC1: Round-trip with `agents` key absent → re-serialises with `agents: []`
    - TC2: Round-trip with `agents: []` → re-serialises with `agents: []`
    - TC3: Round-trip with two paths → preserves order and exact strings
    - TC4: Round-trip after mutating `m.artifacts.agents.append(...)` → new entry appears in YAML
<!-- opsx:tdd:1.3:end -->
- [ ] 1.4 Update `libs/beacon/src/beacon/domains/setup/initializer.py` so `abc setup` writes `beacon.yaml` with the `agents: []` field in the scaffold template.
<!-- opsx:tdd:1.4:begin -->
  - **Input**: `abc warehouse init /tmp/wh-test && cat /tmp/wh-test/.agentic-beacon/beacon.yaml`.
  - **Expected Output**: Scaffolded `beacon.yaml` contains `artifacts.agents: []` under the `artifacts:` block.
  - **Validation**: `grep -A5 'artifacts:' /tmp/wh-test/.agentic-beacon/beacon.yaml` shows `agents: []`; matching unit test in `tests/unit/domains/setup/` passes.
  - **Note**: Regenerate `examples/sample-warehouse/` after this edit (per AGENTS.md critical safeguard) — handled in tasks 7.1 / 7.2.
<!-- opsx:tdd:1.4:end -->

## 2. Dependency resolution wiring

<!-- opsx:phase-summary:2:begin -->
**Goal**: Teach the resolver to consume `beacon.yaml.artifacts.agents`, load `agents.yaml`, validate declared agents, and compute the transitive skill closure with provenance.
**Input**: Schema field from Phase 1 in place; `agents.yaml` loader from predecessor change available.
**Output**: Resolver accepts declared agents, surfaces missing-skill gaps as structured errors carrying `(requiring_agent, missing_skill, warehouse_skill_path)`; transitive closure carries `explicit | required-by-agent` provenance.
**Validation**: `pytest libs/beacon/tests/unit/core/dependencies/ -v` green; resolver returns expected closures for fixture warehouses with single-, multi-, and zero-agent declarations.
<!-- opsx:phase-summary:2:end -->


- [ ] 2.1 Extend `libs/beacon/src/beacon/core/dependencies/resolver.py` to accept declared agents from `beacon.yaml.artifacts.agents`. For each declared agent, load `agents.yaml` (via the loader added in the predecessor change), resolve its `skills:` list.
<!-- opsx:tdd:2.1:begin -->
  - **Input**: `pytest libs/beacon/tests/unit/core/dependencies/test_resolver.py -v` against a fixture project with one declared agent.
  - **Expected Output**: Resolver returns the agent's required skills (from `agents.yaml`) merged into the candidate skill set.
  - **Validation**: Returned closure includes every skill in the agent's `skills:` list with provenance `required-by-agent:<name>`.
  - **TDD Test Cases (write these first):**
    - TC1: One declared agent with one required skill → skill appears in closure with correct provenance
    - TC2: One declared agent with empty `skills:` → no addition to closure, no error
    - TC3: Two declared agents requiring same skill → skill appears once; provenance lists both agents
    - TC4: No declared agents → resolver behaves identically to pre-change baseline
    - TC5: Declared agent missing from `agents.yaml` → handled by validator in 2.2 (this resolver step propagates the structured error, does not raise)
<!-- opsx:tdd:2.1:end -->
- [ ] 2.2 Add `validate_declared_agents_in_manifest(beacon_settings, agent_manifest)` — every path in `artifacts.agents` must have a key in `agents.yaml`; missing key is a hard error with migration URL.
<!-- opsx:tdd:2.2:begin -->
  - **Input**: `pytest libs/beacon/tests/unit/core/dependencies/test_validate_declared_agents.py -v`.
  - **Expected Output**: Function returns cleanly when every declared agent path has a matching `agents.yaml` entry; raises a structured error naming offending paths and the migration URL otherwise.
  - **Validation**: Error message contains all missing agent names AND the migration doc URL string.
  - **TDD Test Cases (write these first):**
    - TC1: Empty `artifacts.agents` → no-op, returns successfully
    - TC2: All declared agents have entries in `agents.yaml` → returns successfully
    - TC3: One declared agent missing from `agents.yaml` → raises with that agent's path in message + migration URL
    - TC4: Two declared agents both missing → raises once, message lists both
    - TC5: Declared path uses bare name without `agents/` prefix → either normalises and matches, or raises a clear schema error (document chosen behaviour)
    - TC6: `agents.yaml` itself missing/malformed → propagates the predecessor change's parse error unchanged (do not double-wrap)
<!-- opsx:tdd:2.2:end -->
- [ ] 2.3 Compute the transitive skill closure: declared explicit skills + skills required by declared agents. Carry provenance (explicit vs required-by-agent) through the resolver's data model.
<!-- opsx:tdd:2.3:begin -->
  - **Input**: `pytest libs/beacon/tests/unit/core/dependencies/test_closure.py -v`.
  - **Expected Output**: Closure object reports each skill once with a provenance set: `{'explicit'}`, `{'required-by-agent:<name>', ...}`, or both. Order is deterministic.
  - **Validation**: Provenance set on a skill ticked both explicitly and via an agent equals `{'explicit', 'required-by-agent:<name>'}`.
  - **TDD Test Cases (write these first):**
    - TC1: Skill explicitly declared + required by agent → provenance is `{'explicit', 'required-by-agent:<name>'}`
    - TC2: Skill only required by agent → provenance is `{'required-by-agent:<name>'}`; flagged as candidate for the repair prompt if missing from `beacon.yaml.artifacts.skills`
    - TC3: Skill only explicit → provenance is `{'explicit'}`
    - TC4: Two agents requiring same skill → provenance is `{'required-by-agent:A', 'required-by-agent:B'}`
    - TC5: Closure ordering is deterministic across runs (sort by `(skill_path,)`)
    - TC6: Skill required by an agent but missing from warehouse → resolver yields a structured error, does not crash
<!-- opsx:tdd:2.3:end -->
- [ ] 2.4 Unit tests covering: no agents declared, one agent with skills, one agent with empty skills, agent not in manifest, skill not in warehouse, multi-agent overlapping skill requirements.
<!-- opsx:tdd:2.4:begin -->
  - **Input**: `pytest libs/beacon/tests/unit/core/dependencies/ -v`.
  - **Expected Output**: Six new parametrised cases, all green.
  - **Validation**: Pytest exit 0; coverage on `resolver.py` and `validate_declared_agents_in_manifest` ≥ 90% for new branches.
  - **TDD Test Cases (write these first):**
    - TC1: `artifacts.agents == []` → closure equals pre-change behaviour
    - TC2: One agent with two required skills → both pulled with correct provenance
    - TC3: One agent with `skills: []` in `agents.yaml` → no additions, no error
    - TC4: Declared agent missing from `agents.yaml` → validator raises with migration URL
    - TC5: Declared agent's required skill missing from warehouse → resolver yields hard-error gap (per spec, fires regardless of TTY mode)
    - TC6: Two agents requiring overlapping skill set → skill appears once with combined provenance
<!-- opsx:tdd:2.4:end -->

## 3. abc sync: interactive repair prompt

<!-- opsx:phase-summary:3:begin -->
**Goal**: Wire the resolver gap into `abc sync` as an interactive Y/N (default N) prompt with non-interactive hard-error and `--yes` auto-accept.
**Input**: Resolver gap shape from Phase 2; existing `abc sync` command in `cli/sync.py` and the interaction helper.
**Output**: `abc sync` halts before any file op when gaps are detected, prompts in TTY, hard-errors otherwise, and `--yes` auto-accepts. `beacon.yaml` is updated atomically (all gaps accepted or none) before sync resumes.
**Validation**: `pytest libs/beacon/tests/unit/cli/ -k sync` and `tests/unit/core/dependencies/ -k repair` both green; CliRunner-driven scenarios exercise Y / N / Enter / non-interactive / `--yes`.
<!-- opsx:phase-summary:3:end -->


- [ ] 3.1 Add a new error/warning shape in `libs/beacon/src/beacon/core/dependencies/` that carries the gap info (requiring agent, missing skill, warehouse skill path).
- [ ] 3.2 In the sync flow (sync command in `domains/warehouse/` or equivalent), intercept the gap before any file operation. In interactive mode, prompt Y/N default N using `click.confirm` or existing interaction helper.
<!-- opsx:tdd:3.2:begin -->
  - **Input**: `pytest libs/beacon/tests/unit/cli/test_sync.py -k 'gap and interactive' -v` using `click.testing.CliRunner` with `monkeypatch.setattr(sys.stdin, 'isatty', lambda: True)` and `input='y\n'` / `input='n\n'`.
  - **Expected Output**: Prompt fires with text naming the requiring agent and missing skill; default answer is N; no symlinks created until response received.
  - **Validation**: CliRunner output contains the expected prompt; `.agentic-beacon/artifacts/` filesystem state is unchanged before the response is provided.
  - **TDD Test Cases (write these first):**
    - TC1: One gap, interactive Y → `beacon.yaml` updated, sync proceeds
    - TC2: One gap, interactive N → exit non-zero, `beacon.yaml` untouched, no symlinks
    - TC3: One gap, interactive Enter (default N) → same as TC2
    - TC4: Two gaps, both Y → atomic write of both skills, sync proceeds (per spec atomicity)
    - TC5: Two gaps, first Y second N → `beacon.yaml` untouched (atomic rejection), exit non-zero
    - TC6: Prompt fires BEFORE any symlink/prune/file op (assert ordering via spy on sync helper)
<!-- opsx:tdd:3.2:end -->
- [ ] 3.3 On Y: append the normalised skill path (`skills/<name>/`) to `beacon.yaml.artifacts.skills`, persist with `BeaconManifest.to_yaml()`, re-run the resolver with the updated state, proceed to sync.
<!-- opsx:tdd:3.3:begin -->
  - **Input**: Run sync against a fixture project with a declared agent missing one required skill; respond `y`.
  - **Expected Output**: `beacon.yaml.artifacts.skills` contains `skills/<name>/` after sync; resolver re-runs and pulls transitive contexts silently; sync exits 0.
  - **Validation**: Diff `beacon.yaml` before/after — skills list grew by exactly one entry, normalised to `skills/<name>/` form (trailing slash, with `skills/` prefix); transitive contexts auto-pulled per `artifact-dependency-resolution` spec.
  - **TDD Test Cases (write these first):**
    - TC1: Bare name `opsx-enhance-tasks` → written as `skills/opsx-enhance-tasks/`
    - TC2: Already prefixed `skills/foo/` → preserved as-is, no double-prefix
    - TC3: Skill with transitive context requirement → context auto-pulled silently after re-run (no second prompt)
    - TC4: Two gaps both Y → single atomic write of both skill entries, single re-resolve
<!-- opsx:tdd:3.3:end -->
- [ ] 3.4 On N (or Enter on default): raise a `DependencyError` carrying the migration URL; let the normal error-printing path surface it; exit non-zero.
<!-- opsx:tdd:3.4:begin -->
  - **Input**: Sync with one gap, respond `N`.
  - **Expected Output**: `DependencyError` raised; CLI exits non-zero; stderr contains the migration URL.
  - **Validation**: `result.exit_code != 0`; `migration` URL substring present in stderr; `beacon.yaml` byte-identical to pre-sync; `.agentic-beacon/artifacts/` byte-identical.
<!-- opsx:tdd:3.4:end -->
- [ ] 3.5 Non-interactive mode (no TTY): skip the prompt; raise the same error unless `--yes` is passed.
<!-- opsx:tdd:3.5:begin -->
  - **Input**: `abc sync < /dev/null` against fixture with a gap; then again with `abc sync --yes < /dev/null`.
  - **Expected Output**: First run: hard error, exit non-zero, `beacon.yaml` untouched. Second run: auto-accept, `beacon.yaml` updated, exit 0.
  - **Validation**: TTY detection helper used is the project's existing `is_interactive()`; error path identical to interactive-N.
  - **TDD Test Cases (write these first):**
    - TC1: No TTY, no `--yes`, gap present → hard error, no mutations
    - TC2: No TTY, `--yes`, gap present → auto-accept, `beacon.yaml` updated, sync proceeds
    - TC3: No TTY, no gaps → sync proceeds normally regardless of `--yes`
    - TC4: Piped stdin (e.g. `echo y | abc sync`) detected as non-interactive → behaves per TC1, NOT as if user typed Y
<!-- opsx:tdd:3.5:end -->
- [ ] 3.6 Add `--yes` flag to `abc sync` CLI handler. Plumb into the resolver's prompt logic as auto-accept.
- [ ] 3.7 Unit tests for each branch: interactive Y, interactive N, interactive default-Enter, non-interactive no-flag, non-interactive with `--yes`. Use `pytest`'s `monkeypatch` to fake TTY detection and `click.testing.CliRunner` for CLI input.
<!-- opsx:tdd:3.7:begin -->
  - **Input**: `pytest libs/beacon/tests/unit/cli/test_sync.py -k 'repair' -v`.
  - **Expected Output**: Five parametrised cases green covering each branch.
  - **Validation**: Pytest exit 0; coverage on the prompt/auto-accept code paths ≥ 90%.
<!-- opsx:tdd:3.7:end -->

## 4. Adoption flow: remove skip + record agents

<!-- opsx:phase-summary:4:begin -->
**Goal**: Eliminate the hard-coded `continue  # agents are managed globally` in `apply.py` and record agent selections in `beacon.yaml.artifacts.agents`, while preserving global install and never uninstalling on unadopt.
**Input**: Schema and resolver from Phases 1–2; existing `apply_adoption`, `discovery.is_adopted`, and `cleanup_unadopted_artifacts`.
**Output**: Adopt flow appends `agents/<name>.md` to `beacon.yaml`, fires global install, recognises agents in `is_adopted()`, and explicitly does NOT uninstall global symlinks on unadopt (with code comment citing Decision 7).
**Validation**: `pytest libs/beacon/tests/unit/domains/adoption/ -v` green; integration assertion that `beacon.yaml` is updated and global symlinks remain after unadopt.
<!-- opsx:phase-summary:4:end -->


- [ ] 4.1 In `libs/beacon/src/beacon/domains/adoption/apply.py::apply_adoption()`, remove the `if candidate.artifact_type == "agents": continue` skip. Extend the branch to append `candidate.path` (form `agents/<name>.md`) to `beacon_settings.artifacts.agents`; deduplicate.
<!-- opsx:tdd:4.1:begin -->
  - **Input**: `pytest libs/beacon/tests/unit/domains/adoption/test_apply.py -k agent -v` after editing `apply.py`.
  - **Expected Output**: Selected agent is appended to `beacon.yaml.artifacts.agents` (no duplicate on re-adopt); persisted via `to_yaml()`.
  - **Validation**: Diff fixture `beacon.yaml` shows new entry; running adopt twice in a row produces only one entry per agent.
  - **TDD Test Cases (write these first):**
    - TC1: First-time adopt of one agent → entry appears exactly once
    - TC2: Re-adopt same agent (already in `agents`) → no duplicate appended
    - TC3: Adopt one agent + one context + one skill in same run → all three appear under their respective lists in a single write
    - TC4: Path normalisation: candidate.path is stored as `agents/<name>.md` (matches Decision 6 / spec scenario)
<!-- opsx:tdd:4.1:end -->
- [ ] 4.2 Ensure the existing global install call path for selected agents (from the adopt apply flow) continues to fire — agents still symlink into `~/.config/opencode/agents/` and `~/.claude/agents/`.
<!-- opsx:tdd:4.2:begin -->
  - **Input**: Run `apply_adoption` against a tmp HOME with the agent install helper; inspect `~/.config/opencode/agents/` and `~/.claude/agents/`.
  - **Expected Output**: Both directories contain a symlink to the warehouse agent file.
  - **Validation**: `os.path.islink(~/.config/opencode/agents/<name>.md) == True` and target resolves into the warehouse working tree.
<!-- opsx:tdd:4.2:end -->
- [ ] 4.3 Update `libs/beacon/src/beacon/domains/adoption/discovery.py::is_adopted()` to check `beacon_settings.artifacts.agents` in addition to contexts and skills.
<!-- opsx:tdd:4.3:begin -->
  - **Input**: `pytest libs/beacon/tests/unit/domains/adoption/test_discovery.py -k is_adopted -v`.
  - **Expected Output**: Agent path returns True when in `artifacts.agents`, False otherwise; symmetric with contexts/skills behaviour.
  - **Validation**: All three artifact types share one parametrised test confirming identical adoption-check semantics.
<!-- opsx:tdd:4.3:end -->
- [ ] 4.4 Update `cleanup_unadopted_artifacts()` (and any unadopt helpers) so that removing an agent from `beacon.yaml.artifacts.agents` does NOT uninstall the global symlink; explicit comment in the code stating this is intentional (Decision 7).
<!-- opsx:tdd:4.4:begin -->
  - **Input**: `pytest libs/beacon/tests/unit/domains/adoption/test_cleanup.py -k 'agent and unadopt' -v`.
  - **Expected Output**: After removing an agent from `beacon.yaml` and running cleanup, both global symlinks (opencode + claude) still exist; no uninstall side effect.
  - **Validation**: Pytest green; `git grep -n 'Decision 7' libs/beacon/src/beacon/domains/adoption/` returns the comment marker.
  - **TDD Test Cases (write these first):**
    - TC1: Remove agent from `beacon.yaml`, run cleanup → global symlinks persist
    - TC2: Same scenario but with two projects sharing the same global agent → other project's `is_adopted` still True; symlinks persist
    - TC3: Code comment explicitly cites Decision 7 (grepable marker) — guards against future regression by removal
<!-- opsx:tdd:4.4:end -->
- [ ] 4.5 Unit tests for apply_adoption with agent selections; assert `beacon.yaml` updated, global install triggered, no global uninstall on unadoption.
<!-- opsx:tdd:4.5:begin -->
  - **Input**: `pytest libs/beacon/tests/unit/domains/adoption/ -v`.
  - **Expected Output**: All new tests green; coverage on the agent branch of `apply_adoption` and on `cleanup_unadopted_artifacts` ≥ 90%.
  - **Validation**: Pytest exit 0.
<!-- opsx:tdd:4.5:end -->

## 5. Adoption TUI: agent category + auto-tick + hard-lock

<!-- opsx:phase-summary:5:begin -->
**Goal**: Render agents as a third TUI category, auto-tick required skills with provenance, hard-lock skill un-toggling while a requiring agent is ticked, and prune transitive ticks while preserving user-explicit ticks.
**Input**: Existing `tui.py` Textual app; `agents.yaml` warehouse loader; `discovery.py` candidate list.
**Output**: Agents section visible; ticking an agent auto-ticks its required skills with `(required by ...)` markers (capped at 3 + `+N more`); attempting to untick a locked skill is refused with a status line; unticking the last requiring agent auto-unticks transitive-only skills; `user_explicit` flag survives agent unticks; `a`/`n` keybindings respect the new propagation rules.
**Validation**: `pytest libs/beacon/tests/unit/domains/adoption/test_tui*.py -v` green including Textual headless snapshot/runtime cases for: tick → propagate; untick-skill while agent ticked → blocked; untick-agent → release; multi-agent shared skill provenance.
<!-- opsx:phase-summary:5:end -->


- [ ] 5.1 In `libs/beacon/src/beacon/domains/adoption/tui.py`, add an "Agents" section alongside "Contexts" and "Skills". Populate with agent candidates from `discovery.py`.
<!-- opsx:tdd:5.1:begin -->
  - **Input**: Textual headless test driving the TUI with a fixture that has 1 context, 1 skill, 1 agent.
  - **Expected Output**: Rendered tree contains three section headings: 'Contexts', 'Skills', 'Agents'; each populated with its candidate.
  - **Validation**: Snapshot matches; the 'Agents' section header is present even when zero candidates exist (empty section, not missing).
<!-- opsx:tdd:5.1:end -->
- [ ] 5.2 When an agent is ticked, read `agents.yaml` (via the warehouse client), resolve `skills:` list, programmatically tick the corresponding skill checkboxes. Record a `required_by` provenance map keyed on skill name → list of requiring agents.
<!-- opsx:tdd:5.2:begin -->
  - **Input**: Headless run: tick `spec-planner` whose `agents.yaml` entry lists `[opsx-enhance-tasks]`.
  - **Expected Output**: After tick event, the `opsx-enhance-tasks` checkbox is checked; `required_by['opsx-enhance-tasks'] == ['spec-planner']`.
  - **Validation**: Snapshot of TUI state shows skill checkbox ticked and provenance present; internal data structure reflects the propagation.
  - **TDD Test Cases (write these first):**
    - TC1: Tick agent with one required skill → skill ticks, provenance recorded
    - TC2: Tick agent whose `agents.yaml` `skills:` list is empty → no propagation, no error
    - TC3: Tick two agents requiring the same skill → `required_by[skill]` contains both
    - TC4: Tick agent then untick same agent immediately → skill un-ticks (per 5.5), provenance cleared
    - TC5: Required skill missing from warehouse → propagation logs/surfaces a TUI error per `agent-skill-dependency-sync` spec; `abc adopt` should refuse to render in this case (see Scenario 'Malformed warehouse blocks adopt TUI')
<!-- opsx:tdd:5.2:end -->
- [ ] 5.3 Render provenance next to each skill checkbox when non-empty (e.g. ``(required by spec-planner, registra-developer)``). Cap display to first 3 agents with `+N more` if the list is longer.
<!-- opsx:tdd:5.3:begin -->
  - **Input**: Headless run: tick four agents that all require the same skill.
  - **Expected Output**: Skill row text reads `(required by A, B, C +1 more)` (first 3 + count).
  - **Validation**: Regex on rendered row matches the cap format; explicit `0` provenance shows nothing (no parenthetical).
  - **TDD Test Cases (write these first):**
    - TC1: 1 requirer → `(required by A)`
    - TC2: 3 requirers → `(required by A, B, C)`
    - TC3: 4+ requirers → `(required by A, B, C +N more)` with N = total - 3
    - TC4: 0 requirers (skill ticked explicitly only) → no provenance text
<!-- opsx:tdd:5.3:end -->
- [ ] 5.4 Implement hard-lock: when a skill's `required_by` list is non-empty, the checkbox rejects toggle-off events. Show a transient status message ``"Required by: <agent> — untick agent first"``.
<!-- opsx:tdd:5.4:begin -->
  - **Input**: Headless run: tick agent (auto-ticks skill); attempt to untick the skill.
  - **Expected Output**: Skill remains ticked; status bar shows `Required by: <agent> — untick agent first`.
  - **Validation**: Snapshot before/after the rejected toggle attempt are identical w.r.t. checkbox state; status message text matches the spec.
  - **TDD Test Cases (write these first):**
    - TC1: Untick a hard-locked skill → toggle refused, status message shown, state unchanged
    - TC2: Same skill required by multiple agents → status message names all agents (or first N + more)
    - TC3: Skill with `required_by == []` (user-explicit only) → toggle works normally
    - TC4: Status message clears after configurable transient interval (or next user input)
<!-- opsx:tdd:5.4:end -->
- [ ] 5.5 When an agent is unticked, remove it from every skill's `required_by` list. If a skill's `required_by` becomes empty AND the user never explicitly ticked it (tracked separately as `user_explicit`), auto-untick the skill.
<!-- opsx:tdd:5.5:begin -->
  - **Input**: Headless run: tick agent → skill auto-ticks; untick agent.
  - **Expected Output**: Skill auto-unticks; `required_by[skill]` cleared; `user_explicit[skill]` is False.
  - **Validation**: Snapshot shows skill un-ticked after agent un-tick; provenance gone.
  - **TDD Test Cases (write these first):**
    - TC1: Single agent → skill; untick agent → skill auto-unticks
    - TC2: Two agents → same skill; untick one → skill stays ticked, provenance keeps the other
    - TC3: User explicitly ticks skill, then ticks agent (which would also require it), then unticks agent → skill stays ticked because `user_explicit` is True (per Open Q1 in design)
    - TC4: User explicitly ticks skill, agent ticking adds redundant provenance, untick all agents → skill stays ticked
<!-- opsx:tdd:5.5:end -->
- [ ] 5.6 When a skill is ticked directly by the user, set `user_explicit[skill] = True`. This survives subsequent agent unticks.
<!-- opsx:tdd:5.6:begin -->
  - **Input**: Headless run: user clicks skill checkbox directly (no agent ticked yet).
  - **Expected Output**: `user_explicit[skill] == True`; later agent untick does not auto-clear the skill.
  - **Validation**: Snapshot after the sequence (explicit-tick → tick-agent → untick-agent) shows skill still ticked.
<!-- opsx:tdd:5.6:end -->
- [ ] 5.7 Update the `select all` (`a`) and `select none` (`n`) keybindings: select-all triggers agent-auto-tick propagation; select-none clears everything including provenance.
<!-- opsx:tdd:5.7:begin -->
  - **Input**: Headless run: press `a`; then press `n`.
  - **Expected Output**: After `a`: every checkbox ticked, agent-auto-tick still propagated (no inconsistent state). After `n`: every checkbox un-ticked, `required_by` and `user_explicit` maps both empty.
  - **Validation**: Snapshot after each keypress matches expected; idempotency: pressing `a` twice yields identical state.
  - **TDD Test Cases (write these first):**
    - TC1: Press `a` with mixed initial state → all ticked, all `user_explicit` True (since user explicitly select-all'd), agent provenance also recorded
    - TC2: Press `n` after `a` → fully empty state, provenance cleared
    - TC3: Press `a` twice → idempotent, no double-provenance entries
<!-- opsx:tdd:5.7:end -->
- [ ] 5.8 TUI snapshot tests or headless runs (textual's test harness) covering: tick agent → skills auto-tick with provenance; untick skill while agent ticked → blocked; untick agent → skill auto-unticks unless user-explicit; multi-agent shared skill provenance.
<!-- opsx:tdd:5.8:begin -->
  - **Input**: `pytest libs/beacon/tests/unit/domains/adoption/test_tui*.py -v`.
  - **Expected Output**: Four snapshot/state cases green; failures produce clear diff output.
  - **Validation**: Pytest exit 0.
<!-- opsx:tdd:5.8:end -->

## 6. Warehouse `abc warehouse status` and safety checks

<!-- opsx:phase-summary:6:begin -->
**Goal**: Surface declared-agent / missing-skill mismatches in `abc warehouse status` and confirm the `validate_declared_agents_in_manifest` error path is reachable end-to-end.
**Input**: Phase 2 validator; existing `validator.py` integrity report.
**Output**: Warehouse status report includes a section listing declared agents whose `agents.yaml` requirements are unmet; the declared-agent-not-in-manifest error path emits the migration URL.
**Validation**: Smoke test with fixture warehouse + project shows the expected report block when a gap exists, and is absent when clean; `pytest libs/beacon/tests/unit/domains/warehouse/ -v` green.
<!-- opsx:phase-summary:6:end -->


- [ ] 6.1 Extend `libs/beacon/src/beacon/domains/warehouse/validator.py` so `abc warehouse status` reports declared agents whose `agents.yaml` entries have missing skills, as part of the existing warehouse integrity report.
<!-- opsx:tdd:6.1:begin -->
  - **Input**: `abc warehouse status` against a fixture warehouse with one declared agent whose `agents.yaml` requires a skill that does not exist in the warehouse.
  - **Expected Output**: Report includes a section listing the offending agent + missing skill; exit non-zero (matching existing integrity-failure semantics).
  - **Validation**: Stdout contains substrings for the agent name AND the missing skill; clean fixture produces no such section.
<!-- opsx:tdd:6.1:end -->
- [ ] 6.2 Confirm the "declared agent not in `agents.yaml`" error (per `validate_declared_agents_in_manifest`) surfaces with clear output.
- [ ] 6.3 Smoke tests using a fixture warehouse + project fixture.
<!-- opsx:tdd:6.3:begin -->
  - **Input**: `pytest libs/beacon/tests/integration/test_warehouse_status_agents.py -v` (or unit-level if integration framework is overkill).
  - **Expected Output**: Smoke covers: clean warehouse, missing-skill warehouse, declared-agent-missing warehouse — each with expected report output and exit code.
  - **Validation**: Pytest exit 0 across all three smokes.
<!-- opsx:tdd:6.3:end -->

## 7. Sample warehouse + migration doc

<!-- opsx:phase-summary:7:begin -->
**Goal**: Update `examples/sample-warehouse/` to demonstrate the feature end-to-end and append the user-facing migration section.
**Input**: Working code from Phases 1–6; current `examples/sample-warehouse/agents/agents.yaml` and `docs/migrations/artifact-dependencies-frontmatter.md`.
**Output**: Sample warehouse declares one example agent with a real skill requirement (and the matching skill exists); migration doc has a 'Project-scoped agents' section.
**Validation**: `abc warehouse init /tmp/wh-test` followed by `abc adopt` shows the example agent as a candidate and auto-ticks the matching skill; `mkdocs build` (or local doc render) succeeds with no broken links.
<!-- opsx:phase-summary:7:end -->


- [ ] 7.1 **[MANUAL]** Update `examples/sample-warehouse/agents/agents.yaml` to declare an example agent with a skill requirement, demonstrating the feature end-to-end.
- [ ] 7.2 **[MANUAL]** If the sample warehouse lacks a sample skill matching the declared requirement, add one (minimal `skills/<name>/SKILL.md`).
- [ ] 7.3 **[MANUAL]** Append a "Project-scoped agents" section to `docs/migrations/artifact-dependencies-frontmatter.md` describing the new field, the `abc adopt` flow, the repair prompt at sync, and the zero-friction "re-run adopt" migration for existing users.

## 8. AGENTS.md & site-docs sync

<!-- opsx:phase-summary:8:begin -->
**Goal**: Bring user-facing prose in line with the new dual semantics (declared per-project AND globally installed) and remove every 'agents are not in beacon.yaml' assertion.
**Input**: Code complete through Phase 7; the enumerated list of stale spots in tasks 8.1 and 8.4.
**Output**: AGENTS.md, README, site-docs, and the six enumerated source-file comments/strings reflect the new dual semantics; no 'agents are global-only / not in beacon.yaml' language remains.
**Validation**: `grep -rn -E 'agents are (managed|installed) globally|not in beacon.yaml|AI agent definitions • installed globally' libs/ AGENTS.md README.md site-docs/ docs/` returns zero matches except in changelog/migration history.
<!-- opsx:phase-summary:8:end -->


- [ ] 8.1 **[MANUAL]** Update `AGENTS.md` at the repo root to describe the new agent declaration field and remove any language asserting "agents are not tracked in beacon.yaml."
- [ ] 8.2 **[MANUAL]** Update relevant pages under `site-docs/` that describe `beacon.yaml` schema or the adoption flow. This is the single MkDocs refresh covering both this change and the predecessor `move-agent-requires-to-warehouse-manifest` — the docs surface is updated once at the end.
- [ ] 8.3 **[MANUAL]** Ensure any README snippets in the repo showing `beacon.yaml` examples include the new `agents:` line where relevant.
- [ ] 8.4 **[MANUAL]** Clean up stale "agents are global-only / not in beacon.yaml" language across the code. Concrete spots:
<!-- opsx:tdd:8.4:begin -->
  - **Input**: After edits: `grep -rn -E 'agents are (managed|installed) globally|not in beacon\.yaml|installed globally to' libs/beacon/src/ libs/beacon/src/beacon/data/templates/`.
  - **Expected Output**: Zero matches outside changelog/migration history.
  - **Validation**: All six enumerated spots updated to reflect dual semantics; CI architecture test still green; sample-warehouse regeneration still matches.
  - **Note**: Six concrete spots enumerated in tasks.md must each be visited and rewritten — not deleted blindly.
  - **Note**: The `continue  # agents are managed globally` comment at apply.py:40 is already covered by task 4.1 (full deletion of the skip), do not double-edit.
<!-- opsx:tdd:8.4:end -->
  - `libs/beacon/src/beacon/domains/adoption/discovery.py:340` — comment `# "adopted" means installed in a global agent directory, not beacon.yaml`
  - `libs/beacon/src/beacon/domains/adoption/tui.py:137` — subtitle string `"AI agent definitions • installed globally to ..."`
  - `libs/beacon/src/beacon/domains/setup/wiring.py:21` — comment `# Agents are machine-level global artifacts — use 'abc install agents/<name>.md'`
  - `libs/beacon/src/beacon/cli/setup.py:56` — console string `"agents — globally linked on your machine with 'abc agents sync' (not in beacon.yaml)"`
  - `libs/beacon/src/beacon/data/templates/README.md:27` — section about installing global agents
  - `libs/beacon/src/beacon/data/templates/agents/README.md:9` — "Unlike other artifact types, agents are globally installed..."
  Rewrite each to reflect the dual semantics: agents are declared per-project in `beacon.yaml.artifacts.agents` AND globally installed. The `continue  # agents are managed globally` comment at `apply.py:40` is already addressed by task 4.1 (full deletion of the skip).

## 9. Release + validation

<!-- opsx:phase-summary:9:begin -->
**Goal**: Run the full automated suite and four manual smokes to confirm the feature works end-to-end and existing-project upgrade is zero-friction.
**Input**: All prior phases complete on `project-scoped-agents` branch.
**Output**: Pytest green, architecture test green, four manual smokes pass, release notes drafted calling out the new field, the breaking adopt-behaviour change, and the sync repair prompt.
**Validation**: `pytest` from repo root → 0 failures; smokes 1–4 each documented with command logs and resulting `beacon.yaml`; release notes reviewed.
<!-- opsx:phase-summary:9:end -->


- [ ] 9.1 **[MANUAL]** Run full `pytest` suite from repo root — all tests pass.
<!-- opsx:tdd:9.1:begin -->
  - **Input**: From repo root: `uv run pytest`.
  - **Expected Output**: Exit 0; zero failures; zero collection errors.
  - **Validation**: `echo $?` returns 0 immediately after pytest.
<!-- opsx:tdd:9.1:end -->
- [ ] 9.2 **[MANUAL]** Run architecture test (`libs/beacon/tests/unit/test_architecture.py`) — still green.
<!-- opsx:tdd:9.2:begin -->
  - **Input**: `uv run pytest libs/beacon/tests/unit/test_architecture.py -v`.
  - **Expected Output**: All cases pass: cli/ → domains/ → core/, utils/ layering still respected; new code does not violate dependency rule.
  - **Validation**: Pytest exit 0.
<!-- opsx:tdd:9.2:end -->
- [ ] 9.3 **[MANUAL]** Manual smoke #1: fresh project, `abc setup`, `abc adopt` — agents appear, auto-tick works, hard-lock works, `beacon.yaml` updated correctly.
<!-- opsx:tdd:9.3:begin -->
  - **Input**: Fresh tmp dir; `abc warehouse init wh && cd /tmp/proj && abc setup && abc adopt` (interactive).
  - **Expected Output**: TUI shows Agents section; ticking the example agent auto-ticks its required skill with provenance; attempting to untick the skill is blocked with status message; on confirm, `beacon.yaml.artifacts.agents` and `.skills` both contain the new entries.
  - **Validation**: Diff `beacon.yaml` before/after confirms both agent and required skill recorded; global symlinks under `~/.config/opencode/agents/` and `~/.claude/agents/` exist.
<!-- opsx:tdd:9.3:end -->
- [ ] 9.4 **[MANUAL]** Manual smoke #2: project with `beacon.yaml.artifacts.agents` declared, hand-remove a required skill, run `abc sync` — prompt fires, Y accepts, `beacon.yaml` updated, sync completes.
<!-- opsx:tdd:9.4:begin -->
  - **Input**: Hand-edit `beacon.yaml` to remove a required skill from `artifacts.skills` while keeping the agent in `artifacts.agents`; run `abc sync` interactively.
  - **Expected Output**: Prompt: `Add 'skills/<name>/' to beacon.yaml and sync it? [y/N]`; press y → skill re-appended, sync proceeds, exit 0.
  - **Validation**: `beacon.yaml.artifacts.skills` regrew the entry; symlink for the skill exists under `.agentic-beacon/artifacts/`; transitive contexts (if any) auto-pulled silently.
<!-- opsx:tdd:9.4:end -->
- [ ] 9.5 **[MANUAL]** Manual smoke #3: same setup as #4 but in non-interactive mode (e.g. `abc sync < /dev/null`) — hard error, `beacon.yaml` unchanged.
<!-- opsx:tdd:9.5:begin -->
  - **Input**: Same fixture as smoke #2; `abc sync < /dev/null` (no TTY, no `--yes`).
  - **Expected Output**: Hard error mentioning the agent + missing skill + migration URL; exit non-zero; `beacon.yaml` byte-identical to pre-run.
  - **Validation**: `echo $?` non-zero; `git diff beacon.yaml` empty; `.agentic-beacon/artifacts/` byte-identical.
  - **Note**: Then re-run with `--yes`: `abc sync --yes < /dev/null` — should auto-accept and complete (sanity check on the `--yes` plumbing).
<!-- opsx:tdd:9.5:end -->
- [ ] 9.6 **[MANUAL]** Manual smoke #4: upgrade existing project that used `abc adopt` for agents pre-this-change — confirm `beacon.yaml.artifacts.agents` is empty and `abc sync` still works (global agents remain symlinked).
<!-- opsx:tdd:9.6:begin -->
  - **Input**: Use a real existing project (one of the user's homelab repos that previously ran `abc adopt`); upgrade Beacon; run `abc sync` without re-running adopt.
  - **Expected Output**: `beacon.yaml.artifacts.agents` is `[]` (or absent and treated as empty); `abc sync` completes successfully; pre-existing global agent symlinks remain in `~/.config/opencode/agents/` and `~/.claude/agents/`.
  - **Validation**: Pre-upgrade backup of `~/.config/opencode/agents/` matches post-sync state (no symlinks removed); `abc sync` exits 0.
<!-- opsx:tdd:9.6:end -->
- [ ] 9.7 **[MANUAL]** Release notes: call out the new field, the breaking change to `abc adopt` behaviour (records in `beacon.yaml`), and the repair prompt in `abc sync`.

<!-- opsx:metadata:begin -->
---

## Enhancement Metadata

**Enhanced**: 2026-05-06
**Methodology**: Spec-Driven Development + TDD
**Enhancements Applied**:
- TDD Workflow Header
- Repositories & Branches table
- Phase summaries (Goal/Input/Output/Validation)
- Task-level TDD criteria on 35 task(s)
- 77 test case(s) across complex tasks
- 14 task(s) flagged [MANUAL]

**Status**: Ready for implementation via `/opsx-apply <name>`.
<!-- opsx:metadata:end -->
