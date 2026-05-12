# fix-docs-broken-xrefs-and-stale-examples

## Why

A pass over the docs surfaced a long tail of mostly-isolated issues that don't fit the earlier focused changes:

- Several broken internal links to files that don't exist (`./knowledge/decisions/single-warehouse-write-entrypoint.md`, `local-warehouse-workflow.md`, etc.).
- One docs file with a broken relative path (`../../guides/...` resolving above repo root from a `docs/` file).
- An invalid `beacon.yaml` example in `docs/specs-vs-artifacts.md` (uses a non-existent top-level `artifacts:` array form alongside `knowledge:` which is not a schema key).
- A pinned version string in `site-docs/installation.md` ("`2.7.1` or higher") that's now multiple major versions behind (current `3.2.0`).
- A `pip install --upgrade` instruction in `site-docs/troubleshooting.md` that contradicts the project's mandated `uv tool` install pattern.
- A "branding leak" in `docs/agentic-warehouse-design.md` that still describes the old "copy" distribution model and the long-removed "project overrides".
- A stale recommendation in `site-docs/concepts/how-it-works.md` that doesn't mention `--main-branch` / `--skip-git-check`.
- A duplicate line in `site-docs/reference/beacon-yaml.md`'s contexts example.

None of these is severe enough to warrant its own change, but together they meaningfully degrade docs quality. This change cleans them up in one pass.

## What Changes

### Broken cross-references

- **README.md (~line 123):** Remove or repoint the link to `./knowledge/decisions/single-warehouse-write-entrypoint.md` (does not exist). Acceptable: link to `docs/no-project-overrides.md`, or drop the inline link and keep the prose.
- **docs/README.md (~lines 42-46, 74, 76):** Remove or repoint references to `local-warehouse-workflow.md` (does not exist anywhere in repo).
- **docs/specs-vs-artifacts.md (~line 201):** Same broken `local-warehouse-workflow.md` reference. Repoint or delete.
- **docs/understanding-agent-skills.md (~line 70):** The link `[Creating Skills](../../guides/creating-skills.md)` resolves OUTSIDE the repo root from `docs/`. Fix to either `../guides/creating-skills.md` (if the target is repo-root `guides/`) or `../../site-docs/guides/creating-skills.md` (if the target is the mkdocs guide).
- **docs/boot-context-design/agents-md-architecture.md (~line 630):** The link `[Warehouse Contribution Guide](./warehouse-contribution-guide.md)` resolves to the same directory; real file is at `../../guides/warehouse-contribution-guide.md`.
- **docs/no-project-overrides.md (~line 14):** Same broken `knowledge/decisions/...` reference as README.md. Remove or repoint to a real document.

### Stale / invalid YAML example

- **docs/specs-vs-artifacts.md (~lines 93-101, 167-180):** The example `beacon.yaml` uses an invalid schema (bare `- backend/api-design-rules.md` items under a top-level `artifacts:` block, and a non-existent `knowledge:` top-level key). Rewrite the example to match the actual schema in `site-docs/reference/beacon-yaml.md`: `artifacts.contexts:`, `artifacts.skills:`, `artifacts.agents:` only.

### Version & install instructions

- **site-docs/installation.md (~line 30):** Either drop the specific pinned version reference ("`2.7.1` or higher") in favour of a generic "you should see a version number", or bump to the actual current version. Pick the version-agnostic option to avoid future bit-rot.
- **site-docs/troubleshooting.md (~lines 12, 46):** Replace `pip install --upgrade agentic-beacon` with `uv tool upgrade agentic-beacon` (matching `site-docs/installation.md`).

### Stale claims

- **docs/agentic-warehouse-design.md (~lines 308-313):** Remove the "project AGENTS.md can override warehouse contexts" claim — `docs/no-project-overrides.md` is the source of truth and explicitly denies this.
- **docs/agentic-warehouse-design.md (~line 397):** Either delete or qualify the sentence "the CLI only copies the declared artifacts to `.agentic-beacon/artifacts/`" — under the current symlink-based model, `abc sync` creates symlinks, not copies.
- **site-docs/concepts/how-it-works.md (~lines 166-168):** Add a note that the main-branch check is configurable (`abc warehouse connect --main-branch <name>` and `abc sync --skip-git-check`).

### Small nits

- **site-docs/reference/beacon-yaml.md (~lines 107-111):** Remove the duplicate `contexts/teams/backend/AGENTS.md` line from the contexts example.

## Out of Scope

- All issues already addressed by `fix-docs-agents-are-project-local`, `fix-docs-adopt-does-not-auto-sync`, and `fix-docs-skill-examples-add-requires-frontmatter`.
- `docs/migrations/**` — preserved as historical.
- Any rewrite of design-doc prose in `docs/boot-context-design/**` beyond the one xref fix.
- Any code change.

## Acceptance Criteria

After this change:

1. `grep -rn "knowledge/decisions/single-warehouse-write-entrypoint" .` returns **zero** matches outside `openspec/`.
2. `grep -rn "local-warehouse-workflow" docs/ site-docs/` returns **zero** matches.
3. `grep -n "pip install --upgrade agentic-beacon" site-docs/troubleshooting.md` returns **zero** matches.
4. `grep -n "2\.7\.1" site-docs/installation.md` returns **zero** matches (or the file is rewritten version-agnostically — verify by reading line ~30).
5. The example `beacon.yaml` in `docs/specs-vs-artifacts.md` validates against the schema described in `site-docs/reference/beacon-yaml.md` — i.e. all artifact lists are nested under `artifacts.contexts:`, `artifacts.skills:`, or `artifacts.agents:`. No top-level `knowledge:` or bare-list `artifacts:` items.
6. `site-docs/reference/beacon-yaml.md` has no duplicate `contexts/teams/backend/AGENTS.md` line.
7. Commit message: `docs: fix broken cross-references, stale examples, and pip→uv guidance`. Conventional Commits.
