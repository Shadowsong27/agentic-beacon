# Documentation

How project documentation is organized and maintained.

---

## Documentation Sources

| Location | Purpose |
|---|---|
| `CONTRIBUTING.md` | Thin entry point at the repo root — environment setup + pointer to this site |
| `site-docs/` | MkDocs source — user-facing docs and contributor guides, published to GitHub Pages |
| `site-docs/contributing/` | Contributor guides (this directory) |
| `docs/archive/` | Frozen historical design and migration notes (not published) |
| `AGENTS.md` | Project context for AI coding agents (authoritative project reference) |
| `CLAUDE.md` | AI agent bootstrap file — imports `AGENTS.md` and context files |

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

1. Create a `.md` file under `site-docs/` (use the existing folder structure: `concepts/`, `guides/`, `tutorials/`, `reference/`, `contributing/`).
2. Add the page to the `nav:` section in `mkdocs.yml`.
3. Verify it renders cleanly with `mkdocs build --strict`.

---

## Archive (`docs/archive/`)

Historical design notes and migration records live under `docs/archive/`. They are not part of the published site. See `docs/archive/README.md` for the index and current-equivalent links.

Do not add new design docs there — write conceptual content in `site-docs/concepts/` instead.

---

## Keeping Docs Current

Documentation updates are part of every code change. The pre-PR checklist includes:

- Update `site-docs/contributing/` if you change architecture, CLI patterns, or configuration semantics.
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
