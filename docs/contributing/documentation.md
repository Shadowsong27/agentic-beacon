# Documentation

How project documentation is organized and maintained.

---

## Documentation Sources

| Location | Purpose | Audience |
|---|---|---|
| `CONTRIBUTING.md` | Environment setup; GitHub-rendered entry point | Humans |
| `site-docs/` | MkDocs source — user-facing docs published to GitHub Pages | Humans (Beacon users) |
| `docs/contributing/` | Deep reference for the `abc` codebase (this directory) | Mostly agents |
| `docs/archive/` | Frozen historical design and migration notes (not published) | Humans on a hunt |
| `AGENTS.md` | High-level project context, auto-loaded on session start | Agents |
| `CLAUDE.md` | Bootstrap file that imports `AGENTS.md` and context files | Agents (Claude Code) |

The split exists because the value of each document is very different:

- `site-docs/` is for **users** of Agentic Beacon — installing `abc`, creating a warehouse, adopting artifacts. It needs to be polished and to have a small, navigable nav.
- `docs/contributing/` is reference material an **agent** reads when modifying the `abc` codebase — architecture, code style, design patterns, gotchas. Surfacing it on the public site would clutter the nav for users who never need it.

---

## Site Build (MkDocs)

The published documentation site is built from `site-docs/` using
[MkDocs Material](https://squidfunk.github.io/mkdocs-material/).

```bash
# Serve locally with hot reload
uv run mkdocs serve --livereload

# Build static site
uv run mkdocs build --strict
```

> **Click 8.3.x regression:** `mkdocs serve` silently disables livereload unless `--livereload` is passed explicitly. Always include the flag.

The site is deployed automatically to GitHub Pages on every push to `main` via
`.github/workflows/docs.yml`.

### Adding a page

1. Create a `.md` file under `site-docs/` (use the existing folder structure: `concepts/`, `guides/`, `tutorials/`, `reference/`, `design/`).
2. Add the page to the `nav:` section in `mkdocs.yml`.
3. Verify it renders cleanly with `mkdocs build --strict`.

---

## Archive (`docs/archive/`)

Historical design notes and migration records live under `docs/archive/`. They are not part of the published site. See `docs/archive/README.md` for the index and current-equivalent links.

Do not add new design docs there — write conceptual content in `site-docs/concepts/` or `site-docs/design/` instead.

---

## Keeping Docs Current

Documentation updates are part of every code change. The pre-PR checklist includes:

- Update `docs/contributing/` if you change architecture, CLI patterns, or configuration semantics.
- Update `site-docs/` (concepts/guides/reference) if you change user-facing commands, output format, or config files.
- Update `AGENTS.md` if the project overview, five domains, Python standards, or common patterns change.

---

## AGENTS.md Conventions

`AGENTS.md` is the authoritative reference for AI coding agents working on this project. Keep it
accurate and concise:

- Five domains table must match the actual `domains/` directory.
- Python standards section must reflect what `test_architecture.py` enforces.
- Common patterns section must reflect current CLI handler and domain conventions.
- Update the **Last Updated** date at the bottom when making changes.

`CLAUDE.md` must not duplicate `AGENTS.md`. It imports `AGENTS.md` via `@AGENTS.md` and adds
any additional context file references.
