## ADDED Requirements

### Requirement: pending.yaml file location and lifecycle

The system SHALL maintain a project-scoped file at `.agentic-beacon/pending.yaml` representing artifacts authored or modified in the warehouse from within this project but not yet wired into `beacon.yaml`. The file SHALL be gitignored by default so per-developer working state is never committed.

#### Scenario: File created on first authoring-skill write

- **WHEN** a user runs `record-knowledge` in a project with no existing `pending.yaml` and the skill completes successfully
- **THEN** the system creates `.agentic-beacon/pending.yaml` containing the new entry and the project's gitignore (or warehouse-supplied gitignore template) already excludes it

#### Scenario: File absent when project has no pending artifacts

- **WHEN** a project has never been authored into or has had every entry resolved via `abc adopt`
- **THEN** `.agentic-beacon/pending.yaml` MAY be absent, or present with `pending: []`; both states are equivalent

#### Scenario: Warehouse contribute does not touch pending.yaml

- **WHEN** a user runs `abc warehouse contribute` in any project
- **THEN** the command reads and writes the warehouse only; `pending.yaml` in the project is not created, read, or modified

---

### Requirement: pending.yaml entry schema

Each entry in `pending.yaml` SHALL carry exactly five fields: `path`, `type`, `action`, `source`, and `created_at`. All fields are required in v1; entries missing any field SHALL cause the file to fail validation at read time.

- `path`: warehouse-relative path to the artifact (e.g. `knowledge/lessons/foo.md`, `skills/bar/`).
- `type`: one of `knowledge`, `skill`, `context`, `agent`.
- `action`: one of `created` (a new artifact written by the skill) or `modified` (an existing warehouse file the skill edited).
- `source`: free-form string identifying the authoring skill (e.g. `record-knowledge`, `record-skill`); unknown values are tolerated by consumers.
- `created_at`: ISO-8601 UTC timestamp of when the entry was appended.

#### Scenario: Well-formed entry parses round-trip

- **WHEN** `pending.yaml` contains `[{path: knowledge/lessons/x.md, type: knowledge, action: created, source: record-knowledge, created_at: 2026-05-06T14:22:00Z}]`
- **THEN** loading and re-dumping the file preserves all fields exactly, with no field reordering that would change YAML key order beyond schema-defined order

#### Scenario: Missing required field fails validation

- **WHEN** a `pending.yaml` entry omits `type`
- **THEN** loading the file raises a validation error identifying the missing field and the entry index

#### Scenario: Invalid enum value fails validation

- **WHEN** a `pending.yaml` entry has `action: deleted`
- **THEN** loading the file raises a validation error listing the allowed values (`created`, `modified`)

#### Scenario: Unknown source is accepted

- **WHEN** a `pending.yaml` entry has `source: my-custom-authoring-skill`
- **THEN** the entry loads successfully; downstream consumers SHALL treat the source as a display grouping hint without coupling to a fixed enum

---

### Requirement: Authoring skill write contract

Any skill that authors or modifies a warehouse artifact SHALL append one entry to the current project's `pending.yaml` per artifact touched. The skill SHALL NOT write to `beacon.yaml`, the project's `AGENTS.md`, or any wiring file; the only project-side write target is `pending.yaml`.

#### Scenario: record-knowledge appends a single knowledge entry with no context pointer

- **WHEN** the user runs `record-knowledge`, accepts the generated knowledge file, and selects "skip" at the context-pointer prompt
- **THEN** exactly one entry is appended to `pending.yaml` with `path` pointing to the new knowledge file, `type: knowledge`, `action: created`, `source: record-knowledge`

#### Scenario: record-knowledge appends two entries when a context pointer is added

- **WHEN** the user runs `record-knowledge`, accepts the generated knowledge file, selects a warehouse context, and confirms the proposed pointer insert
- **THEN** two entries are appended to `pending.yaml`: one for the created knowledge file (`action: created`) and one for the modified context file (`action: modified`), both with `source: record-knowledge`

#### Scenario: record-skill appends a single skill entry

- **WHEN** the user runs `record-skill` and the skill successfully scaffolds `<warehouse>/skills/<name>/SKILL.md`
- **THEN** exactly one entry is appended with `path: skills/<name>/`, `type: skill`, `action: created`, `source: record-skill`

#### Scenario: Authoring skill does not mutate beacon.yaml

