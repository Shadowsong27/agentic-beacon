## Context

The `hl-knowledge-market` warehouse has no CI. Every artifact contract violation — a `SKILL.md` merged without YAML frontmatter, an agent referencing a deleted context, an unparseable `requires:` block — surfaces hours later when a downstream project runs `abc sync` and the dependency resolver throws (concrete recent example: `delegate-to-cc/SKILL.md` regression, broke `abc sync` in `agentic-beacon`).

Beacon already owns every validator needed to catch these defects. The relevant primitives are:

| Primitive | Location | Surface |
|---|---|---|
| `WarehouseValidator.validate` | `domains/warehouse/validator.py` | structure + agent manifest, returns `ValidationResult(errors: list[str])` |
| `parse_frontmatter` | `core/dependencies/frontmatter.py` | returns `FrontmatterResult` (never raises) |
| `SkillFrontmatter` | `core/dependencies/frontmatter.py` | Pydantic model; enforces `requires.contexts` and rejects `requires.skills` |
| `load_agent_manifest`, `validate_agents_directory`, `validate_agent_frontmatter_clean`, `validate_declared_skills` | `core/dependencies/manifest.py` | each raises `AgentManifestError(message)` (message may contain `\n`-joined per-defect lines) |
| `extract_markdown_links`, `resolve_link`, `classify_knowledge_ref` | `core/scanner/scanner.py` | path-agnostic link helpers |
| `scan_file_for_knowledge` | `core/scanner/scanner.py` | returns refs as a `set[str]`; broken targets are `logger.warning` only |

All of these are path-agnostic — they take a `warehouse_path: Path` and operate against any directory. None of them require a project-side `beacon.yaml` or `.agentic-beacon/` to function. That is the key property this design exploits: the lint command is a thin compose-and-format layer over primitives that already exist.

There are two **shape mismatches** between what exists and what lint needs that this design has to bridge:

1. The manifest validators raise on first defect-class (e.g. `validate_agents_directory` raises an `AgentManifestError` whose message is `"\n"`-joined defects). Lint must keep going past the first raise so a single invocation reports every category.
2. `scan_file_for_knowledge` is project-aware (it returns the resolved-set used by `compute_effective_set`) and downgrades broken links to warnings. Lint needs per-file *errors* with the *source file* attached. We do not modify the primitive — we walk the same files in `lint.py` and call the low-level link helpers (`extract_markdown_links` + `resolve_link` + `classify_knowledge_ref`) directly.

The agent-frontmatter `name` / `description` requirement (the third novel piece) has no precedent anywhere in Beacon. `validate_agent_frontmatter_clean` only checks for the *absence* of a `requires:` key; nothing currently asserts presence of `name`/`description`. The new rule is lint-only.

## Goals / Non-Goals

**Goals:**

- Provide `abc warehouse lint [PATH]` as the single entry point a warehouse repo's CI runs to validate every artifact contract Beacon enforces.
- Reuse existing primitives without changing their contracts or behaviour for any existing caller (`abc sync`, `abc warehouse validate`, `compute_effective_set` all unchanged).
- Aggregate every category of error before exiting, so a single CI run gives full visibility (no "fix one, push, see next").
- Group findings by artifact path with stable ordering so CI logs and developer terminals show identical output.
- Keep the new module under ~110 LOC, the CLI handler under ~30 LOC, and add no new third-party dependency.

**Non-Goals:**

- No refactor of the existing primitives. `scan_file_for_knowledge` keeps its warning-only posture. `validate_*` helpers keep raising. The lint module is the only place that re-interprets these as errors.
- No `--json` / SARIF output (defer until a consumer needs it; `--json` flag will be rejected by Click in v1).
- No orphan detection (skills, contexts, knowledge files that nothing references). Out of scope per proposal.
- No `model:` requirement on agent frontmatter — PER-114 says "where applicable", which is undefined, and there is no test signal to lock the rule against.
- No strict frontmatter rule on skills (e.g. requiring `name` / `description` on `SKILL.md`). The existing `SkillFrontmatter` (validating `requires.contexts` only) is preserved.
- No CI yaml for `agentic-beacon` itself — this change ships the CLI; the warehouse-side workflow lives in `hl-knowledge-market` and is rolled out separately.
- No branch protection. Branch protection on private personal repos is not available on the current GitHub plan; the workflow remains advisory until that constraint changes.

## Decisions

### 1. Single orchestrator module, no class hierarchy

A single module `libs/beacon/src/beacon/domains/warehouse/lint.py` exports one entry point:

```python
def lint_warehouse(warehouse_path: Path) -> LintReport: ...
```

