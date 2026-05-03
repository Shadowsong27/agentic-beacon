# Draft: Conventional-Commit Breaking-Change Message

> **Not for commit verbatim.** This file is a draft written for task 10.3 of the
> `symlink-based-artifact-sync` change. When the final commit is prepared,
> copy the subject line + body into the actual commit message. Delete this
> file afterward (or leave it in `openspec/changes/symlink-based-artifact-sync/`
> — it is archived alongside the change).

---

## Subject

```
feat!: symlink-based artifact sync, single-warehouse-write-entrypoint
```

## Body

```
Replace the copy-based artifact distribution model with per-file symlinks
pointing into the local warehouse clone. The warehouse clone is now the
single on-disk copy and single write entrypoint for every harness artifact
on a machine; projects reference it via symlinks under
.agentic-beacon/artifacts/.

This eliminates the last-writer-wins regression class caused by two
project-local copies of the same logical file being edited in parallel.
Cross-project visibility of harness edits on a single machine is now
intended behaviour, not a leak — see
knowledge/decisions/single-warehouse-write-entrypoint.md.

Changes:

- abc sync now creates symlinks into the warehouse clone, expands
  beacon.yaml globs to per-file targets, materializes real directories at
  intermediate levels, and is idempotent (repair broken / wrong-target
  symlinks, prune orphans).
- abc sync adds --dry-run (preview) and the migration flags
  --contribute-local / --discard-local.
- abc warehouse contribute wraps git add + git commit inside the warehouse
  clone (optionally --push).
- abc warehouse status reports uncommitted warehouse state scoped by
  beacon.yaml; supports <path> for single-file diff and --all to drop the
  scope filter.
- First abc sync on a pre-existing copy-based tree runs an interactive
  migration: identical files become symlinks silently; modified files
  prompt contribute/discard/skip with diff preview. Non-interactive bulk
  resolution via the new flags.
- abc warehouse connect rejects non-local paths (http://, git://,
  tarballs) and normalizes the stored path to absolute.

BREAKING CHANGE:
- abc contribute is removed. Use abc warehouse contribute.
- abc delta is removed. Use abc warehouse status.
- abc install <artifact> is removed. Declare the artifact in beacon.yaml
  and run abc sync; use abc agents sync for global agent installs.
- abc sync --preserve flag is removed. Sync no longer overwrites files
  (it creates or repairs symlinks), so the flag has no meaning. --preserve
  remains on abc install.
- Windows is explicitly unsupported. abc sync fails loudly on Windows. No
  copy or hardlink fallback is provided.
- Snapshot semantics are removed. Projects now float on the warehouse
  working tree's current state. Pinning, if needed, is a future feature.

Migration:
- Run abc sync once in each existing project after upgrading. The
  migration prompt resolves any modified artifact files by contributing
  them to the warehouse or discarding them in favor of the warehouse copy.
- Rollback: pin the previous CLI version, then in each project run a
  one-shot copy-restore over the symlink tree before resuming.

Documentation:
- Root README.md, AGENTS.md, guides/, docs/, examples/sample-warehouse/,
  and libs/beacon/src/beacon/data/templates/ all updated for the new
  model.
- Obsolete prose moved to archive/ with "superseded by" pointers; see
  archive/README.md for the convention.
- scripts/check_legacy_docs.sh grep-gates future PRs against legacy
  terminology leaking back in.

Closes: openspec/changes/symlink-based-artifact-sync
```

---

## Notes for the committer

- The subject must start with `feat!:` (not `feat:`) so Release-Please
  detects the breaking change and bumps the major version.
- The `BREAKING CHANGE:` footer must appear exactly as shown (with the
  colon) for Release-Please to parse it.
- If the commit is squashed on merge, ensure the full body above is
  preserved in the PR squash-merge message — not truncated to the PR
  title.
- After merging the Release-Please PR and pushing the release tag, the
  PyPI publish workflow runs automatically; see
  `knowledge/facts/release-workflow.md`.
- mkdocs source (`site-docs/`) was deliberately deferred to a separate
  session; mention it explicitly in the PR body if the release ships
  before that sweep.
- The in-repo `examples/sample-warehouse/` now mirrors the public
  `agentic-beacon-starter-warehouse` content (minus its git metadata).
  That external repo's own README still contains `abc contribute` /
  `abc delta` and needs a separate PR.
