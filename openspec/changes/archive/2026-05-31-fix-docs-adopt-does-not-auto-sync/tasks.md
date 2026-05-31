# Tasks — fix-docs-adopt-does-not-auto-sync

**Type:** Documentation only. No source code, no tests, no schema changes.

> **Note:** This task list was refined in round 2 of PR #134 review. The original framing ("adopt is manifest-only; run `abc sync` separately") was wrong for the interactive TUI flow. Corrected ground truth below.

**Ground truth (verify only, do NOT modify):**

- `libs/beacon/src/beacon/domains/adoption/apply.py:96-265` — `commit_session` runs `_default_symlink_sync` (calls `SyncEngine.sync_all` on the newly-adopted paths) AND `_default_post_sync_wiring` (wires contexts via opencode/claudecode, skills via tool dirs, and agents via project-local symlinks). Both run inside the same atomic transaction. **Interactive `abc adopt` therefore DOES auto-sync.**
- `libs/beacon/src/beacon/cli/adoption.py:120-123` — only the **non-interactive** path (no TTY) prints "Edit beacon.yaml manually to adopt artifacts, then run `abc sync`". This path skips the TUI entirely.
- `.venv/bin/abc adopt --help` lists only `--dry-run`. No `--all` flag.
- `libs/beacon/src/beacon/domains/adoption/tui.py` — `t` keybinding toggles a show-all TUI view, but this is in-TUI, not a CLI flag.

## Phase 1 — Remove bogus `abc adopt --all` flag (interactive-adoption.md)

- [x] **1.1** Locate every reference to a CLI flag `--all` on `abc adopt` in `site-docs/guides/interactive-adoption.md` (originally lines ~60, 67-69). Delete them — the flag does not exist.
- [x] **1.2** Preserve the in-TUI `t` keybinding documentation (the keybinding is real per `tui.py`).
- [x] **1.3** If a "show all artifacts" feature still needs to be described, point users at the in-TUI `t` toggle.

## Phase 2 — Tighten `--dry-run` description (reference/cli.md)

- [x] **2.1** Replace the `--dry-run` description (around line 173) with the exact text from `abc adopt --help`: "Preview adoptable artifacts without modifying beacon.yaml."

## Phase 3 — Correctly describe the auto-sync behaviour

- [x] **3.1** `site-docs/quickstart.md` (~line 72): describe `abc adopt` as writing to `beacon.yaml` AND syncing the new artifacts immediately when the user confirms via the TUI. Add a short follow-up note that manual edits to `beacon.yaml` (outside the TUI) require a separate `abc sync`.
- [x] **3.2** `site-docs/reference/cli.md` (~line 165): in the `abc adopt` description, state that applying the TUI selection writes the manifest AND syncs / wires the new artifacts. Document the non-interactive fallback (no TTY → print + exit → manual edit + `abc sync`).
- [x] **3.3** `site-docs/guides/interactive-adoption.md` (~lines 41-52): "When you press Enter" list should describe the atomic write → sync → wire flow, including:
  - selections appended to `beacon.yaml`
  - matching `pending.yaml` entries removed
  - symlinks created under `.agentic-beacon/artifacts/`
  - contexts wired into agent config
  - skills installed into each detected tool's directories
  - agents wired into project-local `.claude/agents/` and `.opencode/agents/`
- [x] **3.4** Each of the three files above must include a short follow-up note that the auto-sync only fires from the TUI confirm path; manual `beacon.yaml` edits still require an explicit `abc sync`.

## Phase 4 — Verification

- [x] **4.1** `grep -rn "adopt --all\|--all.*adopt" site-docs/`. Expected: zero output.
- [x] **4.2** `grep -rn "abc adopt" site-docs/quickstart.md site-docs/reference/cli.md site-docs/guides/interactive-adoption.md`. Expected: each file has at least one occurrence.
- [x] **4.3** Verify the in-TUI `t` toggle is still mentioned in `site-docs/guides/interactive-adoption.md` and `site-docs/reference/cli.md` (grep for `Toggle show-all` or `press.*t`).
- [x] **4.4** Verify each of the three files describes BOTH the TUI auto-sync AND the non-interactive / manual-edit path requiring `abc sync`.
- [x] **4.5** Commit messages follow Conventional Commits (`docs: …`).

## Out of scope — DO NOT MODIFY

- `docs/migrations/**` and `docs/boot-context-design/**` — historical / design artifacts.
- Agent-wiring claims (separate change).
- SKILL.md frontmatter examples (separate change).
- Source code under `libs/beacon/`.
- Any file outside `site-docs/quickstart.md`, `site-docs/reference/cli.md`, `site-docs/guides/interactive-adoption.md`.
