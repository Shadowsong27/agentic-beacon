## Context

Facts below were verified on `origin/main` @ `427f4ec` unless a line says otherwise.

- There is no `context` command group. `cli/main.py` registers `warehouse`, `setup`,
  `sync`, `reset`, `list`, `clean`, `status`, `adopt` and `doctor`.
- `abc warehouse list contexts` (`cli/warehouse.py:292`) reads the connected warehouse
  from `.agentic-beacon/config.toml` through `WorkspaceConfig`, then lists the working tree
  with `WarehouseDistributor._list_contexts` (`domains/distribution/distributor.py:369`).
  That helper walks `contexts/` recursively for `*.md`, skips dot-files and `README.md`
  (case-insensitive), and returns warehouse-relative paths such as `contexts/testing.md`.
  `beacon.yaml` names contexts with the same path form.
- `utils/git.py` reads git objects without a checkout: `get_file_hash_at_sha` runs
  `git -C <warehouse> show <sha>:<path>` with a 10 s timeout and returns `None` on failure.
- `core/dependencies/frontmatter.py` has `parse_frontmatter(path: Path)`. It reads a file
  from disk and returns `FrontmatterResult(success, data, error, message)` with error codes
  `file-not-found`, `read-error`, `missing-frontmatter`, `unterminated-frontmatter`,
  `yaml-parse-error`, `invalid-frontmatter`. It has no text-level entry point, so it cannot
  parse a blob read at a SHA.
- `validate_warehouse_path` (`domains/warehouse/warehouse_path.py`) resolves a path to its
  git root and returns `WarehousePathOK | WarehousePathMissing | WarehousePathNotARepo`.
- The global `main` group prints the pending-artifacts alert to stderr only
  (`domains/adoption/pending_alert.py`), and loguru logs to stderr. Stdout is free for JSON.
- `tests/unit/test_architecture.py` forbids I/O calls inside CLI handlers (`run`,
  `read_text`, `load`, …) and forbids free functions in `cli/` (TC9).
- AB-109 (context frontmatter description, lint rule) is in progress and not merged. Its
  plan, on branch `openspec/context-frontmatter-description-lint` @ `9dc534e`, fixes the
  field: a YAML frontmatter key `description`, a non-empty string, the only allowed key
  (its design D3). Its lint scan covers `contexts/**/*.md` except `README.md` (its D5).
- The conductor's workspaces already carry a `config.toml` that points at the canonical
  warehouse clone (`/root/.local/state/conductor/canonical/hl-knowledge-market` in this
  run's workspace).

## Goals / Non-Goals

**Goals:**
- `abc context index` prints a stable JSON index of the contexts at one warehouse commit.
- The output names the full SHA it read.
- A context with no usable description is listed with `""` and a stderr warning.
- Missing warehouse, non-repo path, unknown ref, or no `contexts/` at the ref exit 1.

**Non-Goals:**
- Validating frontmatter. `abc warehouse lint` owns that (AB-109).
- Adding descriptions to warehouse contexts (AB-118, a foreground warehouse item).
- Run-owned context families and `abc warehouse resolve` (AB-113).
- The conductor's selector and its settings (HARN-433).
- Indexing skills, agents or knowledge.
- Changing `abc warehouse list`.

## Decisions

**D1 [planner-decided, H3] JSON output shape.** One JSON object on stdout, printed with
`json.dumps(..., indent=2, ensure_ascii=False)` and a trailing newline:

```json
{
  "warehouse": "/abs/path/to/warehouse",
  "ref": "HEAD",
  "sha": "<40-hex commit sha>",
  "contexts": [
    {"name": "testing", "path": "contexts/testing.md", "description": "..."}
  ]
}
```

- `warehouse` is the resolved absolute git root. `ref` is the value given to `--ref`,
  unchanged. `sha` is the full commit SHA that ref resolved to.
- `contexts` is sorted by `path` (byte order of the git path). Each entry has exactly the
  keys `name`, `path`, `description`, all strings.
- An empty `contexts` list is valid (a `contexts/` holding only `README.md`).
Rejected: (a) a bare JSON array of entries — it has no place to name the SHA, and the
ticket requires the output to name it; (b) JSON Lines — the consumer reads the whole index
at once, and a header line would need its own record type; (c) a `schema_version` key —
the smallest contract that meets the ticket has none, and a later key can be added without
breaking a reader that ignores unknown keys; (d) putting warnings in the JSON — the ticket
puts them on stderr, and a reader would have to filter them.

**D2 [planner-decided, H3] Warehouse location.** `--warehouse PATH` selects the warehouse.
When omitted, the command uses the connected warehouse from
`.agentic-beacon/config.toml` in the current directory, read through `WorkspaceConfig`
exactly as `abc warehouse list` does. The chosen path goes through
`validate_warehouse_path`. With no option and no `config.toml`, the command exits 1:
`error: no warehouse given and none connected (pass --warehouse PATH or run 'abc warehouse connect')`.
Rejected: (a) a positional argument defaulting to the current directory, like
`abc warehouse lint` — run from a project, the current directory is the project, not the
warehouse, so the default would index the wrong repository or fail; (b) connected
warehouse only — the conductor can run from its canonical clone or any directory, and an
explicit path is the plainest contract for a command named in its settings; (c) the
option name `--path` — the output also has a `path` key per entry, and `--warehouse`
names what it selects.

**D3 [planner-decided, H3] Description key and leniency.** The description is the
frontmatter key `description`, per AB-109's plan D3 (branch
`openspec/context-frontmatter-description-lint` @ `9dc534e`). The index reads it leniently,
because lint owns validation:
- frontmatter parses to a dict and `description` is a string with non-whitespace text →
  `description` is that string with leading and trailing whitespace stripped;
