## Context

The CLI ships markdown templates as data files under `libs/beacon/src/beacon/data/templates/`. When `abc warehouse init` runs, it renders and writes those files to the warehouse directory. Once written, the files are owned by the user — the CLI has no memory of what it originally wrote, and no mechanism to update them later.

As the CLI evolves, commands referenced in those docs become stale. The `abc warehouse template-upgrade` command solves this by giving users a safe, controlled way to pull in updated templates without clobbering their customisations.

## Goals / Non-Goals

**Goals:**
- Classify every templated file as `unmodified`, `user-modified`, or `legacy-unmodified` before touching it
- Upgrade `unmodified` and `legacy-unmodified` files silently
- Protect `user-modified` files by default: write a `.new` sidecar and warn the user
- Provide `--force` for scripting (blind overwrite) and `--interactive` for per-file diff + prompt
- Bootstrap legacy warehouses (no `.beacon/template-checksums.json`) using a shipped historical hashes registry
- Write / refresh `.beacon/template-checksums.json` after every upgrade run

**Non-Goals:**
- Automatic 3-way merge of user edits with new template content
- Upgrading non-template files (user-created files not tracked in checksums)
- Remote/network template fetching

## Decisions

### D1 — Hash-based file classification (not version markers)

Store SHA256 of each generated file in `.beacon/template-checksums.json` at `abc warehouse init` time. At upgrade time, re-hash the on-disk file and compare.

**Alternatives considered:**
- *Embedded version comments in files* (`[//]: # (beacon-template: v2.0.0 sha:abc)`): Self-contained but noisy, users accidentally delete markers while editing, and comments don't survive all markdown processors.
- *Git blame*: Fragile; not all warehouses use git, and the CLI shouldn't assume it.

**Rationale:** Hash tracking is precise, invisible to users, and works regardless of VCS.

### D2 — Historical hashes registry for legacy bootstrapping

Ship `data/historical_hashes.py` inside the CLI package — a dict mapping `filename → list[sha256]` for every known pristine template version.

```python
KNOWN_TEMPLATE_HASHES: dict[str, list[str]] = {
    "docs/architecture.md": ["<sha-v1>", "<sha-v2>"],
    ...
}
```

At upgrade time, if no checksum file exists, compute on-disk hashes and check against the registry:
- Match found → treat as `legacy-unmodified` → safe to upgrade
- No match → treat as `user-modified` → `.new` sidecar + warn

**Alternatives considered:**
- *Assume all legacy files are unmodified*: Too destructive.
- *Assume all legacy files are modified*: Makes the first upgrade a no-op for most users.

**Rationale:** The Gemini recommendation; leverages the fact that we control all prior template content.

### D3 — `.new` sidecar for "both changed" case (no 3-way merge)

When a file is user-modified and the template has also changed, write the new template to `<file>.new` and warn the user to merge manually.

**Alternatives considered:**
- *3-way merge via `difflib`*: Would inject `<<<<<<< HEAD` markers into Markdown on conflicts, breaking rendering and confusing users unfamiliar with merge syntax.
- *Silently skip with no output*: Users never learn a newer template exists.

**Rationale:** The `.pacnew` pattern (Arch Linux) is well-understood; users can use any diff/merge tool on the two files.

### D4 — `--force` is non-interactive; `--interactive` is per-file

`--force` bypasses all classification and overwrites everything — useful in CI or for users who want a hard reset. It does not prompt.

`--interactive` / `-i` shows a coloured `unified_diff` for each modified file and prompts before overwriting. Uses `click.secho` with `fg='red'`/`'green'` for removed/added lines.

**Rationale:** In CLI convention, `--force` implies scripting-friendly and non-blocking. Mixing prompts into `--force` would break scripts.

## Impacted Modules & Systems

**Repository Branch Strategy:**
- Repositories to be modified: `agentic-beacon` (single-repo project)
- Feature branch name: `feat/warehouse-template-upgrade`
- Base branch: `main` (after merging prerequisite PR `feat/extract-warehouse-templates`)

**Code Changes:**
- `libs/beacon/src/beacon/initializer.py` — add SHA256 computation + atomic write of `.beacon/template-checksums.json` after all template files are written
- `libs/beacon/src/beacon/cli.py` — register `template-upgrade` under the `warehouse` Click group; wire `--dry-run`, `--force`, `--interactive` options
- `libs/beacon/src/beacon/upgrader.py` *(new)* — `WarehouseUpgrader` class: file classification, upgrade loop, `.new` sidecar logic, diff display
- `libs/beacon/src/beacon/data/historical_hashes.py` *(new)* — `KNOWN_TEMPLATE_HASHES` dict + path normalisation helper
- `libs/beacon/tests/test_upgrader.py` *(new)* — unit tests for classification, upgrade logic, flag behaviour
- `libs/beacon/tests/test_template_commands.py` — extend existing regression test to also assert current template hashes are in `KNOWN_TEMPLATE_HASHES`

**Data / Schema Changes:**
- `.beacon/template-checksums.json` *(new file generated in each warehouse)* — JSON with `beacon_version` and `files` dict (relative path → SHA256)

**Configuration Changes:**
- None

**Infrastructure Changes:**
- None — purely additive CLI feature, no deployment or infrastructure impact

---

## Risks / Trade-offs

- **Historical hashes maintenance burden** — `data/historical_hashes.py` must be updated every time a template changes. If missed, legacy warehouses with that template version get false-positives (treated as user-modified).
  → *Mitigation:* The regression test added in the preceding PR (`test_template_commands.py`) will be extended to also assert that current template hashes are present in the registry.

- **SHA256 collision** — Astronomically unlikely, but a user edit could theoretically produce the same hash as a known template.
  → *Accepted trade-off:* Not worth the complexity of a secondary check.

- **`.new` file accumulation** — Repeated upgrades without merging produce multiple `.new` files.
  → *Mitigation:* `template-upgrade` warns if a `.new` file already exists and skips re-writing it.

## Migration Plan

1. Merge the preceding PR (`feat/extract-warehouse-templates`) — templates as files are a prerequisite.
2. Ship this feature in a minor release (`feat:` commit → Release-Please bumps minor).
3. Existing warehouses immediately gain access to `abc warehouse template-upgrade`; legacy bootstrapping via historical hashes handles pre-checksum warehouses transparently.
4. No rollback concern — the command is additive and never destructively modifies without user intent.

## Open Questions

- Should `abc warehouse init` print a hint about `abc warehouse template-upgrade` existing, so users discover it? (UX question, can decide during implementation)
- Should the historical hashes registry be auto-generated as part of the build/release process, or manually maintained? (Automation preferred long-term, manual acceptable for now)
