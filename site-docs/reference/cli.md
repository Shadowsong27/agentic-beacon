# CLI Reference

Complete reference for the `abc` CLI. All commands are subcommands of `abc`.

```bash
abc --help               # list all commands
abc <command> --help     # help for a specific command
abc --version            # show version
```

---

## Warehouse Commands

### `abc warehouse init`

Initialize a new warehouse repository.

```bash
abc warehouse init [NAME] [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `NAME` | Warehouse directory name (prompted if omitted) |
| `--path PATH` | Create warehouse at this path |
| `--org TEXT` | Organization name (used in generated templates) |
| `--languages TEXT` | Comma-separated languages to pre-populate |
| `--domains TEXT` | Comma-separated domains to pre-populate |
| `--no-git` | Skip `git init` |
| `--no-interactive` | Use defaults without prompting |

**Example:**
```bash
abc warehouse init my-org-warehouse
abc warehouse init my-warehouse --path ~/projects --no-interactive
```

---

### `abc warehouse connect`

Connect a project to a warehouse.

```bash
abc warehouse connect [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--path PATH` | Path to the warehouse (prompted if omitted) |

Creates `.agentic-beacon/config.toml` (gitignored) with the warehouse location.

**Example:**
```bash
abc warehouse connect --path ~/my-org-warehouse
```

---

### `abc warehouse list`

List artifacts available in the connected warehouse.

```bash
abc warehouse list [ARTIFACT_TYPE]
```

| Argument | Description |
|----------|-------------|
| (none) | List all artifact types |
| `agents` | List available agents |
| `knowledge` | List available knowledge |
| `skills` | List available skills |
| `contexts` | List available contexts |

---

### `abc warehouse contribute`

Commit changes in the warehouse working tree back to the warehouse repository.

```bash
abc warehouse contribute -m MESSAGE [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-m, --message TEXT` | Commit message (required) |
| `--push` | Push the commit to the remote after committing |
| `--paths TEXT` | Warehouse-relative path to commit (repeatable). When omitted, commits all `beacon.yaml`-tracked dirty paths. |

Stages and commits files tracked by `beacon.yaml` that have uncommitted changes in the warehouse clone.

**Example:**
```bash
abc warehouse contribute -m "Update python standards"
abc warehouse contribute -m "Fix typo" --push
abc warehouse contribute -m "Update skill" --paths skills/foo/SKILL.md
abc warehouse contribute -m "Split commit" --paths a.md --paths b.md
```

---

### `abc warehouse status`

Show warehouse working tree status.

```bash
abc warehouse status [PATH] [OPTIONS]
```

| Argument / Option | Description |
|---|---|
| `PATH` | Optional: show unified diff for this specific file |
| `--all` | Show unfiltered warehouse working-tree status |

**Example:**
```bash
abc warehouse status
abc warehouse status knowledge/python/standards.md
abc warehouse status --all
```

---

### `abc warehouse template-upgrade`

Upgrade warehouse template documentation to the latest version.

```bash
abc warehouse template-upgrade [WAREHOUSE_PATH] [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `WAREHOUSE_PATH` | Path to warehouse (defaults to current directory) |
| `--dry-run` | Preview changes without applying |
| `--interactive` | Prompt before each change |
| `--force` | Apply without confirmation |

---

### `abc warehouse lint`

> **Scope: warehouse-side.** Validates a warehouse's *internal* consistency —
> frontmatter, manifests, and cross-references between artifacts inside one
> warehouse. Run it from the warehouse repo (locally or in CI). For
> *project-side* wiring health — does this project's `.agentic-beacon/`
> resolve correctly into the connected warehouse? — use
> [`abc doctor`](#abc-doctor) instead.

Validate a warehouse directory end-to-end. Runs every Beacon-owned artifact
validation rule against the warehouse at `WAREHOUSE_PATH` (defaults to the
current working directory when omitted).

```bash
abc warehouse lint [WAREHOUSE_PATH]
```

| Option | Description |
|--------|-------------|
| `WAREHOUSE_PATH` | Path to warehouse directory (defaults to current directory) |
| `--fix` | Rewrite fixable cross-artifact-relative links to canonical `.agentic-beacon/artifacts/...` form before reporting remaining findings |

**Validation rules:**

1. **Structure preflight** — required directories (`agents/`, `contexts/`, `skills/`, `docs/`) and README exist.
2. **Skill frontmatter** — every `skills/*/SKILL.md` has a valid YAML frontmatter block that satisfies `SkillFrontmatter` (no `requires.skills` key; correct schema).
3. **Skill context references** — every context name in `requires.contexts` exists as `contexts/<name>.md`.
4. **Agent manifest** — `agents.yaml` is valid YAML; every `agents/*.md` file has a matching entry and vice versa; no legacy `requires:` keys in agent frontmatter; every declared skill exists under `skills/`.
5. **Agent frontmatter** — every `agents/*.md` (excluding `README.md`) has both a `name:` and `description:` YAML frontmatter key.
6. **Artifact link integrity** — every inline Markdown link in `contexts/*.md`, `skills/*/SKILL.md`, `agents/*.md`, and `knowledge/**/*.md` must satisfy the canonical artifact-link contract. Lint emits one finding per defect across four error categories: malformed cross-artifact-relative links, missing canonical targets, unresolved anchors, and warehouse-escape links. This rule is **lint-only**: `abc sync` retains its current warning-only behaviour for broken knowledge links.
7. **Context frontmatter** — every `contexts/**/*.md` (excluding `README.md`) must start with a YAML frontmatter block whose only key is `description`. A missing frontmatter block, a missing `description`, malformed frontmatter, an unknown key, or an empty or non-string `description` is an **error**. See [Context frontmatter](../guides/creating-knowledge-and-contexts.md#context-frontmatter).

**Exit codes:**

- `0` — No errors found. Output contains `✓ Lint passed.`, or `✓ Lint passed with N warning(s) across K file(s).` when only warnings were found.
- `1` — One or more errors found; output is grouped by artifact path with `error:` prefixes. Warnings print with `warning:` prefixes and never change the exit code.

**Example:**

```bash
# Lint the current directory (warehouse clone)
abc warehouse lint

# Lint a specific path
abc warehouse lint ~/my-org-warehouse

# Auto-rewrite fixable malformed links, then report any remaining errors
abc warehouse lint ~/my-org-warehouse --fix
```

With `--fix`, lint rewrites only cross-artifact-relative links into canonical
`.agentic-beacon/artifacts/<warehouse-relative-path>` form. Anchors are preserved,
the rewrite is idempotent, and running `--fix` on an already-clean file is a no-op.
It does not rewrite warehouse-escape links or invent missing targets; those remain
errors for a human to resolve.

> **Note:** `abc warehouse lint` is designed for warehouse-side CI. A freshly
> `abc warehouse init`-ed warehouse passes lint with exit code 0. The
> cross-repo CI workflow (`.github/workflows/lint.yml` in the warehouse repo)
> runs `uvx agentic-beacon==<pinned> warehouse lint .`.

---

## Project Setup

### `abc setup`

Create `.agentic-beacon/beacon.yaml` configuration.

```bash
abc setup
```

Creates a `beacon.yaml` template that declares which artifacts this project uses. Must be run after `abc warehouse connect`.

**Example:**
```bash
abc setup
```

---

## Core Commands

### `abc adopt`

Open an interactive TUI to browse and select warehouse artifacts. Applying your selection writes the new entries to `beacon.yaml` (clearing matching `pending.yaml` entries) and immediately syncs them — symlinks are created and contexts / skills / agents are wired into the project. In non-interactive contexts (no TTY) the command prints the candidate list and exits; you must edit `beacon.yaml` manually and then run `abc sync`. See [Pending & Adoption](../concepts/pending-and-adoption.md) for the underlying file model.

```bash
abc adopt [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview adoptable artifacts without modifying beacon.yaml |

**Keyboard shortcuts in TUI:**

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate |
| `Space` | Toggle selection |
| `Enter` | Confirm and write to `beacon.yaml` |
| `a` / `n` | Select all / Select none |
| `t` | Toggle show-all |
| `Esc` / `q` | Cancel |

---

### `abc sync`

Sync all artifacts declared in `beacon.yaml` from the warehouse.

```bash
abc sync [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--force` | Overwrite all conflicting files without prompting |
| `--dry-run` | Preview what would be synced without making changes |
| `--verbose` | Show per-file sync output |
| `--skip-git-check` | Skip warehouse git state validation |
| `--contribute-local` | Non-interactive: contribute all modified local files to warehouse |
| `--discard-local` | Non-interactive: discard all modified local files and replace with symlinks |
| `--yes` | Auto-accept prompts: add missing agent-required skills to `beacon.yaml` and remove orphaned artifacts no longer in `beacon.yaml` |

Without a terminal, sync never prompts: orphan pruning is skipped with a warning unless `--yes` is passed.

**What sync does per artifact type:**

| Artifact | Action |
|---|---|
| Knowledge | Create symlinks in `.agentic-beacon/artifacts/knowledge/` |
| Contexts | Create symlinks + wire into `AGENTS.md` or `opencode.json`; approve external imports for Claude Code in `~/.claude.json` |
| Skills | Create symlinks + install into tool-specific directories |
| Agents | Create artifact symlinks + wire into project-local `.claude/agents/` and `.opencode/agents/` |

---

## Status & Maintenance

### `abc status`

Show the current warehouse connection and configuration status.

```bash
abc status [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--project PATH` | Check a specific project directory |

Displays the connected warehouse path, configured contexts/skills (with ✓/✗ for synced status), bundled skills status, and total synced file count. See [Bundled Skills](../concepts/bundled-skills.md) for the list and walkthrough.

---

### `abc doctor`

> **Scope: project-side.** Validates that *this project's* beacon configuration
> resolves correctly into the connected warehouse. Run it from a project root
> (a directory containing `.agentic-beacon/`). For *warehouse-side* health —
> frontmatter, manifests, and internal cross-references inside a warehouse —
> use [`abc warehouse lint`](#abc-warehouse-lint) instead.

Diagnose the health of the current project's beacon configuration.

```bash
abc doctor [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--fix` | Auto-migrate stale paths to the current schema (reserved for future repair flows). |

**Checks today:**

1. **Project root** — `.agentic-beacon/` directory present.
2. **Warehouse connection** — `config.toml` exists and `warehouse.local_path` resolves to a real directory.
3. **Manifest validity** — `beacon.yaml` parses as YAML and matches the `BeaconManifest` schema.
4. **Skill resolution** — every entry in `artifacts.skills` maps to an existing `<warehouse>/skills/<name>/` directory.
5. **Context resolution** — every entry in `artifacts.contexts` maps to an existing `<warehouse>/contexts/<name>.md`.
6. **Claude Code approval** — when `AGENTS.md` imports beacon contexts, `~/.claude.json` approves external imports for the main checkout (`projects["<root>"].hasClaudeMdExternalIncludesApproved`). Fix: run `abc sync`.

**When to run:**

- After cloning a project that uses Agentic Beacon for the first time.
- After pulling warehouse changes that may have renamed or moved files referenced from your `beacon.yaml`.
- Before reporting an `abc sync` failure — doctor often pinpoints the root cause faster.

> **Note:** `abc doctor` currently prints findings to stdout and exits zero
> regardless of issue count. Programmatic exit-code behaviour (`--strict`,
> `--json`) is planned in a follow-up so the command can gate CI runs.

---

### `abc list`

List declared and synced project artifacts.

```bash
abc list [ARTIFACT_TYPE]
```

| Argument | Description |
|----------|-------------|
| (none) | List all synced artifacts |
| `agents` | List declared agents (read from `.agentic-beacon/artifacts/agents/`) |
| `knowledge` | List synced knowledge files |
| `skills` | List synced skills |
| `contexts` | List synced contexts |

---

### `abc clean`

Remove synced artifacts from the project.

```bash
abc clean [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--project PATH` | Clean a specific project directory |

Removes `.agentic-beacon/artifacts/` entirely. Run `abc sync` to re-sync.

---

### `abc reset`

Force-overwrite all synced artifacts from the warehouse.

```bash
abc reset [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--project PATH` | Reset a specific project directory |

Overwrites all symlinks from the warehouse, discarding any local modifications.

---

## Context Commands

### `abc context index`

Print the contexts of a warehouse commit as one JSON object. Built for tools that
need each context's name, path and description, such as the conductor's context
selector.

The index reads committed content at the ref, not the warehouse working tree.
Uncommitted edits do not change the output.

```bash
abc context index
abc context index --warehouse ~/warehouse --ref v1.2.0
```

| Option | Description |
|--------|-------------|
| `--warehouse PATH` | Warehouse git repository. Defaults to the warehouse connected in `.agentic-beacon/config.toml` |
| `--ref TEXT` | Commit-ish to index. Default `HEAD` |

**Output (stdout):**

```json
{
  "warehouse": "/abs/path/to/warehouse",
  "ref": "HEAD",
  "sha": "<40-hex commit sha>",
  "contexts": [
    {"name": "testing", "path": "contexts/testing.md", "description": "..."},
    {"name": "teams/backend", "path": "contexts/teams/backend.md", "description": "..."}
  ]
}
```

- `warehouse` is the resolved git root. `ref` is the `--ref` value as given. `sha` is the full commit the ref resolved to.
- `contexts` holds every `.md` file under `contexts/` at that commit, sorted by `path`. README files and dot-files are skipped. `name` is the path under `contexts/` without `.md`.
- `description` is the frontmatter key `description`, stripped of surrounding whitespace. A context with no usable description is listed with `""`.

**Warnings and errors (stderr):**

```text
warning: contexts/plain.md: File has no YAML frontmatter (must start with ---)
error: ref 'nope' not found in warehouse /abs/path/to/warehouse
```

A warning is printed for each context with no usable description, in path order, before the JSON. Warnings do not change the exit code.

**Exit codes:** `0` when the index is printed, `1` on any error. On exit `1` stdout is empty. Errors cover: no warehouse given and none connected, a warehouse path that is missing or not a git repository, an unknown ref, a commit with no `contexts/` directory, and a git failure.

### `abc context show`

Print the committed text of one or more contexts. Use it to read a context's body
without touching the working tree.

```bash
abc context show alpha teams/backend
abc context show alpha --warehouse ~/warehouse --ref v1.2.0
```

`NAMES` are context names as `abc context index` reports them, without `.md`. A name
given twice is printed once, at its first position.

**Output (stdout):**

```json
{
  "warehouse": "/abs/path/to/warehouse",
  "ref": "HEAD",
  "sha": "<40-hex commit sha>",
  "contexts": [
    {
      "name": "teams/backend",
      "path": "contexts/teams/backend.md",
      "text": "<the whole file>",
      "frontmatter": {"description": "..."},
      "body": "<text after the frontmatter>"
    }
  ]
}
```

### `abc context intake-policy`

Print the intake policy context of a board, `contexts/intake-policy-BOARD.md`.

```bash
abc context intake-policy AB
```

**Output (stdout):** the common keys, then `"board"` and `"policy"`, where `policy` is a
file record with `name` (`intake-policy-BOARD`), `path`, `text`, `frontmatter` and `body`.

### `abc context operate-profile`

Print the operate profile context of a domain, `contexts/operate-DOMAIN.md`.

```bash
abc context operate-profile airflow-platform
```

**Output (stdout):** the common keys, then `"domain"` and `"profile"`, where `profile` is
a file record as above.

### `abc context decision-rules`

Print the `## Decision rules` section of every context that has one, sorted by path.
A context with no such section is left out. No sections at all is exit `0` with an
empty list.

```bash
abc context decision-rules
```

**Output (stdout):**

```json
{
  "warehouse": "/abs/path/to/warehouse",
  "ref": "HEAD",
  "sha": "<40-hex commit sha>",
  "rules": [
    {"name": "testing", "path": "contexts/testing.md", "body": "DR1 ..."}
  ]
}
```

The section runs from the heading to the next `## ` heading or a `---` line. Leading and
trailing blank lines are dropped. The body is not split into rules.

**Common notes for the context read commands:**

- Every read command takes `--warehouse PATH` (defaults to the connected warehouse) and
  `--ref REF` (default `HEAD`). Output names the full `sha` the ref resolved to.
- Names are case-sensitive. Board and domain names match `[A-Za-z0-9][A-Za-z0-9_-]*`.
  Context names match `/`-separated segments of `[A-Za-z0-9][A-Za-z0-9._-]*`, with no
  `.md` suffix.
- A file record holds `name`, `path`, `text` (the committed file, unchanged), `frontmatter`
  (the parsed YAML block, or `null`) and `body` (the text after the block). A block that
  fails to parse gives `frontmatter: null`, the body still set, and a warning on stderr.
- Read commands never write. They read committed git objects only.

---

## Agent Commands

### `abc agent show`

Print one or more agent definitions from `agents/NAME.md`, with the frontmatter parsed.

```bash
abc agent show context-selector
abc agent show context-selector --warehouse ~/warehouse --ref v1.2.0
```

**Output (stdout):**

```json
{
  "warehouse": "/abs/path/to/warehouse",
  "ref": "HEAD",
  "sha": "<40-hex commit sha>",
  "agents": [
    {
      "name": "context-selector",
      "path": "agents/context-selector.md",
      "text": "<the whole file>",
      "frontmatter": {"name": "context-selector", "mode": "subagent"},
      "body": "<text after the frontmatter>"
    }
  ]
}
```

---

## Project Commands

### `abc project instructions`

Print the root `AGENTS.md` of a repository at a commit, with the lines that import
beacon-owned artifacts removed. Only the committed file is read.

```bash
abc project instructions
abc project instructions --repo ~/code/app --ref v2.0.0
```

| Option | Description |
|--------|-------------|
| `--repo PATH` | Project git repository. Any path inside it works. Default `.` |
| `--ref TEXT` | Commit-ish to read. Default `HEAD` |

A beacon-owned import is a line whose stripped text is `@.agentic-beacon/artifacts/...`.
Other `@` lines, including `@./.agentic-beacon/...`, are kept.

**Output (stdout):**

```json
{
  "repo": "/abs/path/to/app",
  "ref": "HEAD",
  "sha": "<40-hex commit sha>",
  "path": "AGENTS.md",
  "text": "# Project rules\n...\n",
  "removed": [".agentic-beacon/artifacts/contexts/alpha.md"]
}
```

- `text` has runs of three or more newlines collapsed to two, no trailing blank lines,
  and ends with one newline. It is `""` when nothing is left.
- `removed` lists each removed path in file order. A repeated import appears twice.

---

## Exit Codes for Read Commands

The read commands (`abc context show`, `intake-policy`, `operate-profile`,
`decision-rules`, `abc agent show` and `abc project instructions`) share these exit codes.

| Code | Meaning |
|------|---------|
| `0` | The item was read and printed |
| `1` | The source cannot be read: no warehouse or repo given or connected, a path that is missing or not a git repository, an unknown ref, a commit with no `contexts/` or `agents/` directory, a git failure, or a file that is not valid UTF-8 |
| `2` | Usage error: a bad option or a name that fails the name rules |
| `3` | The requested item is missing at the commit (a context, policy, profile, agent or `AGENTS.md`) |

On any non-zero exit, stdout is empty. The message is one line on stderr, for example:

```text
error: missing at 3f2a9c1e0b7d4a6f8c5e2b1a0d9c8b7a6f5e4d3c: contexts/gone.md, contexts/teams/nope.md
```

`abc context index` keeps its own exit codes: `0` on success and `1` on any error.

---

## Removed Commands

The following commands have been removed. If you are upgrading from a pre-v3
release, replace any scripted invocations with the modern equivalents below:

| Removed | Replacement |
|---------|-------------|
| `abc delta` | `abc warehouse status` |
| `abc contribute` | `abc warehouse contribute -m "message"` |
| `abc update` | `abc sync` (or `abc reset` to force-overwrite) |

---

## Global Options

Available on all commands:

| Option | Description |
|--------|-------------|
| `--verbose` | Enable debug-level logging |
| `--version` | Show version and exit |
| `--help` | Show help and exit |

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `abc warehouse init` | Create a new warehouse |
| `abc warehouse connect` | Connect a project to a warehouse |
| `abc warehouse list` | List available artifacts in warehouse |
| `abc warehouse status` | Show warehouse working tree changes |
| `abc warehouse contribute -m MESSAGE` | Commit warehouse changes back |
| `abc warehouse template-upgrade` | Upgrade warehouse template docs |
| `abc context index [--warehouse PATH] [--ref REF]` | Print warehouse contexts at a commit as JSON |
| `abc context show NAME... [--warehouse PATH] [--ref REF]` | Print committed text of one or more contexts as JSON |
| `abc context intake-policy BOARD [--warehouse PATH] [--ref REF]` | Print a board's intake policy context as JSON |
| `abc context operate-profile DOMAIN [--warehouse PATH] [--ref REF]` | Print a domain's operate profile context as JSON |
| `abc context decision-rules [--warehouse PATH] [--ref REF]` | Print the decision-rules section of every context as JSON |
| `abc agent show NAME... [--warehouse PATH] [--ref REF]` | Print agent definitions with parsed frontmatter as JSON |
| `abc project instructions [--repo PATH] [--ref REF]` | Print AGENTS.md at a commit with beacon import lines removed |
| `abc setup` | Create `beacon.yaml` configuration |
| `abc adopt` | Browse + select artifacts via TUI |
| `abc sync` | Sync all declared artifacts (contexts, skills, agents) |
| `abc status` | Show connection and sync status |
| `abc doctor` | Validate project health |
| `abc list` | List synced artifacts |
| `abc clean` | Remove synced artifacts |
| `abc reset` | Force-overwrite all artifacts |