`LintReport` is a frozen dataclass holding an ordered list of `LintFinding`. `LintFinding` is `(artifact_path: str, message: str)` where `artifact_path` is warehouse-relative (`"skills/foo/SKILL.md"`), and `message` is a single human-readable line (no leading `error:` — the CLI formatter adds that prefix).

**Why a function, not a class?** Each rule is stateless. There is no shared mutable state. A class would just be a bag of static methods. Following the precedent of `compute_effective_set` (also a free function) over `WarehouseUpgrader` (which owns mutable state and cross-step caching).

**Alternative considered:** A `Linter` class with one method per rule. Rejected because every rule is pure `(warehouse_path) → list[LintFinding]` — no state to encapsulate. Adding a class would force test setup boilerplate without buying anything.

### 2. Each rule is a private helper that returns findings; the orchestrator concatenates

The module exposes one public function but internally splits responsibilities one rule per private helper:

```python
def _lint_structure(...)         -> list[LintFinding]
def _lint_skill_frontmatter(...) -> list[LintFinding]
def _lint_skill_requires(...)    -> list[LintFinding]
def _lint_agent_manifest(...)    -> list[LintFinding]
def _lint_agent_frontmatter(...) -> list[LintFinding]
def _lint_knowledge_links(...)   -> list[LintFinding]
```

`lint_warehouse` calls every helper, concatenates the findings in a fixed order, and returns the report. Helpers never raise; if a primitive they call raises, the helper catches and converts to findings.

**Rationale:** Each helper is independently unit-testable against a fixture warehouse with one defect class. The orchestrator's test surface shrinks to "every helper got called, results concatenated in declared order" — a single integration test against a multi-defect fixture covers it.

### 3. Aggregate, don't short-circuit

The structural preflight (`WarehouseValidator.validate`) and the manifest validators do not block the rest of the run. If `WarehouseValidator` returns `valid=False`, lint records each error string as a finding scoped to the path it names (or to `"<warehouse>"` for warehouse-level findings like "Missing required directory: docs/") and proceeds.

If `load_agent_manifest` raises (e.g. unparseable YAML), the agent-rule helpers record one finding against `agents/agents.yaml` and skip the dependent checks (`validate_agents_directory`, `validate_declared_skills`) — those require a parsed manifest to do anything useful. `validate_agent_frontmatter_clean` and the new `_lint_agent_frontmatter` rule still run, because they only need `agents/*.md` files.

**Why aggregate?** Forcing developers to fix-push-repeat for every defect class burns wall-clock CI time and obscures the actual repair scope. The recent `delegate-to-cc` PR would have surfaced both the missing frontmatter AND the broken knowledge link in one run.

**Alternative considered:** Bail at first error class. Rejected — it inverts the value proposition of running lint at all (vs. just running `abc sync` against a synthetic project).

### 4. Knowledge-link rule reimplements the scan loop instead of reusing `scan_file_for_knowledge`

`_lint_knowledge_links` walks `contexts/*.md` and `skills/*/SKILL.md` and, for each, calls `extract_markdown_links` → `resolve_link` → `classify_knowledge_ref` directly. It emits a finding whenever a knowledge-classified link resolves to a non-existent path. It does NOT call `scan_file_for_knowledge`.

**Why not reuse `scan_file_for_knowledge`?** Two reasons:

- It returns a `set[str]` of resolved knowledge refs (including broken ones), losing the source-file association — every finding must say which file the broken link came from, so we need per-source-file iteration anyway.
- It calls `logger.warning` for broken targets. Changing that to an error would either modify the primitive (out of scope per proposal) or require the lint module to capture log output, which is ugly.

The compromise: lint owns its own scan loop, but reuses every *helper below* `scan_file_for_knowledge` — the link extractor, the resolver, the classifier. Those helpers ARE shared, so the parse/resolve semantics cannot drift.

**Alternative considered:** Modify `scan_file_for_knowledge` to return `list[ResolvedKnowledgeRef]` with source-file and existence flag. Rejected — touches a primitive currently shared with `compute_effective_set`, expanding blast radius for no gain.

### 5. New rules live in `lint.py`, not in shared primitives

Two rules in this change are net-new:

- `_lint_agent_frontmatter` (require `name` + `description` on every `agents/*.md` excluding README).
- `_lint_skill_requires_resolve` (every name in `requires.contexts` exists as `contexts/<name>.md`).

Neither is consumed elsewhere in Beacon today. Both stay private to `lint.py`. If a future caller needs them, they can be promoted then — premature reuse would force interface decisions we don't have evidence for yet.

### 6. Error-message preservation from raising primitives

