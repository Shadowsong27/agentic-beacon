## 1. Core manifest & gitignore

- [ ] 1.1 Create `libs/beacon/src/beacon/core/manifest/pending.py` with `PendingEntry` Pydantic model (fields: `path: str`, `type: Literal["knowledge", "skill", "context", "agent"]`, `action: Literal["created", "modified"]`, `source: str`, `created_at: datetime`) and `PendingManifest` (wraps `pending: list[PendingEntry]`).
- [ ] 1.2 Implement `PendingManifest.from_yaml(path: Path) -> PendingManifest` that tolerates absent file (returns empty manifest) and raises clear validation errors on schema violations.
- [ ] 1.3 Implement `PendingManifest.to_yaml(path: Path) -> None` preserving field order (path / type / action / source / created_at) and pretty-printing with trailing newline.
- [ ] 1.4 Implement `PendingManifest.append(entry: PendingEntry) -> None` with in-memory mutation (persistence via `to_yaml`).
- [ ] 1.5 Unit tests: round-trip serialization, missing-field validation, invalid-enum validation, append-then-dump ordering, empty-file handling.
- [ ] 1.6 Update `libs/beacon/src/beacon/core/gitignore.py` template to include `.agentic-beacon/pending.yaml` and `.agentic-beacon/.last-adopt` alongside the existing `config.toml` entry.
- [ ] 1.7 Regenerate `examples/sample-warehouse/` gitignore output to reflect 1.6.

## 2. `.last-adopt` marker

- [ ] 2.1 Add helper `libs/beacon/src/beacon/domains/adoption/last_adopt.py` with `read_last_adopt(project_root: Path) -> datetime | None` and `write_last_adopt(project_root: Path, when: datetime) -> None`. Format: single ISO-8601 UTC line.
- [ ] 2.2 Unit tests: absent file returns `None`, write-then-read round-trips exactly, malformed file raises a clear error.

## 3. Pending alert hook

- [ ] 3.1 Add helper `libs/beacon/src/beacon/cli/pending_alert.py` with `maybe_emit_pending_alert(cwd: Path) -> None` that walks up for `.agentic-beacon/config.toml`, reads `pending.yaml` if present, and emits the one-line stderr notice when entries exist.
- [ ] 3.2 Wire the helper into the Click group entry in `libs/beacon/src/beacon/cli/main.py` (or root command decorator) so it runs before every `abc` subcommand.
- [ ] 3.3 Unit tests: alert fires with correct count, alert suppressed when `pending.yaml` absent or empty, alert suppressed when no `config.toml` in cwd-walk chain, alert does not block subcommand execution.

## 4. Adopt discovery merge

- [ ] 4.1 Extend `libs/beacon/src/beacon/domains/adoption/discovery.py` to merge two sources into one candidate list: entries from `pending.yaml`, and warehouse files modified since `.last-adopt` (via existing git-diff machinery).
- [ ] 4.2 Implement dedup by `path`: when both sources present, prefer the `pending.yaml` entry's metadata (source, created_at, action).
- [ ] 4.3 Annotate warehouse-diff-only entries with `source = "warehouse-modified"` (display-only; not written back to `pending.yaml`).
- [ ] 4.4 Unit tests: pending-only entry, warehouse-only entry, both-sources dedup, empty-both case.

## 5. Adopt TUI three-way actions

- [ ] 5.1 Extend `libs/beacon/src/beacon/domains/adoption/tui.py` per-entry action model from binary (accept/skip) to three-way (accept/reject/defer); update key bindings.
- [ ] 5.2 Add visual affordance showing each entry's current mark + its `source` label.
- [ ] 5.3 Ensure marking choices only update in-memory session state; no filesystem or config mutation during mark phase.
- [ ] 5.4 TUI unit/snapshot tests for the three-way mark transitions and display layout.

## 6. Adopt session-atomic Apply + confirm + rollback

- [ ] 6.1 Add Apply key binding that transitions to a confirm screen summarising `N accepted / N rejected / N deferred` with projected mutations (beacon.yaml adds, symlink syncs, pending.yaml reductions).
- [ ] 6.2 Implement commit transaction in `libs/beacon/src/beacon/domains/adoption/apply.py`: pre-snapshot `beacon.yaml`, `pending.yaml`, `.last-adopt`; apply accepts (beacon.yaml + symlink sync); apply rejects (drop from pending.yaml only, warehouse untouched); keep defers in pending.yaml; advance `.last-adopt`.
- [ ] 6.3 Implement rollback: on any mutation failure mid-commit, restore all three files to their pre-snapshot contents and surface a clear error identifying the failing entry.
- [ ] 6.4 Cancel from confirm screen leaves filesystem unchanged; verify by byte-equality of the three files before/after.
- [ ] 6.5 Integration test: 2 accept / 1 reject / 1 defer happy path → post-state matches expectations.
- [ ] 6.6 Integration test: induced symlink-sync failure mid-commit → all three files restored to pre-state; error message identifies failing entry.

