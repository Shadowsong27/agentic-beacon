# Tasks — fix-docs-adopt-does-not-auto-sync

**Type:** Documentation only. No source code, no tests, no schema changes.

**Ground truth (verify only, do NOT modify):**

- `libs/beacon/src/beacon/cli/adoption.py:122` — non-interactive guidance literally reads "Edit beacon.yaml manually to adopt artifacts, then run `abc sync`".
- `.venv/bin/abc adopt --help` lists only `--dry-run`. No `--all` flag.
- `libs/beacon/src/beacon/domains/adoption/tui.py` — `t` keybinding toggles a show-all TUI view, but this is in-TUI, not a CLI flag.

## Phase 1 — site-docs/quickstart.md

- [ ] **1.1** Locate the paragraph (around line 72) that claims `abc adopt` "writes your selections to `beacon.yaml` and **syncs them immediately** — symlinks are created, agent config is wired, and skills are installed as slash commands. **No separate `abc sync` needed.**" Replace with prose that describes:
  - `abc adopt` updates `beacon.yaml` (and clears matching `pending.yaml` entries) but does **not** create symlinks.
  - Run `abc sync` afterward to materialise the symlinks.
- [ ] **1.2** Around line 86, if a subsequent "what just happened" recap also says adoption syncs automatically, fix it to match Phase 1.1.
- [ ] **1.3** Wherever the quickstart walks the user through "adopt then sync", make the two-step explicit: show `abc adopt` then `abc sync` as separate command blocks.

## Phase 2 — site-docs/reference/cli.md

- [ ] **2.1** In the `abc adopt` section (around line 165), remove the phrase "and syncs immediately" or any equivalent claim. The adopt command is manifest-only.
- [ ] **2.2** Around line 173, replace the `--dry-run` description with the exact text from `abc adopt --help`: "Preview adoptable artifacts without modifying beacon.yaml."
- [ ] **2.3** If the section's "what to run next" hint is missing, add a one-line follow-up note: after `abc adopt`, run `abc sync` to materialise the symlinks.

## Phase 3 — site-docs/guides/interactive-adoption.md

- [ ] **3.1** Around line 44, replace any claim that `abc sync` runs automatically after adoption with a follow-up step that prompts the user to run `abc sync` themselves.
- [ ] **3.2** Around lines 60 and 67-69, delete every reference to a CLI flag `--all` on `abc adopt` (it does not exist). Examples of phrasings to look for: "use `--all` to show every artifact", "pass `--all`", "with `--all`". Replace with a pointer to the in-TUI `t` toggle if a "show all artifacts" feature needs to be documented.
- [ ] **3.3** Keep the `t` (toggle show-all) and other in-TUI keybindings documented exactly as they are now. The bug is only the CLI flag claim.
- [ ] **3.4** If the guide's "after you finish" section omits the explicit `abc sync` step, add it.

## Phase 4 — Verification

- [ ] **4.1** `grep -rn "syncs them immediately\|syncs automatically\|No separate.*sync\|sync.*automatically.*adopt" site-docs/`. Expected: zero output.
- [ ] **4.2** `grep -rn "adopt --all\|--all.*adopt" site-docs/`. Expected: zero output.
- [ ] **4.3** `grep -rn "abc sync" site-docs/quickstart.md site-docs/reference/cli.md site-docs/guides/interactive-adoption.md`. Expected: each file has at least one occurrence (proves the explicit sync step is present).
- [ ] **4.4** Verify the in-TUI `t` toggle is still mentioned in `site-docs/guides/interactive-adoption.md` and `site-docs/reference/cli.md` (grep for `toggle\|press.*t\| t \b`).
- [ ] **4.5** Commit message: `docs: remove false "abc adopt auto-syncs" claim and bogus --all flag`. Conventional Commits.

## Out of scope — DO NOT MODIFY

- `docs/migrations/**` and `docs/boot-context-design/**` — historical / design artifacts.
- Agent-wiring claims (separate change).
- SKILL.md frontmatter examples (separate change).
- Source code under `libs/beacon/`.
- Any file outside `site-docs/quickstart.md`, `site-docs/reference/cli.md`, `site-docs/guides/interactive-adoption.md`.
