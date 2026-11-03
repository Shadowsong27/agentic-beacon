## Context

Facts below were verified on agentic-beacon `origin/main` @ `3bf855a`, agentic-conductor
`origin/main` @ `909977d`, and the warehouse (hl-knowledge-market) canonical clone @
`fc0dea4`, unless a line says otherwise.

**What beacon has today.**
- `abc context index` (AB-116, change `context-index-command`) is the model:
  `cli/context.py` holds a `context` Click group with one `index` command;
  `domains/warehouse/context_index.py` holds `ContextIndexError`,
  `resolve_index_warehouse(warehouse, cwd)` (an explicit `--warehouse` or the connected
  warehouse from `.agentic-beacon/config.toml`, then `validate_warehouse_path`),
  `build_context_index`, and the file filter `_is_context_path` (`.md`, not a dot-file,
  not `README.md`). It exits 1 on every error and prints `error: <message>` on stderr.
- `utils/git.py` has `resolve_commit(repo, ref)`, `list_tree_paths(repo, sha, prefix)` and
  `read_blob(repo, sha, path)`. Each returns `None` on any git failure. `read_blob` also
  returns `None` for a path absent at the SHA, so it cannot tell "missing" from
  "unreadable". `list_tree_paths` can: `[]` means git succeeded and found nothing.
- `core/dependencies/frontmatter.py` has `parse_frontmatter_text(content)`. It finds the
  closing `---` anywhere after the opener (`remainder.find("---")`) and returns the data
  only, not the body.
- `domains/setup/wiring.py` owns `AGENTS.md` wiring (AB-106). `ARTIFACT_REF_PREFIX =
  ".agentic-beacon/artifacts/"`, `_ATPATH_LINE_RE = ^@(.+)$` matched against
  `line.strip()`, and `_strip_owned_refs(content)` returns the owned refs as a **set** plus
  the kept lines. Owned = an `@` line whose path starts with `ARTIFACT_REF_PREFIX`.
- There is no `agent` or `project` Click group. `cli/agent.py` holds only `list_cmd`,
  registered as top-level `abc list`.
- `tests/unit/test_architecture.py` forbids I/O in CLI handlers, free functions in `cli/`,
  more than one domain call per handler, underscore-prefixed names imported across
  modules (TC6), and domain imports deeper than `beacon.domains.X.Y`.

**What the conductor reads today** (each is one item of the ticket).
- Context bodies: `runner/context_select.py:113` `_git_show(warehouse, sha, path)`.
- The selector prompt: `SELECTOR_DEFINITION_PATH = "agents/context-selector.md"`
  (`context_select.py:29`), then `_strip_frontmatter` (`:126`): drop a leading block from a
  first line `---` to the next line that strips to `---`; no closing line leaves the text
  unchanged. HARN-850 (agents as plugins) needs other agent definitions too.
- Intake policy: `settings.py:438` `policy_path = "contexts/intake-policy-{board}.md"`,
  read in `launch_supervisor.py:3533` `_read_intake_policy`.
- Operate profile: `settings.py:439` `profile_path = "contexts/operate-{domain}.md"`.
- Decision rules: `launch_supervisor.py:3586` `_decision_rules_section` and `:3611`
  `_read_decision_rules`. It runs `git grep -l "^## Decision rules"` over `contexts/` at the
  SHA, takes the body under the first line that starts with `## Decision rules`, up to the
  next line starting `## ` or a line equal to `---`, drops leading and trailing blank lines,
  and keys the section by the file stem. Six warehouse contexts carry one today.
- Repo instructions: `runner/repo_instructions.py` `strip_import_lines` removes `@` lines
  whose path (after an optional `./`) starts with a configured prefix (default
  `.agentic-beacon/artifacts/`, `settings.py:353`), trims trailing blanks, and the launcher
  reads `AGENTS.md` from the **working tree** (`launch_supervisor.py:1224`), not a ref.

**Warehouse layout.** `contexts/intake-policy-{AB,HARN,HT,WP}.md`,
`contexts/operate-<domain>.md` (nine domains, e.g. `airflow-platform`, `watchlist-pulse`),
`agents/<name>.md` with YAML frontmatter (`name`, `description`, `mode`), plus
`agents/agents.yaml` and `agents/_partials/` that are not agent definitions.

## Goals / Non-Goals

