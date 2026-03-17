# Keeping Warehouse Docs Up to Date

When `abc` evolves — commands renamed, removed, or added — the documentation files that were generated into your warehouse by `abc warehouse init` can go stale. They may still reference old commands like `abc setup --warehouse` that no longer exist.

`abc warehouse template-upgrade` solves this by re-applying the latest templates to an existing warehouse, while protecting any customisations you have made.

---

## How it works

Every warehouse created by `abc warehouse init` gets a `.beacon/template-checksums.json` file:

```json
{
  "beacon_version": "2.1.0",
  "files": {
    "README.md": "3c1c02ce...",
    "docs/architecture.md": "965c303c...",
    ...
  }
}
```

This records the SHA256 of every template-generated file at creation time. When you run `template-upgrade` later, each file is classified before anything is written:

| Classification | Condition | Action |
|---|---|---|
| **Unmodified** | On-disk hash matches stored checksum | Overwritten with new template |
| **User-modified** | On-disk hash differs from stored checksum | Skipped — `.new` sidecar written |
| **Legacy-unmodified** | No checksum file; hash matches a known pristine version | Overwritten with new template |
| **Legacy-unknown** | No checksum file; hash unrecognised | Skipped — `.new` sidecar written |

Your customisations are never silently overwritten.

---

## Basic usage

```bash
# Upgrade a warehouse at a specific path
abc warehouse template-upgrade /path/to/your-warehouse

# Upgrade the warehouse in the current directory
abc warehouse template-upgrade
```

Example output:

```
✓ Upgraded .gitignore
✓ Upgraded README.md
✓ Upgraded contexts/AGENTS.md
⚠ docs/architecture.md was modified. New template written to docs/architecture.md.new — merge manually.
✓ Upgraded docs/contribution-guide.md
✓ Upgraded knowledge/README.md
✓ Upgraded skills/README.md
Template upgrade complete. 6 upgraded, 1 skipped (see *.new files).
```

Files you customised are left untouched. The new template content is written to a `.new` sidecar so you can merge at your own pace.

---

## Merging a sidecar file

When `docs/architecture.md.new` appears, open both files in your editor and merge the parts you want — usually just the updated command references in the new version.

In VS Code:
1. Right-click `docs/architecture.md` in the explorer → **Select for Compare**
2. Right-click `docs/architecture.md.new` → **Compare with Selected**
3. Copy the updated sections from the right pane into your file
4. Delete `docs/architecture.md.new` when done

Once merged, the next `template-upgrade` run will detect that `docs/architecture.md` no longer matches any known template hash and correctly classify it as user-modified — protecting your merged content in future upgrades.

---

## Preview before writing: `--dry-run`

See what the command would do without changing anything:

```bash
abc warehouse template-upgrade /path/to/your-warehouse --dry-run
```

Output:

```
[would upgrade] .gitignore
[would upgrade] README.md
[would upgrade] contexts/AGENTS.md
[would upgrade] docs/architecture.md
[would upgrade] docs/contribution-guide.md
[would upgrade] knowledge/README.md
[would upgrade] skills/README.md
Template upgrade (dry-run) complete. 0 upgraded, 0 skipped (see *.new files).
```

No files are created or modified. The checksum file is not updated. Use this to audit what will change before committing.

---

## Interactive mode: `--interactive` / `-i`

Review each modified file with a coloured diff before deciding what to do:

```bash
abc warehouse template-upgrade /path/to/your-warehouse --interactive
```

For each user-modified file, you will see a diff and a prompt:

```diff
--- Current (Modified)
+++ New Template
@@ -1,5 +1,5 @@
 # My Warehouse Architecture
-Run `abc setup --warehouse` to connect a project.
+Run `abc warehouse connect --path /path/to/warehouse` to connect a project.
```

```
Overwrite docs/architecture.md with new template? [y/N]:
```

- **y** — overwrites the file with the new template
- **N** (default) — writes a `.new` sidecar and moves on

Use this when you want to quickly accept straightforward template updates (command fixes, typos) without losing your full custom content.

---

## Hard reset: `--force`

Overwrites every template file regardless of modification status. No prompts, no sidecars.

```bash
abc warehouse template-upgrade /path/to/your-warehouse --force
```

```
✓ Upgraded .gitignore (force)
✓ Upgraded README.md (force)
✓ Upgraded docs/architecture.md (force)
...
Template upgrade complete. 7 upgraded, 0 skipped (see *.new files).
```

Use this when:
- You want a hard reset to the latest templates and don't need your customisations
- Running in CI/CD to keep a reference warehouse always current
- You have already backed up any custom content

---

## Legacy warehouses (no checksum file)

Warehouses created before `abc` v2.1 do not have `.beacon/template-checksums.json`. The upgrade command handles this gracefully using a built-in registry of all known pristine template versions.

```bash
# Works the same — no extra steps needed
abc warehouse template-upgrade /path/to/legacy-warehouse
```

What happens:
- Files that are still pristine (never edited) are detected via the historical hash registry and upgraded silently, tagged `(legacy warehouse)`
- Files that have been edited but don't match any known pristine version get a `.new` sidecar

After the first upgrade run completes, `.beacon/template-checksums.json` is written so all future runs use the faster standard path.

---

## When to run it

- After upgrading `abc` to a new minor or major version
- When you see deprecation warnings in warehouse-generated docs
- When teammates report that the commands in `docs/contribution-guide.md` don't work
- As part of your team's periodic warehouse maintenance

A quick way to check whether an upgrade is needed:

```bash
abc warehouse template-upgrade /path/to/your-warehouse --dry-run
```

If all files show `[would upgrade]`, run it without `--dry-run`. If everything is already current, nothing is written.

---

## Recommended workflow

```bash
# 1. Preview changes
abc warehouse template-upgrade ~/my-warehouse --dry-run

# 2. Run the upgrade
abc warehouse template-upgrade ~/my-warehouse

# 3. Merge any .new sidecars in your editor, then delete them

# 4. Commit
cd ~/my-warehouse
git add .
git commit -m "chore: upgrade warehouse templates to latest abc version"
git push
```

Teammates get the updated docs on their next `git pull`.
