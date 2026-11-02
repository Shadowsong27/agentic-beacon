## Context

Facts below were verified on `origin/main` @ `427f4ec`.

- `LintFinding` has only `artifact_path` and `message` (`domains/warehouse/lint.py:40`).
  Every finding is an error. `warehouse_lint` exits `1 if report.findings else 0`
  (`cli/warehouse.py:660`) and `_print_lint_report` prints every finding as `error:`.
- `parse_frontmatter` (`core/dependencies/frontmatter.py`) returns a `FrontmatterResult`
  with error codes `missing-frontmatter`, `unterminated-frontmatter`, `yaml-parse-error`,
  `invalid-frontmatter`, `read-error`. Skills and agents already use it.
- `_lint_agent_frontmatter` (`lint.py:320`) is the closest existing rule: it iterates
  `agents/*.md`, skips `README.md`, and reports missing required keys.
- `abc warehouse init` seeds `contexts/README.md` from `data/templates/contexts/README.md`.
  That file is documentation, not a context.
- Context wiring (`domains/setup/wiring.py`, `wire_contexts_opencode` and
  `wire_contexts_claudecode`) walks `contexts_dir.rglob("*.md")` and writes only paths. It
  never reads a context's content. Subdirectory contexts are supported and documented
  (`creating-knowledge-and-contexts.md`, `contexts/teams/backend.md` example).
- The `abc adopt` description (`domains/adoption/discovery.py`,
  `extract_heading_description`) takes the first `# ` heading line. A frontmatter block with
  only a `description:` key has no such line, so the adopt TUI is unaffected.
- The `contribute-warehouse` bundled skill stops when `abc warehouse lint` exits non-zero.
  Warehouse CI runs the same command. Both read the exit code only.

## Goals / Non-Goals

**Goals:**
- A context can carry `description` frontmatter, validated by `abc warehouse lint`.
- Missing description warns; malformed frontmatter or an unknown key errors.
- Frontmatter changes nothing that `abc sync` writes or that a harness loads.
- The field and rule are documented in site-docs.

**Non-Goals:**
- Adding descriptions to warehouse contexts. That is AB-118, a foreground warehouse item.
- A `--strict` mode that fails on warnings. That is AB-9.
- Changing the `record-knowledge` bundled skill to emit a description, the warehouse init
  template, or the `abc adopt` description source.
- Any reader of the field (the HARN-433 selector, AB-116 `abc context index`).

## Decisions

**D1 [planner-decided, H3] Severity is a field on `LintFinding`; warnings never fail the
run.** Add `severity: Literal["error", "warning"] = "error"` to `LintFinding`. Add
`LintReport.errors` and `LintReport.warnings` (tuples filtered by severity).
`LintReport.__bool__` returns `bool(self.errors)`. The CLI exits `1 if report.errors else 0`.
The default `"error"` keeps every existing rule and call site unchanged.
Rejected: (a) a separate `warnings` tuple on `LintReport` beside `findings` — two
collections for one concept, and every rule would need to know which list to return into;
(b) warnings fail the run — every warehouse CI turns red the day the release ships, before
AB-118 can land, and AB-9 already owns the opt-in strict mode.

**D2 [planner-decided, H3] Rendering.** Findings stay grouped by artifact path in the
existing sorted order. Each line is prefixed `error:` (red) or `warning:` (yellow). The
summary line is:
- no findings: `✓ Lint passed.` (unchanged);
- warnings only: `✓ Lint passed with N warning(s) across K file(s).`, after the grouped
  warnings;
- any error: `Found N error(s) and M warning(s) across K file(s).` (`and M warning(s)`
  omitted when M is 0, so the existing error-only output is unchanged).
Messages stay routed through `rich.markup.escape()` as today.
Rejected: printing warnings in a separate block after errors — it splits one file's
findings across two places and changes the existing grouped layout.

**D3 [planner-decided, H3] Frontmatter schema.** A new pydantic model
`ContextFrontmatter` with `model_config = ConfigDict(extra="forbid")` and
`description: str | None = None`. A validator rejects a `description` that is present but
empty or whitespace-only. `extra="forbid"` produces the unknown-key error. Pydantic's
type check produces the not-a-string error (`strict` string, so `description: 3` errors
rather than coercing). Allowed keys: `description` only. No length limit is enforced; the
docs say "one or two sentences".
Rejected: (a) `allow` extra keys — the ticket requires an error on an unknown key, and a
typo such as `desciption:` would otherwise pass silently while the selector sees nothing;
(b) a hard character limit — not in the ticket, and any number would be arbitrary until
the selector shows a need.

