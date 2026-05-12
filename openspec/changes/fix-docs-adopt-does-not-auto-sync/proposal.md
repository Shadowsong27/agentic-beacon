# fix-docs-adopt-does-not-auto-sync

> **Note on the title:** this change was originally framed as "adopt does not auto-sync" based on the message printed by `libs/beacon/src/beacon/cli/adoption.py:122` in non-interactive mode. The opencode-review bot correctly pointed out (round 2 of PR #134) that this framing is wrong for the interactive TUI flow, which DOES auto-sync via `commit_session`. The change has been refined accordingly — see "What Changes" and "Acceptance Criteria" below. The title is preserved for traceability, but the corrected scope is "make the adopt-sync relationship correct in both directions: TUI auto-syncs, non-interactive does not."

## Why

User-facing docs were imprecise in opposite directions:

- **`site-docs/guides/interactive-adoption.md`** documented a CLI flag `abc adopt --all`. Confirmed against `.venv/bin/abc adopt --help` — the only flag is `--dry-run`. The `t` keybinding inside the TUI toggles a show-all view, but there is no CLI-level `--all` flag.
- **`site-docs/quickstart.md`, `site-docs/reference/cli.md`, `site-docs/guides/interactive-adoption.md`** described the TUI auto-sync as if it required a separate manual `abc sync` step. In fact, `libs/beacon/src/beacon/domains/adoption/apply.py:96-265` shows that `commit_session` runs `_default_symlink_sync` (which calls `SyncEngine.sync_all`) and `_default_post_sync_wiring` (contexts → opencode/claudecode, skills, agents) inside the same atomic transaction. The "you must run `abc sync` afterward" message in `cli/adoption.py:120-123` only fires in non-interactive mode (no TTY).

The corrected mental model:

| Path | Manifest write | Sync + wire |
|---|---|---|
| Interactive TUI confirm (default) | yes | **yes — atomically** |
| Non-interactive (no TTY) | no — prints candidate list, exits | no — user must edit `beacon.yaml` and run `abc sync` |
| Manual edit of `beacon.yaml` outside `abc adopt` | by hand | user must run `abc sync` |

## What Changes

- **Bogus `--all` flag:** Remove every reference to `abc adopt --all` from `site-docs/guides/interactive-adoption.md`. Preserve the in-TUI `t` keybinding (the keybinding is real per `libs/beacon/src/beacon/domains/adoption/tui.py`).
- **`--dry-run` description:** Tighten in `site-docs/reference/cli.md` to match the actual `abc adopt --help` text: "Preview adoptable artifacts without modifying beacon.yaml."
- **TUI auto-sync wording:** Keep the original "adopt syncs immediately" claim for the TUI flow in `site-docs/quickstart.md`, `site-docs/reference/cli.md`, and `site-docs/guides/interactive-adoption.md`. Add a short follow-up note to each pointing out that the auto-sync only fires from the TUI confirm path — users who edit `beacon.yaml` manually still need to run `abc sync`.

## Out of Scope

- Any code changes — `abc adopt` behaviour is correct; only docs are wrong.
- Agent-wiring location (covered by `fix-docs-agents-are-project-local`).
- Skill `requires:` frontmatter examples (covered by `fix-docs-skill-examples-add-requires-frontmatter`).
- `docs/migrations/**` — historical artifacts.

## Acceptance Criteria

After this change:

1. `grep -rn "abc adopt --all\|adopt --all" site-docs/` returns **zero** matches.
2. The TUI flow in `site-docs/quickstart.md`, `site-docs/reference/cli.md`, and `site-docs/guides/interactive-adoption.md` correctly describes the atomic write-then-sync-then-wire behaviour of `commit_session`.
3. Each of those three files also notes that manual `beacon.yaml` edits require a separate `abc sync`.
4. The in-TUI `t` toggle keybinding remains documented in `site-docs/guides/interactive-adoption.md` and `site-docs/reference/cli.md`.
5. Commit messages follow Conventional Commits (`docs: …`).