- **WHEN** any authoring skill completes successfully
- **THEN** `beacon.yaml` is byte-identical before and after the skill run

---

### Requirement: Warehouse root discovery via config.toml

Authoring skills SHALL discover the warehouse root by walking up from `$PWD` to find `.agentic-beacon/config.toml` and reading its `[warehouse] local_path` field. If no `config.toml` is found or the field is missing, the skill SHALL hard-error with a message directing the user to `abc warehouse connect`.

#### Scenario: Warehouse discovered from project root

- **WHEN** the user runs `record-knowledge` from a project whose `.agentic-beacon/config.toml` contains `[warehouse] local_path = "/home/user/warehouse"`
- **THEN** the skill writes the new knowledge file under `/home/user/warehouse/knowledge/<type>/<name>.md`

#### Scenario: Warehouse discovered from nested subdirectory

- **WHEN** the user runs `record-knowledge` from `<project>/src/foo/bar/`
- **THEN** the skill walks up to find `<project>/.agentic-beacon/config.toml` and resolves the warehouse the same as from the project root

#### Scenario: Missing config.toml hard-errors

- **WHEN** the user runs `record-knowledge` from a directory with no `.agentic-beacon/config.toml` in the cwd-walk chain
- **THEN** the skill aborts before any file write and prints: `Error: no warehouse connected. Run 'abc warehouse connect <path>' first.`

#### Scenario: Malformed config.toml hard-errors

- **WHEN** `.agentic-beacon/config.toml` is present but has no `[warehouse] local_path` field
- **THEN** the skill aborts with a parse error identifying the missing field

---

### Requirement: record-knowledge context-pointer behaviour

The `record-knowledge` skill SHALL offer to insert a pointer into a warehouse context file only. The project's `AGENTS.md` SHALL NOT appear as a pointer target. The pointer SHALL be inserted under an existing section in the target context file; the skill SHALL NOT create new section headings as a side effect.

#### Scenario: Context list shown from warehouse only

- **WHEN** `record-knowledge` reaches the pointer-target prompt
- **THEN** the user sees exactly: the list of `<warehouse>/contexts/*.md` files plus a "skip" option; `AGENTS.md` is not in the list

#### Scenario: Pointer inserted under existing section

- **WHEN** the user picks `contexts/python-standards.md` and the LLM identifies `## Exception Handling` as the best-fit existing section
- **THEN** the skill inserts a `**Brief:** ... **Read:** ...` block under that section, shows the user the proposed diff, and writes only on confirmation

#### Scenario: No fitting section surfaces a choice

- **WHEN** the user picks a context file but the LLM cannot identify any existing section that fits the knowledge topic
- **THEN** the skill surfaces "No section in <file> obviously fits this knowledge. Skip pointer, or pick a section manually?" and does not auto-create a new section under any circumstance

#### Scenario: Diff rejected leaves context file untouched

- **WHEN** the user declines the proposed pointer diff
- **THEN** the context file is byte-identical before and after; only the knowledge file entry is appended to `pending.yaml`

---

### Requirement: record-skill requires.contexts suggestion

The `record-skill` skill SHALL scan `<warehouse>/contexts/*.md` and propose a `requires.contexts:` list for the new skill based on the declared purpose. The user SHALL be able to accept, edit, or skip the suggestion. The skill's generated `SKILL.md` frontmatter SHALL include the resulting list (empty list permitted).

#### Scenario: Suggestion offered based on purpose match

- **WHEN** the user describes a new skill as "validate deployment readiness checklist" and the warehouse has `contexts/cicd-flow.md` and `contexts/python-standards.md`
- **THEN** `record-skill` proposes `requires.contexts: [contexts/cicd-flow.md, contexts/python-standards.md]` with rationale for each match

#### Scenario: User accepts the suggestion

- **WHEN** the user confirms the proposed `requires.contexts` list
- **THEN** the generated `SKILL.md` frontmatter contains that exact list

#### Scenario: User skips the suggestion

- **WHEN** the user declines all suggestions
- **THEN** the generated `SKILL.md` frontmatter contains `requires:\n  contexts: []`

#### Scenario: No matching contexts found

- **WHEN** the warehouse `contexts/` directory is empty or no context matches the declared purpose
- **THEN** the skill defaults to `requires.contexts: []` without prompting

---

### Requirement: .last-adopt timestamp marker

