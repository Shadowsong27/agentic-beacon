## Why

Claude Code (v2.1.277 and later) reads a project's `AGENTS.md` natively and expands its `@`
imports, but only when no `CLAUDE.md` exists at or above the working directory. Beacon still
creates `CLAUDE.md` and writes context imports into it, so `AGENTS.md` is never read natively.
The operator decided on 2026-11-02 (AB-106) to deprecate the `CLAUDE.md` wiring fully, with no
shim. Every host in use runs a supported Claude Code version.

## What Changes

- **BREAKING** `abc setup` creates `AGENTS.md` when it is missing and never creates `CLAUDE.md`.
- **BREAKING** `abc sync` (and `abc adopt`, `abc doctor --fix`) reconcile the beacon-owned
  context `@` imports in the root `AGENTS.md` instead of `CLAUDE.md`. Unwiring removes them from
  `AGENTS.md`. Lines that beacon does not own are preserved.
- When a project `CLAUDE.md` or `.claude/CLAUDE.md` exists, the reconcile moves its
  beacon-owned imports into `AGENTS.md`. If the file then holds only `@AGENTS.md`, blank lines or
  HTML comments, it is deleted. Otherwise it is left in place and sync prints a warning.
- `abc doctor` checks `@` import integrity in `AGENTS.md`.
- `abc doctor` reports, as an error, every `CLAUDE.md`, `CLAUDE.local.md` or `.claude/CLAUDE.md`
  in the project root or any ancestor directory (the user's `~/.claude/` excluded), and names the
  path as the reason `AGENTS.md` is ignored.
- Remaining `CLAUDE.md` references are retargeted: harness detection, the gitignore
  tracked-on-purpose list, orchestrator wiring hints, setup/sync CLI output, user docs.
- The dead `wire_contexts_claudecode` and `unwire_context_claudecode` helpers (no production
  callers) are deleted.
- `opencode.json` wiring is unchanged.

## Impact

- Code: `libs/beacon/src/beacon/domains/setup/wiring.py`, `domains/setup/diagnostics.py`,
  `domains/distribution/orchestrator.py`, `domains/artifact/agent.py`, `domains/adoption/apply.py`
  (comment), `core/gitignore.py`, `cli/setup.py`, `cli/sync.py`.
- Tests: the reconcile, sync-wiring, setup, doctor, diagnostics and agent-detection suites.
- Docs: `README.md` and `site-docs/` pages that describe `CLAUDE.md` wiring.
- Users: Claude Code sessions that read `CLAUDE.md` only (versions before 2.1.277, Bedrock/Vertex,
  `managed-only`) lose beacon context wiring. The operator accepted this as unsupported.
- Out of scope: removing `CLAUDE.md` from each repo on the hosts. That is an ops follow-up after
  this ships and `abc` is upgraded.
