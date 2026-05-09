# Agent Sync Edge-Case Audit (PER-126)

PR #109 (PER-113) deleted `libs/beacon/tests/integration/test_agents_sync_command.py`
(321 lines). The replacement tests (`test_agent_sync_lifecycle.py`,
`test_adopt_agent.py`) cover the new project-scoped agent lifecycle.  This document
audits each of the 13 edge cases from the deleted file against the new tests.

---

## Case status legend

- **covered** — an existing test exercises the behaviour; test name noted.
- **not applicable** — the case no longer applies because behaviour or a flag was removed.
- **added** — no existing test found; new test added under the indicated name.

---

## 1. opencode-only install

**Status:** added as `test_sync_wires_only_opencode_when_no_claude_dir`

When only `.opencode/` exists (no `.claude/`), `abc sync` must wire
`.opencode/agents/<name>.md` and must NOT attempt to wire `.claude/agents/`
or raise an error.  The symmetric `.claude`-only case is covered by TC2 in
`test_agent_sync_lifecycle.py` (`test_sync_wires_only_claude_when_no_opencode_dir`),
but the opencode-only direction was untested.

---

## 2. claudecode-only install

**Status:** covered by `test_sync_wires_only_claude_when_no_opencode_dir`
(TC2, `test_agent_sync_lifecycle.py`)

---

## 3. both-tools install

**Status:** added as `test_sync_wires_both_tools_when_both_dirs_present`

The rollback tests (`test_sync_rollback_when_agent_wire_fails_dual_tool`) incidentally
exercise the dual-tool wiring path (they assert both destinations were rolled back,
implying both were wired before failure), but there was no explicit happy-path test
asserting that both `.claude/agents/` and `.opencode/agents/` symlinks are created
when both tool directories are present.

---

## 4. no-agents-dir handling

**Status:** covered by `test_sync_with_empty_agents_list_succeeds` (TC4,
`test_agent_sync_lifecycle.py`)

`abc sync` with `agents: []` in `beacon.yaml` succeeds without creating any agent
artifacts, which is equivalent to the warehouse having no `agents/` directory for the
purposes of the sync pipeline.  The distributor's `_list_agents` also guards on
`agents_dir.exists()` before iteration.

---

## 5. idempotent re-run

**Status:** added as `test_sync_is_idempotent`

The adopt flow's idempotency is covered by TC3 in `test_adopt_agent.py`
(`test_accept_already_declared_agent_is_idempotent`) and TC8
(`test_accept_rollback_preserves_pre_existing_identical_tool_symlink`).  However,
running `abc sync` twice in a row — verifying that the second pass leaves symlinks
unchanged and exits 0 — had no dedicated test.

The underlying idempotency is guaranteed by `wire_agent_claudecode` /
`wire_agent_opencode`: when the destination symlink already resolves to the same
target, both functions return early without touching the filesystem.

---

## 6. force-overwrite

**Status:** not applicable — `--force` does NOT bypass agent regular-file conflicts.

`--force` still exists as a `sync` flag but is passed only to `wire_skills_post_sync`
(orchestrator.py line ~498), not to `wire_agents_atomically`.  The round-5
user-owned-content policy means a regular file at `.claude/agents/<name>.md` raises
`RegularFileConflictError` regardless of `--force`.  This is intentional: agent files
are treated as user-owned content that Beacon must never silently overwrite.

The regular-file conflict path is exercised by
`test_sync_rollback_when_agent_wire_fails` and
`test_sync_rollback_when_agent_wire_fails_dual_tool`.

---

## 7. non-interactive skip

**Status:** covered implicitly — all existing sync tests use Click's `CliRunner`
which runs in non-interactive mode by default.

`wire_agents_atomically` raises `RegularFileConflictError` regardless of terminal
interactivity, so there is no agent-specific "skip" code path that needs a dedicated
non-interactive test.  The orchestrator routes conflict prompts only for skills
(via `skill_conflict_callback`), not for agents.

---

## 8. no-beacon-dir error

**Status:** not applicable as an agent-specific case.

The precondition check (`ensure_sync_ready` / `find_project_root`) is not
agent-specific.  It is exercised by general sync tests in `test_sync_command.py`.

---

## 9. preserve-flag rejected

**Status:** not applicable — the `--preserve` flag no longer exists.

The `--preserve` concept for skills is now expressed as `--discard-local` /
`--contribute-local`.  For agents, there is no equivalent: the round-5 policy raises
`RegularFileConflictError` when a regular file occupies the destination, and Beacon
never overwrites user-owned content.  The flag being referenced in a code comment
inside `_resolve_skill_conflicts` is documentation of the skill-conflict callback
semantics, not a CLI flag.