**Goals:**
- One `abc` read command per ticket item, each with the AB-116 contract: a path and a
  `--ref`, committed content only, JSON on stdout that names the SHA, no writes.
- A missing item exits 3. An unreadable source exits 1. The two never share a code.
- Beacon owns every path convention and every format rule the conductor uses today, so
  the conductor can drop its own.

**Non-Goals:**
- Migrating the conductor to these commands (agentic-conductor tickets).
- Run-owned context families and their lint (AB-113 keeps them).
- Changing `abc context index` output or its exit codes.
- Resolving agent `_partials` links or reading `agents/agents.yaml`.
- Validating frontmatter. `abc warehouse lint` owns that.
- Batching many reads into one git process (R3).

## Decisions

**D1 [planner-decided, H3] Command names and groups.**

| Ticket item | Command |
|---|---|
| Context bodies | `abc context show NAME...` |
| Intake policy | `abc context intake-policy BOARD` |
| Operate profile | `abc context operate-profile DOMAIN` |
| Decision rules | `abc context decision-rules` |
| Agent definitions (incl. the selector prompt) | `abc agent show NAME...` |
| Repo project instructions | `abc project instructions` |

The four context commands join the existing `context` group, because each reads
`contexts/`. `agent` and `project` are new groups. `abc list` (`list_cmd`) stays a
top-level command and is not moved.
Rejected: (a) one `abc read <kind> <name>` group — it splits the context reads from
`abc context index`, their model, and gives one handler six output shapes; (b) only
`abc context show` with the conductor passing `intake-policy-AB` — the conductor would
still own the `intake-policy-{board}` and `operate-{domain}` naming, which DR5 moves to
beacon; (c) `abc warehouse resolve` (the name AB-113 used) — "resolve" does not say what is
printed, and the six items have different arguments.

**D2 [planner-decided, H3] Common options and warehouse location.** Every warehouse
command takes `--warehouse PATH` (default: the connected warehouse) and `--ref REF`
(default `HEAD`), resolved exactly as `abc context index` does, by calling
`resolve_index_warehouse` and `resolve_commit`. `abc project instructions` takes
`--repo PATH` (default `.`) and `--ref REF` (default `HEAD`); the path goes through
`validate_warehouse_path`, which resolves any path to its git root.
Rejected: a required `--ref` — a human running the command wants the current commit, and
the output names the SHA anyway (AB-116 D4).

**D3 [planner-decided, H3] Exit codes.**
- `0` — the item was read and printed.
- `1` — the source is unreadable: no warehouse given or connected, path missing, not a git
  repository, ref not found, git missing or timing out, git failing on an item it listed,
  a blob that is not valid UTF-8, no `contexts/` (or no `agents/`) directory at the SHA.
- `2` — usage error. This is Click's own code for a bad option or argument; the name
  checks in D4 raise `click.BadParameter` so they land here too.
- `3` — the requested item is missing at the SHA: a context, policy, profile or agent
  file, or `AGENTS.md`.
Stdout is empty for every non-zero exit. The message is one plain line on stderr:
`error: <message>`. A missing item names every missing name and the SHA:
`error: missing at <sha>: contexts/foo.md, contexts/bar.md`.
Rejected: (a) exit 2 for missing — Click already uses 2 for usage errors, so a caller
could not tell a typo in an option from a missing file; (b) a `found: false` JSON field
with exit 0 — the ticket asks for a non-zero exit; (c) treating "ref not found" as
missing — the item may exist, the clone simply lacks the commit, which is a source problem.

**D4 [planner-decided, H3] Name checks.** BOARD and DOMAIN must match
`^[A-Za-z0-9][A-Za-z0-9_-]*$`. A context NAME is the index name (AB-116 D6): one or more
`/`-separated segments, each matching `^[A-Za-z0-9][A-Za-z0-9._-]*$` and not `..`, with no
`.md` suffix. An agent NAME is one segment matching the context segment pattern. A failing
name exits 2 (D3). Names are case-sensitive, as git paths are.
Rejected: accepting a `.md` suffix or a full path — two spellings for one item; the index
already gives callers the canonical name.

**D5 [planner-decided, H3] File record.** Every command that returns a file uses one record:

```json
{"name": "context-selector", "path": "agents/context-selector.md",
 "text": "<the whole file>", "frontmatter": {"name": "..."} , "body": "<text after frontmatter>"}
```

