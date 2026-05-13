# Documentation

How project documentation is organized and maintained.

---

## Documentation Sources

| Location | Purpose |
|---|---|
| `CONTRIBUTING.md` | Contributor onboarding (this doc's entry point) |
| `docs/` | Conceptual design documents and contributor reference |
| `docs/contributing/` | Detailed contributor guides (this directory) |
| `site-docs/` | MkDocs source — user-facing documentation published to GitHub Pages |
| `AGENTS.md` | Project context for AI coding agents (authoritative project reference) |
| `CLAUDE.md` | AI agent bootstrap file — imports `AGENTS.md` and context files |

---

## User Docs (MkDocs)

The published documentation site is built from `site-docs/` using
[MkDocs Material](https://squidfunk.github.io/mkdocs-material/).

```bash
# Serve locally with hot reload
uv run mkdocs serve --config-file site-docs/mkdocs.yml

# Build static site
uv run mkdocs build --config-file site-docs/mkdocs.yml
```

The site is deployed automatically to GitHub Pages on every push to `main` via
`.github/workflows/docs.yml`.

### Adding a page

1. Create a `.md` file under `site-docs/docs/`.
2. Add the page to the `nav:` section in `site-docs/mkdocs.yml`.
3. Verify it renders correctly with `mkdocs serve`.

---

## Conceptual Design Docs (`docs/`)

`docs/` contains in-depth design documents written for contributors and advanced users. These
are not part of the published MkDocs site.

When writing a design doc:
- Use plain GitHub-flavored Markdown.
- Link from `AGENTS.md` (or `docs/contributing/architecture.md`) if the doc is referenced in
  contributor workflows.

---

## Keeping Docs Current

Documentation updates are part of every code change. The pre-PR checklist includes:

- Update `docs/contributing/` if you change architecture, CLI patterns, or configuration
  semantics.
- Update `site-docs/docs/` if you change user-facing commands, output format, or config files.
- Update `AGENTS.md` if the project overview, five domains, Python standards, or common patterns
  change.

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
