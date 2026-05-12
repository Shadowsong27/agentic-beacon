# Tasks — fix-docs-skill-examples-add-requires-frontmatter

**Type:** Documentation only. No source code, no tests, no schema changes.

**Ground truth (read but DO NOT modify):**

- `site-docs/reference/beacon-yaml.md:77-87` — canonical `requires:` documentation. Schema:
  ```yaml
  requires:
    contexts: [<context-name>, ...]
    knowledge: [<knowledge-path>, ...]
  ```
- `site-docs/concepts/artifact-types.md:85-93` — narrative explanation of `requires:`.
- The skills bundled with `abc warehouse init` at `libs/beacon/src/beacon/data/skills/*/SKILL.md` — read one or two for canonical formatting (e.g. `record-knowledge/SKILL.md`).

## Phase 1 — site-docs/guides/warehouse-creation.md

- [ ] **1.1** Read the file end-to-end. Note every fenced YAML block whose frontmatter starts with `name:` followed by `description:`.
- [ ] **1.2** For each such block, insert a `requires:` key immediately AFTER `description:` (preserving indentation and surrounding fields). Choose realistic dependencies for the example's domain:
  - The `code-review` example: `contexts: [python-standards]`.
  - Any example with no obvious dependency: `contexts: []`.
- [ ] **1.3** Where the surrounding prose enumerates the SKILL.md fields ("the frontmatter contains name, description, ..."), add `requires:` to the enumeration in the same sentence.
- [ ] **1.4** Do not rewrite the body Markdown of the SKILL.md examples; only edit the frontmatter and the immediately-adjacent prose.

## Phase 2 — site-docs/guides/creating-skills.md

- [ ] **2.1** Read the file end-to-end. Note every fenced YAML frontmatter block.
- [ ] **2.2** For each block, insert `requires:` as above. Pick realistic dependencies based on the example's purpose:
  - Examples that mention contexts: include them in `contexts:`.
  - Examples that mention knowledge files: include them in `knowledge:`.
  - Otherwise: `contexts: []`.
- [ ] **2.3** If the guide has a "fields explained" table or list, add a row for `requires:` with a one-line explanation: "declares the contexts and knowledge files this skill depends on; consumed by `abc sync` for transitive resolution".
- [ ] **2.4** Do not introduce new top-level sections or rewrite surrounding prose beyond the immediate caption.

## Phase 3 — Verification

- [ ] **3.1** Run this command and confirm zero output:
  ```bash
  for f in site-docs/guides/warehouse-creation.md site-docs/guides/creating-skills.md; do
    # For each YAML block in the file, confirm `requires:` appears.
    python3 -c "
  import re, sys
  with open('$f') as fp: text = fp.read()
  for m in re.finditer(r'\`\`\`yaml\n(.*?)\n\`\`\`', text, flags=re.DOTALL):
      block = m.group(1)
      if re.match(r'^\s*name:', block) and 'requires:' not in block:
          print('MISSING requires: in', '$f', 'block starting:', block.splitlines()[0])
          sys.exit(1)
  "
  done
  ```
- [ ] **3.2** `grep -c "^requires:" site-docs/guides/warehouse-creation.md site-docs/guides/creating-skills.md` — both files should report ≥ 1.
- [ ] **3.3** Commit message: `docs: add requires: frontmatter to SKILL.md examples in user guides`. Conventional Commits.

## Out of scope — DO NOT MODIFY

- Any file outside `site-docs/guides/warehouse-creation.md` and `site-docs/guides/creating-skills.md`.
- `docs/migrations/**`, `docs/boot-context-design/**` — preserved as historical.
- Source code under `libs/beacon/`.
- `site-docs/reference/beacon-yaml.md`, `site-docs/concepts/artifact-types.md` — these already document `requires:` correctly.
- The agent-wiring or auto-sync claims (separate changes).
