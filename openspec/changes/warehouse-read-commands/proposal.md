## Why

The conductor reads warehouse content directly today: it runs `git show <sha>:<path>` on
context bodies, the `context-selector` agent, intake policies and operate profiles; it
parses the `## Decision rules` sections of contexts; and it strips beacon's `@` import
lines out of a repo's `AGENTS.md` (HARN-434). That couples the conductor to beacon's file
layout and file formats. The operator decided (2026-11-03, conductor-ops DR5) that beacon
is the only context manager: the conductor reads everything through `abc` at the run's
warehouse SHA and never names a warehouse path or parses a beacon format.

`abc context index` (AB-116) already serves the index this way. This change adds one read
command for each remaining item, with the same contract.

## What Changes

- New `abc context show NAME...`: the committed text of one or more contexts.
- New `abc context intake-policy BOARD`: the board's intake policy context.
- New `abc context operate-profile DOMAIN`: the domain's operate profile context.
- New `abc context decision-rules`: the `## Decision rules` section of every context.
- New `abc agent show NAME...`: one or more agent definitions, frontmatter parsed.
- New `abc project instructions`: a repo's `AGENTS.md` at a ref, with the beacon-owned
  `@` import lines removed.
- Every new command takes a path and `--ref`, reads committed git objects only, prints
  one JSON object that names the SHA it read, never writes, and exits 3 when the
  requested item is missing (distinct from exit 1, the source being unreadable).
- `site-docs/reference/cli.md` documents the six commands.

No existing command changes. `abc context index` keeps its output and exit codes.

## Impact

- Code: new `domains/warehouse/warehouse_read.py`, new
  `domains/setup/project_instructions.py`, a public import-line splitter in
  `domains/setup/wiring.py`, a frontmatter/body splitter in
  `core/dependencies/frontmatter.py`, new handlers in `cli/context.py`, new `cli/agent.py`
  `agent` group, new `cli/project.py`, registration in `cli/main.py`.
- Tests: unit tests per domain module, one integration test file against a fixture git
  warehouse and a fixture project repo.
- Consumers: the conductor (agentic-conductor) moves its readers to these commands in its
  own tickets. That migration is not part of this change.
- Relation: this takes over the `abc warehouse resolve` part of AB-113 (run-owned families
  and warehouse resolve). AB-113 keeps run-owned families in `abc sync` and their lint.