- otherwise → `description` is `""` and one stderr warning is printed. Cases: no
  frontmatter, any frontmatter parse error, key absent, value not a string, value empty or
  whitespace-only, blob not valid UTF-8.
- Other frontmatter keys are ignored.
Rejected: (a) failing the whole command on a malformed context — one bad file would blind
the selector to every other context, and the ticket says never drop a context; (b) reusing
AB-109's `ContextFrontmatter` pydantic model — it forbids unknown keys and is not merged,
so importing it would order the merges and turn a lint concern into an index failure;
(c) falling back to the first `# ` heading or the `**Load when:**` line — the ticket names
frontmatter as the source, and a fallback would hide a missing description from AB-118.

**D4 [planner-decided, H3] Ref resolution.** The option is named `--ref`, per the
`warehouse resolve --ref <sha>` convention in AB-113 (run-owned families and warehouse
resolve), as triage recorded (A5). It accepts any commit-ish and defaults to `HEAD`. It is
resolved with `git -C <warehouse> rev-parse --verify --quiet <ref>^{commit}`. Failure exits
1: `error: ref '<ref>' not found in warehouse <path>`.
Rejected: (a) a required `--ref` — the conductor always passes one, but a human running the
command by hand wants the current commit, and the output still names the SHA; (b) SHA-only
input — rejecting branch and tag names adds a check with no reader that needs it.

**D5 File set (per `_list_contexts`, `distributor.py:369`, and AB-109 plan D5).** The index
lists `git ls-tree -r --name-only <sha> -- contexts/` entries that end in `.md`, whose file
name does not start with `.`, and whose file name is not `README.md` (case-insensitive).
Subdirectories are included. If `git ls-tree` returns no entries at all under `contexts/`,
the commit has no `contexts/` directory and the command exits 1:
`error: no contexts/ directory at <sha> in warehouse <path>`.

**D6 [planner-decided, H3] Entry naming.** `path` is the warehouse-relative path,
`contexts/teams/backend.md`, the same form `beacon.yaml` and `abc warehouse list` use.
`name` is the path relative to `contexts/` with the `.md` suffix removed:
`testing`, `teams/backend`.
Rejected: the file stem alone — two subdirectories may hold the same stem, and names must be
unique.

**D7 [planner-decided, H3] Errors, warnings and exit codes.**
- Exit 0 when the index is printed, with or without warnings.
- Exit 1 for: no warehouse given or connected; `config.toml` unreadable; warehouse path
  missing; path not inside a git repository; ref not found; no `contexts/` at the commit;
  `git` not installed or a git call timing out. Stdout is empty on exit 1.