- `text` is the committed blob decoded as UTF-8, unchanged.
- `frontmatter` and `body` come from one line-based split, the rule the conductor uses
  (`context_select.py:126`): when the first line (after a BOM) is `---` and a later line
  strips to `---`, the lines between are parsed with `yaml.safe_load`, and `body` is every
  line after the closing line. If that YAML parses to a dict, `frontmatter` is the dict.
- No frontmatter block (no opener, or no closing line): `frontmatter` is `null`, `body`
  equals `text`, no warning.
- A block that fails to parse or is not a dict: `frontmatter` is `null`, `body` is still
  the text after the closing line, and one stderr line `warning: <path>: <reason>` is
  printed. The exit stays 0.
- A frontmatter value that YAML parses to a non-JSON type (a date) is converted with
  `str()` so `json.dumps` cannot fail.

The split is a new function in `core/dependencies/frontmatter.py`,
`split_frontmatter(text) -> FrontmatterSplit(frontmatter, body, warning)`.
`parse_frontmatter_text` is not changed.
Rejected: (a) `text` only — the conductor would keep parsing a beacon format, which DR5
removes; (b) reusing `parse_frontmatter_text` — it finds the closing `---` anywhere, not on
its own line, so its data and a line-based body could disagree on one file; (c) failing the
command on bad frontmatter — the body is still usable, and lint owns validation.

**D6 [planner-decided, H3] Output shapes.** One JSON object, `json.dumps(...,
indent=2, ensure_ascii=False)`, trailing newline. Every warehouse command starts with
`"warehouse"` (resolved git root), `"ref"` (as given) and `"sha"` (full commit SHA).
- `context show` → `"contexts": [record, ...]`, in the order the names were given;
  a name given twice is printed once, at its first position.
- `context intake-policy` → `"board": "<BOARD>", "policy": record`;
  path `contexts/intake-policy-<BOARD>.md`, record name `intake-policy-<BOARD>`.
- `context operate-profile` → `"domain": "<DOMAIN>", "profile": record`;
  path `contexts/operate-<DOMAIN>.md`.
- `agent show` → `"agents": [record, ...]`, same ordering rule; path `agents/<NAME>.md`.
- `context decision-rules` → `"rules": [{"name", "path", "body"}, ...]` (D7).
- `project instructions` → `{"repo", "ref", "sha", "path": "AGENTS.md", "text",
  "removed": [...]}` (D8).
For `show` with several names, any missing name fails the whole call with exit 3 and
names all of them; nothing is printed on stdout.
Rejected: (a) a bare array — no place for the SHA; (b) a `schema_version` key — not
needed now, and a reader that ignores unknown keys survives a later addition (AB-116 D1).

**D7 [planner-decided, H3] Decision-rules extraction.** Copy the conductor's algorithm
exactly, so the migration changes no rule text:
- Files: every context at the SHA, using the index file filter (`_is_context_path`, made
  public as `is_context_path`), sorted by path.
- Section: the first line that starts with `## Decision rules`. The body is every following
  line up to, not including, the next line that starts with `## ` or a line equal to `---`,
  or the end of file. Leading and trailing blank lines are dropped; lines are joined with
  `\n` and no trailing newline is added.
- A context with no such heading is left out. A heading with an empty body is included with
  `"body": ""`.
- `name` is the index name (`contexts/teams/x.md` → `teams/x`), not the bare stem the
  conductor uses. For every context in the warehouse today the two are equal (no context
  with a rules section is in a subdirectory).
- No context with a rules section: exit 0 with `"rules": []`. The conductor treats "no
  rules" as normal, so it is not a missing item.
- The section is not further parsed into `DR<n>` entries.
Rejected: (a) splitting into one entry per `**DR<n>**` — the conductor renders the
section whole, and the DR format is prose, not a contract; (b) `git grep` to find files —
the index already lists every context; one rule set for "what is a context" is simpler.

**D8 [planner-decided, H3] Project instructions.** Reads `AGENTS.md` at the repo root at
the ref. It removes the beacon-owned import lines by beacon's own rule (`wiring.py`): a line
whose `strip()` matches `^@(.+)$` and whose path, stripped, starts with
`ARTIFACT_REF_PREFIX`. Then runs of three or more newlines collapse to two (the rule
`_plan_claude_md_migration` uses), trailing blank lines are dropped, and the text ends
with one `\n`, or is `""` when nothing is left. `removed` lists the removed paths in file
order, duplicates kept, so `len(removed)` equals the conductor's removed count.
- The splitter is a new public function in `domains/setup/wiring.py`,
  `split_owned_imports(content) -> tuple[list[str], list[str]]` (ordered refs, kept lines).
  `_strip_owned_refs` becomes `set(refs)` over it, so the two can never disagree. The
  reader lives in `domains/setup/project_instructions.py`, because the setup domain owns
  `AGENTS.md` wiring.