The system SHALL maintain a single-line ISO-8601 UTC timestamp at `.agentic-beacon/.last-adopt` recording when `abc adopt` last successfully committed. The marker SHALL be gitignored. The marker SHALL advance only on a successful adopt-session commit; session open, Ctrl-C, or cancel SHALL NOT modify the marker.

#### Scenario: Marker absent on first adopt

- **WHEN** `abc adopt` runs in a project where `.last-adopt` does not exist
- **THEN** warehouse-modified-since-marker discovery treats every warehouse file as new; the marker is created on successful commit

#### Scenario: Marker advances on successful commit

- **WHEN** `abc adopt` commits a session at `2026-05-06T15:00:00Z`
- **THEN** `.last-adopt` after the command contains exactly `2026-05-06T15:00:00Z` on a single line

#### Scenario: Marker unchanged on cancel

- **WHEN** the user opens `abc adopt`, marks accept/reject/defer choices, and cancels at the confirm screen
- **THEN** `.last-adopt` is byte-identical before and after the command

---

### Requirement: abc command pending alert

Every `abc` subcommand run inside a project (detected by the presence of `.agentic-beacon/config.toml` in the cwd-walk chain) SHALL print a one-line stderr notice when `pending.yaml` is non-empty. The notice SHALL include the entry count and point the user at `abc adopt`. The alert SHALL NOT block the invoked command from running.

#### Scenario: Alert printed when pending is non-empty

- **WHEN** the user runs `abc warehouse status` in a project whose `pending.yaml` contains 3 entries
- **THEN** the first line of stderr is `⚠ 3 pending artifacts. Run 'abc adopt' to wire them.` and the `warehouse status` command executes normally afterward

#### Scenario: No alert when pending is empty or absent

- **WHEN** the user runs `abc warehouse status` in a project with no `pending.yaml` or with `pending: []`
- **THEN** no pending-alert line appears on stderr

#### Scenario: Alert outside a project is suppressed

- **WHEN** the user runs `abc warehouse init` from a directory with no `.agentic-beacon/config.toml` in the cwd-walk chain
- **THEN** no pending-alert check is performed; command runs normally

---

### Requirement: abc adopt merged discovery of pending + warehouse-modified

The `abc adopt` TUI SHALL display entries drawn from two sources: entries in `.agentic-beacon/pending.yaml`, and warehouse files modified since `.last-adopt`. Entries appearing in both sources SHALL be deduplicated by `path`, with the `pending.yaml` entry's metadata (source, created_at, action) preferred. The TUI SHALL group or annotate entries by source so users can distinguish intent-driven entries from warehouse-diff entries.

#### Scenario: Pending-only entry appears

- **WHEN** `pending.yaml` contains `skills/new-skill/` (created) and no warehouse files have changed since `.last-adopt`
- **THEN** the TUI displays exactly one entry for `skills/new-skill/` with its `source` field visible

#### Scenario: Warehouse-only entry appears

- **WHEN** `pending.yaml` is empty but a warehouse file `contexts/hand-edited.md` was modified after `.last-adopt`
- **THEN** the TUI displays one entry for `contexts/hand-edited.md` annotated as "warehouse-modified (no source)"

#### Scenario: Entry in both sources is deduplicated

- **WHEN** `pending.yaml` contains `knowledge/lessons/x.md` and the warehouse diff since `.last-adopt` also shows `knowledge/lessons/x.md` as modified
- **THEN** the TUI displays exactly one entry for that path using the `pending.yaml` entry's source and created_at; no duplicate row appears

---

### Requirement: abc adopt three-way per-entry actions

For each displayed entry, the TUI SHALL allow the user to mark one of: **accept**, **reject**, or **defer**. Marking choices in the TUI SHALL NOT apply any filesystem or config mutation; choices are recorded in session state only until the user confirms at Apply.

#### Scenario: Accept selected for a pending entry

- **WHEN** the user marks a `skills/foo/` pending entry as accept
- **THEN** no file is changed yet; the session state records `foo → accept`

#### Scenario: Reject selected

- **WHEN** the user marks a `knowledge/lessons/x.md` pending entry as reject
- **THEN** no file is changed yet; the session state records `x → reject`

#### Scenario: Defer is the no-op default

- **WHEN** the user makes no explicit choice for an entry and hits Apply
- **THEN** the entry is treated as deferred and remains in `pending.yaml` after the session

