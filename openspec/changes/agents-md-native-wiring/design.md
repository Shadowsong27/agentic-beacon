## Context

All facts below were read at `origin/main` @ `85b875a`.

- `domains/setup/wiring.py` owns all Claude Code context wiring.
  - `_resolve_claude_md` (L64) picks `.claude/CLAUDE.md`, then `./CLAUDE.md`.
  - `_reconcile_claude_md` (L122) treats every line `@.agentic-beacon/artifacts/...` as owned.
    It strips owned lines, collapses blank runs, and appends the sorted desired set. A missing file
    is a no-op.
  - `reconcile_context_references` (L185) runs the opencode and the CLAUDE.md reconcile. It is the
    only production wiring path. Callers: `distribution/orchestrator.py` L474 (`abc sync`),
    `cli/sync.py` L258 (first-time init), `adoption/apply.py` L255 and L417 (`abc adopt`),
    `setup/diagnostics.py` L168 (`abc doctor --fix`).
  - `init_claude_md` (L370) creates an empty root `CLAUDE.md`. Callers: `setup_project` (L353,
    `abc setup`) and `cli/sync.py` L249 (the `agent_config_init_needed` path).
  - `wire_contexts_claudecode` (L288) and `unwire_context_claudecode` (L502) have no production
    callers. Only `tests/integration/test_sync_wiring.py` calls the first. `unwire_pruned_artifacts`
    does `pass` for contexts, so unwiring a context happens through the reconcile.
- `domains/setup/diagnostics.py` `_check_path_references` (L285) scans `.claude/CLAUDE.md` and
  `./CLAUDE.md` with `_check_claude_md` (L319), which classifies each `@` line.
- Other references: `core/gitignore.py` L77 (`TRACKED_ON_PURPOSE`), `artifact/agent.py` L27
  (`detect_agents` marker), `distribution/orchestrator.py` L480-507 (`has_claude` and two wiring
  hints), `cli/setup.py` L53-54 (output), `adoption/apply.py` L401 (comment).
- Claude Code reads `AGENTS.md` natively only when no `CLAUDE.md` / `CLAUDE.local.md` /
  `.claude/CLAUDE.md` exists in the project or an ancestor. The user's `~/.claude/CLAUDE.md` does
  not block it (ticket comment, 2026-11-02).
- The operator settled the scope on 2026-11-02 (AB-106): full deprecation, no shim, the done-when
  list in the ticket, repo cleanup out of scope.

## Goals / Non-Goals

**Goals:**
- Beacon never creates or writes context imports into `CLAUDE.md`.
- The root `AGENTS.md` carries the beacon-owned context imports.
- Existing projects migrate on the next `abc sync` without manual edits.
- `abc doctor` checks `AGENTS.md` imports and reports any `CLAUDE.md` that hides `AGENTS.md`.

**Non-Goals:**
- Changes to `opencode.json` wiring.
- Removing `CLAUDE.md` from the repos on the hosts (ops follow-up, see Migration Plan).
- Editing files outside the project root. Ancestor files are reported, never changed.
- A `CLAUDE.md` shim for sessions that read `CLAUDE.md` only (operator decision).

## Decisions

**D1 The root `AGENTS.md` is the only Claude Code wiring target.** Per the ticket done-when
("wires the context `@` imports into the root `AGENTS.md`"). No `.claude/AGENTS.md` lookup.
Replace `_resolve_claude_md` with a constant path `project_root / "AGENTS.md"`.

**D2 The reconcile algorithm stays; only the target changes.** Rename `_reconcile_claude_md` to
`_reconcile_agents_md`. Ownership, the blank-run collapse and the sorted append are copied from
`wiring.py` L122-181 unchanged. Non-owned lines (`# headings`, prose, `@other.md`) are preserved.
`reconcile_context_references` still aggregates opencode + Claude results.

**D3 [planner-decided, H3] When the reconcile creates `AGENTS.md`.** A missing `AGENTS.md` is a
no-op, as a missing `CLAUDE.md` is today, with one exception: if the migration (D4) found owned
imports in a `CLAUDE.md`, the reconcile creates `AGENTS.md` so the imports are not lost. The
first-time path (`agent_config_init_needed`) creates it through `init_agents_md` (D10).
- Rejected: always create `AGENTS.md` when the desired set is non-empty. That changes behaviour for
  opencode-only projects, which today get no Claude file from sync.
- Rejected: never create it in the reconcile. Then a project with `opencode.json` and a
  `CLAUDE.md` but no `AGENTS.md` would lose its imports during migration.