---

## 10. warehouse-edits-visible (cross-project)

**Status:** added as `test_warehouse_edits_visible_through_symlinks`

This is the core cross-project visibility guarantee of the artifact distribution
model: because `.agentic-beacon/artifacts/agents/<name>.md` is a symlink to the
warehouse file, edits made to the warehouse file are visible through the symlink chain
immediately, without re-running `abc sync`.  No test verified this design property.

---

## 11. identical-file-replacement

**Status:** covered by `test_sync_rollback_when_agent_wire_fails` and the
`wire_agent_claudecode` idempotency path.

In the old (non-symlink) architecture this case was about whether a local regular file
with content identical to the warehouse file would be silently replaced.  Under the
current round-5 policy, ANY regular file at the destination raises
`RegularFileConflictError` regardless of content — identical content is not a
special case.  The pre-flight check in `wire_agents_atomically` uses
`dest.is_file() and not dest.is_symlink()` to detect this.

For the "identical symlink target" scenario (symlink already pointing to the correct
artifact), TC8 in `test_adopt_agent.py`
(`test_accept_rollback_preserves_pre_existing_identical_tool_symlink`) verifies that
the pre-existing symlink is preserved on rollback, and `wire_agent_claudecode` itself
returns early without touching a symlink that already resolves to the correct target.

---

## 12. broken-symlink-repair

**Status:** added as `test_sync_repairs_broken_symlink`

A "broken symlink" is one where `is_symlink()` is True but `exists()` is False
(dangling: the target path does not exist).  `wire_agent_claudecode` handles this via
the symlink branch:

```python
if dest.is_symlink():
    try:
        if dest.resolve(strict=False) == artifact_file.resolve(strict=False):
            return dest
    except OSError:
        pass
    dest.unlink()   # removes the stale/broken symlink
dest.symlink_to(artifact_file)  # creates fresh symlink
```

When the broken symlink's target resolves to a path different from the artifact file,
the comparison fails, the broken symlink is unlinked, and a fresh one is created.
No test existed to verify this concrete scenario; it was mentioned in the ticket as
needing explicit coverage.

---

## 13. README-ignored

**Status:** added as `test_readme_in_warehouse_agents_dir_is_not_wired`

`agents/README.md` in the warehouse is filtered out by `Distributor._list_agents`
(which uses `file.name.upper() != "README.MD"`) and by the `run_sync` agent-manifest
guard (which checks `f.name != "README.md"`).  These filters prevent README.md from
appearing in any catalog listing, meaning it cannot reach `beacon.yaml` through
normal `abc adopt` flows and therefore will not be wired by `abc sync`.

A dedicated test was added to guard against future regressions where the filtering
could be removed or bypassed, ensuring README.md never becomes an accidental
"agent" artifact.

---

## Summary table

| # | Edge case                   | Status         | Test name(s)                                                     |
|---|-----------------------------|----------------|------------------------------------------------------------------|
| 1 | opencode-only install       | added          | `test_sync_wires_only_opencode_when_no_claude_dir`               |
| 2 | claudecode-only install     | covered        | `test_sync_wires_only_claude_when_no_opencode_dir`               |
| 3 | both-tools install          | added          | `test_sync_wires_both_tools_when_both_dirs_present`              |
| 4 | no-agents-dir handling      | covered        | `test_sync_with_empty_agents_list_succeeds`                      |
| 5 | idempotent re-run           | added          | `test_sync_is_idempotent`                                        |
| 6 | force-overwrite             | not applicable | `--force` does not apply to agents (round-5 policy)              |
| 7 | non-interactive skip        | covered        | all existing sync tests run via CliRunner (non-interactive)      |
| 8 | no-beacon-dir error         | not applicable | not agent-specific; covered by general `test_sync_command.py`   |
| 9 | preserve-flag rejected      | not applicable | `--preserve` flag removed; superseded by round-5 policy         |
|10 | warehouse-edits-visible     | added          | `test_warehouse_edits_visible_through_symlinks`                  |
|11 | identical-file-replacement  | covered        | `test_sync_rollback_when_agent_wire_fails`, TC8 adopt            |
|12 | broken-symlink-repair       | added          | `test_sync_repairs_broken_symlink`                               |
|13 | README-ignored              | added          | `test_readme_in_warehouse_agents_dir_is_not_wired`               |
