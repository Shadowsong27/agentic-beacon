# archive/

Superseded prose, guides, and knowledge entries live here with a pointer to the replacing artifact.

## Convention

This tree mirrors the original repository layout. A document that used to live at `guides/foo.md` and has been superseded moves to `archive/guides/foo.md` with a one-line header at the top:

```markdown
> **Superseded by** [`<path-to-replacing-doc>`](../../path/to/replacement.md) — see [knowledge/decisions/<decision>.md](../../knowledge/decisions/<decision>.md).
```

The rest of the original document is preserved verbatim so future readers can recover the old reasoning, commands, and examples without digging through git history.

## Why we archive instead of delete

- **Historical context**: The old prose is often the best explanation of why the new model exists. Deleting it loses the "before" side of every "before → after" comparison.
- **External links**: Out-of-tree docs (blog posts, Slack threads, Linear tickets) may link to guide paths. Moving rather than deleting keeps those links recoverable with a one-hop redirect.
- **Agent context**: An agent asked "why did we stop using `abc contribute`?" should be able to read both the deprecation decision and the original command's documentation without git archaeology.

## When a file belongs here

Move to `archive/` when:

- The entire document is about a removed command, a removed capability, or a superseded mental model.
- The document's central claim no longer holds under the current design.

**Edit in place** (do not archive) when:

- Only some sections are stale and the rest remain accurate. Rewrite those sections with current terminology.
- The topic is orthogonal to the change (e.g., Python standards, release process, unrelated architectural decisions).

## Allowlisted zones

The grep-sweep script (`scripts/check_legacy_docs.sh`) allowlists this `archive/` tree and the `openspec/changes/*/` tree. Legacy terminology is expected and acceptable inside these zones.

## Current contents

Populated by the `symlink-based-artifact-sync` change (2026-05). Entries link to their replacements:

<!-- Keep this list alphabetized by archived path. -->

- *(See individual files for pointers.)*


abc contribute test
