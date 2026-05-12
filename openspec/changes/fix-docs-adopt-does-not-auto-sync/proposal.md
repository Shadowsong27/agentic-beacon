# fix-docs-adopt-does-not-auto-sync

## Why

Several user-facing docs claim that `abc adopt` automatically syncs adopted artifacts. The implementation does the opposite: `libs/beacon/src/beacon/cli/adoption.py:122` explicitly tells the user "Non-interactive mode. Edit beacon.yaml manually to adopt artifacts, **then run `abc sync`**". The adopt command writes `beacon.yaml` and `pending.yaml`; it does **not** create symlinks. Users following the affected guides will be confused when the artifacts they "adopted" never appear in `.agentic-beacon/artifacts/`.

A separate falsehood: `site-docs/guides/interactive-adoption.md` documents a CLI flag `abc adopt --all`. Confirmed against `abc adopt --help` — the only flag is `--dry-run`. The `t` keybinding inside the TUI toggles a show-all view, but there is no CLI-level `--all` flag.

## What Changes

- **site-docs/quickstart.md (lines ~72 and ~86):** Replace the claim that `abc adopt` "syncs them immediately — symlinks are created, agent config is wired, and skills are installed as slash commands. No separate `abc sync` needed." with the truth: `abc adopt` writes to `beacon.yaml` and the user must then run `abc sync`.
- **site-docs/reference/cli.md (line ~165):** In the `abc adopt` description, remove "and syncs immediately"; clarify that adopt is a manifest-only operation and `abc sync` is the separate step.
- **site-docs/guides/interactive-adoption.md (line ~44):** Remove the "`abc sync` runs automatically" sentence and replace with a follow-up step instructing the user to run `abc sync` after adoption.
- **site-docs/guides/interactive-adoption.md (lines ~60, 67-69):** Delete every reference to a CLI-level `--all` flag. Preserve the in-TUI `t` keybinding documentation (the keybinding is real per `libs/beacon/src/beacon/domains/adoption/tui.py`).
- **site-docs/reference/cli.md (line ~173):** Tighten the `--dry-run` description to match the actual `--help` text: "Preview adoptable artifacts without modifying beacon.yaml."

## Out of Scope

- Any code changes — `abc adopt` behaviour is correct; only docs are wrong.
- Agent-wiring location (covered by `fix-docs-agents-are-project-local`).
- Skill `requires:` frontmatter examples (covered by `fix-docs-skill-examples-add-requires-frontmatter`).
- `docs/migrations/**` — historical artifacts.

## Acceptance Criteria

After this change:

1. `grep -rn "syncs them immediately\|syncs automatically\|No separate.*sync\|sync.*automatically.*adopt" site-docs/` returns **zero** matches.
2. `grep -rn "abc adopt --all\|adopt --all" site-docs/` returns **zero** matches.
3. Every workflow walkthrough in `site-docs/quickstart.md`, `site-docs/reference/cli.md`, and `site-docs/guides/interactive-adoption.md` shows `abc adopt` followed by an explicit `abc sync` step (or describes the same separation in prose).
4. The in-TUI `t` toggle keybinding remains documented in `site-docs/guides/interactive-adoption.md` and `site-docs/reference/cli.md`.
5. Commit message: `docs: remove false "abc adopt auto-syncs" claim and bogus --all flag`. Conventional Commits.