- `AGENTS.md` missing at the ref → exit 3. Only the root `AGENTS.md` is read; `CLAUDE.md`
  is not (AB-106: beacon writes `AGENTS.md` only).
- The prefix is beacon's constant, not an option. The conductor's
  `instruction_import_prefixes` setting has one default entry, equal to this constant.
- The `./` form the conductor also strips is not beacon-owned (beacon never writes it), so
  it is kept. See R4.
Rejected: (a) reading the working tree — the ticket requires committed content; (b) a
`--prefix` option — the conductor would keep naming a beacon path, which DR5 removes.

**D9 Placement (per AGENTS.md Domain placement rule; context-index-command D8).**
- `domains/warehouse/warehouse_read.py`: `WarehouseReadError(Exception)` and
  `ItemMissingError(WarehouseReadError)` carrying the missing paths; the file-record and
  result dataclasses, each with `to_dict()`; `read_contexts`, `read_intake_policy`,
  `read_operate_profile`, `read_decision_rules`, `read_agents`, and the pure
  `decision_rules_section(text) -> str | None`. It calls `resolve_index_warehouse` and
  re-raises `ContextIndexError` as `WarehouseReadError`.
- `domains/setup/project_instructions.py`: `read_project_instructions(repo, ref)`, raising
  the two error types from `warehouse_read.py` (a depth-4 cross-domain import, allowed).
- Missing vs unreadable uses `list_tree_paths(repo, sha, path)` per item: `None` → exit 1,
  no exact match in the list → exit 3, then `read_blob`; a `None` there → exit 1. No new
  git helper.
- `cli/context.py` gains four handlers; `cli/agent.py` gains an `agent` group with `show`;
  new `cli/project.py` holds a `project` group with `instructions`; `cli/main.py` registers
  both groups. Each handler makes one domain call, catches `ItemMissingError` (exit 3)
  before `WarehouseReadError` (exit 1), echoes warnings, then the JSON.

**D10 Committed content only, no writes (per context-index-command D9).** Every read goes
through `git ls-tree` and `git show <sha>:<path>`. No command opens a file in the working
tree, writes a file, or changes git state. The integration tests assert both: an
uncommitted edit does not change the output, and the repo's `git status --porcelain` is
unchanged after each command.

**D11 Docs (per site-docs/reference/cli.md layout).** Extend the "Context Commands"
section with the four context commands, add "Agent Commands" and "Project Commands"
sections, add Quick Reference rows, and document the exit-code table from D3 once, shared
by all read commands.

## Risks / Trade-offs

- **R1** The record name for decision rules differs from the conductor's file stem for a
  context in a subdirectory. -> No such context has a rules section today. The conductor
  migration ticket reads `name` from the JSON and must not rebuild it.
- **R2** `split_frontmatter` and `parse_frontmatter_text` can disagree on a file whose
  frontmatter contains `---` inside a value. -> The read commands use only
  `split_frontmatter`. `abc context index` keeps its parser, so its `description` and
  `context show`'s `frontmatter.description` can differ on such a file. Accept: no
  warehouse file has this today, and lint will flag it.
- **R3** One `git ls-tree` plus one `git show` per item; `decision-rules` reads every
  context (about 50). -> Well under a second. `git cat-file --batch` is the upgrade.
- **R4** The conductor also strips `@./.agentic-beacon/artifacts/...` lines; beacon keeps
  them. -> Beacon never writes that form. The conductor migration ticket must note the
  difference. A repo with such a line would show it in the inlined instructions, where a
  human can see and delete it.
- **R5** Agent `body` still carries links to `agents/_partials/`. -> Same as today: the
  conductor does not resolve them either. Out of scope.
- **R6** A stray stdout write breaks the JSON. -> The integration test runs each command
  with a non-empty `pending.yaml` and asserts `json.loads(stdout)` (context-index R6).
- **R7** Refactoring `_strip_owned_refs` over `split_owned_imports` could change sync. ->
  Existing `test_sync_wiring.py` and diagnostics tests must pass unchanged.
