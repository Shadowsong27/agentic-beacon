## Why

The conductor's context selector (HARN-433) must choose which warehouse contexts a run
loads. It needs every context's name, path and description, read from the warehouse at
the exact SHA the run pins. The conductor stays beacon-agnostic: it runs a command named
in its settings and parses the output. Today beacon has no command that prints contexts as
data. `abc warehouse list contexts` prints a Rich table of paths from the working tree,
with no description and no ref.

## What Changes

- New command group `abc context` with one command, `abc context index`.
- `abc context index` prints one JSON object to stdout. It names the warehouse, the ref
  asked for, and the full SHA it read. It lists one entry per context under `contexts/` at
  that SHA, with `name`, `path` and `description`.
- `description` comes from the context's YAML frontmatter key `description`, the field
  AB-109 (context frontmatter description, lint rule) defines.
- `--ref <commit-ish>` selects the commit. It defaults to `HEAD`.
- `--warehouse <path>` selects the warehouse. It defaults to the connected warehouse in
  `.agentic-beacon/config.toml`.
- A context with no usable description is listed with `description: ""` and a warning on
  stderr. It is never dropped.
- A missing warehouse, a path that is not a git repository, an unknown ref, or a commit
  with no `contexts/` directory exits 1 with a message on stderr and nothing on stdout.
- `parse_frontmatter` gains a text-level sibling, `parse_frontmatter_text`, so frontmatter
  can be parsed from a blob read at a SHA. `parse_frontmatter` delegates to it. Behaviour
  is unchanged.
- `site-docs/reference/cli.md` documents the command and its JSON shape.

No breaking changes.

## Impact

- Code: `libs/beacon/src/beacon/cli/context.py` (new), `cli/main.py` (register group),
  `domains/warehouse/context_index.py` (new), `utils/git.py` (three read-only helpers),
  `core/dependencies/frontmatter.py` (text-level parser).
- Tests: unit tests for the domain module and the frontmatter split, an integration test
  that runs the command against a real temporary git warehouse.
- Docs: `site-docs/reference/cli.md`.
- Consumers: HARN-433 (conductor context selector) parses the JSON. The shape in
  design D1 is the contract.
- Related: AB-109 (context frontmatter description, lint rule) defines the field. This
  change reads it but does not import AB-109 code, so the two merge in either order.
- No deploy, no migration. The command only reads git objects.