## 7. record-knowledge skill revamp

- [ ] 7.1 Create `libs/beacon/src/beacon/data/skills/record-knowledge/scripts/resolve_warehouse.py` (PEP 723): walks up from `$PWD` for `.agentic-beacon/config.toml`, parses `[warehouse] local_path`, prints absolute path or errors to stderr and exits non-zero with the documented error text.
- [ ] 7.2 Create `libs/beacon/src/beacon/data/skills/record-knowledge/scripts/append_pending.py` (PEP 723): CLI flags `--path --type --action --source`; auto-stamps `created_at`; resolves project root via cwd-walk; appends to `.agentic-beacon/pending.yaml`; creates the file if absent.
- [ ] 7.3 Rewrite `record-knowledge/SKILL.md`: warehouse-target write flow, pointer-target prompt restricted to `<warehouse>/contexts/*.md` + "skip", diff-confirm before writing pointer, append-pending for both files (or just knowledge) depending on pointer decision, hard-error path when `resolve_warehouse.py` fails.
- [ ] 7.4 Explicitly remove all mention of writing to `.agentic-beacon/artifacts/knowledge/` and of updating `AGENTS.md` from the SKILL.md.
- [ ] 7.5 Manual happy-path test: run `record-knowledge` in this repo; verify knowledge file lands in warehouse, pointer diff is shown, `pending.yaml` receives correct entries.

## 8. record-skill skill revamp

- [ ] 8.1 Create `libs/beacon/src/beacon/data/skills/record-skill/scripts/resolve_warehouse.py` (PEP 723): independent copy of the record-knowledge helper.
- [ ] 8.2 Create `libs/beacon/src/beacon/data/skills/record-skill/scripts/append_pending.py` (PEP 723): independent copy of the record-knowledge helper.
- [ ] 8.3 Delete `libs/beacon/src/beacon/data/skills/record-skill/scripts/create_skill.py` and its compiled `__pycache__/create_skill.cpython-312.pyc`.
- [ ] 8.4 Rewrite `record-skill/SKILL.md`: LLM-driven flow gathering name / description / invocation / include-script; warehouse context scan for `requires.contexts` suggestion with accept / edit / skip; warehouse-target SKILL.md write (+ optional `scripts/<name>.py` PEP 723 scaffold); append-pending with `type: skill action: created source: record-skill`; hard-error path when `resolve_warehouse.py` fails.
- [ ] 8.5 Manual happy-path test: run `record-skill` in this repo; verify skill directory lands in warehouse, `requires.contexts` suggestion surfaces correctly, `pending.yaml` receives entry.

## 9. End-to-end integration tests

- [ ] 9.1 Integration test: author knowledge (no pointer) → one pending entry → `abc adopt` accept → beacon.yaml unchanged (knowledge is not a beacon.yaml artifact), pending.yaml empty, `.last-adopt` advanced.
- [ ] 9.2 Integration test: author knowledge (with pointer) → two pending entries → `abc adopt` accept both → context file symlink reflects the updated body in the project.
- [ ] 9.3 Integration test: author skill → one pending entry → `abc adopt` accept → beacon.yaml has new `skills/<name>/` entry, symlink created, pending.yaml empty.
- [ ] 9.4 Integration test: hand-edit a warehouse context file → no `pending.yaml` change → `abc adopt` picks up via `.last-adopt` diff → user accepts → handled correctly.
- [ ] 9.5 Integration test: run `abc warehouse status` in a project with non-empty `pending.yaml` → alert line appears first on stderr, command output follows, exit code unaffected.
- [ ] 9.6 Integration test: run `record-knowledge` in a project without `.agentic-beacon/config.toml` → hard error with documented text, no file writes.

## 10. Docs & sample warehouse

- [ ] 10.1 Add `docs/migrations/pending-artifacts-flow-and-record-revamp.md` covering: what `pending.yaml` is, how authoring skills changed, how `abc adopt` changed, breaking changes for `record-*` users, rollback path.
- [ ] 10.2 Update root `AGENTS.md` to reflect new `abc adopt` three-way actions and the pending alert.
- [ ] 10.3 Update site-docs page describing `.agentic-beacon/` layout to list `pending.yaml` and `.last-adopt`.
- [ ] 10.4 Regenerate `examples/sample-warehouse/` if anything structural changed (verify via `abc warehouse init` fresh-diff).

## 11. Release & verification

- [ ] 11.1 Run full test suite from repo root: `pytest` passes.
- [ ] 11.2 Verify `abc --version` and basic commands still work after install.
- [ ] 11.3 Smoke test `abc warehouse init test-warehouse` and confirm `.gitignore` in output includes new entries.
- [ ] 11.4 Smoke test `record-knowledge` and `record-skill` end-to-end in a fresh project connected to the sample warehouse.
- [ ] 11.5 Update CHANGELOG with breaking-change callout for `record-*` skills.