**D4 [planner-decided, H3] Migration sources and order.** Inside `_reconcile_agents_md`, before
reconciling `AGENTS.md`, process `./CLAUDE.md` and `./.claude/CLAUDE.md` (the two paths beacon
ever wrote, `_resolve_claude_md` L64). For each that exists:
1. Strip its owned lines (same match as D2). Note whether any were found.
2. Apply the delete test (D5). If it passes, delete the file. Otherwise write the stripped content
   back (only when it changed) and record the path as left.

The migration does not copy the stripped lines. `AGENTS.md` is then reconciled to the desired set,
which already holds every wanted import. Under `dry_run` nothing is written or deleted. Owned
lines found in a `CLAUDE.md` count as a change for the dry-run result. `CLAUDE.local.md` and
ancestor files are never touched. Doctor reports them (D8).
- Rejected: also migrate ancestors. Beacon must not edit files outside the project.
- Rejected: a separate migration step in each caller. All five callers already go through
  `reconcile_context_references`, so putting it there covers sync, adopt and `doctor --fix` at once.

**D5 [planner-decided, H3] The delete test.** After stripping, a `CLAUDE.md` is deleted when every
line, once HTML comments (`<!-- ... -->`, single or multi-line) are removed and the line is
stripped, is empty, `@AGENTS.md` or `@./AGENTS.md`. Any other line (a Markdown heading, a
blockquote, prose, another `@` import) keeps the file.
- Rejected: count `#` lines as comments. In Markdown they are headings, and the operator's rule
  names comments only.
- Rejected: accept any `@` import of an `AGENTS.md` in another directory. It is not the project
  file, so deleting would drop content.

**D6 [planner-decided, H3] A `CLAUDE.md` that resolves to `AGENTS.md`.** If `CLAUDE.md` is a
symlink whose resolved path equals the resolved `AGENTS.md`, skip it in the migration. Stripping
it would strip `AGENTS.md` itself, and deleting it removes a file beacon did not create. Doctor
still reports it (D8).
- Rejected: unlink the symlink. The operator's delete rule covers file content, not links.

**D7 [planner-decided, H3] Reporting a left `CLAUDE.md` from sync.** Add two fields with empty
defaults to `ReferenceReconcileResult`: `claude_md_deleted: tuple[str, ...] = ()` and
`claude_md_left: tuple[str, ...] = ()` (paths relative to the project root). `__bool__` stays
`added or removed`. `reconcile_context_references` carries them through. The orchestrator appends a
note per left path to `wiring_notes` (printed under "Manual wiring required"), naming the path and
saying it stops Claude Code from reading `AGENTS.md` and to run `abc doctor`. It logs each deleted
path with `logger.info`.
- Rejected: a new field on the sync result plus a new CLI block. `wiring_notes` already exists for
  this kind of message.