---

### Requirement: abc adopt session-atomic Apply with confirm

The TUI SHALL require an explicit Apply action followed by a confirmation screen before any filesystem or config mutation. The confirmation screen SHALL summarise the totals of accepted / rejected / deferred entries and the projected mutations (beacon.yaml additions, symlink syncs, pending.yaml reductions). All mutations on confirm SHALL execute as a single logical transaction: on any mutation failure mid-commit, the system SHALL restore the pre-commit state of `beacon.yaml`, `pending.yaml`, and `.last-adopt`.

#### Scenario: Apply shows summary before commit

- **WHEN** the user marks 2 entries accept, 1 reject, 1 defer, and hits Apply
- **THEN** a confirm screen displays "2 accepted → wiring in beacon.yaml + syncing symlinks / 1 rejected → removing from pending.yaml / 1 deferred → keeping in pending.yaml" and waits for explicit confirmation

#### Scenario: Cancel from confirm screen makes no changes

- **WHEN** the user hits Cancel on the confirm screen
- **THEN** `beacon.yaml`, `pending.yaml`, and `.last-adopt` are byte-identical to their pre-session state

#### Scenario: Successful commit atomically advances state

- **WHEN** the user confirms a session with 2 accept / 1 reject / 1 defer
- **THEN** `beacon.yaml` has the 2 accepted entries appended to the correct artifact categories, symlinks for those entries are synced, `pending.yaml` contains only the 1 deferred entry, and `.last-adopt` is set to the commit timestamp

#### Scenario: Commit failure rolls back

- **WHEN** symlink sync for an accepted entry fails partway through the commit
- **THEN** `beacon.yaml`, `pending.yaml`, and `.last-adopt` are restored to their pre-commit state and the user sees a clear error identifying which entry failed

---

### Requirement: Reject does not touch warehouse files

Rejecting a pending entry SHALL remove it from `pending.yaml` only. The warehouse file referenced by the rejected entry SHALL be byte-identical before and after the adopt session. Warehouse-side cleanup is an explicit separate action via `abc warehouse contribute` or manual edit.

#### Scenario: Reject of a pending entry preserves the warehouse file

- **WHEN** the user rejects a `knowledge/lessons/x.md` pending entry and confirms
- **THEN** `pending.yaml` no longer contains the entry, and `<warehouse>/knowledge/lessons/x.md` exists with unchanged contents

#### Scenario: Reject of a warehouse-modified-only entry is a no-op beyond .last-adopt advance

- **WHEN** the user rejects a warehouse-modified entry that came only from the `.last-adopt` diff (not from `pending.yaml`)
- **THEN** no file is changed; the entry simply fails to appear in future adopt sessions because `.last-adopt` advances past its modification time

---

### Requirement: create_skill.py is removed

The PEP 723 script at `libs/beacon/src/beacon/data/skills/record-skill/scripts/create_skill.py` SHALL be deleted from the repository. Each record-* skill SHALL ship its own small helper scripts under its own `scripts/` directory, following the PEP 723 inline metadata convention. Shared helpers across skills SHALL NOT be introduced; duplication between `record-knowledge/scripts/` and `record-skill/scripts/` is the accepted cost of avoiding cross-skill coupling.

#### Scenario: File no longer exists

- **WHEN** the change is merged and a fresh checkout is inspected
- **THEN** `libs/beacon/src/beacon/data/skills/record-skill/scripts/create_skill.py` is absent from the tree

#### Scenario: Each record-* skill carries its own helpers

- **WHEN** the change is merged
- **THEN** both `record-knowledge/scripts/` and `record-skill/scripts/` directories contain their own independent copies of helpers (e.g. `resolve_warehouse.py`, `append_pending.py`) with PEP 723 `# /// script` metadata at the top of each

**Reason for retirement**: The script's three responsibilities (interactive prompting, markdown templating, file writes) are all handled more naturally by the LLM in the skill's markdown instructions. Its filesystem-target assumption (`.agentic-beacon/artifacts/skills/<name>/`) is incompatible with the warehouse-write model this change establishes. Rewriting it line-for-line would leave a layer of indirection with no functional benefit.

**Migration**: Users do not invoke `create_skill.py` directly in steady state (it is a skill-internal script). No user-facing migration is required. Skill behaviour changes are covered in `record-skill` requirements above.
