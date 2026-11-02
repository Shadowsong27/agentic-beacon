## Why

Conductor runs will pick contexts per run with a cheap selector model (HARN-433, the
Haiku context selector in the HARN Token efficiency epic). The selector needs a short,
machine-readable statement of when an agent needs each context. Today a context file is
plain markdown with no structured metadata, and `abc warehouse lint` checks nothing about
its shape (`site-docs/guides/creating-knowledge-and-contexts.md:77`).

## What Changes

- A context file MAY start with a YAML frontmatter block. The only allowed key is
  `description`: one or two sentences on when an agent needs this context.
- `abc warehouse lint` gains a context-frontmatter rule:
  - **warning** when a context has no frontmatter, or has frontmatter with no `description`;
  - **error** when the frontmatter is malformed (unterminated, bad YAML, not a mapping),
    when `description` is not a non-empty string, or when the frontmatter has an unknown key.
- `abc warehouse lint` gains a warning severity. Warnings print with a `warning:` prefix and
  do **not** change the exit code: exit 0 when there are no errors, exit 1 when there is at
  least one error. This keeps warehouse CI (AB-55) green until every context carries a
  description (AB-118, the warehouse migration).
- Documentation of the field and the new rule in site-docs (contexts guide and the
  `abc warehouse lint` reference).

No harness wiring changes. `abc sync` still writes only paths (`@<path>` lines in
`CLAUDE.md`, path entries in `opencode.json`), so frontmatter cannot change what is loaded.

## Impact

- Code: `libs/beacon/src/beacon/domains/warehouse/lint.py` (finding severity, new rule),
  a new `libs/beacon/src/beacon/domains/warehouse/context_frontmatter.py` (schema),
  `libs/beacon/src/beacon/cli/warehouse.py` (report rendering, exit code).
- Tests: `libs/beacon/tests/unit/domains/warehouse/test_lint.py`,
  `libs/beacon/tests/integration/domains/warehouse/test_lint_cli.py`, plus a wiring test.
- Docs: `site-docs/guides/creating-knowledge-and-contexts.md`, `site-docs/reference/cli.md`.
- Consumers: warehouse CI (`uvx agentic-beacon==<pinned> warehouse lint .`) sees new
  warnings but no new failures for contexts without frontmatter. A context that already
  has frontmatter with other keys would start failing; none is known (see design R1).
- Follow-on: AB-118 (warehouse migration, adds a description to every context) runs after
  this merges and a release is published. AB-116 (`abc context index`) can reuse the schema.
