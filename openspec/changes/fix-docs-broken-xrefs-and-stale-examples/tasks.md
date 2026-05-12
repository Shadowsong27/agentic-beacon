# Tasks — fix-docs-broken-xrefs-and-stale-examples

**Type:** Documentation only. No source code, no tests, no schema changes.

**Ground truth (verify only, do NOT modify):**

- `site-docs/reference/beacon-yaml.md` — canonical schema for `beacon.yaml`. Top-level keys: `warehouse:`, `artifacts:` (with sub-keys `contexts`, `skills`, `agents`). NO top-level `knowledge:` key.
- `site-docs/installation.md` (the install instructions block) — uses `uv tool install agentic-beacon`.
- `.venv/bin/abc --version` reflects the current released version.

## Phase 1 — Broken cross-references

- [ ] **1.1** `README.md` (~line 123): Locate the inline link `[Decision — Single Warehouse Write Entrypoint](./knowledge/decisions/single-warehouse-write-entrypoint.md)`. The target does not exist. Replace with either:
  - A link to `docs/no-project-overrides.md` (which covers the same decision).
  - Drop the inline link, preserve the surrounding prose.
- [ ] **1.2** `docs/README.md` (~lines 42-46, 74, 76): Locate every reference to `local-warehouse-workflow.md`. Target does not exist anywhere in the repo. Either delete the row/link entirely or repoint to `docs/no-project-overrides.md` / `docs/agentic-warehouse-design.md` as the closest in-repo analogue.
- [ ] **1.3** `docs/specs-vs-artifacts.md` (~line 201): Same broken `local-warehouse-workflow.md`. Remove the link; preserve the surrounding prose.
- [ ] **1.4** `docs/understanding-agent-skills.md` (~line 70): The link `[Creating Skills](../../guides/creating-skills.md)` resolves OUTSIDE the repo root. Fix to either:
  - `../guides/creating-skills.md` if the target is the repo-root `guides/` directory and a `creating-skills.md` exists there, OR
  - `../../site-docs/guides/creating-skills.md` if the intended target is the mkdocs guide.
  Verify with `ls` before choosing.
- [ ] **1.5** `docs/boot-context-design/agents-md-architecture.md` (~line 630): Fix `[Warehouse Contribution Guide](./warehouse-contribution-guide.md)` to `../../guides/warehouse-contribution-guide.md` (the real location at repo root). Verify the target file exists before linking.
- [ ] **1.6** `docs/no-project-overrides.md` (~line 14): Same broken `../knowledge/decisions/single-warehouse-write-entrypoint.md` reference. Remove or repoint as in 1.1.

## Phase 2 — Invalid YAML schema example

- [ ] **2.1** `docs/specs-vs-artifacts.md` (~lines 93-101 and 167-180): Open both example `beacon.yaml` blocks. They incorrectly use bare items directly under `artifacts:` (e.g. `- backend/api-design-rules.md`) and a non-existent `knowledge:` top-level key.
- [ ] **2.2** Rewrite each example to match the canonical schema:
  ```yaml
  warehouse:
    path: ../my-warehouse
  artifacts:
    contexts:
      - <context-path>.md
    skills:
      - <skill-name>
    agents:
      - <agent-name>
  ```
  Preserve the example's intent (which artifacts it's illustrating) — only fix the structure.

## Phase 3 — Version & install instructions

- [ ] **3.1** `site-docs/installation.md` (~line 30): Locate "You should see the current version (`2.7.1` or higher)." Rewrite version-agnostically: "You should see a version number printed (e.g. `3.x.y`)." Do not pin to a specific minor.
- [ ] **3.2** `site-docs/troubleshooting.md` (~lines 12 and 46): Replace `pip install --upgrade agentic-beacon` with `uv tool upgrade agentic-beacon`. Match the style of `site-docs/installation.md`.

## Phase 4 — Stale claims

- [ ] **4.1** `docs/agentic-warehouse-design.md` (~lines 308-313): Find the paragraph that says project `AGENTS.md` can override warehouse contexts. Delete or rewrite to reflect that overrides are not supported (see `docs/no-project-overrides.md`).
- [ ] **4.2** `docs/agentic-warehouse-design.md` (~line 397): Find the sentence claiming "the CLI only copies the declared artifacts to `.agentic-beacon/artifacts/`". Either:
  - Delete it, OR
  - Rewrite to say symlinks are created (matching the actual sync model).
- [ ] **4.3** `site-docs/concepts/how-it-works.md` (~lines 166-168): After the existing "warehouse must be on `main`" note, add a one-line note that this check is configurable via `abc warehouse connect --main-branch <name>` and `abc sync --skip-git-check`. Do not rewrite surrounding prose.

## Phase 5 — Small nits

- [ ] **5.1** `site-docs/reference/beacon-yaml.md` (~lines 107-111): Locate the duplicated `contexts/teams/backend/AGENTS.md` line in the contexts example. Delete the duplicate; keep one occurrence.
- [ ] **5.2** `site-docs/troubleshooting.md` (~line 36): The row `| \`abc install <artifact>\` | Edit \`beacon.yaml\`, then \`abc sync\` |` references a command that doesn't exist. Replace the left cell with realistic, supported guidance (e.g. delete the row entirely, or rewrite as `| Edit \`beacon.yaml\` and run \`abc sync\` | …  |`).
- [ ] **5.3** `site-docs/reference/cli.md` (~line 307): Same `abc install <artifact>` row. Same treatment as 5.2.

## Phase 6 — Verification

- [ ] **6.1** `grep -rn "knowledge/decisions/single-warehouse-write-entrypoint" README.md docs/ site-docs/`. Expected: zero output.
- [ ] **6.2** `grep -rn "local-warehouse-workflow" docs/ site-docs/`. Expected: zero output.
- [ ] **6.3** `grep -n "pip install --upgrade agentic-beacon" site-docs/troubleshooting.md`. Expected: zero output.
- [ ] **6.4** `grep -n "2\.7\.1" site-docs/installation.md`. Expected: zero output.
- [ ] **6.5** `grep -n "^knowledge:" docs/specs-vs-artifacts.md`. Expected: zero output (no top-level `knowledge:` key).
- [ ] **6.6** `python3 -c "import yaml; yaml.safe_load(open('docs/specs-vs-artifacts.md').read().split('\`\`\`yaml')[1].split('\`\`\`')[0])"` (or equivalent) — should parse without error AND have keys `warehouse` and/or `artifacts` only.
- [ ] **6.7** `awk '/contexts\/teams\/backend\/AGENTS.md/{c++} END{print c}' site-docs/reference/beacon-yaml.md`. Expected: `1` (single occurrence).
- [ ] **6.8** `grep -rn "abc install " site-docs/`. Expected: zero output (Phase 5.2 and 5.3 must have removed the last two stragglers).
- [ ] **6.9** Commit message: `docs: fix broken cross-references, stale examples, and pip→uv guidance`. Conventional Commits.

## Out of scope — DO NOT MODIFY

- `docs/migrations/**` — historical artifacts.
- Any file outside the explicit list in Phases 1-5.
- Agent-wiring claims (separate change, already complete).
- Adopt-auto-sync claims (separate change, already complete).
- SKILL.md frontmatter examples (separate change, already complete).
- Source code under `libs/beacon/`.