**D4 [planner-decided, H3] Rule mapping.** `_lint_context_frontmatter(warehouse_path)`
calls `parse_frontmatter` per context file:
- `missing-frontmatter` → one **warning**: `missing frontmatter description (add a YAML
  frontmatter block with a \`description\` key)`;
- any other parse failure → one **error** with `result.message`;
- parse succeeds → validate with `ContextFrontmatter`. Each validation error → **error**,
  formatted like `_lint_skill_frontmatter` does (`<field>: <msg>`). If valid and
  `description` is `None` → one **warning**: `missing required key \`description\` in
  frontmatter`.
Rejected: treating "no frontmatter" as an error — the ticket says a missing description
warns, and every context in today's warehouses has no frontmatter.

**D5 [planner-decided, H3] Scan scope.** The rule covers every `*.md` under `contexts/`,
recursively, except files named `README.md`. Artifact paths are warehouse-relative
(`contexts/teams/backend.md`).
Rejected: top level only, as `_iter_artifact_markdown_files` does for links — context
wiring uses `rglob` (`wiring.py`), so a subdirectory context is loaded by projects and
would be read by the selector, but would escape the description check. Linting
`README.md` was rejected because the init template seeds `contexts/README.md` as docs, and
a fresh `abc warehouse init` warehouse must still print `✓ Lint passed.` with exit 0
(`site-docs/reference/cli.md`); this copies the `README.md` skip in
`_lint_agent_frontmatter` (`lint.py:330`).

**D6 Placement (per AGENTS.md Domain placement rule).** `ContextFrontmatter` lives in
`domains/warehouse/context_frontmatter.py` because only the warehouse domain reads it.
`_lint_context_frontmatter` lives in `lint.py` directly after `_lint_agent_frontmatter`
and is called from `lint_warehouse` after it, copying the existing rule-per-function
pattern. If AB-116 needs the model from another domain, it moves it to `core/` then.
`parse_frontmatter` is reused unchanged.

**D7 No wiring change; prove it with a test.** `abc sync` writes only paths, so
frontmatter cannot alter loading. A unit test runs context wiring for a context with and
without frontmatter and asserts identical `CLAUDE.md` `@` lines and `opencode.json`
instruction entries. Whether a real harness `@` import tolerates a frontmatter block is a
real-agent behaviour, so it is verified end to end with a real `claude -p` run whose
result is recorded in the PR (per testing context, Test Tiers), not by a test with fakes.

**D8 Docs (per the existing docs layout).** `site-docs/guides/creating-knowledge-and-contexts.md`
gets a "Context frontmatter" subsection under Contexts (field, example, when to write
one, lint behaviour), and line 77 is corrected: lint still does not enforce naming or
layout, but it does check frontmatter. `site-docs/reference/cli.md` gets rule 7 in the
`abc warehouse lint` rule list and the updated exit-code text (warnings never change the
exit code). The `warehouse_lint` docstring is updated to match.

## Risks / Trade-offs

- **R1** A warehouse context that already starts with frontmatter carrying other keys
  starts failing lint with an unknown-key error. -> None is known: the six contexts wired
  into this repo have no frontmatter, and the AB-109 triage counted 50 warehouse contexts
  with a `Load when:` line and no frontmatter. AB-118 runs lint over the full warehouse
  before it commits. The error message names the key, so the fix is obvious.
- **R2** `parse_frontmatter` treats a file whose first non-blank line is `---` (a markdown
  horizontal rule) as frontmatter, and finds the first later `---` anywhere as the closer.
  -> Such a context gets an error, not a silent pass. Accept; do not change the shared
  parser in this change.
- **R3** A YAML comment line `# ...` inside frontmatter would be read as the first heading
  by `extract_heading_description` (adopt TUI) and by heading extraction for anchors. ->
  Cosmetic only. Docs show frontmatter without comments.
- **R4** Changing `LintReport.__bool__` semantics could break a caller that uses truthiness
  to mean "has findings". -> The only callers are `_print_lint_report` and
  `warehouse_lint` (`git grep LintReport origin/main`), both updated here. Existing tests
  that build a report of default-severity findings keep their meaning.
- **R5** Warnings are easy to ignore. -> Intended until AB-118 lands; AB-9 adds the strict
  switch.
