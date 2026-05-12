# Tasks — fix-docs-agents-are-project-local

**Type:** Documentation only. No source code, no tests, no schema changes.

**Ground truth (verify only, do NOT modify):**

- `libs/beacon/src/beacon/domains/setup/wiring.py:335,385` — symlink targets are project-local `.claude/agents/<name>.md` and `.opencode/agents/<name>.md`.
- `libs/beacon/src/beacon/domains/artifact/agent.py:51-68` — adds project-local agent dirs to project root `.gitignore`.
- `abc --help` lists no `agents` subgroup and no `install` command.

## Phase 1 — AGENTS.md (project SSOT)

- [x] **1.1** Open `AGENTS.md`. Locate the "Artifact Distribution Model" section. Find the bullet that reads (approximately):
  > "Agents are declared per-project in `beacon.yaml.artifacts.agents` **AND** installed globally via symlinks into `~/.config/opencode/agents/` and `~/.claude/agents/`."
- [x] **1.2** Replace with a sentence that states agents are declared in `beacon.yaml.artifacts.agents` and wired into **project-local** `.claude/agents/<name>.md` and `.opencode/agents/<name>.md` symlinks (added to `.gitignore` automatically). Do not introduce new claims; just correct the location.

## Phase 2 — README.md

- [x] **2.1** In the ASCII distribution diagram around line 113, change the agents row from `~/.claude/agents/<name>.md` and `~/.config/opencode/agents/<name>.md` to `.claude/agents/<name>.md` and `.opencode/agents/<name>.md`. Replace any `abc agents sync` invocation with `abc sync`.
- [x] **2.2** Around line 137, rewrite the paragraph that mentions "global tool directories" so it describes project-local wiring. Keep the rest of the paragraph intact.
- [x] **2.3** Around line 123, remove or repoint the broken link `./knowledge/decisions/single-warehouse-write-entrypoint.md`. The target file does not exist. Acceptable replacements: link to `docs/no-project-overrides.md`, or simply delete the inline link and keep the prose.

## Phase 3 — docs/cli-reference.md

- [x] **3.1** Delete the entire **Agent Commands** subsection that documents `abc agents sync` (around line 34). Agents do not have a dedicated subcommand; they sync via plain `abc sync`.
- [x] **3.2** In the `abc list agents` description (around line 26), replace "globally installed agents" with "agents wired into the current project (`.claude/agents/`, `.opencode/agents/`)".

## Phase 4 — docs/artifact-type-matrix.md

- [x] **4.1** In the matrix table at lines ~18-24, move the **Agents** row from the "Global / Tool-specific" cell to "Project-scoped / Tool-specific" (same cell as Skills). If the table is structured by row-then-column, update the row's location-column to read `.claude/agents/<name>.md, .opencode/agents/<name>.md`.
- [x] **4.2** In the detailed per-type sections at lines ~55-87 (the Agents detailed block), rewrite locations to project-local. Remove any "Global / Tool-specific" labels.
- [x] **4.3** Around line 103-109, delete every reference to `abc install <artifact>`. Replace with `abc sync` (which is the actual sync command). If a sentence becomes meaningless after removing `abc install`, delete the sentence.

## Phase 5 — docs/no-project-overrides.md

- [x] **5.1** Around line 30, locate the "Historical note" mentioning `abc install` flag behaviour. Rewrite without referring to `abc install` (which never existed in the released CLI). Acceptable: delete the historical note entirely, or rephrase to describe the historical *concept* (an opt-out flag) without naming the non-existent command.

## Phase 6 — site-docs/index.md

- [x] **6.1** Around line 57, in the artifact-type matrix, move **Agents** from "Project-scoped / Tool-agnostic" to "Project-scoped / Tool-specific". The reasoning: agents have separate paths per tool (`.claude/agents/` vs `.opencode/agents/`), exactly like skills.

## Phase 7 — site-docs/concepts/artifact-types.md

- [x] **7.1** Around lines 8-11 (the matrix), same correction as Phase 6: move Agents into the Tool-specific column.
- [x] **7.2** If the body text further down still calls agents tool-agnostic, fix that mention too. Single source of truth: the code wires them tool-specifically.

## Phase 8 — site-docs/guides/connecting-projects.md

- [x] **8.1** Around line 97, the line that reads "Agents → declared per-project in `beacon.yaml` and **installed into global tool directories**" — change "global tool directories" to "project-local `.claude/agents/` and `.opencode/agents/` symlinks".

## Phase 9 — Verification

- [x] **9.1** Run `grep -rn "~/.claude/agents\|~/.config/opencode/agents\|installed globally\|globally installed" AGENTS.md README.md docs/ site-docs/ | grep -v "docs/migrations/\|docs/boot-context-design/"`. Expected: zero output.
- [x] **9.2** Run `grep -rn "abc agents sync\|abc install " AGENTS.md README.md docs/ site-docs/ | grep -v "docs/migrations/"`. Expected: zero output.
- [x] **9.3** Run `grep -rn "\.claude/agents/\|\.opencode/agents/" AGENTS.md README.md docs/cli-reference.md docs/artifact-type-matrix.md site-docs/index.md site-docs/concepts/artifact-types.md site-docs/guides/connecting-projects.md`. Expected: every file appears at least once (proves the project-local form is now present everywhere).
- [x] **9.4** Commit message: `docs: reconcile agent-wiring docs to project-local reality`. Follow Conventional Commits.

## Out of scope — DO NOT MODIFY

- `docs/migrations/**` — historical artifacts.
- `docs/boot-context-design/**` — design docs, preserved as-is.
- `openspec/**` — spec workflow, not docs.
- `libs/beacon/**` source code — implementation is correct.
- `.agentic-beacon/**` — symlinked warehouse copies, not project docs.
- Any other site-docs files not enumerated in Phases 6-8.
- The `abc adopt --all` flag claim or "adopt auto-syncs" myth — those belong to a separate change.