- Every message goes to stderr as one plain line, without Rich markup, so a caller can log
  it unchanged: `error: <message>` and `warning: <path>: <reason>`. Warnings are printed in
  `path` order, before the JSON is written.
- The domain raises one exception type, `ContextIndexError(message)`, defined in
  `domains/warehouse/context_index.py`. The CLI handler catches it, echoes
  `error: <message>` to stderr, and exits 1.
Rejected: distinct exit codes per failure — no reader branches on them; the message names
the cause.

**D8 Placement (per AGENTS.md Domain placement rule and Four-Layer Architecture).**
- `domains/warehouse/context_index.py`: `ContextEntry` and `ContextIndex` dataclasses (per
  python-standards: dataclass for internal carriers), `ContextIndexError`,
  `resolve_index_warehouse(warehouse: Path | None, cwd: Path) -> Path`, and
  `build_context_index(warehouse: Path, ref: str) -> ContextIndex`, which returns entries
  plus a list of warning strings. The warehouse domain owns warehouse reads ("connect /
  validate / catalog").
- A pure function `describe_context(path: str, text: str | None) -> tuple[ContextEntry, str | None]`
  holds D3 and D6, so they are unit-testable without git.
- `utils/git.py` gains three stateless helpers copying `get_file_hash_at_sha`:
  `resolve_commit(repo, ref) -> str | None`, `list_tree_paths(repo, sha, prefix) -> list[str] | None`,
  `read_blob(repo, sha, path) -> bytes | None`. `None` means git failed.
- `core/dependencies/frontmatter.py` gains `parse_frontmatter_text(content: str) -> FrontmatterResult`.
  `parse_frontmatter(path)` keeps its file checks and delegates the parsing to it. Every
  existing result stays identical. It lives in `core/` because skills, agents, lint and now
  the index share it.
- `cli/context.py`: a `context` Click group and an `index` command with `--warehouse` and
  `--ref`. The handler makes one domain call, echoes warnings and the JSON with
  `click.echo`, and holds no other logic. JSON serialisation of the dataclasses is a
  method on `ContextIndex` (`to_dict()`), so `cli/` needs no helper function (TC9).
- `cli/main.py` registers the group with `main.add_command(context)`.

**D9 Reads git objects only.** The index never reads the warehouse working tree, so
uncommitted edits and the checked-out branch do not change the output for a given SHA.
It runs one `git show <sha>:<path>` per context, the pattern of `get_file_hash_at_sha`.

**D10 Docs (per the existing `site-docs/reference/cli.md` layout).** Add an
`abc context index` section and a Quick Reference row. Show the options, the JSON shape from
D1, the warning and error lines from D7, and the exit codes.

## Risks / Trade-offs

- **R1** AB-109 is not merged, so its key could still change. -> Its plan fixes
  `description`. The key is one constant in `context_index.py`. The integration test pins
  it, so a change shows up as a failing test.
- **R2** The index reads committed files at a SHA, so it can differ from
  `abc warehouse list contexts`, which reads the working tree. -> Intended (D9). The docs
  say so.
- **R3** One `git show` per context costs one subprocess each, about 50 today. -> Accept.
  It is well under a second. `git cat-file --batch` is the upgrade if the count grows.
- **R4** `parse_frontmatter` finds the closing `---` anywhere after the opener (AB-109
  plan R2), so an odd file can parse to a wrong dict. -> The result falls under D3: either
  a usable string or `""` plus a warning. The context is still listed.
- **R5** A symlink committed under `contexts/` returns its target path from `git show`, not
  the content. -> It has no frontmatter, so it gets `""` and a warning. Accept.
- **R6** Any stray stdout write breaks the consumer's parse. -> The integration test runs the
  real CLI with a non-empty `pending.yaml` in the working directory and asserts
  `json.loads(stdout)` succeeds.
- **R7** Splitting `parse_frontmatter` could change an existing result. -> The existing
  `tests/unit/core/dependencies/test_frontmatter.py` must pass unchanged.