**D8 [planner-decided, H3] Doctor reports a `CLAUDE.md` that hides `AGENTS.md`.** Add
`_check_claude_md_shadowing(project_root, home)` to `diagnostics.py`, called from
`run_project_health_checks` on every run. It walks `project_root` and each ancestor up to the
filesystem root. In each directory it checks `CLAUDE.md`, `CLAUDE.local.md` and
`.claude/CLAUDE.md`, and skips any candidate under `home / ".claude"`. Each hit is a
`DoctorIssue(severity="error")`. The message names the path. The detail says Claude Code skips
`AGENTS.md` while this file exists. `home` defaults to `Path.home()` and is a parameter so tests
can control it. Source: the ticket comment of 2026-11-02 ("up to but not including the user's
home `~/.claude/`"). `~/CLAUDE.md` itself is reported, because only `~/.claude/` is excluded.
- Rejected: stop the walk at the home directory. The ticket comment excludes `~/.claude/` only, and
  a `CLAUDE.md` above home still blocks `AGENTS.md`.

**D9 Doctor checks `AGENTS.md` imports.** In `_check_path_references`, replace the `CLAUDE.md`
loop with a check of the root `AGENTS.md`. Rename `_check_claude_md` to `_check_atpath_file`; the
classification (`_classify_reference`) is unchanged. `CLAUDE.md` imports are no longer checked: the
file is an error by itself (D8). Copies the existing pattern at `diagnostics.py` L319.

**D10 Setup and first-time sync create `AGENTS.md`.** Replace `init_claude_md` with
`init_agents_md` (creates an empty root `AGENTS.md` when missing, returns whether it created it).
Rename `SetupResult.claude_created` to `agents_md_created`. `cli/setup.py` prints
"Initialized AGENTS.md". `cli/sync.py` calls `init_agents_md`. Per the ticket done-when.

**D11 Orchestrator detection and hints.** `has_claude` becomes "root `AGENTS.md` exists". The two
wiring hints name `AGENTS.md` instead of `CLAUDE.md`. Follows D1.

**D12 [planner-decided, H3] `detect_agents` marker.** Replace the `CLAUDE.md` marker with
`AGENTS.md`: `claudecode` is detected when `.claude/` or `AGENTS.md` exists. Today the first-time
sync creates `CLAUDE.md`, which makes `claudecode` detected for skill install. After this change it
creates `AGENTS.md`, so the marker follows it.
- Rejected: `.claude/` only. A project that sync bootstrapped with only `AGENTS.md` would stop
  getting Claude skills.
- Rejected: keep `CLAUDE.md` as a marker. Beacon no longer creates it.

**D13 [planner-decided, H3] `TRACKED_ON_PURPOSE`.** Replace `"CLAUDE.md"` with `"AGENTS.md"` in
`core/gitignore.py` L77. `AGENTS.md` now carries the committed wiring.
- Rejected: keep both. Listing `CLAUDE.md` says beacon wants it committed, which contradicts the
  deprecation.

**D14 Delete dead Claude helpers.** Delete `wire_contexts_claudecode` and
`unwire_context_claudecode` and the tests that call them. Evidence: `git grep` at `85b875a` finds
no caller outside tests. `wire_contexts_opencode` and `unwire_context_opencode` stay (opencode is
unchanged). Update the `unwire_pruned_artifacts` docstring and the `apply.py` L401 comment to say
`AGENTS.md`.

**D15 User docs.** Per AGENTS.md "Documentation Standards" (keep docs current with code), update
`README.md` and the `site-docs/` pages that describe beacon writing `CLAUDE.md`
(`git grep -n CLAUDE.md origin/main -- README.md site-docs`). Say that beacon wires `AGENTS.md`,
that a `CLAUDE.md` stops Claude Code from reading it, and that `abc doctor` reports one. Leave
`docs/contributing/` and `CONTRIBUTING.md` unless a line states beacon's wiring behaviour.

## Risks / Trade-offs

- **R1** A `CLAUDE.md` with real content that does not import `@AGENTS.md` loses its context
  imports in the migration, and Claude Code keeps reading that `CLAUDE.md`. -> Sync prints a note
  (D7), doctor reports an error (D8), and the ops follow-up removes these files. The operator
  accepted the gap. A `CLAUDE.md` that imports `@AGENTS.md` keeps working, because `AGENTS.md` now
  holds the imports.
- **R2** The ancestor walk can find a real `CLAUDE.md` above the test `tmp_path` on some hosts, so
  doctor tests that expect zero issues fail there. -> Shadowing tests build the tree under
  `tmp_path` and pass `home`. Existing doctor tests that expect a clean run assert on their own
  issue messages, or monkeypatch `_check_claude_md_shadowing` to return `[]`.
- **R3** Sync deletes a user file. -> Only when it holds `@AGENTS.md`, blanks or HTML comments
  (D5). `CLAUDE.md` is git-tracked, so a wrong delete shows in `git status` and can be restored.
- **R4** Claude Code sessions that read `CLAUDE.md` only lose beacon contexts. -> Accepted by the
  operator as unsupported.
- **R5** This repo's own `CLAUDE.md` has a heading and a blockquote, so sync leaves it and doctor
  reports an error here. -> It imports `@AGENTS.md`, so contexts still load. The ops follow-up
  removes it.

## Migration Plan

The code change ships through the normal release. The repo state on the hosts changes only after
`abc` is upgraded there.

1. Merge the PR. Release through release-please and the release-branch push in AGENTS.md
   "Release Process".
2. Upgrade `abc` on each host that runs beacon.
3. In each beacon project on each host, run `abc sync`, then `abc doctor`.
   - Expected: context imports appear in `AGENTS.md`. A thin `CLAUDE.md` is deleted.
   - Verify: `abc doctor` shows no "`CLAUDE.md`" error, and `grep -c '^@.agentic-beacon/artifacts/' AGENTS.md`
     equals the number of effective contexts.
4. For each `CLAUDE.md` doctor still reports, move its remaining content into `AGENTS.md` by hand
   and delete it. Commit in that repo.

Rollback: pin the previous `abc` release and restore `CLAUDE.md` from git.