When a manifest validator raises `AgentManifestError("line1\nline2")`, the rule helper splits the message on `\n` and emits one finding per line, all scoped to the artifact path the rule covers. This means a single raised exception fans out to N findings — same shape as native multi-error rules.

This relies on a stable convention: the raising validators format multi-defect messages with `\n` between defects. That convention is currently honoured by `validate_agents_directory`, `validate_agent_frontmatter_clean`, and `validate_declared_skills`. If a future primitive uses a different separator, the lint output degenerates to one mega-finding — undesirable but not silent (the message is still shown).

**Mitigation:** A unit test will pin a fixture warehouse with two missing-manifest-entry agents and assert two findings are emitted (not one combined finding).

### 7. CLI handler mirrors `warehouse_template-upgrade` precedent

```python
@warehouse.command(name="lint")
@click.argument(
    "warehouse_path",
    # No exists=True / file_okay=False: lint_warehouse + WarehouseValidator
    # already emit structured findings for missing or file-typed paths
    # ("Path not found", "Path is not a directory"). Letting Click reject
    # before lint runs would short-circuit the documented exit-1 finding
    # flow. (Updated after opencode-review PR #144 round-3 finding L1.)
    type=click.Path(path_type=Path),
    required=False,
    default=None,
)
def warehouse_lint(*, warehouse_path: Path | None) -> None:
    target = warehouse_path or Path.cwd()
    report = lint_warehouse(target)
    _print_lint_report(report)
    sys.exit(1 if report.findings else 0)
```

`_print_lint_report` lives in `cli/warehouse.py` (a formatting concern). It uses a Rich `Console`, groups findings by `artifact_path`, sorts groups by path, sorts findings within a group by message, prints each finding as `[red]error:[/red] {message}`, and prints a green success summary when the report is empty.

The CLI handler is a thin parse → call → format → exit; no logic. The `tests/unit/test_architecture.py` thinness check covers this.

### 8. Optional path argument, no `--strict` / `--warnings-as-errors` flag

There are no warnings under the lint's purview — every defect is an error per the proposal's scope. So no flag to escalate warnings is needed in v1. If we later add an orphan-detection rule (currently out of scope) and want it as warning-only, we revisit. The handler stays minimal until then.

### 9. Testing strategy

**Unit tests** (`libs/beacon/tests/unit/domains/warehouse/test_lint.py`):

- One fixture warehouse per rule, exercising the happy path + each defect scenario from `specs/warehouse-lint-command/spec.md`.
- Helpers tested directly: `_lint_skill_frontmatter` called with a fixture warehouse whose only defect is a missing frontmatter block; assert exactly one finding scoped to the expected path with the expected message prefix.
- Orchestrator-level test using a multi-defect fixture warehouse: assert findings from every helper appear, grouped/ordered as documented.

**Integration test** (`libs/beacon/tests/integration/domains/warehouse/test_lint_cli.py`):

- Builds a multi-defect fixture warehouse, runs `abc warehouse lint <path>` via subprocess, asserts exit code 1, asserts stdout contains the per-artifact group headers and the `error:` lines.
- One subprocess invocation against a clean fixture warehouse, asserts exit code 0.

**Regression test** (lives with the unit tests): a fixture warehouse where `skills/delegate-to-cc/SKILL.md` exists with no frontmatter block, mirroring the exact PER-114 regression. Asserts the specific error message from `parse_frontmatter` (`"File has no YAML frontmatter (must start with ---)"`) is surfaced verbatim, scoped to that path.

### 10. Versioning and rollout

This is a backwards-compatible addition (no existing CLI surface, capability, or primitive changes). Release-please will cut a minor version of `agentic-beacon` once merged. The cross-repo follow-up PR in `hl-knowledge-market` pins to that version via `uvx agentic-beacon==<pinned>`.

## Impacted Repositories

This change is scoped narrowly. Two repositories are affected; one is modified directly by this OpenSpec change, the other is modified by a separate follow-up PR documented here.

| Repository | Role in this change | Branch |
|---|---|---|
| `agentic-beacon` | Ships the `abc warehouse lint` CLI command, lint module, tests, docs. **All work under this OpenSpec change happens here.** | `warehouse-lint-cli-for-ci` |
| `hl-knowledge-market` | Adopts the new command via a CI workflow + migrates existing artifacts to pass it. **Not modelled in this change's tasks** — separate PR after `agentic-beacon` releases. | `warehouse-lint-cli-for-ci` (mirrored name) on the warehouse repo |

### `agentic-beacon` (this repo, this change)

