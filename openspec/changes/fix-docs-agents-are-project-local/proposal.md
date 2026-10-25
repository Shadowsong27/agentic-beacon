# fix-docs-agents-are-project-local

## Why

Multiple documentation files claim that Beacon installs agents **globally** into `~/.claude/agents/` and `~/.config/opencode/agents/`, and reference CLI commands (`abc agents sync`, `abc install <artifact>`) that do not exist. The current implementation is unambiguous:

- `libs/beacon/src/beacon/domains/setup/wiring.py:335,385` writes symlinks to **project-local** `.claude/agents/<name>.md` and `.opencode/agents/<name>.md`.
- `libs/beacon/src/beacon/domains/artifact/agent.py:51-68` adds `.claude/agents/` and `.opencode/agents/` to the **project root** `.gitignore` — confirming project-scoped placement.
- The `abc agents sync` and `abc install <artifact>` commands referenced by the docs do not exist in the CLI (`abc --help` lists only `adopt`, `clean`, `doctor`, `list`, `reset`, `setup`, `status`, `sync`, `warehouse`).

Users reading the affected docs are misled about where agents live and may run commands that fail. This change reconciles the docs to the implementation.

## What Changes

- **Source-of-truth correction (AGENTS.md):** Replace the "Agents … installed globally via symlinks into `~/.config/opencode/agents/` and `~/.claude/agents/`" bullet with the project-local truth.
- **README.md:** Fix the ASCII distribution diagram (line ~113) to show agents flowing to `.claude/agents/` and `.opencode/agents/`, replace `abc agents sync` with `abc sync`, and rewrite the "globally" paragraph at line ~137.
- **docs/cli-reference.md:** Delete the "Agent Commands" section that documents `abc agents sync`; fix the `abc list agents` description and the "global" claim.
- **docs/artifact-type-matrix.md:** Move agents out of "Global / Tool-specific" into "Project-scoped / Tool-specific"; delete the `abc install <artifact>` references.
- **docs/no-project-overrides.md:** Delete the `abc install` "historical note" or rewrite without referring to a non-existent command.
- **site-docs/index.md:** Fix the artifact-type matrix cell for Agents — move from "Tool-agnostic" to "Tool-specific" (matches Skills row).
- **site-docs/concepts/artifact-types.md:** Same correction — agents are tool-specific (different per-tool agent dir).
- **site-docs/guides/connecting-projects.md:** Fix the "installed into global tool directories" line.

## Out of Scope

- The `--all` flag on `abc adopt` (covered by `fix-docs-adopt-does-not-auto-sync`).
- The `abc adopt` auto-sync claim (covered by `fix-docs-adopt-does-not-auto-sync`).
- Any code changes — implementation is correct; only docs are wrong.
- `docs/migrations/**` — historical artifacts, intentionally preserved.
- `docs/boot-context-design/**` — design docs, intentionally preserved.

## Acceptance Criteria

After this change:

1. `grep -rn "~/.claude/agents\|~/.config/opencode/agents\|installed globally\|globally installed" AGENTS.md README.md docs/ site-docs/` returns **zero** matches outside `docs/migrations/` and `docs/boot-context-design/`.
2. `grep -rn "abc agents sync\|abc install " AGENTS.md README.md docs/ site-docs/` returns **zero** matches outside `docs/migrations/`.
3. Every mention of agents' wiring location in `README.md`, `AGENTS.md`, `docs/cli-reference.md`, `docs/artifact-type-matrix.md`, `docs/no-project-overrides.md`, `site-docs/index.md`, `site-docs/concepts/artifact-types.md`, and `site-docs/guides/connecting-projects.md` consistently states **project-local** paths (`.claude/agents/<name>.md`, `.opencode/agents/<name>.md`).
4. The artifact-type matrices in `docs/artifact-type-matrix.md`, `site-docs/index.md`, and `site-docs/concepts/artifact-types.md` agree: Agents live in the same Project-scoped / Tool-specific cell as Skills.
5. No new MkDocs build warnings are introduced (run `mkdocs build --strict` if mkdocs is available; otherwise grep for unresolved links).