- New: `libs/beacon/src/beacon/domains/warehouse/lint.py` — orchestrator + private rule helpers.
- New: `libs/beacon/src/beacon/cli/warehouse.py` — `warehouse_lint` Click handler + `_print_lint_report` formatter.
- New: `libs/beacon/tests/unit/domains/warehouse/test_lint.py` — per-rule and orchestrator unit tests.
- New: `libs/beacon/tests/integration/domains/warehouse/test_lint_cli.py` — CLI subprocess test against multi-defect fixture.
- Update: `libs/beacon/README.md` — add `warehouse lint` to the command list.
- Update: `site-docs/` — add lint command reference under the warehouse CLI section.
- No changes to: `core/dependencies/`, `core/scanner/`, `domains/warehouse/validator.py`, `cli/sync.py`, or any other existing module.

### `hl-knowledge-market` (separate follow-up PR, NOT in this change's tasks)

A single PR after the `agentic-beacon` release:

1. Migrate every `agents/*.md` (except `README.md`) to include a `name:` and `description:` YAML frontmatter block.
2. Fix the two known broken knowledge links surfaced by lint.
3. Add `.github/workflows/lint.yml`:
   ```yaml
   on:
     pull_request:
     push:
       branches: [main]
   jobs:
     lint:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: astral-sh/setup-uv@v5
         - run: uvx agentic-beacon==<pinned-version> warehouse lint .
   ```
4. (Aspirational, blocked by GitHub plan) Branch protection on `main` requiring the lint check.

This is referenced in this design for completeness only. It is tracked outside the spec-driven workflow because the artifacts that change live in a different repository.

## Risks / Trade-offs

- **[Risk]** The `AgentManifestError` message convention (newline-separated per-defect lines) is not contractually pinned anywhere. A future change to a validator that uses a different separator silently degrades lint output to one combined finding. → **Mitigation**: unit test asserts N findings are emitted from a fixture with N defects of the same class; regression caught at PR time.

- **[Risk]** `scan_file_for_knowledge` and `_lint_knowledge_links` walk overlapping file sets but produce different outputs (set vs. error list). Future divergence in what each treats as a "knowledge link" could leave a class of broken links uncaught by lint. → **Mitigation**: both call `classify_knowledge_ref` from the shared `scanner` module — the classification rule is shared, only the *consumption* differs. Any future change to what counts as a knowledge link lands in `scanner.classify_knowledge_ref` and both sides update together.

- **[Risk]** `abc warehouse lint` runs against a path that is actually a project (`.agentic-beacon/artifacts/` present). `WarehouseValidator` already refuses this case with a clear error, but a user running the wrong command in the wrong directory will see a confusing single-error report. → **Mitigation**: the structural preflight error is unambiguous ("This appears to be a project directory, not a warehouse"). Acceptable.

- **[Risk]** Pinning the CI to `agentic-beacon==<version>` means a warehouse-side PR cannot land lint-passing artifacts that depend on a *newer* rule until the warehouse pin is bumped. → **Mitigation**: that's the desired behaviour. Loosening the pin (e.g. `agentic-beacon>=<version>`) would mean a Beacon release with a stricter rule could fail every open warehouse PR overnight. Pinning is intentional.

- **[Trade-off]** No `--json` output means downstream tooling (GitHub annotations, ReviewDog) cannot parse findings programmatically in v1. Adding it is cheap when a real consumer asks; building it now would be speculative. Decision: defer.

- **[Trade-off]** Branch protection cannot be enforced on the warehouse repo until the GitHub plan changes. The lint workflow is therefore advisory at first — a developer can still merge a red PR. This is an accepted constraint of the current account plan, not a design choice; it is named here so it doesn't get rediscovered later.

## Migration Plan

No data migration. No code migration in this repo (additive change only).

For the cross-repo follow-up in `hl-knowledge-market` (not in this change's tasks):

1. Release `agentic-beacon` with `abc warehouse lint` available.
2. In a single warehouse-side PR: add `name:` + `description:` frontmatter to every `agents/*.md`, fix the two known broken knowledge links, add `lint.yml` pinned to the new Beacon version.
3. Verify CI passes on that PR before merge.
4. When the GitHub plan permits, enable branch protection on `main` requiring the lint check.

Rollback: revert the agentic-beacon PR. The CLI command disappears in the next release; nothing depends on it in this repo. The warehouse-side workflow would then fail on `uvx`, which is the correct failure mode — it would block warehouse merges until either the workflow is removed or Beacon is fixed.

## Open Questions

None. Every PER-114 decision is resolved in the proposal or above. The follow-up cross-repo work is sequenced (release first, then warehouse PR) and named, but tracked outside this OpenSpec change.
